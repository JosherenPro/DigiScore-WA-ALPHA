import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, asList, money, zoneClass, type DemandeDetail, type Knockout, type Critere } from "../api/client";
import { getUser } from "../auth";

function msgClass(code?: string) {
  if (!code) return "msg";
  if (["MONTANT_OK", "UPSELL_POSSIBLE"].includes(code)) return "msg ok";
  if (["MONTANT_PLAFONNE", "VOIE_EXCEPTIONNELLE", "HISTORIQUE_INSUFFISANT"].includes(code)) return "msg plafonne";
  return "msg ko";
}

export default function Resultat() {
  const { id } = useParams();
  const user = getUser();
  const [d, setD] = useState<DemandeDetail | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [fileHint, setFileHint] = useState("");
  const [motif, setMotif] = useState("");

  function load() {
    api.demande(Number(id)).then(setD).catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }

  useEffect(load, [id]);

  async function analyser() {
    setBusy(true);
    setErr("");
    try {
      await api.analyser(Number(id));
      load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function soumettre() {
    setBusy(true);
    setErr("");
    try {
      const out = await api.soumettre(Number(id));
      setFileHint(out.file === "cic" ? "Envoyé en file CIC" : "Envoyé en file chef");
      load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function decider(avis: string, override = false) {
    if (!user) return;
    setBusy(true);
    setErr("");
    try {
      await api.decision(Number(id), {
        niveau: user.role === "cic" ? "cic" : "chef_agence",
        avis,
        motif: motif || null,
        override,
      });
      setMotif("");
      load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!d) return <div className="page">{err || "Chargement…"}</div>;
  const s = d.score;
  const pct = s ? Math.min(100, s.score_global) : 0;
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
      {fileHint && <p className="msg ok">{fileHint}</p>}
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
            {s.zone && <div className={`badge ${zoneClass(s.zone)}`} style={{ marginTop: 8 }}>{s.zone}</div>}
          </div>
          <div className="amounts">
            <div className="block">
              <span className="muted">Demandé</span>
              <strong>{money(d.montant_demande)}</strong>
            </div>
            <div className="block">
              <span className="muted">Plafond éligible</span>
              <strong>{money(s.montant_eligible)}</strong>
              {s.montant_max_suggestion ? (
                <div className="muted">Suggestion {money(s.montant_max_suggestion)}</div>
              ) : null}
            </div>
          </div>
          <p>
            Score <strong>{Math.round(s.score_global)}/100</strong>
            {s.thin_file ? " · thin-file" : ""} · {s.eligible ? "éligible" : "non éligible"}
          </p>
          <div className="gauge">
            <div className="needle" style={{ left: `${pct}%` }} />
          </div>
          <div className="gauge-labels">
            <span>rejet 0–40</span>
            <span>analyse 41–70</span>
            <span>approbation 71–100</span>
          </div>
          {d.ratios && (
            <p className="muted">
              CAF {money(d.ratios.caf)} · RCSD {d.ratios.rcsd.toFixed(2)} · EBE {money(d.ratios.ebe)} — calculés par le moteur, pas ici.
            </p>
          )}
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
            <section className="block" style={{ marginTop: "0.9rem" }}>
              <h2>Critères</h2>
              <table>
                <thead>
                  <tr>
                    <th>Critère</th>
                    <th>Note</th>
                    <th>Poids</th>
                  </tr>
                </thead>
                <tbody>
                  {criteres.map((c, i) => (
                    <tr key={String(c.code || i)}>
                      <td>{String(c.code || "—")}</td>
                      <td>{c.note != null ? Math.round(Number(c.note)) : "—"}</td>
                      <td>{c.poids != null ? `${Math.round(Number(c.poids) * 100)}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </>
      )}
      {(chef || cic) && (
        <section className="block" style={{ marginTop: "0.9rem" }}>
          <h2>Avis humain</h2>
          <p className="lede">Motif obligatoire si tu t’écartes de la reco.</p>
          <label className="field">
            Motif
            <input value={motif} onChange={(e) => setMotif(e.target.value)} />
          </label>
          {chef && (
            <div className="actions">
              <button className="btn teal" disabled={busy} onClick={() => decider("valider")}>
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
              <button className="btn teal" disabled={busy} onClick={() => decider("accorder")}>
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
        <p className="muted" style={{ marginTop: "1rem" }}>
          Décisions : {d.decisions.map((x) => `${x.niveau} ${x.avis}`).join(" · ")}
        </p>
      )}
      {err && <p className="error">{err}</p>}
      <div className="actions">
        {s && user?.role === "agent" && (d.statut === "analyse" || d.statut === "brouillon") && (
          <button className="btn teal" disabled={busy} onClick={soumettre}>
            Soumettre au chef / CIC
          </button>
        )}
        <Link className="btn ghost" to={`/demandes/${d.id}/memo`}>
          Mémo + échéancier
        </Link>
      </div>
    </div>
  );
}
