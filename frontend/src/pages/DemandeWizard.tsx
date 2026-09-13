import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Produit } from "../api/client";
import { getUser } from "../auth";

export default function DemandeWizard() {
  const { id } = useParams();
  const nav = useNavigate();
  const user = getUser();
  const [step, setStep] = useState(1);
  const [produits, setProduits] = useState<Produit[]>([]);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({
    objet: "Renouvellement stock",
    montant_demande: 500000,
    duree_mois: 12,
    produit_id: 1,
    situation_fiscale: "en_regle",
    credits_ailleurs: false,
    preuves_externes_ok: false,
    ca: 2400000,
    cmv: 1200000,
    charges_exploitation: 400000,
    revenu_perso: 150000,
    charge_familiale: 60000,
    fonds_propres: 400000,
    total_dettes: 150000,
    actif_total: 900000,
    actif_circulant: 400000,
    passif_circulant: 180000,
    resultat_net: 180000,
    preuve_revenu: "N2",
    preuve_charge: "N2",
    saisonnier: false,
    type_piece: "RELEVE",
  });

  useEffect(() => {
    api.produits().then(setProduits).catch(() => undefined);
  }, []);

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit() {
    setErr("");
    try {
      const created = await api.createDemande({
        membre_id: Number(id),
        agent_id: user?.id ?? 1,
        objet: form.objet,
        montant_demande: form.montant_demande,
        duree_mois: form.duree_mois,
        produit_id: form.produit_id,
        situation_fiscale: form.situation_fiscale,
        credits_ailleurs: form.credits_ailleurs,
        preuves_externes_ok: form.preuves_externes_ok,
        collecte: {
          ca: form.ca,
          cmv: form.cmv,
          charges_exploitation: form.charges_exploitation,
          revenu_perso: form.revenu_perso,
          charge_familiale: form.charge_familiale,
          fonds_propres: form.fonds_propres,
          total_dettes: form.total_dettes,
          actif_total: form.actif_total,
          actif_circulant: form.actif_circulant,
          passif_circulant: form.passif_circulant,
          resultat_net: form.resultat_net,
          preuve_revenu: form.preuve_revenu,
          preuve_charge: form.preuve_charge,
          saisonnier: form.saisonnier,
        },
      });
      if (form.credits_ailleurs && form.preuves_externes_ok) {
        await api.piece(created.id, { type_piece: form.type_piece, qualite_ocr: "ok" });
      }
      await api.analyser(created.id);
      nav(`/demandes/${created.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    }
  }

  return (
    <div className="page">
      <h1>Demande — étape {step}/3</h1>
      <p className="lede">Collecte A–E. Les formules restent dans le moteur, pas ici.</p>
      {step === 1 && (
        <div className="grid two">
          <label className="field">
            Objet
            <input value={form.objet} onChange={(e) => set("objet", e.target.value)} />
          </label>
          <label className="field">
            Montant (FCFA)
            <input
              type="number"
              value={form.montant_demande}
              onChange={(e) => set("montant_demande", Number(e.target.value))}
            />
          </label>
          <label className="field">
            Durée (mois)
            <input type="number" value={form.duree_mois} onChange={(e) => set("duree_mois", Number(e.target.value))} />
          </label>
          <label className="field">
            Produit
            <select value={form.produit_id} onChange={(e) => set("produit_id", Number(e.target.value))}>
              {produits.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.libelle}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {step === 2 && (
        <div className="grid two">
          <label className="field">
            CA annuel
            <input type="number" value={form.ca} onChange={(e) => set("ca", Number(e.target.value))} />
          </label>
          <label className="field">
            CMV
            <input type="number" value={form.cmv} onChange={(e) => set("cmv", Number(e.target.value))} />
          </label>
          <label className="field">
            Charges exploitation
            <input
              type="number"
              value={form.charges_exploitation}
              onChange={(e) => set("charges_exploitation", Number(e.target.value))}
            />
          </label>
          <label className="field">
            Revenu perso
            <input type="number" value={form.revenu_perso} onChange={(e) => set("revenu_perso", Number(e.target.value))} />
          </label>
          <label className="field">
            Charges familiales
            <input
              type="number"
              value={form.charge_familiale}
              onChange={(e) => set("charge_familiale", Number(e.target.value))}
            />
          </label>
          <label className="field">
            Preuve revenu
            <select value={form.preuve_revenu} onChange={(e) => set("preuve_revenu", e.target.value)}>
              <option>N1</option>
              <option>N2</option>
              <option>N3</option>
            </select>
          </label>
        </div>
      )}
      {step === 3 && (
        <div className="grid">
          <label className="field">
            Situation fiscale
            <select value={form.situation_fiscale} onChange={(e) => set("situation_fiscale", e.target.value)}>
              <option value="en_regle">En règle</option>
              <option value="a_verifier">À vérifier</option>
              <option value="non_fourni">Non fourni</option>
              <option value="non_conforme">Non conforme</option>
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.credits_ailleurs}
              onChange={(e) => set("credits_ailleurs", e.target.checked)}
            />{" "}
            Crédits ailleurs (hors institution)
          </label>
          {form.credits_ailleurs && (
            <>
              <label>
                <input
                  type="checkbox"
                  checked={form.preuves_externes_ok}
                  onChange={(e) => set("preuves_externes_ok", e.target.checked)}
                />{" "}
                Pièces déposées (relevé, carnet, échéancier, BIC)
              </label>
              <label className="field">
                Type de pièce
                <select value={form.type_piece} onChange={(e) => set("type_piece", e.target.value)}>
                  <option>RELEVE</option>
                  <option>CARNET</option>
                  <option>ECHEANCIER</option>
                  <option>BIC</option>
                  <option>FISCAL</option>
                </select>
              </label>
              {!form.preuves_externes_ok && (
                <p className="error">Sans pièces exigibles : refus catégorique à l’analyse.</p>
              )}
            </>
          )}
        </div>
      )}
      {err && <p className="error">{err}</p>}
      <div className="actions">
        {step > 1 && (
          <button className="btn ghost" onClick={() => setStep(step - 1)}>
            Retour
          </button>
        )}
        {step < 3 && (
          <button className="btn" onClick={() => setStep(step + 1)}>
            Suite
          </button>
        )}
        {step === 3 && (
          <button className="btn teal" onClick={submit}>
            Analyser
          </button>
        )}
      </div>
    </div>
  );
}
