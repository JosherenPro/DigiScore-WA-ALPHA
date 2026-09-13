import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, type DemandeResume } from "../api/client";
import { getUser } from "../auth";

export default function Queue({ kind }: { kind: "chef" | "cic" }) {
  const user = getUser();
  const [rows, setRows] = useState<DemandeResume[]>([]);
  const [motif, setMotif] = useState("");
  const [err, setErr] = useState("");
  const niveau = kind === "chef" ? "chef_agence" : "cic";

  function load() {
    (kind === "chef" ? api.fileChef() : api.fileCic()).then(setRows).catch((e) => setErr(String(e)));
  }

  useEffect(load, [kind]);

  async function act(id: number, avis: string, override = false) {
    setErr("");
    try {
      await api.decision(id, {
        niveau,
        avis,
        motif: motif || null,
        utilisateur_id: user?.id ?? 1,
        override,
      });
      setMotif("");
      load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <h1>{kind === "chef" ? "File chef d’agence" : "File CIC"}</h1>
      <p className="lede">Avis humain obligatoire. Motif requis si écart à la recommandation.</p>
      <label className="field">
        Motif (override / renvoi)
        <input value={motif} onChange={(e) => setMotif(e.target.value)} />
      </label>
      {err && <p className="error">{err}</p>}
      <div className="list" style={{ marginTop: "1rem" }}>
        {rows.length === 0 && <p className="muted">Aucun dossier en file.</p>}
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
                  <button className="btn teal" onClick={() => act(d.id, "valider")}>
                    Valider
                  </button>
                  <button className="btn danger" onClick={() => act(d.id, "refuser")}>
                    Refuser
                  </button>
                  <button className="btn ghost" onClick={() => act(d.id, "renvoyer")}>
                    Renvoyer
                  </button>
                  <button className="btn warn" onClick={() => act(d.id, "escalader")}>
                    CIC
                  </button>
                </div>
              ) : (
                <div className="actions">
                  <button className="btn teal" onClick={() => act(d.id, "accorder")}>
                    Accorder
                  </button>
                  <button className="btn warn" onClick={() => act(d.id, "conditionner")}>
                    Conditionner
                  </button>
                  <button className="btn danger" onClick={() => act(d.id, "refuser")}>
                    Refuser
                  </button>
                </div>
              )}
            </div>
            <span className="badge">{d.score != null ? `${Math.round(d.score)}/100` : "—"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
