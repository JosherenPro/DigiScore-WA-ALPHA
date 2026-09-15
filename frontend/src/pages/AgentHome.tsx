import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type DemandeResume, type MembreResume } from "../api/client";
import { getUser } from "../auth";
import Pager from "../components/Pager";
import Alert from "../components/Alert";
import Spinner from "../components/Spinner";
import DossierCard from "../components/DossierCard";
import PageSearch from "../components/PageSearch";

const PAGE = 30;

type StatutFilter = "brouillon" | "en_cours" | "historique" | null;

// "en_cours" regroupe les 2 statuts où le dossier a quitté les mains de
// l'agent et attend un avis (chef ou CIC) — chaque carte affiche déjà
// laquelle des deux via son badge de statut (DossierCard), le filtre ne fait
// que restreindre la liste aux deux. "historique" = dossiers déjà décidés
// (accordé, conditionné, refusé, clos) — pas "renvoyé", qui revient chez
// l'agent pour correction, donc pas encore une décision finale.
const STATUT_FILTER_QUERY: Record<Exclude<StatutFilter, null>, string> = {
  brouillon: "brouillon",
  en_cours: "soumis_chef,soumis_cic",
  historique: "accorde,conditionne,refuse,clos",
};

const FILTER_LABEL: Record<Exclude<StatutFilter, null>, string> = {
  brouillon: "brouillons",
  en_cours: "en cours (chef ou CIC)",
  historique: "historique (déjà traités)",
};

export default function AgentHome({ dossiers = false }: { dossiers?: boolean }) {
  const user = getUser();
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

  async function loadDemandes(p: number, activeTab: "mine" | "all", filter: StatutFilter, search: string) {
    setBusy(true);
    setErr("");
    try {
      const res = await api.demandes({
        page: p,
        pageSize: PAGE,
        agentId: activeTab === "mine" ? user?.id : undefined,
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
    api.demandes({ page: 1, pageSize: 1, agentId: user?.id }).then((res) => setMineTotal(res.total)).catch(() => undefined);
    loadDemandes(1, tab, statutFilter, dossierSearch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dossiers, tab, statutFilter]);

  if (dossiers) {
    return (
      <div className="page">
        <div className="tabs">
          <button type="button" className={`tab${tab === "mine" ? " active" : ""}`} onClick={() => setTab("mine")}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6" />
            </svg>
            Mes dossiers {mineTotal != null && <span className="count">{mineTotal}</span>}
          </button>
          <button type="button" className={`tab${tab === "all" ? " active" : ""}`} onClick={() => setTab("all")}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            Base complète {allTotal != null && <span className="count">{allTotal}</span>}
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
        </div>

        <PageSearch
          value={dossierSearch}
          onChange={setDossierSearch}
          onSubmit={() => loadDemandes(1, tab, statutFilter, dossierSearch)}
          placeholder="Rechercher un dossier (nom, code membre)…"
        />

        <p className="section-label">
          {tab === "mine" ? "Dossiers qui me sont attribués" : "Tous les dossiers"}
          {statutFilter ? ` — ${FILTER_LABEL[statutFilter]}` : ""}
          <span>{total} résultat{total > 1 ? "s" : ""}</span>
        </p>
        {err && <Alert kind="error">{err}</Alert>}
        {busy && <Spinner />}
        {!busy && (
          <div className="dcards">
            {rows.map((d) => (
              <DossierCard key={d.id} d={d} currentUserId={user?.id} />
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
          <Link className="row" key={m.id} to={`/membres/${m.id}`}>
            <div>
              <strong>
                {m.prenom} {m.nom}
              </strong>
              <div className="muted">
                {m.code_externe} · adhésion {m.date_adhesion}
              </div>
            </div>
            <span className={`badge ${m.statut === "actif" ? "ok" : "bad"}`}>{m.statut}</span>
          </Link>
        ))}
      </div>
      {busy && <Spinner />}
      {!busy && membres.length === 0 && !err && <p className="muted">Aucun membre sur cette page.</p>}
      <Pager page={page} pageSize={PAGE} total={total} onPage={(p) => loadMembres(q, p)} />
    </div>
  );
}
