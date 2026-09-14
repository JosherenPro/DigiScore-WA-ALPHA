import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type CollecteBody, type Produit } from "../api/client";

const STEPS = ["Demande", "Activité", "Exploitation", "Bilan", "Preuves"];

const empty: CollecteBody & {
  objet: string;
  montant_demande: number;
  duree_mois: number;
  produit_id: number;
  situation_fiscale: string;
  credits_ailleurs: boolean;
  preuves_externes_ok: boolean;
  type_piece: string;
  qualite_ocr: string;
} = {
  objet: "Renouvellement stock",
  montant_demande: 500000,
  duree_mois: 12,
  produit_id: 1,
  situation_fiscale: "en_regle",
  credits_ailleurs: false,
  preuves_externes_ok: false,
  type_piece: "CNI",
  qualite_ocr: "ok",
  ca: 2400000,
  cmv: 1200000,
  charges_exploitation: 400000,
  produits_financiers: 0,
  revenu_perso: 150000,
  charge_familiale: 60000,
  charge_credits_en_cours: 0,
  fonds_propres: 400000,
  total_dettes: 150000,
  actif_total: 900000,
  actif_circulant: 400000,
  passif_circulant: 180000,
  stock_moyen: 200000,
  resultat_net: 180000,
  preuve_revenu: "N2",
  preuve_charge: "N2",
  saisonnier: false,
  type_activite: "commerce",
  valeur_garanties: 0,
};

