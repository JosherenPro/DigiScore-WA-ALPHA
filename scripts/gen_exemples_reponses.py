"""Rejoue les cas de demo et ecrit les vrais corps de reponse dans un .md."""
import sys, json, copy, subprocess
sys.path[:0] = [".", "scoring"]
from digiscore.pipeline import run
from digiscore.ml import run_ml_assistance
from digiscore.simulation import simulate_resilience
from digiscore.counterfactual import suggest_counterfactuals

def _base(**over):
    d = {
        "membre": {"id": 1, "anciennete_mois": 48, "statut": "actif"},
        "compte": {"solde": 400000, "date_ouverture_jours": 800, "statut": "actif"},
        "historique": {
            "credits_passes": [{"montant": 400000, "statut": "solde", "nb_retards": 0}],
            "incidents": [], "epargne_moy_3m": 400000, "epargne_moy_6m": 380000,
            "nb_mouvements_90j": 6,
        },
        "demande": {"montant": 500000, "duree_mois": 12, "plafond_produit": 3000000,
                    "situation_fiscale": "en_regle"},
        "analyse": {
            "ca": 3600000, "cmv": 1800000, "charges_exploitation": 600000,
            "produits_financiers": 20000, "revenu_perso": 200000, "charge_familiale": 80000,
            "fonds_propres": 800000, "total_dettes": 200000, "actif_total": 1500000,
            "actif_circulant": 700000, "passif_circulant": 250000, "stock_moyen": 300000,
            "resultat_net": 400000, "valeur_garanties": 350000,
            "preuve_revenu": "N3", "preuve_charge": "N2",
            "tresorerie": [{"mois": m, "flux_entrant": 300000, "flux_sortant": 180000}
                           for m in range(1, 13)],
        },
    }
    d = copy.deepcopy(d)
    for k, v in over.items():
        if isinstance(v, dict) and k in d:
            d[k].update(v)
        else:
            d[k] = v
    return d

CAS = [
    ("MEM-001", "Bon payeur, demande dans le plafond", _base()),
    ("MEM-002", "Montant au-dela du plafond calcule", _base(
        historique={"epargne_moy_3m": 100_000, "epargne_moy_6m": 100_000},
        demande={"montant": 2_900_000, "duree_mois": 60, "seuil_caution": 3_000_000})),
    ("MEM-003", "Incident de remboursement grave", _base(
        historique={"incidents": [{"gravite": "grave"}]})),
    ("MEM-004", "Thin-file bloque par le RCSD", {
        "membre": {"id": 4, "anciennete_mois": 2, "statut": "actif"},
        "compte": {"solde": 35000, "date_ouverture_jours": 60, "statut": "actif"},
        "historique": {"credits_passes": [], "incidents": [], "epargne_moy_3m": 30000,
                       "epargne_moy_6m": 20000, "nb_mouvements_90j": 1},
        "demande": {"montant": 400000, "duree_mois": 8, "situation_fiscale": "non_fourni"},
        "analyse": {"ca": 900000, "cmv": 500000, "charges_exploitation": 200000,
                    "revenu_perso": 60000, "charge_familiale": 30000, "fonds_propres": 50000,
                    "total_dettes": 80000, "actif_total": 200000, "actif_circulant": 80000,
                    "passif_circulant": 60000, "stock_moyen": 40000, "resultat_net": 40000,
                    "preuve_revenu": "N1", "preuve_charge": "N1",
                    "patrimoine": {"actifs_productifs": 80000, "actifs_non_productifs": 20000,
                                   "passifs_formels": 40000, "passifs_informels": 20000}},
    }),
    ("MEM-008", "Capacite de remboursement insuffisante", _base(
        analyse={"ca": 800_000, "cmv": 550_000, "charges_exploitation": 300_000},
        demande={"montant": 800_000})),
    ("MEM-009", "Montant exceptionnel, voie CIC", _base(
        demande={"montant": 10_000_000, "duree_mois": 24, "plafond_produit": 12_000_000,
                 "exceptionnel": True, "seuil_caution": 2_000_000,
                 "nb_cautions_eligibles": 2, "nb_cautions_min": 2},
        analyse={"ca": 18_000_000, "cmv": 8_000_000, "charges_exploitation": 2_500_000})),
    ("MEM-010", "Compte gele", _base(membre={"id": 10, "anciennete_mois": 70, "statut": "gele"})),
    ("KO-ESG", "Activite exclue (ESG)", _base(demande={"exclusion_esg": True})),
    ("KO-CAUTION", "Cautionnaire eligible manquant", _base(
        demande={"montant": 2_000_000, "seuil_caution": 2_000_000,
                 "nb_cautions_eligibles": 0, "nb_cautions_min": 1})),
    ("KO-PREUVES", "Credits ailleurs sans justificatifs", _base(
        historique={"credits_ailleurs": True, "preuves_externes_ok": False,
                    "credits_passes": [], "epargne_moy_6m": 40000})),
]

