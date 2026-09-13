---
name: DigiScore Architecture CDC
overview: Architecture membre-centrique non invasive, score/plafond type télécom, workflow Agent→Chef d’agence→CIC, différenciation produit claire, perf 1M+, monorepo React/FastAPI/PostgreSQL, CDC + guide équipe IN/OUT 72h.
todos:
  - id: cdc-complet
    content: Rédiger docs/CDC_DigiScore-WA_complet.md (membre préalable, intégration SI, perf, ressources, IN/OUT 72h)
    status: completed
  - id: schema-member-first
    content: Schéma SQL membre-centrique + tables_liaison digiscore_* (ADD-only, FK logique vers IDs métier)
    status: pending
  - id: seeds-riches
    content: Seeds métier 8–12 profils + jeu perf volumétrique (index, EXPLAIN, pagination) simulant échelle 1M+
    status: pending
  - id: scoring-plafond
    content: SPEC moteur score + eligibility + montant_eligible + messages métier type télécom
    status: pending
  - id: arch-skeleton
    content: "Monorepo : docker-compose, stubs FastAPI + scoring + React PWA (parcours membre → demande)"
    status: pending
  - id: contracts
    content: OpenAPI stub + contrats dossier + mapping champs SI (pilote API/gateway)
    status: pending
  - id: readme-sync
    content: README stack, cas démo, ressources min/recommandées, plan H0–H72
    status: pending
  - id: guide-equipe
    content: docs/GUIDE_EQUIPE.md — monorepo, ports, rôles, intégration, guide modèle
    status: pending
  - id: arch-integration-si
    content: Documenter archi sidecar / topologies agences / ADD-only / anti-greffe dans CDC+architecture.md
    status: pending
  - id: workflow-roles
    content: Spec + écrans/API circuit Agent → Chef d’agence → CIC (files, avis, audit, routage par zone)
    status: pending
  - id: innovation-pitch
    content: Section CDC + slide pitch « différenciation » (plafond télécom + membre + 3 niveaux + sidecar)
    status: completed
isProject: false
---

# DigiScore-WA — Architecture, plan de travail et CDC complet

## Précision terrain (hackathon) — idée à bien comprendre

Les responsables ont clarifié le modèle réel des SFD (ex. FUCEC) :

1. **Pas de demande de crédit « orpheline »** : tout demandeur **doit déjà avoir un compte membre** dans l’institution (épargne / compte d’opérations), quel que soit le type de crédit.
2. Le score ne se calcule **pas seulement** sur le formulaire de demande du jour, mais surtout sur le **profil + comportement historique dans l’institution** (épargne, anciens crédits, retards, discipline de remboursement, ancienneté, mouvements).
3. Analogie voulue : **crédit d’appel / crédit mobile** (syntaxes opérateurs Togo) — le système regarde la consommation / l’historique, puis :
   - accepte avec un **montant plafonné** ;
   - ou refuse avec un **message explicite** (« montant de consommation inférieur à X », « historique insuffisant », etc.).
4. Au-delà du oui/non, le modèle doit **proposer un montant éligible** (souvent ≤ demande ; parfois **suggestion d’augmentation** si le profil est très solide — rare pour les gros tickets type 10 M FCFA, mais possible).
5. Conséquence produit : la **BDD + seeds + parcours UI** doivent simuler une vraie microfinance (membres, comptes, historique riche), pas un formulaire isolé.
6. **Nouveau parcours « sans historique interne »** (précision terrain) : certains demandeurs n’ont pas encore de compte / pas d’historique dans l’institution → ouverture de compte, puis questionnaire sur crédits **ailleurs** + dépôt de pièces (relevés, carnets…). DigiScore digitalise upload + contrôle qualité photo + extraction (OCR) ; **refus catégorique** si les preuves exigibles ne sont pas fournies.

**Positionnement DigiScore-WA (reformulé)** : copilote d’éligibilité et de **plafond de crédit** pour les **institutions membres de la CIF** (FUCEC = échantillon d’existant, pas la seule cible) — logique « crédit télécom » + historique interne **ou** preuves d’historique externe, décision humaine Agent → Chef d’agence → CIC.


```mermaid
flowchart TD
  Member[Compte_membre_existant] --> Hist[Historique_institution]
  Member --> Demande[Formulaire_demande]
  Hist --> Engine[Moteur_score_et_plafond]
  Demande --> Engine
  Engine --> Out["Eligibilite + score/100 + montant_eligible + message"]
  Out --> Agent[Agent_credit]
  Agent --> Chef[Chef_agence]
  Chef --> CIC[CIC_comite]
```

---

## Contexte retenu (sources)

- Docs [`resoure/`](resoure/) : briefing CIF, CDC consolidé, existant FUCEC, formation, critique jury.
- **MVP 72h** : M1→M5 fonctionnels ; M6/M7 maquettes.
- **Score** : 6 critères /100 (CDC consolidé), avec **poids réel de l’historique institutionnel** renforcé côté données et moteur de plafond.
- Contraintes CIF : Android/Windows, mode dégradé, données synthétiques, git+README, démo live ; gel J3 14h.
- Repo : pas de code encore.

**Stack figée** :

| Couche | Choix |
|--------|--------|
| Frontend | React + Vite + TypeScript (PWA) |
| Backend | FastAPI (Python) |
| Moteur | Package Python règles (score + plafond + messages) — pas de ML |
| BDD | PostgreSQL + Docker Compose |
| Démo | `docker compose up` + README |

---

## Architecture technique

```mermaid
flowchart LR
  Agent[Agent_credit] --> PWA[React_PWA]
  PWA -->|lookup_membre| API[FastAPI]
  PWA -->|demande_credit| API
  API --> Engine[Scoring_and_Limit_Engine]
  API --> DB[(PostgreSQL)]
  Engine --> DB
  API --> Memo[Memo_Fiche_Comite]
  Memo --> Committee[Comite_credit]
  API --> Audit[journal_audit]
```

### Précisions terrain SI / réseau (hackathon) — contraintes d’intégration

Les responsables ont précisé le paysage réel des agences. DigiScore doit être conçu **dès le MVP** pour coller à ces règles (même si en 72h on tourne en autonome sur Postgres synthétique).

#### 1. Topologies de bases (hétérogènes)

- **Certaines agences** : **une base unique** partagée (plusieurs points de vente → même SGBD).
- **D’autres** : **bases divisées** (par agence / région) avec un mécanisme de synchro ou d’échange entre elles.
- Conséquence produit : DigiScore ne suppose **pas** « une seule BDD nationale ». Le modèle de données porte un `agence_id` / `tenant_local` ; en pilote l’adaptateur d’intégration gère **base centrale** vs **base locale + agrégation**.

#### 2. Interdiction absolue : greffe sur le système transactionnel

- Si la solution exigeait de **modifier le cœur transactionnel** (écritures métier, triggers sur tables partenaires, changer le flux de transaction) → **non faisable**.
- DigiScore = application **à côté** (**sidecar / satelitte**), en lecture via API/vues autorisées + **écriture uniquement dans nos objets**.

