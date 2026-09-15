"""Contrats JSON des capacités ML consultatives (GUIDE_ML_BACKEND_DATA.md).

Le ML éclaire, l'humain décide : ces champs ne modifient jamais `eligible`,
`zone`, `message_code`, les knockouts ni le routage.
"""

from pydantic import BaseModel, Field


class AnomalieOut(BaseModel):
    feature: str
    value: float | None = None
    reference_value: float | None = None
    z_score: float
    severity: str = "a_verifier"
    message: str


class AnomaliesOut(BaseModel):
    model_version: str | None = None
    scope_excluded: bool = False
    anomaly_score: float | None = None
    anomalies: list[AnomalieOut] = Field(default_factory=list)


class SimulationIn(BaseModel):
    scenario: str | dict = "normal"
    montant: float | None = Field(default=None, ge=0)
    duree_mois: int | None = Field(default=None, ge=1, le=60)
    horizon_mois: int | None = Field(default=None, ge=1, le=24)
    iterations: int = Field(default=1000, ge=1, le=10000)
    seed: int = 42


class SimulationOut(BaseModel):
    application_id: int
    scenario: str
    scenario_libelle: str = ""
    description: str = ""
    mecanique: dict = Field(default_factory=dict)
    model_version: str
    seed: int
    p_incident: float
    p10: list[float]
    p50: list[float]
    p90: list[float]
    mois_critique: int | None = None
    explication: str
    montant: float
    duree_mois: int
    horizon_mois: int
    iterations: int


class SimulationSavedOut(SimulationOut):
    id: int
    created_at: str


class AlerteOut(BaseModel):
    application_id: int | None = None
    member_code: str
    member_name: str = ""
    member_id: int | None = None
    p_par30_90j: float
    exposure: float
    days_late: int
    signals: list[str] = Field(default_factory=list)
    explication: str


class AlertesOut(BaseModel):
    model_version: str
    items: list[AlerteOut] = Field(default_factory=list)


class ScorecardShadowOut(BaseModel):
    model_version: str | None = None
    mode: str = "shadow"
    probabilite_defaut: float | None = None
    # Score /100 historique (100 * (1 - p_defaut)), conserve pour compatibilite
    # front ; preferer `niveau_risque` pour tout nouvel affichage.
    score_global_ml: float | None = None
    niveau_risque: str | None = None
    regles_knockout: bool = False
    top_factors: list[dict] = Field(default_factory=list)
    contributions: list[dict] = Field(default_factory=list)
    warning: str | None = None


class PlafondMlOut(BaseModel):
    enabled: bool = False
    blocked_by_knockout: bool = False
    model_version: str | None = None
    plafond_regles: float | None = None
    plafond_ml_recommande: float | None = None
    probabilite_defaut: float | None = None
    facteur_prudence: float | None = None
    explication: str | None = None
    # Decomposition auditable du calcul + resume en langage clair.
    detail: dict = Field(default_factory=dict)
    raisons: list[str] = Field(default_factory=list)
