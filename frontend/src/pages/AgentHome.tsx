import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, money, type DemandeResume, type MembreResume } from "../api/client";
import { getUser } from "../auth";
import Pager from "../components/Pager";
import Alert from "../components/Alert";
import Spinner from "../components/Spinner";
import DossierCard from "../components/DossierCard";
import PageSearch from "../components/PageSearch";

const PAGE = 30;

// Au-dela de ce nombre de dossiers, le lot d'un client s'ouvre replie.
const PLIER_AU_DELA = 6;

type StatutFilter = "brouillon" | "a_corriger" | "en_cours" | "historique" | null;

// "en_cours" regroupe les 2 statuts où le dossier a quitté les mains de
// l'agent et attend un avis (chef ou CIC) — chaque carte affiche déjà
// laquelle des deux via son badge de statut (DossierCard), le filtre ne fait
// que restreindre la liste aux deux. "historique" = dossiers déjà décidés
// (accordé, conditionné, refusé, clos) — pas "renvoyé", qui revient chez
// l'agent pour correction, donc pas encore une décision finale.
const STATUT_FILTER_QUERY: Record<Exclude<StatutFilter, null>, string> = {
  brouillon: "brouillon",
  // "renvoye" n'entrait dans aucun filtre : les dossiers que le chef renvoie a
  // l'agent, donc exactement ceux qui attendent son travail, etaient noyes dans
  // la liste complete.
  a_corriger: "renvoye",
  en_cours: "soumis_chef,soumis_cic",
  historique: "accorde,conditionne,refuse,clos",
};

const FILTER_LABEL: Record<Exclude<StatutFilter, null>, string> = {
  brouillon: "brouillons",
  a_corriger: "à corriger (renvoyés par le chef)",
  en_cours: "en cours (chef ou CIC)",
  historique: "historique (déjà traités)",
};

type LotClient = {
  membreId: number;
  nom: string;
  code?: string | null;
  statut?: string | null;
  dossiers: DemandeResume[];
  montant: number;
};

/** Regroupe les dossiers d'une page par membre.
 *
 * A plat, un client qui a 55 demandes remplit tout l'ecran de cartes
 * identiques et noie les autres clients. L'ordre d'arrivee de l'API est
 * conserve : le premier dossier d'un membre fixe la position de son lot, on ne
 * rebat pas le tri (le plus recent d'abord) au profit d'un ordre alphabetique.
 */
function grouperParClient(rows: DemandeResume[]): LotClient[] {
  const lots = new Map<number, LotClient>();
  for (const d of rows) {
    let lot = lots.get(d.membre_id);
    if (!lot) {
      lot = {
        membreId: d.membre_id,
        nom: d.membre,
        code: d.code_externe,
        statut: d.membre_statut,
        dossiers: [],
        montant: 0,
      };
      lots.set(d.membre_id, lot);
    }
    lot.dossiers.push(d);
    lot.montant += d.montant_demande || 0;
  }
  return [...lots.values()];
}

/** Un client et ses dossiers. Replie au-dela de PLIER_AU_DELA dossiers :
 * un lot de 55 cartes repousse tous les autres clients hors de l'ecran. */
function LotDossiers({ lot, currentUserId }: { lot: LotClient; currentUserId?: number }) {
  const [ouvert, setOuvert] = useState(lot.dossiers.length <= PLIER_AU_DELA);
  const actif = lot.statut === "actif";
  return (
    <section className="lot">
      <div className="lot-head">
        <button
          type="button"
          className="lot-toggle"
          aria-expanded={ouvert}
          onClick={() => setOuvert((v) => !v)}
        >
          <span className={`lot-chevron${ouvert ? " open" : ""}`} aria-hidden="true">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </span>
          <span className="lot-id">
            <strong>{lot.nom}</strong>
            <span className="muted">
              {lot.code || `membre #${lot.membreId}`} · {lot.dossiers.length} dossier
              {lot.dossiers.length > 1 ? "s" : ""} · {money(lot.montant)} demandés
            </span>
          </span>
        </button>
        <div className="lot-actions">
          <Link className="btn ghost sm" to={`/membres/${lot.membreId}`}>
            Fiche
          </Link>
          {actif && (
            <Link className="btn primary sm" to={`/membres/${lot.membreId}/demande`}>
              Nouveau crédit
            </Link>
          )}
        </div>
      </div>
      {ouvert && (
        <div className="dcards lot-cards">
          {lot.dossiers.map((d) => (
            <DossierCard key={d.id} d={d} currentUserId={currentUserId} />
          ))}
        </div>
      )}
    </section>
  );
}

