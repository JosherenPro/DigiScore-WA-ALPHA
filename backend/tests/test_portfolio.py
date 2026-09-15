"""Suivi portefeuille M6 / recouvrement M7 : formules + routes vision."""

from datetime import date
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.main import app
from app.models.tables import AuditLog, PortfolioFollowup, RecoveryAction, RecoveryCase
from app.services import portfolio_service as svc

client = TestClient(app)


def _headers(login: str = "chef") -> dict[str, str]:
    token = client.post("/auth/login", json={"login": login, "password": "demo"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_formules_par_et_priorisation():
    assert svc.bucket_aging(0) == "courant"
    assert svc.bucket_aging(3) == "1-7"
    assert svc.bucket_aging(30) == "8-30"
    assert svc.bucket_aging(91) == ">90"
    assert svc.niveau_recouvrement(0) is None
    assert svc.niveau_recouvrement(3) == 1
    assert svc.niveau_recouvrement(15) == 2
    assert svc.niveau_recouvrement(45) == 3
    assert svc.niveau_recouvrement(120) == 4
    assert svc.priorite(3_000_000, 12) == "P1"
    assert svc.priorite(500_000, 12) == "P3"
    assert svc.priorite(500_000, 45) == "P2"
    assert svc.priorite(100_000, 0) == "S"
    assert svc.taux_recuperation_theorique(5) == 0.95
    assert svc.taux_recuperation_theorique(120) == 0.20
    assert len(svc.SIGNAUX_FUCEC) == 12


def test_jours_retard_fifo():
    loan = SimpleNamespace(status="en_cours", days_late=0, observed_on=None)
    schedule = [
        SimpleNamespace(due_on=date(2026, 6, 1), installment_amount=100_000),
        SimpleNamespace(due_on=date(2026, 7, 1), installment_amount=100_000),
    ]
    payments = [SimpleNamespace(paid_on=date(2026, 6, 5), amount=100_000)]
    assert svc.jours_retard(loan, date(2026, 7, 20), schedule=schedule, payments=payments) == 19

    loan_snapshot = SimpleNamespace(status="impaye", days_late=30, observed_on=date(2026, 9, 1))
    assert svc.jours_retard(loan_snapshot, date(2026, 9, 11)) == 40

    loan_solde = SimpleNamespace(status="solde", days_late=30, observed_on=None)
    assert svc.jours_retard(loan_solde, date(2026, 9, 11)) == 0


def test_vision_portefeuille_chef_et_agent():
    for login in ("chef", "agent"):
        r = client.get("/vision/portefeuille", headers=_headers(login))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["module"]
        assert body["par"] and all({"agence_id", "par30", "par90"} <= set(item) for item in body["par"])
        assert body["alertes"]
        assert {"signal", "membre_id"} <= set(body["alertes"][0])


def test_vision_aging_echeances_visites():
    h = _headers("chef")
    aging = client.get("/vision/aging", headers=h)
    assert aging.status_code == 200
    buckets = aging.json()["buckets"]
    assert [b["bucket"] for b in buckets] == list(svc.BUCKETS)

    ech = client.get("/vision/echeances?page_size=3", headers=h)
    assert ech.status_code == 200
    assert len(ech.json()["items"]) <= 3

    vis = client.get("/vision/visites?limit=5", headers=h)
    assert vis.status_code == 200
    assert len(vis.json()["items"]) <= 5


def test_vision_recouvrement_et_signaux():
    h = _headers("chef")
    m7 = client.get("/vision/recouvrement?limit=5", headers=h)
    assert m7.status_code == 200
    dossiers = m7.json()["dossiers"]
    assert dossiers and {"membre_id", "niveau", "action", "responsable"} <= set(dossiers[0])

    rich = client.get("/vision/recouvrement/dossiers?page_size=5", headers=h)
    assert rich.status_code == 200
    assert rich.json()["total"] > 0
    assert len(rich.json()["items"]) <= 5

    signaux = client.get("/vision/signaux", headers=h)
    assert signaux.status_code == 200
    assert len(signaux.json()["items"]) == 12


def test_log_visite_et_cleanup():
    h = _headers("agent")
    with SessionLocal() as db:
        max_visit = db.scalar(select(func.max(PortfolioFollowup.id))) or 0
        max_audit = db.scalar(select(func.max(AuditLog.id))) or 0
    r = client.post(
        "/vision/visites",
        headers=h,
        json={"member_id": 3, "visit_code": "V2", "signal_code": "COM_EVITEMENT", "action_taken": "test"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["visit_code"] == "V2"
    assert body["signal_code"] == "COM_EVITEMENT"
    with SessionLocal() as db:
        db.execute(delete(PortfolioFollowup).where(PortfolioFollowup.id > max_visit))
        db.execute(delete(AuditLog).where(AuditLog.id > max_audit))
        db.commit()


def test_action_recouvrement_et_cleanup():
    h = _headers("chef")
    dossiers = client.get("/vision/recouvrement/dossiers?page_size=1", headers=h).json()["items"]
    case_id = dossiers[0]["case_id"]
    with SessionLocal() as db:
        case = db.get(RecoveryCase, case_id)
        before = {
            field: getattr(case, field)
            for field in ("level", "priority", "recovered_amount", "last_action_on", "next_on", "owner_name")
        }
        max_action = db.scalar(select(func.max(RecoveryAction.id)).where(RecoveryAction.case_id == case_id)) or 0
        max_audit = db.scalar(select(func.max(AuditLog.id))) or 0

    r = client.post(
        f"/vision/recouvrement/{case_id}/actions",
        headers=h,
        json={"action_type": "appel", "note": "test", "amount_recovered": 1000, "next_on": "2026-09-30"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_id"] == case_id
    assert body["recovered_amount"] >= 1000
    assert body["journal"]

    with SessionLocal() as db:
        db.execute(delete(RecoveryAction).where(RecoveryAction.case_id == case_id, RecoveryAction.id > max_action))
        db.execute(delete(AuditLog).where(AuditLog.id > max_audit))
        case = db.get(RecoveryCase, case_id)
        for field, value in before.items():
            setattr(case, field, value)
        db.commit()


def test_recalcul_par_snapshot():
    h = _headers("chef")
    r = client.post("/vision/par/recalcul", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["snapshots"]
    assert {"agency_id", "par1", "par30", "par90", "encours_brut"} <= set(body["snapshots"][0])
