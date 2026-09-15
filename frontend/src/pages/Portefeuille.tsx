import { useEffect, useState } from "react";
import {
  api,
  money,
  type AgingOut,
  type AlertePortefeuille,
  type Capabilities,
  type M6Out,
} from "../api/client";
import Spinner from "../components/Spinner";
import Alert from "../components/Alert";
import PageSearch from "../components/PageSearch";
import Pager from "../components/Pager";
import { useApi } from "../hooks/useApi";

const PAGE_SIZE = 30;

type Tab = "overview" | "echeances" | "aging";

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

function Overview({ d, caps, ewAlertes }: { d: M6Out; caps: Capabilities | null; ewAlertes: AlertePortefeuille[] | null }) {
  return (
    <>
      <section className="block dashboard-head">
        <div className="stat-row">
          {d.par.map((p, i) => (
            <div className="stat-tile" key={p.agence_id ?? i}>
              <span className="muted">Agence {p.agence_id ?? "—"} · PAR 30 / PAR 90</span>
              <strong>{p.par30} % <span className="muted" style={{ fontWeight: 400, fontSize: "0.9rem" }}>/ {p.par90} %</span></strong>
            </div>
          ))}
        </div>
      </section>

      <section className="block mt-md">
        <h2>Alertes portefeuille</h2>
        {d.alertes.length === 0 && <p className="muted">Aucune alerte.</p>}
        {d.alertes.map((a, i) => (
          <p key={i}>Membre {a.membre_id} — {a.signal}</p>
        ))}
      </section>

      {caps?.early_warning && (
        <section className="block ml mt-md">
          <span className="ml-tag">Éclairage ML — consultatif, jamais décisionnel</span>
          <h2>Early warning (risque de retard à 30–90 j)</h2>
          {!ewAlertes && <Spinner />}
          {ewAlertes?.length === 0 && <p className="muted">Rien à signaler.</p>}
          {ewAlertes?.map((a, i) => (
            <div className="kv mb-sm" key={i}>
              <span>Membre</span>
              <strong>{a.member_code}</strong>
              <span>Probabilité retard 30–90j</span>
              <strong>{Math.round(a.p_par30_90j * 100)} %</strong>
              <span>Exposition</span>
              <strong>{money(a.exposure)}</strong>
              <span>Signaux</span>
              <span>{a.signals.join(" · ")}</span>
            </div>
          ))}
        </section>
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

  return (
    <section className="block">
      <h2>Échéances du jour — {data.jour}</h2>
      {busy && <Spinner />}
      {!busy && data.items.length === 0 && (
        <p className="muted">Aucune échéance{search ? " pour cette recherche" : " en retard aujourd'hui"}.</p>
      )}
      {!busy && (
        <div className="list">
          {data.items.map((e) => (
            <div className="row" key={e.outstanding_loan_id}>
              <div>
                <strong>{e.member_code}</strong>
                <div className="muted">{money(e.outstanding)} · {e.days_late} j de retard{e.due_on ? ` · échéance ${e.due_on}` : ""}</div>
              </div>
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
        <div className="list">
          {data.buckets.map((b) => (
            <div className="row" key={b.bucket}>
              <div>
                <strong>{BUCKET_LABEL[b.bucket] || b.bucket}</strong>
                <div className="muted">{b.dossiers} dossier{b.dossiers > 1 ? "s" : ""} · {money(b.montant)}</div>
              </div>
              <span className={`badge rect ${bucketTone(b.bucket)}`}>{b.part_pct} %</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

export default function Portefeuille() {
  const { data: d, error, loading } = useApi<M6Out>(() => api.portefeuille(), []);
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [ewAlertes, setEwAlertes] = useState<AlertePortefeuille[] | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.capabilities().then(setCaps).catch(() => undefined);
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
      <p className="lede">PAR calculé depuis les encours — aging, échéances et alertes.</p>

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
          Aging
        </button>
      </div>

      {tab === "echeances" && (
        <PageSearch value={search} onChange={setSearch} placeholder="Rechercher un membre (code)…" />
      )}

      {tab === "overview" && <Overview d={d} caps={caps} ewAlertes={ewAlertes} />}
      {tab === "echeances" && <EcheancesTab search={search} />}
      {tab === "aging" && <AgingTab />}
    </div>
  );
}
