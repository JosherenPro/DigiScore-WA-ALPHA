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
      <p className="lede">4 niveaux de recouvrement — dossiers et journal d'actions.</p>
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
    </div>
  );
}
