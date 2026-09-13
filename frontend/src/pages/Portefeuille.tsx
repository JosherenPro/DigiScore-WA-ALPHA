import { useEffect, useState } from "react";
import { api, type M6Out } from "../api/client";

export default function Portefeuille() {
  const [d, setD] = useState<M6Out | null>(null);
  useEffect(() => {
    api.portefeuille().then(setD);
  }, []);
  if (!d) return <div className="page">Chargement…</div>;
  return (
    <div className="page">
      <h1>Suivi portefeuille</h1>
      <p className="lede">Maquette M6 — chiffres seed, pas de moteur PAR live.</p>
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
            {d.par.map((p) => (
              <tr key={p.agence_id}>
                <td>{p.agence_id}</td>
                <td>{p.par30} %</td>
                <td>{p.par90} %</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="block" style={{ marginTop: "0.9rem" }}>
        <h2>Alertes</h2>
        {d.alertes.map((a, i) => (
          <p key={i}>
            Membre {a.membre_id} — {a.signal}
          </p>
        ))}
      </section>
    </div>
  );
}
