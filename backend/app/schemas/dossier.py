"""Contrats JSON Front ↔ Back (alignés scoring/SPEC.md)."""

from pydantic import BaseModel, Field


class CollecteIn(BaseModel):
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
    preuve_revenu: str = "N1"
    preuve_charge: str = "N1"
    saisonnier: bool = False
    type_activite: str = "commerce"
    valeur_garanties: float = 0


class DemandeCreate(BaseModel):
    membre_id: int
    produit_id: int = 1
    objet: str
    montant_demande: float = Field(gt=0, le=100_000_000)
    duree_mois: int = Field(default=12, ge=1, le=60)
    agent_id: int = 1
    situation_fiscale: str = "non_fourni"
    credits_ailleurs: bool = False
    preuves_externes_ok: bool = False
    collecte: CollecteIn | None = None


class DecisionIn(BaseModel):
    niveau: str
    avis: str
    motif: str | None = None
    override: bool = False


class LoginIn(BaseModel):
    login: str = Field(..., examples=["agent"])
    password: str = Field(..., examples=["demo"])


class LoginOut(BaseModel):
    id: int
    login: str
    nom: str
    role: str
    agence_id: int | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: LoginOut


class PieceIn(BaseModel):
    type_piece: str
    fichier: str = "upload/demo.jpg"
    qualite_ocr: str = "ok"


class ProduitOut(BaseModel):
    id: int
    code: str
    libelle: str
    montant_max: float
    seuil_montant_caution: float
    exceptionnel: bool


class MembreListItem(BaseModel):
    id: int
    code_externe: str
    nom: str
    prenom: str
    statut: str
    date_adhesion: str
    agence_id: int | None = None


class PageMembres(BaseModel):
    items: list[MembreListItem]
    page: int
    page_size: int
    total: int


class CompteOut(BaseModel):
    numero: str
    statut: str
    solde: float
    epargne_moy_6m: float


class CreditPasseOut(BaseModel):
    montant: float
    statut: str
    nb_retards: int
    jours_max_retard: int
    source: str | None = None
    institution: str | None = None
    date_octroi: str | None = None


class IncidentOut(BaseModel):
    type: str
    gravite: str | None = None
    detail: str | None = None
    date: str


class MembreDetail(BaseModel):
    id: int
    code_externe: str
    nom: str
    prenom: str
    telephone: str | None = None
    adresse: str | None = None
    occupation: str | None = None
    statut: str
    zone: str | None = None
    date_adhesion: str
    anciennete_mois: int
    thin_file: bool
    agence: dict | None = None
    compte: CompteOut | None = None
    credits_passes: list[CreditPasseOut] = Field(default_factory=list)
    incidents: list[IncidentOut] = Field(default_factory=list)
    nb_mouvements: int = 0
    nb_credits_passes: int = 0
    nb_demandes: int = 0
    nb_comptes_externes: int = 0
    garanties: list[dict] = Field(default_factory=list)


class DemandeCreateOut(BaseModel):
    id: int
    statut: str


class OkOut(BaseModel):
    ok: bool = True


class DemandeListItem(BaseModel):
    id: int
    membre: str
    membre_id: int
    montant_demande: float
    statut: str
    score: float | None = None
    message_code: str | None = None
    zone: str | None = None


class PageDemandes(BaseModel):
    items: list[DemandeListItem]
    page: int
    page_size: int
    total: int


class ScoreBloc(BaseModel):
    score_global: float
    thin_file: bool
    eligible: bool
    montant_eligible: float
    montant_max_suggestion: float
    message_code: str
    message_humain: str
    criteres: list | dict | None = None
    knockouts: list | dict | None = None
    explication: list | dict | None = None
    zone: str | None = None


class RatiosOut(BaseModel):
    caf: float
    rcsd: float
    ebe: float


class DecisionOut(BaseModel):
    niveau: str
    avis: str
    motif: str | None = None
    override: bool = False


