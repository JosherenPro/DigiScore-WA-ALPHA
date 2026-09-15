import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
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
  3: { libelle: "Recouvrement intensif", periode: "J+31 à J+90", responsable: "Superviseur + Directeur (Chef d’Agence)", actions: "Convocation formelle, échéancier écrit, garanties activées", tone: "bad" },
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

const AUJOURD_HUI = new Date().toISOString().slice(0, 10);

/** Etat de la prochaine relance. Le champ `next_on` etait affiche brut : une
 * date au 21/09 ne dit pas a l'agent qu'elle est depassee depuis trois jours. */
function etatRelance(nextOn?: string | null): { texte: string; tone: string } | null {
  if (!nextOn) return null;
  if (nextOn < AUJOURD_HUI) return { texte: `Relance en retard (prévue le ${nextOn})`, tone: "bad" };
  if (nextOn === AUJOURD_HUI) return { texte: "Relance prévue aujourd’hui", tone: "warn" };
  return { texte: `Relance prévue le ${nextOn}`, tone: "" };
}

/** Part de l'encours deja recuperee — le seul indicateur de progres du dossier. */
function progres(it: DossierRecouvrement): number {
  const total = it.outstanding + it.recovered_amount;
  return total > 0 ? Math.round((it.recovered_amount / total) * 100) : 0;
}

const ACTION_LABEL: Record<string, string> = Object.fromEntries(
  [
    ["appel", "Appel téléphonique"],
    ["visite", "Visite terrain"],
    ["courrier", "Courrier / lettre"],
    ["mise_en_demeure", "Mise en demeure"],
    ["promesse", "Promesse de paiement"],
    ["huissier", "Huissier / contentieux"],
    ["relance", "Relance"],
  ],
);

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

/** Journal des actions deja menees sur le dossier (GET .../actions).
 * Charge a l'ouverture : l'ecran ne montrait l'historique qu'apres avoir
 * consigne une nouvelle action, donc jamais au moment ou il sert. */
