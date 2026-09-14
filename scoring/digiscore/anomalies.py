"""Detection consultative d'incoherences documentaires.

Le module est volontairement independant du pipeline de decision : une
anomalie est un signal a montrer a l'agent, jamais un knockout automatique.
"""

from __future__ import annotations

from math import expm1, log1p
from pathlib import Path
from typing import Any, Iterable

from digiscore.financials import compute_all
from digiscore.limits import is_thin_file
from digiscore.types import DossierInput

MODEL_VERSION = "anomaly-v2"
ANOMALY_FEATURE_NAMES = (
    "log_revenus_sur_epargne",
    "solde_sur_revenu_mensuel",
    "patrimoine_sur_fonds_propres",
    "garanties_sur_demande",
    "rcsd",
    "mouvements_90j",
)


def _validated(dossier: dict | DossierInput) -> DossierInput:
    return dossier if isinstance(dossier, DossierInput) else DossierInput.model_validate(dossier)


def extract_features(dossier: dict | DossierInput, financials: dict | None = None) -> dict[str, float]:
    d = _validated(dossier)
    fin = financials or compute_all(d.analyse, d.demande)
    monthly_revenue = max(d.analyse.ca / 12.0, 1.0)
    epargne = max(d.historique.epargne_moy_6m, 1.0)
    equity = max(d.analyse.fonds_propres, 1.0)
    requested = max(d.demande.montant, 1.0)
    return {
        "log_revenus_sur_epargne": float(log1p(max(0.0, d.analyse.ca / epargne))),
        "solde_sur_revenu_mensuel": float(max(0.0, d.compte.solde / monthly_revenue)),
        "patrimoine_sur_fonds_propres": float(
            max(0.0, d.analyse.actif_total / equity)
        ),
        "garanties_sur_demande": float(max(0.0, d.analyse.valeur_garanties / requested)),
        "rcsd": float(max(0.0, min(10.0, fin["rcsd"]))),
        "mouvements_90j": float(max(0, d.historique.nb_mouvements_90j)),
    }


def _matrix(rows: Iterable[dict[str, float]], feature_names=ANOMALY_FEATURE_NAMES):
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - dependance optionnelle
        raise RuntimeError("numpy est requis pour la detection d'anomalies") from exc
    return np.asarray(
        [[float(row.get(name, 0.0)) for name in feature_names] for row in rows],
        dtype=float,
    )


def fit_anomaly(
    rows: Iterable[dict[str, float]],
    *,
    seed: int = 72,
) -> dict[str, Any]:
    """Entraine Isolation Forest sur des dossiers reputes normaux."""

    try:
        from sklearn.ensemble import IsolationForest
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:  # pragma: no cover - dependance optionnelle
        raise RuntimeError("scikit-learn est requis pour entrainer l'anomaly model") from exc

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "isolation_forest",
                IsolationForest(
                    contamination=0.02,
                    n_estimators=200,
                    random_state=seed,
                ),
            ),
        ]
    )
    model.fit(_matrix(rows))
    return {
        "model": model,
        "feature_names": list(ANOMALY_FEATURE_NAMES),
        "model_version": MODEL_VERSION,
        "model_type": "isolation_forest",
        "explanation_method": "z_score_features",
    }


def default_artifact_path() -> Path:
    return Path(__file__).resolve().parents[1] / "models" / "anomaly_v2.joblib"


def load_artifact(path: str | Path | None = None) -> dict[str, Any] | None:
    candidate = Path(path) if path else default_artifact_path()
    if not candidate.exists():
        return None
    try:
        import joblib

        return joblib.load(candidate)
    except (ImportError, OSError, ValueError):
        return None


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = 1.0 / (1.0 + pow(2.718281828, -value))
    else:
        ez = pow(2.718281828, value)
        z = ez / (1.0 + ez)
    return max(0.0, min(1.0, z))


def detect(
    dossier: dict | DossierInput,
    financials: dict | None = None,
    *,
    artifact: dict[str, Any] | None = None,
    artifact_path: str | Path | None = None,
) -> dict[str, Any]:
    """Retourne un signal explicable, avec fallback silencieux si absent."""

    d = _validated(dossier)
    if is_thin_file(d):
        return {
            "enabled": True,
            "scope_excluded": True,
            "anomaly_score": 0.0,
            "anomalies": [],
            "model_version": MODEL_VERSION,
        }

    bundle = artifact or load_artifact(artifact_path)
    if not bundle:
        return {
            "enabled": False,
            "scope_excluded": False,
            "anomaly_score": 0.0,
            "anomalies": [],
            "model_version": None,
        }

    try:
        import numpy as np

        features = extract_features(d, financials)
        names = tuple(bundle.get("feature_names", ANOMALY_FEATURE_NAMES))
        matrix = _matrix([features], names)
        model = bundle["model"]
        scaler = model.named_steps.get("scaler")
        transformed = scaler.transform(matrix)[0] if scaler is not None else matrix[0]
        isolation = model.named_steps.get("isolation_forest", model)
        decision = float(isolation.decision_function(transformed.reshape(1, -1))[0])
        model_component = _sigmoid(-8.0 * decision)
        z_scores = {name: float(value) for name, value in zip(names, transformed)}
        max_abs_z = max(abs(value) for value in z_scores.values()) if z_scores else 0.0
        robust_component = _sigmoid((max_abs_z - 3.0) * 1.5)
        anomaly_score = round(max(model_component, robust_component), 5)

        explanations = []
        for name, z_value in sorted(z_scores.items(), key=lambda item: abs(item[1]), reverse=True)[:3]:
            if abs(z_value) < 1.5:
                continue
            value = features[name]
            if name == "log_revenus_sur_epargne":
                message = f"Revenus declares {expm1(value):.1f}x superieurs a l'epargne moyenne observee."
            elif name == "garanties_sur_demande":
                message = f"Couverture des garanties atypique ({value:.1f}x la demande)."
            elif name == "rcsd":
                message = f"RCSD atypique ({value:.2f}) par rapport aux dossiers de reference."
            else:
                message = f"Ecart inhabituel sur {name.replace('_', ' ')} ({value:.2f})."
            explanations.append(
                {
                    "feature": name,
                    "z_score": round(z_value, 4),
                    "message": message,
                }
            )

        return {
            "enabled": True,
            "scope_excluded": False,
            "anomaly_score": anomaly_score,
            "anomalies": explanations,
            "model_version": bundle.get("model_version", MODEL_VERSION),
        }
    except (KeyError, AttributeError, IndexError, TypeError, ValueError):
        return {
            "enabled": False,
            "scope_excluded": False,
            "anomaly_score": 0.0,
            "anomalies": [],
            "model_version": None,
        }