```mermaid
flowchart TB
  subgraph interdit [Interdit]
    TxCore[Systeme_transactionnel_partenaire]
  end
  subgraph autorise [Autorise_pilote]
    APIGw[Passerelles_APIs_agence]
    Liaison[Tables_digiscore_ADD_only]
    Digi[DigiScore_backend]
  end
  Digi -->|lecture_mappee| APIGw
  Digi -->|INSERT_UPDATE| Liaison
  APIGw -.->|lecture_seule| TxCore
  Liaison -.->|FK_logique_ids| TxCore
```

#### 3. Pilote : passerelles / APIs + mapping de champs

- Quand la solution est déployée, **certaines agences** peuvent mettre à disposition des **passerelles / APIs**.
- Notre backend communique alors avec leurs bases **via ces APIs** (ou exports), avec un **mapping de champs** explicite (ex. leur `NUM_CLIENT` → notre `membre.code_externe`).
- En 72h : couche `adapters/` **stubbée** (lit Postgres local) ; contrat de mapping documenté pour le jury / le pilote.

#### 4. Tables : ADD only, jamais ALTER/DELETE du existant

- Le SI actuel est développé par un **partenaire** : l’institution **ne peut pas modifier ni supprimer** leurs objets.
- **Autorisé** : **créer / ajouter** d’autres tables (ex. `digiscore_demande`, `digiscore_score_resultat`, `digiscore_decision`, `digiscore_audit`, tables de liaison `digiscore_membre_map`).
- Règle de conception schéma :
  - Préfixe `digiscore_` pour tout objet à nous.
  - Références vers le SI existant = **IDs métier stockés** (pas de FK physique obligatoire vers tables partenaires si interdite).
  - Zéro script qui fasse `ALTER` / `DROP` sur le schéma tiers.

#### 5. Performance : > 1 million de clients

- Les requêtes vers la BDD doivent être **optimisées** (index, pas de `SELECT *` sur historiques, pagination, agrégats précalculés si besoin).
- En hackathon : seeds métier riches (8–12 profils) **+** un jeu / script de **charge volumétrique** (ex. 50k–100k membres synthétiques ou au minimum preuve d’index + `EXPLAIN` sur lookup membre / historique) pour démontrer qu’on a pensé l’échelle 1M+.
- Patterns obligatoires dès le backend MVP :
  - Lookup membre par **n° compte / code indexé**, jamais scan full table.
  - Historique : dernières N opérations / crédits (LIMIT) + agrégats (solde moyen) plutôt que tout charger.
  - Éviter N+1 ORM ; endpoints paginés.

#### 6. Ressources requises (à spécifier dans CDC + README)

Ordres de grandeur pour faire tourner DigiScore (à affiner au pitch, déjà chiffrés dans la doc) :

**A. Démo hackathon (laptop / petit serveur)**

| Ressource | Minimum | Recommandé |
|-----------|---------|------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 Go | 8 Go |
| Disque | 10 Go (images Docker + DB) | 20 Go |
| OS | Windows 10+ ou Linux ; Android pour consultation PWA | — |
| Logiciel | Docker Desktop / Engine, navigateur Chrome/Edge | — |
| Réseau démo | Localhost ; mode dégradé PWA si faible connectivité | — |

**B. Phase pilote (1 COOPEC / agence, ~lecture API + nos tables)**

| Ressource | Minimum | Recommandé |
|-----------|---------|------------|
| CPU | 4 vCPU | 8 vCPU |
| RAM | 8 Go | 16 Go |
| Disque | 50 Go SSD | 100 Go+ SSD (logs + scores + audit) |
| Postgres | 1 instance dédiée DigiScore **ou** schéma/tables `digiscore_*` sur instance autorisée | Séparer si possible du OLTP critique |
| App | 1 VM/container backend + reverse proxy (nginx) | 2 instances backend derrière LB si besoin |
| Accès SI | Compte API lecture + droit **CREATE TABLE** (pas ALTER tiers) | Mapping champs validé avec DSI |
| Réseau | Lien stable agence ↔ serveur ; timeout/retry documentés | Cache lecture membre côté DigiScore |

**C. Ce qu’on ne demande pas** : modifier le moteur transactionnel, droits DROP/ALTER sur tables partenaires, GPU, cluster Kubernetes dès le pilote.

---

### Parcours métier MVP (UI) + workflows acteurs

#### Les 3 rôles (figés pour produit + démo)

| Rôle | Qui | Ce qu’il fait dans DigiScore |
|------|-----|------------------------------|
| **Agent de crédit** | Accueil du demandeur | Vérifie le **membre**, questionne, remplit le formulaire (A–E / N1–N3), lance l’analyse, **génère score + plafond + message**, constitue le mémo, soumet le dossier |
| **Chef d’agence** | 1er niveau de validation | Reçoit la file des dossiers soumis, **analyse** le score/explications/plafond, **valide / refuse / renvoie** à l’agent (motif obligatoire si écart à la reco) |
| **CIC** (comité d’octroi / crédit) | Dernier niveau | Décision finale **accorder / conditionner / refuser** ; obligatoire en zone grise, voie exceptionnelle (gros montant), ou si le chef escalade |

```mermaid
stateDiagram-v2
  [*] --> SaisieAgent: membre_ok
  SaisieAgent --> ScoreGenere: agent_analyse
  ScoreGenere --> FileChef: agent_soumet
  FileChef --> RenvoiAgent: chef_renvoie
  RenvoiAgent --> SaisieAgent
  FileChef --> DecideChef: chef_valide_ou_refuse
  FileChef --> FileCIC: chef_escalade_ou_regle_auto
  DecideChef --> FileCIC: si_regle_exige_CIC
  DecideChef --> Clos: si_delegation_autorisee
  FileCIC --> Clos: decision_CIC
```

#### Routage selon le score (règles MVP)

| Zone / cas | Après l’agent | Chef d’agence | CIC |
|------------|---------------|---------------|-----|
| Score **&lt; 40** ou knockout | Soumet avec reco rejet | Peut confirmer rejet **ou** override motivé → escalade CIC | Décision si override / recours |
| Score **41–70** (gris) | Soumet | Analyse + avis ; **passage CIC obligatoire** | Décision finale |
| Score **&gt; 70** et montant ≤ éligible et non exceptionnel | Soumet | **Validation simplifiée** possible (toujours humaine) | CIC si politique agence l’exige ou montant élevé |
| **Voie exceptionnelle** (~8–10 M+) | Soumet | Ne peut pas clôturer seul | **CIC obligatoire** + conditions/garanties |
| Thin-file / plafond | Message clair à l’agent | Contrôle du micro-plafond | Si dérogation demandée |

**Invariant** : le système **ne décide jamais seul**. Chaque avis (agent / chef / CIC) est horodaté dans `digiscore_decision` + `digiscore_audit` (qui, quoi, motif si ≠ reco).

#### Écrans UI par rôle (MVP)

