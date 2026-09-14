"""Anomalies consultatives (guide ML, phase 2).

Adapte `digiscore.anomalies` au contrat API sans toucher au dossier.
Modèle v3 (fallback v2 si l'artefact v3 est absent). Les thin-files sont hors
scope : liste vide et `scope_excluded: true`.
"""

from __future__ import annotations

from typing import Any

from digiscore.anomalies import detect_v3, extract_features_v3


def _round_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def detect_anomalies(dossier: dict) -> dict[str, Any]:
    report = detect_v3(dossier)
    features = extract_features_v3(dossier)
    anomalies = [
        {
            "feature": item["feature"],
            "value": _round_value(features.get(item["feature"])),
            "reference_value": None,
            "z_score": float(item["z_score"]),
            "severity": "a_verifier",
            "message": str(item["message"]),
        }
        for item in report.get("anomalies", [])
    ]
    return {
        "model_version": report.get("model_version"),
        "scope_excluded": bool(report.get("scope_excluded")),
        "anomaly_score": report.get("anomaly_score"),
        "anomalies": anomalies,
    }
