"""Auth 3 rôles + 403 + avis invalide (Postgres local)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _login(login: str, password: str | None = None):
    return client.post("/auth/login", json={"login": login, "password": password or login})


def _token(login: str) -> str:
    r = _login(login)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_health_db():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "digiscore-wa"
    assert "database" in body


def test_capabilities_ml_desactive(monkeypatch):
    """ML coupe : aucune capacite annoncee, meme si les artefacts sont sur le disque.

    L'ancienne version de ce test lisait /capabilities sans fixer ML_ENABLED :
    elle passait ou echouait selon la variable d'environnement du shell qui
    lancait pytest, pas selon le code. On pilote desormais le drapeau.
    """
    monkeypatch.setenv("ML_ENABLED", "0")
    r = client.get("/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert body["ml_scorecard"] is False
    assert body["anomalies"] is False
    assert body["simulation"] is False
    assert body["early_warning"] is False
    assert body["model_version"] is None


def test_capabilities_ml_active(monkeypatch):
    """ML actif : simulation et early warning suivent le drapeau ; scorecard et
    anomalies dependent en plus de la presence d'un artefact entraine."""
    monkeypatch.setenv("ML_ENABLED", "1")
    body = client.get("/capabilities").json()
    assert body["simulation"] is True
    assert body["early_warning"] is True
    assert isinstance(body["ml_scorecard"], bool)
    assert isinstance(body["anomalies"], bool)
    # Toute capacite annoncee doit pouvoir nommer le modele qui la sert :
    # un eclairage consultatif sans version affichable n'est pas auditable.
    if body["ml_scorecard"] or body["anomalies"]:
        assert body["model_version"]


def test_login_ok_and_bad_password():
    ok = _login("agent")
    assert ok.status_code == 200
    assert ok.json()["user"]["role"] == "agent"
    assert ok.json()["access_token"]
    bad = _login("agent", "wrong")
    assert bad.status_code == 401


def test_membres_require_bearer():
    r = client.get("/membres?q=MEM-001")
    assert r.status_code == 401


def test_agent_forbidden_file_cic():
    token = _token("agent")
    r = client.get("/files/cic", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_agent_can_lookup_paginated():
    token = _token("agent")
    r = client.get("/membres?q=MEM-001", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert body["items"][0]["code_externe"] == "MEM-001"


def test_decision_unknown_avis_400():
    token = _token("direct")
    # "nimp" n'existe pas dans l'enum AvisDecision -> 422 de validation Pydantic
    # (avant memes les alias toleres ; la BDD n'est jamais atteinte).
    r = client.post(
        "/demandes/1/decision",
        headers={"Authorization": f"Bearer {token}"},
        json={"niveau": "chef_agence", "avis": "nimp"},
    )
    assert r.status_code == 422
    # L'ancien alias tolere "approuver" reste accepte puis normalise en "accorder".
    r2 = client.post(
        "/demandes/1/decision",
        headers={"Authorization": f"Bearer {token}"},
        json={"niveau": "chef_agence", "avis": "approuver"},
    )
    assert r2.status_code in (200, 400, 404)


def test_decision_alias_normalises_sans_db():
    from app.api.routes import normaliser_decision

    assert normaliser_decision("chef_agence", "approuver") == ("chef_agence", "accorder")
    assert normaliser_decision("chef", "accorder") == ("chef_agence", "accorder")
    assert normaliser_decision("cic", "rejeter") == ("cic", "refuser")
    assert normaliser_decision("cic", " Approuver ") == ("cic", "accorder")


def test_situation_fiscale_invalide_rejetee_avant_bdd():
    """a_jour n'existe pas dans credit_application_tax_status_check.

    Avant le fix, la valeur passait jusqu'a l'INSERT -> IntegrityError -> 500
    genrique "Erreur interne". Desormais l'enum Pydantic rejete en 422.
    """
    token = _token("agent")
    r = client.post(
        "/demandes",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "membre_id": 1,
            "objet": "Test validation",
            "montant_demande": 100000,
            "situation_fiscale": "a_jour",
        },
    )
    assert r.status_code == 422
    valeurs = r.json()["detail"][0]["ctx"]["expected"]
    assert "en_regle" in valeurs and "non_fourni" in valeurs

    # Les valeurs canoniques restent acceptees.
    for ok in ("en_regle", "a_verifier", "non_conforme", "non_fourni"):
        r2 = client.post(
            "/demandes",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "membre_id": 1,
                "objet": "Test validation",
                "montant_demande": 100000,
                "situation_fiscale": ok,
            },
        )
        assert r2.status_code == 200, (ok, r2.text)


