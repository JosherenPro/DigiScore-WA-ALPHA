function apiBase(): string {
  if (import.meta.env.DEV) return "/api";
  const raw = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  try {
    const u = new URL(raw, typeof window === "undefined" ? "http://127.0.0.1" : window.location.origin);
    if (u.hostname === "localhost") u.hostname = "127.0.0.1";
    return u.origin;
  } catch {
    return raw.replace(/\/$/, "");
  }
}

const BASE = apiBase();

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function token(): string | null {
  return sessionStorage.getItem("digiscore_token");
}

async function parseError(res: Response): Promise<string> {
  const raw = await res.text();
  try {
    const j = JSON.parse(raw) as { detail?: unknown };
    if (typeof j.detail === "string") {
      const d = j.detail;
      if (/qualit[eé] photo|recommencer la prise/i.test(d)) return "Reprendre la photo — qualité OCR insuffisante.";
      if (d === "COMPTE_INACTIF") return "Compte gelé ou inactif : aucune demande possible.";
      if (d === "NON_MEMBRE") return "Ouverture de compte préalable obligatoire.";
      if (res.status === 401) return "Session expirée — reconnecte-toi (agent / chef / cic + mot de passe demo).";
      if (res.status === 403) return d.includes("Role") ? "Accès refusé pour ce rôle (file CIC réservée au comité)." : d;
      return d;
    }
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: string }).msg) : JSON.stringify(d)))
        .join(" · ");
    }
  } catch {
    /* texte brut */
  }
  if (res.status === 401) return "Session expirée — reconnecte-toi (agent / chef / cic + mot de passe demo).";
  if (res.status === 403) return "Accès refusé pour ce rôle (file CIC réservée au comité).";
  if (res.status === 0 || !raw) return "Lance uvicorn :8000 (API indisponible).";
  return raw || res.statusText;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) || {}),
  };
  const t = token();
  if (t) headers.Authorization = `Bearer ${t}`;
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Lance uvicorn :8000 (API indisponible).");
  }
  if (res.status === 401) {
    sessionStorage.removeItem("digiscore_token");
    sessionStorage.removeItem("digiscore_user");
  }
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// Upload multipart (photo de pièce) : pas de Content-Type manuel, le
// navigateur pose lui-même la boundary. Le reste (token, erreurs) suit req().
async function reqForm<T>(path: string, form: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  const t = token();
  if (t) headers.Authorization = `Bearer ${t}`;
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { method: "POST", headers, body: form });
  } catch {
    throw new ApiError(0, "Lance uvicorn :8000 (API indisponible).");
  }
  if (res.status === 401) {
    sessionStorage.removeItem("digiscore_token");
    sessionStorage.removeItem("digiscore_user");
  }
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return res.json() as Promise<T>;
}

/** Récupère une pièce stockée côté serveur (route authentifiée : une pièce
 * d'identité n'est pas une URL publique) et la renvoie en URL locale
 * affichable dans une <img>. Penser à URL.revokeObjectURL à l'usage fini. */
