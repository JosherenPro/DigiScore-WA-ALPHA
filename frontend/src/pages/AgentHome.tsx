import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, type DemandeResume, type MembreResume } from "../api/client";

export default function AgentHome({ dossiers = false }: { dossiers?: boolean }) {
  const [q, setQ] = useState("");
  const [membres, setMembres] = useState<MembreResume[]>([]);
  const [rows, setRows] = useState<DemandeResume[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (dossiers) {
      api.demandes().then(setRows).catch((e) => setErr(String(e)));
    } else {
      api.membres("").then(setMembres).catch((e) => setErr(String(e)));
    }
  }, [dossiers]);

  async function search(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      setMembres(await api.membres(q));
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Erreur");
    }
  }

  if (dossiers) {
    return (
      <div className="page">
        <h1>Dossiers</h1>
        <p className="lede">Demandes seed + nouvelles saisies.</p>
        {err && <p className="error">{err}</p>}
        <div className="list">
          {rows.map((d) => (
            <Link className="row" key={d.id} to={`/demandes/${d.id}`}>
              <div>
                <strong>
                  #{d.id} {d.membre}
                </strong>
                <div className="muted">
                  {money(d.montant_demande)} · {d.statut}
                  {d.message_code ? ` · ${d.message_code}` : ""}
                </div>
              </div>
              <span className="badge">{d.score != null ? `${Math.round(d.score)}/100` : "—"}</span>
            </Link>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Membre d’abord</h1>
      <p className="lede">Recherche par code (MEM-001) ou nom. Pas de demande sans compte actif.</p>
      <form className="search-row" onSubmit={search}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="MEM-001, Mensah, Slim…" />
        <button className="btn" type="submit">
          Chercher
        </button>
      </form>
      {err && <p className="error">{err}</p>}
      <div className="list">
        {membres.map((m) => (
          <Link className="row" key={m.id} to={`/membres/${m.id}`}>
            <div>
              <strong>
                {m.prenom} {m.nom}
              </strong>
              <div className="muted">{m.code_externe}</div>
            </div>
            <span className={`badge ${m.statut === "actif" ? "ok" : "bad"}`}>{m.statut}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
