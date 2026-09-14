"""Contrats JSON du suivi portefeuille M6 / recouvrement M7 (règles FUCEC)."""

from pydantic import BaseModel, Field


class AgingBucketOut(BaseModel):
    bucket: str
    montant: float
    dossiers: int
    part_pct: float


class AgingOut(BaseModel):
    as_of: str
    par1: float
    par30: float
    par90: float
    label: str
    encours_brut: float
    buckets: list[AgingBucketOut] = Field(default_factory=list)


class EcheanceOut(BaseModel):
    outstanding_loan_id: int
    member_id: int
    member_code: str
    outstanding: float
    days_late: int
    due_on: str | None = None
    bucket: str
    priorite: str
    niveau: int | None = None
    action: str | None = None
    responsable: str | None = None
    jour: str


class EcheancesOut(BaseModel):
    jour: str
    items: list[EcheanceOut] = Field(default_factory=list)


class VisiteAFaireOut(BaseModel):
    outstanding_loan_id: int
    member_id: int
    member_code: str
    visite: str
    cible: str
    jours_de_retard: int
    statut: str


class VisitesOut(BaseModel):
    as_of: str
    items: list[VisiteAFaireOut] = Field(default_factory=list)


class VisiteIn(BaseModel):
    member_id: int
    visit_code: str = Field(..., pattern="^V[123]$")
    visit_on: str | None = None
    officer_id: int | None = None
    signal_code: str | None = None
    signal: str | None = None
    visit_status: str = Field(default="realisee", pattern="^(planifiee|realisee|manquee)$")
    next_on: str | None = None
    action_taken: str | None = None


class VisiteOut(BaseModel):
    id: int
    member_id: int
    visit_code: str
    visit_on: str | None = None
    visit_status: str
    signal_code: str | None = None
    signal: str | None = None
    action_taken: str | None = None


class DossierRecouvrementRichOut(BaseModel):
    case_id: int
    member_id: int
    member_code: str
    niveau: int
    libelle: str
    action: str
    responsable: str
    priorite: str
    statut: str
    outstanding: float
    days_late: int
    opened_on: str | None = None
    next_on: str | None = None
    recovered_amount: float = 0


class DossiersOut(BaseModel):
    as_of: str
    total: int
    items: list[DossierRecouvrementRichOut] = Field(default_factory=list)


class ActionRecouvrementIn(BaseModel):
    action_type: str
    note: str | None = None
    action_on: str | None = None
    promise_on: str | None = None
    promise_kept: bool | None = None
    amount_recovered: float = Field(default=0, ge=0)
    next_on: str | None = None
    owner_name: str | None = None


class ActionRecouvrementOut(BaseModel):
    case_id: int
    level: int
    priority: str | None = None
    status: str
    next_on: str | None = None
    recovered_amount: float
    journal: list[dict] = Field(default_factory=list)


class ParRecalculOut(BaseModel):
    as_of: str
    snapshots: list[dict] = Field(default_factory=list)


class SignalOut(BaseModel):
    code: str
    famille: str
    libelle: str


class SignauxOut(BaseModel):
    model_version: str = "referential-fucec-v1"
    items: list[SignalOut] = Field(default_factory=list)
