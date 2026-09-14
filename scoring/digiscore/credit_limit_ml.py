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


def recommend_credit_limit(
    dossier: dict | DossierInput,
    default_probability: float,
    *,
    rule_result: ScoreResult | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    """Retourne un plafond consultatif qui ne dépasse jamais le plafond règles.

    Un knockout bloque toute recommandation. Le résultat ne modifie pas le
    ``ScoreResult`` et ne constitue pas une décision d'octroi.
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
    recommended = floor(rule_cap * factor / ROUNDING_UNIT) * ROUNDING_UNIT
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
    }
