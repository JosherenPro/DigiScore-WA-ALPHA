"""Scorecard logistique facultative et explicable.

Le moteur de regles reste la reference. Ce module fournit une couche de
calibration en *shadow mode* : elle predit une probabilite de defaut et un
score /100, sans jamais lever un knockout ni prendre la decision finale.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

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

MODEL_VERSION = "scorecard-v2"
FEATURE_NAMES = (
    "note_financier",
    "note_capacite",
    "note_historique",
    "note_activite",
    "note_garanties",
    "note_documents",
    "anciennete_mois",
    "rcsd",
    "epargne_regularite",
    "incidents_graves",
    "montant_sur_plafond",
)
BUSINESS_WEIGHTS = {
    "note_financier": 0.25,
    "note_capacite": 0.20,
    "note_historique": 0.20,
    "note_activite": 0.15,
    "note_garanties": 0.10,
    "note_documents": 0.10,
}


@dataclass(frozen=True)
class MLScorecardResult:
    score_global: float
    probabilite_defaut: float
    contributions: list[dict[str, float | str]]
    modele_version: str
    modele_type: str = "logreg"
    methode_explication: str = "contributions_logit"
    enabled: bool = True


def _validated(dossier: dict | DossierInput) -> DossierInput:
    return dossier if isinstance(dossier, DossierInput) else DossierInput.model_validate(dossier)


def extract_features(dossier: dict | DossierInput, financials: dict | None = None) -> dict[str, float]:
    """Construit le vecteur ML depuis le contrat scoring existant.

    Le vecteur est volontairement stable et sans acces SQL. Les notes metier
    sont conservees comme features afin de comparer le poids regle au poids
    appris sur les outcomes synthetiques.
    """

    d = _validated(dossier)
    fin = financials or compute_all(d.analyse, d.demande)
    notes = {
        "note_financier": note_financier(fin),
        "note_capacite": note_capacite(fin),
        "note_historique": note_historique(d),
        "note_activite": note_activite(d),
        "note_garanties": note_garanties(d),
        "note_documents": note_documents(d),
    }
    graves = sum(incident.gravite == "grave" for incident in d.historique.incidents)
    epargne_6m = max(d.historique.epargne_moy_6m, 1.0)
    regularite = max(0.0, min(100.0, d.historique.epargne_moy_3m / epargne_6m * 100))
    plafond = max(d.demande.plafond_produit, 1.0)
    return {
        **{key: float(value) for key, value in notes.items()},
        "anciennete_mois": float(max(0, d.membre.anciennete_mois)),
        "rcsd": float(max(0.0, min(10.0, fin["rcsd"]))),
        "epargne_regularite": float(regularite),
        "incidents_graves": float(graves),
        "montant_sur_plafond": float(max(0.0, d.demande.montant / plafond)),
    }


def _matrix(rows: Iterable[dict[str, float]], feature_names: tuple[str, ...] = FEATURE_NAMES):
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - dependance optionnelle
        raise RuntimeError("numpy est requis pour le scorecard ML") from exc

    return np.asarray(
        [[float(row.get(name, 0.0)) for name in feature_names] for row in rows],
        dtype=float,
    )


def fit_scorecard(
    rows: Iterable[dict[str, float]],
    labels: Iterable[int],
    *,
    seed: int = 72,
) -> dict[str, Any]:
    """Entraine une regression logistique deterministe et serialisable."""

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:  # pragma: no cover - dependance optionnelle
        raise RuntimeError("scikit-learn est requis pour entrainer le scorecard ML") from exc

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=500,
                    random_state=seed,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    model.fit(_matrix(rows), list(labels))
    return {
        "model": model,
        "feature_names": list(FEATURE_NAMES),
        "model_version": MODEL_VERSION,
        "model_type": "logreg",
        "explanation_method": "contributions_logit",
    }


def default_artifact_path() -> Path:
    return Path(__file__).resolve().parents[2] / "models" / "scorecard_v2.joblib"


def load_artifact(path: str | Path | None = None) -> dict[str, Any] | None:
    """Charge un artefact si present ; l'absence est un fallback normal."""

    candidate = Path(path) if path else default_artifact_path()
    if not candidate.exists():
        return None
    try:
        import joblib

        return joblib.load(candidate)
    except (ImportError, OSError, ValueError):
        return None


