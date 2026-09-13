import json
from pathlib import Path

import pytest

from digiscore.pipeline import _zone, run


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


def test_score_result_preserve_le_contrat_de_serialisation():
    payload = run(_base()).model_dump()
    assert set(payload) == {
        "eligible",
        "thin_file",
        "score_global",
        "criteres",
        "knockouts",
        "montant_demande",
        "montant_eligible",
        "montant_max_suggestion",
        "message_code",
        "message_humain",
        "explication",
        "zone",
        "financials",
    }


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
    assert not r.eligible
    assert r.montant_eligible == 0


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
    assert not r.eligible
    assert r.montant_eligible == 0


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


@pytest.mark.parametrize(
    ("score", "expected_zone"),
    [(40, "rejet"), (41, "analyse"), (70, "analyse"), (71, "approbation")],
)
def test_zone_boundaries(score, expected_zone):
    assert _zone(score) == expected_zone


@pytest.mark.parametrize(
    ("demande", "expected_code"),
    [
        ({"exclusion_esg": True, "situation_fiscale": "en_regle"}, "KNOCKOUT_ESG"),
        ({"situation_fiscale": "non_conforme"}, "BIC_OU_FISCAL_MANQUANT"),
        (
            {
                "montant": 2_000_000,
                "seuil_caution": 2_000_000,
                "nb_cautions_eligibles": 0,
                "nb_cautions_min": 1,
                "situation_fiscale": "en_regle",
            },
            "CAUTION_REQUISE",
        ),
    ],
)
def test_knockouts_refusent_sans_plafond(demande, expected_code):
    r = run(_base(demande=demande))
    assert r.message_code == expected_code
    assert r.zone == "rejet"
    assert not r.eligible
    assert r.montant_eligible == 0
    assert r.montant_max_suggestion is None


def test_knockout_priority_is_stable():
    r = run(
        _base(
            historique={"credits_ailleurs": True, "preuves_externes_ok": False},
            demande={"exclusion_esg": True, "situation_fiscale": "non_conforme"},
        )
    )
    assert r.message_code == "PREUVES_EXTERNES_MANQUANTES"
    assert [k.code for k in r.knockouts][:3] == [
        "KNOCKOUT_ESG",
        "PREUVES_EXTERNES_MANQUANTES",
        "BIC_OU_FISCAL_MANQUANT",
    ]


def test_plafond_est_arrondi_vers_le_bas():
    r = run(
        _base(
            analyse={"revenu_perso": 205_000},
            demande={"montant": 600_001, "situation_fiscale": "en_regle"},
        )
    )
    # Le plafond brut RCSD est ~815 151 FCFA : il ne doit jamais monter à 820 000.
    assert r.montant_eligible == 810_000


def test_cas_attendus_de_demo():
    expected = {
        1: _base(),
        2: _base(
            historique={"epargne_moy_3m": 100_000, "epargne_moy_6m": 100_000},
            demande={
                "montant": 2_900_000,
                "duree_mois": 60,
                "seuil_caution": 3_000_000,
                "situation_fiscale": "en_regle",
            }
        ),
        3: _base(historique={"incidents": [{"gravite": "grave"}]}),
        4: _base(
            membre={"id": 4, "anciennete_mois": 2, "statut": "actif"},
            historique={"credits_passes": [], "epargne_moy_6m": 20_000, "nb_mouvements_90j": 1},
            demande={"montant": 400_000, "duree_mois": 8, "situation_fiscale": "en_regle"},
        ),
        8: _base(
            analyse={"ca": 800_000, "cmv": 550_000, "charges_exploitation": 300_000},
            demande={"montant": 800_000, "situation_fiscale": "en_regle"},
        ),
        9: _base(
            demande={
                "montant": 10_000_000,
                "duree_mois": 24,
                "plafond_produit": 12_000_000,
                "exceptionnel": True,
                "seuil_caution": 2_000_000,
                "nb_cautions_eligibles": 2,
                "nb_cautions_min": 2,
                "situation_fiscale": "en_regle",
            },
            analyse={"ca": 18_000_000, "cmv": 8_000_000, "charges_exploitation": 2_500_000},
        ),
        10: _base(membre={"id": 10, "anciennete_mois": 70, "statut": "gele"}),
    }
    payload = json.loads(
        (Path(__file__).parents[2] / "data" / "synthetic" / "cas_attendus.json").read_text()
    )

    for case in payload["cas"]:
        result = run(expected[case["id"]])
        assert result.message_code in case["message_codes_ok"]
        if "thin_file" in case:
            assert result.thin_file is case["thin_file"]
        if "score_min" in case:
            assert result.score_global >= case["score_min"]