def test_piece_invalide_rejetee_avant_bdd():
    token = _token("agent")
    r = client.post(
        "/demandes/1/pieces",
        headers={"Authorization": f"Bearer {token}"},
        json={"type_piece": "PASSPORT", "qualite_ocr": "ok"},
    )
    assert r.status_code == 422


def test_referentiels_agences_institutions_moi():
    token = _token("agent")
    h = {"Authorization": f"Bearer {token}"}
    ag = client.get("/agences", headers=h)
    assert ag.status_code == 200
    body = ag.json()
    assert body[0]["code"] == "AGE-LME-01"
    assert "topologie" in body[0]

    inst = client.get("/institutions", headers=h)
    assert inst.status_code == 200
    kinds = {row["type"] for row in inst.json()}
    assert kinds <= {"coopec", "banque", "microfinance"}
    assert "emoney" not in kinds
    assert any(row["code"] == "IF-BTCI" for row in inst.json())

    ref = client.get("/referentiels", headers=h)
    assert ref.status_code == 200
    assert "actif" in ref.json()["statuts_membre"]
    assert "ok" in ref.json()["qualite_ocr"]

    moi = client.get("/moi", headers=h)
    assert moi.status_code == 200
    assert moi.json()["login"] == "agent"
    assert moi.json()["role"] == "agent"


def test_fiche_historique_mouvements_mem001():
    token = _token("agent")
    h = {"Authorization": f"Bearer {token}"}
    fiche = client.get("/membres/1", headers=h)
    assert fiche.status_code == 200
    fbody = fiche.json()
    assert fbody["code_externe"] == "MEM-001"
    assert fbody["agence"]["code"] == "AGE-LME-01"
    assert fbody["nb_mouvements"] >= 6
    assert "nb_comptes_externes" in fbody

    hist = client.get("/membres/1/historique", headers=h)
    assert hist.status_code == 200
    hbody = hist.json()
    assert hbody != fbody
    assert len(hbody["mouvements"]) >= 1
    assert hbody["total_mouvements"] == fbody["nb_mouvements"]
    assert "libelle" in hbody["mouvements"][0]

    mv = client.get("/membres/1/mouvements?page=1&page_size=30", headers=h)
    assert mv.status_code == 200
    page = mv.json()
    assert "items" in page
    assert page["total"] == fbody["nb_mouvements"]
    assert page["items"]


def test_mem012_comptes_externes_pas_melange():
    token = _token("agent")
    h = {"Authorization": f"Bearer {token}"}
    ext = client.get("/membres/12/comptes-externes", headers=h)
    assert ext.status_code == 200
    rows = ext.json()
    assert rows
    assert rows[0]["institution"]["code"] == "IF-BTCI"
    assert rows[0]["institution"]["type"] == "banque"

    em = client.get("/membres/12/mouvements-externes?page=1", headers=h)
    assert em.status_code == 200
    assert em.json()["total"] >= 1
    assert em.json()["items"]

    loc = client.get("/membres/12/mouvements", headers=h)
    assert loc.status_code == 200
    local_labels = " ".join(x.get("libelle") or "" for x in loc.json()["items"])
    ext_labels = " ".join(x.get("libelle") or "" for x in em.json()["items"])
    assert "BTCI" not in local_labels
    assert "BTCI" in ext_labels


def test_demande_enrichie_collecte_et_scores():
    token = _token("agent")
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/demandes/1", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["membre"]["code_externe"] == "MEM-001"
    assert body["collecte"] is not None
    assert body["collecte"]["ca"] > 0
    assert len(body["tresorerie"]) == 12
    hist = client.get("/demandes/1/scores", headers=h)
    assert hist.status_code == 200
    assert isinstance(hist.json(), list)

