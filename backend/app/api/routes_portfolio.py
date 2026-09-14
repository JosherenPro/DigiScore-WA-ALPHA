"""Routes suivi portefeuille M6 / recouvrement M7 — calculées depuis la base.

M6 : échéances du jour, aging, PAR 1/30/90, visites V1/V2/V3, 12 signaux FUCEC.
M7 : matrice de priorisation, 4 niveaux, journal d'actions.
Le ML consultatif reste sur `/portefeuille/alertes` (tag `ml`).
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import ReviewerUser, StaffUser
from app.db import get_db
from app.models.tables import (
    AuditLog,
    Member,
    OutstandingLoan,
    ParIndicator,
    PortfolioFollowup,
    RecoveryAction,
    RecoveryCase,
)
from app.schemas.dossier import VisionPortefeuilleOut, VisionRecouvrementOut
from app.schemas.portfolio import (
    ActionRecouvrementIn,
    ActionRecouvrementOut,
    AgingOut,
    DossiersOut,
    EcheancesOut,
    ParRecalculOut,
    SignauxOut,
    VisiteIn,
    VisitesOut,
    VisiteOut,
)
from app.services import portfolio_service as svc

router = APIRouter()


def _date(value: str | None, *, default_today: bool = True) -> date:
    if not value:
        if default_today:
            return date.today()
        raise HTTPException(422, "Date requise (AAAA-MM-JJ)")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(422, "Date invalide (AAAA-MM-JJ)") from None


def _agency_scope(user) -> int | None:
    return user.agency_id if user.role == "chef_agence" else None


def _agences(db: Session, agency_id: int | None) -> list[int]:
    stmt = select(Member.agency_id).join(OutstandingLoan, OutstandingLoan.member_id == Member.id)
    if agency_id is not None:
        stmt = stmt.where(Member.agency_id == agency_id)
    return sorted({row for row in db.scalars(stmt.distinct()).all() if row is not None})


def _member_state(db: Session, member_id: int) -> tuple[float, int]:
    row = db.execute(
        select(
            func.coalesce(func.sum(OutstandingLoan.outstanding), 0),
            func.max(OutstandingLoan.days_late),
        ).where(OutstandingLoan.member_id == member_id, OutstandingLoan.status != "solde")
    ).one()
    return float(row[0] or 0), int(row[1] or 0)


@router.get("/vision/portefeuille", tags=["vision"], response_model=VisionPortefeuilleOut)
def vision_portefeuille(
    user: StaffUser,
    as_of: str | None = None,
    db: Session = Depends(get_db),
):
    day = _date(as_of)
    agency = _agency_scope(user)
    agences = _agences(db, agency)
    snapshots = [svc.par_snapshot(db, day, item) for item in agences]
    if snapshots:
        par = [
            {
                "agence_id": snap["agency_id"],
                "par1": snap["par1"],
                "par30": snap["par30"],
                "par90": snap["par90"],
                "encours_brut": snap["encours_brut"],
                "label": svc.par_label(snap["par30"]),
            }
            for snap in snapshots
        ]
    else:
        rows = db.scalars(select(ParIndicator).where(ParIndicator.as_of <= day).order_by(ParIndicator.as_of.desc())).all()
        seen: set[int | None] = set()
        par = []
        for row in rows:
            if row.agency_id in seen:
                continue
            seen.add(row.agency_id)
            par.append(
                {
                    "agence_id": row.agency_id,
                    "par1": float(row.par1_pct or 0),
                    "par30": float(row.par30_pct or 0),
                    "par90": float(row.par90_pct or 0),
                    "encours_brut": float(row.encours_brut or 0),
                    "label": svc.par_label(float(row.par30_pct or 0)),
                }
            )

    stmt = (
        select(OutstandingLoan, Member)
        .join(Member, Member.id == OutstandingLoan.member_id)
        .where(OutstandingLoan.status != "solde", OutstandingLoan.days_late > 0)
        .order_by(OutstandingLoan.days_late.desc())
        .limit(5)
    )
    if agency is not None:
        stmt = stmt.where(Member.agency_id == agency)
    alertes = []
    for loan, member in db.execute(stmt).all():
        retard = int(loan.days_late or 0)
        detail = svc.niveau_detail(retard) or {}
        alertes.append(
            {
                "signal": f"Retard {retard} j - niveau N{detail.get('niveau')}",
                "membre_id": member.id,
                "member_code": member.external_code,
                "days_late": retard,
                "niveau": detail.get("niveau"),
                "priorite": svc.priorite(float(loan.outstanding or 0), retard),
            }
        )
    return {"module": "M6 portefeuille (calcule)", "as_of": day.isoformat(), "par": par, "alertes": alertes}


@router.get("/vision/recouvrement", tags=["vision"], response_model=VisionRecouvrementOut)
def vision_recouvrement(
    user: StaffUser,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    agence = _agency_scope(user)
    stmt = (
        select(RecoveryCase, Member)
        .join(Member, Member.id == RecoveryCase.member_id)
        .where(RecoveryCase.status != "clos")
        .order_by(RecoveryCase.level.desc(), RecoveryCase.opened_on.desc())
        .limit(limit)
    )
    if agence is not None:
        stmt = stmt.where(Member.agency_id == agence)
    dossiers = []
    for case, member in db.execute(stmt).all():
        detail = svc.niveau_detail((case.level - 1) * 30 + 1) or {}
        dossiers.append(
            {
                "membre_id": member.id,
                "niveau": case.level,
                "action": case.action or detail.get("actions"),
                "responsable": case.owner_name or detail.get("responsable"),
            }
        )
    return {"module": "M7 recouvrement (calcule)", "dossiers": dossiers}


@router.get("/vision/aging", tags=["vision"], response_model=AgingOut)
def vision_aging(
    user: StaffUser,
    as_of: str | None = None,
    db: Session = Depends(get_db),
):
    day = _date(as_of)
    snap = svc.par_snapshot(db, day, _agency_scope(user))
    return {
        "as_of": day.isoformat(),
        "par1": snap["par1"],
        "par30": snap["par30"],
        "par90": snap["par90"],
        "label": svc.par_label(snap["par30"]),
        "encours_brut": snap["encours_brut"],
        "buckets": svc.aging_report(db, day, _agency_scope(user)),
    }


@router.get("/vision/echeances", tags=["vision"], response_model=EcheancesOut)
def vision_echeances(
    user: StaffUser,
    jour: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    day = _date(jour)
    items = svc.echeances_du_jour(db, day, _agency_scope(user), limit=limit)
    return {"jour": day.isoformat(), "items": [{**item, "due_on": item["due_on"].isoformat() if item["due_on"] else None, "jour": day.isoformat()} for item in items]}


@router.get("/vision/visites", tags=["vision"], response_model=VisitesOut)
def vision_visites(
    user: StaffUser,
    as_of: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    day = _date(as_of)
    items = svc.visites_a_faire(db, day, _agency_scope(user), limit=limit)
    return {
        "as_of": day.isoformat(),
        "items": [{**item, "cible": item["cible"].isoformat()} for item in items],
    }


@router.post("/vision/visites", tags=["vision"], response_model=VisiteOut, status_code=201)
def log_visite(body: VisiteIn, user: StaffUser, db: Session = Depends(get_db)):
    member = db.get(Member, body.member_id)
    if not member:
        raise HTTPException(404, "Membre introuvable")
    _, retard = _member_state(db, member.id)
    row = PortfolioFollowup(
        member_id=member.id,
        visit_code=body.visit_code,
        visit_on=_date(body.visit_on) if body.visit_on else date.today(),
        officer_id=body.officer_id or user.id,
        days_late=retard,
        signal=body.signal,
        signal_code=body.signal_code,
        visit_status=body.visit_status,
        next_on=_date(body.next_on) if body.next_on else None,
        action_taken=body.action_taken,
    )
    db.add(row)
    db.add(
        AuditLog(
            application_id=None,
            user_id=user.id,
            action="visite_m6",
            detail=f"{body.visit_code} membre {member.external_code} signal={body.signal_code or '-'}",
        )
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "member_id": row.member_id,
        "visit_code": row.visit_code,
        "visit_on": row.visit_on.isoformat() if row.visit_on else None,
        "visit_status": row.visit_status,
        "signal_code": row.signal_code,
        "signal": row.signal,
        "action_taken": row.action_taken,
    }


@router.get("/vision/recouvrement/dossiers", tags=["vision"], response_model=DossiersOut)
def vision_dossiers(
    user: StaffUser,
    niveau: int | None = Query(None, ge=1, le=4),
    priorite: str | None = Query(None, pattern="^(P1|P2|P3|S)$"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    agence = _agency_scope(user)
    loans = (
        select(
            OutstandingLoan.member_id.label("member_id"),
            func.max(OutstandingLoan.days_late).label("retard"),
            func.coalesce(func.sum(OutstandingLoan.outstanding), 0).label("encours"),
        )
        .where(OutstandingLoan.status != "solde")
        .group_by(OutstandingLoan.member_id)
        .subquery()
    )
    stmt = (
        select(RecoveryCase, Member, loans.c.retard, loans.c.encours)
        .join(Member, Member.id == RecoveryCase.member_id)
        .outerjoin(loans, loans.c.member_id == RecoveryCase.member_id)
        .order_by(RecoveryCase.level.desc(), RecoveryCase.opened_on.desc())
        .limit(limit)
    )
    if agence is not None:
        stmt = stmt.where(Member.agency_id == agence)
    if niveau is not None:
        stmt = stmt.where(RecoveryCase.level == niveau)
    cases = db.execute(stmt).all()
    items = []
    for case, member, retard, encours in cases:
        retard = int(retard or 0)
        encours = float(encours or 0)
        detail = svc.niveau_detail(retard) or svc.niveau_detail((case.level - 1) * 30 + 1) or {}
        item = {
            "case_id": case.id,
            "member_id": member.id,
            "member_code": member.external_code,
            "niveau": case.level,
            "libelle": detail.get("libelle", ""),
            "action": case.action or detail.get("actions", ""),
            "responsable": case.owner_name or detail.get("responsable", ""),
            "priorite": svc.priorite(encours, retard),
            "statut": case.status,
            "outstanding": encours,
            "days_late": retard,
            "opened_on": case.opened_on.isoformat() if case.opened_on else None,
            "next_on": case.next_on.isoformat() if case.next_on else None,
            "recovered_amount": float(case.recovered_amount or 0),
        }
        items.append(item)
    if priorite is not None:
        items = [item for item in items if item["priorite"] == priorite]
    return {"as_of": date.today().isoformat(), "total": len(items), "items": items}


@router.post(
    "/vision/recouvrement/{case_id}/actions",
    tags=["vision"],
    response_model=ActionRecouvrementOut,
)
def log_action_recouvrement(
    case_id: int,
    body: ActionRecouvrementIn,
    user: StaffUser,
    db: Session = Depends(get_db),
):
    case = db.get(RecoveryCase, case_id)
    if not case:
        raise HTTPException(404, "Dossier de recouvrement introuvable")
    if case.status == "clos":
        raise HTTPException(409, "Dossier clos")
    action_on = _date(body.action_on) if body.action_on else date.today()
    member = db.get(Member, case.member_id)
    encours, retard = _member_state(db, case.member_id)
    db.add(
        RecoveryAction(
            case_id=case.id,
            action_on=action_on,
            action_type=body.action_type,
            note=body.note,
            promise_on=_date(body.promise_on) if body.promise_on else None,
            promise_kept=body.promise_kept,
            amount_recovered=body.amount_recovered,
        )
    )
    niveau = svc.niveau_recouvrement(retard)
    if niveau is not None:
        case.level = niveau
    case.priority = svc.priorite(encours, retard)
    case.recovered_amount = float(case.recovered_amount or 0) + float(body.amount_recovered or 0)
    case.last_action_on = action_on
    if body.owner_name:
        case.owner_name = body.owner_name
    elif not case.owner_name and niveau is not None:
        case.owner_name = str(svc.NIVEAUX_RECOUVREMENT[niveau]["responsable"])
    case.next_on = _date(body.next_on) if body.next_on else action_on + timedelta(days=7)
    db.add(
        AuditLog(
            application_id=None,
            user_id=user.id,
            action="action_m7",
            detail=f"case {case.id} {body.action_type} montant={body.amount_recovered} membre={member.external_code if member else case.member_id}",
        )
    )
    db.commit()
    journal = [
        {
            "date": action.action_on.isoformat(),
            "type": action.action_type,
            "note": action.note,
            "montant": float(action.amount_recovered or 0),
        }
        for action in db.scalars(
            select(RecoveryAction).where(RecoveryAction.case_id == case.id).order_by(RecoveryAction.action_on)
        ).all()
    ]
    return {
        "case_id": case.id,
        "level": case.level,
        "priority": case.priority,
        "status": case.status,
        "next_on": case.next_on.isoformat() if case.next_on else None,
        "recovered_amount": float(case.recovered_amount or 0),
        "journal": journal,
    }


@router.post("/vision/par/recalcul", tags=["vision"], response_model=ParRecalculOut)
def recalcul_par(_user: ReviewerUser, as_of: str | None = None, db: Session = Depends(get_db)):
    day = _date(as_of)
    snapshots = svc.recalculer_par(db, day)
    return {
        "as_of": day.isoformat(),
        "snapshots": [{**snap, "as_of": day.isoformat()} for snap in snapshots],
    }


@router.get("/vision/signaux", tags=["vision"], response_model=SignauxOut)
def vision_signaux(_user: StaffUser):
    return {"items": list(svc.SIGNAUX_FUCEC)}
