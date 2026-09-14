from typing import Any

from pydantic import BaseModel, Field


class MembreIn(BaseModel):
    id: int
    anciennete_mois: int = 0
    statut: str = "actif"


class CompteIn(BaseModel):
    solde: float = 0
    date_ouverture_jours: int = 365
    statut: str = "actif"


class CreditPasseIn(BaseModel):
    montant: float = 0
    statut: str = "solde"
    nb_retards: int = 0
    jours_max_retard: int = 0


class IncidentIn(BaseModel):
    gravite: str = "faible"


class HistoriqueIn(BaseModel):
    credits_passes: list[CreditPasseIn] = Field(default_factory=list)
    incidents: list[IncidentIn] = Field(default_factory=list)
    epargne_moy_3m: float = 0
    epargne_moy_6m: float = 0
    nb_mouvements_90j: int = 0
    credits_ailleurs: bool = False
    preuves_externes_ok: bool = False


class DemandeIn(BaseModel):
    montant: float
    duree_mois: int = 12
    objet: str = ""
    produit_id: int = 1
    plafond_produit: float = 3_000_000
    seuil_caution: float = 2_000_000
    exceptionnel: bool = False
    situation_fiscale: str = "non_fourni"
    exclusion_esg: bool = False
    nb_cautions_eligibles: int = 0
    nb_cautions_min: int = 1


class TresorerieMois(BaseModel):
    mois: int
    flux_entrant: float = 0
    flux_sortant: float = 0


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
    ca: float = 0
    cmv: float = 0
    charges_exploitation: float = 0
    produits_financiers: float = 0
    revenu_perso: float = 0
    charge_familiale: float = 0
    charge_credits_en_cours: float = 0
    fonds_propres: float = 0
    total_dettes: float = 0
    actif_total: float = 0
    actif_circulant: float = 0
    passif_circulant: float = 0
    stock_moyen: float = 0
    resultat_net: float = 0
    valeur_garanties: float = 0
    preuve_revenu: str = "N1"
    preuve_charge: str = "N1"
    saisonnier: bool = False
    dependance_debouche: bool = False
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