def predict_scorecard(
    dossier: dict | DossierInput,
    financials: dict | None = None,
    *,
    artifact: dict[str, Any] | None = None,
    artifact_path: str | Path | None = None,
) -> MLScorecardResult | None:
    """Retourne la prediction ML, ou ``None`` si le fallback doit s'appliquer."""

    bundle = artifact or load_artifact(artifact_path)
    if not bundle:
        return None

    try:
        import numpy as np

        features = extract_features(dossier, financials)
        names = tuple(bundle.get("feature_names", FEATURE_NAMES))
        matrix = _matrix([features], names)
        model = bundle["model"]
        probability = float(model.predict_proba(matrix)[0, 1])
        score = max(0.0, min(100.0, 100.0 * (1.0 - probability)))

        classifier = model.named_steps.get("classifier", model)
        scaler = model.named_steps.get("scaler")
        transformed = scaler.transform(matrix)[0] if scaler is not None else matrix[0]
        coefficients = classifier.coef_[0]
        contributions = [
            {
                "feature": name,
                "value": round(float(features.get(name, 0.0)), 4),
                "coefficient": round(float(coefficient), 6),
                "contribution": round(float(value * coefficient), 6),
            }
            for name, value, coefficient in zip(names, transformed, coefficients)
        ]
        contributions.sort(key=lambda item: abs(float(item["contribution"])), reverse=True)
        return MLScorecardResult(
            score_global=round(score, 1),
            probabilite_defaut=round(max(0.0, min(1.0, probability)), 6),
            contributions=contributions,
            modele_version=bundle.get("model_version", MODEL_VERSION),
            modele_type=bundle.get("model_type", "logreg"),
            methode_explication=bundle.get("explanation_method", "contributions_logit"),
        )
    except (KeyError, AttributeError, IndexError, TypeError, ValueError):
        # Un artefact invalide ne doit jamais casser la decision regle.
        return None


def ml_enabled() -> bool:
    return os.getenv("ML_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# v3 — nouvelles variables issues des tables historisees / externes.
# Label : defaut PAR30 / impaye constate (outstanding days_late>=30 ou
# past_credit impaye). Features point-in-time a applied_at (jamais de fuite).
# ---------------------------------------------------------------------------

MODEL_VERSION_V3 = "scorecard-v3"

FEATURE_NAMES_V3 = (
    # v2 (11)
    "note_financier",
    "note_capacite",
    "note_historique",
    "note_activite",
    "note_garanties",
    "note_documents",
    "anciennete_mois",
    "rcsd",
    "epargne_regularite",
    "incidents_graves",
    "montant_sur_plafond",
    # v3 : 9 nouvelles variables (externes, BIC, comportement, preuves, marche)
    "has_external",
    "ext_epargne_log",
    "bic_incidents",
    "past_impayes",
    "max_jours_retard",
    "preuves_score",
    "dependance_debouche",
    "concurrence",
    "signaux_patrimoine",
)

_PREUVE_RANK = {"N1": 0.0, "N2": 1.0, "N3": 2.0}


def _preuves_score(d: DossierInput) -> float:
    return float(
        _PREUVE_RANK.get(d.analyse.preuve_revenu, 0.0)
        + _PREUVE_RANK.get(d.analyse.preuve_charge, 0.0)
    )


def extract_features_v3(
    dossier: dict | DossierInput, financials: dict | None = None
) -> dict[str, float]:
    """Vecteur v3 : v2 + 9 variables nouvelles, toutes optionnelles (defaut 0)."""
    base = extract_features(dossier, financials)
    d = _validated(dossier)
    h = d.historique
    past_impayes = sum(1 for c in h.credits_passes if c.statut == "impaye")
    max_jours = 0
    for c in h.credits_passes:
        max_jours = max(max_jours, int(c.jours_max_retard or 0))
    p = d.analyse.patrimoine
    signaux = sum(
        [
            p.signal_erosion_ca,
            p.signal_marge,
            p.signal_creances,
            p.signal_fournisseurs,
            p.signal_nette,
        ]
    )
    try:
        from math import log1p as _log1p

        ext_log = float(_log1p(max(0.0, h.ext_epargne_6m)))
    except (ValueError, TypeError):
        ext_log = 0.0
    base.update(
        {
            "has_external": float(1.0 if h.credits_ailleurs else 0.0),
            "ext_epargne_log": ext_log,
            "bic_incidents": float(max(0, h.bic_incidents)),
            "past_impayes": float(past_impayes),
            "max_jours_retard": float(max_jours),
            "preuves_score": float(_preuves_score(d)),
            "dependance_debouche": float(1.0 if d.analyse.dependance_debouche else 0.0),
            "concurrence": float(max(0, d.analyse.concurrence)),
            "signaux_patrimoine": float(signaux),
        }
    )
    return base


def _matrix_v3(rows: Iterable[dict[str, float]]):
    return _matrix(rows, FEATURE_NAMES_V3)


def fit_scorecard_v3(
    rows: Iterable[dict[str, float]],
    labels: Iterable[int],
    *,
    seed: int = 72,
) -> dict[str, Any]:
    """Entraine la logreg v3 (meme solveur deterministe que v2)."""
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("scikit-learn est requis pour entrainer le scorecard ML") from exc

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(max_iter=1000, random_state=seed, solver="lbfgs"),
            ),
        ]
    )
    model.fit(_matrix_v3(rows), list(labels))
    return {
        "model": model,
        "feature_names": list(FEATURE_NAMES_V3),
        "model_version": MODEL_VERSION_V3,
        "model_type": "logreg",
        "explanation_method": "contributions_logit",
    }


