import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from digiscore.adaptive.scorecard_ml import FEATURE_NAMES, fit_scorecard, predict_scorecard
from digiscore.anomalies import detect, fit_anomaly
from digiscore.counterfactual import suggest_counterfactuals
from digiscore.credit_limit_ml import recommend_credit_limit
from digiscore.ml import run_ml_assistance
from digiscore.simulation import mecanique_scenario, simulate_resilience
from training.generate import generate_dataset
from training.train_anomaly import generate_normal_rows


def _dossier():
    return {
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
            "tresorerie": [
                {"mois": month, "flux_entrant": 300000, "flux_sortant": 180000}
                for month in range(1, 13)
            ],
        },
    }


def test_scorecard_appris_rejouable_et_auc():
    rows, labels = generate_dataset(4000, seed=72)
    assert 0.15 <= sum(labels) / len(labels) <= 0.25
    train_rows, test_rows, train_labels, test_labels = train_test_split(
        rows, labels, test_size=0.25, random_state=72, stratify=labels
    )
    first = fit_scorecard(train_rows, train_labels, seed=72)
    second = fit_scorecard(train_rows, train_labels, seed=72)
    x_test = [[row[name] for name in FEATURE_NAMES] for row in test_rows]
    p_first = first["model"].predict_proba(x_test)[:, 1]
    p_second = second["model"].predict_proba(x_test)[:, 1]
    assert np.allclose(p_first, p_second)
    assert roc_auc_score(test_labels, p_first) >= 0.70
    assert abs(float(np.mean(p_first)) - float(np.mean(test_labels))) < 0.03
    assert brier_score_loss(test_labels, p_first) < 0.18


def test_scorecard_prediction_est_sur_100_et_expliquable():
    rows, labels = generate_dataset(2000, seed=72)
    artifact = fit_scorecard(rows, labels, seed=72)
    result = predict_scorecard(_dossier(), artifact=artifact)
    assert result is not None
    assert 0 <= result.score_global <= 100
    assert 0 <= result.probabilite_defaut <= 1
    assert result.modele_version == "scorecard-v2"
    assert result.contributions
    assert {item["feature"] for item in result.contributions} == set(FEATURE_NAMES)


def test_facade_ml_desactivee_ne_casse_pas_le_moteur():
    result = run_ml_assistance(_dossier(), enabled=False)
    assert result == {
        "enabled": False,
        "modele": None,
        "probabilite_defaut": None,
        "anomalies": [],
        "anomaly_score": None,
        "anomaly_scope_excluded": False,
        "plafond_ml": None,
    }


def test_plafond_ml_ne_depasse_jamais_le_plafond_regles():
    low_risk = recommend_credit_limit(_dossier(), default_probability=0.05)
    high_risk = recommend_credit_limit(_dossier(), default_probability=0.40)
    assert low_risk["plafond_ml_recommande"] <= low_risk["plafond_regles"]
    assert high_risk["plafond_ml_recommande"] < low_risk["plafond_ml_recommande"]
    assert high_risk["facteur_prudence"] == 0.60


def test_plafond_ml_est_bloque_par_un_knockout():
    dossier = _dossier()
    dossier["membre"]["statut"] = "gele"
    result = recommend_credit_limit(dossier, default_probability=0.05)
    assert result["blocked_by_knockout"] is True
    assert result["plafond_ml_recommande"] is None


def test_anomalie_documentaire_explique_un_revenu_trop_eleve():
    artifact = fit_anomaly(generate_normal_rows(3000, seed=72), seed=72)
    normal = detect(_dossier(), artifact=artifact)
    trap = _dossier()
    trap["analyse"]["ca"] *= 5.6
    suspicious = detect(trap, artifact=artifact)
    assert suspicious["anomaly_score"] > normal["anomaly_score"]
    assert suspicious["anomaly_score"] >= 0.8
    assert any(item["feature"] == "log_revenus_sur_epargne" for item in suspicious["anomalies"])


def test_thin_file_est_hors_du_scope_des_anomalies():
    dossier = _dossier()
    dossier["membre"]["anciennete_mois"] = 2
    dossier["historique"].update(
        {
            "credits_passes": [],
            "epargne_moy_3m": 30_000,
            "epargne_moy_6m": 20_000,
            "nb_mouvements_90j": 1,
        }
    )
    result = detect(dossier)
    assert result["scope_excluded"] is True
    assert result["anomalies"] == []


def test_simulation_est_deterministe_et_le_choc_augmente_le_risque():
    dossier = _dossier()
    normal = simulate_resilience(dossier, seed=72)
    replay = simulate_resilience(dossier, seed=72)
    shock = simulate_resilience(dossier, scenario={"type": "choc", "intensite": -0.40}, seed=72)
    assert normal == replay
    assert shock["p_incident"] >= normal["p_incident"]
    assert len(shock["trajectoires"]["p50"]) == 12


def test_mecanique_scenario_explicite_le_choc_reel():
    assert mecanique_scenario({"type": "choc", "intensite": -0.40}) == {
        "revenus": 0.6,
        "charges": 1.1,
    }
    assert mecanique_scenario({"type": "inflation", "intensite": 0.15}) == {
        "revenus": 1.0,
        "charges": 1.15,
    }
    assert mecanique_scenario(None) == {"revenus": 1.0, "charges": 1.0}


def test_simulation_produit_un_risque_intermediaire_sur_un_dossier_limite():
    dossier = _dossier()
    dossier["analyse"]["tresorerie"] = [
        {"mois": month, "flux_entrant": 260_000, "flux_sortant": 180_000}
        for month in range(1, 13)
    ]
    result = simulate_resilience(
        dossier,
        scenario={"type": "choc", "intensite": -0.20},
        trajectories=5_000,
        seed=72,
    )
    assert 0 < result["p_incident"] < 1


def test_contrefactuel_ne_leve_jamais_un_knockout():
    dossier = _dossier()
    dossier["membre"] = {"id": 4, "anciennete_mois": 2, "statut": "actif"}
    dossier["historique"] = {
        "credits_passes": [],
        "incidents": [],
        "epargne_moy_3m": 30000,
        "epargne_moy_6m": 20000,
        "nb_mouvements_90j": 1,
    }
    dossier["demande"].update({"montant": 400000, "duree_mois": 8, "situation_fiscale": "non_fourni"})
    dossier["analyse"].update(
        {
            "ca": 900000,
            "cmv": 500000,
            "charges_exploitation": 200000,
            "revenu_perso": 60000,
            "charge_familiale": 30000,
            "fonds_propres": 50000,
            "total_dettes": 80000,
            "actif_total": 200000,
            "actif_circulant": 80000,
            "passif_circulant": 60000,
            "stock_moyen": 40000,
            "resultat_net": 40000,
        }
    )
    result = suggest_counterfactuals(dossier, target_score=71)
    assert result["blocked_by_knockout"] is True
    assert result["items"] == []