1. **Agent** : lookup membre → fiche historique → wizard demande → résultat score/plafond → mémo → bouton « Soumettre au chef »
2. **Chef** : file « à valider » → détail score + explications → Valider / Refuser / Renvoyer / Envoyer CIC
3. **CIC** : file comité → fiche synthèse 1 page → Accorder / Conditionner / Refuser (+ PV simplifié)

Login démo : 3 comptes (`agent`, `chef`, `cic`) suffisent pour le pitch.

---

### Parcours « sans historique interne » + preuves externes (innovation terrain)

Précision des responsables : certains demandeurs veulent un crédit **sans historique dans l’institution** (souvent pas encore de compte).

**Tunnel métier (à digitaliser)**

1. **Devenir membre** : ouverture de compte obligatoire (toujours).
2. Questionnaire : « Avez-vous déjà eu des crédits / prêts dans une autre banque, SFD ou IMF ? »
3. Si **oui** → apporter les preuves papier (photocopies) ; l’agent photographie / téléverse dans DigiScore.
4. DigiScore : **contrôle qualité image** (flou, trop sombre, coin coupé) → si mauvais, demander de recommencer ; puis **extraction OCR** des montants / échéances / retards pour nourrir le score (critère Historique + anomalies).
5. Si les preuves **exigibles ne sont pas fournies** → **refus catégorique** (pas d’analyse « au feeling »).
6. Si **jamais de crédit nulle part** (vrai primo-emprunteur) → pas le même refus « documents manquants » : parcours **first-time** (micro-plafond, garanties renforcées, CIC) — à confirmer avec les mentors, distinct du cas « a eu des crédits ailleurs mais n’apporte rien ».

**Noms de pièces usuels (UEMOA / SFD — à afficher dans l’UI)**

| Document | Usage |
|----------|--------|
| **Relevé de compte** bancaire ou SFD (souvent 3 à 6 mois) | Voir mouvements, discipline, soldes |
| **Carnet / livret d’épargne** (COOPEC / SFD) | Historique épargne papier très courant en microfinance |
| **Échéancier / tableau d’amortissement** d’un crédit antérieur | Voir si les échéances étaient tenues |
| **Attestation de solde** ou de clôture de crédit | Preuve de fin de prêt |
| **Rapport de crédit / solvabilité BIC** (si disponible + consentement) | Endettement ailleurs (Bureau d’Information sur le Crédit — BCEAO) |
| Pièces support : **CNI**, justificatif d’activité | Identité / activité |

**Scope 72 h réaliste pour cette innovation**

- **IN** : UI questionnaire + upload multi-fichiers + contrôle qualité photo (flou/luminosité) + stockage + saisie assistée / OCR démo sur images nettes synthétiques + refus si pièces manquantes.
- **OUT / pilote** : OCR production robuste sur tous formats de carnets sales, connecteur BIC live.

C’est un axe d’**innovation fort** au pitch : on ne refuse plus bêtement « pas d’historique ici » ; on **ouvre une voie de preuve externe**, avec garde-fou documentaire strict.

---

### Preuve d’intégrabilité SI (réponse jury / innovation déploiement)

**Question typique** : « Qu’est-ce qui prouve que DigiScore s’adaptera facilement à nos bases / architectures en phase pilote ? »

**Réponse structurée (3 preuves + quand on le fait)**

| Preuve | Ce qu’on a conçu / on livre | Étape exacte |
|--------|-----------------------------|--------------|
| **1. Architecture sidecar (non invasive)** | DigiScore tourne **à côté** du SI : lecture via API/passerelle ; **aucune greffe** sur le cœur transactionnel ; **aucun ALTER/DROP** des tables partenaires | **Conception H0** (déjà dans CDC/archi) → respecté tout le long du dev |
| **2. Contrat de mapping de champs** | Table de correspondance explicite : ex. leur `NUM_CLIENT` / `CODE_MEMBRE` → notre `membre.code_externe` ; soldes, crédits, incidents mappés champ à champ | **Conception H0–H8** (SPEC + `docs/mapping_si.md`) ; **pilote** = brancher l’adaptateur réel |
| **3. Couche `adapters/` interchangeable** | En hackathon : adapter **stub** lit Postgres synthétique. En pilote : on **swap** l’adapter (API agence / export) **sans réécrire** le moteur de score ni le front | **Dev MVP** : interface + stub ; **pilote semaine 1** : adapter réel |
| **4. Tables `digiscore_*` ADD-only** | Nos objets (demande, score, décision, audit, map membre) créés **en plus** ; FK logique par IDs métier stockés | **Schéma BDD dès H0** ; déploiement pilote = scripts `CREATE TABLE digiscore_%` seulement |
| **5. Multi-topologie prévue** | `agence_id` + pas d’hypothèse « une seule BDD nationale » (base partagée **ou** bases divisées) | **Modèle de données H0** |
| **6. Perf pensée dès le schéma** | Index lookup n° compte, historiques paginés — prêt pour >1 M clients | **Schéma + seeds/EXPLAIN en MVP** |

**Ce qu’on intègre à quelle étape**

```text
CONCEPTION (maintenant / H0)
  → sidecar figé
  → schéma digiscore_* + code_externe
  → mapping champs documenté
  → interface AdapterHistorique

DEV HACKATHON (72 h)
  → AdapterStub (données synthétiques)
  → API métier stable (mêmes endpoints qu’en pilote)
  → UI upload preuves externes (parcours sans hist. interne)

PILOTE (après sélection)
  → AdapterApiAgence / export fichier
  → CREATE tables digiscore_* sur instance autorisée
  → mapping validé avec DSI (atelier 1–2 jours)
  → pas de refonte du scoring
```

**Phrase pitch (20 s)** :  
« On n’attend pas le pilote pour être intégrable : dès la conception, DigiScore est un **sidecar** avec **mapping de champs**, tables **digiscore_ en ajout seul**, et une couche **adapter** qu’on branche sur vos APIs sans toucher au transactionnel ni au moteur de score. Le hackathon prouve le métier ; le pilote ne fait que remplacer le stub de données. »

---

### Différenciation / innovation — réponse à l’encadreur

**Ce que la plupart des autres groupes vont probablement proposer** : un formulaire de demande → un score 0–100 (ou classes A–E) → oui/non, parfois avec un peu de « ML » générique, souvent **sans** ancrage fort sur le compte membre ni sur le plafond, et peu de workflow réel Chef/CIC.

**Notre plus-value distinctive (à marteler)** — une innovation **métier + produit**, pas un gadget tech :

1. **Moteur d’éligibilité type crédit télécom SFD** (cœur de différenciation)  
   Pas seulement un score : à partir du **comportement institutionnel** (épargne, mouvements, crédits passés), DigiScore sort **éligible / non**, un **montant plafonné**, et un **message explicite** (« historique insuffisant », « demande &gt; plafond : X proposés », etc.). C’est l’équivalent du crédit d’appel mobile, adapté à la microfinance — rare chez les équipes qui ne font qu’un scorecard.

