import { useEffect, useState } from "react";
import {
  api,
  money,
  type Agence,
  type AgingOut,
  type AlertePortefeuille,
  type Capabilities,
  type M6Out,
  type SignalFucec,
} from "../api/client";
import { getUser } from "../auth";
import Spinner from "../components/Spinner";
import Alert from "../components/Alert";
import PageSearch from "../components/PageSearch";
import MlSection from "../components/MlSection";
import EarlyWarning from "../components/EarlyWarning";
import MembreLabel from "../components/MembreLabel";
import Pager from "../components/Pager";
import { useApi } from "../hooks/useApi";

const PAGE_SIZE = 30;

type Tab = "overview" | "echeances" | "aging" | "signaux";

const BUCKET_LABEL: Record<string, string> = {
  courant: "Courant",
  "1-7": "1 à 7 jours",
  "8-30": "8 à 30 jours",
  "31-90": "31 à 90 jours",
  ">90": "Plus de 90 jours",
};

function bucketTone(bucket: string): string {
  if (bucket === "courant") return "ok";
  if (bucket === "1-7" || bucket === "8-30") return "warn";
  return "bad";
}

function prioriteTone(p?: string | null): string {
  if (p === "P1") return "bad";
  if (p === "P2") return "warn";
  return "";
}

function parTone(label?: string | null): string {
  if (label === "critique") return "bad";
  if (label === "vigilance") return "warn";
  return "ok";
}

const FAMILLE_LABEL: Record<string, string> = {
  activite: "Activité",
  comportement: "Comportement",
  environnement: "Environnement",
};

/** Referentiel FUCEC (GET /vision/signaux) : la grille terrain de la Section 5.
 * Statique, mais c'est la legende qui rend lisibles les signaux bruts de M6/M7 —
 * un agent qui ne sait pas quoi regarder ne remonte rien. */
