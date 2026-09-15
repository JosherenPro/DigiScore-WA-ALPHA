"""Reprise d'un dossier renvoye : lecture de la collecte, PATCH, garde-fous.

Couvre le cycle « le chef renvoie -> l'agent corrige -> resoumission », qui
n'avait aucune ecriture cote API avant : `POST /collecte` ne touchait pas aux
termes de la demande et il n'existait pas de PATCH.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.main import app
from app.models.tables import ApplicationGuarantee, AuditLog, CreditApplication

client = TestClient(app)

# Dossiers jetables crees par les tests, retires en fin de session : ces tests
# tournent sur la base de demo partagee, ils ne doivent pas la faire grossir a
# chaque execution.
_CREES: list[int] = []


@pytest.fixture(scope="module", autouse=True)
def _nettoyage():
    yield
    if not _CREES:
        return
    with SessionLocal() as db:
        # audit_log et bic_report n'ont pas d'ON DELETE CASCADE (cf. schema.sql) :
        # le journal doit partir explicitement, le reste suit la cascade.
        db.execute(delete(AuditLog).where(AuditLog.application_id.in_(_CREES)))
        db.execute(delete(CreditApplication).where(CreditApplication.id.in_(_CREES)))
        db.commit()
    _CREES.clear()


CHAMPS_COLLECTE = {
    "ca",
    "cmv",
    "charges_exploitation",
    "produits_financiers",
    "revenu_perso",
    "charge_familiale",
    "charge_credits_en_cours",
    "fonds_propres",
    "total_dettes",
    "actif_total",
    "actif_circulant",
    "passif_circulant",
    "stock_moyen",
    "resultat_net",
    "preuve_revenu",
    "preuve_charge",
    "saisonnier",
    "type_activite",
    "valeur_garanties",
}


def _headers(login: str) -> dict[str, str]:
    token = client.post("/auth/login", json={"login": login, "password": login}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _nouveau_dossier(agent: dict[str, str]) -> int:
    """Cree un dossier jetable plutot que de muter un dossier de demo."""
    membre = client.get("/membres?page=1&page_size=1", headers=agent).json()["items"][0]
    r = client.post(
        "/demandes",
        json={
            "membre_id": membre["id"],
            "objet": "Test correction",
            "montant_demande": 250_000,
            "duree_mois": 12,
            "situation_fiscale": "en_regle",
            "collecte": {"ca": 1_800_000, "cmv": 900_000, "valeur_garanties": 100_000},
        },
        headers=agent,
    )
    assert r.status_code == 200, r.text
    did = int(r.json()["id"])
    _CREES.append(did)
    return did


def test_collecte_complete_rend_tous_les_champs():
    """La reprise a besoin du bilan et de l'activite, pas seulement du compte
    de resultat : sinon le formulaire repart vide et ecrase des donnees valides."""
    agent = _headers("agent")
    did = _nouveau_dossier(agent)
    body = client.get(f"/demandes/{did}/collecte", headers=agent).json()
    assert CHAMPS_COLLECTE <= set(body["complete"])
    assert body["complete"]["ca"] == 1_800_000
    assert body["complete"]["valeur_garanties"] == 100_000


def test_collecte_repetee_ne_duplique_pas_la_garantie():
    """Regression : `_persist_collecte` empilait une ApplicationGuarantee a
    chaque enregistrement. Sur un dossier corrige deux fois, la couverture --
    donc la note Garanties du score -- enflait toute seule."""
    agent = _headers("agent")
    did = _nouveau_dossier(agent)
    for valeur in (120_000, 140_000, 160_000):
        r = client.post(
            f"/demandes/{did}/collecte",
            json={"ca": 1_800_000, "valeur_garanties": valeur},
            headers=agent,
        )
        assert r.status_code == 200, r.text

    with SessionLocal() as db:
        lignes = db.scalars(
            select(ApplicationGuarantee).where(
                ApplicationGuarantee.application_id == did,
                ApplicationGuarantee.kind == "Saisie terrain",
            )
        ).all()
    assert len(lignes) == 1, "la garantie saisie doit etre mise a jour, pas empilee"
    assert float(lignes[0].value_amount) == 160_000


def test_collecte_a_zero_retire_la_garantie():
    """Une valeur remise a zero ne doit pas continuer a compter dans le score."""
    agent = _headers("agent")
    did = _nouveau_dossier(agent)
    client.post(f"/demandes/{did}/collecte", json={"ca": 1_000_000, "valeur_garanties": 0}, headers=agent)
    with SessionLocal() as db:
        restantes = db.scalars(
            select(ApplicationGuarantee).where(
                ApplicationGuarantee.application_id == did,
                ApplicationGuarantee.kind == "Saisie terrain",
            )
        ).all()
    assert restantes == []


def test_patch_corrige_les_termes_de_la_demande():
    agent = _headers("agent")
    did = _nouveau_dossier(agent)
    r = client.patch(
        f"/demandes/{did}",
        json={"objet": "Objet corrige", "montant_demande": 310_000, "duree_mois": 18},
        headers=agent,
    )
    assert r.status_code == 200, r.text
    detail = client.get(f"/demandes/{did}", headers=agent).json()
    assert detail["objet"] == "Objet corrige"
    assert detail["montant_demande"] == 310_000
    assert detail["duree_mois"] == 18
    # La correction est tracee comme le reste du parcours.
    actions = [x["action"] for x in client.get(f"/demandes/{did}/audit", headers=agent).json()]
    assert "modifier" in actions


def test_patch_refuse_sur_dossier_engage():
    """Un dossier parti en decision n'est plus reecrivable : l'agent doit le
    savoir avant de ressaisir, pas au moment d'enregistrer."""
    agent = _headers("agent")
    did = _nouveau_dossier(agent)
    assert client.post(f"/demandes/{did}/analyser", headers=agent).status_code == 200
    assert client.post(f"/demandes/{did}/soumettre", headers=agent).status_code == 200
    r = client.patch(f"/demandes/{did}", json={"objet": "Trop tard"}, headers=agent)
    assert r.status_code == 409
    assert "modifiable" in r.json()["detail"]


