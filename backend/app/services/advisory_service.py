"""Orchestration ML consultative (guide ML).

Le ML éclaire, l'humain décide : ce service n'écrit ni `score_result` ni
`decision`. Les capacités restent masquées par défaut (`ML_ENABLED=0`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.capabilities_service import capabilities, ml_enabled
from app.services.dossier_builder import build_dossier
from app.services.resilience_service import resolve_scenario

__all__ = ["assistance", "capabilities", "ml_enabled", "simulate"]

try:
    from digiscore.adaptive.scorecard_ml import predict_scorecard_v3
except ImportError:  # scoring non installe
    predict_scorecard_v3 = None  # type: ignore

try:
    from digiscore.anomalies import detect_v3
except ImportError:
    detect_v3 = None  # type: ignore

try:
    from digiscore.credit_limit_ml import recommend_credit_limit
except ImportError:
    recommend_credit_limit = None  # type: ignore

try:
    from digiscore.pipeline import run as run_rules
except ImportError:
    run_rules = None  # type: ignore

try:
    from digiscore.simulation import simulate_resilience
except ImportError:
    simulate_resilience = None  # type: ignore


def _niveau_risque(probability: float | None) -> str | None:
    if probability is None:
        return None
    if probability <= 0.10:
        return "faible"
    if probability <= 0.20:
        return "modere"
    if probability <= 0.35:
        return "eleve"
    return "tres_eleve"


def assistance(db: Session, application_id: int, dossier: dict | None = None) -> dict[str, Any]:
    """Assistance ML v3 (shadow) : scorecard + anomalies + plafond consultatif."""
    dossier = dossier or build_dossier(db, application_id)
    rule_result = None
    if run_rules is not None:
        try:
            rule_result = run_rules(dossier)
        except Exception:
            rule_result = None
    rules_knockout = bool(rule_result.knockouts) if rule_result is not None else False
    out: dict[str, Any] = {
        "model_version": "scorecard-v3",
        "mode": "shadow",
        "scorecard": None,
        "anomalies": {"enabled": False, "anomalies": [], "anomaly_score": 0.0,
                      "scope_excluded": False, "model_version": None},
        "plafond_ml": None,
        "warning": "Volume synthetique : pipeline technique OK, pas un risque reel. Ne decide jamais.",
    }
    if rules_knockout:
        out["warning"] = (
            "Knockout metier present : l'avis ML ne s'applique pas. "
            + out["warning"]
        )
    if predict_scorecard_v3 is not None:
        try:
            sc = predict_scorecard_v3(dossier)
        except Exception:
            sc = None
        if sc is not None:
            out["scorecard"] = {
                "score_global_ml": sc.score_global,
                "probabilite_defaut": sc.probabilite_defaut,
                "niveau_risque": None if rules_knockout else _niveau_risque(sc.probabilite_defaut),
                "regles_knockout": rules_knockout,
                "modele_version": sc.modele_version,
                "modele_type": sc.modele_type,
                "top_factors": [
                    {"feature": c["feature"], "contribution": c["contribution"]}
                    for c in (sc.contributions or [])[:3]
                ],
                "contributions": sc.contributions,
            }
            out["model_version"] = sc.modele_version
    if detect_v3 is not None:
        try:
            out["anomalies"] = detect_v3(dossier)
        except Exception:
            pass
    if recommend_credit_limit is not None and rule_result is not None and out["scorecard"]:
        try:
            out["plafond_ml"] = recommend_credit_limit(
                dossier,
                out["scorecard"]["probabilite_defaut"],
                rule_result=rule_result,
                model_version=out["scorecard"]["modele_version"],
            )
        except Exception:
            out["plafond_ml"] = None
    return out


def simulate(db: Session, application_id: int, scenario: str | dict[str, Any] | None,
             montant: float | None = None, duree_mois: int | None = None,
             seed: int = 72) -> dict[str, Any]:
    dossier = build_dossier(db, application_id)
    if simulate_resilience is None:
        raise RuntimeError("moteur de simulation indisponible")
    _, payload = resolve_scenario(scenario)
    return simulate_resilience(dossier, scenario=payload, montant=montant,
                               duree_mois=duree_mois, seed=seed)
