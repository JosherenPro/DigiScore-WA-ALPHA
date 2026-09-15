import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, zoneClass, type AlertePortefeuille, type Capabilities, type DemandeStats } from "../api/client";
import { getUser } from "../auth";
import Alert from "../components/Alert";
import Spinner from "../components/Spinner";
import { STATUS_LABEL } from "../components/DossierCard";
import { TrendChart } from "../components/charts";

const ZONE_LABEL: Record<string, string> = {
  approbation: "Approbation",
  analyse: "Analyse",
  rejet: "Rejet",
  non_analyse: "Non analysé",
};

/** Tableau de bord de l'agent — agrégats réels (GET /demandes/stats), pas de
 * boucle côté front sur des milliers de dossiers. Onglet à part entière de la
 * navigation (plus un sous-onglet de la page Dossiers). */
export default function Dashboard() {
  const user = getUser();
  const [stats, setStats] = useState<DemandeStats | null>(null);
  const [err, setErr] = useState("");
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [ewAlertes, setEwAlertes] = useState<AlertePortefeuille[] | null>(null);
  const [ewModel, setEwModel] = useState("");

  useEffect(() => {
    setErr("");
    api.demandeStats(user?.id).then(setStats).catch((e) => setErr(e instanceof Error ? e.message : "Erreur"));
    api.capabilities().then(setCaps).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!caps?.early_warning) return;
    api
      .alertesPortefeuille(10)
      .then((r) => {
        setEwAlertes(r.items);
        setEwModel(r.model_version);
      })
      .catch(() => undefined);
  }, [caps]);

  if (err) return <div className="page"><Alert kind="error">{err}</Alert></div>;
  if (!stats) return <div className="page"><Spinner /></div>;

  const zones = ["approbation", "analyse", "rejet", "non_analyse"].filter((z) => stats.par_zone[z]);
  const statuts = Object.entries(stats.par_statut).sort((a, b) => b[1] - a[1]);

  const totalExposure = ewAlertes?.reduce((sum, a) => sum + a.exposure, 0) ?? 0;

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <p className="lede">Vue d’ensemble de tes dossiers — agrégats calculés en temps réel.</p>

      {caps?.early_warning && (
        <section className="block ml">
          <div className="ml-h2-row">
            <span className="ml-tag">Éclairage ML — consultatif, jamais décisionnel</span>
            {ewModel && <span className="badge">modèle {ewModel}</span>}
          </div>
          <h2>Early warning — risque de retard à 30–90 jours sur ton portefeuille</h2>
          {ewAlertes === null && <Spinner />}
          {ewAlertes?.length === 0 && <p className="muted">Rien à signaler sur ton portefeuille pour l’instant.</p>}
          {ewAlertes && ewAlertes.length > 0 && (
            <>
              <div className="stat-row">
                <div className="stat-tile">
                  <span className="muted">Membres à surveiller</span>
                  <strong>{ewAlertes.length}</strong>
                </div>
                <div className="stat-tile">
                  <span className="muted">Exposition concernée</span>
                  <strong>{money(totalExposure)}</strong>
                </div>
                <div className="stat-tile">
                  <span className="muted">Risque le plus élevé</span>
                  <strong>{Math.round(Math.max(...ewAlertes.map((a) => a.p_par30_90j)) * 100)} %</strong>
                </div>
              </div>
              <ul className="ml-factors mt-sm">
                {ewAlertes.slice(0, 3).map((a) => (
                  <li key={a.member_code}>
                    <strong>{a.member_code}</strong> — {Math.round(a.p_par30_90j * 100)} % de risque · {money(a.exposure)}
                    {a.signals.length > 0 ? ` · ${a.signals.join(", ")}` : ""}
                  </li>
                ))}
              </ul>
              <Link className="btn ghost sm mt-sm" to="/m6">
                Voir tout le portefeuille →
              </Link>
            </>
          )}
        </section>
      )}

      <section className="block dashboard-head mt-md">
        <div className="stat-row stat-row-4">
          <div className="stat-tile">
            <span className="muted">Total dossiers</span>
            <strong>{stats.total}</strong>
          </div>
          <div className="stat-tile">
            <span className="muted">Score moyen</span>
            <strong>{stats.score_moyen != null ? Math.round(stats.score_moyen) : "—"}</strong>
          </div>
          <div className="stat-tile">
            <span className="muted">Montant demandé (total)</span>
            <strong>{money(stats.montant_total_demande)}</strong>
          </div>
          <div className="stat-tile">
            <span className="muted">Montant éligible (total)</span>
            <strong>{money(stats.montant_total_eligible)}</strong>
          </div>
        </div>
      </section>

      {stats.serie_creations.length > 1 && (
        <section className="block mt-md">
          <h2>Dossiers créés par semaine</h2>
          <TrendChart points={stats.serie_creations} />
        </section>
      )}

      <section className="block mt-md">
        <h2>Répartition par niveau</h2>
        <div className="zone-tiles">
          {zones.map((z) => (
            <div className={`zone-tile ${zoneClass(z === "non_analyse" ? undefined : z)}`} key={z}>
              <strong>{stats.par_zone[z]}</strong>
              <span>{ZONE_LABEL[z] || z}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="block mt-md">
        <h2>Répartition par statut</h2>
        <div className="status-tiles">
          {statuts.map(([code, n]) => (
            <span className="badge rect" key={code}>
              {STATUS_LABEL[code] || code} · {n}
            </span>
          ))}
        </div>
      </section>

      {stats.nb_credits_ailleurs > 0 && (
        <p className="muted mt-md">
          {stats.nb_credits_ailleurs} dossier{stats.nb_credits_ailleurs > 1 ? "s" : ""} avec un crédit ailleurs déclaré.
        </p>
      )}
    </div>
  );
}
