import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, money, type AmortOut, type MemoOut } from "../api/client";

export default function Memo() {
  const { id } = useParams();
  const [m, setM] = useState<MemoOut | null>(null);
  const [am, setAm] = useState<AmortOut | null>(null);

  useEffect(() => {
    api.memo(Number(id)).then(setM);
    api.amortissement(Number(id)).then(setAm).catch(() => undefined);
  }, [id]);

  if (!m) return <div className="page">Chargement…</div>;

  return (
    <div className="page">
      <h1>{m.titre}</h1>
      <p className="lede">
        {m.client} — {m.projet}
      </p>
      <section className="block">
        <div className="kv">
          <span>Montant demandé</span>
          <strong>{money(m.demande)}</strong>
          <span>Avis moteur</span>
          <span>{m.avis}</span>
          {m.analyse && (
            <>
              <span>RCSD</span>
              <strong>{m.analyse.rcsd.toFixed(2)}</strong>
            </>
          )}
        </div>
      </section>
      <section className="block" style={{ marginTop: "0.9rem" }}>
        <h2>Rubriques comité</h2>
        {m.rubriques.map((r) => (
          <p key={r}>{r}</p>
        ))}
      </section>
      {am && (
        <section className="block" style={{ marginTop: "0.9rem" }}>
          <h2>Amortissement ({money(am.montant)} / {am.duree_mois} mois)</h2>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Échéance</th>
                <th>Capital</th>
                <th>Intérêt</th>
                <th>Restant</th>
              </tr>
            </thead>
            <tbody>
              {am.lignes.slice(0, 6).map((l) => (
                <tr key={l.numero}>
                  <td>{l.numero}</td>
                  <td>{money(l.echeance)}</td>
                  <td>{money(l.capital)}</td>
                  <td>{money(l.interet)}</td>
                  <td>{money(l.restant)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {am.lignes.length > 6 && <p className="muted">+ {am.lignes.length - 6} échéances</p>}
        </section>
      )}
    </div>
  );
}