2. **Membre préalable + historique institutionnel comme source de vérité**  
   Pas de dossier orphelin : pas de compte = pas de crédit. Le formulaire du jour **complète** l’historique, il ne le remplace pas. Aligné sur la réalité FUCEC / SFD (les autres réinventent souvent un formulaire isolé).

3. **Copilote à 3 niveaux (Agent → Chef d’agence → CIC) avec audit**  
   Routage automatique de la file selon la zone de score, override motivé, jamais de robot d’octroi. Ça parle directement au jury institutionnel (gouvernance, BCEAO).

4. **Ancré FUCEC mais lisible comité** : 6 critères /100 mappés sur le scorecard 275 pts existant (CAF, RCSD, N1–N3) — digitalisation de **leur** méthode, pas une boîte noire importée.

5. **Déployable chez eux** : architecture **sidecar** (pas de greffe transactionnelle), tables `digiscore_*` en **ADD-only**, APIs/passerelles en pilote — alors que beaucoup proposeront une appli qui « remplace » le SI (irréaliste).

**Phrase courte pour l’encadreur / le pitch** :  
« Notre innovation n’est pas un algorithme magique : c’est un **copilote d’éligibilité et de plafond**, calqué sur la logique du crédit mobile, nourri par l’historique du membre dans la COOPEC, et branché sur la vraie chaîne **Agent → Chef d’agence → CIC**, sans toucher au système transactionnel. »

**Ce qu’on ne vend pas comme innovation** : « on a mis de l’IA » sans données réelles ; un score /100 seul (banal) ; remplacer le comité.

---

### Monorepo

```
digiscore_wa/
  docs/CDC_DigiScore-WA_complet.md
  backend/
  scoring/          # score + plafond + messages + thin-file
  frontend/
  data/synthetic/   # membres + historiques + demandes
  docker-compose.yml
  README.md
```

### Contrats

- OpenAPI = Front ↔ Back.
- `schema.sql` = Data ↔ Back.
- `scoring/SPEC.md` + tests golden : entrée = `{membre, historique, demande, analyse_financiere}` ; sortie = `{eligible, score_global, criteres[], knockouts[], montant_demande, montant_eligible, montant_max_institution, message_code, message_humain, explication[], thin_file}`.

---

## Moteur de décision enrichi (score + plafond)

### Pipeline (ordre fixe)

1. Garde-fou membre / compte actif (ou parcours ouverture + preuves externes).
2. Contrôles **BIC / fiscalité** + pièces associées.
3. Profil historique interne (+ OCR preuves externes si besoin) ; thin-file si applicable.
4. Si `montant_demande ≥ seuil_caution` → **parcours cautionnaire(s)** (capacité de relais).
5. Collecte terrain A–E + N1/N2/N3.
6. **Calculs financiers détaillés** (sections A–E ci-dessous).
7. Notation 6 critères /100.
8. Knock-outs.
9. Moteur de plafond + messages.
10. Mémo + circuit Agent → Chef → CIC + audit.

---

### Formules et calculs détaillés (formation SFD / échantillon FUCEC)

Référence unique pour `scoring/financials.py` — issues des supports analyse financière / décision + CDC consolidé.

#### A. Agrégats de base

| Symbole | Formule / définition |
|---------|----------------------|
| EBE | `CA − CMV − Charges_exploitation` (avant charges financières) |
| Surplus_Deficit_personnel | `Revenus_perso − Charges_familiales` (dossier sans budget familial = incomplet) |
| Service_total_dette | `Dettes_en_cours + Service_credit_sollicite` (capital+intérêts période) |

#### B. CAF et RCSD (cœur capacité)

```text
CAF  = EBE + Produits_financiers + Surplus_Deficit_personnel
RCSD = CAF / Service_total_dette
```

| Règle | Valeur |
|-------|--------|
| Norme confort | RCSD **≥ 1,50 (150 %)** |
| Knock-out | RCSD **&lt; 1,00** → bloque reco automatique |
| Limites à afficher | projections déclaratives ; masque les creux mensuels ; ≠ volonté de payer |

#### C. Les 6 ratios

| Ratio | Formule | Seuil indicatif |
|-------|---------|-----------------|
| Marge brute | `(Marge_brute / CA) × 100` | Sectoriel |
| BN / CA | `(Resultat_net / CA) × 100` | Sectoriel |
| Solvabilité | `Fonds_propres / Total_dettes` | **&gt; 1** |
| Rotation stocks | `(Stock_moyen × 365) / CAMV` | Sectoriel (jours) |
| Participation | `(FP_consolidés / Actif_total) × 100` | **&gt; 35 %** |
| Fonds de roulement | `Actif_circulant / Passif_circulant` | **&gt; 150 %** |

Arbitrage : RCSD = juge de paix capacité ; ratios = conditions. **2–3 ratios dégradés ensemble** → suspendre reco auto → revue Chef/CIC.

#### D. Trésorerie 12 mois

```text
Solde_mensuel(m) = Flux_entrant(m) − Flux_sortant(m)
Solde_cumule(m)  = Solde_cumule(m-1) + Solde_mensuel(m)
```

Objectif : cumul **≥ 0 chaque mois**. Interdit : lisser le CA annuel en 12 parts égales. Mois critique = premier cumul &lt; 0.

#### E. Patrimoine + 5 signaux

```text
Situation_nette = Actifs_totaux − Passifs_totaux   (> 0)
```

Signaux (2–3 simultanés → analyse approfondie même si RCSD OK) : érosion CA ; marge qui baisse ; créances clients qui explosent ; dettes fournisseurs en hausse ; situation nette en déclin. Tests cohérence patrimoine ↔ bénéfices déclarés.

#### F. Score /100

> **Décision encadreurs** : score sur **100** (pas 1000) — plus simple à expliquer aux agents et au CIC ; seuils **40 / 70** (équivalents des anciens 400 / 700).

Note `n_i` sur 0–100 par critère, puis :

```text
score = Σ (n_i/100) × poids_i × 100
poids: financier 25% | capacité 20% | historique 20% | activité 15% | garanties(+cautions) 10% | documents(+BIC/fiscal) 10%
```

Zones : 0–40 rejet reco · 41–70 analyse/CIC · 71–100 approbation reco. Mapping pédagogique du scorecard 275 pts (A160/B55/C50/D10).

#### G. Knock-outs

RCSD &lt; 1 · ESG · incohérence critique · incidents graves / compte gelé · **BIC/fiscal exigible non conforme** · **seuil caution sans cautionnaire éligible**.

#### H. BIC, fiscalité, cautionnaires (ajout terrain)

**BIC + « en règle » fiscale**

- Consentement BIC tracé ; rapport/extrait (endettement ailleurs) — seed en 72h, API en pilote.
- Pièces types : rapport BIC, **quittance / attestation fiscale**, patente selon pays, relevés, carnets…
- `situation_fiscale` : `en_regle | a_verifier | non_conforme | non_fourni`.
- Absences exigibles → knockout documentaire / refus soumission.

**Cautionnaires (montant ≥ seuil produit)**

