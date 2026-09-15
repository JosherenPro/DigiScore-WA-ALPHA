import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  money,
  type BicOut,
  type CompteExterne,
  type DemandeResume,
  type HistoriqueMembre,
  type MembreDetail,
  type Mouvement,
  type PretEnCours,
  type RecouvrementMembre,
  type SuiviMembre,
} from "../api/client";
import Pager from "../components/Pager";
import Spinner from "../components/Spinner";
import Alert from "../components/Alert";
import Section from "../components/Section";
import { useApi } from "../hooks/useApi";

type Fiche = {
  membre: MembreDetail;
  hist: HistoriqueMembre;
  mv: { items: Mouvement[]; page: number; total: number };
  ext: CompteExterne[];
  extMv: { items: Mouvement[]; page: number; total: number };
  bic: BicOut | null;
  prets: PretEnCours[];
  suivi: SuiviMembre[];
  recouvrement: RecouvrementMembre[];
  demandes: DemandeResume[];
};

// Les sous-ressources de la fiche (BIC, encours, suivi terrain, recouvrement)
// sont accessoires : si l'une echoue, la fiche doit rester affichable.
function optionnel<T>(p: Promise<T>, defaut: T): Promise<T> {
  return p.catch(() => defaut);
}

const VISITE_LABEL: Record<string, string> = {
  V1: "V1 — relance amiable",
  V2: "V2 — visite terrain",
  V3: "V3 — mise en demeure",
};

