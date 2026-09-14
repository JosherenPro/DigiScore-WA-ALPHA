# Prompt agent IA — Frontend DigiScore-WA

> **Usage** : coller ce fichier **en entier** à l’agent de code du collègue frontend (Cursor, Copilot, etc.).  
> En cas de conflit : **ce prompt + l’OpenAPI live** (`http://localhost:8000/docs`) priment.  
> Ne pas inventer de produit « néobanque », de JWT, ni de formules de score.

Tu es l’agent qui implémente / termine la **PWA React** du repo `digiscore_wa`.  
Tu travailles **uniquement** dans `frontend/`. Tu ne modifies pas `backend/`, `scoring/`, `backend/db/`, ni Docker.

---

## 0) Lis ça d’abord (30 secondes)

DigiScore-WA n’est **pas** un robot qui accorde le crédit tout seul. C’est un **copilote** pour les institutions de microfinance (CIF, exemple FUCEC-Togo) :

1. Pas de demande sans **compte membre déjà ouvert** et **actif**.
2. Le système calcule un **score /100**, un **plafond** (montant éligible) et un **message** (comme un opérateur télécom).
3. Un **humain** décide : Agent → Chef d’agence → CIC.
4. Hackathon 72 h. On vise un parcours démo fluide, pas un core banking.

**Toi (front)** = écrans + appels HTTP.  
**Back** = API + enregistrement en Postgres.  
**Scoring** = moteur de calcul (tu n’y touches pas, tu **affiches** le JSON).

Si tu commences à écrire `SELECT`, `postgresql://`, `EBE =`, `CAF =` ou `RCSD =` dans React : **tu t’es trompé de couche. Efface.**

---

## 1) Le projet, de A à Z (socle déjà là)

### 1.1 Qui fait quoi

```text
Utilisateur (agent / chef / cic)
        │
   PWA React  :5173     ← TOI
        │  fetch  VITE_API_URL=http://localhost:8000
   FastAPI    :8000     ← déjà prêt (ne pas réécrire)
        │
        ├── assemble le dossier → scoring.run()
        └── PostgreSQL :5432    ← déjà prêt (Docker)
```

| Dossier | Déjà en place ? | Toi |
|---------|-----------------|-----|
| `backend/` | Oui : routes, pagination, OpenAPI | Interdit de modifier |
| `scoring/` | Oui : `run(dossier)` | Interdit de modifier |
| `docker-compose.yml` | Oui : Postgres + Adminer + seed 120k | Tu lances, tu ne changes pas |
| `frontend/` | **Squelette** (login, routes, pages) | **Tu termines / corriges / polish** |

### 1.2 Comment lancer (ne pas réinventer)

```bash
# 1) Base (une fois)
docker compose up -d
# laptop lent : LOAD_VOLUME=0 docker compose up -d

# 2) API (obligatoire pour que le front vive)
cd backend && uvicorn app.main:app --reload --port 8000

# 3) Front
cd frontend && npm install && npm run dev
```

- UI : http://localhost:5173  
- Contrat API : http://localhost:8000/docs  
- OpenAPI figé : `docs/openapi.json`  
- Postman : `docs/postman/`  
- Guide court : `docs/GUIDE_FRONTEND.md`  
- Archi : `docs/ARCHI.md`

Fichier env front : `frontend/.env` avec `VITE_API_URL=http://localhost:8000`.

### 1.3 Login démo (pas de mot de passe, pas de JWT)

`POST /auth/login` body `{ "login": "agent" }` (ou `chef`, `cic`).

Réponse : `{ "id", "login", "nom", "role" }`.

| Bouton écran | `login` envoyé | `role` renvoyé | Accueil |
|--------------|----------------|----------------|---------|
| Agent de crédit | `agent` | `agent` | `/agent` |
| Chef d’agence | `chef` | `chef_agence` | `/chef` |
| CIC | `cic` | `cic` | `/cic` |

Session actuelle : `sessionStorage` via `frontend/src/auth.ts`. **Garde ce modèle.** Pas de SSO.

### 1.4 Les 12 users de démo (pitch)

Ce sont des **membres en base**, pas des comptes UI.