- `seuil_montant_caution` + `nb_cautions_min` sur le produit.
- Chaque cautionnaire est **évalué** (revenus, charges, CAF/RCSD de relais, hist. s’il est membre) : peut-il **payer les échéances** si le principal ne peut plus ?
- Alimente le critère Garanties (10 %) ; sinon message `CAUTION_REQUISE` / blocage.

#### I. Plafond

```text
montant_eligible = min(plafond_produit, f(épargne, CAF, RCSD, score, hist, garanties+cautions), capacité_échéance)
```

Messages : `MONTANT_OK`, `MONTANT_PLAFONNE`, `UPSELL_POSSIBLE`, `VOIE_EXCEPTIONNELLE`, `CAUTION_REQUISE`, `BIC_OU_FISCAL_MANQUANT`, etc.

SYSCOFOP / tontine : hors score de base MVP (bonus pilote).

---

## Schéma BDD membre-centrique (priorité absolue)

### Cœur institutionnel

- `agence`, `produit_credit` (+ `seuil_montant_caution`, `nb_cautions_min`, plafonds, flag exceptionnel)
- `membre`, `compte`, `mouvement_compte`, `epargne_snapshot`, `credit_passe`, `incident`
- `garantie_membre` (garanties matérielles)

### BIC / fiscalité / pièces

- `consentement_bic` (membre, date, scan, statut)
- `rapport_bic` (endettement résumé, incidents, source simulate|api)
- `piece_justificative` (type `BIC|FISCAL|RELEVE|CARNET|ECHEANCIER|ATTESTATION_SOLDE|CNI|AUTRE`, fichier, qualite_ocr, validation)
- `situation_fiscale` sur demande ou pièce

### Cautionnaires (évaluation de relais)

- `cautionnaire` (identité, lien, `membre_id` nullable)
- `demande_caution` (demande, cautionnaire, type simple|solidaire, montant engagé)
- `evaluation_cautionnaire` (revenus, charges, caf_relais, rcsd_relais, score_relais, eligible, motif)

### Demande & scoring & décision

- `demande_credit` (+ flag généré `seuil_caution_atteint`)
- collecte A–E : menage, activite, modele_economique, marche, revenu_charge, patrimoine, tresorerie_mensuelle, garantie_demande, N1/N2/N3
- `ratio_financier` (EBE, CAF, RCSD, 6 ratios, alertes)
- `score_resultat`, `tableau_amortissement`
- `decision` (agent|chef_agence|cic), `journal_audit`, `utilisateur`
- pilote ADD-only : `digiscore_*` (demande, score, decision, audit, membre_map)

### Vision

- `suivi_portefeuille`, `par_indicateur`, `recouvrement`

**Invariants** : membre+compte avant demande ; si montant ≥ seuil caution → cautions éligibles requises ; pièces BIC/fiscal selon politique produit.

---

## Seeds riches — simuler « à fond »

Objectif : **8–12 membres** synthétiques + demandes associées.

| # | Profil | Ce que ça prouve |
|---|--------|------------------|
| 1 | Bon payeur, épargne régulière | Score haut, MONTANT_OK |
| 2 | Demande &gt; plafond | MONTANT_PLAFONNE |
| 3 | Incidents récents | Refus / plafond bas |
| 4 | Thin-file | Historique insuffisant |
| 5 | Ancien sans crédit, épargne OK | Micro-éligibilité |
| 6 | Agricole saisonnier | Creux trésorerie |
| 7 | Zone grise 41–70 | CIC |
| 8 | RCSD &lt; 1 | Knock-out |
| 9 | Gros montant + **cautions** | Voie exceptionnelle + eval cautionnaires |
| 10 | Compte gelé / non membre | Garde-fou |
| 11 | Override motivé | Audit |
| 12 | Preuves externes + **BIC/fiscal** OK vs manquant | Upload / refus pièces |

Chaque seed : montants attendus + `message_code` (tests golden). Complément perf : volumétrie + index + EXPLAIN.

---

## Périmètre IN / OUT 72h

**IN**

- Parcours **membre obligatoire** → fiche historique → demande → score + **plafond** + messages
- M1–M5 (collecte, calculs, scoring, mémo, décision/amortissement sur montant retenu)
- Gestion thin-file + non-membre + plafonnement + voie exceptionnelle (règles)
- Seeds 8–12 profils nourris
- Mode dégradé minimal PWA
- README + docker-compose + démo live

**OUT — détail de chaque point (ce que ça voudrait dire en vrai)**

Ces items sont **volontairement hors MVP 72h** : trop longs, trop dépendants de SI tiers / données réelles / conformité. On les **explique au jury** comme roadmap pilote ; pour M6/M7 on montre des **maquettes** (écrans + données seed), pas un moteur live.

### 1. Vrai core banking / BIC / YAS-Flooz / SYSCOFOP live

Quatre **connecteurs vers des systèmes externes** de l’institution (ou partenaires). « Live » = brancher en temps réel sur les vrais systèmes, pas simuler en base locale.

| Élément | C’est quoi ? | Ce qu’on ferait en pilote | Ce qu’on fait en 72h à la place |
|---------|--------------|---------------------------|--------------------------------|
| **Core banking** | SI cœur (comptes, soldes, crédits production). | **Jamais greffé** sur le transactionnel. Lecture via **API/passerelle** + mapping ; écritures DigiScore dans tables `digiscore_*` (ADD-only). | Postgres autonome + adapters stub. |
| **BIC** | **Bureau d’Information sur le Crédit** / centrale des risques (endettement ailleurs, impayés déclarés au niveau national/régional). | Appel API (ou fichier) BIC avant scoring : détecter crédits cachés hors FUCEC. | Champ / flag `source_bic` **simulé** dans les seeds (incident « vu à la BIC » inventé). |
| **YAS / Flooz** | Mobile money Togo (Moov/Yas, Flooz/TMoney etc.) : historique de cash-in/cash-out du membre. | Consentement + API opérateur : enrichir capacité/comportement (flux réels), pas seulement déclarations. | Hors scope ; éventuellement un champ « revenu mobile money déclaré » dans le formulaire, **sans** API. |
| **SYSCOFOP live** | Système de **tontine / épargne digitalisée de groupe** FUCEC : assiduité, cotisations, caution solidaire. | Brancher l’indice « capital social de groupe » sur les vraies données tontine. | Module **hors score de base** ; seed optionnel minimal, pas de connexion SYSCOFOP. |

En résumé : OUT = **intégrations production** ; IN = **même logique métier**, nourrie par des **données fake** bien structurées.

### 2. ML sur historique réel

| | |
|--|--|
| **C’est quoi ?** | Remplacer (ou compléter) les **règles + pondérations fixes** par un modèle d’**apprentissage automatique** (régression, gradient boosting, etc.) entraîné sur des **milliers de dossiers réels** passés (qui a remboursé / qui est passé en PAR). |
| **Pourquoi OUT ?** | Interdit / impossible en hackathon CIF : **aucune donnée personnelle réelle** ; pas de volume ; risque « boîte noire » face au jury FUCEC/BCEAO ; calibration et biais = semaines de travail. |
| **Ce qu’on livre quand même** | Moteur **explicable** (règles, 6 critères, messages). Au pitch on peut dire : « en pilote, les pondérations pourront être **recalibrées** sur l’historique institutionnel (scoring adaptatif), voire un modèle supervisé **auditable**. » |
| **Ce que ce n’est pas** | Ce n’est pas « un peu d’IA dans le slide » : c’est un chantier data science + gouvernance modèle + validation prudentielle. |