export async function fetchUploadUrl(relPath: string): Promise<string> {
  const t = token();
  const res = await fetch(`${BASE}/uploads/${relPath}`, {
    headers: t ? { Authorization: `Bearer ${t}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "Photo indisponible");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export type Page<T> = { items: T[]; page: number; page_size: number; total: number };

export type User = {
  id: number;
  login: string;
  nom: string;
  role: string;
  agence_id?: number | null;
};

export type TokenOut = { access_token: string; token_type: string; user: User };

export type MembreResume = {
  id: number;
  code_externe: string;
  nom: string;
  prenom: string;
  statut: string;
  date_adhesion: string;
  agence_id?: number | null;
};

export type CompteOut = { numero: string; statut: string; solde: number; epargne_moy_6m: number };

export type CreditPasse = {
  montant: number;
  statut: string;
  nb_retards: number;
  jours_max_retard: number;
  source?: string | null;
  institution?: string | null;
  date_octroi?: string | null;
};

export type Incident = { type: string; gravite?: string | null; detail?: string | null; date: string };

export type Mouvement = { date: string; type: string; montant: number; libelle?: string | null };

export type Agence = { id: number; code: string; nom: string; ville?: string | null; topologie?: string | null };

export type Institution = { id: number; code: string; nom: string; ville?: string | null; type: string };

export type CompteExterne = {
  id: number;
  numero_masque: string;
  solde: number;
  statut: string;
  ouvert_le: string;
  institution: Institution | null;
};

export type MembreDetail = {
  id: number;
  code_externe: string;
  nom: string;
  prenom: string;
  telephone?: string | null;
  adresse?: string | null;
  occupation?: string | null;
  statut: string;
  zone?: string | null;
  date_adhesion: string;
  anciennete_mois: number;
  thin_file: boolean;
  agence?: { id: number; code: string; nom: string; ville?: string } | null;
  compte: CompteOut | null;
  credits_passes: CreditPasse[];
  incidents: Incident[];
  nb_mouvements: number;
  nb_credits_passes: number;
  nb_demandes: number;
  nb_comptes_externes: number;
  garanties: { nature: string; valeur: number }[];
};

export type HistoriqueMembre = {
  id: number;
  code_externe: string;
  credits_passes: CreditPasse[];
  incidents: Incident[];
  mouvements: Mouvement[];
  total_mouvements: number;
  nb_comptes_externes: number;
};

export type Produit = {
  id: number;
  code: string;
  libelle: string;
  montant_max: number;
  seuil_montant_caution?: number;
  exceptionnel: boolean;
};

export type DemandeResume = {
  id: number;
  membre: string;
  membre_id: number;
  code_externe?: string | null;
  membre_statut?: string | null;
  montant_demande: number;
  statut: string;
  score: number | null;
  message_code: string | null;
  zone: string | null;
  agent_id?: number | null;
  nb_incidents?: number;
  bon_historique?: boolean;
};

export type Critere = { code?: string; note?: number; poids?: number; contribution?: number; [k: string]: unknown };
export type Knockout = { code?: string; detail?: string; [k: string]: unknown };

export type ScoreOut = {
  score_global: number;
  thin_file: boolean;
  eligible: boolean;
  montant_eligible: number;
  montant_max_suggestion: number;
  message_code: string;
  message_humain: string;
  criteres?: Critere[] | Record<string, unknown> | null;
  knockouts?: Knockout[] | Record<string, unknown> | null;
  explication?: string[] | Record<string, unknown> | null;
  zone?: string | null;
  engine_version?: string;
};

export type CautionReview = {
  revenu: number;
  charges: number;
  caf_relais: number | null;
  rcsd_relais: number | null;
  score_relais: number | null;
  eligible: boolean;
  motif: string | null;
};

export type Caution = {
  nom: string;
  prenom: string;
  telephone: string | null;
  relation: string | null;
  type_caution: string;
  montant_engage: number;
  membre_existant: boolean;
  revue: CautionReview | null;
};

export type DemandeDetail = {
  id: number;
  membre_id: number;
  produit_id?: number | null;
  objet: string;
  montant_demande: number;
  duree_mois: number;
  statut: string;
  situation_fiscale: string;
  membre?: { id: number; code_externe: string; nom: string; prenom: string } | null;
  produit?: { id: number; code: string; libelle: string; exceptionnel: boolean } | null;
  score: ScoreOut | null;
  ratios: { caf: number; rcsd: number; ebe: number } | null;
  decisions: { niveau: string; avis: string; motif: string | null; override: boolean }[];
  pieces: { type_piece: string; qualite_ocr?: string | null; fichier?: string | null }[];
  cautions: Caution[];
  collecte?: Record<string, unknown> | null;
  tresorerie?: { mois: number; periode?: string | null; encaissements: number; decaissements: number }[];
  patrimoine?: { actifs_productifs: number; actifs_non_productifs: number } | null;
  menage?: { taille: number; logement: string; charges: number } | null;
  activite?: { type: string; saisonnier: boolean; description?: string } | null;
};

export type MemoOut = {
  titre: string;
  client: string;
  projet: string;
  demande: number;
  avis?: string | null;
  rubriques: string[];
  score: ScoreOut | null;
  analyse: { caf: number; rcsd: number; ebe: number } | null;
};

export type AmortOut = {
  montant: number;
  duree_mois: number;
  lignes: { numero?: number; echeance?: number; capital?: number; interet?: number; restant?: number; [k: string]: unknown }[];
};

export type M6Out = {
  module?: string;
  par: { agence_id?: number | null; par30: number; par90: number }[];
  alertes: { signal: string; membre_id: number }[];
};

export type M7Out = {
  module?: string;
  dossiers: { membre_id: number; niveau: number; action?: string | null; responsable?: string | null }[];
};

export type AgingBucket = { bucket: string; montant: number; dossiers: number; part_pct: number };

export type AgingOut = {
  as_of: string;
  par1: number;
  par30: number;
  par90: number;
  label: string;
  encours_brut: number;
  buckets: AgingBucket[];
};

export type Echeance = {
  outstanding_loan_id: number;
  member_id: number;
  member_code: string;
  outstanding: number;
  days_late: number;
  due_on: string | null;
  bucket: string;
  priorite: string;
  niveau: number | null;
  action?: string | null;
  responsable?: string | null;
  jour: string;
};

export type EcheancesOut = { jour: string; page: number; page_size: number; total: number; items: Echeance[] };

export type DossierRecouvrement = {
  case_id: number;
  member_id: number;
  member_code: string;
  niveau: number;
  libelle: string;
  action: string;
  responsable: string;
  priorite: string;
  statut: string;
  outstanding: number;
  days_late: number;
  opened_on: string | null;
  next_on: string | null;
  recovered_amount: number;
};

export type DossiersRecouvrementOut = {
  as_of: string;
  page: number;
  page_size: number;
  total: number;
  items: DossierRecouvrement[];
};

export type ActionRecouvrementIn = {
  action_type: string;
  note?: string;
  action_on?: string;
  promise_on?: string;
  promise_kept?: boolean;
  amount_recovered?: number;
  next_on?: string;
  owner_name?: string;
};

export type JournalEntry = { date: string; type: string; note?: string | null; montant: number };

export type ActionRecouvrementOut = {
  case_id: number;
  level: number;
  priority: string | null;
  status: string;
  next_on: string | null;
  recovered_amount: number;
  journal: JournalEntry[];
};

export type VisiteAFaire = {
  outstanding_loan_id: number;
  member_id: number;
  member_code: string;
  visite: string;
  cible: string;
  jours_de_retard: number;
  statut: string;
};

export type VisitesOut = { as_of: string; items: VisiteAFaire[] };

export type VisiteIn = {
  member_id: number;
  visit_code: string;
  visit_on?: string;
  signal_code?: string;
  signal?: string;
  visit_status?: "planifiee" | "realisee" | "manquee";
  next_on?: string;
  action_taken?: string;
};

export type DemandeStats = {
  total: number;
  par_statut: Record<string, number>;
  par_zone: Record<string, number>;
  score_moyen: number | null;
  montant_total_demande: number;
  montant_total_eligible: number;
  nb_credits_ailleurs: number;
  serie_creations: { date: string; total: number }[];
};

export type VisiteOut = {
  id: number;
  member_id: number;
  visit_code: string;
  visit_on?: string | null;
  visit_status: string;
  signal_code?: string | null;
  signal?: string | null;
  action_taken?: string | null;
};

export type Capabilities = {
  ml_scorecard: boolean;
  anomalies: boolean;
  simulation: boolean;
  early_warning: boolean;
  model_version?: string | null;
};

export type Health = { status: string; service: string; database: string };

// --- ML consultatif : éclaire, ne décide jamais (voir GUIDE_ML_BACKEND_DATA.md) ---

export type Anomalie = {
  feature: string;
  value: number;
  reference_value?: number | null;
  z_score: number;
  severity: string;
  message: string;
};

export type AnomaliesOut = {
  model_version: string;
  scope_excluded: boolean;
  anomaly_score: number | null;
  anomalies: Anomalie[];
};

export type ScorecardMlOut = {
  model_version: string;
  mode: string;
  probabilite_defaut: number;
  score_global_ml: number;
  niveau_risque: string;
  regles_knockout: boolean;
  top_factors: { feature: string; contribution: number }[];
  warning?: string | null;
};

export type PlafondMlOut = {
  enabled: boolean;
  blocked_by_knockout: boolean;
  model_version: string;
  plafond_regles: number;
  plafond_ml_recommande: number | null;
  probabilite_defaut: number;
  facteur_prudence: number | null;
  explication: string;
};

export type SimulationOut = {
  application_id?: number;
  scenario: string;
  scenario_libelle?: string;
  description?: string;
  mecanique?: { revenus: number; charges: number };
  model_version: string;
  seed: number;
  p_incident: number;
  p10: number[];
  p50: number[];
  p90: number[];
  mois_critique: number | null;
  explication: string;
  montant: number;
  duree_mois: number;
  horizon_mois: number;
  iterations: number;
};

// Snapshot persistant (table resilience_simulation) — rejouable avec sa seed.
export type SimulationSavedOut = SimulationOut & { id: number; created_at: string };

export type AlertePortefeuille = {
  application_id?: number | null;
  member_code: string;
  p_par30_90j: number;
  exposure: number;
  days_late?: number;
  signals: string[];
  explication: string;
};

export type AlertesPortefeuilleOut = { model_version: string; items: AlertePortefeuille[] };

export type CollecteBody = {
  ca: number;
  cmv: number;
  charges_exploitation: number;
  produits_financiers: number;
  revenu_perso: number;
  charge_familiale: number;
  charge_credits_en_cours: number;
  fonds_propres: number;
  total_dettes: number;
  actif_total: number;
  actif_circulant: number;
  passif_circulant: number;
  stock_moyen: number;
  resultat_net: number;
  preuve_revenu: string;
  preuve_charge: string;
  saisonnier: boolean;
  type_activite: string;
  valeur_garanties: number;
};

function qs(params: Record<string, string | number | undefined>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === "") continue;
    u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => req<Health>("/health"),
  capabilities: () => req<Capabilities>("/capabilities"),
  login: (login: string, password: string) =>
    req<TokenOut>("/auth/login", { method: "POST", body: JSON.stringify({ login, password }) }),
  moi: () => req<User>("/moi"),
  agences: () => req<Agence[]>("/agences"),
  institutions: () => req<Institution[]>("/institutions"),
  referentiels: () => req<Record<string, string[]>>("/referentiels"),
  produits: () => req<Produit[]>("/produits"),
  membres: (q = "", page = 1, pageSize = 30) =>
    req<Page<MembreResume>>(`/membres${qs({ q, page, page_size: pageSize })}`),
  membre: (id: number) => req<MembreDetail>(`/membres/${id}`),
  historique: (id: number) => req<HistoriqueMembre>(`/membres/${id}/historique`),
  mouvements: (id: number, page = 1, pageSize = 30) =>
    req<Page<Mouvement>>(`/membres/${id}/mouvements${qs({ page, page_size: pageSize })}`),
  comptesExternes: (id: number) => req<CompteExterne[]>(`/membres/${id}/comptes-externes`),
  mouvementsExternes: (id: number, page = 1, pageSize = 30, institutionId?: number) =>
    req<Page<Mouvement>>(
      `/membres/${id}/mouvements-externes${qs({ page, page_size: pageSize, institution_id: institutionId })}`,
    ),
  demandes: (opts?: { statut?: string; q?: string; page?: number; pageSize?: number; membre_id?: number; agentId?: number }) =>
    req<Page<DemandeResume>>(
      `/demandes${qs({
        statut: opts?.statut,
        q: opts?.q,
        page: opts?.page ?? 1,
        page_size: opts?.pageSize ?? 30,
        membre_id: opts?.membre_id,
        agent_id: opts?.agentId,
      })}`,
    ),
  demande: (id: number) => req<DemandeDetail>(`/demandes/${id}`),
  demandeStats: (agentId?: number) => req<DemandeStats>(`/demandes/stats${qs({ agent_id: agentId })}`),
  createDemande: (body: Record<string, unknown>) =>
    req<{ id: number; statut: string }>("/demandes", { method: "POST", body: JSON.stringify(body) }),
  collecte: (id: number, body: CollecteBody) =>
    req(`/demandes/${id}/collecte`, { method: "POST", body: JSON.stringify(body) }),
  piece: (id: number, body: { type_piece: string; qualite_ocr: string; fichier?: string }) =>
    req(`/demandes/${id}/pieces`, { method: "POST", body: JSON.stringify(body) }),
  uploadPiece: (id: number, body: { type_piece: string; qualite_ocr: string; file: File }) => {
    const form = new FormData();
    form.append("type_piece", body.type_piece);
    form.append("qualite_ocr", body.qualite_ocr);
    form.append("fichier", body.file);
    return reqForm<{ ok: boolean; fichier: string }>(`/demandes/${id}/pieces/upload`, form);
  },
  analyser: (id: number) => req<ScoreOut>(`/demandes/${id}/analyser`, { method: "POST" }),
  soumettre: (id: number) => req<{ statut: string; file: string }>(`/demandes/${id}/soumettre`, { method: "POST" }),
  decision: (id: number, body: { niveau: string; avis: string; motif?: string | null; override?: boolean }) =>
    req(`/demandes/${id}/decision`, { method: "POST", body: JSON.stringify(body) }),
  memo: (id: number) => req<MemoOut>(`/demandes/${id}/memo`),
  amortissement: (id: number) => req<AmortOut>(`/demandes/${id}/amortissement`),
  scores: (id: number) => req<ScoreOut[]>(`/demandes/${id}/scores`),
  fileChef: (page = 1, pageSize = 30, q = "") =>
    req<Page<DemandeResume>>(`/files/chef${qs({ page, page_size: pageSize, q: q || undefined })}`),
  fileCic: (page = 1, pageSize = 30, q = "") =>
    req<Page<DemandeResume>>(`/files/cic${qs({ page, page_size: pageSize, q: q || undefined })}`),
  portefeuille: () => req<M6Out>("/vision/portefeuille"),
  recouvrement: () => req<M7Out>("/vision/recouvrement"),
  aging: () => req<AgingOut>("/vision/aging"),
  echeances: (page = 1, pageSize = 30, q = "") =>
    req<EcheancesOut>(`/vision/echeances${qs({ page, page_size: pageSize, q: q || undefined })}`),
  dossiersRecouvrement: (opts?: { niveau?: number; priorite?: string; q?: string; page?: number; pageSize?: number }) =>
    req<DossiersRecouvrementOut>(
      `/vision/recouvrement/dossiers${qs({
        niveau: opts?.niveau,
        priorite: opts?.priorite,
        q: opts?.q || undefined,
        page: opts?.page ?? 1,
        page_size: opts?.pageSize ?? 30,
      })}`,
    ),
  logActionRecouvrement: (caseId: number, body: ActionRecouvrementIn) =>
    req<ActionRecouvrementOut>(`/vision/recouvrement/${caseId}/actions`, { method: "POST", body: JSON.stringify(body) }),
  visites: (limit = 50) => req<VisitesOut>(`/vision/visites${qs({ limit })}`),
  logVisite: (body: VisiteIn) => req<VisiteOut>("/vision/visites", { method: "POST", body: JSON.stringify(body) }),

  // ML consultatif — masqué si capabilities.* est false (voir Capabilities)
  anomalies: (id: number) => req<AnomaliesOut>(`/demandes/${id}/anomalies`),
  mlScorecard: (id: number) => req<ScorecardMlOut>(`/demandes/${id}/ml/scorecard`),
  mlPlafond: (id: number) => req<PlafondMlOut>(`/demandes/${id}/ml/plafond`),
  simuler: (id: number, body: { scenario: string; montant?: number; duree_mois?: number; horizon_mois?: number }) =>
    req<SimulationOut>(`/demandes/${id}/simuler`, { method: "POST", body: JSON.stringify(body) }),
  enregistrerSimulation: (id: number, body: { scenario: string; montant?: number; duree_mois?: number; horizon_mois?: number }) =>
    req<SimulationSavedOut>(`/demandes/${id}/simulation/enregistrer`, { method: "POST", body: JSON.stringify(body) }),
  simulations: (id: number) => req<SimulationSavedOut[]>(`/demandes/${id}/simulations`),
  alertesPortefeuille: (limit = 20) => req<AlertesPortefeuilleOut>(`/portefeuille/alertes${qs({ limit })}`),
};

export const money = (n: number) =>
  new Intl.NumberFormat("fr-FR").format(Math.round(n || 0)) + " F";

export function asList<T>(v: T[] | Record<string, unknown> | null | undefined): T[] {
  if (!v) return [];
  if (Array.isArray(v)) return v;
  return Object.entries(v).map(([code, rest]) => ({ code, ...(typeof rest === "object" && rest ? rest : {}) }) as T);
}

export function zoneClass(zone?: string | null): string {
  if (zone === "approbation") return "ok";
  if (zone === "analyse") return "warn";
  if (zone === "rejet") return "bad";
  return "";
}