| Code | Qui | Ce que l’écran doit montrer |
|------|-----|-----------------------------|
| **MEM-001** | Kodjo Mensah | Bon dossier → score haut, montant OK / upsell → soumettre **file chef** |
| **MEM-004** | Aisha Slim | `thin_file: true`, message historique insuffisant |
| **MEM-009** | Isaac Gbeglo | 10 M, voie exceptionnelle → soumettre **file CIC** |
| **MEM-010** | Compte Gele | `statut: gele` → **pas** de bouton « Nouvelle demande » |

Cherche-les avec `GET /membres?q=MEM-001`.

### 1.5 Postgres existe, tu ne t’en sers pas

La BDD est **PostgreSQL 16**. Tables en **anglais** (`member.external_code`, `credit_application.requested_amount`…).

**Règle d’or :** le navigateur ne parle **jamais** à Postgres. Pas d’Adminer dans le front. Pas de noms de colonnes SQL dans le code React.

Tu respectes la BDD **indirectement** : tu affiches et tu envoies les **mêmes codes métier** que le seed / l’API (ils viennent de la base). Si tu inventes `active` au lieu de `actif`, tu casses le métier.

---

## 2) Contrat à respecter (la « structure »)

### 2.1 JSON français uniquement

L’API a traduit le SQL pour toi. Bind **ces clés-là** :

| Tu utilises (API) | Tu n’utilises JAMAIS (SQL) |
|-------------------|----------------------------|
| `code_externe` | `external_code` |
| `nom` / `prenom` | `last_name` / `first_name` |
| `montant_demande` | `requested_amount` |
| `epargne_moy_6m` | `avg_balance_6m` |
| `message_code` / `message_humain` | colonnes `score_result` |
| `montant_eligible` | `eligible_amount` |
| `ca` / `cmv` | `revenue` / `cogs` |

Source de vérité des champs : `backend/app/schemas/dossier.py` + Swagger.  
Si un champ n’est pas dans l’API : **tu ne l’inventes pas**. Ping le back.

### 2.2 Vocabulaire métier (valeurs exactes, minuscules)

**Membre / compte `statut`**

- `actif` — on peut ouvrir une demande  
- `gele` — compte gelé, **bloquer** la création  
- `radie` — même logique que gelé (pas de nouvelle demande)

**Demande `statut`** (parcours)

`brouillon` → `analyse` → `soumis_chef` **ou** `soumis_cic` → `accorde` / `conditionne` / `refuse` / `renvoye` (`clos` existe, rarement utile en démo)

**Crédits passés `statut`** : `solde`, `en_cours`, `impaye`.

**Preuves** : `N1` (faible) · `N2` · `N3` (fort). Sélecteurs, pas de texte libre.

**Situation fiscale** : `en_regle` · `a_verifier` · `non_conforme` · `non_fourni`.

**Qualité photo** : `ok` · `flou` · `sombre` · `coupe`.  
Si tu envoies autre chose que `ok`, l’API répond **400** : affiche « Reprendre la photo ».

**Types de pièce** (liste fermée) : `BIC`, `FISCAL`, `RELEVE`, `CARNET`, `ECHEANCIER`, `ATTESTATION_SOLDE`, `CNI`, `AUTRE`.

**Zone score** (déjà calculée par l’API, champ `zone`) :

- `rejet` = 0–40 (rouge)  
- `analyse` = 41–70 (orange)  
- `approbation` = 71–100 (vert)

Le score est **/100**, pas /1000.

**Décision**

- `niveau` : `agent` · `chef_agence` · `cic`  
- `avis` : `soumettre` · `valider` · `refuser` · `renvoyer` · `escalader` · `accorder` · `conditionner`  
- Si l’humain va **contre** la reco : `motif` **obligatoire**.

**Messages scoring** (affichage, ne pas renommer) :  
`NON_MEMBRE`, `COMPTE_INACTIF`, `HISTORIQUE_INSUFFISANT`, `EPARGNE_SOUS_SEUIL`, `INCIDENTS_RECENTS`, `MONTANT_PLAFONNE`, `MONTANT_OK`, `UPSELL_POSSIBLE`, `VOIE_EXCEPTIONNELLE`, `REJET_SCORE`, `CAUTION_REQUISE`, `BIC_OU_FISCAL_MANQUANT`, `PREUVES_EXTERNES_MANQUANTES`, `KNOCKOUT_RCSD`, `KNOCKOUT_ESG`.