### 3. M6 / M7 temps réel → maquettes

| Module | Rôle métier (rappel FUCEC) | « Temps réel » voudrait dire | « Maquette » en 72h |
|--------|----------------------------|------------------------------|---------------------|
| **M6 Suivi portefeuille** | Après décaissement : échéances du jour, visites V1/V2/V3, **12 signaux** d’alerte, calcul **PAR 30 / PAR 90**. | Cron/jobs qui recalculent retards chaque jour, alertes push agent, tableau de bord agence branché sur crédits **octroyés**. | 1–2 **écrans UI** avec chiffres **pré-chargés** (seed) : on *montre* la vision produit, sans moteur qui met à jour le PAR à chaque paiement. |
| **M7 Recouvrement** | 4 niveaux (relance → contentieux), priorisation des dossiers en retard, journal d’actions, rôles gradués. | Workflow live : changer de niveau, assigner superviseur, tracer actions, lier au PAR. | **Matrice / liste** visuelle + données d’exemple ; pas de moteur d’escalade automatique branché. |

Pourquoi découper ainsi : le jury veut voir que le **cycle ne s’arrête pas à l’octroi** ; 72h ne suffisent pas à un vrai moteur post-décaissement de qualité. D’où : **cœur M1–M5 fonctionnel** + **M6/M7 en maquette assumée**.

### 4. Multi-tenant / SSO / i18n ewé complète

Trois sujets **infra / produit entreprise**, pas nécessaires pour une démo mono-institution.

| Terme | C’est quoi ? | Pourquoi OUT 72h | Ce qu’on fait à minima |
|-------|--------------|------------------|------------------------|
| **Multi-tenant** | Une seule appli qui sert **plusieurs** COOPEC / SFD isolées (données cloisonnées, params de score par institution, logos, plafonds différents). | Modèle de données + auth + isolation = chantier large. Le hackathon cible **un** proto type FUCEC. | Une base, une institution fictive « COOPEC démo » ; params de score dans config/SPEC (préparer le jour où ce sera multi). |
| **SSO** | **Single Sign-On** : l’agent se connecte avec le compte institutionnel existant (Active Directory, Keycloak, Microsoft, etc.), pas un login DigiScore isolé. | Intégration IdP + sécurité + comptes réels. | Soit pas d’auth, soit login démo simple (`agent` / `responsable`) pour enchaîner les écrans. |
| **i18n ewé complète** | **Internationalisation** : toute l’UI traduite en **éwé** (langue locale Togo), pas seulement le français — menus, erreurs, mémo, messages télécom. | Traduction pro + relecture métier = long ; le jury CIF est surtout FR. | UI en **français** ; si temps : 2–3 labels clés bilingues (wow factor), pas une i18n complète. |

---

**Phrase utile au pitch** : « DigiScore ne touche pas au système transactionnel du partenaire : on lit via les APIs/passerelles quand elles existent, on n’ajoute que nos tables de liaison, et le moteur d’octroi tourne à côté — calibré pour des portefeuilles à l’échelle du million de membres. »

---

## Organisation synchrone — 4 flux

| Rôle | Focus mis à jour |
|------|------------------|
| **Data** | Schéma membre-centrique + seeds 8–12 + fixtures golden |
| **Scoring** | Score 6 critères + **limit engine** + thin-file + messages |
| **Backend** | Lookup membre, agrégation historique, API demande/score |
| **Frontend** | Parcours **3 rôles** (agent / chef / CIC), bandeau historique, écran résultat type télécom, files de validation |


Rituels : gel contrats H0 (schéma + SPEC plafond + OpenAPI) ; sync 4 h ; merge si tests scoring verts.

---

## Plan de travail A→Z

| Bloc | Focus | Done quand |
|------|--------|------------|
| H0–H8 | Schéma membre + seeds riches + SPEC score/plafond | Compose up ; lookup membre OK |
| H8–H24 | UI membre + demande M1 + calculs M2 | Historique visible ; ratios OK |
| H24–H40 | M3 score + plafond + messages | Cas seed 1–10 verts |
| H40–H52 | M4–M5 mémo/décision/amortissement | Override + gros montant exceptionnel |
| H52–H60 | Maquettes M6/M7 | Vision portefeuille |
| H60–gel | E2E scénarios télécom + pitch | Démo 3 cas contrastés sans crash |

Scénario pitch recommandé : (A) agent → bon payeur plafonné → chef valide ; (B) thin-file → message + chef ; (C) gros montant → **CIC** voie exceptionnelle. Montrer les **3 rôles** (login) en 2–3 minutes.

---

## CDC complet à régénérer

Enrichir le CDC consolidé avec **membre préalable & plafond télécom** + **intégration SI non invasive** :

1–4. Contexte, existant FUCEC, objectifs, 9 composantes  
5. Scoring 6 critères **+** eligibility/plafond/messages/thin-file  
5bis. **Workflows Agent → Chef d’agence → CIC** + routage par zone de score  
5ter. **Différenciation / innovation** (plafond télécom + historique membre + sidecar + gouvernance 3 niveaux)  
6. Architecture membre-first + **sidecar SI**  
7. Modèle de données + mapping pilote + **perf 1M+** + seeds  
8. Spec M1–M7 (écrans par rôle)  
9. IN/OUT 72h  
10. NFR + **fiches ressources**  
11–13. Plan, impact, réponses jury  
Annexes : crédit mobile ; cas seeds ; mapping SI

---

## Guide monorepo — qui travaille où, comment on se branche

Objectif : **un seul repo git** (`digiscore_wa`), chacun dans son dossier, **contrats figés**, services qui se parlent via **localhost + ports** (pas besoin d’échanger l’IP perso si tout le monde clone le même repo et lance Docker localement).

### Arborescence détaillée (ownership)

