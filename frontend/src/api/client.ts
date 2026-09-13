const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type User = { id: number; login: string; nom: string; role: string };

export const api = {
  login: (login: string) => req<User>("/auth/login", { method: "POST", body: JSON.stringify({ login }) }),
  membres: (q = "") => req<MembreResume[]>(`/membres?q=${encodeURIComponent(q)}`),
  membre: (id: number) => req<MembreDetail>(`/membres/${id}`),
  produits: () => req<Produit[]>("/produits"),
  demandes: (statut?: string) => req<DemandeResume[]>(statut ? `/demandes?statut=${statut}` : "/demandes"),
  demande: (id: number) => req<DemandeDetail>(`/demandes/${id}`),
  createDemande: (body: Record<string, unknown>) =>
    req<{ id: number; statut: string }>("/demandes", { method: "POST", body: JSON.stringify(body) }),
  collecte: (id: number, body: Record<string, unknown>) =>
    req(`/demandes/${id}/collecte`, { method: "POST", body: JSON.stringify(body) }),
  piece: (id: number, body: Record<string, unknown>) =>
    req(`/demandes/${id}/pieces`, { method: "POST", body: JSON.stringify(body) }),
  analyser: (id: number) => req<ScoreOut>(`/demandes/${id}/analyser`, { method: "POST" }),
  soumettre: (id: number, utilisateurId: number) =>
    req<{ statut: string; file: string }>(`/demandes/${id}/soumettre?utilisateur_id=${utilisateurId}`, {
      method: "POST",
    }),
  decision: (id: number, body: Record<string, unknown>) =>
    req(`/demandes/${id}/decision`, { method: "POST", body: JSON.stringify(body) }),
  memo: (id: number) => req<MemoOut>(`/demandes/${id}/memo`),
  amortissement: (id: number) => req<AmortOut>(`/demandes/${id}/amortissement`),
  fileChef: () => req<DemandeResume[]>("/files/chef"),
  fileCic: () => req<DemandeResume[]>("/files/cic"),
  portefeuille: () => req<M6Out>("/vision/portefeuille"),
  recouvrement: () => req<M7Out>("/vision/recouvrement"),
};

export type MembreResume = {
  id: number;
  code_externe: string;
  nom: string;
  prenom: string;
  statut: string;
  date_adhesion: string;
};

export type MembreDetail = MembreResume & {
  telephone?: string;
  zone?: string;
  anciennete_mois: number;
  thin_file: boolean;
  compte: { numero: string; statut: string; solde: number; epargne_moy_6m: number } | null;
  credits_passes: { montant: number; statut: string; nb_retards: number; jours_max_retard: number }[];
  incidents: { type: string; gravite: string; detail: string; date: string }[];
};

export type Produit = {
  id: number;
  code: string;
  libelle: string;
  montant_max: number;
  exceptionnel: boolean;
};

export type DemandeResume = {
  id: number;
  membre: string;
  membre_id?: number;
  montant_demande: number;
  statut: string;
  score: number | null;
  message_code: string | null;
  zone: string | null;
};

export type ScoreOut = {
  score_global: number;
  thin_file: boolean;
  eligible: boolean;
  montant_eligible: number;
  montant_max_suggestion: number;
  message_code: string;
  message_humain: string;
  criteres: { code: string; note: number; poids: number; contribution: number }[];
  knockouts: { code: string; detail: string }[];
  explication: string[];
  zone?: string;
};

export type DemandeDetail = {
  id: number;
  membre_id: number;
  objet: string;
  montant_demande: number;
  duree_mois: number;
  statut: string;
  situation_fiscale: string;
  score: ScoreOut | null;
  ratios: { caf: number; rcsd: number; ebe: number } | null;
  decisions: { niveau: string; avis: string; motif: string | null; override: boolean }[];
  pieces: { type_piece: string; qualite_ocr: string }[];
};

export type MemoOut = {
  titre: string;
  client: string;
  projet: string;
  demande: number;
  avis: string;
  rubriques: string[];
  score: ScoreOut | null;
  analyse: { caf: number; rcsd: number; ebe: number } | null;
};

export type AmortOut = {
  montant: number;
  duree_mois: number;
  lignes: { numero: number; echeance: number; capital: number; interet: number; restant: number }[];
};

export type M6Out = {
  par: { agence_id: number; par30: number; par90: number }[];
  alertes: { signal: string; membre_id: number }[];
};

export type M7Out = {
  dossiers: { membre_id: number; niveau: number; action: string; responsable: string }[];
};

export const money = (n: number) =>
  new Intl.NumberFormat("fr-FR").format(Math.round(n)) + " F";
