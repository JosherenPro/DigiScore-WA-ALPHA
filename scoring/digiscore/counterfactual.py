"""Contrefactuels explicables pour franchir un seuil sans contourner les KO."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from digiscore.pipeline import run
from digiscore.types import DossierInput, ScoreResult


def _validated(dossier: dict | DossierInput) -> DossierInput:
    return dossier if isinstance(dossier, DossierInput) else DossierInput.model_validate(dossier)


def _evaluate(dossier: DossierInput) -> ScoreResult:
    return run(dossier)


def _clone(dossier: DossierInput) -> DossierInput:
    return DossierInput.model_validate(deepcopy(dossier.model_dump()))


def _search_first(
    dossier: DossierInput,
    candidates: list[float],
    setter: Callable[[DossierInput, float], None],
    target_score: float,
) -> tuple[float, ScoreResult] | None:
    for value in candidates:
        candidate = _clone(dossier)
        setter(candidate, value)
        result = _evaluate(candidate)
        if not result.knockouts and result.score_global >= target_score:
            return value, result
    return None


def suggest_counterfactuals(
    dossier: dict | DossierInput,
    *,
    target_score: float = 71.0,
) -> dict[str, Any]:
    """Renvoie les plus petites variations candidates pour atteindre un score.

    Les knock-outs sont une barriere explicite : le module renvoie alors une
    reponse bloquee et ne propose pas de modifier artificiellement le RCSD,
    les incidents ou les garde-fous.
    """

    d = _validated(dossier)
    base = _evaluate(d)
    target = max(0.0, min(100.0, float(target_score)))
    if base.knockouts:
        return {
            "blocked_by_knockout": True,
            "knockouts": [knockout.model_dump() for knockout in base.knockouts],
            "base_score": base.score_global,
            "items": [],
        }
    if base.score_global >= target:
        return {
            "blocked_by_knockout": False,
            "base_score": base.score_global,
            "items": [],
        }

    current_age = max(0, d.membre.anciennete_mois)
    current_savings = max(0.0, d.historique.epargne_moy_6m)
    current_guarantees = max(0.0, d.analyse.valeur_garanties)
    current_duration = max(1, d.demande.duree_mois)
    candidates = [
        (
            "epargne_moy_6m",
            [current_savings + step for step in range(10000, 500001, 10000)],
            lambda item, value: setattr(item.historique, "epargne_moy_6m", value),
            lambda value: value - current_savings,
        ),
        (
            "valeur_garanties",
            [current_guarantees + step for step in range(10000, 1000001, 10000)],
            lambda item, value: setattr(item.analyse, "valeur_garanties", value),
            lambda value: value - current_guarantees,
        ),
        (
            "duree_mois",
            [float(value) for value in range(current_duration + 1, 61)],
            lambda item, value: setattr(item.demande, "duree_mois", int(value)),
            lambda value: value - current_duration,
        ),
        (
            "anciennete_mois",
            [float(value) for value in range(current_age + 1, max(current_age + 1, 37))],
            lambda item, value: setattr(item.membre, "anciennete_mois", int(value)),
            lambda value: value - current_age,
        ),
    ]
    items: list[dict[str, Any]] = []
    for lever, values, setter, variation in candidates:
        found = _search_first(d, values, setter, target)
        if not found:
            continue
        value, result = found
        items.append(
            {
                "levier": lever,
                "unite": "FCFA" if lever in {"epargne_moy_6m", "valeur_garanties"} else "mois",
                "variation_min": variation(value),
                "nouvelle_valeur": value,
                "nouveau_score": result.score_global,
                "nouveau_plafond": result.montant_eligible,
                "message": result.message_code,
            }
        )
    return {"blocked_by_knockout": False, "base_score": base.score_global, "items": items}
