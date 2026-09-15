import { useState } from "react";
import { api, type VisiteAFaire } from "../api/client";
import Spinner from "../components/Spinner";
import Alert from "../components/Alert";
import PageSearch from "../components/PageSearch";
import MembreLabel from "../components/MembreLabel";
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

/** Une tournée se lit par urgence, pas dans l'ordre d'arrivée de l'API : ce
 * qui est en retard passe devant ce qui est simplement à faire. */
const STATUT_LABEL: Record<string, string> = {
  en_retard: "En retard",
  a_faire: "À faire",
  planifiee: "Planifiée",
};

const GROUPES: { cle: string; titre: string; aide: string }[] = [
  { cle: "en_retard", titre: "En retard", aide: "Visites dépassées — à traiter en premier." },
  { cle: "a_faire", titre: "À faire", aide: "Planifiées, pas encore dépassées." },
  { cle: "autre", titre: "Autres", aide: "" },
];

export default function Suivi() {
  const { data: d, error, loading, reload } = useApi(() => api.visites(50), []);
  const [open, setOpen] = useState<number | null>(null);
  // Les visites consignées restaient absentes sans un mot : l'agent ne savait
  // pas s'il avait réellement enregistré. On garde la ligne, marquée faite.
  const [done, setDone] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState("");

  if (error) return <div className="page"><Alert kind="error">{error}</Alert></div>;
  if (loading || !d) return <div className="page"><Spinner /></div>;

  // La recherche porte sur le nom comme sur le code : depuis qu'on affiche
  // « Yala Tetsah », taper « Yala » doit trouver la ligne. /vision/visites n'a
  // pas de parametre q, le filtrage reste donc cote client sur la page chargee.
  const needle = search.trim().toLowerCase();
  const items = d.items.filter(
    (v) =>
      !needle ||
      v.member_code.toLowerCase().includes(needle) ||
      (v.member_name || "").toLowerCase().includes(needle),
  );
  const restantes = items.filter((v) => !done.has(v.outstanding_loan_id));
  const enRetard = restantes.filter((v) => v.statut === "en_retard").length;

  const groupes = GROUPES.map((g) => ({
    ...g,
    visites: items.filter((v) =>
      g.cle === "autre" ? !["en_retard", "a_faire"].includes(v.statut) : v.statut === g.cle,
    ),
  })).filter((g) => g.visites.length > 0);

  return (
    <div className="page">
      <h1>Suivi terrain</h1>
      <p className="lede">
        Les visites à mener, calculées depuis les encours en retard : <strong>V1</strong> relance amiable
        (J+7 après décaissement), <strong>V2</strong> visite terrain (mi-parcours), <strong>V3</strong> mise
        en demeure (30 j avant l’échéance). Consigner une visite la clôture ici et alimente l’historique du membre.
      </p>
      <p className="hint">
        « En retard » = plus de 15 jours après la date cible ; « À faire » = échéance cible atteinte.
      </p>

      {/* Avancement de la tournée : sans compteur, on ne sait pas où on en est. */}
      <section className="block dashboard-head">
        <div className="stat-row">
          <div className="stat-tile">
            <span className="muted">Visites à faire</span>
            <strong>{restantes.length}</strong>
          </div>
          <div className="stat-tile">
            <span className="muted">Dont en retard</span>
            <strong className={enRetard > 0 ? "bad" : ""}>{enRetard}</strong>
          </div>
          <div className="stat-tile">
            <span className="muted">Consignées dans cette session</span>
            <strong className="ok">{done.size}</strong>
          </div>
        </div>
      </section>

      <PageSearch value={search} onChange={setSearch} placeholder="Rechercher un membre (nom ou code)…" />

      {items.length === 0 && (
        <p className="muted">Aucune visite à faire{needle ? " pour cette recherche" : " pour l’instant"}.</p>
      )}

      {groupes.map((g) => (
        <section className="mt-md" key={g.cle}>
          <p className="section-label">
            {g.titre}
            <span>{g.visites.length}</span>
          </p>
          {g.aide && <p className="muted" style={{ marginTop: 0 }}>{g.aide}</p>}
          <div className="list">
            {g.visites.map((v) => {
              const fait = done.has(v.outstanding_loan_id);
              return (
                <div className={`visite-card${fait ? " fait" : ""}`} key={v.outstanding_loan_id}>
                  <div className="visite-row">
                    <div>
                      <MembreLabel nom={v.member_name} code={v.member_code} membreId={v.member_id} />
                      <div className="muted">
                        {VISITE_LABEL[v.visite] || v.visite} · échéance cible {v.cible}
                        {v.jours_de_retard > 0 ? ` · ${v.jours_de_retard} j de retard` : ""}
                      </div>
                    </div>
                    {fait ? (
                      <span className="badge rect ok">Consignée</span>
                    ) : (
                      <>
                        <span className={`badge rect ${statutTone(v.statut)}`}>{STATUT_LABEL[v.statut] || v.statut.replace("_", " ")}</span>
                        <button
                          className="btn ghost sm"
                          type="button"
                          onClick={() => setOpen(open === v.outstanding_loan_id ? null : v.outstanding_loan_id)}
                        >
                          {open === v.outstanding_loan_id ? "Fermer" : "Consigner"}
                        </button>
                      </>
                    )}
                  </div>
                  {open === v.outstanding_loan_id && !fait && (
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
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
