"""Simulateur de résilience (guide ML, phase 3).

Adapte `digiscore.simulation.simulate_resilience` au contrat API et persiste
les snapshots dans `resilience_simulation` (rejouables avec leur seed).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import ResilienceSimulation
from digiscore.simulation import mecanique_scenario, simulate_resilience

SCENARIOS: dict[str, dict[str, Any]] = {
    # Les intensites sont des stress CONVENTIONNELS (niveaux illustratifs pour
    # la demo, non calibres sur l'historique) : chaque fiche precise donc en
    # langage clair ce que le scenario fait subir au dossier.
    "mauvaise_recolte": {
        "type": "choc",
        "intensite": -0.40,
        "description": (
            "Stress conventionnel : perte de 40 % des revenus d'activité sur "
            "toute la durée (sécheresse, mévente) et charges +10 % "
            "(intrants, transport). Niveau illustratif, non calibré."
        ),
    },
    "choc": {
        "type": "choc",
        "intensite": -0.30,
        "description": "Stress conventionnel : revenus −30 %, charges +7,5 %.",
    },
    "maladie": {
        "type": "maladie",
        "intensite": 0.0,
        "description": "Arrêt d'activité : revenus −35 %, charges +15 % (soins, remplacement).",
    },
    "inflation": {
        "type": "inflation",
        "intensite": 0.15,
        "description": "Hausse des charges de 15 %, revenus inchangés.",
    },
    "normal": {
        "type": "normal",
        "intensite": 0.0,
        "description": "Aucun choc : trajectoire sur la base du plan de trésorerie.",
    },
    "prudent": {
        "type": "choc",
        "intensite": -0.30,
        "description": "Variante prudente : revenus −30 %, charges +7,5 %.",
    },
    "central": {
        "type": "normal",
        "intensite": 0.0,
        "description": "Aucun choc : trajectoire centrale du plan de trésorerie.",
    },
    "optimiste": {
        "type": "normal",
        "intensite": 0.0,
        "description": "Aucun choc (variante optimiste du plan de base).",
    },
    "intrants_+20": {
        "type": "inflation",
        "intensite": 0.20,
        "description": "Hausse des intrants : charges +20 %, revenus inchangés.",
    },
}
SCORING_TYPES = frozenset({"choc", "maladie", "inflation", "normal"})

# Libelles d'affichage par scenario. La cle technique reste stable pour l'API ;
# seul le libelle s'adapte a l'activite du dossier (un choc de revenus ne
# s'appelle pas "mauvaise recolte" chez une commercante).
LIBELLES_DEFAUT: dict[str, str] = {
    "mauvaise_recolte": "Choc de revenus (−40 %)",
    "choc": "Choc de revenus",
    "prudent": "Choc de revenus",
    "maladie": "Maladie / arrêt d'activité",
    "inflation": "Hausse des charges",
    "intrants_+20": "Hausse des intrants (+20 %)",
    "normal": "Trajectoire normale",
    "central": "Trajectoire normale",
    "optimiste": "Trajectoire optimiste",
}
LIBELLES_CHOC_PAR_ACTIVITE: dict[str, str] = {
    "primaire": "Mauvaise récolte",
    "secondaire": "Baisse de la demande",
    "tertiaire": "Mévente prolongée",
    # anciennes valeurs du seed v1 (rétro-compatibilité)
    "agriculture": "Mauvaise récolte",
    "commerce": "Mévente prolongée",
    "services": "Creux d'activité",
}


def libelle_scenario(label: str, activite: str | None = None) -> str:
    """Libelle humain d'un scenario, adapte a l'activite du dossier."""
    if label == "mauvaise_recolte" and (activite or "").lower() in LIBELLES_CHOC_PAR_ACTIVITE:
        return LIBELLES_CHOC_PAR_ACTIVITE[activite.lower()]
    return LIBELLES_DEFAUT.get(label, label)


def resolve_scenario(scenario: str | dict | None) -> tuple[str, dict[str, Any]]:
    if isinstance(scenario, dict):
        kind = str(scenario.get("type", "normal"))
        if kind not in SCORING_TYPES:
            raise ValueError(f"Scenario inconnu : {kind}")
        payload = {"type": kind, "intensite": float(scenario.get("intensite", 0.0))}
        return kind, payload
    label = str(scenario or "normal")
    if label not in SCENARIOS:
        raise ValueError(f"Scenario inconnu : {label}")
    payload = dict(SCENARIOS[label])
    return label, payload


def description_scenario(label: str, payload: dict[str, Any]) -> str:
    """Description en langage clair ; les scenarios custom sont decrits via leur mecanique."""
    if payload.get("description"):
        return str(payload["description"])
    mec = mecanique_scenario(payload)
    return (
        f"Scenario personnalisé : revenus ×{mec['revenus']}, charges ×{mec['charges']}."
    )


def _explication(p_incident: float, critical_month: int | None) -> str:
    if critical_month is not None:
        return (
            f"{round(p_incident * 100)} % des simulations ne couvrent pas "
            f"l'échéance du mois {critical_month}."
        )
    return "Trajectoire médiane positive sur tout l'horizon simulé."


def simulate(
    dossier: dict,
    application_id: int,
    *,
    scenario: str | dict | None,
    montant: float | None,
    duree_mois: int | None,
    horizon_mois: int | None,
    iterations: int,
    seed: int,
    activite: str | None = None,
) -> dict[str, Any]:
    label, payload = resolve_scenario(scenario)
    result = simulate_resilience(
        dossier,
        scenario=payload,
        montant=montant,
        duree_mois=duree_mois,
        trajectories=iterations,
        months=horizon_mois,
        seed=seed,
    )
    trajectories = result["trajectoires"]
    p_incident = float(result["p_incident"])
    critical = result.get("mois_critique")
    return {
        "application_id": application_id,
        "scenario": label,
        "scenario_libelle": libelle_scenario(label, activite),
        "description": description_scenario(label, payload),
        "mecanique": mecanique_scenario(payload),
        "model_version": str(result["model_version"]),
        "seed": int(result["seed"]),
        "p_incident": p_incident,
        "p10": trajectories["p10"],
        "p50": trajectories["p50"],
        "p90": trajectories["p90"],
        "mois_critique": critical,
        "explication": _explication(p_incident, critical),
        "montant": float(result["montant"]),
        "duree_mois": int(result["duree_mois"]),
        "horizon_mois": len(trajectories["p50"]),
        "iterations": int(result["trajectories"]),
    }


def save_simulation(db: Session, user_id: int, result: dict[str, Any]) -> ResilienceSimulation:
    row = ResilienceSimulation(
        application_id=result["application_id"],
        scenario=result["scenario"],
        requested_amount=result["montant"],
        term_months=result["duree_mois"],
        horizon_months=result["horizon_mois"],
        iterations=result["iterations"],
        random_seed=result["seed"],
        model_version=result["model_version"],
        incident_probability=result["p_incident"],
        critical_month=result["mois_critique"],
        result_json={
            "p10": result["p10"],
            "p50": result["p50"],
            "p90": result["p90"],
            "explication": result["explication"],
            "scenario_libelle": result.get("scenario_libelle", result["scenario"]),
            "description": result.get("description", ""),
            "mecanique": result.get("mecanique", {}),
        },
        created_by=user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_simulations(db: Session, application_id: int) -> list[ResilienceSimulation]:
    return list(
        db.scalars(
            select(ResilienceSimulation)
            .where(ResilienceSimulation.application_id == application_id)
            .order_by(ResilienceSimulation.created_at.desc(), ResilienceSimulation.id.desc())
        ).all()
    )


def serialize_simulation(row: ResilienceSimulation) -> dict[str, Any]:
    payload = row.result_json or {}
    return {
        "id": row.id,
        "application_id": row.application_id,
        "scenario": row.scenario,
        "scenario_libelle": payload.get("scenario_libelle", row.scenario),
        "description": payload.get("description", ""),
        "mecanique": payload.get("mecanique", {}),
        "model_version": row.model_version,
        "seed": int(row.random_seed or 0),
        "p_incident": float(row.incident_probability or 0.0),
        "p10": payload.get("p10", []),
        "p50": payload.get("p50", []),
        "p90": payload.get("p90", []),
        "mois_critique": row.critical_month,
        "explication": payload.get("explication", ""),
        "montant": float(row.requested_amount or 0.0),
        "duree_mois": int(row.term_months or 0),
        "horizon_mois": int(row.horizon_months or 0),
        "iterations": int(row.iterations or 0),
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }
