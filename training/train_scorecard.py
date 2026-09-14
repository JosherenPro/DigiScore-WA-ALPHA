"""Entraine le scorecard v1 et exporte modele, poids et calibration."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from digiscore.adaptive.scorecard_ml import (
    BUSINESS_WEIGHTS,
    FEATURE_NAMES,
    fit_scorecard,
)


def read_dataset(path: str | Path):
    rows: list[dict[str, float]] = []
    labels: list[int] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            labels.append(int(raw.pop("label_defaut")))
            rows.append({key: float(raw[key]) for key in FEATURE_NAMES})
    return rows, labels


def train(
    dataset_path: str | Path,
    artifact_path: str | Path,
    weights_path: str | Path,
    metrics_path: str | Path,
    *,
    seed: int = 72,
) -> dict[str, object]:
    rows, labels = read_dataset(dataset_path)
    train_rows, test_rows, train_labels, test_labels = train_test_split(
        rows,
        labels,
        test_size=0.25,
        random_state=seed,
        stratify=labels,
    )
    bundle = fit_scorecard(train_rows, train_labels, seed=seed)
    model = bundle["model"]
    test_matrix = [[row[name] for name in FEATURE_NAMES] for row in test_rows]
    probabilities = model.predict_proba(test_matrix)[:, 1]
    auc = float(roc_auc_score(test_labels, probabilities))
    brier = float(brier_score_loss(test_labels, probabilities))
    fraction, mean_predicted = calibration_curve(test_labels, probabilities, n_bins=10, strategy="quantile")

    classifier = model.named_steps["classifier"]
    coefficients = classifier.coef_[0]
    absolute = {name: abs(float(value)) for name, value in zip(FEATURE_NAMES, coefficients)}
    total = max(sum(absolute.values()), 1e-12)
    learned_weights = {name: round(value / total, 6) for name, value in absolute.items()}
    weights = {
        "model_version": bundle["model_version"],
        "model_type": bundle["model_type"],
        "business_weights": BUSINESS_WEIGHTS,
        "learned_weights": learned_weights,
        "coefficients": {name: round(float(value), 6) for name, value in zip(FEATURE_NAMES, coefficients)},
    }
    metrics = {
        "model_version": bundle["model_version"],
        "seed": seed,
        "rows": len(rows),
        "default_rate": round(sum(labels) / len(labels), 6),
        "auc": round(auc, 6),
        "brier_score": round(brier, 6),
        "calibration": [
            {"mean_predicted": round(float(predicted), 6), "fraction_positive": round(float(actual), 6)}
            for predicted, actual in zip(mean_predicted, fraction)
        ],
    }

    import joblib

    artifact_path = Path(artifact_path)
    weights_path = Path(weights_path)
    metrics_path = Path(metrics_path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, artifact_path)
    weights_path.write_text(json.dumps(weights, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="training/dataset_v1.csv")
    parser.add_argument("--artifact", default="scoring/models/scorecard_v1.joblib")
    parser.add_argument("--weights", default="scoring/models/scorecard_v1_poids.json")
    parser.add_argument("--metrics", default="scoring/models/scorecard_v1_metrics.json")
    parser.add_argument("--seed", type=int, default=72)
    args = parser.parse_args()
    print(json.dumps(train(args.dataset, args.artifact, args.weights, args.metrics, seed=args.seed), ensure_ascii=False))


if __name__ == "__main__":
    main()
