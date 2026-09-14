# Recommandations backend & BDD — DigiScore-WA

Document de travail à destination du développeur backend. Il consolide une
revue du moteur `scoring/`, de la couche ML, des routes FastAPI, du schéma SQL
et de la cohérence entre `docs/ARCHI.md` et `docs/GUIDE_ML_BACKEND_DATA.md`.

Chaque point est référencé `fichier:ligne` pour être vérifiable directement.

**Statut de la vérification** : les 29 tests passent (`python3 -m pytest`).
Aucun des points ci-dessous n'est couvert par la suite existante.

---

## Ordre de traitement recommandé

| Prio | Sujet | Pourquoi maintenant |
|---|---|---|
| **P0** | Bug de pagination front/back | Casse 3 écrans du parcours de démo |
| **P0** | Arbitrer le périmètre ML | Deux docs du dépôt se contredisent |
| **P1** | Historiser `score_result` / `financial_ratio` | Chaque `/analyser` détruit de la donnée définitivement |
| **P1** | Dettes transverses (`response_model`, OpenAPI, migrations) | Pièges silencieux, coût croissant |
| **P2** | Dater l'issue crédit (`outstanding_loan`) | Prérequis de tout modèle supervisé |
| **P2** | Endpoints ML | Seulement après arbitrage du périmètre |

---

# P0 — Le front est cassé contre le backend actuel

La pagination ajoutée sur 4 routes n'a jamais été répercutée côté front.

| Route | Backend renvoie | Front attend |
|---|---|---|
| `GET /membres` | `PageMembres` = `{items, page, page_size, total}` | `MembreResume[]` |
| `GET /demandes` | `PageDemandes` | `DemandeResume[]` |
| `GET /files/chef` | `PageDemandes` | `DemandeResume[]` |
| `GET /files/cic` | `PageDemandes` | `DemandeResume[]` |

Schémas : `backend/app/schemas/dossier.py:85` et `:149`.
Client front : `frontend/src/api/client.ts:19,22,39,40`.

Le front stocke l'objet page tel quel puis itère dessus :

- `frontend/src/pages/AgentHome.tsx:36` → `rows.map(...)` — accueil agent
- `frontend/src/pages/AgentHome.tsx:67` → `membres.map(...)` — recherche membre
- `frontend/src/pages/Queue.tsx:47` → `rows.map(...)` — files chef **et** CIC

`.map` sur un objet lève un `TypeError` à l'exécution. Il n'existe **aucune
occurrence de `.items` dans tout `frontend/src/`** : la correction n'a été faite
nulle part.

Les types TypeScript ne protègent pas : `req<T>` fait un
`res.json() as Promise<T>` (`client.ts:12`), donc le mensonge passe à la
compilation et casse au runtime.

**Décision à prendre à deux (back + front)** : soit le front lit `.items`, soit
le backend redevient compatible. À trancher avant tout autre chantier — c'est le
parcours M1→M5 de la démo.

---

# P0 — Arbitrage de périmètre : deux documents se contredisent

`docs/ARCHI.md:83` déclare **OUT du périmètre 72 h** : « core banking / BIC /
Flooz live, **ML**, M6/M7 temps réel, **JWT / SSO**, i18n éwé, backend dans
Compose ».

`docs/GUIDE_ML_BACKEND_DATA.md` planifie 5 phases de ML, et exige des routes
gatées par rôle avec `403`.

Tant que ce n'est pas arbitré, le dev backend ne sait pas si les 5 endpoints ML
sont son travail de cette semaine ou d'un sprint ultérieur. **Aucun code ne doit
partir sur la Phase 2+ avant cet arbitrage.**

### Conséquence concrète sur l'identité

Il n'existe aujourd'hui aucune authentification :

- `backend/app/api/routes.py:75-80` — `/auth/login` prend un simple
  `login: str`, sans mot de passe, sans token, sans session.
- Aucune des 19 routes n'a de dépendance de rôle : toutes n'injectent que
  `Depends(get_db)`.
- `/demandes/{id}/soumettre?utilisateur_id=1` passe l'identité en **query param
  avec défaut à 1** (`routes.py:449`).
- `/demandes/{id}/decision` (`routes.py:478`) ne vérifie aucun rôle : n'importe
  quel appelant peut poser un avis CIC.

C'est cohérent avec le périmètre déclaré (JWT/SSO = OUT), donc **ce n'est pas un
oubli**. Mais cela signifie que le `403` exigé par le guide ML est hors périmètre
actuel : le guide demande quelque chose qu'`ARCHI.md` a explicitement exclu, sans
le signaler.

---

# P1 — Dettes backend transverses

