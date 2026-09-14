import { useEffect, useState } from "react";
import { api, type Capabilities, type M6Out } from "../api/client";

export default function Portefeuille() {
  const [d, setD] = useState<M6Out | null>(null);
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.portefeuille().then(setD).catch((e) => setErr(e instanceof Error ? e.message : String(e)));
    api.capabilities().then(setCaps).catch(() => undefined);
  }, []);
  if (err) return <div className="page error">{err}</div>;
  if (!d) return <div className="page">Chargement…</div>;
  return (
    <div className="page">
      <h1>Suivi portefeuille</h1>
      <p className="lede">Maquette M6 — pas le live. Chiffres seed, pas de moteur PAR temps réel.</p>
      <section className="block">
        <h2>PAR agence</h2>
        <table>
          <thead>
            <tr>
              <th>Agence</th>
              <th>PAR 30</th>
              <th>PAR 90</th>
            </tr>
          </thead>
          <tbody>
            {d.par.map((p, i) => (
              <tr key={p.agence_id ?? i}>
                <td>{p.agence_id ?? "—"}</td>
                <td>{p.par30} %</td>
                <td>{p.par90} %</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {caps?.anomalies || caps?.early_warning ? (
        <section className="block" style={{ marginTop: "0.9rem" }}>
          <h2>Alertes</h2>
          {d.alertes.map((a, i) => (
            <p key={i}>
              Membre {a.membre_id} — {a.signal}
            </p>
          ))}
        </section>
      ) : (
        <p className="muted">Anomalies / simulation / early-warning masqués (capabilities à false).</p>
      )}
    </div>
  );
}