export default function AgentHome({ dossiers = false }: { dossiers?: boolean }) {
  const user = getUser();
  const estAgent = user?.role === "agent";
  const [params] = useSearchParams();
  const initialQ = params.get("q") || "";
  const [q, setQ] = useState(initialQ);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [membres, setMembres] = useState<MembreResume[]>([]);
  const [rows, setRows] = useState<DemandeResume[]>([]);
  const [tab, setTab] = useState<"mine" | "all">("mine");
  const [mineTotal, setMineTotal] = useState<number | null>(null);
  const [allTotal, setAllTotal] = useState<number | null>(null);
  const [statutFilter, setStatutFilter] = useState<StatutFilter>(null);
  const [dossierSearch, setDossierSearch] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadMembres(query: string, p: number) {
    setBusy(true);
    setErr("");
    try {
      const res = await api.membres(query, p, PAGE);
      setMembres(res.items);
      setTotal(res.total);
      setPage(res.page);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function loadDemandes(p: number, _activeTab: "mine" | "all", filter: StatutFilter, search: string) {
    setBusy(true);
    setErr("");
    try {
      const res = await api.demandes({
        page: p,
        pageSize: PAGE,
        // "Mes dossiers" comme "Base complète" : tous les clients sont
        // affichés. Restreindre aux seules demandes de l'agent connecté
        // masquait des clients qu'il dessert aussi (dossiers pris par un
        // collègue, ou demandes en cours de saisie sur un autre appareil).
        agentId: undefined,
        statut: filter ? STATUT_FILTER_QUERY[filter] : undefined,
        q: search || undefined,
      });
      setRows(res.items);
      setTotal(res.total);
      setPage(res.page);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!dossiers) {
      // ?q= vient de la barre de recherche globale (présente sur toutes les
      // pages) : on lance directement la recherche au lieu de réafficher les
      // premiers membres de la base.
      loadMembres(initialQ, 1);
      return;
    }
    // Compteurs des onglets : toujours le total réel (non filtré), indépendant
    // du filtre "Brouillons" — sinon les chiffres sur les pastilles mentiraient.
    api.demandes({ page: 1, pageSize: 1 }).then((res) => setAllTotal(res.total)).catch(() => undefined);
    api.demandes({ page: 1, pageSize: 1 }).then((res) => setMineTotal(res.total)).catch(() => undefined);
    loadDemandes(1, tab, statutFilter, dossierSearch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dossiers, tab, statutFilter]);

  if (dossiers) {
    return (
      <div className="page">
        <div className="tabs">
          {estAgent && (
            <button type="button" className={`tab${tab === "mine" ? " active" : ""}`} onClick={() => setTab("mine")}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <path d="M14 2v6h6" />
              </svg>
              Mes dossiers {mineTotal != null && <span className="count">{mineTotal}</span>}
            </button>
          )}
          <button type="button" className={`tab${tab === "all" ? " active" : ""}`} onClick={() => setTab("all")}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            {estAgent ? "Base complète" : "Tous les dossiers"} {allTotal != null && <span className="count">{allTotal}</span>}
          </button>
          <button
            type="button"
            className={`tab filter-chip${statutFilter === "brouillon" ? " active" : ""}`}
            onClick={() => setStatutFilter((v) => (v === "brouillon" ? null : "brouillon"))}
            aria-pressed={statutFilter === "brouillon"}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6" />
              <path d="M9 15h6M9 11h3" />
            </svg>
            Brouillons uniquement
          </button>
          <button
            type="button"
            className={`tab filter-chip${statutFilter === "a_corriger" ? " active" : ""}`}
            onClick={() => setStatutFilter((v) => (v === "a_corriger" ? null : "a_corriger"))}
            aria-pressed={statutFilter === "a_corriger"}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M3 7v6h6" />
              <path d="M3.51 13a9 9 0 1 0 2.13-9.36L3 7" />
            </svg>
            À corriger
          </button>
          <button
            type="button"
            className={`tab filter-chip${statutFilter === "en_cours" ? " active" : ""}`}
            onClick={() => setStatutFilter((v) => (v === "en_cours" ? null : "en_cours"))}
            aria-pressed={statutFilter === "en_cours"}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 3" />
            </svg>
            En cours de traitement
          </button>
          <button
            type="button"
            className={`tab filter-chip${statutFilter === "historique" ? " active" : ""}`}
            onClick={() => setStatutFilter((v) => (v === "historique" ? null : "historique"))}
            aria-pressed={statutFilter === "historique"}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <rect x="3" y="4" width="18" height="4" rx="1" />
              <path d="M5 8v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8" />
              <path d="M10 13h4" />
            </svg>
            Historique (traités)
          </button>
          {estAgent && (
          <Link className="visitor-card" to="/agent" style={{ marginLeft: "auto" }}>
            <span className="avatar-dot" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7" />
                <path d="m21 21-4.3-4.3" />
              </svg>
            </span>
            <span>
              <strong style={{ display: "block", fontSize: "0.9rem" }}>Rechercher un membre</strong>
              <span className="muted" style={{ fontSize: "0.8rem" }}>Nouvelle demande de crédit</span>
            </span>
          </Link>
          )}
        </div>

        <PageSearch
          value={dossierSearch}
          onChange={setDossierSearch}
          onSubmit={() => loadDemandes(1, tab, statutFilter, dossierSearch)}
          placeholder="Rechercher un dossier (nom, code membre)…"
        />

        <p className="section-label">
          {estAgent && tab === "mine" ? "Tous les clients" : "Tous les dossiers"}
          {statutFilter ? ` — ${FILTER_LABEL[statutFilter]}` : ""}
          <span>{total} résultat{total > 1 ? "s" : ""}</span>
        </p>
        {err && <Alert kind="error">{err}</Alert>}
        {busy && <Spinner />}
        {!busy && (
          <div className="lots">
            {grouperParClient(rows).map((lot) => (
              <LotDossiers key={lot.membreId} lot={lot} currentUserId={user?.id} />
            ))}
          </div>
        )}
        {!busy && rows.length === 0 && !err && (
          <p className="muted">
            Aucun dossier{statutFilter ? ` — ${FILTER_LABEL[statutFilter]}` : ""}.
          </p>
        )}
        <Pager page={page} pageSize={PAGE} total={total} onPage={(p) => loadDemandes(p, tab, statutFilter, dossierSearch)} />
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Membre d’abord</h1>
      <p className="lede">Code MEM-001, nom, ou n° de compte. Pas de demande sans compte actif. Ne charge pas 120 000 lignes d’un coup.</p>
      <form
        className="search-row"
        onSubmit={(e) => {
          e.preventDefault();
          loadMembres(q, 1);
        }}
      >
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="MEM-001, Mensah, CPT-001, VOL-…" />
        <button className="btn" type="submit" disabled={busy}>
          Chercher
        </button>
      </form>
      {err && <Alert kind="error">{err}</Alert>}
      <div className="list">
        {membres.map((m) => (
          // Ligne non cliquable en bloc : elle porte deux destinations
          // distinctes (consulter la fiche / ouvrir une demande), et un lien
          // imbrique dans un lien n'est pas du HTML valide.
          <div className="row" key={m.id}>
            <div>
              <Link to={`/membres/${m.id}`}>
                <strong>
                  {m.prenom} {m.nom}
                </strong>
              </Link>
              <div className="muted">
                {m.code_externe} · adhésion {m.date_adhesion}
              </div>
            </div>
            <span className={`badge ${m.statut === "actif" ? "ok" : "bad"}`}>{m.statut}</span>
            {/* Raccourci direct : l'agent cherche un membre precisement pour
                lui monter un credit. Le faire passer par la fiche puis
                descendre en bas de page ajoutait deux etapes inutiles. */}
            {m.statut === "actif" ? (
              <Link className="btn primary sm" to={`/membres/${m.id}/demande`}>
                Nouvelle demande
              </Link>
            ) : (
              <span className="muted" title="Compte gelé ou radié : aucune demande possible.">
                demande impossible
              </span>
            )}
          </div>
        ))}
      </div>
      {busy && <Spinner />}
      {!busy && membres.length === 0 && !err && <p className="muted">Aucun membre sur cette page.</p>}
      <Pager page={page} pageSize={PAGE} total={total} onPage={(p) => loadMembres(q, p)} />
    </div>
  );
}