```
digiscore_wa/
├── README.md                          # tous : comment démarrer
├── docker-compose.yml                 # Data (+ aide Back) : Postgres (+ optionnel Adminer)
├── .env.example                       # secrets/ports partagés (jamais de vrais secrets)
├── docs/
│   ├── CDC_DigiScore-WA_complet.md    # produit / métier
│   ├── GUIDE_EQUIPE.md                # CE guide (à livrer à l’exécution)
│   └── architecture.md
├── backend/
│   ├── db/
│   │   ├── schema.sql                 # ★ OWNER DATA (source de vérité schéma)
│   │   └── seed/                      # ★ OWNER DATA (SQL ou scripts)
│   ├── app/                           # ★ OWNER BACKEND (FastAPI)
│   │   ├── main.py
│   │   ├── api/                       # routes membres, demandes, score
│   │   ├── models/                    # ORM / schémas SQLAlchemy
│   │   ├── services/                  # orchestre : charge BDD → appelle scoring
│   │   └── schemas/                   # Pydantic (contrat JSON Front)
│   ├── requirements.txt
│   └── Dockerfile
├── scoring/                           # ★ OWNER SCORING (package Python pur)
│   ├── SPEC.md                        # formules, seuils, messages
│   ├── digiscore/                     # code importable
│   │   ├── financials.py              # CAF, RCSD, ratios
│   │   ├── scorecard.py               # 6 critères /100
│   │   ├── limits.py                  # plafond + thin-file
│   │   ├── messages.py                # codes → textes
│   │   └── pipeline.py                # run(dossier) → résultat
│   ├── tests/                         # golden tests sur cas seeds
│   └── pyproject.toml / requirements.txt
├── frontend/                          # ★ OWNER FRONT
│   ├── src/
│   │   ├── pages/                     # lookup membre, demande, résultat, mémo
│   │   ├── api/client.ts              # baseURL → http://localhost:8000
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
└── data/synthetic/                    # ★ OWNER DATA (CSV/JSON sources + README cas)
    ├── membres.json
    ├── comptes_mouvements.json
    ├── credits_passes.json
    ├── demandes.json
    └── cas_attendus.json              # score/plafond/message attendus (pour tests)
```

**Règle d’or** : on ne copie pas de fichiers « à la main » entre machines pour la BDD. On **commit** `schema.sql` + seeds + code ; chacun `git pull` + `docker compose up`.

---

### Comment la BDD est mise à disposition (Data → Backend)

**Mode recommandé (hackathon) : Postgres Docker sur chaque machine**

1. La personne **Data** écrit / maintient :
   - `backend/db/schema.sql`
   - `backend/db/seed/*.sql` (ou script qui charge `data/synthetic/*.json`)
   - `data/synthetic/` + `cas_attendus.json`
2. `docker-compose.yml` expose Postgres ainsi :

```yaml
# ports host:container
postgres:
  image: postgres:16
  ports:
    - "5432:5432"
  environment:
    POSTGRES_USER: digiscore
    POSTGRES_PASSWORD: digiscore
    POSTGRES_DB: digiscore
  volumes:
    - ./backend/db/schema.sql:/docker-entrypoint-initdb.d/01_schema.sql
    - ./backend/db/seed:/docker-entrypoint-initdb.d/02_seed
```

3. Ce que Data donne aux collègues (**une seule fiche connexion**, identique pour tous) :

| Paramètre | Valeur |
|-----------|--------|
| Host | `localhost` (ou `127.0.0.1`) |
| Port | `5432` |
| DB | `digiscore` |
| User | `digiscore` |
| Password | `digiscore` |
| URL | `postgresql://digiscore:digiscore@localhost:5432/digiscore` |

4. Backend lit cette URL via `.env` (`DATABASE_URL=...`). **Pas besoin de l’IP Wi‑Fi de la machine Data**, sauf mode dégradé ci‑dessous.

**Mode secours (une seule BDD partagée sur le LAN)** — seulement si Docker est lent / une seule machine « serveur » :

- Sur la machine Data : `docker compose up -d` + firewall autorise le port 5432.
- Data donne : `postgresql://digiscore:digiscore@<IP_LAN>:5432/digiscore` (ex. `192.168.1.42`).
- Inconvénient : dépendance réseau hackathon, collisions si plusieurs `compose` sur le même IP/port. **À éviter si possible.**

**Procédure Data au quotidien**