export default function DemandeWizard() {
  const { id } = useParams();
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [produits, setProduits] = useState<Produit[]>([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(empty);

  useEffect(() => {
    api
      .produits()
      .then((ps) => {
        setProduits(ps);
        setForm((f) =>
          ps.length && !ps.some((p) => p.id === f.produit_id) ? { ...f, produit_id: ps[0].id } : f,
        );
      })
      .catch(() => undefined);
  }, []);

  function patch<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function collecte(): CollecteBody {
    const {
      ca,
      cmv,
      charges_exploitation,
      produits_financiers,
      revenu_perso,
      charge_familiale,
      charge_credits_en_cours,
      fonds_propres,
      total_dettes,
      actif_total,
      actif_circulant,
      passif_circulant,
      stock_moyen,
      resultat_net,
      preuve_revenu,
      preuve_charge,
      saisonnier,
      type_activite,
      valeur_garanties,
    } = form;
    return {
      ca,
      cmv,
      charges_exploitation,
      produits_financiers,
      revenu_perso,
      charge_familiale,
      charge_credits_en_cours,
      fonds_propres,
      total_dettes,
      actif_total,
      actif_circulant,
      passif_circulant,
      stock_moyen,
      resultat_net,
      preuve_revenu,
      preuve_charge,
      saisonnier,
      type_activite,
      valeur_garanties,
    };
  }

  async function submit() {
    setErr("");
    if (form.qualite_ocr !== "ok") {
      setErr("Reprendre la photo — qualité OCR insuffisante.");
      return;
    }
    setBusy(true);
    try {
      const created = await api.createDemande({
        membre_id: Number(id),
        objet: form.objet,
        montant_demande: form.montant_demande,
        duree_mois: form.duree_mois,
        produit_id: form.produit_id,
        situation_fiscale: form.situation_fiscale,
        credits_ailleurs: form.credits_ailleurs,
        preuves_externes_ok: form.preuves_externes_ok,
        collecte: collecte(),
      });
      await api.piece(created.id, { type_piece: form.type_piece, qualite_ocr: form.qualite_ocr });
      await api.analyser(created.id);
      nav(`/demandes/${created.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h1>Nouvelle demande</h1>
      <p className="lede">Collecte A–E. Les formules CAF / RCSD / score restent dans le moteur.</p>
      <div className="steps">
        {STEPS.map((s, i) => (
          <span key={s} className={i === step ? "on" : ""}>
            {i + 1}. {s}
          </span>
        ))}
      </div>

      {step === 0 && (
        <div className="grid two">
          <label className="field">
            Objet
            <input value={form.objet} onChange={(e) => patch("objet", e.target.value)} />
          </label>
          <label className="field">
            Montant (FCFA)
            <input type="number" value={form.montant_demande} onChange={(e) => patch("montant_demande", Number(e.target.value))} />
          </label>
          <label className="field">
            Durée (mois)
            <input type="number" value={form.duree_mois} onChange={(e) => patch("duree_mois", Number(e.target.value))} />
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
              <option value="commerce">Commerce</option>
              <option value="agriculture">Agriculture</option>
              <option value="services">Services</option>
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
            <input type="number" value={form.ca} onChange={(e) => patch("ca", Number(e.target.value))} />
          </label>
          <label className="field">
            CMV
            <input type="number" value={form.cmv} onChange={(e) => patch("cmv", Number(e.target.value))} />
          </label>
          <label className="field">
            Charges exploitation
            <input type="number" value={form.charges_exploitation} onChange={(e) => patch("charges_exploitation", Number(e.target.value))} />
          </label>
          <label className="field">
            Produits financiers
            <input type="number" value={form.produits_financiers} onChange={(e) => patch("produits_financiers", Number(e.target.value))} />
          </label>
          <label className="field">
            Revenu perso
            <input type="number" value={form.revenu_perso} onChange={(e) => patch("revenu_perso", Number(e.target.value))} />
          </label>
          <label className="field">
            Charge familiale
            <input type="number" value={form.charge_familiale} onChange={(e) => patch("charge_familiale", Number(e.target.value))} />
          </label>
          <label className="field">
            Charge crédits en cours
            <input type="number" value={form.charge_credits_en_cours} onChange={(e) => patch("charge_credits_en_cours", Number(e.target.value))} />
          </label>
        </div>
      )}

      {step === 3 && (
        <div className="grid two">
          <label className="field">
            Fonds propres
            <input type="number" value={form.fonds_propres} onChange={(e) => patch("fonds_propres", Number(e.target.value))} />
          </label>
          <label className="field">
            Total dettes
            <input type="number" value={form.total_dettes} onChange={(e) => patch("total_dettes", Number(e.target.value))} />
          </label>
          <label className="field">
            Actif total
            <input type="number" value={form.actif_total} onChange={(e) => patch("actif_total", Number(e.target.value))} />
          </label>
          <label className="field">
            Actif circulant
            <input type="number" value={form.actif_circulant} onChange={(e) => patch("actif_circulant", Number(e.target.value))} />
          </label>
          <label className="field">
            Passif circulant
            <input type="number" value={form.passif_circulant} onChange={(e) => patch("passif_circulant", Number(e.target.value))} />
          </label>
          <label className="field">
            Stock moyen
            <input type="number" value={form.stock_moyen} onChange={(e) => patch("stock_moyen", Number(e.target.value))} />
          </label>
          <label className="field">
            Résultat net
            <input type="number" value={form.resultat_net} onChange={(e) => patch("resultat_net", Number(e.target.value))} />
          </label>
          <label className="field">
            Valeur garanties
            <input type="number" value={form.valeur_garanties} onChange={(e) => patch("valeur_garanties", Number(e.target.value))} />
          </label>
        </div>
      )}

      {step === 4 && (
        <div className="grid two">
          <label className="field">
            Preuve revenu
            <select value={form.preuve_revenu} onChange={(e) => patch("preuve_revenu", e.target.value)}>
              <option>N1</option>
              <option>N2</option>
              <option>N3</option>
            </select>
          </label>
          <label className="field">
            Preuve charge
            <select value={form.preuve_charge} onChange={(e) => patch("preuve_charge", e.target.value)}>
              <option>N1</option>
              <option>N2</option>
              <option>N3</option>
            </select>
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
          <label className="field">
            Type de pièce
            <select value={form.type_piece} onChange={(e) => patch("type_piece", e.target.value)}>
              <option>CNI</option>
              <option>FISCAL</option>
              <option>RELEVE</option>
              <option>CARNET</option>
              <option>BIC</option>
            </select>
          </label>
          <label className="field">
            Qualité photo (OCR)
            <select value={form.qualite_ocr} onChange={(e) => patch("qualite_ocr", e.target.value)}>
              <option value="ok">ok</option>
              <option value="flou">flou</option>
              <option value="sombre">sombre</option>
              <option value="coupe">coupé</option>
            </select>
          </label>
          {form.qualite_ocr !== "ok" && <p className="error">Reprendre la photo — qualité OCR insuffisante.</p>}
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
          {form.credits_ailleurs && !form.preuves_externes_ok && (
            <p className="error">Sans pièces : l’analyse peut refuser (preuves externes manquantes).</p>
          )}
        </div>
      )}

      {err && <p className="error">{err}</p>}
      <div className="actions">
        {step > 0 && (
          <button className="btn ghost" type="button" onClick={() => setStep(step - 1)}>
            Retour
          </button>
        )}
        {step < 4 && (
          <button className="btn" type="button" onClick={() => setStep(step + 1)}>
            Suite
          </button>
        )}
        {step === 4 && (
          <button className="btn teal" type="button" disabled={busy || form.qualite_ocr !== "ok"} onClick={submit}>
            Enregistrer et analyser
          </button>
        )}
      </div>
    </div>
  );
}
