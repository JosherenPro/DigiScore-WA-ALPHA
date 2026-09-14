"""Facade d'integration ML, sans effet sur la decision regle existante."""

from __future__ import annotations

from typing import Any

from digiscore.adaptive.scorecard_ml import ml_enabled, predict_scorecard
from digiscore.anomalies import detect
from digiscore.types import DossierInput


def run_ml_assistance(
    dossier: dict | DossierInput,
    financials: dict | None = None,
    *,
    enabled: bool | None = None,
) -> dict[str, Any]:
    """Retourne les aides ML avec un fallback vide et contractuel.

    ``enabled`` est explicite dans les tests ; en production il est pilote par
    ``ML_ENABLED``. Aucun knockout et aucune decision ne transitent par cette
    facade.
    """

    active = ml_enabled() if enabled is None else enabled
    if not active:
        return {
            "enabled": False,
            "modele": None,
            "probabilite_defaut": None,
            "anomalies": [],
        }
    scorecard = predict_scorecard(dossier, financials)
    anomaly = detect(dossier, financials)
    return {
        "enabled": scorecard is not None or anomaly["enabled"],
        "modele": None
        if scorecard is None
        else {
            "version": scorecard.modele_version,
            "type": scorecard.modele_type,
            "methode_explication": scorecard.methode_explication,
            "score_global_ml": scorecard.score_global,
            "contributions": scorecard.contributions,
        },
        "probabilite_defaut": None if scorecard is None else scorecard.probabilite_defaut,
        "anomalies": anomaly["anomalies"],
        "anomaly_score": anomaly["anomaly_score"],
    }
