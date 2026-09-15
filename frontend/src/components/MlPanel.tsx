import { useEffect, useState } from "react";
import {
  api,
  money,
  type AnomaliesOut,
  type Capabilities,
  type PlafondMlOut,
  type ScorecardMlOut,
  type SimulationOut,
  type SimulationSavedOut,
} from "../api/client";
import Spinner from "./Spinner";
import Alert from "./Alert";
import MlSection from "./MlSection";
import { CompareBar, FactorsChart, TrajectoryChart } from "./charts";

const SCENARIOS = [
  { value: "normal", label: "Normal" },
  { value: "mauvaise_recolte", label: "Mauvaise récolte" },
  { value: "maladie", label: "Maladie" },
  { value: "inflation", label: "Inflation" },
];

function riskBadgeClass(niveau?: string) {
  if (niveau === "faible") return "badge ok";
  if (niveau === "eleve" || niveau === "élevé" || niveau === "fort") return "badge bad";
  return "badge warn";
}

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

/** Éclairages ML consultatifs pour un dossier — n'apparaît que si le backend
 * les expose (GET /capabilities). Ne modifie jamais le score/plafond/zone
 * du moteur de règles : "le ML éclaire, l'humain décide". */
export default function MlPanel({
  demandeId,
  montant,
  dureeMois,
}: {
  demandeId: number;
  montant: number;
  dureeMois: number;
}) {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [scorecard, setScorecard] = useState<ScorecardMlOut | null>(null);
  const [plafond, setPlafond] = useState<PlafondMlOut | null>(null);
  const [anomalies, setAnomalies] = useState<AnomaliesOut | null>(null);

  const [scenario, setScenario] = useState("normal");
  const [simMontant, setSimMontant] = useState(Math.max(0, Math.round(montant)));
  const [simDuree, setSimDuree] = useState(Math.min(24, Math.max(1, dureeMois || 12)));
  const [sim, setSim] = useState<SimulationOut | null>(null);
  const [simBusy, setSimBusy] = useState(false);
  const [simErr, setSimErr] = useState("");
  const [saved, setSaved] = useState<SimulationSavedOut[]>([]);
  const [saveBusy, setSaveBusy] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  useEffect(() => {
    api.capabilities().then(setCaps).catch(() => setCaps(null));
  }, []);

  useEffect(() => {
    if (!caps) return;
    if (caps.ml_scorecard) {
      api.mlScorecard(demandeId).then(setScorecard).catch(() => undefined);
      api.mlPlafond(demandeId).then(setPlafond).catch(() => undefined);
    }
    if (caps.anomalies) {
      api.anomalies(demandeId).then(setAnomalies).catch(() => undefined);
    }
    if (caps.simulation) {
      api.simulations(demandeId).then(setSaved).catch(() => undefined);
    }
  }, [caps, demandeId]);

  async function runSimulation() {
    setSimBusy(true);
    setSimErr("");
    setSaveMsg("");
    try {
      const out = await api.simuler(demandeId, {
        scenario,
        montant: simMontant,
        duree_mois: simDuree,
        horizon_mois: simDuree,
      });
      setSim(out);
    } catch (e) {
      setSimErr(e instanceof Error ? e.message : "Simulation indisponible");
    } finally {
      setSimBusy(false);
    }
  }

  async function persistSimulation() {
    setSaveBusy(true);
    setSaveMsg("");
    try {
      await api.enregistrerSimulation(demandeId, {
        scenario,
        montant: simMontant,
        duree_mois: simDuree,
        horizon_mois: simDuree,
      });
      const rows = await api.simulations(demandeId);
      setSaved(rows);
      setSaveMsg("Simulation enregistrée au dossier.");
    } catch (e) {
      setSaveMsg(e instanceof Error ? e.message : "Échec de l'enregistrement");
    } finally {
      setSaveBusy(false);
    }
  }

  if (!caps) return null;
  if (!caps.ml_scorecard && !caps.anomalies && !caps.simulation) return null;

  // Résumé lisible replié : le niveau de risque suffit à décider s'il faut ouvrir.
  const resume = scorecard
    ? `risque ${scorecard.niveau_risque} · défaut estimé ${Math.round(scorecard.probabilite_defaut * 100)} %`
    : "scorecard adaptative, anomalies, simulation de résilience";

  return (
    <MlSection titre="Éclairages sur ce dossier" resume={resume} className="mt-md">

      {caps.ml_scorecard && scorecard && (
        <div className="ml-block">
          <div className="ml-h2-row">
            <h2>Scorecard adaptative</h2>
            <span className="badge">modèle {scorecard.model_version}</span>
          </div>
          <div className="kv">
            <span>Niveau de risque</span>
            <span className={riskBadgeClass(scorecard.niveau_risque)}>{scorecard.niveau_risque}</span>
            <span>Probabilité de défaut indicative</span>
            <strong>{Math.round(scorecard.probabilite_defaut * 100)} %</strong>
          </div>
          {scorecard.top_factors?.length > 0 && (
            <FactorsChart factors={scorecard.top_factors.slice(0, 5)} />
          )}
          {scorecard.warning && <p className="muted mt-sm">{scorecard.warning}</p>}
        </div>
      )}

      {caps.ml_scorecard && plafond && (
        <div className="ml-block">
          <div className="ml-h2-row">
            <h2>Plafond ML indicatif</h2>
            <span className="badge">modèle {plafond.model_version}</span>
          </div>
          {plafond.blocked_by_knockout ? (
            <p className="muted">Aucune recommandation — un knockout métier bloque déjà le dossier.</p>
          ) : (
            <>
              <CompareBar
                label="Plafond règles (officiel)"
                value={plafond.plafond_regles}
                max={plafond.plafond_regles}
                valueLabel={money(plafond.plafond_regles)}
              />
              <CompareBar
                label="Plafond ML recommandé"
                value={plafond.plafond_ml_recommande ?? 0}
                max={plafond.plafond_regles}
                valueLabel={plafond.plafond_ml_recommande != null ? money(plafond.plafond_ml_recommande) : "—"}
                tone={plafond.facteur_prudence != null && plafond.facteur_prudence < 1 ? "warn" : "ok"}
              />
              <p className="muted mt-sm">{plafond.explication}</p>
            </>
          )}
        </div>
      )}

      {caps.anomalies && anomalies && (
        <div className="ml-block">
          <div className="ml-h2-row">
            <h2>Anomalies documentaires</h2>
            {anomalies.model_version && <span className="badge">modèle {anomalies.model_version}</span>}
          </div>
          {anomalies.scope_excluded ? (
            <p className="muted">Hors périmètre — profil thin-file, la détection n'est pas fiable sur peu d'historique.</p>
          ) : anomalies.anomalies.length === 0 ? (
            <p className="muted">Rien à signaler sur ce dossier.</p>
          ) : (
            <ul className="ml-factors">
              {anomalies.anomalies.map((a, i) => (
                <li key={i}>
                  <span className="badge warn">à vérifier</span> {a.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {caps.simulation && (
        <div className="ml-block">
          <div className="ml-h2-row">
            <h2>Simulateur de résilience</h2>
            <span className="badge">1 000 scénarios</span>
          </div>
          <p className="muted">Trésorerie sous choc — n'affecte ni le plafond ni la décision.</p>

          <div className="tabs sim-tabs">
            {SCENARIOS.map((s) => (
              <button
                key={s.value}
                type="button"
                className={`tab${scenario === s.value ? " active" : ""}`}
                onClick={() => setScenario(s.value)}
              >
                {s.label}
              </button>
            ))}
          </div>

          <div className="sim-sliders">
            <label className="field">
              Montant <strong className="sim-slider-value">{money(simMontant)}</strong>
              <input
                type="range"
                min={100000}
                max={Math.max(5_000_000, simMontant * 2, montant * 2)}
                step={50000}
                value={simMontant}
                onChange={(e) => setSimMontant(Number(e.target.value))}
              />
            </label>
            <label className="field">
              Durée <strong className="sim-slider-value">{simDuree} mois</strong>
              <input
                type="range"
                min={1}
                max={24}
                value={simDuree}
                onChange={(e) => setSimDuree(Number(e.target.value))}
              />
            </label>
          </div>

          <div className="actions">
            <button className="btn ghost sm" type="button" disabled={simBusy} onClick={runSimulation}>
              {simBusy ? "Simulation…" : "Simuler"}
            </button>
          </div>
          {simBusy && <Spinner label="Simulation en cours…" />}
          {simErr && <Alert kind="error">{simErr}</Alert>}
          {sim && !simBusy && (
            <div className="mt-sm">
              <p className="sim-headline">{sim.explication}</p>
              <TrajectoryChart p10={sim.p10} p50={sim.p50} p90={sim.p90} moisCritique={sim.mois_critique} />
              <p className="muted mt-sm">
                modèle {sim.model_version} · {sim.iterations} scénarios · seed {sim.seed}
              </p>
              <div className="actions mt-sm">
                <button className="btn ghost sm" type="button" disabled={saveBusy} onClick={persistSimulation}>
                  {saveBusy ? "Enregistrement…" : "✓ Enregistrer la simulation au dossier"}
                </button>
              </div>
              {saveMsg && <p className="muted mt-sm">{saveMsg}</p>}
            </div>
          )}
          {saved.length > 0 && (
            <p className="muted mt-sm">
              {saved.length} simulation{saved.length > 1 ? "s" : ""} enregistrée{saved.length > 1 ? "s" : ""} au dossier · dernière le {fmtDate(saved[0].created_at)}
            </p>
          )}
        </div>
      )}
    </MlSection>
  );
}
