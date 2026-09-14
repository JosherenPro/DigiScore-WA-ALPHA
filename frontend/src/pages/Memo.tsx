import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, money, type AmortOut, type MemoOut } from "../api/client";

export default function Memo() {
  const { id } = useParams();
  const [m, setM] = useState<MemoOut | null>(null);
  const [am, setAm] = useState<AmortOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.memo(Number(id)).then(setM).catch((e) => setErr(e instanceof Error ? e.message : String(e)));
    api.amortissement(Number(id)).then(setAm).catch(() => undefined);
  }, [id]);

  if (err) return <div className="page error">{err}</div>;
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
          <span>{m.avis || "—"}</span>
          {m.analyse && (
            <>
              <span>CAF</span>
              <strong>{money(m.analyse.caf)}</strong>
              <span>RCSD</span>
              <strong>{m.analyse.rcsd.toFixed(2)}</strong>
              <span>EBE</span>
              <strong>{money(m.analyse.ebe)}</strong>
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
          <h2>
            Amortissement sur le montant éligible ({money(am.montant)} / {am.duree_mois} mois)
          </h2>
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
              {am.lignes.map((l, i) => (
                <tr key={Number(l.numero ?? i)}>
                  <td>{String(l.numero ?? i + 1)}</td>
                  <td>{money(Number(l.echeance ?? 0))}</td>
                  <td>{money(Number(l.capital ?? 0))}</td>
                  <td>{money(Number(l.interet ?? 0))}</td>
                  <td>{money(Number(l.restant ?? 0))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <div className="actions">
        <Link className="btn ghost" to={`/demandes/${id}`}>
          Retour au résultat
        </Link>
      </div>
    </div>
  );
}
