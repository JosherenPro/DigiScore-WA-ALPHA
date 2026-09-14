import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, zoneClass, type DemandeResume, type MembreResume } from "../api/client";
import Pager from "../components/Pager";

const PAGE = 30;

export default function AgentHome({ dossiers = false }: { dossiers?: boolean }) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [membres, setMembres] = useState<MembreResume[]>([]);
  const [rows, setRows] = useState<DemandeResume[]>([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadMembres(query: string, p: number) {
    setBusy(true);
    setErr("");
    try {
      const res = await api.membres(query, p, PAGE);
      setMembres(res.items);
      setTotal(res.total);
      setPage(res.page);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function loadDemandes(p: number) {
    setBusy(true);
    setErr("");
    try {
      const res = await api.demandes({ page: p, pageSize: PAGE });
      setRows(res.items);
      setTotal(res.total);
      setPage(res.page);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (dossiers) loadDemandes(1);
    else loadMembres("", 1);
  }, [dossiers]);

  if (dossiers) {
    return (
      <div className="page">
        <h1>Dossiers</h1>
        <p className="lede">Demandes en base — ouvre un dossier pour le score, le mémo ou la soumission.</p>
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
              <span className={`badge ${zoneClass(d.zone)}`}>
                {d.score != null ? `${Math.round(d.score)}/100` : "—"}
              </span>
            </Link>
          ))}
        </div>
        {!busy && rows.length === 0 && !err && <p className="muted">Aucun dossier.</p>}
        <Pager page={page} pageSize={PAGE} total={total} onPage={loadDemandes} />
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Membre d’abord</h1>
      <p className="lede">Code MEM-001, nom, ou n° de compte. Pas de demande sans compte actif. Ne charge pas 120 000 lignes d’un coup.</p>
      <form
        className="search-row"
        onSubmit={(e) => {
          e.preventDefault();
          loadMembres(q, 1);
        }}
      >
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="MEM-001, Mensah, CPT-001, VOL-…" />
        <button className="btn" type="submit" disabled={busy}>
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
              <div className="muted">
                {m.code_externe} · adhésion {m.date_adhesion}
              </div>
            </div>
            <span className={`badge ${m.statut === "actif" ? "ok" : "bad"}`}>{m.statut}</span>
          </Link>
        ))}
      </div>
      {!busy && membres.length === 0 && !err && <p className="muted">Aucun membre sur cette page.</p>}
      <Pager page={page} pageSize={PAGE} total={total} onPage={(p) => loadMembres(q, p)} />
    </div>
  );
}
