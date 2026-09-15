import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api, type CollecteBody, type MembreDetail, type Produit } from "../api/client";
import Alert from "../components/Alert";
import Spinner from "../components/Spinner";

const STEPS = ["Demande", "Activité", "Exploitation", "Bilan", "Preuves"];

// Statuts ou le dossier appartient encore a l'agent (miroir de
// STATUTS_MODIFIABLES cote API, routes.py).
const MODIFIABLES = ["brouillon", "analyse", "renvoye"];

// Repère affiché dans le panneau latéral pour chaque étape — texte
// d'aide fixe (aucune donnée), aligné sur STEPS.
const STEP_HELP = [
  "Objet, produit, montant et durée du crédit demandé.",
  "Type d’activité et son caractère saisonnier éventuel.",
  "Chiffre d’affaires, charges et revenus utilisés pour la CAF.",
  "Fonds propres, dettes, actif et garanties.",
  "Niveau de preuve des pièces déposées et crédits ailleurs.",
];

// Formulaire vierge : aucun chiffre plausible pré-rempli. Un dossier de
// crédit part de zéro — l'agent saisit les vrais chiffres du membre, il
// ne corrige pas des valeurs d'exemple qu'il pourrait oublier de changer.
const empty: CollecteBody & {
  objet: string;
  montant_demande: number;
  duree_mois: number;
  produit_id: number;
  situation_fiscale: string;
  credits_ailleurs: boolean;
  preuves_externes_ok: boolean;
} = {
  objet: "",
  montant_demande: 0,
  duree_mois: 12,
  produit_id: 0,
  situation_fiscale: "a_verifier",
  credits_ailleurs: false,
  preuves_externes_ok: false,
  ca: 0,
  cmv: 0,
  charges_exploitation: 0,
  produits_financiers: 0,
  revenu_perso: 0,
  charge_familiale: 0,
  charge_credits_en_cours: 0,
  fonds_propres: 0,
  total_dettes: 0,
  actif_total: 0,
  actif_circulant: 0,
  passif_circulant: 0,
  stock_moyen: 0,
  resultat_net: 0,
  preuve_revenu: "",
  preuve_charge: "",
  saisonnier: false,
  type_activite: "tertiaire",
  valeur_garanties: 0,
};

// Pas de détection OCR réelle côté backend (qualité déclarée par l'agent) :
// on ne lui fait plus juger une photo à l'aveugle, une photo attachée suffit.
type PieceDraft = { type_piece: string; file: File | null; previewUrl: string | null };
const emptyDraft = (typePiece = ""): PieceDraft => ({ type_piece: typePiece, file: null, previewUrl: null });

const PREUVE_HELP: Record<string, string> = {
  N1: "Faible — déclaratif, sans justificatif solide",
  N2: "Intermédiaire — justificatif partiel (carnet, facture)",
  N3: "Fort — document officiel vérifiable",
};

/** Assistant de collecte A–E.
 *
 * Deux usages pour un meme formulaire : creation (`/membres/:id/demande`, `id`
 * = le membre) et correction (`/demandes/:id/modifier`, `id` = le dossier).
 * Un dossier renvoye par le chef n'avait aucun ecran pour etre corrige : on
 * pouvait le resoumettre, pas le reparer.
 */
