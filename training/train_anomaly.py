"""Entraine l'artefact Isolation Forest sur un reference normal synthetique."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from digiscore.anomalies import ANOMALY_FEATURE_NAMES, fit_anomaly


def generate_normal_rows(volume: int = 5000, seed: int = 72):
    rng = np.random.default_rng(seed)
    n = max(100, int(volume))
    values = np.column_stack(
        [
            np.clip(rng.normal(25.0, 8.0, n), 4.0, 60.0),
            np.clip(rng.normal(0.65, 0.25, n), 0.05, 2.0),
            np.clip(rng.normal(3.5, 1.2, n), 0.5, 8.0),
            np.clip(rng.normal(0.55, 0.25, n), 0.0, 1.5),
            np.clip(rng.normal(1.55, 0.40, n), 0.4, 3.5),
            np.clip(rng.normal(5.0, 2.0, n), 0.0, 15.0),
        ]
    )
    return [
        {name: float(value) for name, value in zip(ANOMALY_FEATURE_NAMES, row)}
        for row in values
    ]


def train(output: str | Path, volume: int = 5000, seed: int = 72):
    bundle = fit_anomaly(generate_normal_rows(volume, seed), seed=seed)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output)
    metadata = {
        "model_version": bundle["model_version"],
        "model_type": bundle["model_type"],
        "feature_names": bundle["feature_names"],
        "seed": seed,
        "rows": volume,
    }
    output.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="scoring/models/anomaly_v1.joblib")
    parser.add_argument("--volume", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=72)
    args = parser.parse_args()
    print(json.dumps(train(args.output, args.volume, args.seed), ensure_ascii=False))


if __name__ == "__main__":
    main()
