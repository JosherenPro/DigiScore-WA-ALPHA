import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, zoneClass, type DemandeResume } from "../api/client";
import { getUser } from "../auth";
import Pager from "../components/Pager";
import Alert from "../components/Alert";
import Spinner from "../components/Spinner";
import PageSearch from "../components/PageSearch";
import { STATUS_LABEL } from "../components/DossierCard";

const PAGE = 30;

const ZONE_LABEL: Record<string, string> = {
  approbation: "Approbation suggérée",
  analyse: "Autorisation hiérarchique",
  rejet: "Dossier à régulariser",
};

/** Recommandation du moteur de règles, dérivée de la zone exactement comme le
 * fait `decision()` côté API (approbation → accorder, analyse → escalader,
 * rejet → refuser). C'est la référence par rapport à laquelle un avis compte
 * comme écart : l'afficher évite au chef de découvrir l'écart via un 400. */
function reco(zone?: string | null): "accorder" | "escalader" | "refuser" {
  if (zone === "rejet") return "refuser";
  if (zone === "analyse") return "escalader";
  return "accorder";
}

const RECO_LABEL: Record<string, string> = {
  accorder: "Accorder",
  escalader: "Escalader au CIC",
  refuser: "Refuser",
};

/** Avis qui comptent comme un écart à la recommandation, et exigent donc un
 * motif. Miroir de la règle serveur : renvoyer / escalader / valider /
 * conditionner ne sont jamais des écarts ; accorder et refuser le sont dès
 * qu'ils contredisent la reco. `refuser` est de plus toujours envoyé avec
 * override=true, donc toujours motivé. */
function ecart(avis: string, zone?: string | null): boolean {
  if (avis === "refuser") return true;
  if (avis === "accorder") return reco(zone) !== "accorder";
  return false;
}

type Avis = { code: string; libelle: string; classe: string };

const AVIS_CHEF: Avis[] = [
  { code: "valider", libelle: "Valider", classe: "primary" },
  { code: "escalader", libelle: "Escalader CIC", classe: "warn" },
  { code: "renvoyer", libelle: "Renvoyer à l’agent", classe: "ghost" },
  { code: "refuser", libelle: "Refuser", classe: "danger" },
];

const AVIS_CIC: Avis[] = [
  { code: "accorder", libelle: "Accorder", classe: "primary" },
  { code: "conditionner", libelle: "Conditionner", classe: "warn" },
  { code: "refuser", libelle: "Refuser", classe: "danger" },
];

function initials(nomComplet: string): string {
  const parts = nomComplet.trim().split(/\s+/);
  return ((parts[0]?.[0] || "") + (parts[1]?.[0] || parts[0]?.[1] || "")).toUpperCase();
}

/** Une ligne de file = un dossier + sa propre décision. Le motif est porté par
 * la carte et non par la page : un champ de motif partagé par toute la file
 * laissait partir la justification d'un dossier sur le voisin. */
