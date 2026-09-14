import { useEffect, useState } from "react";
import { api, type Capabilities, type M7Out } from "../api/client";

export default function Recouvrement() {
  const [d, setD] = useState<M7Out | null>(null);
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.recouvrement().then(setD).catch((e) => setErr(e instanceof Error ? e.message : String(e)));
    api.capabilities().then(setCaps).catch(() => undefined);
  }, []);
  if (err) return <div className="page error">{err}</div>;
  if (!d) return <div className="page">Chargement…</div>;
  return (
    <div className="page">
      <h1>Recouvrement</h1>
      <p className="lede">Maquette M7 — 4 niveaux, données d’exemple. Pas le live.</p>
      <section className="block">
        <table>
          <thead>
            <tr>
              <th>Membre</th>
              <th>Niveau</th>
              <th>Action</th>
              <th>Responsable</th>
            </tr>
          </thead>
          <tbody>
            {d.dossiers.map((r, i) => (
              <tr key={i}>
                <td>{r.membre_id}</td>
                <td>{r.niveau}</td>
                <td>{r.action}</td>
                <td>{r.responsable}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {caps && !caps.anomalies && !caps.simulation && !caps.early_warning && (
        <p className="muted">Anomalies / simulation / early-warning masqués (capabilities à false).</p>
      )}
    </div>
  );
}