Tu montres `message_humain` à l’utilisateur, et `message_code` en petit (debug / badge).

### 2.3 Pagination — le squelette actuel est FAUX

L’API ne renvoie **plus** un tableau. Le client `frontend/src/api/client.ts` attend encore un tableau : **corrige-le en premier**.

```json
{ "items": [ ... ], "page": 1, "page_size": 30, "total": 120012 }
```

Concerne : `GET /membres`, `GET /demandes`, `GET /files/chef`, `GET /files/cic`.

- Query : `q`, `page`, `page_size` (max **100**).  
- `q` cherche code membre, nom, prénom, **numéro de compte**.  
- Il peut y avoir **120 000** membres. Interdit de tout charger. Pager ou « page suivante » basé sur `total`.

Exemple :

```ts
type Page<T> = { items: T[]; page: number; page_size: number; total: number };

api.membres = (q: string, page = 1, pageSize = 30) =>
  req<Page<MembreResume>>(`/membres?q=${encodeURIComponent(q)}&page=${page}&page_size=${pageSize}`);
```

### 2.4 Interdits (l’agent qui divague casse le hackathon)

1. Recalculer CAF, RCSD, EBE, score, plafond dans le front. Tu **affiches** `ratios` et `score` renvoyés.  
2. Créer de nouveaux endpoints ou changer les URLs.  
3. Modifier `scoring/`, `schema.sql`, les seeds, Docker.  
4. Ajouter JWT / OAuth / i18n éwé.  
5. Brancher un autre host que `VITE_API_URL`.  
6. Mapper les écrans sur les noms de tables SQL.  
7. Faire un dashboard analytics générique à la place du parcours crédit.  
8. Auto-accorder un crédit (pas de bouton magique « Décaisser »).

---

## 3) Ce qui existe déjà dans `frontend/` (ne jette pas)

Squelette Vite + React + TypeScript + React Router.

| Fichier | Rôle | Ton job |
|---------|------|---------|
| `src/api/client.ts` | Tous les appels | **Corriger pagination + types Page** |
| `src/auth.ts` | Session | Garder |
| `src/App.tsx` | Routes + shell | Garder les URLs ; droits menu selon `role` |
| `pages/Login.tsx` | 3 rôles | Polish OK |
| `pages/AgentHome.tsx` | Lookup + liste dossiers | Pager, statut gelé |
| `pages/Membre.tsx` | Fiche + historique | Complet + CTA conditionnel |
| `pages/DemandeWizard.tsx` | Formulaire | Découper **A–E**, clés API exactes |
| `pages/Resultat.tsx` | Score / plafond | Demandé **vs** éligible bien visible |
| `pages/Memo.tsx` | Mémo | 6 rubriques API |
| `pages/FileChef.tsx` / `FileCic.tsx` | Files | Pagination + décision |
| `pages/Portefeuille.tsx` | M6 | Maquette, données API |
| `pages/Recouvrement.tsx` | M7 | Maquette, données API |

**Étends**, ne réécris pas une nouvelle app à côté.

Routes à conserver :

| Chemin | Écran |
|--------|--------|
| `/` | Login |
| `/agent` | Recherche membres |
| `/membres/:id` | Fiche |
| `/membres/:id/demande` | Wizard |
| `/demandes` | Liste dossiers agent |
| `/demandes/:id` | Résultat |
| `/demandes/:id/memo` | Mémo |
| `/chef` | File chef |
| `/cic` | File CIC |
| `/m6` | Portefeuille |
| `/m7` | Recouvrement |

---

## 4) Ce que tu dois implémenter (parcours)

Fais-le **dans cet ordre**. Chaque étape doit marcher avec l’API réelle avant de passer à la suivante.

### Étape A — Client API + login

- Types `Page<T>`.  
- Login 3 boutons, redirection selon `role`.  
- Erreur claire si l’API est down (« Lance uvicorn :8000 »).  
- Bandeau hors-ligne déjà dans le shell : garde-le.

### Étape B — Lookup membre (agent)

Écran `/agent` :

- Champ recherche (code `MEM-001`, nom, ou n° compte `CPTV-…`).  
- Liste : code, nom, prénom, **statut** (badge vert `actif` / rouge `gele`).  
- Pagination (`page` / `total`).  
- Clic → `/membres/:id`.

