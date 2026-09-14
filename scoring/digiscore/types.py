from typing import Any

from pydantic import BaseModel, Field


class MembreIn(BaseModel):
    id: int
    anciennete_mois: int = Field(default=0, ge=0)
    statut: str = "actif"


class CompteIn(BaseModel):
    solde: float = Field(default=0, ge=0)
    date_ouverture_jours: int = Field(default=365, ge=0)
    statut: str = "actif"


class CreditPasseIn(BaseModel):
    montant: float = Field(default=0, ge=0)
    statut: str = "solde"
    nb_retards: int = Field(default=0, ge=0)
    jours_max_retard: int = Field(default=0, ge=0)


class IncidentIn(BaseModel):
    gravite: str = "faible"


class HistoriqueIn(BaseModel):
    credits_passes: list[CreditPasseIn] = Field(default_factory=list)
    incidents: list[IncidentIn] = Field(default_factory=list)
    epargne_moy_3m: float = Field(default=0, ge=0)
    epargne_moy_6m: float = Field(default=0, ge=0)
    nb_mouvements_90j: int = Field(default=0, ge=0)
    credits_ailleurs: bool = False
    preuves_externes_ok: bool = False
    # v3 — nouvelles variables issues des tables historisees / externes (defaut 0 = compatible v2).
    ext_epargne_6m: float = Field(default=0, ge=0)
    ext_nb_mouvements_90j: int = Field(default=0, ge=0)
    bic_incidents: int = Field(default=0, ge=0)


class DemandeIn(BaseModel):
    montant: float = Field(ge=0)
    duree_mois: int = Field(default=12, ge=1)
    objet: str = ""
    produit_id: int = 1
    plafond_produit: float = Field(default=3_000_000, ge=0)
    seuil_caution: float = Field(default=2_000_000, ge=0)
    exceptionnel: bool = False
    situation_fiscale: str = "non_fourni"
    exclusion_esg: bool = False
    nb_cautions_eligibles: int = Field(default=0, ge=0)
    nb_cautions_min: int = Field(default=1, ge=0)


class TresorerieMois(BaseModel):
    mois: int = Field(ge=1)
    flux_entrant: float = Field(default=0, ge=0)
    flux_sortant: float = Field(default=0, ge=0)


class PatrimoineIn(BaseModel):
    actifs_productifs: float = 0
    actifs_non_productifs: float = 0
    passifs_formels: float = 0
    passifs_informels: float = 0
    signal_erosion_ca: bool = False
    signal_marge: bool = False
    signal_creances: bool = False
    signal_fournisseurs: bool = False
    signal_nette: bool = False


class AnalyseIn(BaseModel):
    ca: float = Field(default=0, ge=0)
    cmv: float = Field(default=0, ge=0)
    charges_exploitation: float = Field(default=0, ge=0)
    produits_financiers: float = Field(default=0, ge=0)
    revenu_perso: float = Field(default=0, ge=0)
    charge_familiale: float = Field(default=0, ge=0)
    charge_credits_en_cours: float = Field(default=0, ge=0)
    fonds_propres: float = Field(default=0, ge=0)
    total_dettes: float = Field(default=0, ge=0)
    actif_total: float = Field(default=0, ge=0)
    actif_circulant: float = Field(default=0, ge=0)
    passif_circulant: float = Field(default=0, ge=0)
    stock_moyen: float = Field(default=0, ge=0)
    resultat_net: float = 0
    valeur_garanties: float = Field(default=0, ge=0)
    preuve_revenu: str = "N1"
    preuve_charge: str = "N1"
    saisonnier: bool = False
    dependance_debouche: bool = False
    # v3 — marche / activite issus de market + activity (defaut 0 = compatible v2).
    concurrence: int = Field(default=0, ge=0)
    anciennete_activite_mois: int = Field(default=12, ge=0)
    tresorerie: list[TresorerieMois] = Field(default_factory=list)
    patrimoine: PatrimoineIn = Field(default_factory=PatrimoineIn)


class DossierInput(BaseModel):
    membre: MembreIn
    compte: CompteIn
    historique: HistoriqueIn
    demande: DemandeIn
    analyse: AnalyseIn


class CritereOut(BaseModel):
    code: str
    note: float = Field(ge=0, le=100)
    poids: float
    contribution: float


class KnockoutOut(BaseModel):
    code: str
    detail: str


class ScoreResult(BaseModel):
    eligible: bool
    thin_file: bool
    # Contrat public DigiScore : le score est toujours exprime sur 100.
    score_global: float = Field(ge=0, le=100)
    criteres: list[CritereOut]
    knockouts: list[KnockoutOut]
    montant_demande: float
    montant_eligible: float
    montant_max_suggestion: float | None = None
    message_code: str
    message_humain: str
    explication: list[str]
    zone: str
    financials: dict[str, Any] = Field(default_factory=dict)