function Journal({
  caseId,
  entries,
  onCharge,
}: {
  caseId: number;
  entries?: JournalEntry[];
  onCharge: (j: JournalEntry[]) => void;
}) {
  const [busy, setBusy] = useState(entries === undefined);

  useEffect(() => {
    if (entries !== undefined) return;
    let vivant = true;
    setBusy(true);
    api
      .journalRecouvrement(caseId)
      .then((r) => {
        if (vivant) onCharge(r.journal);
      })
      .catch(() => {
        if (vivant) onCharge([]);
      })
      .finally(() => {
        if (vivant) setBusy(false);
      });
    return () => {
      vivant = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  if (busy) return <Spinner />;
  if (!entries || entries.length === 0) {
    return <p className="muted mt-sm">Aucune action consignée jusqu’ici — ce dossier n’a encore rien reçu.</p>;
  }

  const recupere = entries.reduce((sum, j) => sum + (j.montant || 0), 0);

  return (
    <div className="rec-journal mt-sm">
      <p className="hint">
        Historique — {entries.length} action{entries.length > 1 ? "s" : ""}
        {recupere > 0 ? ` · ${money(recupere)} encaissés` : ""}
      </p>
      <ol className="rec-journal-list">
        {entries.map((j, i) => (
          <li key={i}>
            <span className="rec-journal-date">{j.date || "—"}</span>
            <span>
              <strong>{ACTION_LABEL[j.type] || j.type}</strong>
              {j.montant ? <span className="badge rect ok">{money(j.montant)}</span> : null}
              {j.note && <div className="muted">{j.note}</div>}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Un client et ses dossiers de recouvrement.
 *
 * A plat, un membre qui accumule les retards remplit l'ecran de cartes et noie
 * les autres clients. L'ordre d'arrivee de l'API est conserve : le premier
 * dossier d'un membre fixe la position de son lot, on ne rebat pas le tri au
 * profit d'un ordre alphabetique.
 */
type LotClient = {
  membreId: number;
  nom: string;
  code: string;
  dossiers: DossierRecouvrement[];
  outstanding: number;
  recovered: number;
  enRetard: boolean;
};

function grouperParClient(items: DossierRecouvrement[]): LotClient[] {
  const lots = new Map<number, LotClient>();
  for (const it of items) {
    let lot = lots.get(it.member_id);
    if (!lot) {
      lot = {
        membreId: it.member_id,
        nom: it.member_name || `membre #${it.member_id}`,
        code: it.member_code,
        dossiers: [],
        outstanding: 0,
        recovered: 0,
        enRetard: false,
      };
      lots.set(it.member_id, lot);
    }
    lot.dossiers.push(it);
    lot.outstanding += it.outstanding || 0;
    lot.recovered += it.recovered_amount || 0;
    // Une relance en retard sur l'un des dossiers = client prioritaire.
    if (etatRelance(it.next_on)?.tone === "bad") lot.enRetard = true;
  }
  return [...lots.values()];
}

/** Un client et tous ses dossiers de recouvrement, repliable.
 *
 * La carte du lot porte le total de l'encours du client et son retard maximal :
 * c'est l'information qui fait choisir par quel client commencer la tournée. */
function LotDossiers({
  lot,
  ouvertCase,
  setOuvertCase,
  journals,
  setJournals,
}: {
  lot: LotClient;
  ouvertCase: number | null;
  setOuvertCase: (id: number | null) => void;
  journals: Record<number, JournalEntry[]>;
  setJournals: React.Dispatch<React.SetStateAction<Record<number, JournalEntry[]>>>;
}) {
  const [ouvert, setOuvert] = useState(lot.dossiers.length === 1);
  const retardMax = Math.max(...lot.dossiers.map((d) => d.days_late || 0));
  return (
    <section className={`lot${lot.enRetard ? " en-retard" : ""}`}>
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
              {lot.code} · {lot.dossiers.length} dossier{lot.dossiers.length > 1 ? "s" : ""} ·{" "}
              {money(lot.outstanding)} restants
              {retardMax > 0 ? ` · retard max ${retardMax} j` : ""}
            </span>
          </span>
        </button>
        <div className="lot-actions">
          <Link className="btn ghost sm" to={`/membres/${lot.membreId}`}>
            Fiche
          </Link>
          <Link className="btn primary sm" to={`/membres/${lot.membreId}/demande`}>
            Nouveau crédit
          </Link>
        </div>
      </div>
      {ouvert && (
        <div className="list lot-cards">
          {lot.dossiers.map((it) => (
            <CarteDossier
              key={it.case_id}
              it={it}
              ouvert={ouvertCase === it.case_id}
              onToggle={() => setOuvertCase(ouvertCase === it.case_id ? null : it.case_id)}
              journal={journals[it.case_id]}
              onJournal={(j) => setJournals((m) => ({ ...m, [it.case_id]: j }))}
            />
          ))}
        </div>
      )}
    </section>
  );
}

/** Une ligne de prêt au sein du lot d'un client (journal + formulaire). */
function CarteDossier({
  it,
  ouvert,
  onToggle,
  journal,
  onJournal,
}: {
  it: DossierRecouvrement;
  ouvert: boolean;
  onToggle: () => void;
  journal?: JournalEntry[];
  onJournal: (j: JournalEntry[]) => void;
}) {
  const relance = etatRelance(it.next_on);
  const pct = progres(it);
  return (
    <div className={`visite-card${relance?.tone === "bad" ? " en-retard" : ""}`}>
      <div className="visite-row">
        <div>
          <span className="badge rect">Prêt #{it.case_id}</span>
          <div className="muted">
            {money(it.outstanding)} restant · {it.days_late} j de retard
            {it.responsable ? ` · ${it.responsable}` : ""}
          </div>
          {relance && <div className={`rec-relance ${relance.tone}`}>{relance.texte}</div>}
        </div>
        <span className="badge rect">N{it.niveau} — {it.libelle}</span>
        <span className={`badge rect ${prioriteTone(it.priorite)}`}>{it.priorite}</span>
        <button className="btn ghost sm" type="button" onClick={onToggle}>
          {ouvert ? "Fermer" : "Ouvrir le dossier"}
        </button>
      </div>

      {/* Progres du recouvrement : sans lui, deux dossiers au meme encours se
          ressemblent, alors que l'un rembourse et pas l'autre. */}
      {it.recovered_amount > 0 && (
        <div className="rec-progres">
          <span className="rec-progres-track">
            <span className="rec-progres-fill" style={{ width: `${Math.min(pct, 100)}%` }} />
          </span>
          <span className="muted">
            {money(it.recovered_amount)} récupérés · {pct} % de la créance
          </span>
        </div>
      )}

      {ouvert && (
        <>
          {/* Le journal se charge a l'ouverture : on ne relance pas un membre
              sans savoir ce qui a deja ete tente. */}
          <Journal caseId={it.case_id} entries={journal} onCharge={onJournal} />
          <ActionForm dossier={it} onDone={onJournal} />
        </>
      )}
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
      <p className="hint">
        P1 = encours &gt; 2 M et retard &gt; 8 j · P2 = retard &gt; 30 j · P3 = suivi courant · S = à jour.
      </p>
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

      <div className="lots">
        {grouperParClient(items).map((lot) => (
          <LotDossiers
            key={lot.membreId}
            lot={lot}
            ouvertCase={openCase}
            setOuvertCase={setOpenCase}
            journals={journals}
            setJournals={setJournals}
          />
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
      <p className="lede">
        4 niveaux d’escalade selon le retard : <strong>N1</strong> J+1 à J+7 (appel, visite),
        <strong> N2</strong> J+8 à J+30 (domicile, caution), <strong>N3</strong> J+31 à J+90 (mise en demeure),
        <strong> N4</strong> au-delà (contentieux). Chaque action est consignée au journal du dossier.
      </p>

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
        <PageSearch value={search} onChange={setSearch} placeholder="Rechercher un membre (nom ou code)…" />
      )}

      {tab === "niveaux" && <NiveauxTab d={d} />}
      {tab === "dossiers" && <DossiersTab search={search} />}
    </div>
  );
}
