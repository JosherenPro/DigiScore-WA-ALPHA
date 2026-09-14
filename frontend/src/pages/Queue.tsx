import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, zoneClass, type DemandeResume } from "../api/client";
import { getUser } from "../auth";
import Pager from "../components/Pager";

const PAGE = 30;

export default function Queue({ kind }: { kind: "chef" | "cic" }) {
  const user = getUser();
  const [rows, setRows] = useState<DemandeResume[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [motif, setMotif] = useState("");
  const [err, setErr] = useState("");
  const niveau = kind === "chef" ? "chef_agence" : "cic";

  async function load(p = 1) {
    setErr("");
    try {
      const res = kind === "chef" ? await api.fileChef(p, PAGE) : await api.fileCic(p, PAGE);
      setRows(res.items);
      setPage(res.page);
      setTotal(res.total);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    }
  }

  useEffect(() => {
    load(1);
  }, [kind]);

  async function act(id: number, avis: string, override = false) {
    setErr("");
    try {
      await api.decision(id, { niveau, avis, motif: motif || null, override });
      setMotif("");
      load(page);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <h1>{kind === "chef" ? "File chef d’agence" : "File CIC"}</h1>
      <p className="lede">
        Avis humain obligatoire. Motif requis si écart à la recommandation. Connecté : {user?.nom}.
      </p>
      <label className="field">
        Motif (override / renvoi)
        <input value={motif} onChange={(e) => setMotif(e.target.value)} />
      </label>
      {err && <p className="error">{err}</p>}
      <div className="list" style={{ marginTop: "1rem" }}>
        {rows.length === 0 && !err && <p className="muted">Aucun dossier en file.</p>}
        {rows.map((d) => (
          <div className="row" key={d.id}>
            <div>
              <Link to={`/demandes/${d.id}`}>
                <strong>
                  #{d.id} {d.membre}
                </strong>
              </Link>
              <div className="muted">
                {money(d.montant_demande)} · {d.message_code || "sans score"} · {d.zone || "—"}
              </div>
              {kind === "chef" ? (
                <div className="actions">
                  <button className="btn teal sm" type="button" onClick={() => act(d.id, "valider")}>
                    Valider
                  </button>
                  <button className="btn danger sm" type="button" onClick={() => act(d.id, "refuser", true)}>
                    Refuser
                  </button>
                  <button className="btn ghost sm" type="button" onClick={() => act(d.id, "renvoyer")}>
                    Renvoyer
                  </button>
                  <button className="btn warn sm" type="button" onClick={() => act(d.id, "escalader")}>
                    CIC
                  </button>
                </div>
              ) : (
                <div className="actions">
                  <button className="btn teal sm" type="button" onClick={() => act(d.id, "accorder")}>
                    Accorder
                  </button>
                  <button className="btn warn sm" type="button" onClick={() => act(d.id, "conditionner")}>
                    Conditionner
                  </button>
                  <button className="btn danger sm" type="button" onClick={() => act(d.id, "refuser", true)}>
                    Refuser
                  </button>
                </div>
              )}
            </div>
            <span className={`badge ${zoneClass(d.zone)}`}>{d.score != null ? `${Math.round(d.score)}/100` : "—"}</span>
          </div>
        ))}
      </div>
      <Pager page={page} pageSize={PAGE} total={total} onPage={load} />
    </div>
  );
}
