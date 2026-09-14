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
  montant_demande: number;
  statut: string;
  score: number | null;
  message_code: string | null;
  zone: string | null;
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
  pieces: { type_piece: string; qualite_ocr?: string | null }[];
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

export type Capabilities = {
  ml_scorecard: boolean;
  anomalies: boolean;
  simulation: boolean;
  early_warning: boolean;
  model_version?: string | null;
};

export type Health = { status: string; service: string; database: string };

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
  demandes: (opts?: { statut?: string; page?: number; pageSize?: number; membre_id?: number }) =>
    req<Page<DemandeResume>>(
      `/demandes${qs({
        statut: opts?.statut,
        page: opts?.page ?? 1,
        page_size: opts?.pageSize ?? 30,
        membre_id: opts?.membre_id,
      })}`,
    ),
  demande: (id: number) => req<DemandeDetail>(`/demandes/${id}`),
  createDemande: (body: Record<string, unknown>) =>
    req<{ id: number; statut: string }>("/demandes", { method: "POST", body: JSON.stringify(body) }),
  collecte: (id: number, body: CollecteBody) =>
    req(`/demandes/${id}/collecte`, { method: "POST", body: JSON.stringify(body) }),
  piece: (id: number, body: { type_piece: string; qualite_ocr: string; fichier?: string }) =>
    req(`/demandes/${id}/pieces`, { method: "POST", body: JSON.stringify(body) }),
  analyser: (id: number) => req<ScoreOut>(`/demandes/${id}/analyser`, { method: "POST" }),
  soumettre: (id: number) => req<{ statut: string; file: string }>(`/demandes/${id}/soumettre`, { method: "POST" }),
  decision: (id: number, body: { niveau: string; avis: string; motif?: string | null; override?: boolean }) =>
    req(`/demandes/${id}/decision`, { method: "POST", body: JSON.stringify(body) }),
  memo: (id: number) => req<MemoOut>(`/demandes/${id}/memo`),
  amortissement: (id: number) => req<AmortOut>(`/demandes/${id}/amortissement`),
  scores: (id: number) => req<ScoreOut[]>(`/demandes/${id}/scores`),
  fileChef: (page = 1, pageSize = 30) =>
    req<Page<DemandeResume>>(`/files/chef${qs({ page, page_size: pageSize })}`),
  fileCic: (page = 1, pageSize = 30) =>
    req<Page<DemandeResume>>(`/files/cic${qs({ page, page_size: pageSize })}`),
  portefeuille: () => req<M6Out>("/vision/portefeuille"),
  recouvrement: () => req<M7Out>("/vision/recouvrement"),
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
