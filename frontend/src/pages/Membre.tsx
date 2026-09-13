import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, money, type MembreDetail } from "../api/client";

export default function Membre() {
  const { id } = useParams();
  const [m, setM] = useState<MembreDetail | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.membre(Number(id)).then(setM).catch((e) => setErr(String(e)));
  }, [id]);

  if (err) return <div className="page error">{err}</div>;
  if (!m) return <div className="page">Chargement…</div>;

  const bloqué = m.statut !== "actif" || m.compte?.statut !== "actif";

  return (
    <div className="page">
      <h1>
        {m.prenom} {m.nom}
      </h1>
      <p className="lede">
        {m.code_externe} · adhésion {m.date_adhesion} · {m.anciennete_mois} mois
      </p>
      <div className="grid two">
        <section className="block">
          <h2>Compte</h2>
          {m.compte ? (
            <div className="kv">
              <span>N°</span>
              <strong>{m.compte.numero}</strong>
              <span>Statut</span>
              <span className={`badge ${m.compte.statut === "actif" ? "ok" : "bad"}`}>{m.compte.statut}</span>
              <span>Solde</span>
              <strong>{money(m.compte.solde)}</strong>
              <span>Épargne moy. 6 mois</span>
              <strong>{money(m.compte.epargne_moy_6m)}</strong>
            </div>
          ) : (
            <p>Pas de compte — ouverture obligatoire.</p>
          )}
          {m.thin_file && <p className="badge warn">Thin-file / historique léger</p>}
        </section>
        <section className="block">
          <h2>Incidents</h2>
          {m.incidents.length === 0 && <p className="muted">Aucun incident.</p>}
          {m.incidents.map((i, idx) => (
            <p key={idx}>
              <span className="badge bad">{i.gravite}</span> {i.type} — {i.detail}
            </p>
          ))}
        </section>
      </div>
      <section className="block" style={{ marginTop: "0.9rem" }}>
        <h2>Crédits passés</h2>
        <table>
          <thead>
            <tr>
              <th>Montant</th>
              <th>Statut</th>
              <th>Retards</th>
              <th>Jours max</th>
            </tr>
          </thead>
          <tbody>
            {m.credits_passes.map((c, i) => (
              <tr key={i}>
                <td>{money(c.montant)}</td>
                <td>{c.statut}</td>
                <td>{c.nb_retards}</td>
                <td>{c.jours_max_retard}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {m.credits_passes.length === 0 && <p className="muted">Aucun crédit interne.</p>}
      </section>
      <div className="actions">
        {bloqué ? (
          <p className="error">Compte inactif ou gelé : aucune demande possible.</p>
        ) : (
          <Link className="btn" to={`/membres/${m.id}/demande`}>
            Nouvelle demande
          </Link>
        )}
      </div>
    </div>
  );
}
