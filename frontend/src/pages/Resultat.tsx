import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, asList, money, zoneClass, type AuditEntry, type DemandeDetail, type Knockout, type Critere } from "../api/client";
import { getUser } from "../auth";
import Spinner from "../components/Spinner";
import Alert from "../components/Alert";
import MlPanel from "../components/MlPanel";
import Section from "../components/Section";
import AuthImage from "../components/AuthImage";
import { CompareBar, CRITERE_LABELS, CriteriaBars, ScoreGauge, ZONE_SCORE_LABEL } from "../components/charts";
import { useApi } from "../hooks/useApi";

function msgClass(code?: string) {
  if (!code) return "msg";
  if (["MONTANT_OK", "UPSELL_POSSIBLE"].includes(code)) return "msg ok";
  if (["MONTANT_PLAFONNE", "VOIE_EXCEPTIONNELLE", "HISTORIQUE_INSUFFISANT"].includes(code)) return "msg plafonne";
  return "msg ko";
}

/** Horodatage court, lisible par un contrôleur : date + heure locale. */
function quand(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

const STATUT_CLOS: Record<string, string> = {
  accorde: "accordé",
  conditionne: "accordé sous conditions",
  refuse: "refusé",
  clos: "clos",
};

const AUDIT_LABEL: Record<string, string> = {
  create: "Dossier créé",
  collecte: "Collecte économique saisie",
  piece: "Pièce justificative jointe",
  analyser: "Analyse lancée",
  soumettre: "Soumis pour décision",
  valider: "Validé par le Directeur (Chef d’Agence)",
  renvoyer: "Renvoyé à l’agent",
  escalader: "Escaladé au CIC",
  accorder: "Accordé",
  conditionner: "Accordé sous conditions",
  refuser: "Refusé",
};

/** Piste d'audit (GET /demandes/:id/audit). Le backend journalise chaque etape
 * du dossier ; sans cette section, l'ecran ne montrait que la derniere decision
 * — or c'est justement la tracabilite qui rend la decision defendable. */
function AuditTrail({ demandeId }: { demandeId: number }) {
  const [rows, setRows] = useState<AuditEntry[] | null>(null);

  useEffect(() => {
    api.audit(demandeId).then(setRows).catch(() => setRows([]));
  }, [demandeId]);

  if (!rows || rows.length === 0) return null;

  return (
    <Section titre="Piste d’audit" compteur={rows.length} resume="Qui, quoi, quand">
      <ol className="top-list">
        {rows.map((r, i) => (
          <li key={i}>
            <span className="num">{i + 1}</span>
            <span>
              <strong>{AUDIT_LABEL[r.action] || r.action}</strong>
              <div className="muted">
                {[r.auteur, quand(r.date)].filter(Boolean).join(" · ") || "auteur inconnu"}
              </div>
              {r.detail && <div className="muted">{r.detail}</div>}
            </span>
          </li>
        ))}
      </ol>
    </Section>
  );
}

export default function Resultat() {
  const { id } = useParams();
  const user = getUser();
  const { data: d, error, loading, reload, setError } = useApi<DemandeDetail>(
    () => api.demande(Number(id)),
    [id],
  );
  const [busy, setBusy] = useState(false);
  const [fileHint, setFileHint] = useState("");
  const [motif, setMotif] = useState("");

  async function analyser() {
    setBusy(true);
    setError("");
    try {
      await api.analyser(Number(id));
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function soumettre() {
    setBusy(true);
    setError("");
    try {
      const out = await api.soumettre(Number(id));
      setFileHint(out.file === "cic" ? "Envoyé en file CIC" : "Envoyé en file chef");
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function decider(avis: string, override = false) {
    if (!user) return;
    setBusy(true);
    setError("");
    try {
      await api.decision(Number(id), {
        niveau: user.role === "cic" ? "cic" : "chef_agence",
        avis,
        motif: motif || null,
        override,
      });
      setMotif("");
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (error && !d) return <div className="page"><Alert kind="error">{error}</Alert></div>;
  if (loading || !d) return <div className="page"><Spinner /></div>;
  const s = d.score;
  const criteres = asList<Critere>(s?.criteres as Critere[] | Record<string, unknown> | null);
  const knockouts = asList<Knockout>(s?.knockouts as Knockout[] | Record<string, unknown> | null);
  const chef = user?.role === "chef_agence" && d.statut === "soumis_chef";
  const cic = user?.role === "cic" && d.statut === "soumis_cic";
  // Un dossier tranche n'attend plus rien : la suite naturelle est un nouveau
  // credit pour ce membre, pas de rester sur un ecran en lecture seule.
  const dossierClos = ["accorde", "conditionne", "refuse", "clos"].includes(d.statut);
  const renvoye = d.statut === "renvoye";
  // Le backend ne verrouille ni l'analyse (elle archive le score precedent) ni
  // la soumission (elle exige seulement un score) : un dossier renvoye peut
  // repartir. Seul l'ecran l'interdisait, ce qui en faisait une impasse.
  const peutReanalyser = user?.role === "agent" && !dossierClos;
  // Miroir de STATUTS_MODIFIABLES cote API : au-dela, le dossier est engage
  // dans le circuit de decision et l'ecriture est refusee (409).
  const peutCorriger =
    user?.role === "agent" && ["brouillon", "analyse", "renvoye"].includes(d.statut);
  const peutSoumettre =
    user?.role === "agent" && !!s && ["analyse", "brouillon", "renvoye"].includes(d.statut);
  // Motif du renvoi : sans lui, l'agent ne sait pas ce qu'on lui demande de corriger.
  const motifRenvoi = [...(d.decisions || [])].reverse().find((x) => x.avis === "renvoyer");
  const membreBloque = !!d.membre?.statut && d.membre.statut !== "actif";
  const peutSouscrire = user?.role === "agent" && !membreBloque;

  return (
    <div className="page">
      <h1>Résultat — dossier #{d.id}</h1>
      <p className="lede">
        {d.membre ? (
          <>
            <Link to={`/membres/${d.membre.id}`}>
              {d.membre.prenom} {d.membre.nom}
            </Link>{" "}
            · {d.membre.code_externe}
          </>
        ) : (
          <Link to={`/membres/${d.membre_id}`}>Membre #{d.membre_id}</Link>
        )}{" "}
        · {d.objet} · <span className="badge">{d.statut}</span>
        {membreBloque && <span className="badge bad">compte {d.membre?.statut}</span>}
      </p>
      {fileHint && <Alert kind="success">{fileHint}</Alert>}

      {renvoye && (
        <div className="msg plafonne">
          <strong>Dossier renvoyé pour correction</strong>
          <div>
            {motifRenvoi?.motif
              ? `Motif : ${motifRenvoi.motif}`
              : "Aucun motif n’a été consigné lors du renvoi."}
            {motifRenvoi?.auteur ? ` — ${motifRenvoi.auteur}` : ""}
          </div>
          <div className="muted mt-sm">
            Corrige ce qui est demandé, relance l’analyse, puis soumets à nouveau.
          </div>
          {peutCorriger && (
            <div className="actions">
              <Link className="btn primary" to={`/demandes/${d.id}/modifier`}>
                Corriger le dossier
              </Link>
            </div>
          )}
        </div>
      )}
      {!s && peutReanalyser && (
        <div className="actions">
          <button className="btn" disabled={busy} onClick={analyser}>
            Lancer l’analyse
          </button>
        </div>
      )}
      {!s && !peutReanalyser && (
        <p className="muted">Dossier non analysé.</p>
      )}
      {s && (
        <>
          <div className={msgClass(s.message_code)}>
            <strong>{s.message_code}</strong>
            <div>{s.message_humain}</div>
            {s.zone && <div className={`badge ${zoneClass(s.zone)} mt-sm`}>{ZONE_SCORE_LABEL[s.zone] || s.zone}</div>}
          </div>
          <section className="block dashboard-head">
            <div className="gauge-card">
              <ScoreGauge score={s.score_global} zone={s.zone} />
              <div>
                <p style={{ margin: 0 }}>
                  {s.eligible ? "Éligible" : "Non éligible"}
                  {s.thin_file ? " · thin-file" : ""}
                </p>
                {d.ratios && (
                  <div className="stat-row mt-sm">
                    <div className="stat-tile">
                      <span className="muted">CAF</span>
                      <strong>{money(d.ratios.caf)}</strong>
                    </div>
                    <div className="stat-tile">
                      <span className="muted">RCSD</span>
                      <strong>{d.ratios.rcsd.toFixed(2)}</strong>
                    </div>
                    <div className="stat-tile">
                      <span className="muted">EBE</span>
                      <strong>{money(d.ratios.ebe)}</strong>
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="grid two mt-md">
              <CompareBar
                label="Demandé sur plafond éligible"
                value={d.montant_demande}
                max={Math.max(s.montant_eligible, d.montant_demande)}
                valueLabel={money(d.montant_demande)}
                tone={d.montant_demande > s.montant_eligible ? "warn" : "ok"}
              />
              {s.montant_max_suggestion ? (
                <CompareBar
                  label="Suggestion (capacité estimée)"
                  value={s.montant_max_suggestion}
                  max={Math.max(s.montant_max_suggestion, s.montant_eligible)}
                  valueLabel={money(s.montant_max_suggestion)}
                />
              ) : (
                <CompareBar
                  label="Plafond éligible"
                  value={s.montant_eligible}
                  max={Math.max(s.montant_eligible, d.montant_demande)}
                  valueLabel={money(s.montant_eligible)}
                />
              )}
            </div>
          </section>
          <MlPanel demandeId={d.id} montant={s.montant_eligible || d.montant_demande} dureeMois={d.duree_mois} />
          {knockouts.length > 0 && (
            <section className="block">
              <h2>Knock-outs</h2>
              {knockouts.map((k, i) => (
                <p key={String(k.code || i)}>
                  {String(k.code || "")} {k.detail ? `— ${k.detail}` : ""}
                </p>
              ))}
            </section>
          )}
          {criteres.length > 0 && (
            <section className="block mt-md">
              <h2>Détail des 6 critères</h2>
              <CriteriaBars criteres={criteres} />
            </section>
          )}
          {criteres.length > 0 && (
            <section className="block mt-md">
              <h2>Critères déterminants</h2>
              <ol className="top-list">
                {[...criteres]
                  .sort((a, b) => Number(b.contribution ?? 0) - Number(a.contribution ?? 0))
                  .slice(0, 3)
                  .map((c, i) => {
                    const code = String(c.code || "");
                    const note = Math.round(Number(c.note ?? 0));
                    const poids = c.poids != null ? Math.round(Number(c.poids) * 100) : null;
                    const contribution = c.contribution != null ? Math.round(Number(c.contribution)) : null;
                    return (
                      <li key={code || i}>
                        <span className="num">{i + 1}</span>
                        <span>
                          <strong>{CRITERE_LABELS[code] || code}</strong>
                          <div className="muted">
                            Note {note}/100{poids != null ? ` · poids ${poids} %` : ""}
                            {contribution != null ? ` · +${contribution} pts` : ""}
                          </div>
                        </span>
                      </li>
                    );
                  })}
              </ol>
            </section>
          )}
          {d.cautions.length > 0 && (
            <Section titre="Cautionnaires" compteur={d.cautions.length}>
              <div className="list">
                {d.cautions.map((c, i) => (
                  <div className="row" key={i}>
                    <div>
                      <strong>{c.prenom} {c.nom}</strong>
                      <div className="muted">
                        {c.relation ? `${c.relation} · ` : ""}
                        {c.telephone || "tél. inconnu"} · caution {c.type_caution} · {money(c.montant_engage)} engagés
                        {c.membre_existant ? " · déjà membre" : ""}
                      </div>
                      {c.revue && (
                        <div className="muted mt-sm" style={{ fontSize: "0.85rem" }}>
                          Capacité de relais — CAF {money(c.revue.caf_relais ?? 0)}
                          {c.revue.rcsd_relais != null ? ` · RCSD ${c.revue.rcsd_relais.toFixed(2)}` : ""}
                          {c.revue.score_relais != null ? ` · score ${Math.round(c.revue.score_relais)}/100` : ""}
                          {c.revue.motif ? ` — ${c.revue.motif}` : ""}
                        </div>
                      )}
                    </div>
                    <span className={`badge rect ${c.revue?.eligible ? "ok" : "warn"}`}>
                      {c.revue ? (c.revue.eligible ? "Éligible" : "À vérifier") : "Non évalué"}
                    </span>
                  </div>
                ))}
              </div>
            </Section>
          )}
          {d.pieces.length > 0 && (
            <Section titre="Pièces justificatives" compteur={d.pieces.length}>
              <div className="list">
                {d.pieces.map((p, i) => (
                  <div className="row" key={i}>
                    <div className="piece-photo-picker">
                      {p.fichier ? (
                        <AuthImage className="piece-thumb" path={p.fichier} alt={p.type_piece} />
                      ) : (
                        <div className="piece-thumb" />
                      )}
                      <strong>{p.type_piece}</strong>
                    </div>
                    <span className={`badge ${p.qualite_ocr === "ok" ? "ok" : "warn"}`}>{p.qualite_ocr || "—"}</span>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </>
      )}
      {(chef || cic) && (
        <section className="block mt-md">
          <h2>Avis humain</h2>
          <p className="lede">Motif obligatoire si tu t’écartes de la reco.</p>
          <label className="field">
            Motif
            <input value={motif} onChange={(e) => setMotif(e.target.value)} />
          </label>
          {chef && (
            <div className="actions">
              <button className="btn primary" disabled={busy} onClick={() => decider("valider")}>
                Valider
              </button>
              <button className="btn danger" disabled={busy} onClick={() => decider("refuser", true)}>
                Refuser
              </button>
              <button className="btn ghost" disabled={busy} onClick={() => decider("renvoyer")}>
                Renvoyer
              </button>
              <button className="btn warn" disabled={busy} onClick={() => decider("escalader")}>
                Escalader CIC
              </button>
            </div>
          )}
          {cic && (
            <div className="actions">
              <button className="btn primary" disabled={busy} onClick={() => decider("accorder")}>
                Accorder
              </button>
              <button className="btn warn" disabled={busy} onClick={() => decider("conditionner")}>
                Conditionner
              </button>
              <button className="btn danger" disabled={busy} onClick={() => decider("refuser", true)}>
                Refuser
              </button>
            </div>
          )}
        </section>
      )}
      {d.decisions?.length > 0 && (
        <section className="block mt-md">
          <h2>Décisions</h2>
          <div className="list">
            {d.decisions.map((x, i) => (
              <div className="row" key={i}>
                <div>
                  <strong>{x.niveau.replace("_", " ")} — {x.avis}</strong>
                  <div className="muted">{[x.auteur, quand(x.date)].filter(Boolean).join(" · ")}</div>
                  {x.motif && <div className="muted">{x.motif}</div>}
                </div>
                {x.override && <span className="badge rect warn">Écart motivé</span>}
              </div>
            ))}
          </div>
        </section>
      )}

      <AuditTrail demandeId={d.id} />
      {error && <Alert kind="error">{error}</Alert>}

      {/* Suite du parcours. Un dossier clos renvoyait l'agent dans le vide :
          il devait repasser par la recherche membre pour ouvrir le credit
          suivant. La prochaine action est proposee ici, en clair. */}
      {dossierClos && (
        <section className="block suite mt-md">
          <h2>Et maintenant ?</h2>
          <p className="muted">
            Ce dossier est {STATUT_CLOS[d.statut] || d.statut}. Il n’attend plus d’action.
          </p>
          <div className="actions">
            {peutSouscrire && (
              <Link className="btn primary" to={`/membres/${d.membre_id}/demande`}>
                Souscrire un nouveau crédit pour ce membre
              </Link>
            )}
            {membreBloque && (
              <p className="error">
                Compte {d.membre?.statut} — aucun nouveau crédit possible pour ce membre.
              </p>
            )}
            <Link className="btn ghost" to={`/membres/${d.membre_id}`}>
              Fiche du membre
            </Link>
            {user?.role === "agent" ? (
              <Link className="btn ghost" to="/demandes">
                Retour aux dossiers
              </Link>
            ) : (
              <Link className="btn ghost" to={user?.role === "cic" ? "/cic" : "/chef"}>
                Retour à la file
              </Link>
            )}
          </div>
        </section>
      )}

      <div className="actions mt-md">
        {peutSoumettre && (
          <button className="btn primary" disabled={busy} onClick={soumettre}>
            {renvoye ? "Soumettre à nouveau" : "Soumettre au Directeur (Chef d’Agence)"}
          </button>
        )}
        {peutCorriger && !renvoye && (
          <Link className="btn ghost" to={`/demandes/${d.id}/modifier`}>
            Corriger le dossier
          </Link>
        )}
        {s && peutReanalyser && (
          <button className="btn ghost" disabled={busy} onClick={analyser}>
            Relancer l’analyse
          </button>
        )}
        <Link className="btn ghost" to={`/demandes/${d.id}/memo`}>
          Mémo + échéancier
        </Link>
        <Link className="btn ghost" to={`/membres/${d.membre_id}`}>
          Fiche du membre
        </Link>
        {/* Sur un dossier encore vivant, ouvrir un credit reste possible mais
            discret : ce n'est pas l'action attendue a cet instant. */}
        {!dossierClos && peutSouscrire && (
          <Link className="btn ghost" to={`/membres/${d.membre_id}/demande`}>
            Nouveau crédit pour ce membre
          </Link>
        )}
      </div>
    </div>
  );
}
