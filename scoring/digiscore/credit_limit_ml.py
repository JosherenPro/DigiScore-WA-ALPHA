"""Recommandation prudente de plafond, complémentaire aux règles métier."""

from __future__ import annotations

from math import floor
from typing import Any

from digiscore.pipeline import run
from digiscore.types import DossierInput, ScoreResult

MODEL_VERSION = "credit-limit-advisory-v1"
ROUNDING_UNIT = 10_000


def _validated(dossier: dict | DossierInput) -> DossierInput:
    return dossier if isinstance(dossier, DossierInput) else DossierInput.model_validate(dossier)


def _risk_factor(default_probability: float) -> float:
    """Applique une décote prudente selon le risque ML indicatif."""
    probability = max(0.0, min(1.0, float(default_probability)))
    if probability <= 0.10:
        return 1.00
    if probability <= 0.20:
        return 0.90
    if probability <= 0.35:
        return 0.75
    return 0.60


def _tranche_risque(probability: float) -> str:
    """Tranche de la grille p -> facteur, en clair (auditabilite)."""
    probability = max(0.0, min(1.0, float(probability)))
    if probability <= 0.10:
        return "p ≤ 0,10 : risque faible"
    if probability <= 0.20:
        return "0,10 < p ≤ 0,20 : risque modéré"
    if probability <= 0.35:
        return "0,20 < p ≤ 0,35 : risque élevé"
    return "p > 0,35 : risque très élevé"


def recommend_credit_limit(
    dossier: dict | DossierInput,
    default_probability: float,
    *,
    rule_result: ScoreResult | None = None,
    model_version: str | None = None,
    facteurs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Retourne un plafond consultatif qui ne dépasse jamais le plafond règles.

    Un knockout bloque toute recommandation. Le résultat ne modifie pas le
    ``ScoreResult`` et ne constitue pas une décision d'octroi.

    Le calcul est entierement decompose dans ``detail`` (chaque etape est
    auditable) et resume en langage clair dans ``raisons``.
    """

    d = _validated(dossier)
    result = rule_result or run(d)
    if result.knockouts:
        return {
            "enabled": True,
            "blocked_by_knockout": True,
            "model_version": model_version or MODEL_VERSION,
            "plafond_regles": result.montant_eligible,
            "plafond_ml_recommande": None,
            "probabilite_defaut": round(max(0.0, min(1.0, default_probability)), 6),
            "facteur_prudence": None,
            "explication": "Aucune recommandation ML : un knockout métier bloque le dossier.",
        }

    probability = max(0.0, min(1.0, float(default_probability)))
    factor = _risk_factor(probability)
    rule_cap = max(0.0, result.montant_eligible)
    avant_arrondi = rule_cap * factor
    recommended = floor(avant_arrondi / ROUNDING_UNIT) * ROUNDING_UNIT
    demande = max(0.0, float(d.demande.montant))
    def _fcfa(montant: float) -> str:
        return f"{montant:,.0f}".replace(",", " ")

    raisons = [
        f"Plafond règles : {_fcfa(rule_cap)} FCFA (capacité RCSD, garanties, moteur règles).",
        f"Risque estimé p = {probability:.4f} → {_tranche_risque(probability)} : décote {int((1 - factor) * 100)} % (×{factor}).",
        f"Arrondi prudent au {_fcfa(ROUNDING_UNIT)} FCFA inférieur : −{_fcfa(avant_arrondi - recommended)} FCFA.",
    ]
    if facteurs:
        top = facteurs[0]
        raisons.append(
            f"Principal driver du risque : {top.get('feature')} "
            f"(contribution {float(top.get('contribution', 0)):+.2f} au logit)."
        )
    if recommended >= demande:
        raisons.append(
            f"Montant demandé ({_fcfa(demande)} FCFA) couvert avec une marge de "
            f"{_fcfa(recommended - demande)} FCFA."
        )
    else:
        raisons.append(
            f"Montant demandé ({_fcfa(demande)} FCFA) NON couvert : écart de "
            f"{_fcfa(demande - recommended)} FCFA sous le plafond recommandé."
        )
    return {
        "enabled": True,
        "blocked_by_knockout": False,
        "model_version": model_version or MODEL_VERSION,
        "plafond_regles": rule_cap,
        "plafond_ml_recommande": recommended,
        "probabilite_defaut": round(probability, 6),
        "facteur_prudence": factor,
        "explication": (
            "Plafond ML indicatif : plafond règles réduit par une décote de "
            f"{int((1 - factor) * 100)} % liée au risque estimé."
        ),
        "detail": {
            "plafond_regles": rule_cap,
            "probabilite_defaut": round(probability, 6),
            "tranche_risque": _tranche_risque(probability),
            "facteur_prudence": factor,
            "decote_fcfa": round(rule_cap - avant_arrondi, 2),
            "avant_arrondi": round(avant_arrondi, 2),
            "arrondi_unite": ROUNDING_UNIT,
            "perte_arrondi_fcfa": round(avant_arrondi - recommended, 2),
            "montant_demande": demande,
            "couverture_demande": recommended >= demande,
            "ecart_demande_fcfa": round(recommended - demande, 2),
        },
        "raisons": raisons,
    }