def j(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)

out = []
w = out.append
rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

w("# Exemples de corps de réponse — moteur de scoring et couche ML\n")
w("Sorties **réelles** produites en rejouant les cas de démo à travers")
w("`digiscore.pipeline.run()` et `digiscore.ml.run_ml_assistance()`.\n")
w(f"- Commit : `{rev}`")
w("- Régénérable : voir la section « Reproduire » en fin de document.")
w("- Aucune donnée client : tous les dossiers sont synthétiques.\n")
w("Ces corps correspondent à ce que renvoie `POST /demandes/{id}/analyser`")
w("(`response_model=ScoreResult`). Les clés JSON sont en français, c'est le")
w("contrat front.\n")
w("---\n")
w("## Vue d'ensemble\n")
w("| Cas | Situation | `message_code` | `zone` | `eligible` | Score | Plafond (FCFA) |")
w("|---|---|---|---|---|---:|---:|")
results = []
for code, label, dossier in CAS:
    r = run(dossier)
    results.append((code, label, dossier, r))
    montant = f"{int(r.montant_eligible):,}".replace(",", " ")
    w(f"| `{code}` | {label} | `{r.message_code}` | {r.zone} | "
      f"{'oui' if r.eligible else 'non'} | {r.score_global} | {montant} |")
w("")
w("---\n")
w("## Corps complets — `POST /demandes/{id}/analyser`\n")
for code, label, dossier, r in results:
    w(f"### `{code}` — {label}\n")
    if r.knockouts:
        w(f"> Knockout : {', '.join(k.code for k in r.knockouts)} — "
          f"`montant_eligible` forcé à 0 et `eligible: false`.\n")
    w("```json")
    w(j(r.model_dump()))
    w("```\n")

w("---\n")
w("## Couche ML — `run_ml_assistance()`\n")
w("Consultatif. Ces champs **ne modifient jamais** `eligible`, `montant_eligible`,")
w("`zone`, `message_code` ni les knockouts.\n")
w("### Contrat quand le ML est désactivé (`ML_ENABLED=0`, défaut)\n")
w("Les clés sont **identiques** à l'état actif, seules les valeurs sont nulles —")
w("un consommateur n'a jamais de `KeyError`.\n")
w("```json")
w(j(run_ml_assistance(_base(), enabled=False)))
w("```\n")
for code, label in [("MEM-001", "bon payeur"), ("MEM-004", "thin-file"), ("MEM-010", "compte gelé")]:
    dossier = dict(CAS[[c[0] for c in CAS].index(code)][2])
    w(f"### `{code}` ({label}) — ML actif\n")
    w("```json")
    w(j(run_ml_assistance(dossier, enabled=True)))
    w("```\n")

w("---\n")
w("## Simulateur de résilience — `simulate_resilience()`\n")
w("Déterministe : même dossier + même `seed` ⇒ réponse strictement identique.\n")
base = _base()
for title, scenario in [("Scénario normal", None),
                        ("Choc de revenus −40 %", {"type": "choc", "intensite": -0.40}),
                        ("Maladie du chef de ménage", {"type": "maladie"})]:
    res = simulate_resilience(base, scenario=scenario, trajectories=2000, seed=72)
    w(f"### {title}\n")
    w("```json")
    w(j(res))
    w("```\n")

w("---\n")
w("## Contrefactuels — `suggest_counterfactuals()`\n")
w("Leviers minimaux pour atteindre un score cible. **Ne lève jamais un knockout.**\n")
cf_ok = _base(membre={"anciennete_mois": 10},
              historique={"credits_passes": [], "epargne_moy_3m": 60000,
                          "epargne_moy_6m": 60000, "nb_mouvements_90j": 4},
              analyse={"valeur_garanties": 50000, "preuve_revenu": "N1", "preuve_charge": "N1"},
              demande={"montant": 300000, "duree_mois": 12})
w("### Dossier sans knockout, sous la cible\n")
w("```json")
w(j(suggest_counterfactuals(cf_ok, target_score=71)))
w("```\n")
w("### Dossier avec knockout — réponse bloquée\n")
w("```json")
w(j(suggest_counterfactuals(CAS[3][2], target_score=71)))
w("```\n")

w("---\n")
w("## Reproduire\n")
w("```bash")
w("python3 -m pytest -q          # suite complète")
w("python3 scripts/gen_exemples_reponses.py > docs/EXEMPLES_REPONSES.md")
w("```\n")
w("Le script est volontairement sans dépendance à la base : il construit les")
w("dossiers en mémoire et n'appelle que le package `scoring/`.")

sys.stdout.write("\n".join(out) + "\n")