### Étape C — Fiche + historique

`GET /membres/{id}` (l’historique est le même objet).

Afficher :

- Identité, téléphone, zone, ancienneté, `thin_file` (bandeau si vrai).  
- Compte : numéro, statut, solde, épargne moy. 6 mois.  
- Crédits passés (montant, statut, retards).  
- Incidents.

Bouton **Nouvelle demande** **seulement si** `statut === "actif"` **et** `compte.statut === "actif"`.  
Sinon : texte « Compte inactif / gelé — demande impossible » (cas MEM-010).

### Étape D — Wizard collecte (visuellement A–E)

Une demande = `POST /demandes` puis éventuellement `POST /demandes/{id}/collecte` et `/pieces`.

Le body **collecte** doit utiliser **exactement** ces noms :

`ca`, `cmv`, `charges_exploitation`, `produits_financiers`, `revenu_perso`, `charge_familiale`, `charge_credits_en_cours`, `fonds_propres`, `total_dettes`, `actif_total`, `actif_circulant`, `passif_circulant`, `stock_moyen`, `resultat_net`, `preuve_revenu`, `preuve_charge`, `saisonnier`, `type_activite`, `valeur_garanties`.

Découpe l’UX en 5 étapes (labels terrain, un seul objet JSON à la fin) :

| Étape | Sens | Champs UI (côté API) |
|-------|------|----------------------|
| A Ménage / projet | Objet, produit, montant, durée, fiscale | `objet`, `produit_id`, `montant_demande`, `duree_mois`, `situation_fiscale` |
| B Activité | Type, saisonnier | `type_activite`, `saisonnier` |
| C Modèle / capacité | CA, CMV, charges, revenus ménage | `ca`, `cmv`, `charges_exploitation`, `produits_financiers`, `revenu_perso`, `charge_familiale` |
| D Marché / patrimoine | Dettes, actifs, garanties | `fonds_propres`, `total_dettes`, `actif_*`, `valeur_garanties`… |
| E Preuves | N1–N3, crédits ailleurs, photo | `preuve_*`, `credits_ailleurs`, `preuves_externes_ok`, pièce |

`GET /produits` pour le select produit (`id`, `libelle`, `montant_max`, `exceptionnel`).

Après création : `POST /analyser` puis aller sur `/demandes/{id}`.

Si membre gelé, l’API renvoie 400 `COMPTE_INACTIF` : affiche le message, ne invente pas un succès.

### Étape E — Résultat (le cœur du pitch)

Côte à côte, très visible :

- **Montant demandé**  
- **Montant éligible** (`score.montant_eligible`)  
- Score /100 + couleur de `zone`  
- Bannière `message_humain`  
- Optionnel : barre des 6 critères (`criteres[]` : note × poids), liste `knockouts`  
- `ratios.caf` / `rcsd` / `ebe` : **affichage seul**, légende « calculé par le moteur »

Boutons agent :

- Relancer analyse  
- Voir mémo  
- Voir amortissement (`GET .../amortissement` — tableau déjà calculé sur le montant **éligible**)  
- **Soumettre** → `POST /soumettre` → l’API dit `file: "chef"` ou `"cic"`. Confirme à l’écran (« Envoyé au chef » / « Envoyé au CIC »).

### Étape F — Mémo

`GET /demandes/{id}/memo` : titre, client, projet, 6 `rubriques`, avis, score.  
Mise en page imprimable simple (pas besoin de PDF réel).

### Étape G — File chef

`GET /files/chef?page=`  
Pour chaque ligne : ouvrir le dossier. Actions :

- Valider → `{ niveau: "chef_agence", avis: "valider", utilisateur_id }`  
- Refuser → `avis: "refuser"` + motif  
- Renvoyer → `avis: "renvoyer"` + motif  
- Escalader CIC → `avis: "escalader"`

`utilisateur_id` = `getUser().id`.

### Étape H — File CIC

Pareil avec `GET /files/cic` et `niveau: "cic"`, avis `accorder` / `conditionner` / `refuser`.

### Étape I — Maquettes M6 / M7 (léger)

- `GET /vision/portefeuille` : PAR 30/90 + alertes. Titre « Maquette — pas le live ».  
- `GET /vision/recouvrement` : liste niveaux 1–4.