### 1. `response_model` filtre silencieusement tout enrichissement ML

`routes.py:390` déclare `/demandes/{id}/analyser` avec
`response_model=ScoringOut`, soit exactement `digiscore.types.ScoreResult`.

FastAPI filtre la réponse sur le `response_model` : **tout champ
`ml_assistance` ajouté sera supprimé sans erreur ni log.** Le symptôme est un
enrichissement qui « disparaît » sans trace.

À prévoir le jour du branchement ML : soit une route dédiée, soit un nouveau
`response_model` qui enveloppe `ScoreResult`.

### 2. Deux sources OpenAPI divergentes

- `docs/openapi.json` : à jour, 20 paths.
- `docs/openapi.yaml` : périmé, il manque `POST /demandes/{id}/pieces`.

Or `ARCHI.md:88` dit au front « n'invente pas d'endpoint ; consomme OpenAPI ».
Désigner laquelle fait foi, ou régénérer le yaml depuis
`backend/scripts/export_openapi.py`.

### 3. Il n'existe aucun mécanisme de migration

`docker-compose.yml:12` monte `schema.sql` dans
`/docker-entrypoint-initdb.d/`. Postgres n'exécute ce répertoire **que si le
volume de données est vide**, et le volume `pgdata` est persistant.

Le fichier contient par ailleurs **36 `CREATE TABLE` bruts, zéro
`IF NOT EXISTS`** — un re-run échouerait de toute façon.

Conséquence : ajouter une table à `schema.sql` ne crée rien tant qu'on ne fait
pas `docker compose down -v`, ce qui **détruit les 120 000 lignes** et impose un
rechargement complet.

Le test d'acceptation n°6 du guide (« Les migrations et seeds démarrent avec
`docker compose up -d` ») est donc **faux tel qu'écrit** : il n'y a pas de
migrations, il y a une initialisation one-shot.

