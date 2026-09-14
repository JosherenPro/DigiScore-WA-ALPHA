import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, money, type CompteExterne, type HistoriqueMembre, type MembreDetail, type Mouvement } from "../api/client";
import Pager from "../components/Pager";

export default function Membre() {
  const { id } = useParams();
  const mid = Number(id);
  const [m, setM] = useState<MembreDetail | null>(null);
  const [hist, setHist] = useState<HistoriqueMembre | null>(null);
  const [mvPage, setMvPage] = useState({ items: [] as Mouvement[], page: 1, total: 0 });
  const [ext, setExt] = useState<CompteExterne[]>([]);
  const [extMv, setExtMv] = useState({ items: [] as Mouvement[], page: 1, total: 0 });
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!mid) return;
    setErr("");
    Promise.all([
      api.membre(mid),
      api.historique(mid),
      api.mouvements(mid, 1),
      api.comptesExternes(mid),
      api.mouvementsExternes(mid, 1),
    ])
      .then(([fiche, h, mv, comptes, em]) => {
        setM(fiche);
        setHist(h);
        setMvPage({ items: mv.items, page: mv.page, total: mv.total });
        setExt(comptes);
        setExtMv({ items: em.items, page: em.page, total: em.total });
      })
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, [mid]);

  if (err) return <div className="page error">{err}</div>;
  if (!m) return <div className="page">Chargement…</div>;

  const bloqué = m.statut !== "actif" || m.compte?.statut !== "actif";

  return (
    <div className="page">
      <h1>
        {m.prenom} {m.nom}
      </h1>
      <p className="lede">
        {m.code_externe}
        {m.occupation ? ` · ${m.occupation}` : ""} · {m.anciennete_mois} mois
        {m.agence ? ` · ${m.agence.nom}` : ""}
        {m.telephone ? ` · ${m.telephone}` : ""}
      </p>
      {m.thin_file && (
        <div className="banner-thin">Thin-file : historique interne léger. Le moteur le signalera à l’analyse.</div>
      )}
      <div className="grid two">
        <section className="block">
          <h2>Compte — cette COOPEC</h2>
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
              <span>Mouvements</span>
              <strong>{m.nb_mouvements}</strong>
            </div>
          ) : (
            <p>Pas de compte — ouverture obligatoire.</p>
          )}
        </section>
        <section className="block">
          <h2>Incidents</h2>
          {(hist?.incidents || m.incidents).length === 0 && <p className="muted">Aucun incident.</p>}
          {(hist?.incidents || m.incidents).map((i, idx) => (
            <p key={idx}>
              <span className="badge bad">{i.gravite}</span> {i.type} — {i.detail}{" "}
              <span className="muted">{i.date}</span>
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
              <th>Source</th>
              <th>Institution</th>
              <th>Retards</th>
            </tr>
          </thead>
          <tbody>
            {(hist?.credits_passes || m.credits_passes).map((c, i) => (
              <tr key={i}>
                <td>{money(c.montant)}</td>
                <td>{c.statut}</td>
                <td>{c.source || "—"}</td>
                <td>{c.institution || "agence"}</td>
                <td>
                  {c.nb_retards} / {c.jours_max_retard} j
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(hist?.credits_passes || m.credits_passes).length === 0 && <p className="muted">Aucun crédit passé.</p>}
      </section>

      <section className="block" style={{ marginTop: "0.9rem" }}>
        <h2>Mouvements agence</h2>
        <p className="ledger-note">Livre de cette COOPEC seulement — pas mélangé avec un relevé ailleurs.</p>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Montant</th>
              <th>Libellé</th>
            </tr>
          </thead>
          <tbody>
            {mvPage.items.map((x, i) => (
              <tr key={i}>
                <td>{x.date}</td>
                <td>{x.type}</td>
                <td>{money(x.montant)}</td>
                <td>{x.libelle}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {mvPage.total === 0 && <p className="muted">Aucun mouvement agence.</p>}
        <Pager
          page={mvPage.page}
          pageSize={30}
          total={mvPage.total}
          onPage={(p) =>
            api.mouvements(mid, p).then((r) => setMvPage({ items: r.items, page: r.page, total: r.total }))
          }
        />
      </section>

      {m.nb_comptes_externes > 0 && (
        <section className="block" style={{ marginTop: "0.9rem" }}>
          <h2>Ailleurs — autre COOPEC / banque / IMF</h2>
          <p className="ledger-note">Preuve d’historique hors agence. Pas Flooz / T-Money. Ne change pas le solde local.</p>
          {ext.map((c) => (
            <div className="kv" key={c.id} style={{ marginBottom: "0.8rem" }}>
              <span>Institution</span>
              <strong>
                {c.institution?.nom} ({c.institution?.type})
              </strong>
              <span>N° masqué</span>
              <span>{c.numero_masque}</span>
              <span>Solde</span>
              <strong>{money(c.solde)}</strong>
            </div>
          ))}
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Montant</th>
                <th>Libellé</th>
              </tr>
            </thead>
            <tbody>
              {extMv.items.map((x, i) => (
                <tr key={i}>
                  <td>{x.date}</td>
                  <td>{x.type}</td>
                  <td>{money(x.montant)}</td>
                  <td>{x.libelle}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pager
            page={extMv.page}
            pageSize={30}
            total={extMv.total}
            onPage={(p) =>
              api.mouvementsExternes(mid, p).then((r) => setExtMv({ items: r.items, page: r.page, total: r.total }))
            }
          />
        </section>
      )}

      <div className="actions">
        {bloqué ? (
          <p className="error">Compte inactif / gelé — demande impossible (cas MEM-010).</p>
        ) : (
          <Link className="btn" to={`/membres/${m.id}/demande`}>
            Nouvelle demande
          </Link>
        )}
      </div>
    </div>
  );
}