Pas de graphiques complexes. Tableaux suffisent.

---

## 5) Mapping écran → API (pense-bête)

| Action utilisateur | Appel |
|--------------------|--------|
| Choisir un rôle | `POST /auth/login` |
| Chercher un membre | `GET /membres?q=&page=&page_size=` |
| Ouvrir la fiche | `GET /membres/{id}` |
| Liste produits | `GET /produits` |
| Créer le dossier | `POST /demandes` |
| Sauver la collecte | `POST /demandes/{id}/collecte` |
| Ajouter une pièce | `POST /demandes/{id}/pieces` |
| Lancer le score | `POST /demandes/{id}/analyser` |
| Revoir le dossier | `GET /demandes/{id}` |
| Mémo | `GET /demandes/{id}/memo` |
| Échéancier | `GET /demandes/{id}/amortissement` |
| Envoyer en file | `POST /demandes/{id}/soumettre?utilisateur_id=` |
| File chef / CIC | `GET /files/chef` · `GET /files/cic` |
| Trancher | `POST /demandes/{id}/decision` |
| M6 / M7 | `GET /vision/portefeuille` · `/vision/recouvrement` |
| Santé API | `GET /health` |

---

## 6) UX / UI (sans te perdre)

- Mobile d’abord (agent terrain), desktop OK pour chef / CIC.  
- Langue : **français**. Montants : FCFA, `fr-FR` (helper `money()` déjà dans `client.ts`).  
- Couleurs utiles : navy `#0B3D5C`, teal `#1A6B5C`, danger `#B42318`, warning `#B54708`, ok `#027A48`.  
- Pas de purple gradient, pas de néo-bank crypto.  
- Chaque score doit sembler **explicable** (critères + message), pas une boîte noire.

Maquettes Figma (inspiration, pas une spec pixel) : `docs/PROMPT_FIGMA_IA_DigiScore-WA.md`.  
Attention : ce texte Figma parle parfois de score /1000 — **ignore**, le produit est **/100**.

---

## 7) Comment savoir que c’est bon (recette)

Sans front « parfait », ces 4 scénarios doivent passer à la souris :

1. Login **agent** → `MEM-001` → nouvelle demande (ou dossier seed `#1`) → analyser → score haut → soumettre → badge file **chef**.  
2. `MEM-004` → fiche `thin_file` → analyser → message historique.  
3. `MEM-009` → analyser → `VOIE_EXCEPTIONNELLE` → soumettre → file **CIC**.  
4. `MEM-010` → pas de création de demande.

Puis login **chef** : voir la file, ouvrir, valider ou renvoyer.  
Login **cic** : voir MEM-009, accorder / refuser avec motif si besoin.

Recherche `VOL-` : une page de 30, `total` énorme — la page ne doit **pas** geler.

---

## 8) Si tu es bloqué

| Symptôme | Cause probable |
|----------|----------------|
| `Failed to fetch` | uvicorn pas lancé, ou mauvais `VITE_API_URL` |
| `/membres` « items.map is not a function » | Tu traites encore la réponse comme un tableau |
| 400 `COMPTE_INACTIF` | Membre/compte gelé — c’est normal |
| 400 qualité photo | `qualite_ocr` ≠ `ok` |
| 400 motif obligatoire | Override sans `motif` |
| Score bizarre | Tu as recalculé au lieu d’afficher l’API |

Docs alliés : `docs/GUIDE_FRONTEND.md`, `docs/ARCHI.md`, `docs/postman/README.md`, `docs/workflow-roles.md`.

---

## 9) Message à l’agent (résumé opératoire)

1. Ouvre seulement `frontend/`.  
2. Répare `api/client.ts` pour la pagination.  
3. Relie chaque écran déjà routé aux **vrais** JSON.  
4. Wizard A–E avec les **clés FR** listées.  
5. Résultat = demandé vs éligible + message + soumission.  
6. Files chef/CIC + décisions.  
7. Ne touche ni au SQL, ni au moteur, ni aux `message_code`.  
8. Recette MEM-001 / 004 / 009 / 010.

Tu construis l’interface du copilote. Le cerveau (score, plafond, règles) est **déjà derrière** `:8000`.