1. Modifier schéma/seeds dans le repo.
2. Si schéma change de façon incompatible : documenter `RESET BDD` (`docker compose down -v && docker compose up -d`).
3. `git commit` + prévenir Back/Scoring (« seeds v3, cas #4 thin-file mis à jour »).
4. Vérifier avec Adminer optionnel (`http://localhost:8080`) ou `psql`.

**Ce que Backend ne fait pas** : inventer des tables. Il consomme le schéma Data ; s’il manque un champ, ticket → Data met à jour `schema.sql`.

---

### Backend — tâches concrètes + dossier

**Dossier** : `backend/` (+ consomme `scoring/` en dépendance Python).

**Mission** : exposer une API HTTP qui (1) lit/écrit Postgres, (2) assemble le « dossier normalisé », (3) appelle le package `scoring`, (4) renvoie JSON au front, (5) journalise décisions.

**Tâches pas à pas**

1. Brancher SQLAlchemy/asyncpg sur `DATABASE_URL`.
2. Endpoints minimaux :
   - `GET /membres?q=` / `GET /membres/{id}` → fiche + résumé historique
   - `GET /membres/{id}/historique` → crédits passés, mouvements agrégés, incidents
   - `POST /demandes` → crée demande **liée à un membre** (refus si non membre)
   - `POST /demandes/{id}/analyser` → charge BDD → `scoring.pipeline.run(...)` → sauve `score_resultat`
   - `GET /demandes/{id}` → demande + score + messages
   - `POST /demandes/{id}/decision` → override + audit
3. Couche `services/dossier_builder.py` : **seul endroit** qui transforme lignes SQL → objet attendu par Scoring (contrat figé dans `scoring/SPEC.md`).
4. Ne **pas** recalculer CAF/RCSD/score dans les routes — déléguer à `scoring`.
5. Publier OpenAPI : `http://localhost:8000/docs` = contrat pour le Front.
6. CORS : autoriser `http://localhost:5173` (Vite).

**Ports**

| Service | Port |
|---------|------|
| Postgres | 5432 |
| FastAPI | 8000 |
| Frontend Vite | 5173 |
| Adminer (opt.) | 8080 |

**Comment Backend « reçoit » le travail Scoring**

- Ajoute `scoring` en dépendance locale, ex. dans `requirements.txt` : `-e ../scoring`
- Dans le code : `from digiscore.pipeline import run`
- Si Scoring change la signature → Back adapte uniquement `dossier_builder` + tests d’intégration.

**Comment Backend « reçoit » le travail Data**

- Au démarrage : DB déjà peuplée via init Docker.
- Modèles ORM alignés sur `schema.sql` (même noms de colonnes).

---

### Scoring — comment travailler avec Backend + guide modèle pas à pas

**Dossier** : `scoring/` uniquement (pas de FastAPI, pas de React, **pas d’accès BDD obligatoire**).

**Principe d’échange** : Scoring = **fonction pure**. Backend envoie un JSON/dict déjà assemblé ; Scoring renvoie un résultat ; Backend persiste.

```mermaid
sequenceDiagram
  participant Front
  participant Back
  participant DB
  participant Scoring
  Front->>Back: POST /demandes/id/analyser
  Back->>DB: load membre+hist+demande
  Back->>Back: dossier_builder
  Back->>Scoring: run(dossier)
  Scoring-->>Back: ScoreResult
  Back->>DB: insert score_resultat
  Back-->>Front: JSON score+plafond+message
```

**Contrat d’entrée (exemple)** — figé dans `scoring/SPEC.md` :

```text
DossierInput:
  membre: { id, anciennete_mois, statut }
  compte: { solde, date_ouverture }
  historique: { credits_passes[], incidents[], epargne_moy_3m, nb_mouvements_90j }
  demande: { montant, duree_mois, objet, produit_id }
  analyse: { revenus, charges, ratios saisis ou bruts, tresorerie[], patrimoine, preuves_N }
```

**Contrat de sortie** :

```text
ScoreResult:
  eligible: bool
  thin_file: bool
  score_global: 0..100
  criteres: [{ code, note, poids, contribution }]
  knockouts: [{ code, detail }]
  montant_demande, montant_eligible, montant_max_suggestion?
  message_code, message_humain
  explication: [str]   # top facteurs métier
```

**Workflow collab Scoring ↔ Back**

1. H0 : Scoring écrit `SPEC.md` + types (TypedDict/Pydantic dans `scoring`).
2. Data livre `cas_attendus.json` (entrée simplifiée + résultat attendu).
3. Scoring code + `pytest` golden **sans** attendre l’API.
4. Back branche `run()` ; test d’intégration sur 2–3 IDs seed.
5. Tout changement de formule = bump de version dans SPEC + maj `cas_attendus` + ping Back/Front (textes messages).

#### Guide collègue Scoring — outils + implémentation étape par étape

**Outils**

- Python 3.11+ , `pytest`, éventuellement `pydantic`
- Excel/Sheets ou table dans SPEC pour grilles de notes (lisibles jury)
- Calculatrice métier : valider 1 dossier à la main (CAF, RCSD) avant de coder
- **Pas** de Jupyter obligatoire ; si used → notebook hors package, résultats recopiés en tests

**Étape A — Cadre (½ journée max)**

1. Lire CDC + section plafond/thin-file du plan.
2. Remplir `scoring/SPEC.md` : formules CAF/RCSD, grille 6 critères, seuils 40/70, knock-outs, table messages, seuils thin-file, formule plafond.
3. Se mettre d’accord avec Data sur les champs disponibles dans les seeds.

**Étape B — Calculs financiers (`financials.py`)**

1. Implémenter `CAF = EBE + produits_financiers + surplus_deficit_personnel`
2. `RCSD = CAF / service_total_dette` (crédits en cours + crédit sollicité)
3. 6 ratios (marge, BN/CA, solvabilité, rotation stocks, participation, FR)
4. Tests unitaires avec chiffres ronds (ex. RCSD = 1.8)

**Étape C — Scorecard (`scorecard.py`)**

1. Pour chaque critère : fonction `note_0_100(...)` à partir de seuils (table SPEC).
2. `score = Σ (note_i / 100) * poids_i * 100`
3. Critère **Historique** : alimenté par `credits_passes` / incidents / ancienneté — **pas** inventé dans le formulaire seul.
4. Test : même entrée → même score (déterministe).

**Étape D — Thin-file + garde-fous (`limits.py` début)**

1. `thin_file` si ancienneté &lt; 3 mois OU (0 crédit soldé ET activité faible).
2. Si compte inactif / non membre → le Back bloque avant ; Scoring peut aussi renvoyer `NON_MEMBRE` en défense.

**Étape E — Plafond type télécom (`limits.py`)**

1. Calculer `montant_eligible` = min(
     plafond_produit,
     f(épargne_moy, CAF, score, taux_remboursement_hist),
     contrainte_RCSD (échéance supportable)
   )
2. Si thin-file → micro-plafond (ex. % épargne) ou refus au-delà.
3. Si demande &gt; éligible → `MONTANT_PLAFONNE`
4. Si score très haut + hist long + demande &lt;&lt; capacité → `UPSELL_POSSIBLE` (suggestion, pas octroi auto)
5. Si montant ≥ seuil exceptionnel (ex. 8–10 M) → `VOIE_EXCEPTIONNELLE`

**Étape F — Messages (`messages.py`)**

- Map `message_code` → phrase agent (FR), courte, style opérateur mobile.

**Étape G — Pipeline (`pipeline.py`)**

Ordre strict : garde-fous → financials → thin-file → scorecard → knockouts → limits → messages → explications.

**Étape H — Golden tests**

- Pour chaque cas dans `data/synthetic/cas_attendus.json` : assert message_code + fourchette score + montant_eligible (± tolérance).
- Back n’accepte le merge Scoring que si `pytest` vert.

**Ce que Scoring ne fait pas** : UI, SQL, Docker (sauf pour rejouer un cas via Back plus tard).

---

### Frontend — intégration Backend

**Dossier** : `frontend/`

**Branchement**

1. `.env` : `VITE_API_URL=http://localhost:8000`
2. Client fetch/axios centralisé (`src/api/client.ts`)
3. Écrans alignés parcours :
   - Recherche membre → fiche historique (badges thin-file / incidents)
   - Wizard demande (désactivé si non membre)
   - Bouton « Analyser » → affiche score, jauge, **montant demandé vs éligible**, message type télécom
   - Mémo + décision (motif si override)
4. Pendant que Back n’est pas prêt : mock MSW **ou** JSON statique issus de `cas_attendus` (même formes que l’OpenAPI).
5. Dès `/docs` dispo : supprimer mocks, pointer sur l’API réelle.
6. PWA : cache shell ; file d’attente offline = nice-to-have si temps.

**Règle** : le Front **n’implémente pas** les formules de score (affichage + saisie seulement).

---

### Matrice d’intégration « à chaque niveau »

| Niveau | Qui livre | Qui consomme | Comment on branche |
|--------|-----------|--------------|--------------------|
| Schéma SQL + seeds | Data | Back | Docker init + `DATABASE_URL` localhost:5432 |
| Cas attendus JSON | Data + Scoring | Scoring tests, démo | Fichiers dans `data/synthetic/` |
| Package `run(dossier)` | Scoring | Back `services/` | `pip install -e ../scoring` |
| OpenAPI JSON | Back | Front | `localhost:8000/docs` + `VITE_API_URL` |
| UI démo | Front | Jury | `localhost:5173` |

**Ordre de démarrage machine collègue**

```bash
git pull
docker compose up -d          # Postgres (+ seeds)
cd scoring && pytest          # optionnel mais sain
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev    # port 5173
```

**Sync humaine minimale**

- Data annonce tout reset `-v` (casse les bases locales).
- Scoring annonce tout changement de `message_code` / champs `DossierInput`.
- Back annonce tout breaking change d’URL.
- Front ne commit pas de formules métier « en dur ».

---

## À l’exécution (après validation)

1. CDC markdown complet (membre + SI/réseau + ressources).  
2. `schema.sql` membre-centrique + objets `digiscore_*` + seeds 8–12 (+ script volumétrie/index).  
3. SPEC scoring/plafond + squelette monorepo + README (ressources min/reco).  
4. `docs/GUIDE_EQUIPE.md` + `docs/architecture.md` (sidecar, topologies, ADD-only, anti-greffe).

*(Implémentation complète M1–M5 = sprint hackathon cadré par ce plan.)*
