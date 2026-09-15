"""Routes ML consultatives : capabilities, anomalies, simulation, early warning."""

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db import SessionLocal
from app.main import app
from app.models.tables import ResilienceSimulation

client = TestClient(app)


def _token(login: str = "agent") -> str:
    r = client.post("/auth/login", json={"login": login, "password": "demo"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _headers(login: str = "agent") -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(login)}"}


def _enable_ml(monkeypatch):
    monkeypatch.setenv("ML_ENABLED", "1")


def test_ml_routes_503_quand_desactive(monkeypatch):
    monkeypatch.delenv("ML_ENABLED", raising=False)
    assert client.get("/demandes/1/anomalies", headers=_headers()).status_code == 503
    sim = client.post("/demandes/1/simuler", headers=_headers(), json={"scenario": "normal"})
    assert sim.status_code == 503
    assert client.get("/portefeuille/alertes", headers=_headers("chef")).status_code == 503
    assert client.get("/demandes/1/ml/scorecard", headers=_headers()).status_code == 503
    assert client.get("/demandes/1/ml/plafond", headers=_headers()).status_code == 503


def test_capabilities_quand_ml_active(monkeypatch):
    _enable_ml(monkeypatch)
    body = client.get("/capabilities").json()
    assert body["anomalies"] is True
    assert body["simulation"] is True
    assert body["early_warning"] is True
    assert body["ml_scorecard"] is True
    assert body["model_version"] == "scorecard-v3"


def test_anomalies_exigent_bearer():
    assert client.get("/demandes/1/anomalies").status_code == 401


def test_anomalies_agent(monkeypatch):
    _enable_ml(monkeypatch)
    r = client.get("/demandes/1/anomalies", headers=_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_version"] == "anomaly-v3"
    assert isinstance(body["scope_excluded"], bool)
    assert isinstance(body["anomalies"], list)
    for item in body["anomalies"]:
        assert item["feature"]
        assert item["z_score"] is not None
        assert item["severity"] == "a_verifier"
        assert item["message"]


def test_anomalies_service_thin_file_hors_scope():
    from app.services.anomaly_service import detect_anomalies

    dossier = {
        "membre": {"id": 999, "anciennete_mois": 1, "statut": "actif"},
        "compte": {"solde": 0, "date_ouverture_jours": 5, "statut": "actif"},
        "historique": {
            "credits_passes": [],
            "incidents": [],
            "epargne_moy_3m": 0,
            "epargne_moy_6m": 0,
            "nb_mouvements_90j": 0,
        },
        "demande": {"montant": 100000, "duree_mois": 12},
        "analyse": {},
    }
    body = detect_anomalies(dossier)
    assert body["scope_excluded"] is True
    assert body["anomalies"] == []


def _payload(scenario: str = "mauvaise_recolte", iterations: int = 200, seed: int = 42):
    return {"scenario": scenario, "iterations": iterations, "seed": seed}


def test_simulation_reproductible(monkeypatch):
    _enable_ml(monkeypatch)
    first = client.post("/demandes/1/simuler", headers=_headers(), json=_payload())
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["scenario"] == "mauvaise_recolte"
    assert body["model_version"] == "resilience-v2"
    assert body["seed"] == 42
    assert len(body["p10"]) == len(body["p50"]) == len(body["p90"]) > 0
    assert 0.0 <= body["p_incident"] <= 1.0

    second = client.post("/demandes/1/simuler", headers=_headers(), json=_payload())
    assert second.status_code == 200
    assert second.json() == body


def test_simulation_libelle_adapte_activite(monkeypatch):
    _enable_ml(monkeypatch)
    commerce = client.post("/demandes/1/simuler", headers=_headers(), json=_payload())
    assert commerce.status_code == 200, commerce.text
    assert commerce.json()["scenario"] == "mauvaise_recolte"
    assert commerce.json()["scenario_libelle"] == "Mévente prolongée"

    agri = client.post("/demandes/6/simuler", headers=_headers(), json=_payload())
    assert agri.status_code == 200, agri.text
    assert agri.json()["scenario_libelle"] == "Mauvaise récolte"


def test_simulation_expose_mecanique_et_description(monkeypatch):
    _enable_ml(monkeypatch)
    r = client.post("/demandes/1/simuler", headers=_headers(), json=_payload())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mecanique"] == {"revenus": 0.6, "charges": 1.1}
    assert "40 %" in body["description"] and "+10 %" in body["description"]

    custom = client.post(
        "/demandes/1/simuler",
        headers=_headers(),
        json={"scenario": {"type": "choc", "intensite": -0.2}, "iterations": 50, "seed": 42},
    )
    assert custom.status_code == 200, custom.text
    assert custom.json()["mecanique"] == {"revenus": 0.8, "charges": 1.05}
    assert custom.json()["description"] != ""


def test_simulation_scenario_inconnu_422(monkeypatch):
    _enable_ml(monkeypatch)
    r = client.post("/demandes/1/simuler", headers=_headers(), json=_payload("nimportequoi"))
    assert r.status_code == 422


def test_simulation_snapshot_relisible(monkeypatch):
    _enable_ml(monkeypatch)
    created = client.post(
        "/demandes/1/simulation/enregistrer",
        headers=_headers(),
        json=_payload("maladie", iterations=100),
    )
    assert created.status_code == 201, created.text
    saved = created.json()
    assert saved["id"] > 0
    assert saved["scenario"] == "maladie"
    assert saved["seed"] == 42

    listed = client.get("/demandes/1/simulations", headers=_headers())
    assert listed.status_code == 200
    assert any(item["id"] == saved["id"] for item in listed.json())

    direct = client.post("/demandes/1/simuler", headers=_headers(), json=_payload("maladie", iterations=100))
    assert direct.status_code == 200
    assert direct.json()["p50"] == saved["p50"]

    with SessionLocal() as db:
        db.execute(delete(ResilienceSimulation).where(ResilienceSimulation.id == saved["id"]))
        db.commit()


def test_alertes_chef_ok_agent_scoped(monkeypatch):
    _enable_ml(monkeypatch)
    r = client.get("/portefeuille/alertes?limit=5", headers=_headers("chef"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_version"] == "early-warning-v1"
    assert len(body["items"]) <= 5
    for item in body["items"]:
        assert item["member_code"]
        assert 0.0 <= item["p_par30_90j"] <= 1.0
        assert item["exposure"] >= 0
        assert item["explication"]

    # L'agent voit aussi ses alertes (Portefeuille lui est ouvert), mais
    # restreintes a ses propres clients (credit_application.agent_id) — plus
    # un 403 : c'est le meme module, juste un perimetre plus etroit.
    agent_r = client.get("/portefeuille/alertes", headers=_headers("agent"))
    assert agent_r.status_code == 200, agent_r.text


def test_scorecard_shadow(monkeypatch):
    _enable_ml(monkeypatch)
    r = client.get("/demandes/1/ml/scorecard", headers=_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "shadow"
    assert body["model_version"] == "scorecard-v3"
    assert body["warning"]
    if body["probabilite_defaut"] is not None:
        assert 0.0 <= body["probabilite_defaut"] <= 1.0
        assert body["niveau_risque"] in {"faible", "modere", "eleve", "tres_eleve"}
        assert isinstance(body["contributions"], list)
    # Compatibilite front : le score /100 historique est expose aux cotes des bandes.
    if body["probabilite_defaut"] is not None and not body["regles_knockout"]:
        assert body["score_global_ml"] == round(100.0 * (1.0 - body["probabilite_defaut"]), 1)


def test_niveau_risque_bandes():
    from app.services.advisory_service import _niveau_risque

    assert _niveau_risque(0.05) == "faible"
    assert _niveau_risque(0.15) == "modere"
    assert _niveau_risque(0.30) == "eleve"
    assert _niveau_risque(0.80) == "tres_eleve"
    assert _niveau_risque(None) is None


def test_scorecard_shadow_knockout_non_applicable(monkeypatch):
    _enable_ml(monkeypatch)
    r = client.get("/demandes/4/ml/scorecard", headers=_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["regles_knockout"] is True
    assert body["niveau_risque"] is None
    assert "knockout" in (body["warning"] or "").lower()


def test_plafond_ml_shadow(monkeypatch):
    _enable_ml(monkeypatch)
    r = client.get("/demandes/1/ml/plafond", headers=_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["enabled"], bool)
    if body["enabled"] and not body["blocked_by_knockout"]:
        assert body["plafond_ml_recommande"] <= body["plafond_regles"]
        assert body["facteur_prudence"] in {1.0, 0.9, 0.75, 0.6}
        assert body["explication"]
        assert body["detail"]["facteur_prudence"] == body["facteur_prudence"]
        assert body["detail"]["avant_arrondi"] - body["detail"]["perte_arrondi_fcfa"] == body["plafond_ml_recommande"]
        assert len(body["raisons"]) >= 4


def test_simulation_alias_scenarios(monkeypatch):
    _enable_ml(monkeypatch)
    for alias in ("prudent", "central", "optimiste", "intrants_+20"):
        r = client.post("/demandes/1/simuler", headers=_headers(), json=_payload(alias, iterations=50))
        assert r.status_code == 200, f"{alias}: {r.text}"
        assert r.json()["scenario"] == alias
