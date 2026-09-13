from digiscore.pipeline import run


def _base(**over):
    d = {
        "membre": {"id": 1, "anciennete_mois": 48, "statut": "actif"},
        "compte": {"solde": 400000, "date_ouverture_jours": 800, "statut": "actif"},
        "historique": {
            "credits_passes": [{"montant": 400000, "statut": "solde", "nb_retards": 0}],
            "incidents": [],
            "epargne_moy_3m": 400000,
            "epargne_moy_6m": 380000,
            "nb_mouvements_90j": 6,
        },
        "demande": {
            "montant": 500000,
            "duree_mois": 12,
            "plafond_produit": 3000000,
            "situation_fiscale": "en_regle",
        },
        "analyse": {
            "ca": 3600000,
            "cmv": 1800000,
            "charges_exploitation": 600000,
            "produits_financiers": 20000,
            "revenu_perso": 200000,
            "charge_familiale": 80000,
            "fonds_propres": 800000,
            "total_dettes": 200000,
            "actif_total": 1500000,
            "actif_circulant": 700000,
            "passif_circulant": 250000,
            "stock_moyen": 300000,
            "resultat_net": 400000,
            "valeur_garanties": 350000,
            "preuve_revenu": "N3",
            "preuve_charge": "N2",
        },
    }
    for k, v in over.items():
        if isinstance(v, dict) and k in d:
            d[k].update(v)
        else:
            d[k] = v
    return d


def test_bon_payeur_montant_ok():
    r = run(_base())
    assert r.message_code in ("MONTANT_OK", "UPSELL_POSSIBLE")
    assert r.score_global >= 55
    assert not r.thin_file


def test_thin_file():
    r = run(
        _base(
            membre={"id": 4, "anciennete_mois": 2, "statut": "actif"},
            historique={
                "credits_passes": [],
                "incidents": [],
                "epargne_moy_3m": 30000,
                "epargne_moy_6m": 20000,
                "nb_mouvements_90j": 1,
            },
            demande={"montant": 400000, "duree_mois": 8, "situation_fiscale": "en_regle"},
        )
    )
    assert r.thin_file
    assert r.message_code in ("HISTORIQUE_INSUFFISANT", "MONTANT_PLAFONNE")


def test_compte_gele():
    r = run(_base(membre={"id": 10, "anciennete_mois": 70, "statut": "gele"}))
    assert r.message_code == "COMPTE_INACTIF"


def test_rcsd_knockout():
    r = run(
        _base(
            analyse={
                "ca": 800000,
                "cmv": 550000,
                "charges_exploitation": 300000,
                "revenu_perso": 50000,
                "charge_familiale": 40000,
                "charge_credits_en_cours": 40000,
                "fonds_propres": 60000,
                "total_dettes": 350000,
                "actif_total": 250000,
                "actif_circulant": 90000,
                "passif_circulant": 160000,
                "resultat_net": -20000,
            },
            demande={"montant": 800000, "duree_mois": 12, "situation_fiscale": "en_regle"},
        )
    )
    assert any(k.code == "KNOCKOUT_RCSD" for k in r.knockouts)


def test_voie_exceptionnelle():
    r = run(
        _base(
            demande={
                "montant": 10000000,
                "duree_mois": 24,
                "plafond_produit": 12000000,
                "exceptionnel": True,
                "seuil_caution": 2000000,
                "nb_cautions_eligibles": 2,
                "nb_cautions_min": 2,
                "situation_fiscale": "en_regle",
            },
            analyse={"valeur_garanties": 8000000, "ca": 18000000, "cmv": 8000000, "charges_exploitation": 2500000, "produits_financiers": 200000, "revenu_perso": 800000, "charge_familiale": 200000, "fonds_propres": 8000000, "total_dettes": 3500000, "actif_total": 18000000, "actif_circulant": 6000000, "passif_circulant": 2000000, "resultat_net": 2200000, "preuve_revenu": "N3", "preuve_charge": "N3"},
        )
    )
    assert r.message_code == "VOIE_EXCEPTIONNELLE"


def test_preuves_externes_manquantes():
    r = run(
        _base(
            historique={
                "credits_ailleurs": True,
                "preuves_externes_ok": False,
                "credits_passes": [],
                "epargne_moy_6m": 40000,
            }
        )
    )
    assert r.message_code == "PREUVES_EXTERNES_MANQUANTES"
