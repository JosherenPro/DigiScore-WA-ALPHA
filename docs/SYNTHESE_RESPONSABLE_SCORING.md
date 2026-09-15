# Note — responsable scoring

À : owner du package `scoring/`  
De : backend / BDD  
Objet : ce que le back a figé, ce qui est **à toi**, ce que plus de CSV ne réparera pas.

Le moteur **règles** (`digiscore.pipeline.run`) est la seule décision exposée à la démo. Le ML n’est pas branché. On n’a **pas** modifié `scoring/` volontairement.

Contrat inchangé : [GUIDE_SCORING.md](GUIDE_SCORING.md) · [scoring/SPEC.md](../scoring/SPEC.md). **Données enrichies (mix 120k, deux cahiers, dates)** : [DONNEES_RESPONSABLE_MODELE.md](DONNEES_RESPONSABLE_MODELE.md). Plan interne data : [PLAN_ROBUSTESSE_DONNEES.md](PLAN_ROBUSTESSE_DONNEES.md).

---

## Ce que le back a figé (ne pas contourner)

| Sujet | État |
|--------|------|
| Appel unique | `POST /demandes/{id}/analyser` → `dossier_builder` → `run(dossier)` → persist |
| Réponse | `response_model=ScoringOut` = `ScoreResult`. **Aucun** champ `ml_assistance` furtif : FastAPI le supprimerait sans erreur |
| ML masqué | `GET /capabilities` : `ml_scorecard`, `anomalies`, `simulation`, `early_warning` = `false`. `ML_ENABLED=0` |
| Ré-analyse | Avant écrasement : copie vers `score_result_history` / `financial_ratio_history` |
| Version | `score_result.engine_version` = `rules-v1` |
| Auth | Relancer `/analyser` exige `Authorization: Bearer` (`agent` / `demo`) |

Règle produit si un jour on branche le ML : **il éclaire, l’humain décide**. Jamais `eligible`, `zone`, `message_code`, knockouts, `next_queue`. Routes ML **dédiées**, pas un champ en plus sur `/analyser`.

---

## Ta liste — 14 défauts, toujours dans `scoring/`

Tous vérifiés par les collègues (exécution), **aucun** exposé par l’API aujourd’hui. Les corriger **chez toi** avant qu’on ouvre une route. On ne masquera pas un bug moteur par un adaptateur back.

### Bloquants (ne pas exposer tant que c’est vrai)

1. **Proba de défaut non calibrée** — `class_weight="balanced"` + seuils 0,10 / 0,20 / 0,35. Mesure : défaut réel ~0,20 vs proba ~0,46 → 71 % des dossiers décotés au max. Calibrer ou retirer les seuils absolus.
2. **Monte Carlo dégénéré** — même tirage inflow/outflow → `p_incident` vaut 0 ou 1, jamais un entre-deux. Deux tirages indépendants.
3. **Upsell hors RCSD** — `limits.py` × 1,1 puis arrondi au plus proche. Ex. plafond 870 k → suggestion 960 k (RCSD 1,37 vs confort 1,50).
4. **Anomalies thin-file** — `revenus_sur_epargne` explose si épargne faible. **MEM-004** (jeu démo) score 1,0. Log / borne / exclure `thin_file`.

### Moyens

5. `eligible: true` + `montant_eligible: 0` (RCSD saturé, pas de knockout).
6. Score **= 40** : zone rejet (`<= 40`) mais palier plafond « analyse » (`< 40`) → saut 350 k → 650 k. Aligner `pipeline.py` et `limits.py`.
7. Façade `ml.py` : 5 clés si `ML_ENABLED=0`, 6 si `1` → `KeyError` sur `anomaly_score` par défaut.
8. Contrefactuels triés sur `variation_min` (26 mois classé avant 50 000 FCFA).
9. Train/serve scorecard : AUC 0,711 sur synthétique (`montant_sur_plafond ~ N(0.68)`), dossiers réels ~0,17.

### Mineurs

10. Pas de `ge=0` sur `montant` / durées / épargne.
11. `ca = a.ca or 1` → marge absurde si CA nul.
12. `rotation_stocks_jours` calculé, jamais noté.
13. `_sigmoid` avec `2.718…` au lieu de `math.exp`.
14. `recommend_credit_limit` rappelle `run()` → pipeline **deux fois** par dossier.

**Ne pas toucher** (sain) : knockouts, ordre `policy.py`, arrondis vers le bas, contrat de sérialisation `ScoreResult`.

---

## GUIDE_ML vs ton code — trancher avant Phase 2

Le guide décrit des contrats que `scoring/` ne produit pas. Tant que ce n’est pas arbitré, le back n’ouvrira pas les routes.

| Guide | Code actuel |
|--------|-------------|
| `scenario: "mauvaise_recolte"` (string) | `{"type", "intensite"}` ; type inconnu → `normal` silencieux |
| `p10` / `p50` / `p90` à plat | sous `trajectoires` |
| `seed: 42` | défaut `72` |
| anomalie : `value`, `reference_value`, `severity` | `feature`, `z_score`, `message` |
| `scope_excluded` thin-file | absent |
| `default_probability`, `top_factors` | `probabilite_defaut`, `contributions` |

`scoring/models/scorecard_v1.joblib` est commité (20k synthétiques). On le **laisse** derrière `ML_ENABLED=0`. Ne pas l’activer pour le jury.

Ping **back + front** si tu renommes un `message_code` ou étends `DossierInput`.

---

## Plus de CSV ≠ modèle meilleur

On peut dater `outstanding_loan`, ancrer l’épargne, densifier les mouvements — **c’est fait.** Détail pour toi : [DONNEES_RESPONSABLE_MODELE.md](DONNEES_RESPONSABLE_MODELE.md). Historique interne : [PLAN_ROBUSTESSE_DONNEES.md](PLAN_ROBUSTESSE_DONNEES.md).

Ça te donnera des **cibles constructibles** le jour où la FUCEC livre de vrais historiques.

Ça **ne** remplace **pas** :

- tes 14 défauts (c’est du code) ;
- un entraînement sur 120k lignes générées (tu apprendrais le générateur, le guide le dit déjà).

Les 12 profils démo (MEM-001 / 004 / 009) restent le contrat golden. `pytest scoring/tests` avant tout merge.

---

## Recette back (si tu changes `run`)

1. `pytest scoring/tests`
2. Login `agent` / `demo` → Bearer → `POST /demandes/1/analyser` (MEM-001)
3. Relancer `/analyser` : une ligne dans `score_result_history`, l’écran voit toujours **un** `score_result`
