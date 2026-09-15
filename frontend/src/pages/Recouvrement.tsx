import { useEffect, useState } from "react";
import {
  api,
  money,
  type ActionRecouvrementIn,
  type DossierRecouvrement,
  type JournalEntry,
  type M7Out,
} from "../api/client";
import Spinner from "../components/Spinner";
import Alert from "../components/Alert";
import PageSearch from "../components/PageSearch";
import Pager from "../components/Pager";
import { useApi } from "../hooks/useApi";

type Tab = "niveaux" | "dossiers";
const PAGE_SIZE = 30;

// Miroir des 4 niveaux définis côté backend (portfolio_service.NIVEAUX_RECOUVREMENT)
// — référentiel métier fixe, pas une donnée à aller chercher à chaque affichage.
const NIVEAU_INFO: Record<number, { libelle: string; periode: string; responsable: string; actions: string; tone: string }> = {
  1: { libelle: "Relance immédiate", periode: "J+1 à J+7", responsable: "Chargé de crédit", actions: "Appel J+1, visite J+3, documentation SIG", tone: "" },
  2: { libelle: "Relance renforcée", periode: "J+8 à J+30", responsable: "Chargé de crédit + Superviseur", actions: "Visite domicile, caution contactée, mise en demeure", tone: "warn" },
  3: { libelle: "Recouvrement intensif", periode: "J+31 à J+90", responsable: "Superviseur + Chef d’agence", actions: "Convocation formelle, échéancier écrit, garanties activées", tone: "bad" },
  4: { libelle: "Contentieux", periode: "> J+90", responsable: "Direction / Juridique", actions: "Huissier, réalisation des garanties, action judiciaire", tone: "bad" },
};

const ACTION_TYPES = [
  { value: "appel", label: "Appel téléphonique" },
  { value: "visite", label: "Visite terrain" },
  { value: "courrier", label: "Courrier / lettre" },
  { value: "mise_en_demeure", label: "Mise en demeure" },
  { value: "promesse", label: "Promesse de paiement" },
  { value: "huissier", label: "Huissier / contentieux" },
];

function prioriteTone(p: string): string {
  if (p === "P1") return "bad";
  if (p === "P2") return "warn";
  if (p === "S") return "ok";
  return "";
}

function NiveauxTab({ d }: { d: M7Out }) {
  const counts: Record<number, number> = {};
  d.dossiers.forEach((x) => { counts[x.niveau] = (counts[x.niveau] || 0) + 1; });
  return (
    <div className="zone-tiles">
      {[1, 2, 3, 4].map((n) => (
        <div className={`zone-tile ${NIVEAU_INFO[n].tone}`} key={n}>
          <strong>{counts[n] || 0}</strong>
          <span>Niveau {n} — {NIVEAU_INFO[n].libelle}</span>
          <p className="muted mt-sm" style={{ fontSize: "0.78rem", margin: "0.4rem 0 0" }}>
            {NIVEAU_INFO[n].periode} · {NIVEAU_INFO[n].responsable}
            <br />
            {NIVEAU_INFO[n].actions}
          </p>
        </div>
      ))}
    </div>
  );
}

/** Consigne une action de recouvrement — POST /vision/recouvrement/{id}/actions,
 * qui renvoie le journal complet à jour (pas besoin d'un 2e appel pour le relire). */
