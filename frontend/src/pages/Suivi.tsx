import { useState } from "react";
import { api, type VisiteAFaire } from "../api/client";
import Spinner from "../components/Spinner";
import Alert from "../components/Alert";
import PageSearch from "../components/PageSearch";
import { useApi } from "../hooks/useApi";

const VISITE_LABEL: Record<string, string> = {
  V1: "V1 — relance amiable",
  V2: "V2 — visite terrain",
  V3: "V3 — mise en demeure",
};

function statutTone(statut: string): string {
  if (statut === "en_retard") return "bad";
  if (statut === "a_faire") return "warn";
  return "";
}

/** Formulaire de compte-rendu pour une visite de suivi (V1/V2/V3), branché sur
 * /vision/visites — l'historique de suivi terrain existait déjà côté backend
 * (table portfolio_followup) mais n'avait aucune page pour le remplir. */
function VisiteForm({ v, onDone }: { v: VisiteAFaire; onDone: () => void }) {
  const [statut, setStatut] = useState<"realisee" | "manquee">("realisee");
  const [note, setNote] = useState("");
  const [nextOn, setNextOn] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit() {
    setBusy(true);
    setErr("");
    try {
      await api.logVisite({
        member_id: v.member_id,
        visit_code: v.visite,
        visit_status: statut,
        action_taken: note || undefined,
        next_on: nextOn || undefined,
      });
      onDone();
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
          Résultat
          <select value={statut} onChange={(e) => setStatut(e.target.value as "realisee" | "manquee")}>
            <option value="realisee">Réalisée</option>
            <option value="manquee">Manquée</option>
          </select>
        </label>
        <label className="field">
          Prochaine relance
          <input type="date" value={nextOn} onChange={(e) => setNextOn(e.target.value)} />
        </label>
      </div>
      <label className="field mt-sm">
        Compte-rendu
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="ex. Promesse de paiement le 20, boutique fermée…" />
      </label>
      {err && <Alert kind="error">{err}</Alert>}
      <div className="actions">
        <button className="btn primary sm" type="button" disabled={busy} onClick={submit}>
          {busy ? "Enregistrement…" : "Consigner la visite"}
        </button>
      </div>
    </div>
  );
}

export default function Suivi() {
  const { data: d, error, loading, reload } = useApi(() => api.visites(50), []);
  const [open, setOpen] = useState<number | null>(null);
  const [done, setDone] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState("");

  if (error) return <div className="page"><Alert kind="error">{error}</Alert></div>;
  if (loading || !d) return <div className="page"><Spinner /></div>;

  const needle = search.trim().toLowerCase();
  const items = d.items.filter(
    (v) => !done.has(v.outstanding_loan_id) && (!needle || v.member_code.toLowerCase().includes(needle)),
  );

  return (
    <div className="page">
      <h1>Suivi terrain</h1>
      <p className="lede">Visites de relance à faire (V1 amiable, V2 terrain, V3 mise en demeure) — calculées depuis les encours en retard.</p>

      <PageSearch value={search} onChange={setSearch} placeholder="Rechercher un membre (code)…" />

      {items.length === 0 && <p className="muted">Aucune visite à faire{needle ? " pour cette recherche" : " pour l’instant"}.</p>}

      <div className="list">
        {items.map((v) => (
          <div className="visite-card" key={v.outstanding_loan_id}>
            <div className="visite-row">
              <div>
                <strong>{v.member_code}</strong>
                <div className="muted">
                  {VISITE_LABEL[v.visite] || v.visite} · cible {v.cible} · {v.jours_de_retard} j de retard
                </div>
              </div>
              <span className={`badge rect ${statutTone(v.statut)}`}>{v.statut.replace("_", " ")}</span>
              <button
                className="btn ghost sm"
                type="button"
                onClick={() => setOpen(open === v.outstanding_loan_id ? null : v.outstanding_loan_id)}
              >
                {open === v.outstanding_loan_id ? "Fermer" : "Consigner"}
              </button>
            </div>
            {open === v.outstanding_loan_id && (
              <VisiteForm
                v={v}
                onDone={() => {
                  setOpen(null);
                  setDone((s) => new Set(s).add(v.outstanding_loan_id));
                  reload();
                }}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
