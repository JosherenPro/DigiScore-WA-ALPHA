"""Gating + capabilities ML consultatives (guide ML, phase 1).

Le moteur règles reste la référence : ces capacités sont masquées par défaut
(`ML_ENABLED=0`) et n'influencent jamais une décision.
"""

from __future__ import annotations

import os

from digiscore.adaptive.scorecard_ml import (
    MODEL_VERSION as SCORECARD_VERSION,
    MODEL_VERSION_V3 as SCORECARD_VERSION_V3,
    load_artifact as load_scorecard_artifact,
    load_artifact_v3 as load_scorecard_artifact_v3,
)
from digiscore.anomalies import (
    MODEL_VERSION as ANOMALY_VERSION,
    MODEL_VERSION_V3 as ANOMALY_VERSION_V3,
    load_artifact as load_anomaly_artifact,
    load_artifact_v3 as load_anomaly_artifact_v3,
)
from digiscore.simulation import MODEL_VERSION as RESILIENCE_VERSION


def ml_enabled() -> bool:
    return os.getenv("ML_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def anomaly_version() -> str | None:
    if load_anomaly_artifact_v3() is not None:
        return ANOMALY_VERSION_V3
    if load_anomaly_artifact() is not None:
        return ANOMALY_VERSION
    return None


def scorecard_version() -> str | None:
    if load_scorecard_artifact_v3() is not None:
        return SCORECARD_VERSION_V3
    if load_scorecard_artifact() is not None:
        return SCORECARD_VERSION
    return None


def capabilities() -> dict:
    enabled = ml_enabled()
    anomaly = anomaly_version() if enabled else None
    scorecard = scorecard_version() if enabled else None
    version = scorecard or anomaly or (RESILIENCE_VERSION if enabled else None)
    return {
        "ml_scorecard": scorecard is not None,
        "anomalies": anomaly is not None,
        "simulation": enabled,
        "early_warning": enabled,
        "model_version": version,
    }
