import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  money,
  zoneClass,
  type AgingOut,
  type AlertePortefeuille,
  type Capabilities,
  type DemandeStats,
} from "../api/client";
import { getUser } from "../auth";
import Alert from "../components/Alert";
import Spinner from "../components/Spinner";
import { STATUS_LABEL } from "../components/DossierCard";
import MlSection from "../components/MlSection";
import EarlyWarning from "../components/EarlyWarning";

/** Priorités de recouvrement, telles que les calcule `priorite()` côté service :
 * S = pas de retard, P3/P2 = retard croissant, P1 = gros encours ET retard. */
const PRIORITES: { code: string; libelle: string; tone: string }[] = [
  { code: "P1", libelle: "P1 — encours élevé en retard", tone: "bad" },
  { code: "P2", libelle: "P2 — retard installé", tone: "warn" },
  { code: "P3", libelle: "P3 — retard récent", tone: "" },
];

const BUCKET_LABEL: Record<string, string> = {
  courant: "Courant",
  "1-7": "1 à 7 j",
  "8-30": "8 à 30 j",
  "31-90": "31 à 90 j",
  ">90": "Plus de 90 j",
};

function parTone(label?: string | null): string {
  if (label === "critique") return "bad";
  if (label === "vigilance") return "warn";
  return "ok";
}

type Charge = { chef: number; cic: number; echeances: number };

/** Espace chef d'agence / CIC. Leur métier n'est pas de parcourir des dossiers
 * mais d'arbitrer et de répondre du portefeuille : cet écran réunit ce qui
 * attend une signature et l'état du risque dont ils sont comptables. Tout vient
 * d'agrégats serveur — aucune boucle front sur les 20 000 dossiers. */
