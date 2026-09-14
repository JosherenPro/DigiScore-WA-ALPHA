"""Genere un dataset synthetique labellise pour le scorecard ML.

Le generateur ne lit ni la base ni de donnees client. La seed et les
coefficients de verite terrain sont publies afin de rendre l'experience
rejouable et auditable.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from digiscore.adaptive.scorecard_ml import FEATURE_NAMES

GROUND_TRUTH = {
    "intercept": -1.70,
    "note_mean": -0.018,
    "anciennete_mois": -0.012,
    "rcsd": -1.10,
    "epargne_regularite": -0.008,
    "incidents_graves": 1.10,
    "montant_sur_plafond": 1.20,
    "noise_std": 0.35,
}


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def generate_dataset(volume: int = 20_000, seed: int = 72) -> tuple[list[dict[str, float]], list[int]]:
    rng = np.random.default_rng(seed)
    n = max(100, int(volume))
    notes = np.clip(rng.normal(62.0, 18.0, size=(n, 6)), 0.0, 100.0)
    age = np.clip(rng.gamma(shape=2.4, scale=10.0, size=n), 0.0, 120.0)
    rcsd = np.clip(rng.normal(1.45, 0.55, size=n), 0.15, 4.5)
    regularity = np.clip(rng.normal(68.0, 22.0, size=n), 0.0, 100.0)
    incidents = rng.binomial(1, 0.16, size=n).astype(float)
    amount_ratio = np.clip(rng.normal(0.68, 0.24, size=n), 0.05, 1.5)
    note_mean = notes.mean(axis=1)
    logit = (
        GROUND_TRUTH["intercept"]
        + GROUND_TRUTH["note_mean"] * (note_mean - 60.0)
        + GROUND_TRUTH["anciennete_mois"] * (age - 18.0)
        + GROUND_TRUTH["rcsd"] * (rcsd - 1.45)
        + GROUND_TRUTH["epargne_regularite"] * (regularity - 65.0)
        + GROUND_TRUTH["incidents_graves"] * incidents
        + GROUND_TRUTH["montant_sur_plafond"] * (amount_ratio - 0.65)
        + rng.normal(0.0, GROUND_TRUTH["noise_std"], size=n)
    )
    probabilities = _sigmoid(logit)
    labels = rng.binomial(1, probabilities).astype(int).tolist()
    rows: list[dict[str, float]] = []
    for index in range(n):
        row = {
            name: float(value)
            for name, value in zip(
                FEATURE_NAMES[:6],
                notes[index],
            )
        }
        row.update(
            {
                "anciennete_mois": float(age[index]),
                "rcsd": float(rcsd[index]),
                "epargne_regularite": float(regularity[index]),
                "incidents_graves": float(incidents[index]),
                "montant_sur_plafond": float(amount_ratio[index]),
            }
        )
        rows.append(row)
    return rows, labels


def write_dataset(output: str | Path, ground_truth_output: str | Path, volume: int, seed: int) -> dict[str, float]:
    rows, labels = generate_dataset(volume, seed)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*FEATURE_NAMES, "label_defaut"])
        writer.writeheader()
        for row, label in zip(rows, labels):
            writer.writerow({**row, "label_defaut": label})
    ground_truth = {
        "seed": seed,
        "volume": len(rows),
        "taux_defaut": round(float(np.mean(labels)), 6),
        "coefficients": GROUND_TRUTH,
    }
    target = Path(ground_truth_output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(ground_truth, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ground_truth


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=72)
    parser.add_argument("--output", default="training/dataset_v1.csv")
    parser.add_argument("--ground-truth", default="training/ground_truth.json")
    args = parser.parse_args()
    result = write_dataset(args.output, args.ground_truth, args.volume, args.seed)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