export default function DemandeWizard({ edition = false }: { edition?: boolean }) {
  const { id } = useParams();
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  // En edition, l'id de route designe le dossier ; le membre vient de lui.
  const [membreId, setMembreId] = useState<number | null>(edition ? null : Number(id));
  const [chargement, setChargement] = useState(edition);
  const [statutDossier, setStatutDossier] = useState("");
  const [produits, setProduits] = useState<Produit[]>([]);
  const [ref, setRef] = useState<Record<string, string[]>>({});
  const [membre, setMembre] = useState<MembreDetail | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(empty);
  const [pieces, setPieces] = useState<PieceDraft[]>([]);
  const [draft, setDraft] = useState<PieceDraft>(emptyDraft());

  useEffect(() => {
    if (!id) return;
    if (!edition) {
      setMembreId(Number(id));
      api.membre(Number(id)).then(setMembre).catch(() => undefined);
      return;
    }
    // Reprise : on repeuple le formulaire avec ce qui est deja en base, sinon
    // une correction ecraserait les donnees valides par des champs vides.
    setChargement(true);
    Promise.all([api.demande(Number(id)), api.collecteComplete(Number(id))])
      .then(([dem, col]) => {
        setMembreId(dem.membre_id);
        setStatutDossier(dem.statut);
        setForm((f) => ({
          ...f,
          ...col.complete,
          objet: dem.objet || "",
          montant_demande: dem.montant_demande || 0,
          duree_mois: dem.duree_mois || 12,
          produit_id: dem.produit_id || f.produit_id,
          situation_fiscale: dem.situation_fiscale || f.situation_fiscale,
        }));
        return api.membre(dem.membre_id).then(setMembre);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "Dossier introuvable"))
      .finally(() => setChargement(false));
  }, [id, edition]);

  useEffect(() => {
    api
      .produits()
      .then((ps) => {
        const commercialisables = ps.filter((p) => !p.exceptionnel);
        setProduits(commercialisables);
        setForm((f) => (commercialisables.length && !f.produit_id ? { ...f, produit_id: commercialisables[0].id } : f));
      })
      .catch(() => undefined);
    // Selects de preuves / type de pièce / qualité photo : source unique = /referentiels,
    // pas une liste recopiée à la main qui peut désynchroniser du backend.
    api
      .referentiels()
      .then((r) => {
        setRef(r);
        setForm((f) => ({
          ...f,
          preuve_revenu: f.preuve_revenu || r.preuves?.[0] || "",
          preuve_charge: f.preuve_charge || r.preuves?.[0] || "",
        }));
        setDraft((d) => (d.type_piece ? d : emptyDraft(r.types_piece?.[0] || "")));
      })
      .catch(() => undefined);
  }, []);

  function patch<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function onDraftFile(file: File | null) {
    if (draft.previewUrl) URL.revokeObjectURL(draft.previewUrl);
    setDraft((d) => ({ ...d, file, previewUrl: file ? URL.createObjectURL(file) : null }));
  }

  function addPiece() {
    if (!draft.file || !draft.type_piece) return;
    setPieces((p) => [...p, draft]);
    setDraft(emptyDraft(draft.type_piece));
  }

  function removePiece(i: number) {
    setPieces((p) => {
      const target = p[i];
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return p.filter((_, j) => j !== i);
    });
  }

  const piecesOk = pieces.length > 0;
  const draftOk = form.objet.trim() !== "" && form.montant_demande > 0;
  const demandeOk = draftOk && form.ca > 0;

  function collecte(): CollecteBody {
    const {
      ca, cmv, charges_exploitation, produits_financiers, revenu_perso, charge_familiale,
      charge_credits_en_cours, fonds_propres, total_dettes, actif_total, actif_circulant,
      passif_circulant, stock_moyen, resultat_net, preuve_revenu, preuve_charge, saisonnier,
      type_activite, valeur_garanties,
    } = form;
    return {
      ca, cmv, charges_exploitation, produits_financiers, revenu_perso, charge_familiale,
      charge_credits_en_cours, fonds_propres, total_dettes, actif_total, actif_circulant,
      passif_circulant, stock_moyen, resultat_net, preuve_revenu, preuve_charge, saisonnier,
      type_activite, valeur_garanties,
    };
  }

  async function createWithPieces() {
    const created = await api.createDemande({
      membre_id: Number(membreId),
      objet: form.objet,
      montant_demande: form.montant_demande,
      duree_mois: form.duree_mois,
      produit_id: form.produit_id,
      situation_fiscale: form.situation_fiscale,
      credits_ailleurs: form.credits_ailleurs,
      preuves_externes_ok: form.preuves_externes_ok,
      collecte: collecte(),
    });
    for (const p of pieces) {
      if (!p.file) continue;
      await api.uploadPiece(created.id, { type_piece: p.type_piece, qualite_ocr: "ok", file: p.file });
    }
    return created;
  }

  /** Enregistre la correction d'un dossier existant puis relance l'analyse.
   * Les pieces deja deposees restent en place ; on n'ajoute que les nouvelles. */
  async function saveEdition() {
    const did = Number(id);
    await api.modifierDemande(did, {
      objet: form.objet,
      montant_demande: form.montant_demande,
      duree_mois: form.duree_mois,
      produit_id: form.produit_id,
      situation_fiscale: form.situation_fiscale,
      credits_ailleurs: form.credits_ailleurs,
      preuves_externes_ok: form.preuves_externes_ok,
      collecte: collecte(),
    });
    for (const p of pieces) {
      if (!p.file) continue;
      await api.uploadPiece(did, { type_piece: p.type_piece, qualite_ocr: "ok", file: p.file });
    }
    return did;
  }

  async function submit() {
    setErr("");
    if (!demandeOk) {
      setErr("Objet, montant demandé et CA sont obligatoires (étapes 1 et 3).");
      return;
    }
    // En correction, les pieces du dossier sont deja au dossier : en exiger une
    // nouvelle a chaque passage obligerait a rephotographier pour changer un chiffre.
    if (!edition && !piecesOk) {
      setErr("Ajoute au moins une pièce avec une photo.");
      return;
    }
    setBusy(true);
    try {
      const did = edition ? await saveEdition() : (await createWithPieces()).id;
      await api.analyser(did);
      nav(`/demandes/${did}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  // Enregistre le dossier tel quel (statut "brouillon" côté backend — l'analyse
  // n'est pas déclenchée) : reprend au même endroit plus tard, aucune donnée perdue.
  async function saveDraft() {
    setErr("");
    if (!draftOk) {
      setErr("Objet et montant demandé sont nécessaires pour enregistrer un brouillon.");
      return;
    }
    setBusy(true);
    try {
      const created = await createWithPieces();
      nav(`/demandes/${created.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  if (chargement) {
    return (
      <div className="page">
        <Spinner />
      </div>
    );
  }

  // Un compte gele ou radie ne peut pas ouvrir de demande : l'API le refuse
  // (NON_MEMBRE / COMPTE_INACTIF). Sans ce controle en amont, l'agent saisit
  // tout le formulaire et ne decouvre le refus qu'a l'enregistrement.
  if (!edition && membre && membre.statut !== "actif") {
    return (
      <div className="page">
        <h1>Demande impossible</h1>
        <Alert kind="error">
          Le compte de {membre.prenom} {membre.nom} est {membre.statut === "gele" ? "gelé" : "radié"} :{" "}
          aucune demande de crédit n'est possible tant qu'il n'est pas réactivé.
        </Alert>
        <div className="actions">
          <button className="btn ghost" type="button" onClick={() => nav(-1)}>
            Revenir
          </button>
          <Link className="btn" to={`/membres/${membre.id}`}>
            Voir la fiche
          </Link>
        </div>
      </div>
    );
  }

  // Miroir de STATUTS_MODIFIABLES cote API. Sans ce controle en amont, on
  // pouvait ouvrir l'ecran sur un dossier deja soumis, tout ressaisir, et ne
  // decouvrir le refus (409) qu'au moment d'enregistrer.
  if (edition && statutDossier && !MODIFIABLES.includes(statutDossier)) {
    return (
      <div className="page">
        <h1>Dossier non modifiable</h1>
        <Alert kind="error">
          Ce dossier est au statut « {statutDossier} » : il est engagé dans le circuit de décision et
          ne peut plus être corrigé.
        </Alert>
        <div className="actions">
          <button className="btn ghost" type="button" onClick={() => nav(`/demandes/${id}`)}>
            Revenir au dossier
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="wizard-top">
        <button type="button" className="btn ghost icon-btn" onClick={() => nav(-1)} aria-label="Retour">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <div className="wizard-title">
          <span className="wizard-eyebrow">
            {edition ? `Correction du dossier #${id}` : "Étape " + (step + 1) + " — Collecte A–E"}
          </span>
          <h1>
            {edition ? "Corriger la demande" : "Demande de crédit"}
            {membre ? ` — ${membre.prenom} ${membre.nom}` : ""}
          </h1>
        </div>
        <span className="wizard-count">{step + 1}/{STEPS.length}</span>
      </div>

      <div className="wizard-progress" role="progressbar" aria-valuenow={step + 1} aria-valuemin={1} aria-valuemax={STEPS.length}>
        {STEPS.map((s, i) => (
          <span key={s} className={i <= step ? "filled" : ""} />
        ))}
      </div>

      <div className="wizard-layout">
        <div className="wizard-main">
          <p className="lede">Collecte A–E. Les formules CAF / RCSD / score restent dans le moteur.</p>

          {step === 0 && (
            <div className="grid two">
              <label className="field">
                Objet
                <input value={form.objet} placeholder="ex. Renouvellement stock boutique" onChange={(e) => patch("objet", e.target.value)} />
              </label>
              <label className="field">
                Montant (FCFA)
                <input type="number" min={0} value={form.montant_demande || ""} placeholder="0" onChange={(e) => patch("montant_demande", Number(e.target.value))} />
              </label>
              <label className="field">
                Durée (mois)
                <input type="number" min={1} value={form.duree_mois} onChange={(e) => patch("duree_mois", Number(e.target.value))} />
              </label>
              <label className="field">
                Produit
                <select
                  value={form.produit_id}
                  onChange={(e) => {
                    const pid = Number(e.target.value);
                    const p = produits.find((x) => x.id === pid);
                    setForm((f) => ({
                      ...f,
                      produit_id: pid,
                      ...(p?.exceptionnel && f.montant_demande < 5_000_000
                        ? { montant_demande: 10_000_000, duree_mois: 24 }
                        : {}),
                    }));
                  }}
                >
                  {produits.length === 0 && <option value={0}>Chargement…</option>}
                  {produits.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.libelle} {p.exceptionnel ? "(CIC)" : ""}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {step === 1 && (
            <div className="grid two">
              <label className="field">
                Type d’activité
                <select value={form.type_activite} onChange={(e) => patch("type_activite", e.target.value)}>
                  <option value="primaire">Primaire</option>
                  <option value="secondaire">Secondaire</option>
                  <option value="tertiaire">Tertiaire</option>
                </select>
              </label>
              <label className="check">
                <input type="checkbox" checked={form.saisonnier} onChange={(e) => patch("saisonnier", e.target.checked)} />
                Activité saisonnière
              </label>
            </div>
          )}

          {step === 2 && (
            <div className="grid two">
              <label className="field">
                CA annuel
                <input type="number" min={0} value={form.ca || ""} placeholder="0" onChange={(e) => patch("ca", Number(e.target.value))} />
              </label>
              <label className="field">
                CMV
                <input type="number" min={0} value={form.cmv || ""} placeholder="0" onChange={(e) => patch("cmv", Number(e.target.value))} />
              </label>
              <label className="field">
                Charges exploitation
                <input type="number" min={0} value={form.charges_exploitation || ""} placeholder="0" onChange={(e) => patch("charges_exploitation", Number(e.target.value))} />
              </label>
              <label className="field">
                Produits financiers
                <input type="number" min={0} value={form.produits_financiers || ""} placeholder="0" onChange={(e) => patch("produits_financiers", Number(e.target.value))} />
              </label>
              <label className="field">
                Revenu perso
                <input type="number" min={0} value={form.revenu_perso || ""} placeholder="0" onChange={(e) => patch("revenu_perso", Number(e.target.value))} />
              </label>
              <label className="field">
                Charge familiale
                <input type="number" min={0} value={form.charge_familiale || ""} placeholder="0" onChange={(e) => patch("charge_familiale", Number(e.target.value))} />
              </label>
              <label className="field">
                Charge crédits en cours
                <input type="number" min={0} value={form.charge_credits_en_cours || ""} placeholder="0" onChange={(e) => patch("charge_credits_en_cours", Number(e.target.value))} />
              </label>
            </div>
          )}

          {step === 3 && (
            <div className="grid two">
              <label className="field">
                Fonds propres
                <input type="number" min={0} value={form.fonds_propres || ""} placeholder="0" onChange={(e) => patch("fonds_propres", Number(e.target.value))} />
              </label>
              <label className="field">
                Total dettes
                <input type="number" min={0} value={form.total_dettes || ""} placeholder="0" onChange={(e) => patch("total_dettes", Number(e.target.value))} />
              </label>
              <label className="field">
                Actif total
                <input type="number" min={0} value={form.actif_total || ""} placeholder="0" onChange={(e) => patch("actif_total", Number(e.target.value))} />
              </label>
              <label className="field">
                Actif circulant
                <input type="number" min={0} value={form.actif_circulant || ""} placeholder="0" onChange={(e) => patch("actif_circulant", Number(e.target.value))} />
              </label>
              <label className="field">
                Passif circulant
                <input type="number" min={0} value={form.passif_circulant || ""} placeholder="0" onChange={(e) => patch("passif_circulant", Number(e.target.value))} />
              </label>
              <label className="field">
                Stock moyen
                <input type="number" min={0} value={form.stock_moyen || ""} placeholder="0" onChange={(e) => patch("stock_moyen", Number(e.target.value))} />
              </label>
              <label className="field">
                Résultat net
                <input type="number" value={form.resultat_net || ""} placeholder="0" onChange={(e) => patch("resultat_net", Number(e.target.value))} />
              </label>
              <label className="field">
                Valeur garanties
                <input type="number" min={0} value={form.valeur_garanties || ""} placeholder="0" onChange={(e) => patch("valeur_garanties", Number(e.target.value))} />
              </label>
            </div>
          )}

          {step === 4 && (
            <div>
              <section className="block">
                <h2>Niveau de preuve</h2>
                <div className="grid two">
                  <label className="field">
                    Preuve revenu
                    <select value={form.preuve_revenu} onChange={(e) => patch("preuve_revenu", e.target.value)}>
                      {(ref.preuves || []).map((p) => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                    <span className="hint">{PREUVE_HELP[form.preuve_revenu] || ""}</span>
                  </label>
                  <label className="field">
                    Preuve charge
                    <select value={form.preuve_charge} onChange={(e) => patch("preuve_charge", e.target.value)}>
                      {(ref.preuves || []).map((p) => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                    <span className="hint">{PREUVE_HELP[form.preuve_charge] || ""}</span>
                  </label>
                  <label className="field">
                    Situation fiscale
                    <select value={form.situation_fiscale} onChange={(e) => patch("situation_fiscale", e.target.value)}>
                      <option value="en_regle">En règle</option>
                      <option value="a_verifier">À vérifier</option>
                      <option value="non_fourni">Non fourni</option>
                      <option value="non_conforme">Non conforme</option>
                    </select>
                  </label>
                </div>
              </section>

              <section className="block mt-md">
                <h2>Pièces justificatives</h2>
                <p className="muted">Une photo par pièce — prise sur le moment ou chargée depuis l’appareil. Pas de pièce sans photo.</p>

                {pieces.length > 0 && (
                  <div className="list mb-sm">
                    {pieces.map((p, i) => (
                      <div className="row" key={i}>
                        <div className="piece-photo-picker">
                          {p.previewUrl && <img className="piece-thumb" src={p.previewUrl} alt={p.type_piece} />}
                          <div>
                            <strong>{p.type_piece}</strong>
                            <div className="muted">{p.file?.name}</div>
                          </div>
                        </div>
                        <button className="btn ghost sm" type="button" onClick={() => removePiece(i)}>
                          Retirer
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="grid two">
                  <label className="field">
                    Type de pièce
                    <select value={draft.type_piece} onChange={(e) => setDraft((d) => ({ ...d, type_piece: e.target.value }))}>
                      {(ref.types_piece || []).map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Photo (caméra ou fichier)
                    <input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      onChange={(e) => onDraftFile(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>
                {draft.previewUrl && <img className="piece-thumb mt-sm" src={draft.previewUrl} alt="aperçu" />}
                <div className="actions">
                  <button className="btn ghost sm" type="button" disabled={!draft.file || !draft.type_piece} onClick={addPiece}>
                    Ajouter cette pièce
                  </button>
                </div>
              </section>

              <section className="block mt-md">
                <h2>Crédits ailleurs</h2>
                <div className="grid two">
                  <label className="check">
                    <input type="checkbox" checked={form.credits_ailleurs} onChange={(e) => patch("credits_ailleurs", e.target.checked)} />
                    Crédits ailleurs (hors cette COOPEC)
                  </label>
                  {form.credits_ailleurs && (
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={form.preuves_externes_ok}
                        onChange={(e) => patch("preuves_externes_ok", e.target.checked)}
                      />
                      Pièces externes déposées
                    </label>
                  )}
                </div>
                {form.credits_ailleurs && !form.preuves_externes_ok && (
                  <p className="error mt-sm">Sans pièces : l’analyse peut refuser (preuves externes manquantes).</p>
                )}
              </section>
            </div>
          )}

          {err && <Alert kind="error">{err}</Alert>}

          <div className="actions wizard-actions">
            <div className="wizard-actions-left">
              {step > 0 && (
                <button className="btn ghost" type="button" onClick={() => setStep(step - 1)}>
                  Retour
                </button>
              )}
              {/* Le brouillon cree un nouveau dossier : hors de propos quand on
                  en corrige un qui existe deja. */}
              {!edition && (
                <button className="btn ghost" type="button" disabled={busy || !draftOk} onClick={saveDraft}>
                  Enreg. brouillon
                </button>
              )}
            </div>
            {step < STEPS.length - 1 && (
              <button className="btn primary" type="button" onClick={() => setStep(step + 1)}>
                Continuer
              </button>
            )}
            {step === STEPS.length - 1 && (
              <button
                className="btn primary"
                type="button"
                disabled={busy || (!edition && !piecesOk) || !demandeOk}
                onClick={submit}
              >
                {edition ? "Enregistrer et relancer l’analyse" : "Enregistrer et analyser"}
              </button>
            )}
          </div>
        </div>

        <aside className="wizard-side">
          <div className="block wizard-nav">
            <h2>Progression</h2>
            <ol className="wizard-steps-list">
              {STEPS.map((s, i) => (
                <li key={s} className={i === step ? "current" : i < step ? "done" : ""}>
                  <span className="wizard-step-num">{i < step ? "✓" : i + 1}</span>
                  {s}
                </li>
              ))}
            </ol>
          </div>
          <div className="block wizard-help">
            <h2>Repère</h2>
            <p className="muted">{STEP_HELP[step]}</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