export default function Membre() {
  const { id } = useParams();
  const mid = Number(id);
  const [mvPage, setMvPage] = useState({ items: [] as Mouvement[], page: 1, total: 0 });
  const [extMv, setExtMv] = useState({ items: [] as Mouvement[], page: 1, total: 0 });

  const { data, error, loading } = useApi<Fiche>(async () => {
    const [membre, hist, mv, ext, extMvRes, bic, prets, suivi, recouvrement, demandes] = await Promise.all([
      api.membre(mid),
      api.historique(mid),
      api.mouvements(mid, 1),
      api.comptesExternes(mid),
      api.mouvementsExternes(mid, 1),
      optionnel<BicOut | null>(api.membreBic(mid), null),
      optionnel(api.membrePrets(mid), []),
      optionnel(api.membreSuivi(mid), []),
      optionnel(api.membreRecouvrement(mid), []),
      optionnel(api.membreDemandes(mid, 1, 5).then((r) => r.items), []),
    ]);
    setMvPage(mv);
    setExtMv(extMvRes);
    return { membre, hist, mv, ext, extMv: extMvRes, bic, prets, suivi, recouvrement, demandes };
  }, [mid]);

  if (error) return <div className="page"><Alert kind="error">{error}</Alert></div>;
  if (loading || !data) return <div className="page"><Spinner /></div>;

  const m = data.membre;
  const hist = data.hist;
  const ext = data.ext;
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
      <div className="actions membre-cta">
        {bloqué ? (
          <p className="error">
            Compte {m.statut !== "actif" ? m.statut : "inactif"} — aucune demande de crédit possible.
          </p>
        ) : (
          <Link className="btn primary" to={`/membres/${m.id}/demande`}>
            Souscrire un nouveau crédit
          </Link>
        )}
      </div>
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

      {(data.prets.length > 0 || data.bic?.rapport || data.bic?.consentement) && (
        <div className="grid two mt-md">
          {data.prets.length > 0 && (
            <section className="block">
              <h2>Encours en cours</h2>
              <div className="list">
                {data.prets.map((p, i) => (
                  <div className="row" key={i}>
                    <div>
                      <strong>{money(p.encours)}</strong>
                      <div className="muted">
                        sur {money(p.principal)} · {p.statut}
                        {p.echeance ? ` · échéance ${p.echeance}` : ""}
                      </div>
                    </div>
                    <span className={`badge rect ${p.jours_retard > 30 ? "bad" : p.jours_retard > 0 ? "warn" : "ok"}`}>
                      {p.jours_retard > 0 ? `${p.jours_retard} j de retard` : "à jour"}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {(data.bic?.rapport || data.bic?.consentement) && (
            <section className="block">
              <h2>Centrale des risques (BIC)</h2>
              <p className="ledger-note">
                Consultation soumise au consentement écrit du membre — sans consentement signé, pas d’interrogation.
              </p>
              <div className="kv">
                <span>Consentement</span>
                {data.bic.consentement ? (
                  <span className={`badge ${data.bic.consentement.statut === "signe" ? "ok" : "warn"}`}>
                    {data.bic.consentement.statut}
                    {data.bic.consentement.signe_le ? ` · ${data.bic.consentement.signe_le}` : ""}
                  </span>
                ) : (
                  <span className="badge warn">absent</span>
                )}
                {data.bic.rapport && (
                  <>
                    <span>Crédits externes</span>
                    <strong>{data.bic.rapport.nb_credits_externes}</strong>
                    <span>Incidents BIC</span>
                    <strong>{data.bic.rapport.nb_incidents}</strong>
                    <span>Synthèse</span>
                    <span>{data.bic.rapport.synthese || "—"}</span>
                  </>
                )}
              </div>
            </section>
          )}
        </div>
      )}

      {m.garanties?.length > 0 && (
        <section className="block mt-md">
          <h2>Garanties déclarées</h2>
          <div className="list">
            {m.garanties.map((g, i) => (
              <div className="row" key={i}>
                <strong>{g.nature}</strong>
                <span>{money(g.valeur)}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {data.suivi.length > 0 && (
        <Section titre="Suivi terrain" compteur={data.suivi.length}>
          <div className="list">
            {data.suivi.map((v, i) => (
              <div className="row" key={i}>
                <div>
                  <strong>{VISITE_LABEL[v.visite] || v.visite}</strong>
                  <div className="muted">
                    {v.date || "date inconnue"}
                    {v.signal ? ` · ${v.signal}` : ""}
                  </div>
                </div>
                {v.jours_retard != null && v.jours_retard > 0 && (
                  <span className="badge rect warn">{v.jours_retard} j</span>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {data.recouvrement.length > 0 && (
        <Section titre="Recouvrement" compteur={data.recouvrement.length}>
          {data.recouvrement.map((r, i) => (
            <div key={i} className="mb-sm">
              <div className="row">
                <div>
                  <strong>Niveau N{r.niveau} — {r.action || "action non précisée"}</strong>
                  <div className="muted">
                    {r.responsable ? `${r.responsable} · ` : ""}
                    {r.ouvert_le ? `ouvert le ${r.ouvert_le}` : ""}
                  </div>
                </div>
              </div>
              {r.journal.length > 0 && (
                <ul className="muted">
                  {r.journal.map((j, k) => (
                    <li key={k}>
                      {j.date || "—"} · {j.type}
                      {j.note ? ` — ${j.note}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </Section>
      )}

      {data.demandes.length > 0 && (
        <Section titre="Demandes de ce membre" compteur={data.demandes.length}>
          <div className="list">
            {data.demandes.map((dem) => (
              <div className="row" key={dem.id}>
                <div>
                  <Link to={`/demandes/${dem.id}`}>
                    <strong>Dossier #{dem.id}</strong>
                  </Link>
                  <div className="muted">
                    {money(dem.montant_demande)}
                    {dem.score != null ? ` · score ${Math.round(dem.score)}/100` : ""}
                    {dem.message_code ? ` · ${dem.message_code}` : ""}
                  </div>
                </div>
                <span className="badge rect">{dem.statut}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section titre="Crédits passés" compteur={(hist?.credits_passes || m.credits_passes).length}>
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
      </Section>

      <Section titre="Mouvements agence" compteur={mvPage.total} resume="Livre de cette COOPEC">
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
        <Pager
          page={mvPage.page}
          pageSize={30}
          total={mvPage.total}
          onPage={(p) =>
            api.mouvements(mid, p).then((r) => setMvPage({ items: r.items, page: r.page, total: r.total }))
          }
        />
      </Section>

      {m.nb_comptes_externes > 0 && (
        <Section
          titre="Ailleurs — autre COOPEC / banque / IMF"
          compteur={ext.length}
          resume="Preuve d’historique hors agence"
        >
          <p className="ledger-note">Preuve d’historique hors agence. Pas Flooz / T-Money. Ne change pas le solde local.</p>
          {ext.map((c) => (
            <div className="kv mb-sm" key={c.id}>
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
        </Section>
      )}


    </div>
  );
}
