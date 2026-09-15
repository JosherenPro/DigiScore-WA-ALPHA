import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, zoneClass, type DemandeResume } from "../api/client";
import { getUser } from "../auth";
import Pager from "../components/Pager";
import Alert from "../components/Alert";
import Spinner from "../components/Spinner";
import PageSearch from "../components/PageSearch";

const PAGE = 30;

export default function Queue({ kind }: { kind: "chef" | "cic" }) {
  const user = getUser();
  const [rows, setRows] = useState<DemandeResume[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [motif, setMotif] = useState("");
  const [search, setSearch] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const niveau = kind === "chef" ? "chef_agence" : "cic";

  async function load(p = 1, q = search) {
    setErr("");
    setLoading(true);
    try {
      const res = kind === "chef" ? await api.fileChef(p, PAGE, q) : await api.fileCic(p, PAGE, q);
      setRows(res.items);
      setPage(res.page);
      setTotal(res.total);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setSearch("");
    load(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      <PageSearch value={search} onChange={setSearch} onSubmit={() => load(1, search)} placeholder="Rechercher un dossier (nom, code membre)…" />

      <label className="field">
        Motif (override / renvoi)
        <input value={motif} onChange={(e) => setMotif(e.target.value)} />
      </label>
      {err && <Alert kind="error">{err}</Alert>}
      <div className="list mt-lg">
        {loading && <Spinner />}
        {!loading && rows.length === 0 && !err && <p className="muted">Aucun dossier en file.</p>}
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
                  <button className="btn primary sm" type="button" onClick={() => act(d.id, "valider")}>
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
                  <button className="btn primary sm" type="button" onClick={() => act(d.id, "accorder")}>
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
