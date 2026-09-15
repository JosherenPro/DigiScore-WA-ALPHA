"""Routes ML consultatives (guide ML, phases 2-5).

Le ML éclaire, l'humain décide : ces routes n'écrivent ni `score_result` ni
`decision` et restent masquées par défaut (`ML_ENABLED=0`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import StaffUser
from app.db import get_db
from app.models.tables import Activity, CreditApplication
from app.schemas.ml import (
    AlertesOut,
    AnomaliesOut,
    PlafondMlOut,
    ScorecardShadowOut,
    SimulationIn,
    SimulationOut,
    SimulationSavedOut,
)
from app.services.advisory_service import assistance
from app.services.capabilities_service import ml_enabled
from app.services.anomaly_service import detect_anomalies
from app.services.dossier_builder import build_dossier
from app.services.early_warning_service import list_alerts
from app.services.resilience_service import (
    list_simulations,
    save_simulation,
    serialize_simulation,
    simulate,
)

router = APIRouter()


def require_ml() -> None:
    if not ml_enabled():
        raise HTTPException(503, "Capacités ML désactivées (ML_ENABLED=0)")


def _dossier_or_404(db: Session, demande_id: int) -> dict:
    try:
        return build_dossier(db, demande_id)
    except ValueError:
        raise HTTPException(404, "Demande introuvable") from None


def _run_simulation(demande_id: int, body: SimulationIn, dossier: dict, db: Session) -> dict:
    activite = db.scalars(
        select(Activity.activity_type).where(Activity.application_id == demande_id)
    ).first()
    try:
        return simulate(
            dossier,
            demande_id,
            scenario=body.scenario,
            montant=body.montant,
            duree_mois=body.duree_mois,
            horizon_mois=body.horizon_mois,
            iterations=body.iterations,
            seed=body.seed,
            activite=activite,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from None


@router.get("/demandes/{demande_id}/anomalies", tags=["ml"], response_model=AnomaliesOut)
def get_anomalies(
    demande_id: int,
    _user: StaffUser,
    _ml: None = Depends(require_ml),
    db: Session = Depends(get_db),
):
    return detect_anomalies(_dossier_or_404(db, demande_id))


@router.post("/demandes/{demande_id}/simuler", tags=["ml"], response_model=SimulationOut)
def post_simulation(
    demande_id: int,
    body: SimulationIn,
    _user: StaffUser,
    _ml: None = Depends(require_ml),
    db: Session = Depends(get_db),
):
    dossier = _dossier_or_404(db, demande_id)
    return _run_simulation(demande_id, body, dossier, db)


@router.post(
    "/demandes/{demande_id}/simulation/enregistrer",
    tags=["ml"],
    response_model=SimulationSavedOut,
    status_code=201,
)
def post_simulation_snapshot(
    demande_id: int,
    body: SimulationIn,
    user: StaffUser,
    _ml: None = Depends(require_ml),
    db: Session = Depends(get_db),
):
    dossier = _dossier_or_404(db, demande_id)
    result = _run_simulation(demande_id, body, dossier, db)
    return serialize_simulation(save_simulation(db, user.id, result))


@router.get(
    "/demandes/{demande_id}/simulations",
    tags=["ml"],
    response_model=list[SimulationSavedOut],
)
def get_simulations(
    demande_id: int,
    _user: StaffUser,
    _ml: None = Depends(require_ml),
    db: Session = Depends(get_db),
):
    if not db.get(CreditApplication, demande_id):
        raise HTTPException(404, "Demande introuvable")
    return [serialize_simulation(row) for row in list_simulations(db, demande_id)]


@router.get("/portefeuille/alertes", tags=["ml"], response_model=AlertesOut)
def get_alertes(
    user: StaffUser,
    limit: int = Query(20, ge=1, le=100),
    _ml: None = Depends(require_ml),
    db: Session = Depends(get_db),
):
    agency_id = user.agency_id if user.role in ("chef_agence", "agent") else None
    agent_id = user.id if user.role == "agent" else None
    return list_alerts(db, limit=limit, agency_id=agency_id, agent_id=agent_id)


@router.get(
    "/demandes/{demande_id}/ml/scorecard",
    tags=["ml"],
    response_model=ScorecardShadowOut,
)
def get_scorecard_shadow(
    demande_id: int,
    _user: StaffUser,
    _ml: None = Depends(require_ml),
    db: Session = Depends(get_db),
):
    """Scorecard v3 en shadow : probabilite indicative, jamais decisionnelle."""
    dossier = _dossier_or_404(db, demande_id)
    result = assistance(db, demande_id, dossier)
    sc = result.get("scorecard") or {}
    return {
        "model_version": sc.get("modele_version"),
        "mode": "shadow",
        "probabilite_defaut": sc.get("probabilite_defaut"),
        "score_global_ml": sc.get("score_global_ml"),
        "niveau_risque": sc.get("niveau_risque"),
        "regles_knockout": bool(sc.get("regles_knockout", False)),
        "top_factors": sc.get("top_factors", []),
        "contributions": sc.get("contributions", []),
        "warning": result.get("warning"),
    }


@router.get(
    "/demandes/{demande_id}/ml/plafond",
    tags=["ml"],
    response_model=PlafondMlOut,
)
def get_plafond_ml(
    demande_id: int,
    _user: StaffUser,
    _ml: None = Depends(require_ml),
    db: Session = Depends(get_db),
):
    """Plafond ML indicatif : decote du plafond regles, null si knockout."""
    dossier = _dossier_or_404(db, demande_id)
    plafond = assistance(db, demande_id, dossier).get("plafond_ml") or {}
    return {
        "enabled": bool(plafond.get("enabled", False)),
        "blocked_by_knockout": bool(plafond.get("blocked_by_knockout", False)),
        "model_version": plafond.get("model_version"),
        "plafond_regles": plafond.get("plafond_regles"),
        "plafond_ml_recommande": plafond.get("plafond_ml_recommande"),
        "probabilite_defaut": plafond.get("probabilite_defaut"),
        "facteur_prudence": plafond.get("facteur_prudence"),
        "explication": plafond.get("explication"),
        "detail": plafond.get("detail") or {},
        "raisons": plafond.get("raisons") or [],
    }
