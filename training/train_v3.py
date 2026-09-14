"""Entraine scorecard-v3 + anomaly-v3 sur dataset_v3 (Postgres point-in-time).

Usage : python3 training/train_v3.py
Sorties : scoring/models/scorecard_v3.joblib + _metrics.json + _poids.json,
          scoring/models/anomaly_v3.joblib + .json
"""

from __future__ import annotations

import csv
import json
from math import log1p
from pathlib import Path

from digiscore.adaptive.scorecard_ml import (
    FEATURE_NAMES_V3,
    fit_scorecard_v3,
)
from digiscore.anomalies import ANOMALY_FEATURE_NAMES_V3, fit_anomaly
from digiscore.financials import compute_all
from digiscore.scorecard import (
    note_activite,
    note_capacite,
    note_documents,
    note_financier,
    note_garanties,
    note_historique,
)
from digiscore.types import DossierInput

DATASET = Path("training/dataset_v3.csv")
SEED = 72
_RANK = {"N1": 0.0, "N2": 1.0, "N3": 2.0}


def _f(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (ValueError, TypeError):
        return default


def _i(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except (ValueError, TypeError):
        return default


def row_to_dossier(r: dict) -> DossierInput:
    nb_solde_ok = _i(r.get("nb_solde_ok"))
    nb_solde = _i(r.get("nb_solde"))
    nb_impaye = _i(r.get("nb_impaye"))
    nb_grave = _i(r.get("nb_grave"))
    credits = (
        [{"montant": 300000, "statut": "solde", "nb_retards": 0, "jours_max_retard": 0}] * nb_solde_ok
        + [{"montant": 300000, "statut": "solde", "nb_retards": 2, "jours_max_retard": 10}]
        * max(0, nb_solde - nb_solde_ok)
        + [{"montant": 300000, "statut": "impaye", "nb_retards": 3, "jours_max_retard": _i(r.get("max_jours_past"))}]
        * nb_impaye
    )
    # anciennete_mois depuis joined_on si dispo, sinon 12
    anciennete = 12
    try:
        from datetime import date

        j = str(r.get("joined_on") or "")[:10]
        if j:
            y, m, _d = map(int, j.split("-"))
            today = date.today()
            anciennete = max(0, (today.year - y) * 12 + today.month - m)
    except (ValueError, TypeError):
        pass
    return DossierInput.model_validate(
        {
            "membre": {"id": _i(r.get("member_id"), 1), "anciennete_mois": anciennete, "statut": r.get("member_status") or "actif"},
            "compte": {"solde": _f(r.get("solde")), "date_ouverture_jours": 365, "statut": r.get("account_status") or "actif"},
            "historique": {
                "credits_passes": credits,
                "incidents": [{"gravite": "grave"}] * nb_grave,
                "epargne_moy_3m": _f(r.get("epargne_3m")),
                "epargne_moy_6m": _f(r.get("epargne_6m")),
                "nb_mouvements_90j": _i(r.get("nb_mvt_90j")),
                "credits_ailleurs": str(r.get("has_external_credits")).lower() in ("1", "true", "t"),
                "preuves_externes_ok": str(r.get("external_proofs_ok")).lower() in ("1", "true", "t"),
                "ext_epargne_6m": _f(r.get("ext_epargne_6m")),
                "ext_nb_mouvements_90j": _i(r.get("ext_mvt_90j")),
                "bic_incidents": _i(r.get("bic_incidents")),
            },
            "demande": {
                "montant": _f(r.get("requested_amount"), 500000),
                "duree_mois": _i(r.get("term_months"), 12) or 12,
                "objet": r.get("purpose") or "",
                "produit_id": _i(r.get("product_id"), 1),
                "plafond_produit": _f(r.get("plafond_produit"), 3000000),
                "seuil_caution": _f(r.get("seuil_caution"), 2000000),
                "exceptionnel": str(r.get("exceptionnel")).lower() in ("1", "true", "t"),
                "situation_fiscale": r.get("tax_status") or "non_fourni",
                "exclusion_esg": str(r.get("esg_exclusion")).lower() in ("1", "true", "t"),
                "nb_cautions_eligibles": 0,
                "nb_cautions_min": 1,
            },
            "analyse": {
                "ca": _f(r.get("ca")),
                "cmv": _f(r.get("cmv")),
                "charges_exploitation": _f(r.get("operating_costs")),
                "produits_financiers": _f(r.get("financial_income")),
                "revenu_perso": _f(r.get("personal_income")),
                "charge_familiale": _f(r.get("family_cost")),
                "charge_credits_en_cours": _f(r.get("existing_debt_service")),
                "fonds_propres": _f(r.get("fonds_propres")),
                "total_dettes": _f(r.get("total_debt")),
                "actif_total": _f(r.get("total_assets")),
                "actif_circulant": _f(r.get("current_assets")),
                "passif_circulant": _f(r.get("current_liabilities")),
                "stock_moyen": _f(r.get("stock_moyen")),
                "resultat_net": _f(r.get("resultat_net")),
                "valeur_garanties": _f(r.get("valeur_garanties")),
                "preuve_revenu": (r.get("preuve_revenu") or "N1").strip() or "N1",
                "preuve_charge": (r.get("preuve_charge") or "N1").strip() or "N1",
                "saisonnier": str(r.get("saisonnier")).lower() in ("1", "true", "t"),
                "dependance_debouche": str(r.get("dependance")).lower() in ("1", "true", "t"),
                "concurrence": _i(r.get("concurrence")),
                "tresorerie": [],
                "patrimoine": {
                    "actifs_productifs": 0,
                    "actifs_non_productifs": 0,
                    "passifs_formels": 0,
                    "passifs_informels": 0,
                    "signal_erosion_ca": False,
                    "signal_marge": False,
                    "signal_creances": False,
                    "signal_fournisseurs": False,
                    "signal_nette": False,
                },
            },
        }
    )


def dossier_to_features_v3(d: DossierInput, signaux_pat: int) -> dict[str, float]:
    from digiscore.adaptive.scorecard_ml import extract_features_v3

    feats = extract_features_v3(d)
    feats["signaux_patrimoine"] = float(signaux_pat)
    return feats


def dossier_to_anomaly_v3(d: DossierInput) -> dict[str, float]:
    from digiscore.anomalies import extract_features_v3

    return extract_features_v3(d)


def main() -> None:
    import joblib
    from sklearn.calibration import calibration_curve
    from sklearn.metrics import brier_score_loss, roc_auc_score
    from sklearn.model_selection import train_test_split

    rows_raw = list(csv.DictReader(DATASET.open(encoding="utf-8")))
    feats, labels, anom_feats, anom_labels = [], [], [], []
    # Label futur propre (anti-fuite) : PAR30 constate APRES decision.
    # label_defaut (past inclus) est circulaire avec past_impayes -> AUC=1.0.
    label_col = "label_par30_futur" if "label_par30_futur" in (rows_raw[0].keys() if rows_raw else []) else "label_defaut"
    for r in rows_raw:
        d = row_to_dossier(r)
        f = dossier_to_features_v3(d, _i(r.get("signaux_pat")))
        feats.append({k: float(f.get(k, 0.0)) for k in FEATURE_NAMES_V3})
        labels.append(int(float(r[label_col])))
        a = dossier_to_anomaly_v3(d)
        anom_feats.append({k: float(a.get(k, 0.0)) for k in ANOMALY_FEATURE_NAMES_V3})
        anom_labels.append(int(float(r[label_col])))

    tr, te, ytr, yte = train_test_split(feats, labels, test_size=0.25, random_state=SEED, stratify=labels)
    bundle = fit_scorecard_v3(tr, ytr, seed=SEED)
    proba = bundle["model"].predict_proba([[x[n] for n in FEATURE_NAMES_V3] for x in te])[:, 1]
    auc = float(roc_auc_score(yte, proba))
    brier = float(brier_score_loss(yte, proba))
    frac, mean_pred = calibration_curve(yte, proba, n_bins=8, strategy="quantile")
    clf = bundle["model"].named_steps["classifier"]
    coefs = clf.coef_[0]
    total = max(sum(abs(float(c)) for c in coefs), 1e-12)
    learned = {n: round(abs(float(c)) / total, 6) for n, c in zip(FEATURE_NAMES_V3, coefs)}

    out = Path("scoring/models/scorecard_v3.joblib")
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out)
    (out.parent / "scorecard_v3_metrics.json").write_text(
        json.dumps(
            {
                "model_version": "scorecard-v3",
                "seed": SEED,
                "rows": len(feats),
                "default_rate": round(sum(labels) / len(labels), 6),
                "auc": round(auc, 6),
                "brier_score": round(brier, 6),
                "label": "par30_futur_outstanding_impaye_j30+_seul",
                "source": "postgres_volume_v2_point_in_time",
                "warning": "Volume synthetique deterministe (profil late -> past_impaye + PAR30 lies) : AUC proche de 1. Pipeline technique OK, pas un risque reel. Shadow/demo uniquement; production = historiques FUCEC reels.",
                "calibration": [
                    {"mean_predicted": round(float(p), 6), "fraction_positive": round(float(f), 6)}
                    for p, f in zip(mean_pred, frac)
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (out.parent / "scorecard_v3_poids.json").write_text(
        json.dumps(
            {"model_version": "scorecard-v3", "learned_weights": learned,
             "coefficients": {n: round(float(c), 6) for n, c in zip(FEATURE_NAMES_V3, coefs)}},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # Anomalie v3 : fit sur sains uniquement
    normals = [f for f, y in zip(anom_feats, anom_labels) if y == 0][:8000]
    abundle = fit_anomaly(normals, seed=SEED)
    abundle["feature_names"] = list(ANOMALY_FEATURE_NAMES_V3)
    abundle["model_version"] = "anomaly-v3"
    # re-fit avec bonnes features (fit_anomaly utilise ANOMALY_FEATURE_NAMES v2 en interne :
    # on reordonne via _matrix v3 en reappelant le pipeline sur les memes lignes)
    import numpy as np

    X = np.asarray([[float(x[n]) for n in ANOMALY_FEATURE_NAMES_V3] for x in normals], dtype=float)
    abundle["model"].fit(X)
    joblib.dump(abundle, Path("scoring/models/anomaly_v3.joblib"))
    Path("scoring/models/anomaly_v3.json").write_text(
        json.dumps(
            {"model_version": "anomaly-v3", "model_type": "isolation_forest",
             "feature_names": list(ANOMALY_FEATURE_NAMES_V3), "seed": SEED, "rows": len(normals)},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"auc": round(auc, 4), "brier": round(brier, 4),
                      "rows": len(feats), "rate": round(sum(labels) / len(labels), 4),
                      "anomaly_rows": len(normals)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
