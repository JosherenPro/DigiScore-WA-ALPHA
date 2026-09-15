import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, asList, money, zoneClass, type DemandeDetail, type Knockout, type Critere } from "../api/client";
import { getUser } from "../auth";
import Spinner from "../components/Spinner";
import Alert from "../components/Alert";
import MlPanel from "../components/MlPanel";
import AuthImage from "../components/AuthImage";
import { CompareBar, CRITERE_LABELS, CriteriaBars, ScoreGauge } from "../components/charts";
import { useApi } from "../hooks/useApi";

function msgClass(code?: string) {
  if (!code) return "msg";
  if (["MONTANT_OK", "UPSELL_POSSIBLE"].includes(code)) return "msg ok";
  if (["MONTANT_PLAFONNE", "VOIE_EXCEPTIONNELLE", "HISTORIQUE_INSUFFISANT"].includes(code)) return "msg plafonne";
  return "msg ko";
}

export default function Resultat() {
  const { id } = useParams();
  const user = getUser();
  const { data: d, error, loading, reload, setError } = useApi<DemandeDetail>(
    () => api.demande(Number(id)),
    [id],
  );
  const [busy, setBusy] = useState(false);
  const [fileHint, setFileHint] = useState("");
  const [motif, setMotif] = useState("");

  async function analyser() {
    setBusy(true);
    setError("");
    try {
      await api.analyser(Number(id));
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function soumettre() {
    setBusy(true);
    setError("");
    try {
      const out = await api.soumettre(Number(id));
      setFileHint(out.file === "cic" ? "Envoyé en file CIC" : "Envoyé en file chef");
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function decider(avis: string, override = false) {
    if (!user) return;
    setBusy(true);
    setError("");
    try {
      await api.decision(Number(id), {
        niveau: user.role === "cic" ? "cic" : "chef_agence",
        avis,
        motif: motif || null,
        override,
      });
      setMotif("");
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (error && !d) return <div className="page"><Alert kind="error">{error}</Alert></div>;
  if (loading || !d) return <div className="page"><Spinner /></div>;
  const s = d.score;
  const criteres = asList<Critere>(s?.criteres as Critere[] | Record<string, unknown> | null);
  const knockouts = asList<Knockout>(s?.knockouts as Knockout[] | Record<string, unknown> | null);
  const chef = user?.role === "chef_agence" && d.statut === "soumis_chef";
  const cic = user?.role === "cic" && d.statut === "soumis_cic";

  return (
    <div className="page">
      <h1>Résultat — dossier #{d.id}</h1>
      <p className="lede">
        {d.membre ? `${d.membre.prenom} ${d.membre.nom} · ${d.membre.code_externe}` : `Membre #${d.membre_id}`} · {d.objet} ·{" "}
        <span className="badge">{d.statut}</span>
      </p>
      {fileHint && <Alert kind="success">{fileHint}</Alert>}
      {!s && (
        <div className="actions">
          <button className="btn" disabled={busy} onClick={analyser}>
            Lancer l’analyse
          </button>
        </div>
      )}
      {s && (
        <>
          <div className={msgClass(s.message_code)}>
            <strong>{s.message_code}</strong>
            <div>{s.message_humain}</div>
            {s.zone && <div className={`badge ${zoneClass(s.zone)} mt-sm`}>{s.zone}</div>}
          </div>
          <section className="block dashboard-head">
            <div className="gauge-card">
              <ScoreGauge score={s.score_global} zone={s.zone} />
              <div>
                <p style={{ margin: 0 }}>
                  {s.eligible ? "Éligible" : "Non éligible"}
                  {s.thin_file ? " · thin-file" : ""}
                </p>
                {d.ratios && (
                  <div className="stat-row mt-sm">
                    <div className="stat-tile">
                      <span className="muted">CAF</span>
                      <strong>{money(d.ratios.caf)}</strong>
                    </div>
                    <div className="stat-tile">
                      <span className="muted">RCSD</span>
                      <strong>{d.ratios.rcsd.toFixed(2)}</strong>
                    </div>
                    <div className="stat-tile">
                      <span className="muted">EBE</span>
                      <strong>{money(d.ratios.ebe)}</strong>
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="grid two mt-md">
              <CompareBar
                label="Demandé sur plafond éligible"
                value={d.montant_demande}
                max={Math.max(s.montant_eligible, d.montant_demande)}
                valueLabel={money(d.montant_demande)}
                tone={d.montant_demande > s.montant_eligible ? "warn" : "ok"}
              />
              {s.montant_max_suggestion ? (
                <CompareBar
                  label="Suggestion (capacité estimée)"
                  value={s.montant_max_suggestion}
                  max={Math.max(s.montant_max_suggestion, s.montant_eligible)}
                  valueLabel={money(s.montant_max_suggestion)}
                />
              ) : (
                <CompareBar
                  label="Plafond éligible"
                  value={s.montant_eligible}
                  max={Math.max(s.montant_eligible, d.montant_demande)}
                  valueLabel={money(s.montant_eligible)}
                />
              )}
            </div>
          </section>
          <MlPanel demandeId={d.id} montant={s.montant_eligible || d.montant_demande} dureeMois={d.duree_mois} />
          {knockouts.length > 0 && (
            <section className="block">
              <h2>Knock-outs</h2>
              {knockouts.map((k, i) => (
                <p key={String(k.code || i)}>
                  {String(k.code || "")} {k.detail ? `— ${k.detail}` : ""}
                </p>
              ))}
            </section>
          )}
          {criteres.length > 0 && (
            <section className="block mt-md">
              <h2>Détail des 6 critères</h2>
              <CriteriaBars criteres={criteres} />
            </section>
          )}
          {criteres.length > 0 && (
            <section className="block mt-md">
              <h2>Critères déterminants</h2>
              <ol className="top-list">
                {[...criteres]
                  .sort((a, b) => Number(b.contribution ?? 0) - Number(a.contribution ?? 0))
                  .slice(0, 3)
                  .map((c, i) => {
                    const code = String(c.code || "");
                    const note = Math.round(Number(c.note ?? 0));
                    const poids = c.poids != null ? Math.round(Number(c.poids) * 100) : null;
                    const contribution = c.contribution != null ? Math.round(Number(c.contribution)) : null;
                    return (
                      <li key={code || i}>
                        <span className="num">{i + 1}</span>
                        <span>
                          <strong>{CRITERE_LABELS[code] || code}</strong>
                          <div className="muted">
                            Note {note}/100{poids != null ? ` · poids ${poids} %` : ""}
                            {contribution != null ? ` · +${contribution} pts` : ""}
                          </div>
                        </span>
                      </li>
                    );
                  })}
              </ol>
            </section>
          )}
          {d.cautions.length > 0 && (
            <section className="block mt-md">
              <h2>Cautionnaires</h2>
              <div className="list">
                {d.cautions.map((c, i) => (
                  <div className="row" key={i}>
                    <div>
                      <strong>{c.prenom} {c.nom}</strong>
                      <div className="muted">
                        {c.relation ? `${c.relation} · ` : ""}
                        {c.telephone || "tél. inconnu"} · caution {c.type_caution} · {money(c.montant_engage)} engagés
                        {c.membre_existant ? " · déjà membre" : ""}
                      </div>
                      {c.revue && (
                        <div className="muted mt-sm" style={{ fontSize: "0.85rem" }}>
                          Capacité de relais — CAF {money(c.revue.caf_relais ?? 0)}
                          {c.revue.rcsd_relais != null ? ` · RCSD ${c.revue.rcsd_relais.toFixed(2)}` : ""}
                          {c.revue.score_relais != null ? ` · score ${Math.round(c.revue.score_relais)}/100` : ""}
                          {c.revue.motif ? ` — ${c.revue.motif}` : ""}
                        </div>
                      )}
                    </div>
                    <span className={`badge rect ${c.revue?.eligible ? "ok" : "warn"}`}>
                      {c.revue ? (c.revue.eligible ? "Éligible" : "À vérifier") : "Non évalué"}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
          {d.pieces.length > 0 && (
            <section className="block mt-md">
              <h2>Pièces justificatives</h2>
              <div className="list">
                {d.pieces.map((p, i) => (
                  <div className="row" key={i}>
                    <div className="piece-photo-picker">
                      {p.fichier ? (
                        <AuthImage className="piece-thumb" path={p.fichier} alt={p.type_piece} />
                      ) : (
                        <div className="piece-thumb" />
                      )}
                      <strong>{p.type_piece}</strong>
                    </div>
                    <span className={`badge ${p.qualite_ocr === "ok" ? "ok" : "warn"}`}>{p.qualite_ocr || "—"}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
      {(chef || cic) && (
        <section className="block mt-md">
          <h2>Avis humain</h2>
          <p className="lede">Motif obligatoire si tu t’écartes de la reco.</p>
          <label className="field">
            Motif
            <input value={motif} onChange={(e) => setMotif(e.target.value)} />
          </label>
          {chef && (
            <div className="actions">
              <button className="btn primary" disabled={busy} onClick={() => decider("valider")}>
                Valider
              </button>
              <button className="btn danger" disabled={busy} onClick={() => decider("refuser", true)}>
                Refuser
              </button>
              <button className="btn ghost" disabled={busy} onClick={() => decider("renvoyer")}>
                Renvoyer
              </button>
              <button className="btn warn" disabled={busy} onClick={() => decider("escalader")}>
                Escalader CIC
              </button>
            </div>
          )}
          {cic && (
            <div className="actions">
              <button className="btn primary" disabled={busy} onClick={() => decider("accorder")}>
                Accorder
              </button>
              <button className="btn warn" disabled={busy} onClick={() => decider("conditionner")}>
                Conditionner
              </button>
              <button className="btn danger" disabled={busy} onClick={() => decider("refuser", true)}>
                Refuser
              </button>
            </div>
          )}
        </section>
      )}
      {d.decisions?.length > 0 && (
        <p className="muted mt-lg">
          Décisions : {d.decisions.map((x) => `${x.niveau} ${x.avis}`).join(" · ")}
        </p>
      )}
      {error && <Alert kind="error">{error}</Alert>}
      <div className="actions">
        {s && user?.role === "agent" && (d.statut === "analyse" || d.statut === "brouillon") && (
          <button className="btn primary" disabled={busy} onClick={soumettre}>
            Soumettre au chef d’agence
          </button>
        )}
        <Link className="btn ghost" to={`/demandes/${d.id}/memo`}>
          Mémo + échéancier
        </Link>
      </div>
    </div>
  );
}