def test_cycle_renvoi_correction_resoumission():
    """Le parcours complet : l'ecran bloquait la reprise alors que l'API l'a
    toujours permise (analyser archive le score, soumettre n'exige qu'un score)."""
    agent, chef = _headers("agent"), _headers("direct")
    did = _nouveau_dossier(agent)
    client.post(f"/demandes/{did}/analyser", headers=agent)
    client.post(f"/demandes/{did}/soumettre", headers=agent)
    renvoi = client.post(
        f"/demandes/{did}/decision",
        json={"niveau": "chef_agence", "avis": "renvoyer", "motif": "Stock moyen sous-evalue"},
        headers=chef,
    )
    assert renvoi.status_code == 200, renvoi.text
    assert renvoi.json()["statut"] == "renvoye"

    # Le motif doit etre lisible par l'agent : sans lui, il ignore quoi corriger.
    detail = client.get(f"/demandes/{did}", headers=agent).json()
    motifs = [d["motif"] for d in detail["decisions"] if d["avis"] == "renvoyer"]
    assert motifs == ["Stock moyen sous-evalue"]

    collecte = client.get(f"/demandes/{did}/collecte", headers=agent).json()["complete"]
    collecte["stock_moyen"] = 450_000
    assert client.patch(f"/demandes/{did}", json={"collecte": collecte}, headers=agent).status_code == 200
    assert client.post(f"/demandes/{did}/analyser", headers=agent).status_code == 200
    assert client.post(f"/demandes/{did}/soumettre", headers=agent).json()["statut"] in {
        "soumis_chef",
        "soumis_cic",
    }


def test_patch_reserve_a_l_agent():
    chef = _headers("direct")
    agent = _headers("agent")
    did = _nouveau_dossier(agent)
    assert client.patch(f"/demandes/{did}", json={"objet": "X"}, headers=chef).status_code == 403

