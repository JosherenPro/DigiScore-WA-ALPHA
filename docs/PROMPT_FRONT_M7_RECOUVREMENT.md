# PROMPT 2 — M7 : Gestion du recouvrement (module vision, rôle chef_agence / cic)

## Contexte projet

Tu codes le module **M7 "Recouvrement"** de DigiScore-WA, copilote d'éligibilité et de
plafond de crédit pour les institutions CIF (FUCEC-Togo = échantillon démo,
hackathon CIF DigiCoop-WA+, équipe Alpha, thématique 02).

Le backend FastAPI existe **déjà**, tous les endpoints sont créés. Ton boulot : consommer
l'API. **Ne recalcule rien côté front** — les niveaux, priorités et buckets sont calculés
par le backend selon le protocole FUCEC.

Référence métier : `Cours_Gestion_Portefeuille_Recouvrement.pdf` (IPC-GMB / FUCEC Togo).

## Connexion API

- Base URL : `http://localhost:8000`
- Auth : `POST /auth/login` avec `{"login": "chef", "password": "demo"}` → `access_token`.
  Header ensuite : `Authorization: Bearer <token>` sur **tous** les appels (sinon 401).
- Logins : `agent` / `chef_agence` / `cic`, mot de passe `demo`.
- Swagger : `http://localhost:8000/docs`.
- `GET /moi` donne `role` et `agence_id`. Un **`chef_agence` ne voit que son agence**
  (filtrage automatique backend), `cic` voit tout.

## Le métier : le protocole en 4 niveaux

Le recouvrement FUCEC est **une mécanique implacable en 4 niveaux, sans improvisation**.
L'objectif est "militaire" : **éteindre l'incendie au niveau 1** — 95 % des dossiers se
règlent au N1. Chaque appel, visite et engagement **doit être tracé dès J+1** :
"si ce n'est pas écrit, ce n'est pas fait".

| Niveau | Période | Responsable | Actions |
|---|---|---|---|
| **N1** | J+1 à J+7 | Chargé de crédit | Appel J+1, visite J+3, documentation SIG |
| **N2** | J+8 à J+30 | Chargé + Superviseur | Visite domicile, caution contactée, mise en demeure |
| **N3** | J+31 à J+90 | Superviseur + Chef d'agence | Convocation formelle, échéancier écrit, garanties activées |
| **N4** | > J+90 | Direction / Juridique | Huissier, réalisation des garanties, action judiciaire |

**Preuve par les chiffres** (taux de récupération selon le délai d'action — à afficher en
callout, c'est l'argument le plus fort de la formation) :
- **J+1 à J+7 : 95 %** (quasi garantie)
- **J+30 à J+90 : 45 %** (1 dossier sur 2 perdu)
- **> 90 j : < 20 %** (catastrophique)
- **Contentieux : 40 % des dossiers = 0 franc récupéré**

Économie : intervenir tôt coûte ~50–500 F (un appel + une visite + une fiche) ;
intervenir tard coûte 100 000–500 000 F+ (huissier, justice, temps direction) avec
1 chance sur 2 de ne rien récupérer.

Matrice de priorisation (outil 04 FUCEC, pilotage hebdomadaire) : `P1` (encours > 2M ET
retard > 8 j) → **jour même** ; `P2` → sous 48 h ; `P3` → dans la semaine ;
`S` (surveillance) → visite planifiée.

Règle de transmission (aucun dossier ne monte sans) : historique J+1/J+3 documenté,
comptes-rendus de visite, engagements écrits, avis de la caution.

Le cours raconte le cas **Kpalimé** : PAR 3,8 % → 14 % en 4 mois, +12M → −8M, parce que
"aucun suivi J+1, zéro visite terrain, relance à J+30, pilotage mensuel".
Le danger commence **dès J+1**, jamais à 30 jours.

## Endpoints à utiliser (M7)

### 1. Vue d'ensemble recouvrement — `GET /vision/recouvrement`
Query : `?limit=100`. Permissions : agent / chef_agence / cic.
```json
{
  "module": "M7 recouvrement (calcule)",
  "dossiers": [
    { "membre_id": 7, "niveau": 3, "action": "Convocation formelle...", "responsable": "Superviseur + Chef d'agence" }
  ]
}
```
Vue synthétique des dossiers **non clos**, triés par niveau décroissant.

### 2. Dossiers de recouvrement détaillés — `GET /vision/recouvrement/dossiers`
Query (toutes optionnelles) : `?niveau=1..4&priorite=P1|P2|P3|S&limit=100`.
Permissions : agent / chef_agence / cic.
```json
{
  "as_of": "2026-09-14", "total": 3,
  "items": [{
    "case_id": 42, "member_id": 7, "member_code": "MEM-007",
    "niveau": 3, "libelle": "Recouvrement intensif",
    "action": "Convocation formelle, échéancier écrit, garanties activées",
    "responsable": "Superviseur + Chef d'agence",
    "priorite": "P1", "statut": "ouvert",
    "outstanding": 1450000, "days_late": 42,
    "opened_on": "2026-08-01", "next_on": "2026-09-21",
    "recovered_amount": 300000
  }]
}
```
C'est la **matrice de priorisation du recouvrement** (outil 04 FUCEC) — la vue principale
de M7. Filtres : `niveau` (1-4) et `priorite` (P1/P2/P3/S), à refléter comme filtres UI.
`statut` ∈ {`ouvert`, `clos`}.
Le backend complète automatiquement `libelle`/`action`/`responsable` à partir de
`days_late` selon la table des 4 niveaux — affiche-les tels quels.