function ActionForm({ dossier, onDone }: { dossier: DossierRecouvrement; onDone: (journal: JournalEntry[]) => void }) {
  const [actionType, setActionType] = useState(ACTION_TYPES[0].value);
  const [note, setNote] = useState("");
  const [montant, setMontant] = useState(0);
  const [promiseOn, setPromiseOn] = useState("");
  const [nextOn, setNextOn] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit() {
    setBusy(true);
    setErr("");
    try {
      const body: ActionRecouvrementIn = {
        action_type: actionType,
        note: note || undefined,
        amount_recovered: montant || 0,
        promise_on: promiseOn || undefined,
        next_on: nextOn || undefined,
      };
      const out = await api.logActionRecouvrement(dossier.case_id, body);
      onDone(out.journal);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="visite-form">
      <div className="grid two">
        <label className="field">
          Type d’action
          <select value={actionType} onChange={(e) => setActionType(e.target.value)}>
            {ACTION_TYPES.map((a) => (
              <option key={a.value} value={a.value}>{a.label}</option>
            ))}
          </select>
        </label>
        <label className="field">
          Montant récupéré (FCFA)
          <input type="number" min={0} value={montant || ""} placeholder="0" onChange={(e) => setMontant(Number(e.target.value))} />
        </label>
        <label className="field">
          Promesse de paiement (date)
          <input type="date" value={promiseOn} onChange={(e) => setPromiseOn(e.target.value)} />
        </label>
        <label className="field">
          Prochaine relance
          <input type="date" value={nextOn} onChange={(e) => setNextOn(e.target.value)} />
        </label>
      </div>
      <label className="field mt-sm">
        Note
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="ex. Client injoignable, relancer par le fils…" />
      </label>
      {err && <Alert kind="error">{err}</Alert>}
      <div className="actions">
        <button className="btn primary sm" type="button" disabled={busy} onClick={submit}>
          {busy ? "Enregistrement…" : "Consigner l’action"}
        </button>
      </div>
    </div>
  );
}

function DossiersTab({ search }: { search: string }) {
  const [niveau, setNiveau] = useState<number | null>(null);
  const [priorite, setPriorite] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: DossierRecouvrement[]; page: number; page_size: number; total: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [openCase, setOpenCase] = useState<number | null>(null);
  const [journals, setJournals] = useState<Record<number, JournalEntry[]>>({});

  useEffect(() => {
    setBusy(true);
    setErr("");
    api
      .dossiersRecouvrement({ niveau: niveau ?? undefined, priorite: priorite ?? undefined, q: search, page, pageSize: PAGE_SIZE })
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "Erreur"))
      .finally(() => setBusy(false));
  }, [niveau, priorite, search, page]);

  // Changer un filtre ou la recherche repart toujours page 1.
  useEffect(() => {
    setPage(1);
  }, [niveau, priorite, search]);

  const items = data?.items || [];

  return (
    <>
      <div className="tabs">
        {[null, 1, 2, 3, 4].map((n) => (
          <button
            key={n ?? "all"}
            type="button"
            className={`tab filter-chip${niveau === n ? " active" : ""}`}
            onClick={() => setNiveau(n)}
          >
            {n === null ? "Tous niveaux" : `Niveau ${n}`}
          </button>
        ))}
      </div>
      <div className="tabs mt-sm">
        {[null, "P1", "P2", "P3", "S"].map((p) => (
          <button
            key={p ?? "allp"}
            type="button"
            className={`tab filter-chip${priorite === p ? " active" : ""}`}
            onClick={() => setPriorite(p)}
          >
            {p === null ? "Toutes priorités" : p}
          </button>
        ))}
      </div>

      {err && <Alert kind="error">{err}</Alert>}
      {busy && <Spinner />}
      {!busy && items.length === 0 && !err && <p className="muted">Aucun dossier{search ? " pour cette recherche" : ""}.</p>}

      <div className="list">
        {items.map((it) => (
          <div className="visite-card" key={it.case_id}>
            <div className="visite-row">
              <div>
                <strong>{it.member_code}</strong>
                <div className="muted">
                  {money(it.outstanding)} · {it.days_late} j de retard
                  {it.next_on ? ` · prochaine relance ${it.next_on}` : ""}
                  {it.recovered_amount > 0 ? ` · ${money(it.recovered_amount)} déjà récupéré` : ""}
                </div>
              </div>
              <span className="badge rect">Niveau {it.niveau}</span>
              <span className={`badge rect ${prioriteTone(it.priorite)}`}>{it.priorite}</span>
              <button
                className="btn ghost sm"
                type="button"
                onClick={() => setOpenCase(openCase === it.case_id ? null : it.case_id)}
              >
                {openCase === it.case_id ? "Fermer" : "Consigner une action"}
              </button>
            </div>
            {openCase === it.case_id && (
              <ActionForm
                dossier={it}
                onDone={(journal) => {
                  setOpenCase(null);
                  setJournals((j) => ({ ...j, [it.case_id]: journal }));
                }}
              />
            )}
            {journals[it.case_id] && journals[it.case_id].length > 0 && (
              <div className="mt-sm">
                <p className="hint">Journal du dossier</p>
                {journals[it.case_id].map((j, i) => (
                  <div className="muted" key={i} style={{ fontSize: "0.85rem" }}>
                    {j.date} · {j.type}
                    {j.montant ? ` · ${money(j.montant)}` : ""}
                    {j.note ? ` — ${j.note}` : ""}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {data && <Pager page={data.page} pageSize={data.page_size} total={data.total} onPage={setPage} />}
    </>
  );
}

export default function Recouvrement() {
  const { data: d, error, loading } = useApi<M7Out>(() => api.recouvrement(), []);
  const [tab, setTab] = useState<Tab>("niveaux");
  const [search, setSearch] = useState("");

  if (error) return <div className="page"><Alert kind="error">{error}</Alert></div>;
  if (loading || !d) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <h1>Recouvrement</h1>
      <p className="lede">4 niveaux d’escalade selon le retard — dossiers, priorité et journal d’actions.</p>

      <div className="tabs">
        <button type="button" className={`tab${tab === "niveaux" ? " active" : ""}`} onClick={() => setTab("niveaux")}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M4 20V10M11 20V4M18 20v-7" />
          </svg>
          Niveaux
        </button>
        <button type="button" className={`tab${tab === "dossiers" ? " active" : ""}`} onClick={() => setTab("dossiers")}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6" />
          </svg>
          Dossiers
        </button>
      </div>

      {tab === "dossiers" && (
        <PageSearch value={search} onChange={setSearch} placeholder="Rechercher un membre (code)…" />
      )}

      {tab === "niveaux" && <NiveauxTab d={d} />}
      {tab === "dossiers" && <DossiersTab search={search} />}
    </div>
  );
}