function SignauxTab() {
  const { data, error, loading } = useApi(() => api.signaux(), []);
  if (error) return <Alert kind="error">{error}</Alert>;
  if (loading || !data) return <Spinner />;

  const familles = data.items.reduce<Record<string, SignalFucec[]>>((acc, sig) => {
    (acc[sig.famille] ||= []).push(sig);
    return acc;
  }, {});

  return (
    <>
      <p className="lede">
        Grille de lecture terrain — ce qu’un agent doit savoir repérer avant que le retard n’apparaisse
        dans le PAR. <span className="muted">Référentiel {data.model_version}.</span>
      </p>
      <div className="grid two">
        {Object.entries(familles).map(([famille, items]) => (
          <section className="block" key={famille}>
            <h2>{FAMILLE_LABEL[famille] || famille}</h2>
            <div className="list">
              {items.map((sig) => (
                <div className="row" key={sig.code}>
                  <div>
                    <strong>{sig.libelle}</strong>
                    <div className="muted">{sig.code}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </>
  );
}

function Overview({
  d,
  caps,
  ewAlertes,
  agences,
  onRecalcul,
}: {
  d: M6Out;
  caps: Capabilities | null;
  ewAlertes: AlertePortefeuille[] | null;
  agences: Agence[];
  onRecalcul: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [recalcul, setRecalcul] = useState("");
  const [err, setErr] = useState("");
  const role = getUser()?.role;
  // Le recalcul PAR ecrit un snapshot : reserve aux profils de revue, comme cote API.
  const peutRecalculer = role === "chef_agence" || role === "cic";
  const nomAgence = (id?: number | null) =>
    agences.find((a) => a.id === id)?.nom || (id != null ? `Agence ${id}` : "Toutes agences");

  async function recalculer() {
    setBusy(true);
    setErr("");
    try {
      await onRecalcul();
      setRecalcul(`PAR recalculé à ${new Date().toLocaleTimeString("fr-FR")}.`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {d.par.map((p, i) => (
        <section className="block dashboard-head" key={p.agence_id ?? i}>
          <div className="row">
            <div>
              <h2 style={{ margin: 0 }}>{nomAgence(p.agence_id)}</h2>
              {d.as_of && <div className="muted">Arrêté au {d.as_of}</div>}
            </div>
            <span className={`badge rect ${parTone(p.label)}`}>{p.label || "—"}</span>
          </div>
          <div className="stat-row mt-sm">
            <div className="stat-tile">
              <span className="muted" title="Part de l’encours brut avec au moins 1 jour de retard">PAR 1</span>
              <strong>{p.par1} %</strong>
            </div>
            <div className="stat-tile">
              <span className="muted" title="Part de l’encours brut avec au moins 30 jours de retard">PAR 30</span>
              <strong>{p.par30} %</strong>
            </div>
            <div className="stat-tile">
              <span className="muted" title="Part de l’encours brut avec au moins 90 jours de retard">PAR 90</span>
              <strong>{p.par90} %</strong>
            </div>
            {p.encours_brut != null && (
              <div className="stat-tile">
                <span className="muted" title="Total des crédits décaissés non soldés">Encours brut</span>
                <strong>{money(p.encours_brut)}</strong>
              </div>
            )}
          </div>
        </section>
      ))}

      {peutRecalculer && (
        <div className="actions">
          <button className="btn ghost sm" type="button" disabled={busy} onClick={recalculer}>
            {busy ? "Recalcul…" : "Recalculer le PAR"}
          </button>
          {recalcul && <span className="muted">{recalcul}</span>}
        </div>
      )}
      {err && <Alert kind="error">{err}</Alert>}

      <section className="block mt-md">
        <h2>Alertes portefeuille <span className="muted">({d.alertes.length})</span></h2>
        <p className="hint">P1 = à traiter en priorité (gros encours, retard marqué) · P2 = à surveiller.</p>
        {d.alertes.length === 0 && <p className="muted">Aucune alerte.</p>}
        <div className="list">
          {d.alertes.map((a, i) => (
            <div className="row" key={`${a.membre_id}-${i}`}>
              <div>
                <MembreLabel nom={a.member_name} code={a.member_code} membreId={a.membre_id} />
                <div className="muted">
                  {a.signal}
                  {a.days_late != null ? ` · ${a.days_late} j de retard` : ""}
                </div>
              </div>
              {a.priorite && <span className={`badge rect ${prioriteTone(a.priorite)}`}>{a.priorite}</span>}
            </div>
          ))}
        </div>
      </section>

      {caps?.early_warning && (
        <MlSection
          titre="Early warning — risque de retard à 30–90 j"
          resume={
            ewAlertes
              ? `${ewAlertes.length} membre${ewAlertes.length > 1 ? "s" : ""} à surveiller`
              : "chargement…"
          }
          className="mt-md"
        >
          <EarlyWarning alertes={ewAlertes} />
        </MlSection>
      )}
    </>
  );
}

function EcheancesTab({ search }: { search: string }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Awaited<ReturnType<typeof api.echeances>> | null>(null);
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    setBusy(true);
    setErr("");
    api
      .echeances(page, PAGE_SIZE, search)
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "Erreur"))
      .finally(() => setBusy(false));
  }, [page, search]);

  // La recherche repart toujours page 1 (sinon "page 3" d'une recherche
  // precedente peut ne plus exister pour la nouvelle).
  useEffect(() => {
    setPage(1);
  }, [search]);

  if (err) return <Alert kind="error">{err}</Alert>;
  if (busy && !data) return <Spinner />;
  if (!data) return null;

  // Montant de la page courante : le total global n'est pas renvoye par l'API,
  // on annonce donc explicitement ce que couvre la somme plutot que de laisser
  // croire qu'elle porte sur les 2 000 echeances.
  const montantPage = data.items.reduce((sum, e) => sum + e.outstanding, 0);

  return (
    <section className="block">
      <h2>Échéances du jour — {data.jour}</h2>
      <div className="stat-row">
        <div className="stat-tile">
          <span className="muted">Échéances en retard</span>
          <strong>{data.total}</strong>
        </div>
        <div className="stat-tile">
          <span className="muted">Encours sur cette page</span>
          <strong>{money(montantPage)}</strong>
        </div>
      </div>
      {busy && <Spinner />}
      {!busy && data.items.length === 0 && (
        <p className="muted">Aucune échéance{search ? " pour cette recherche" : " en retard aujourd'hui"}.</p>
      )}
      {!busy && (
        <div className="list mt-sm">
          {data.items.map((e) => (
            <div className="row" key={e.outstanding_loan_id}>
              <div>
                <MembreLabel nom={e.member_name} code={e.member_code} membreId={e.member_id} />
                <div className="muted">
                  {money(e.outstanding)} · {e.days_late} j de retard
                  {e.due_on ? ` · échéance ${e.due_on}` : ""}
                  {e.responsable ? ` · ${e.responsable}` : ""}
                </div>
              </div>
              {e.niveau != null && <span className="badge rect">N{e.niveau}</span>}
              <span className={`badge rect ${bucketTone(e.bucket)}`}>{BUCKET_LABEL[e.bucket] || e.bucket}</span>
            </div>
          ))}
        </div>
      )}
      <Pager page={data.page} pageSize={data.page_size} total={data.total} onPage={setPage} />
    </section>
  );
}

function AgingTab() {
  const { data, error, loading } = useApi<AgingOut>(() => api.aging(), []);
  if (error) return <Alert kind="error">{error}</Alert>;
  if (loading || !data) return <Spinner />;
  return (
    <>
      <section className="block dashboard-head">
        <div className="stat-row">
          <div className="stat-tile">
            <span className="muted">Encours brut</span>
            <strong>{money(data.encours_brut)}</strong>
          </div>
          <div className="stat-tile">
            <span className="muted">PAR 30</span>
            <strong>{data.par30} %</strong>
          </div>
          <div className="stat-tile">
            <span className="muted">PAR 90</span>
            <strong>{data.par90} %</strong>
          </div>
        </div>
      </section>
      <section className="block mt-md">
        <h2>Répartition par ancienneté de retard</h2>
        <p className="ledger-note">
          La part de chaque tranche se compare à l’œil : un tableau de pourcentages oblige à faire le
          calcul de tête.
        </p>
        <div className="revue-aging">
          {data.buckets.map((b) => (
            <div className="revue-aging-row" key={b.bucket}>
              <span className="revue-aging-label">{BUCKET_LABEL[b.bucket] || b.bucket}</span>
              <span className="revue-aging-track">
                <span
                  className={`revue-aging-fill ${bucketTone(b.bucket)}`}
                  style={{ width: `${Math.max(b.part_pct, 0.5)}%` }}
                />
              </span>
              <span className="revue-aging-value">
                {b.part_pct} %{" "}
                <span className="muted">
                  · {money(b.montant)} · {b.dossiers} dossier{b.dossiers > 1 ? "s" : ""}
                </span>
              </span>
            </div>
          ))}
        </div>
        {/* Ce qui est deja hors du courant : le chiffre que le chef doit retenir. */}
        {(() => {
          const risque = data.buckets.filter((b) => b.bucket !== "courant");
          const montant = risque.reduce((sum, b) => sum + b.montant, 0);
          const dossiers = risque.reduce((sum, b) => sum + b.dossiers, 0);
          if (dossiers === 0) return null;
          return (
            <p className="msg plafonne mt-md">
              <strong>{money(montant)}</strong> en retard sur {dossiers} dossier{dossiers > 1 ? "s" : ""}
              {data.encours_brut > 0
                ? ` — ${Math.round((montant / data.encours_brut) * 100)} % de l’encours brut.`
                : "."}
            </p>
          );
        })()}
      </section>
    </>
  );
}

export default function Portefeuille() {
  const { data: d, error, loading, reload } = useApi<M6Out>(() => api.portefeuille(), []);
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [ewAlertes, setEwAlertes] = useState<AlertePortefeuille[] | null>(null);
  const [agences, setAgences] = useState<Agence[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.capabilities().then(setCaps).catch(() => undefined);
    // Nom d'agence plutot qu'un id nu dans les tuiles PAR.
    api.agences().then(setAgences).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!caps?.early_warning) return;
    api.alertesPortefeuille().then((r) => setEwAlertes(r.items)).catch(() => undefined);
  }, [caps]);

  if (error) return <div className="page"><Alert kind="error">{error}</Alert></div>;
  if (loading || !d) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <h1>Suivi portefeuille</h1>
      <p className="lede">
        Le PAR mesure la part de l’encours en retard : <strong>PAR 1</strong> ≥ 1 jour, <strong>PAR 30</strong>
        {" "}≥ 30 jours, <strong>PAR 90</strong> ≥ 90 jours. Les onglets détaillent les échéances du jour,
        l’ancienneté des retards et les signaux d’alerte terrain.
      </p>

      <div className="tabs">
        <button type="button" className={`tab${tab === "overview" ? " active" : ""}`} onClick={() => setTab("overview")}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <rect x="3" y="3" width="7" height="9" rx="1" />
            <rect x="14" y="3" width="7" height="5" rx="1" />
            <rect x="14" y="12" width="7" height="9" rx="1" />
            <rect x="3" y="16" width="7" height="5" rx="1" />
          </svg>
          Vue d’ensemble
        </button>
        <button type="button" className={`tab${tab === "echeances" ? " active" : ""}`} onClick={() => setTab("echeances")}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <rect x="3" y="4" width="18" height="17" rx="2" />
            <path d="M3 9h18M8 2v4M16 2v4" />
          </svg>
          Échéances du jour
        </button>
        <button type="button" className={`tab${tab === "aging" ? " active" : ""}`} onClick={() => setTab("aging")}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M4 20V10M11 20V4M18 20v-7" />
          </svg>
          Ancienneté des retards
        </button>
        <button type="button" className={`tab${tab === "signaux" ? " active" : ""}`} onClick={() => setTab("signaux")}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <path d="M12 9v4M12 17h.01" />
          </svg>
          Signaux d’alerte
        </button>
      </div>

      {tab === "echeances" && (
        <PageSearch value={search} onChange={setSearch} placeholder="Rechercher un membre (nom ou code)…" />
      )}

      {tab === "overview" && (
        <Overview
          d={d}
          caps={caps}
          ewAlertes={ewAlertes}
          agences={agences}
          onRecalcul={async () => {
            await api.recalculPar();
            reload();
          }}
        />
      )}
      {tab === "echeances" && <EcheancesTab search={search} />}
      {tab === "aging" && <AgingTab />}
      {tab === "signaux" && <SignauxTab />}
    </div>
  );
}