À trancher : introduire Alembic (l'ORM existe déjà), ou documenter `down -v`
comme procédure assumée avec l'ordre de rechargement.

### 4. `ML_ENABLED` n'est documenté nulle part

C'est pourtant la variable qui gouverne toute la couche
(`scoring/digiscore/adaptive/scorecard_ml.py:216`, défaut `"0"`). C'est elle qui
doit alimenter `GET /capabilities`. Le guide ne la cite pas une seule fois.

---

# P1 — Chantier BDD : rendre la base capable de servir un modèle

Le problème n'est pas le volume, c'est **la datation**.

### 1. Aucune cible (label) n'est constructible

`outstanding_loan` (`backend/db/schema.sql:469`) est le seul endroit où une issue
de crédit pourrait vivre. Il porte `days_late` et `status`, mais :

- **la table n'a aucune colonne de date.** Pas de `disbursed_on`, pas de
  `due_on`, pas d'`as_of`. Sur les 18 colonnes DATE/TIMESTAMPTZ du schéma,
  aucune n'appartient à cette table.
- `application_id` est **nullable** — impossible de rattacher de façon fiable
  une issue à la demande qui l'a produite.
- le CSV de volume confirme :
  `external_code,principal,outstanding,days_late,status`.

Conséquence : le `p_par30_90j` demandé en Phase 5 du guide est **impossible à
construire**. « PAR30 à 90 jours du décaissement » suppose une date de
décaissement et une date d'observation ; ni l'une ni l'autre n'existe.
`days_late` est un instantané sans « à quelle date ».

### 2. Fuite de données garantie par construction

Le guide interdit en Phase 4 les variables postérieures à la décision. Le schéma
rend cette règle inapplicable :

| Table | Problème |
|---|---|
| `savings_snapshot` (`schema.sql:106`) | `avg_balance_3m/6m/12m` sans **aucune date ni `as_of`** — une seule ligne d'état courant. Entraîner sur une demande passée utiliserait l'épargne d'aujourd'hui pour prédire un défaut d'hier. Pas d'`UNIQUE(account_id)` non plus. |
| `account.current_balance` | état courant, même problème |
| `financial_ratio` (`schema.sql:301`) | `UNIQUE(application_id)`, **écrasé sur place** par `/analyser` (`routes.py:417-438`, `setattr` sur la ligne existante) |
| `score_result` (`schema.sql:399`) | idem : `UNIQUE(application_id)`, écrasé (`routes.py:399-414`) |

**Ré-analyser un dossier détruit ce que le moteur avait vu la première fois.**
C'est la raison pour laquelle ce chantier est en P1 et non en P2 : chaque
`/analyser` exécuté aujourd'hui détruit de la donnée qu'on ne pourra jamais
reconstituer.

**Ce qui est déjà exploitable** : les flux d'événements bruts sont datés —
`past_credit.granted_on/closed_on`, `incident.occurred_on`,
`account_movement.moved_on` (avec l'index `(account_id, moved_on DESC)`),
`member.joined_on`, `account.opened_on`, `credit_application.applied_at`,
`decision.decided_at`. On peut donc **recalculer** les agrégats d'épargne à une
date donnée plutôt que lire un snapshot mutable. L'index existe déjà pour ça.

### 3. La trésorerie n'est pas ancrée dans le calendrier

`monthly_cashflow.month_no` (`schema.sql:283`) est un entier relatif `1..12`,
pas une date. Impossible d'aligner la série sur une saison réelle, sur un choc
daté, ou sur la fenêtre d'observation de la cible.

### 4. Aucune traçabilité de modèle

`score_result` n'a ni `engine_version` ni `model_version`. Il n'existe ni
registre de modèles ni journal d'inférence. Or le guide exige « chaque réponse
ML porte un `model_version` » (test d'acceptation n°5) et un mode shadow — qui
n'a de sens que si l'on peut comparer dans le temps ce que le modèle aurait dit
à ce que l'humain a décidé.

### 5. `par_indicator` n'est pas un label

`schema.sql:494` : agrégat **par agence**, avec un défaut codé en dur
`DATE '2026-09-13'`. Utile pour un tableau de bord, inutilisable comme cible au
niveau membre.

### Chantier BDD, par ordre de dépendance

1. **Dater l'issue** — `outstanding_loan` : `disbursed_on`, `observed_on`,
   `due_on`, et `application_id` NOT NULL. Sans ça, aucune cible n'existe.
2. **Historiser au lieu d'écraser** — `score_result` / `financial_ratio`
   append-only (`computed_at` + `engine_version`), ou tables d'historique
   jumelles.
3. **Dater les agrégats** — `savings_snapshot` avec `as_of` +
   `UNIQUE(account_id, as_of)` ; ou l'abandonner et recalculer depuis
   `account_movement`.
4. **Ancrer la trésorerie** — un `period_month DATE` à côté de `month_no`.
5. **Figer le vecteur de features** par demande au moment de la décision. Seule
   garantie réelle contre la fuite, et ce qui rend possible le « rejouer le même
   scénario » de la Phase 3.
6. **Tracer les modèles** — `model_version` sur `score_result`, plus les deux
   tables additives que le guide nomme déjà.

### Conflit à arbitrer dans le guide

`GUIDE_ML_BACKEND_DATA.md:303-305` pose : « toutes les tables ML sont additives :
**aucune modification destructive de `credit_application`, `score_result` ou
`financial_ratio`** ».

Mais servir un modèle exige précisément de toucher `score_result` et
`financial_ratio` — au minimum lever leur `UNIQUE` et les rendre append-only.
**La règle du guide et l'objectif du guide se contredisent.** Soit on historise
ces tables, soit on crée des tables miroir versionnées et on assume la
duplication.

### Réserve importante

Même avec ces six changements, les 5 000 lignes d'`outstanding_loan` restent
**générées synthétiquement** : `status` et `days_late` sortent d'un générateur,
pas d'un processus de remboursement réel. Un modèle entraîné dessus apprendrait
le générateur — le guide le dit lui-même et il a raison.

Ce chantier ne sert donc pas à entraîner maintenant. Il sert à ce que **le jour
où la FUCEC fournit de vrais historiques, les données soient collectables sans
rétro-ingénierie.**

---

# P2 — Endpoints ML restants (après arbitrage)

Aucun des 5 endpoints du guide n'existe. `routes.py` n'importe aujourd'hui que
`digiscore.pipeline.run` (`routes.py:53`) — la couche `digiscore.ml` n'est
jamais appelée.

| Endpoint | Phase | Dépendances non satisfaites |
|---|---|---|
| `GET /capabilities` | 1 | doit lire `ML_ENABLED` (non documenté) |
| `GET /demandes/{id}/anomalies` | 2 | contrat guide ≠ contrat code (voir plus bas) |
| `POST /demandes/{id}/simuler` | 3 | contrat guide ≠ contrat code |
| `POST /demandes/{id}/simulation/enregistrer` | 3 | table `resilience_simulation` absente |
| `GET /portefeuille/alertes` | 5 | exige un `403` (pas d'auth), et une cible PAR inexistante |

### Le guide décrit des contrats qui ne correspondent pas au code existant

C'est le point le plus coûteux en temps : le dev ne saura pas qui fait autorité,
le `.md` ou `scoring/`.

| Guide | Code réel | Conséquence |
|---|---|---|
| `scenario: "mauvaise_recolte"` (string) | `simulation.py:17-27` attend `{"type":…, "intensite":…}` et ne connaît que `choc`/`maladie`/`inflation`/`normal` | un type inconnu **retombe silencieusement sur `normal` = choc nul** ; la simulation renvoie un résultat plausible et faux |
| `p10`/`p50`/`p90` à plat | imbriqués sous `trajectoires` | adaptateur à écrire |
| `seed: 42` | défaut `seed=72` | reproductibilité annoncée ≠ réelle |
| `explication: [...]` en réponse simulation | absent de `simulate_resilience()` | à construire, non spécifié |
| anomalie : `value`, `reference_value`, `severity` | `detect()` ne renvoie que `feature`, `z_score`, `message` | 3 champs sur 6 n'existent pas |
| `scope_excluded: true` pour les thin-files | n'existe pas | comportement à écrire de zéro |
| `anomaly-v2`, `resilience-v2`, `scorecard-v2` | artefacts en `v1` | réentraîner ou pas ? non dit |
| `default_probability`, `top_factors`, `mode: "shadow"` | `probabilite_defaut`, `contributions`, pas de `mode` | renommages non tracés |
| `weights_learned` indexé sur 6 critères métier | `scorecard_v1_poids.json` indexe **11 features** | l'exemple du guide n'est pas produisible |

### Contradiction Phase 4 vs état du dépôt

Le guide dit « ne pas entraîner un modèle de défaut sur des profils
synthétiques » et classe la scorecard **en dernier**. Or
`scoring/models/scorecard_v1.joblib` est **déjà commité**, entraîné sur 20 000
lignes synthétiques, et `ml.py` l'active dès `ML_ENABLED=1`. L'ignorer, le
supprimer, ou le laisser derrière le flag ? Non tranché.

### Phase 5 ignore l'existant

Le guide invente `GET /portefeuille/alertes` sans mentionner que
`/vision/portefeuille` et `/vision/recouvrement` existent déjà
(`routes.py:594,607`), ni que `outstanding_loan`, `portfolio_followup`,
`par_indicator` et `recovery_case` sont déjà au schéma. La règle « Backend
n'invente pas de table » est bonne, mais le guide n'indique jamais quelles
tables existantes consommer.

---

# Annexe — Défauts confirmés dans `scoring/` et la couche ML

Ces points conditionnent ce que le backend peut exposer. Tous ont été vérifiés
par exécution, aucun n'est couvert par les tests.

### Bloquants

1. **La probabilité de défaut n'est pas une probabilité.**
   `adaptive/scorecard_ml.py:130` entraîne avec `class_weight="balanced"`, ce
   qui fait du modèle un score de rang, pas une probabilité calibrée. Or
   `credit_limit_ml.py:19-28` applique des seuils **absolus** (0.10 / 0.20 /
   0.35) dessus. Mesuré sur 5 000 dossiers : taux de défaut réel 0.199 vs
   proba moyenne prédite 0.459 → **71 % des dossiers subissent la décote
   maximale de 40 %** alors que 20 % défaillent. Cohérent avec le
   `brier_score: 0.214` de `scorecard_v1_metrics.json`.
   → Retirer `class_weight="balanced"`, ou calibrer (`CalibratedClassifierCV`)
   avant d'exposer le champ.

2. **Le Monte Carlo de résilience est dégénéré.**
   `simulation.py:88-90` applique **le même tirage de bruit** aux encaissements
   et aux décaissements. Le net se factorise en
   `noise * (inflow·income − outflow·expenses) − service` : un facteur commun.
   Résultat mesuré : `p_incident` vaut **0.0 ou 1.0, jamais une valeur
   intermédiaire**. Dispersion p10/p50/p90 de ±5 %.
   → Deux tirages indépendants (corrélation explicite si voulue).

3. **La suggestion d'upsell franchit le plafond RCSD.**
   `limits.py:48-49` multiplie par 1,1 puis arrondit **au plus proche**, après
   que `compute_plafond` a pourtant arrondi vers le bas (commentaire l.45). Sur
   le dossier « bon payeur » : plafond 870 000, cap RCSD 877 538, suggestion
   **960 000** → RCSD **1,371** contre une norme de confort de 1,50.

4. **Faux positifs d'anomalie systématiques sur les thin-files.**
   `anomalies.py:38` : `revenus_sur_epargne = ca / max(epargne_6m, 1.0)`, alors
   que le modèle est entraîné sur une loi centrée en 25
   (`train_anomaly.py:20`) :

   ```
   épargne_6m = 380 000 → ratio     9.5 → score 0.592
   épargne_6m =  80 000 → ratio    45.0 → score 0.629
   épargne_6m =  20 000 → ratio   180.0 → score 1.000
   épargne_6m =       0 → ratio 3 600 000 → score 1.000
   ```

   `20 000` est exactement le profil MEM-004 du jeu de démo : la détection
   signale au maximum **la population thin-file que le produit cible**.
   → Passer la feature en log, la borner, ou exclure les thin-files du scope
   (ce que le guide demande déjà, sans que le code le fasse).

### Moyens

5. **`eligible = True` avec `montant_eligible = 0`.** Quand l'endettement
   existant sature le RCSD de confort, `montant_par_rcsd` renvoie 0 sans
   déclencher de knockout. Sortie reproduite :
   `code: MONTANT_PLAFONNE | eligible: True | montant_eligible: 0.0 | score: 74.6`,
   message « Montant demande superieur au plafond : **0 FCFA** proposes ».
   `pipeline.py:100-101` contient en outre du code mort (`MONTANT_PLAFONNE` est
   déjà dans le tuple l.99).

6. **Frontière de zone incohérente à score = 40.** `pipeline.py:15-16` classe en
   rejet si `score <= 40` ; `limits.py:41` n'applique la décote sévère que si
   `score < 40`. Un score de 40,0 est donc **en zone rejet mais reçoit le palier
   « analyse »** : plafond 350 000 à 39,9 → **650 000 à 40,0**. La frontière
   70/71 est, elle, correctement alignée.

7. **La façade ML change de forme selon qu'elle est active.** `ml.py:28-34`
   renvoie 5 clés désactivée, 6 activée (`anomaly_score` en plus). Tout
   consommateur lisant `result["anomaly_score"]` lève un `KeyError` dès que
   `ML_ENABLED=0` — c'est-à-dire **par défaut**. `test_ml.py:86` verrouille la
   forme courte par égalité stricte, donc le test ne peut pas le détecter.

8. **Tri des contrefactuels sur des unités hétérogènes.**
   `counterfactual.py:114` trie sur `variation_min`, qui mêle mois et FCFA :
   « attendre **26 mois** » est classé avant « apporter **50 000 FCFA** de
   garanties » uniquement parce que `26 < 50000`.

9. **Décalage train/serve du scorecard.** `training/generate.py` tire
   `montant_sur_plafond ~ N(0.68, 0.24)` ; les vrais dossiers sont à 0.167.
   L'AUC de 0,711 est mesurée sur la distribution synthétique et ne se
   transporte pas.

### Mineurs

10. `types.py:40` — aucun `ge=0` sur `montant`. Un montant négatif passe :
    `rcsd = 99.0`, `code = UPSELL_POSSIBLE`, `eligible = True`. Idem
    `duree_mois`, `epargne_*`.
11. `financials.py:43` — `ca = a.ca or 1` : avec un CA nul,
    `marge_brute_pct` vaut `-cmv × 100`, valeur absurde exposée telle quelle.
12. `financials.py:47` — `rotation_stocks_jours` calculé et exposé mais n'entre
    dans aucune note.
13. `anomalies.py:113-119` — `_sigmoid` réimplémenté avec la constante littérale
    `2.718281828` ; `math.exp` est plus précis. (La branche est sûre en
    overflow, vérifié.)
14. `ml.py:39` + `credit_limit_ml.py:45` — `recommend_credit_limit` rappelle
    `run()` en interne sans recevoir `rule_result` : **le pipeline complet
    tourne deux fois par dossier**.

---

# Ce qui est sain — ne pas retoucher

- Le cœur du moteur de règles : knockouts, ordre de priorité
  (`policy.py:13-27`), arrondis vers le bas, contrat de sérialisation de
  `ScoreResult`.
- **Toutes les cibles de clés étrangères du guide existent** et sont
  correctement nommées : `credit_application.id`, `app_user.id` sont bien au
  schéma, et le snake_case anglais respecte `backend/db/NAMING.md`.
- La règle additive et l'interdiction d'écrire les anomalies dans
  `score_result`.
- `result_json` pour les tableaux P10/P50/P90 plutôt qu'une colonne par mois.
- L'avertissement sur les fuites de données en Phase 4 du guide : c'est le point
  le plus professionnel du document.
- Les flux d'événements datés (`account_movement`, `past_credit`, `incident`,
  `decision`) : c'est la fondation sur laquelle reconstruire des features
  point-in-time.
- Le front n'appelle aucun endpoint inexistant : les 20 appels de `client.ts`
  ont tous leur route. En endpoints M1–M5, **il ne manque rien**.