### 3. Journal d'actions — `POST /vision/recouvrement/{case_id}/actions`
Permissions : agent / chef_agence / cic. Body :
```json
{
  "action_type": "appel_j1",
  "note": "Appel 10h. Promesse de règlement pour demain.",
  "action_on": "2026-09-14",
  "promise_on": "2026-09-15",
  "promise_kept": null,
  "amount_recovered": 0,
  "next_on": "2026-09-21",
  "owner_name": "A. Kossi"
}
```
Réponse :
```json
{
  "case_id": 42, "level": 3, "priority": "P1", "status": "ouvert",
  "next_on": "2026-09-21", "recovered_amount": 300000,
  "journal": [
    { "date": "2026-09-14", "type": "appel_j1", "note": "...", "montant": 0 },
    { "date": "2026-09-15", "type": "visite_j3", "note": "...", "montant": 150000 }
  ]
}
```
Effets côté backend (à refléter dans l'UI) : le **niveau du dossier est recalculé** à
partir du retard courant, `priority` est recalculée, `recovered_amount` est cumulé,
`next_on` par défaut = action_on + 7 jours, et `owner_name` est mis à jour.
**Cas d'erreur : 404 "Dossier de recouvrement introuvable" ; 409 "Dossier clos" si on
 poste une action sur un dossier fermé — affiche-le clairement.**

Types d'action attendus (vocabulaire FUCEC) : `appel_j1`, `visite_j3`, `visite_domicile`,
`contact_caution`, `convocation`, `mise_en_demedeure`, `echeancier écrit`,
`huissier`, `contentieux`. Le `action_type` est un `str` libre côté API — c'est TOI qui
tiens la liste dans le front (sélecteur), utilise ce vocabulaire.
`promise_on` + `promise_kept` = tracer les **promesses de paiement** : règle FUCEC
"un seul report écrit accordé, jamais deux sans escalade".
`amount_recovered` ∈ `>= 0` (validé par le backend).

### 4. Détail d'un dossier — croisement à afficher dans la fiche recouvrement
Pour le contexte du membre (à droite du journal) :
- `GET /membres/{membre_id}` — fiche (code, nom, statut, agence)
- `GET /membres/{membre_id}/prets` — prêts en cours
- `GET /membres/{membre_id}/recouvrement` — cas de recouvrement côté membre
- `GET /membres/{membre_id}/incidents` — incidents (gravité faible/moyenne/grave)
- `GET /membres/{membre_id}/garanties` — garanties (simple/solidaire)
- `GET /membres/{membre_id}/suivi` — historique de suivi
Tous nécessitent le header Bearer. Tous accessibles aux 3 rôles.

### 5. Référentiel signaux (pré-remplissage)
`GET /vision/signaux` (agent/chef/cic) — 12 signaux en 3 familles
(`activite`, `comportement`, `environnement`), `model_version: "referential-fucec-v1"`.
Sert pour le formulaire d'action de visite M6 si tu codes aussi M6 (voir prompt 1).

## Contraintes UI / UX

- **Traçabilité** : le journal d'actions est le cœur de M7. Chaque action doit avoir sa
  date, son type, sa note et son montant. "Si ce n'est pas écrit, ce n'est pas fait."
- **Pas de décision automatique** : le système propose (niveau, priorité), l'humain
  décide. Affiche le niveau/priorité comme une **recommandation**, pas comme un verdict.
- Montants en **FCFA** avec séparateur de milliers + suffixe "F".
- Affiche `next_on` de façon proéminente (prochaine action obligatoire) — un dossier
  sans prochaine action est un dossier oublié. En rouge si la date est dépassée.
- Filtres niveau (N1-N4) + priorité (P1/P2/P3/S) en haut de la liste des dossiers.
- Affiche en permanence le **taux de récupération** : 95 % / 45 % / <20 % selon
  l'ancienneté du retard — c'est l'argument qui justifie l'urgence de l'action.
- N'affiche pas les dossiers `clos` dans la liste de travail par défaut (filtre
  débrayable), mais laisse la possibilité de les consulter (lecture seule).
- Étiquettes en **français** (l'API parle déjà français : `statut`, `niveau`,
  `priorite`, `responsable`...).
- PWA mode dégradé : prévois l'état "serveur injoignable" sur le POST action,
  car c'est une action métier critique — ne laisse pas un bouton mourir silencieusement.

## Définition de done

1. Liste des dossiers de recouvrement (matrice de priorisation) avec filtres
   niveau (N1-N4) et priorité (P1/P2/P3/S), tri par niveau décroissant.
2. Fiche dossier détaillée : infos membre (cross-endpoints), niveau, responsable,
   prochaine action `next_on`, montant récupéré vs encours.
3. Journal d'actions chronologique + formulaire de saisie (POST .../actions)
   avec type d'action (sélecteur), note, promesse, montant récupéré, prochaine date.
4. Gestion des erreurs 404 (dossier introuvable) et 409 (dossier clos).
5. Callout "preuve par les chiffres" : 95 % / 45 % / <20 % de récupération.
6. Vue `GET /vision/recouvrement` (synthèse non-clos) comme page d'accueil du module.