function DossierFile({
  d,
  kind,
  onDecide,
}: {
  d: DemandeResume;
  kind: "chef" | "cic";
  onDecide: (id: number, avis: string, motif: string) => Promise<void>;
}) {
  const [motif, setMotif] = useState("");
  const [choix, setChoix] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const avisDispo = kind === "chef" ? AVIS_CHEF : AVIS_CIC;
  const recommande = reco(d.zone);
  const motifRequis = choix != null && ecart(choix, d.zone);
  const bloque = motifRequis && motif.trim().length === 0;

  async function confirmer() {
    if (!choix || bloque) return;
    setBusy(true);
    try {
      await onDecide(d.id, choix, motif.trim());
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="qcard">
      <div className="qcard-head">
        <div className="dcard-avatar">{initials(d.membre)}</div>
        <div className="dcard-id">
          <div className="dcard-name-row">
            <Link to={`/demandes/${d.id}`}>
              <strong>{d.membre}</strong>
            </Link>
            {d.membre_statut && d.membre_statut !== "actif" && (
              <span className="badge rect bad">Membre {d.membre_statut}</span>
            )}
          </div>
          <span className="muted dcard-code">
            #{d.id}
            {d.code_externe ? ` · ${d.code_externe}` : ""} · {money(d.montant_demande)}
          </span>
        </div>
        <span className={`dcard-score ${zoneClass(d.zone)}`}>{d.score != null ? Math.round(d.score) : "—"}</span>
      </div>

      <div className="qcard-tags">
        {d.zone && <span className={`badge rect ${zoneClass(d.zone)}`}>{ZONE_LABEL[d.zone] || d.zone}</span>}
        {d.message_code && <span className="badge rect">{d.message_code}</span>}
        {d.nb_incidents ? (
          <span className="badge rect bad">
            {d.nb_incidents} incident{d.nb_incidents > 1 ? "s" : ""}
          </span>
        ) : d.bon_historique ? (
          <span className="badge rect">Bon historique</span>
        ) : null}
        <span className="badge rect">{STATUS_LABEL[d.statut] || d.statut}</span>
      </div>

      <p className="qcard-reco">
        Recommandation du moteur : <strong>{RECO_LABEL[recommande]}</strong>
        {d.score == null && <span className="muted"> — dossier non scoré, à analyser avant de signer</span>}
      </p>

      <div className="qcard-actions">
        {avisDispo.map((a) => (
          <button
            key={a.code}
            type="button"
            className={`btn ${a.classe} sm${choix === a.code ? " active" : ""}`}
            aria-pressed={choix === a.code}
            onClick={() => {
              setChoix(choix === a.code ? null : a.code);
              setMotif("");
            }}
          >
            {a.libelle}
          </button>
        ))}
        <Link className="btn ghost sm" to={`/demandes/${d.id}`}>
          Ouvrir le dossier
        </Link>
      </div>

      {choix && (
        <div className="qcard-confirm">
          <label className="field">
            Motif {motifRequis ? <span className="req">— obligatoire (écart à la recommandation)</span> : <span className="muted">— facultatif</span>}
            <input
              value={motif}
              onChange={(e) => setMotif(e.target.value)}
              placeholder={
                motifRequis
                  ? "ex. Garantie insuffisante malgré un score favorable"
                  : "ex. Dossier conforme, pièces complètes"
              }
            />
          </label>
          <div className="actions">
            <button className="btn primary sm" type="button" disabled={busy || bloque} onClick={confirmer}>
              {busy ? "Signature…" : `Confirmer : ${avisDispo.find((a) => a.code === choix)?.libelle}`}
            </button>
            <button className="btn ghost sm" type="button" onClick={() => setChoix(null)}>
              Annuler
            </button>
          </div>
          {bloque && <p className="muted">Sans motif, la décision est refusée par le registre — elle doit rester défendable.</p>}
        </div>
      )}
    </article>
  );
}

export default function Queue({ kind }: { kind: "chef" | "cic" }) {
  const user = getUser();
  const [rows, setRows] = useState<DemandeResume[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [err, setErr] = useState("");
  const [fait, setFait] = useState("");
  const [loading, setLoading] = useState(true);
  const niveau = kind === "chef" ? "chef_agence" : "cic";

  async function load(p = 1, q = search) {
    setErr("");
    setLoading(true);
    try {
      const res = kind === "chef" ? await api.fileChef(p, PAGE, q) : await api.fileCic(p, PAGE, q);
      setRows(res.items);
      setPage(res.page);
      setTotal(res.total);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setSearch("");
    setFait("");
    load(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind]);

  async function decide(id: number, avis: string, motif: string) {
    setErr("");
    setFait("");
    try {
      // `refuser` reste un override explicite : un refus se motive toujours.
      const res = await api.decision(id, {
        niveau,
        avis,
        motif: motif || null,
        override: avis === "refuser",
      });
      const label = STATUS_LABEL[res.statut] || res.statut;
      setFait(
        res.statut === "soumis_cic" && avis === "valider"
          ? `Dossier #${id} validé — hors délégation du Directeur (Chef d’Agence), il part au CIC.`
          : `Dossier #${id} — ${label}.${res.override ? " Écart à la recommandation consigné." : ""}`,
      );
      load(page);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    }
  }

  // Répartition de la file par zone : un chef doit voir d'un coup d'œil ce qui
  // l'attend (et ce qui est encore non scoré) avant d'ouvrir dossier par dossier.
  const parZone = rows.reduce<Record<string, number>>((acc, d) => {
    const z = d.zone || "non_analyse";
    acc[z] = (acc[z] || 0) + 1;
    return acc;
  }, {});
  const engage = rows.reduce((sum, d) => sum + (d.montant_demande || 0), 0);

  return (
    <div className="page">
      <h1>{kind === "chef" ? "File Directeur (Chef d’Agence)" : "File CIC"}</h1>
      <p className="lede">
        {kind === "chef"
          ? "Dossiers soumis par les agents. Le moteur recommande, vous signez."
          : "Dossiers escaladés ou hors délégation du Directeur (Chef d’Agence). Décision finale du comité."}{" "}
        Connecté : {user?.nom}.
      </p>

      {rows.length > 0 && (
        <section className="block dashboard-head">
          <div className="stat-row">
            <div className="stat-tile">
              <span className="muted">En attente</span>
              <strong>{total}</strong>
            </div>
            <div className="stat-tile">
              <span className="muted">Montant engagé (page)</span>
              <strong>{money(engage)}</strong>
            </div>
            {["approbation", "analyse", "rejet", "non_analyse"].map((z) =>
              parZone[z] ? (
                <div className="stat-tile" key={z}>
                  <span className="muted">{ZONE_LABEL[z] || "Non analysé"}</span>
                  <strong className={zoneClass(z)}>{parZone[z]}</strong>
                </div>
              ) : null,
            )}
          </div>
        </section>
      )}

      <PageSearch
        value={search}
        onChange={setSearch}
        onSubmit={() => load(1, search)}
        placeholder="Rechercher un dossier (nom, code membre)…"
      />

      {fait && <Alert kind="success">{fait}</Alert>}
      {err && <Alert kind="error">{err}</Alert>}

      <div className="qlist mt-lg">
        {loading && <Spinner />}
        {!loading && rows.length === 0 && !err && (
          <p className="muted">Aucun dossier en file{search ? " pour cette recherche" : ""}.</p>
        )}
        {!loading &&
          rows.map((d) => <DossierFile key={d.id} d={d} kind={kind} onDecide={decide} />)}
      </div>

      <Pager page={page} pageSize={PAGE} total={total} onPage={load} />
    </div>
  );
}
