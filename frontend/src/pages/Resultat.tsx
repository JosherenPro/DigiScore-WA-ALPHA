import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, money, type DemandeDetail } from "../api/client";
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

  function load() {
    api.demande(Number(id)).then(setD).catch((e) => setErr(String(e)));
  }

  useEffect(load, [id]);

  async function analyser() {
    setBusy(true);
    try {
      await api.analyser(Number(id));
      load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function soumettre() {
    setBusy(true);
    try {
      await api.soumettre(Number(id), user?.id ?? 1);
      load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!d) return <div className="page">{err || "Chargement…"}</div>;
  const s = d.score;
  const pct = s ? Math.min(100, s.score_global) : 0;

  return (
    <div className="page">
      <h1>Résultat — dossier #{d.id}</h1>
      <p className="lede">
        {d.objet} · statut {d.statut}
      </p>
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
          </div>
          <div className="amounts">
            <div className="block">
              <span className="muted">Demandé</span>
              <strong>{money(d.montant_demande)}</strong>
            </div>
            <div className="block">
              <span className="muted">Plafond éligible</span>
              <strong>{money(s.montant_eligible)}</strong>
            </div>
          </div>
          <p>
            Score <strong>{Math.round(s.score_global)}/100</strong>
            {s.thin_file ? " · thin-file" : ""}
          </p>
          <div className="gauge">
            <div className="needle" style={{ left: `${pct}%` }} />
          </div>
          {d.ratios && (
            <p className="muted">
              CAF {money(d.ratios.caf)} · RCSD {d.ratios.rcsd.toFixed(2)} · EBE {money(d.ratios.ebe)}
            </p>
          )}
          {s.knockouts?.length > 0 && (
            <section className="block">
              <h2>Knock-outs</h2>
              {s.knockouts.map((k) => (
                <p key={k.code}>
                  {k.code} — {k.detail}
                </p>
              ))}
            </section>
          )}
          <section className="block">
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
                {(s.criteres || []).map((c) => (
                  <tr key={c.code}>
                    <td>{c.code}</td>
                    <td>{Math.round(c.note)}</td>
                    <td>{Math.round(c.poids * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
      {err && <p className="error">{err}</p>}
      <div className="actions">
        {s && user?.role === "agent" && d.statut === "analyse" && (
          <button className="btn teal" disabled={busy} onClick={soumettre}>
            Soumettre au chef / CIC
          </button>
        )}
        <Link className="btn ghost" to={`/demandes/${d.id}/memo`}>
          Mémo
        </Link>
      </div>
    </div>
  );
}
