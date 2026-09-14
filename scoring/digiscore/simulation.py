"""Simulation deterministe de resilience de tresorerie (Monte Carlo)."""

from __future__ import annotations

from typing import Any

from digiscore.financials import service_credit_sollicite
from digiscore.types import DossierInput

MODEL_VERSION = "resilience-v1"


def _validated(dossier: dict | DossierInput) -> DossierInput:
    return dossier if isinstance(dossier, DossierInput) else DossierInput.model_validate(dossier)


def _scenario_adjustments(scenario: dict[str, Any] | None) -> tuple[str, float, float]:
    scenario = scenario or {"type": "normal", "intensite": 0.0}
    kind = str(scenario.get("type", "normal"))
    intensity = float(scenario.get("intensite", 0.0))
    if kind == "choc":
        return kind, min(0.0, intensity), abs(intensity) * 0.25
    if kind == "maladie":
        return kind, -0.35, 0.15
    if kind == "inflation":
        return kind, 0.0, max(0.0, intensity or 0.15)
    return "normal", 0.0, 0.0


def _base_months(dossier: DossierInput, months: int):
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - dependance optionnelle
        raise RuntimeError("numpy est requis pour la simulation") from exc

    rows = {row.mois: (row.flux_entrant, row.flux_sortant) for row in dossier.analyse.tresorerie}
    if rows:
        values = [rows.get(index, rows[max(rows)]) for index in range(1, months + 1)]
        inflow = np.asarray([item[0] for item in values], dtype=float)
        outflow = np.asarray([item[1] for item in values], dtype=float)
    else:
        inflow = np.full(months, max(0.0, dossier.analyse.ca / 12.0), dtype=float)
        outflow = np.full(
            months,
            max(
                0.0,
                (dossier.analyse.cmv + dossier.analyse.charges_exploitation + dossier.analyse.charge_credits_en_cours)
                / 12.0,
            ),
            dtype=float,
        )
    return inflow, outflow


def simulate_resilience(
    dossier: dict | DossierInput,
    *,
    scenario: dict[str, Any] | None = None,
    montant: float | None = None,
    duree_mois: int | None = None,
    trajectories: int = 1000,
    months: int | None = None,
    seed: int = 72,
) -> dict[str, Any]:
    """Simule les soldes cumules P10/P50/P90 et la probabilite d'incident.

    Le resultat est JSON-ready et ne persiste rien. Le meme seed et le meme
    dossier produisent exactement la meme reponse, ce qui est indispensable
    pour la demo et les tests.
    """

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - dependance optionnelle
        raise RuntimeError("numpy est requis pour la simulation") from exc

    d = _validated(dossier)
    n_paths = max(1, min(int(trajectories), 10000))
    horizon = max(1, min(int(months or duree_mois or 12), 24))
    requested = d.demande.montant if montant is None else max(0.0, float(montant))
    duration = d.demande.duree_mois if duree_mois is None else max(1, int(duree_mois))
    kind, income_delta, expense_delta = _scenario_adjustments(scenario)
    inflow, outflow = _base_months(d, horizon)
    rng = np.random.default_rng(seed)

    income = max(0.0, 1.0 + income_delta)
    expenses = max(0.0, 1.0 + expense_delta)
    noise = rng.normal(1.0, 0.08, size=(n_paths, horizon)).clip(0.5, 1.5)
    inflow_paths = inflow[None, :] * income * noise
    outflow_paths = outflow[None, :] * expenses * noise
    debt_service = service_credit_sollicite(
        d.demande.model_copy(update={"montant": requested, "duree_mois": duration})
    ) / 12.0
    net = inflow_paths - outflow_paths - debt_service
    cumulative = np.cumsum(net, axis=1)
    incident = np.any(cumulative < 0, axis=1)
    quantiles = np.quantile(cumulative, [0.10, 0.50, 0.90], axis=0)
    median = quantiles[1]
    negative_months = np.flatnonzero(median < 0)
    critical_month = int(negative_months[0] + 1) if len(negative_months) else None

    def rounded(values):
        return [round(float(value), 2) for value in values]

    return {
        "model_version": MODEL_VERSION,
        "seed": seed,
        "scenario": {"type": kind, "intensite": scenario.get("intensite", 0.0) if scenario else 0.0},
        "montant": requested,
        "duree_mois": duration,
        "trajectories": n_paths,
        "p_incident": round(float(np.mean(incident)), 5),
        "trajectoires": {
            "p10": rounded(quantiles[0]),
            "p50": rounded(quantiles[1]),
            "p90": rounded(quantiles[2]),
        },
        "mois_critique": critical_month,
    }