def default_artifact_path_v3() -> Path:
    return Path(__file__).resolve().parents[2] / "models" / "scorecard_v3.joblib"


def load_artifact_v3(path: str | Path | None = None) -> dict[str, Any] | None:
    candidate = Path(path) if path else default_artifact_path_v3()
    if not candidate.exists():
        return None
    try:
        import joblib

        return joblib.load(candidate)
    except (ImportError, OSError, ValueError):
        return None


def predict_scorecard_v3(
    dossier: dict | DossierInput,
    financials: dict | None = None,
    *,
    artifact: dict[str, Any] | None = None,
    artifact_path: str | Path | None = None,
) -> MLScorecardResult | None:
    """Prediction v3 ; fallback v2 si l'artefact v3 est absent (compat)."""
    bundle = artifact or load_artifact_v3(artifact_path)
    if not bundle:
        return predict_scorecard(dossier, financials)
    try:
        features = extract_features_v3(dossier, financials)
        names = tuple(bundle.get("feature_names", FEATURE_NAMES_V3))
        matrix = _matrix([features], names)
        model = bundle["model"]
        probability = float(model.predict_proba(matrix)[0, 1])
        score = max(0.0, min(100.0, 100.0 * (1.0 - probability)))
        classifier = model.named_steps.get("classifier", model)
        scaler = model.named_steps.get("scaler")
        transformed = scaler.transform(matrix)[0] if scaler is not None else matrix[0]
        coefficients = classifier.coef_[0]
        contributions = [
            {
                "feature": name,
                "value": round(float(features.get(name, 0.0)), 4),
                "coefficient": round(float(coefficient), 6),
                "contribution": round(float(value * coefficient), 6),
            }
            for name, value, coefficient in zip(names, transformed, coefficients)
        ]
        contributions.sort(key=lambda item: abs(float(item["contribution"])), reverse=True)
        return MLScorecardResult(
            score_global=round(score, 1),
            probabilite_defaut=round(max(0.0, min(1.0, probability)), 6),
            contributions=contributions,
            modele_version=bundle.get("model_version", MODEL_VERSION_V3),
            modele_type=bundle.get("model_type", "logreg"),
            methode_explication=bundle.get("explanation_method", "contributions_logit"),
        )
    except (KeyError, AttributeError, IndexError, TypeError, ValueError):
        return None
