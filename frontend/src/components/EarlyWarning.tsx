import { useEffect, useState } from "react";
import { api, money, type AlertePortefeuille, type SignalFucec } from "../api/client";
import Spinner from "./Spinner";
import MembreLabel from "./MembreLabel";

/** Référentiel FUCEC mis en cache au niveau du module : il est fixe côté
 * serveur, et trois écrans affichent ces alertes. Le récupérer une fois évite
 * autant d'allers-retours que de listes montées, sans dupliquer les libellés
 * dans le front (ils resteraient à re-synchroniser à chaque évolution métier). */
let cacheSignaux: Record<string, SignalFucec> | null = null;
let enVol: Promise<Record<string, SignalFucec>> | null = null;

function chargerSignaux(): Promise<Record<string, SignalFucec>> {
  if (cacheSignaux) return Promise.resolve(cacheSignaux);
  if (!enVol) {
    enVol = api
      .signaux()
      .then((r) => {
        cacheSignaux = Object.fromEntries(r.items.map((s) => [s.code, s]));
        return cacheSignaux;
      })
      .catch(() => ({}));
  }
  return enVol;
}

/** Bande de risque plutôt qu'un pourcentage nu.
 *
 * `p_par30_90j` vient d'une heuristique (essentiellement le retard rapporté à
 * 90 jours), pas d'un modèle entraîné : afficher « 81,1 % » en tête donne une
 * fausse impression de précision, et plusieurs membres au même retard sortent
 * forcément au même chiffre. La bande dit le niveau, le détail reste lisible. */
function bande(p: number): { libelle: string; tone: string } {
  if (p >= 0.7) return { libelle: "Risque élevé", tone: "bad" };
  if (p >= 0.4) return { libelle: "Risque modéré", tone: "warn" };
  return { libelle: "Risque faible", tone: "" };
}

export default function EarlyWarning({
  alertes,
  limite,
}: {
  alertes: AlertePortefeuille[] | null;
  limite?: number;
}) {
  const [signaux, setSignaux] = useState<Record<string, SignalFucec>>(cacheSignaux || {});

  useEffect(() => {
    chargerSignaux().then(setSignaux);
  }, []);

  if (alertes === null) return <Spinner />;
  if (alertes.length === 0) return <p className="muted">Rien à signaler.</p>;

  const items = limite ? alertes.slice(0, limite) : alertes;
  const exposition = alertes.reduce((sum, a) => sum + a.exposure, 0);

  return (
    <>
      <p className="ledger-note">
        Classées par montant en jeu à risque égal — le score sature vite, l’exposition départage.
        {alertes.length > 1 && ` ${money(exposition)} exposés au total.`}
      </p>
      <div className="ew-list">
        {items.map((a) => {
          const b = bande(a.p_par30_90j);
          return (
            <div className="ew-card" key={`${a.member_code}-${a.application_id ?? ""}`}>
              <div className="ew-head">
                <div className="ew-id">
                  <MembreLabel
                    nom={a.member_name}
                    code={a.member_code}
                    membreId={a.member_id}
                    suffixe={a.days_late != null ? `${a.days_late} j de retard` : undefined}
                  />
                </div>
                <div className="ew-expo">
                  <strong>{money(a.exposure)}</strong>
                  <span className="muted">exposés</span>
                </div>
                <span className={`badge rect ${b.tone}`} title={`Indice ${Math.round(a.p_par30_90j * 100)} / 100`}>
                  {b.libelle}
                </span>
              </div>
              {a.signals.length > 0 && (
                <ul className="ew-signaux">
                  {a.signals.map((code) => (
                    <li key={code}>
                      {signaux[code] ? (
                        <>
                          {signaux[code].libelle}
                          <span className="muted"> · {signaux[code].famille}</span>
                        </>
                      ) : (
                        code
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}
