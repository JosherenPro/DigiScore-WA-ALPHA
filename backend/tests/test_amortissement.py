"""Amortissement M5 : valeurs dures par defaut (nominal 14 %, assurance 5,7 %)."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import amortissement as svc

client = TestClient(app)


def _headers(login: str = "agent") -> dict[str, str]:
    token = client.post("/auth/login", json={"login": login, "password": login}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_valeurs_par_defaut_dans_le_service():
    assert svc.TAUX_NOMINAL_DEFAUT == 0.14
    assert svc.TAUX_ASSURANCE_DEFAUT == 0.057
    tableau = svc.generer(200000, 24)
    assert tableau["mensualite_hors_assurance"] == 9603
    assert tableau["assurance_mensuelle"] == 950
    assert tableau["mensualite_totale"] == 10553
    assert tableau["cout_total"] == 53259.0
    assert sum(ligne["capital"] for ligne in tableau["lignes"]) == 200000.0
    assert tableau["lignes"][-1]["restant"] == 0.0


def test_route_amortissement_applique_les_defauts():
    reponse = client.get(
        "/demandes/1/amortissement?montant=200000&duree_mois=24",
        headers=_headers(),
    )
    assert reponse.status_code == 200
    data = reponse.json()
    assert data["taux_nominal"] == 0.14
    assert data["taux_assurance"] == 0.057
    assert data["mensualite_hors_assurance"] == 9603
    assert data["assurance_mensuelle"] == 950
    assert data["mensualite_totale"] == 10553
    assert data["cout_total"] == 53259.0
