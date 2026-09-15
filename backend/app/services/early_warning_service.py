"""Early warning portefeuille (guide ML, phase 5).

File de revue chef/CIC construite par règles sur `outstanding_loan` et
`portfolio_followup` : ce n'est pas un modèle entraîné et cela ne change
jamais le statut d'un crédit. Le score `p_par30_90j` est indicatif.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import CreditApplication, Member, OutstandingLoan, PortfolioFollowup
from app.services.portfolio_service import nom_complet

MODEL_VERSION = "early-warning-v1"
MAX_SCAN = 5000
MAX_SIGNALS = 4


def _p_par30_90j(days_late: int, signals: list[str], status: str) -> float:
    base = min(0.9, max(0.05, days_late / 90.0))
    bonus = min(0.15, 0.05 * len(signals))
    if status == "impaye":
        bonus += 0.05
    return round(min(1.0, base + bonus), 3)


def _derived_signals(days_late: int, status: str) -> list[str]:
    signals: list[str] = []
    if days_late > 30:
        signals.append("Retard > 30 j")
    elif days_late > 0:
        signals.append("Retard récent")
    if status == "impaye":
        signals.append("Encours impayé")
    return signals


def list_alerts(
    db: Session, *, limit: int = 20, agency_id: int | None = None, agent_id: int | None = None
) -> dict[str, Any]:
    stmt = (
        select(OutstandingLoan, Member)
        .join(Member, Member.id == OutstandingLoan.member_id)
        .where(OutstandingLoan.status != "solde", OutstandingLoan.days_late > 0)
    )
    if agency_id is not None:
        stmt = stmt.where(Member.agency_id == agency_id)
    if agent_id is not None:
        owned = select(CreditApplication.member_id).where(CreditApplication.agent_id == agent_id).distinct()
        stmt = stmt.where(Member.id.in_(owned))
    rows = db.execute(stmt.order_by(OutstandingLoan.days_late.desc()).limit(MAX_SCAN)).all()

    member_ids = [member.id for _, member in rows]
    followups: dict[int, list[str]] = {}
    if member_ids:
        records = db.scalars(
            select(PortfolioFollowup)
            .where(PortfolioFollowup.member_id.in_(member_ids), PortfolioFollowup.signal.isnot(None))
            .order_by(PortfolioFollowup.visit_on.desc())
        ).all()
        for record in records:
            bucket = followups.setdefault(record.member_id, [])
            signal = (record.signal or "").strip()
            if signal and signal not in bucket and len(bucket) < MAX_SIGNALS:
                bucket.append(signal)

    items: list[dict[str, Any]] = []
    for loan, member in rows:
        signals = _derived_signals(int(loan.days_late or 0), loan.status)
        for signal in followups.get(member.id, []):
            if signal not in signals and len(signals) < MAX_SIGNALS:
                signals.append(signal)
        items.append(
            {
                "application_id": loan.application_id,
                "member_code": member.external_code,
                "member_name": nom_complet(member),
                "member_id": member.id,
                "p_par30_90j": _p_par30_90j(int(loan.days_late or 0), signals, loan.status),
                "exposure": float(loan.outstanding or 0.0),
                "days_late": int(loan.days_late or 0),
                "signals": signals,
                "explication": "Risque consultatif : revue recommandée.",
            }
        )

    # A risque egal, l'exposition departage : le score heuristique sature vite
    # (il derive surtout de days_late), et une file ou 20 membres affichent la
    # meme probabilite n'aide pas a choisir qui visiter en premier. Le montant
    # en jeu, lui, varie d'un facteur 10 entre deux dossiers a retard identique.
    items.sort(
        key=lambda item: (item["p_par30_90j"], item["exposure"], item["days_late"]),
        reverse=True,
    )
    return {"model_version": MODEL_VERSION, "items": items[:limit]}