class PieceOut(BaseModel):
    type_piece: str
    qualite_ocr: str | None = None


class DemandeDetail(BaseModel):
    id: int
    membre_id: int
    produit_id: int | None = None
    objet: str
    montant_demande: float
    duree_mois: int
    statut: str
    situation_fiscale: str
    membre: dict | None = None
    produit: dict | None = None
    score: ScoreBloc | None = None
    ratios: RatiosOut | None = None
    decisions: list[DecisionOut] = Field(default_factory=list)
    pieces: list[PieceOut] = Field(default_factory=list)
    collecte: dict | None = None
    tresorerie: list[dict] = Field(default_factory=list)
    patrimoine: dict | None = None
    menage: dict | None = None
    activite: dict | None = None


class SoumettreOut(BaseModel):
    statut: str
    file: str


class DecisionResultOut(BaseModel):
    statut: str
    override: bool


class MemoOut(BaseModel):
    titre: str
    client: str
    projet: str
    demande: float
    analyse: RatiosOut | None = None
    score: ScoreBloc | None = None
    avis: str | None = None
    rubriques: list[str]


class AmortissementOut(BaseModel):
    montant: float
    duree_mois: int
    taux_nominal: float = 0.018
    taux_assurance: float = 0.12
    mensualite_hors_assurance: float = 0
    assurance_mensuelle: float = 0
    mensualite_totale: float = 0
    cout_total: float = 0
    lignes: list[dict]


class ParOut(BaseModel):
    agence_id: int | None = None
    par1: float | None = None
    par30: float
    par90: float
    encours_brut: float | None = None
    label: str | None = None


class VisionPortefeuilleOut(BaseModel):
    module: str
    as_of: str | None = None
    par: list[ParOut]
    alertes: list[dict]


class DossierRecouvrementOut(BaseModel):
    membre_id: int
    niveau: int
    action: str | None = None
    responsable: str | None = None


class VisionRecouvrementOut(BaseModel):
    module: str
    dossiers: list[DossierRecouvrementOut]


class HealthOut(BaseModel):
    status: str
    service: str
    database: str = "ok"


class CapabilitiesOut(BaseModel):
    ml_scorecard: bool = False
    anomalies: bool = False
    simulation: bool = False
    early_warning: bool = False
    model_version: str | None = None


class AgenceOut(BaseModel):
    id: int
    code: str
    nom: str
    ville: str | None = None
    topologie: str | None = None


class InstitutionOut(BaseModel):
    id: int
    code: str
    nom: str
    ville: str | None = None
    type: str


class ReferentielsOut(BaseModel):
    statuts_membre: list[str]
    statuts_demande: list[str]
    avis: list[str]
    niveaux: list[str]
    zones: list[str]
    preuves: list[str]
    types_piece: list[str]
    qualite_ocr: list[str]


class MouvementOut(BaseModel):
    date: str
    type: str
    montant: float
    libelle: str | None = None


class PageMouvements(BaseModel):
    items: list[MouvementOut]
    page: int
    page_size: int
    total: int


class MlScorecardOut(BaseModel):
    score_global_ml: float | None = None
    probabilite_defaut: float | None = None
    modele_version: str | None = None
    modele_type: str | None = None
    top_factors: list[dict] = Field(default_factory=list)
    contributions: list[dict] = Field(default_factory=list)


class MlAnomalyOut(BaseModel):
    enabled: bool = False
    scope_excluded: bool = False
    anomaly_score: float | None = None
    anomalies: list[dict] = Field(default_factory=list)
    model_version: str | None = None


class MlAssistanceOut(BaseModel):
    model_version: str | None = None
    mode: str = "shadow"
    scorecard: MlScorecardOut | None = None
    anomalies: MlAnomalyOut | None = None
    plafond_ml: dict | None = None
    warning: str | None = None


class SimulationIn(BaseModel):
    scenario: dict | str | None = None
    montant: float | None = None
    duree_mois: int | None = None
    seed: int = 72