export default function Revue() {
  const user = getUser();
  const estCic = user?.role === "cic";
  const [charge, setCharge] = useState<Charge | null>(null);
  const [stats, setStats] = useState<DemandeStats | null>(null);
  const [aging, setAging] = useState<AgingOut | null>(null);
  const [recouv, setRecouv] = useState<Record<string, number> | null>(null);
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [ew, setEw] = useState<AlertePortefeuille[] | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    // Chaque bloc se charge pour lui-même : le PAR ne doit pas retenir
    // l'affichage du nombre de dossiers à signer, qui est l'info urgente.
    Promise.all([
      api.fileChef(1, 1).then((r) => r.total).catch(() => 0),
      estCic ? api.fileCic(1, 1).then((r) => r.total).catch(() => 0) : Promise.resolve(0),
      api.echeances(1, 1).then((r) => r.total).catch(() => 0),
    ])
      .then(([chef, cic, echeances]) => setCharge({ chef, cic, echeances }))
      .catch((e) => setErr(e instanceof Error ? e.message : "Erreur"));

    api.demandeStats().then(setStats).catch(() => undefined);
    api.aging().then(setAging).catch(() => undefined);
    api.capabilities().then(setCaps).catch(() => undefined);

    // Un total par priorité, obtenu avec page_size=1 : on ne rapatrie pas
    // 2 000 dossiers pour en afficher le compte.
    Promise.all(
      PRIORITES.map((p) =>
        api
          .dossiersRecouvrement({ priorite: p.code, page: 1, pageSize: 1 })
          .then((r) => [p.code, r.total] as const)
          .catch(() => [p.code, 0] as const),
      ),
    ).then((paires) => setRecouv(Object.fromEntries(paires)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estCic]);

  useEffect(() => {
    if (!caps?.early_warning) return;
    api.alertesPortefeuille(5).then((r) => setEw(r.items)).catch(() => undefined);
  }, [caps]);

  if (err) return <div className="page"><Alert kind="error">{err}</Alert></div>;

  const aSigner = (charge?.chef ?? 0) + (estCic ? charge?.cic ?? 0 : 0);
  const decisions = stats
    ? (["accorde", "conditionne", "refuse", "renvoye"] as const)
        .map((code) => [code, stats.par_statut[code] || 0] as const)
        .filter(([, n]) => n > 0)
    : [];

  return (
    <div className="page">
      <h1>Espace {estCic ? "comité de crédit" : "Directeur (Chef d’Agence)"}</h1>
      <p className="lede">
        {estCic
          ? "Décision finale sur les dossiers escaladés, et surveillance du risque consolidé."
          : "Arbitrage des dossiers soumis par les agents, et santé du portefeuille de l’agence."}{" "}
        Connecté : {user?.nom}.
      </p>

      {/* 1. Ce qui attend une signature — l'action, avant l'analyse. */}
      <section className="block">
        <h2>À décider maintenant</h2>
        {!charge && <Spinner />}
        {charge && (
          <div className="revue-cta">
            <Link className={`revue-card${charge.chef > 0 ? " urgent" : ""}`} to="/chef">
              <span className="revue-num">{charge.chef}</span>
              <span className="revue-label">
                dossier{charge.chef > 1 ? "s" : ""} en file Directeur (Chef d’Agence)
              </span>
            </Link>
            {estCic && (
              <Link className={`revue-card${charge.cic > 0 ? " urgent" : ""}`} to="/cic">
                <span className="revue-num">{charge.cic}</span>
                <span className="revue-label">
                  dossier{charge.cic > 1 ? "s" : ""} escaladé{charge.cic > 1 ? "s" : ""} au CIC
                </span>
              </Link>
            )}
            <Link className="revue-card" to="/m6">
              <span className="revue-num">{charge.echeances}</span>
              <span className="revue-label">échéance{charge.echeances > 1 ? "s" : ""} en retard aujourd’hui</span>
            </Link>
          </div>
        )}
        {charge && aSigner === 0 && (
          <p className="muted">Aucune signature en attente — la file est vide.</p>
        )}
      </section>

      {/* 2. Le risque dont ils répondent. */}
      <section className="block mt-md">
        <div className="row">
          <h2 style={{ margin: 0 }}>Santé du portefeuille</h2>
          {aging && <span className={`badge rect ${parTone(aging.label)}`}>{aging.label}</span>}
        </div>
        {!aging && <Spinner />}
        {aging && (
          <>
            <div className="stat-row stat-row-4 mt-sm">
              <div className="stat-tile">
                <span className="muted">PAR 1</span>
                <strong>{aging.par1} %</strong>
              </div>
              <div className="stat-tile">
                <span className="muted">PAR 30</span>
                <strong className={aging.par30 > 5 ? "bad" : ""}>{aging.par30} %</strong>
              </div>
              <div className="stat-tile">
                <span className="muted">PAR 90</span>
                <strong className={aging.par90 > 2 ? "bad" : ""}>{aging.par90} %</strong>
              </div>
              <div className="stat-tile">
                <span className="muted">Encours brut</span>
                <strong>{money(aging.encours_brut)}</strong>
              </div>
            </div>
            <div className="revue-aging mt-sm">
              {aging.buckets.map((b) => (
                <div className="revue-aging-row" key={b.bucket}>
                  <span className="revue-aging-label">{BUCKET_LABEL[b.bucket] || b.bucket}</span>
                  <span className="revue-aging-track">
                    <span
                      className={`revue-aging-fill ${b.bucket === "courant" ? "ok" : b.bucket === ">90" || b.bucket === "31-90" ? "bad" : "warn"}`}
                      style={{ width: `${Math.max(b.part_pct, 0.5)}%` }}
                    />
                  </span>
                  <span className="revue-aging-value">
                    {b.part_pct} % <span className="muted">· {money(b.montant)}</span>
                  </span>
                </div>
              ))}
            </div>
            <Link className="btn ghost sm mt-sm" to="/m6">
              Détail du portefeuille →
            </Link>
          </>
        )}
      </section>

      {/* 3. Où mettre les agents en priorité. */}
      <section className="block mt-md">
        <h2>Priorités de recouvrement</h2>
        {!recouv && <Spinner />}
        {recouv && (
          <>
            <div className="stat-row">
              {PRIORITES.map((p) => (
                <div className="stat-tile" key={p.code}>
                  <span className="muted">{p.libelle}</span>
                  <strong className={p.tone}>{recouv[p.code] ?? 0}</strong>
                </div>
              ))}
            </div>
            <Link className="btn ghost sm mt-sm" to="/m7">
              Ouvrir le recouvrement →
            </Link>
          </>
        )}
      </section>

      {/* 4. Ce qui a déjà été tranché — le miroir de leur propre activité. */}
      {stats && (
        <section className="block mt-md">
          <h2>Décisions rendues</h2>
          <div className="status-tiles">
            {decisions.length === 0 && <p className="muted">Aucune décision enregistrée pour l’instant.</p>}
            {decisions.map(([code, n]) => (
              <span className={`badge rect ${code === "refuse" ? "bad" : code === "accorde" ? "ok" : "warn"}`} key={code}>
                {STATUS_LABEL[code] || code} · {n}
              </span>
            ))}
          </div>
          <div className="stat-row mt-sm">
            <div className="stat-tile">
              <span className="muted">Dossiers au total</span>
              <strong>{stats.total}</strong>
            </div>
            <div className="stat-tile">
              <span className="muted">Score moyen</span>
              <strong className={zoneClass(
                stats.score_moyen == null ? undefined : stats.score_moyen >= 70 ? "approbation" : stats.score_moyen >= 50 ? "analyse" : "rejet",
              )}>
                {stats.score_moyen != null ? Math.round(stats.score_moyen) : "—"}
              </strong>
            </div>
            <div className="stat-tile">
              <span className="muted">Montant demandé</span>
              <strong>{money(stats.montant_total_demande)}</strong>
            </div>
            <div className="stat-tile">
              <span className="muted">Montant éligible</span>
              <strong>{money(stats.montant_total_eligible)}</strong>
            </div>
          </div>
        </section>
      )}

      {/* 5. Éclairage ML — strictement consultatif, comme partout ailleurs. */}
      {caps?.early_warning && (
        <MlSection
          titre="Membres à surveiller (retard probable à 30–90 j)"
          resume={ew ? `${ew.length} signalement${ew.length > 1 ? "s" : ""}` : "chargement…"}
          className="mt-md"
        >
          <EarlyWarning alertes={ew} />
        </MlSection>
      )}
    </div>
  );
}
