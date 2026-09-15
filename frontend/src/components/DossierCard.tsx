import { Link } from "react-router-dom";
import { zoneClass, type DemandeResume } from "../api/client";

export const STATUS_LABEL: Record<string, string> = {
  brouillon: "Brouillon",
  analyse: "Analysé",
  soumis_chef: "Chez le Chef",
  renvoye: "Renvoyé à l’agent",
  soumis_cic: "Au CIC",
  accorde: "Accordé",
  conditionne: "Conditionné",
  refuse: "Refusé",
  clos: "Clos",
};

export function statusTone(statut: string): string {
  if (statut === "accorde" || statut === "conditionne") return "ok";
  if (statut === "refuse") return "bad";
  if (statut === "soumis_chef" || statut === "soumis_cic" || statut === "renvoye") return "warn";
  return "";
}

function initials(nomComplet: string): string {
  const parts = nomComplet.trim().split(/\s+/);
  return (parts[0]?.[0] || "") + (parts[1]?.[0] || parts[0]?.[1] || "");
}

/** Carte dossier — utilisée dans la liste "Dossiers" de l'agent. Chaque
 * badge vient d'une donnée réelle de l'API (statut, agent_id, incidents,
 * historique) : rien n'est déduit côté front. Badges en rectangle (coins
 * légèrement arrondis) pour distinguer les caractéristiques du dossier des
 * pastilles de statut utilisées ailleurs dans l'appli. */
export default function DossierCard({ d, currentUserId }: { d: DemandeResume; currentUserId?: number }) {
  const isMine = currentUserId != null && d.agent_id === currentUserId;
  const actif = d.membre_statut === "actif";
  return (
    <Link className="dcard" to={`/demandes/${d.id}`}>
      <div className="dcard-top">
        <div className="dcard-avatar">
          {initials(d.membre).toUpperCase()}
          {actif && <span className="dcard-check" aria-hidden="true">✓</span>}
        </div>
        <div className="dcard-id">
          <div className="dcard-name-row">
            <strong>{d.membre}</strong>
            {isMine && <span className="badge rect warn">Mon dossier</span>}
          </div>
          {d.code_externe && <span className="muted dcard-code">{d.code_externe}</span>}
        </div>
        <span className={`dcard-score ${zoneClass(d.zone)}`}>{d.score != null ? Math.round(d.score) : "—"}</span>
      </div>
      <div className="dcard-bottom">
        <span className={`badge rect ${statusTone(d.statut)}`}>{STATUS_LABEL[d.statut] || d.statut}</span>
        {d.nb_incidents ? (
          <span className="badge rect bad">{d.nb_incidents} incident{d.nb_incidents > 1 ? "s" : ""}</span>
        ) : d.bon_historique ? (
          <span className="badge rect">Bon historique</span>
        ) : null}
        <span className="dcard-chevron" aria-hidden="true">›</span>
      </div>
    </Link>
  );
}
