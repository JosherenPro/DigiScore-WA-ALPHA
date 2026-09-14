"""Suivi portefeuille M6 — formules FUCEC/CGAP et règles de gestion.

Aucune décision de crédit ici : ce module calcule les indicateurs du
portefeuille (retard, aging, PAR 1/30/90, priorité, niveau de recouvrement,
visites) à partir des tables `outstanding_loan`, `loan_payment`,
`portfolio_followup` et `recovery_case`.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any, Iterable

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.tables import (
    CreditApplication,
    LoanPayment,
    Member,
    OutstandingLoan,
    ParIndicator,
    PortfolioFollowup,
)

PRIORITE_P1_ENCOURS = 2_000_000
PRIORITE_P1_RETARD = 8
PRIORITES = ("P1", "P2", "P3", "S")
BUCKETS = ("courant", "1-7", "8-30", "31-90", ">90")

NIVEAUX_RECOUVREMENT: dict[int, dict[str, Any]] = {
    1: {
        "libelle": "Relance immédiate",
        "periode": "J+1 à J+7",
        "responsable": "Chargé de crédit",
        "actions": "Appel J+1, visite J+3, documentation SIG",
        "delai_jours": 7,
    },
    2: {
        "libelle": "Relance renforcée",
        "periode": "J+8 à J+30",
        "responsable": "Chargé de crédit + Superviseur",
        "actions": "Visite domicile, caution contactée, mise en demeure",
        "delai_jours": 30,
    },
    3: {
        "libelle": "Recouvrement intensif",
        "periode": "J+31 à J+90",
        "responsable": "Superviseur + Chef d'agence",
        "actions": "Convocation formelle, échéancier écrit, garanties activées",
        "delai_jours": 90,
    },
    4: {
        "libelle": "Contentieux",
        "periode": "> J+90",
        "responsable": "Direction / Juridique",
        "actions": "Huissier, réalisation des garanties, action judiciaire",
        "delai_jours": None,
    },
}

SIGNAUX_FUCEC: tuple[dict[str, str], ...] = (
    {"code": "ACT_BAISSE_STOCK", "famille": "activite", "libelle": "Baisse visible des stocks ou de l'achalandage"},
    {"code": "ACT_CHANGEMENT", "famille": "activite", "libelle": "Changement d'activité non déclaré"},
    {"code": "ACT_FERMETURE", "famille": "activite", "libelle": "Fermeture temporaire ou définitive du point de vente"},
    {"code": "ACT_PERTE_CLIENT", "famille": "activite", "libelle": "Perte d'un client ou fournisseur majeur"},
    {"code": "COM_EVITEMENT", "famille": "comportement", "libelle": "Évitement : ne répond plus, absent aux visites"},
    {"code": "COM_PROMESSE_NON_TENUE", "famille": "comportement", "libelle": "Promesses de paiement répétées et non tenues"},
    {"code": "COM_AGRESSIVITE", "famille": "comportement", "libelle": "Agressivité ou victimisation excessive"},
    {"code": "COM_REECHELONNEMENT", "famille": "comportement", "libelle": "Demande de rééchelonnement précoce"},
    {"code": "ENV_SINISTRE", "famille": "environnement", "libelle": "Sinistre (incendie, inondation, vol) touchant l'activité"},
    {"code": "ENV_CRISE_SECTEUR", "famille": "environnement", "libelle": "Crise sectorielle : chute des prix, marché fermé"},
    {"code": "ENV_SANTE", "famille": "environnement", "libelle": "Problème de santé grave du sociétaire ou d'un membre clé"},
    {"code": "ENV_SURENDETTEMENT", "famille": "environnement", "libelle": "Surendettement détecté : crédits multiples"},
)

TAUX_RECUPERATION_FUCEC = (
    {"anciennete_max": 7, "taux": 0.95, "libelle": "J+1 à J+7"},
    {"anciennete_max": 30, "taux": 0.75, "libelle": "J+8 à J+30"},
    {"anciennete_max": 90, "taux": 0.45, "libelle": "J+31 à J+90"},
    {"anciennete_max": None, "taux": 0.20, "libelle": "> J+90"},
)


def _pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(100.0 * numerator / denominator, 2)


def _add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def bucket_aging(retard: int) -> str:
    if retard <= 0:
        return "courant"
    if retard <= 7:
        return "1-7"
    if retard <= 30:
        return "8-30"
    if retard <= 90:
        return "31-90"
    return ">90"


def niveau_recouvrement(retard: int) -> int | None:
    if retard <= 0:
        return None
    if retard <= 7:
        return 1
    if retard <= 30:
        return 2
    if retard <= 90:
        return 3
    return 4


def niveau_detail(retard: int) -> dict[str, Any] | None:
    niveau = niveau_recouvrement(retard)
    if niveau is None:
        return None
    return {"niveau": niveau, **NIVEAUX_RECOUVREMENT[niveau]}


def priorite(encours: float, retard: int) -> str:
    if retard <= 0:
        return "S"
    if encours > PRIORITE_P1_ENCOURS and retard > PRIORITE_P1_RETARD:
        return "P1"
    if retard > 30 or (encours > 1_000_000 and retard > PRIORITE_P1_RETARD):
        return "P2"
    return "P3"


def taux_recuperation_theorique(retard: int) -> float:
    for tranche in TAUX_RECUPERATION_FUCEC:
        if tranche["anciennete_max"] is None or retard <= tranche["anciennete_max"]:
            return float(tranche["taux"])
    return 0.20


def jours_retard(
    loan: OutstandingLoan,
    as_of: date,
    *,
    schedule: Iterable[Any] | None = None,
    payments: Iterable[Any] | None = None,
) -> int:
    """Retard (jours) : plus ancienne échéance non couverte, sinon snapshot daté."""
    if loan.status == "solde":
        return 0

    lines = [line for line in (schedule or []) if getattr(line, "due_on", None)]
    if lines:
        paid = sum(float(p.amount or 0) for p in (payments or []) if p.paid_on and p.paid_on <= as_of)
        for line in sorted(lines, key=lambda item: item.due_on):
            if line.due_on > as_of:
                break
            paid -= float(line.installment_amount or 0)
            if paid < 0:
                return (as_of - line.due_on).days
        return 0

    snapshot = int(loan.days_late or 0)
    observed = loan.observed_on
    if observed and as_of > observed:
        return max(0, snapshot + (as_of - observed).days)
    return snapshot


def prochaine_visite(
    loan: OutstandingLoan,
    as_of: date,
    *,
    term_months: int = 12,
    visites_faites: Iterable[str] = (),
) -> dict[str, Any] | None:
    if not loan.disbursed_on or loan.status == "solde":
        return None
    done = {code for code in visites_faites}
    term = max(1, int(term_months or 12))
    cibles: list[tuple[str, date]] = [
        ("V1", loan.disbursed_on + timedelta(days=7)),
        ("V2", _add_months(loan.disbursed_on, max(1, term // 2))),
        ("V3", _add_months(loan.disbursed_on, term) - timedelta(days=30)),
    ]
    for code, cible in cibles:
        if code in done:
            continue
        retard = (as_of - cible).days
        statut = "en_retard" if retard > 15 else ("a_faire" if retard >= 0 else "planifiee")
        return {"visite": code, "cible": cible, "jours_de_retard": max(0, retard), "statut": statut}
    return None


def _loan_scope(db: Session, agency_id: int | None):
    stmt = select(OutstandingLoan).join(Member, Member.id == OutstandingLoan.member_id)
    if agency_id is not None:
        stmt = stmt.where(Member.agency_id == agency_id)
    return stmt


def par_snapshot(db: Session, as_of: date, agency_id: int | None = None) -> dict[str, Any]:
    stmt = (
        select(
            func.coalesce(func.sum(OutstandingLoan.outstanding), 0),
            func.coalesce(
                func.sum(case((OutstandingLoan.restructured.is_(True), OutstandingLoan.outstanding), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((OutstandingLoan.days_late >= 1, OutstandingLoan.outstanding), else_=0)), 0
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            or_(
                                OutstandingLoan.days_late > 30,
                                OutstandingLoan.restructured.is_(True),
                            ),
                            OutstandingLoan.outstanding,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            or_(
                                OutstandingLoan.days_late > 90,
                                OutstandingLoan.restructured.is_(True),
                            ),
                            OutstandingLoan.outstanding,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .join(Member, Member.id == OutstandingLoan.member_id)
        .where(OutstandingLoan.status != "solde")
    )
    if agency_id is not None:
        stmt = stmt.where(Member.agency_id == agency_id)
    brut, restructured, late1, late30, late90 = db.execute(stmt).one()
    brut, restructured, late1, late30, late90 = (
        float(brut),
        float(restructured),
        float(late1),
        float(late30),
        float(late90),
    )
    return {
        "agency_id": agency_id,
        "as_of": as_of,
        "encours_brut": brut,
        "restructured_amount": restructured,
        "par1": _pct(late1, brut),
        "par30": _pct(late30, brut),
        "par90": _pct(late90, brut),
    }


def par_label(par30: float) -> str:
    if par30 < 5:
        return "acceptable"
    if par30 <= 10:
        return "alerte"
    return "critique"


def recalculer_par(db: Session, as_of: date) -> list[dict[str, Any]]:
    agencies = [
        row
        for row in db.scalars(
            select(Member.agency_id).where(Member.agency_id.isnot(None)).distinct().order_by(Member.agency_id)
        ).all()
    ]
    snapshots = [par_snapshot(db, as_of, agency) for agency in agencies]
    snapshots.append(par_snapshot(db, as_of, None))
    for snap in snapshots:
        existing = db.scalars(
            select(ParIndicator).where(
                ParIndicator.as_of == as_of,
                ParIndicator.agency_id.is_(None) if snap["agency_id"] is None else ParIndicator.agency_id == snap["agency_id"],
            )
        ).first()
        if existing:
            existing.par1_pct = snap["par1"]
            existing.par30_pct = snap["par30"]
            existing.par90_pct = snap["par90"]
            existing.encours_brut = snap["encours_brut"]
            existing.restructured_amount = snap["restructured_amount"]
        else:
            db.add(
                ParIndicator(
                    agency_id=snap["agency_id"],
                    as_of=as_of,
                    par1_pct=snap["par1"],
                    par30_pct=snap["par30"],
                    par90_pct=snap["par90"],
                    encours_brut=snap["encours_brut"],
                    restructured_amount=snap["restructured_amount"],
                )
            )
    db.commit()
    return snapshots


def aging_report(db: Session, as_of: date, agency_id: int | None = None) -> list[dict[str, Any]]:
    rows = db.execute(
        _loan_scope(db, agency_id).with_only_columns(
            OutstandingLoan.outstanding, OutstandingLoan.days_late
        )
    ).all()
    buckets = {name: {"bucket": name, "montant": 0.0, "dossiers": 0} for name in BUCKETS}
    total = 0.0
    for outstanding, days_late in rows:
        montant = float(outstanding or 0)
        bucket = buckets[bucket_aging(int(days_late or 0))]
        bucket["montant"] += montant
        bucket["dossiers"] += 1
        total += montant
    for bucket in buckets.values():
        bucket["montant"] = round(bucket["montant"], 2)
        bucket["part_pct"] = _pct(bucket["montant"], total)
    return list(buckets.values())


def indicateurs_recuperation(db: Session) -> dict[str, Any]:
    paid = float(db.scalar(select(func.coalesce(func.sum(LoanPayment.amount), 0))) or 0)
    principal, outstanding = db.execute(
        select(
            func.coalesce(func.sum(OutstandingLoan.principal), 0),
            func.coalesce(func.sum(OutstandingLoan.outstanding), 0),
        )
    ).one()
    principal, outstanding = float(principal), float(outstanding)
    derived = max(0.0, principal - outstanding)
    montant = paid if paid > 0 else derived
    return {
        "montant_recupere": round(montant, 2),
        "source": "paiements" if paid > 0 else "derive_encours",
        "taux_recuperation": None if principal <= 0 else round(100.0 * montant / principal, 2),
        "encours_brut": round(outstanding, 2),
    }


def echeances_du_jour(db: Session, jour: date, agency_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
    stmt = (
        select(OutstandingLoan, Member)
        .join(Member, Member.id == OutstandingLoan.member_id)
        .where(OutstandingLoan.status != "solde", OutstandingLoan.days_late > 0)
        .order_by(OutstandingLoan.days_late.desc(), OutstandingLoan.outstanding.desc())
        .limit(limit)
    )
    if agency_id is not None:
        stmt = stmt.where(Member.agency_id == agency_id)
    items: list[dict[str, Any]] = []
    for loan, member in db.execute(stmt).all():
        retard = int(loan.days_late or 0)
        detail = niveau_detail(retard) or {}
        items.append(
            {
                "outstanding_loan_id": loan.id,
                "member_id": member.id,
                "member_code": member.external_code,
                "outstanding": float(loan.outstanding or 0),
                "days_late": retard,
                "due_on": loan.due_on,
                "bucket": bucket_aging(retard),
                "priorite": priorite(float(loan.outstanding or 0), retard),
                "niveau": detail.get("niveau"),
                "action": detail.get("actions"),
                "responsable": detail.get("responsable"),
                "jour": jour,
            }
        )
    return items


def visites_a_faire(
    db: Session,
    as_of: date,
    agency_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(OutstandingLoan, Member)
        .join(Member, Member.id == OutstandingLoan.member_id)
        .where(OutstandingLoan.status != "solde")
    ).all()
    if agency_id is not None:
        rows = [(loan, member) for loan, member in rows if member.agency_id == agency_id]
    member_ids = [member.id for _, member in rows]
    suivis: dict[int, list[str]] = {}
    if member_ids:
        for record in db.scalars(
            select(PortfolioFollowup).where(PortfolioFollowup.member_id.in_(member_ids))
        ).all():
            suivis.setdefault(record.member_id, []).append(record.visit_code)
    terms = {
        app.id: app.term_months
        for app in db.scalars(
            select(CreditApplication).where(
                CreditApplication.id.in_([loan.application_id for loan, _ in rows if loan.application_id])
            )
        ).all()
    }
    items: list[dict[str, Any]] = []
    for loan, member in rows:
        detail = prochaine_visite(
            loan,
            as_of,
            term_months=terms.get(loan.application_id or 0, 12),
            visites_faites=suivis.get(member.id, []),
        )
        if not detail or detail["statut"] == "planifiee":
            continue
        items.append(
            {
                "outstanding_loan_id": loan.id,
                "member_id": member.id,
                "member_code": member.external_code,
                **detail,
            }
        )
    items.sort(key=lambda item: item["jours_de_retard"], reverse=True)
    return items[:limit]
