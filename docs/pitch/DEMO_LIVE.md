# Démo live DigiScore-WA — données client & parcours Agent → Chef → CIC

> Fichier de préparation pour la démo jury. Toutes les valeurs sont celles du seed
> réel (constatées sur l'API le 15/09/2026). **Accent : pages Chef d'agence et CIC.**

## 0. Accès

| Service | URL | Compte |
|---|---|---|
| PWA | http://localhost:5173 | `agent`/`agent` · `direct`/`direct` · `cic`/`cic` |
| Swagger | http://localhost:8000/docs | Bearer via `POST /auth/login` |
| Adminer | http://localhost:8080 | `digiscore` / `digiscore` |

`ML_ENABLED=1` : panneau ML shadow visible (scorecard-v3, anomalies, plafond, simulation).
Files seedées déjà présentes : demandes **10** (MEM-011) et **20037** en `soumis_chef` — ne pas les confondre avec les dossiers de la démo.

---

## 1. Le client : MEM-001 Kodjo Mensah (parcours agent)

### Fiche membre

| Champ | Valeur |
|---|---|
| Membre | id **1** — `MEM-001` Mensah Kodjo |
| Téléphone / occupation | 90111111 — commerçant |
| Zone / agence | urbaine — AGE-LME-01 COOPEC Demo Lomé Centre |
| Adhésion | 2021-03-01 (66 mois) |
| Compte | `CPT-001` épargne, actif, solde **450 000 F**, épargne moy. 6 m **400 000 F** |
| Crédits passés | 400 000 soldé (10/01/2024, 0 retard) · 600 000 soldé (01/03/2025, 0 retard) |
| Incidents | aucun · 46 mouvements · garantie « Stock commerce » **350 000 F** (N2) |

### Valeurs à saisir dans le formulaire (wizard 5 étapes)

**Étape 1 — Demande**

| Champ | Valeur |
|---|---|
| Produit | `COM-STD` — Crédit commerce standard (id 1, plafond 3 000 000) |
| Objet | Renouvellement stock boutique |
| Montant | **500 000 F** |
| Durée | **12 mois** |
| Situation fiscale | en règle |
| Crédits ailleurs | ☐ non |
| Preuves externes | ☐ (sans objet ici) |

**Étape 2 — Activité** : type **commerce**, saisonnier ☐ non (activité « Boutique vivres », 60 mois, Lomé).

**Étape 3 — Exploitation**

| Champ | Valeur |
|---|---|
| CA | **3 600 000 F** |
| CMV | **1 800 000 F** |
| Charges d'exploitation | **600 000 F** |
| Produits financiers | 20 000 F |
| Revenu perso | 200 000 F |
| Charge familiale | 80 000 F |
| Charge crédits en cours | **0 F** |

**Étape 4 — Bilan / garanties**

| Champ | Valeur |
|---|---|
| Fonds propres | 800 000 F |
| Total dettes | 200 000 F |
| Actif total | 1 500 000 F |
| Actif circulant | 700 000 F |
| Passif circulant | 250 000 F |
| Stock moyen | 300 000 F |
| Résultat net | 400 000 F |
| Valeur garanties | **350 000 F** |

**Étape 5 — Preuves** : preuve revenu **N3**, preuve charge **N2** ; pièces CNI (ok) + FISCAL (ok).

### Contexte affiché sur la fiche (pas à saisir)

- Patrimoine : actifs productifs 700 000 · non productifs 200 000 · passifs formels 150 000 · informels 50 000 ·
  signaux ⌀
- Marché : haute déc-jan · basse juin-août · 40 clients/j · **6 concurrents** · débouché unique ☐
- Ménage : taille 5 · locataire · 3 dépendants · revenus d'appoint : activité 1 200 000, secondaire 100 000, conjoint 80 000
- Trésorerie : plan 12 mois seedé (mois 1–12)

### Résultat attendu après « Analyser » (constaté)

| | |
|---|---|
| Score | **86,1 / 100** — zone **approbation** |
| Message | **`UPSELL_POSSIBLE`** → capacité jusqu'à **870 000 F** (suggestion) |
| Ratios | EBE 1 200 000 · CAF 1 340 000 · **RCSD 2,633** |
| Thin-file / KO | non / aucun |
| ML shadow | proba faible · plafond ML = plafond règles (facteur 1,0) |

**Action :** `Analyser` (déjà fait 10 fois → historisé) puis **`Soumettre`** → statut `soumis_chef` → file du **chef d'agence**.

---

## 2. Page Directeur (Chef d'Agence) (compte `direct` / `direct`) — à montrer en détail

**Où :** menu **File d'attente → Chef** (`GET /files/chef`, statut `soumis_chef`, agence 1).
**Ce qu'il voit :** la liste avec MEM-001 Kodjo, score **86,1**, plafond **870 000**, message `UPSELL_POSSIBLE`.

**Boutons et effets réels :**

| Bouton | Avis envoyé | Statut résultant |
|---|---|---|
| **Valider** | `valider` | `accorde` (si zone approbation, hors voie exceptionnelle, montant < 8 M) |
| Refuser | `refuser` (+ override) | `refuse` — **motif obligatoire** |
| Renvoyer | `renvoyer` | `renvoye` (retour agent) |
| **Escalader CIC** | `escalader` | `soumis_cic` |

**Valeurs pour la démo :**

1. **MEM-001 (500 000 F)** : cliquer **Valider** (motif vide) → le dossier passe **`accorde`**.
   Phrase : « recommandation approbation + plafond couvert → le chef peut clôturer ».
2. **MEM-009 (10 000 000 F)** : le chef **ne peut pas clôturer** (montant ≥ 8 M, `VOIE_EXCEPTIONNELLE`)
   → cliquer **Escalader CIC** → statut **`soumis_cic`** → file CIC.
   (S'il clique « valider », le back route automatiquement en `soumis_cic` — garde-fou.)
3. Optionnel : **Refuser** avec motif (ex. « garanties insuffisantes ») pour montrer l'override tracé
   (`decision.is_override = true`, motif obligatoire).

---

## 3. Page CIC (compte `cic` / `demo`) — à montrer en détail

**Où :** menu **File d'attente → CIC** (`GET /files/cic`, statut `soumis_cic`).
**Dossier à défendre : MEM-009 Isaac Gbeglo — 10 000 000 F sur 24 mois** (produit exceptionnel `EXC-10M`).

| Élément | Valeur |
|---|---|
| Objet | Extension entrepôt (exceptionnel) |
| Montant / durée | **10 000 000 F** / 24 mois |
| Score | **83,2 / 100** — zone approbation — `VOIE_EXCEPTIONNELLE` |
| Ratios | EBE 7 500 000 · **CAF 8 300 000** · **RCSD 1,543** (confort ≥ 1,50) |
| Plafond moteur | **10 290 000 F** |
| Situation fiscale | en règle |
| Cautions (2, éligibles) | **Paul Mensah** (frère, solidaire) 5 000 000 — revenu 900 000, CAF relais 600 000, RCSD 1,8, score 78 · **Grace Koffi** (épouse, solidaire) 5 000 000 — revenu 700 000, CAF relais 450 000, RCSD 1,6, score 72 |

**Boutons :**

| Bouton | Avis | Statut |
|---|---|---|
| **Accorder** | `accorder` | `accorde` |
| **Conditionner** | `conditionner` | `conditionne` (ex. « déblocage par tranches ») |
| Refuser | `refuser` (+ override) | `refuse` — motif obligatoire |

**Valeurs pour la démo :** **Accorder** avec motif « garanties et 2 cautions solidaires vérifiées, RCSD 1,54 »
— ou **Conditionner** « déblocage par tranches selon avancement des travaux ».
Montrer après coup : `decision`, `audit_log`, historique `score_result_history`.

---

## 4. Autres cas (oral, sans formulaire)

| Membre | Demande | Attendu constaté |
|---|---|---|
| MEM-004 Aisha Slim | 4 — 400 000 F / 8 mois | score **27,1** · **`KNOCKOUT_RCSD`** (RCSD 0,41) · plafond 0 → refus tracé |
| MEM-009 Isaac Gbeglo | 9 | `VOIE_EXCEPTIONNELLE` → chef escalade → CIC (section 3) |
| MEM-010 Compte Gele | aucune | compte gelé — aucune demande possible |
| MEM-012 Extern Bicok | 11 — 350 000 F | preuves externes (relevé BTCI) |

## 5. Ce qui est tracé (à dire au jury)

- `score_result` + `financial_ratio` (courant) et `score_result_history` (avant chaque ré-analyse)
- `decision` : niveau (`agent`/`chef_agence`/`cic`), avis, motif, `is_override`
- `audit_log` : action + détail à chaque étape
- Statuts : `brouillon → analyse → soumis_chef → soumis_cic → accorde / conditionne / refuse / renvoye / clos`
