# PROMPT 1 — M6 : Suivi du portefeuille (module vision, rôle chef_agence / cic)

## Contexte projet

Tu codes le module **M6 "Suivi du portefeuille"** de DigiScore-WA, un copilote d'éligibilité
et de plafond de crédit pour les institutions membres de la CIF (FUCEC-Togo = échantillon de
démonstration, hackathon CIF DigiCoop-WA+, équipe Alpha, thématique 02).

Le backend FastAPI existe **déjà** et tous les endpoints dont tu as besoin sont créés.
Ton boulot : consommer l'API et afficher. **Ne recalcule rien côté front** — chaque indicateur
(PAR, aging, priorité, niveau) est calculé par le backend selon les formules FUCEC/CGAP.

Référence métier : `Cours_Gestion_Portefeuille_Recouvrement.pdf` (IPC-GMB / FUCEC Togo) et
`Section_5_FUCEC_S5_Suivi_portefeuille.pptx`.

## Connexion API

- Base URL : `http://localhost:8000`
- Auth : JWT Bearer. `POST /auth/login` body `{"login": "chef", "password": "demo"}`
  → réponse `{"access_token": "...", "token_type": "bearer", "user": {...}}`.
- Ensuite : header `Authorization: Bearer <token>` sur **tous** les appels (sinon 401
  "Token Bearer requis").
- Rôles disponibles : `agent`, `chef_agence`, `cic` — mot de passe `demo` pour les trois.
- Swagger interactif : `http://localhost:8000/docs`.
- `GET /moi` (header Bearer) retourne `{"id","login","nom","role","agence_id"}` : sers-t-en
  pour le scopage. **Note importante : un `chef_agence` ne voit que SON agence**
  (`agency_id`), le backend filgle automatiquement. `cic` voit tout.

## Le métier (à traduire en UI)

Le PAR est le thermomètre du portefeuille. Règle d'or FUCEC/CGAP : **tout le capital restant
dû est contaminé dès le premier retard**, pas seulement l'échéance impayée. Le cours IPC
montre une COOPEC passée de **PAR 3,8 % → 14 % en 4 mois** (+12M de bénéfice → −8M de perte)
par simple inaction : aucun suivi J+1, zéro visite terrain, relance à J+30 seulement, pilotage
mensuel. Moralité : **le danger commence à J+1, pas à 30 jours**.

Seuils PAR-30 (déjà implémentés dans le backend, champ `label` des réponses) :
- `< 5 %` → `acceptable` (sous contrôle, vigilance hebdo)
- `5–10 %` → `alerte` (protocole J+1 renforcé, superviseur)
- `> 10 %` → `critique` (plan de redressement, direction)

Cas d'école à afficher si tu veux un callout pédagogique : 1 milliard FCFA d'encours à
PAR 3 % = **30 000 000 F à risque**, et si la moitié est perdue = 15 M envolés.

Rituels à refléter dans l'UI : revue PAR **hebdomadaire chaque lundi** (pas en fin de mois),
transparence (le PAR s'affiche en agence), tolérance zéro (1 jour de retard = 1 action).

## Endpoints à utiliser (M6)

### 1. Vue tableau de bord — `GET /vision/portefeuille`
Query optionnelle : `?as_of=AAAA-MM-JJ` (défaut = aujourd'hui).
Permissions : agent / chef_agence / cic.

Réponse :
```json
{
  "module": "M6 portefeuille (calcule)",
  "as_of": "2026-09-14",
  "par": [
    { "agence_id": 1, "par1": 2.1, "par30": 3.4, "par90": 0.8,
      "encours_brut": 480000000, "label": "acceptable" }
  ],
  "alertes": [
    { "signal": "Retard 42 j - niveau N3", "membre_id": 7, "member_code": "MEM-007",
      "days_late": 42, "niveau": 3, "priorite": "P1" }
  ]
}
```
C'est ta page principale : cartes PAR-1 / PAR-30 / PAR-90 + encours brut par agence,
badge de couleur selon `label` (acceptable=vert, alerte=orange, critique=rouge),
et le top 5 des retards (`alertes`).

### 2. Tableau aging — `GET /vision/aging`
Query : `?as_of=AAAA-MM-JJ`. Permissions : agent / chef_agence / cic.
```json
{
  "as_of": "2026-09-14", "par1": 2.1, "par30": 3.4, "par90": 0.8,
  "label": "acceptable", "encours_brut": 480000000,
  "buckets": [
    { "bucket": "courant", "montant": 460000000, "dossiers": 1820, "part_pct": 95.8 },
    { "bucket": "1-7", "montant": 8200000, "dossiers": 44, "part_pct": 1.7 },
    { "bucket": "8-30", "montant": 5100000, "dossiers": 21, "part_pct": 1.1 },
    { "bucket": "31-90", "montant": 4400000, "dossiers": 11, "part_pct": 0.9 },
    { "bucket": ">90", "montant": 2300000, "dossiers": 6, "part_pct": 0.5 }
  ]
}
```
Affiche en tableau à 5 lignes (courant, 1-7, 8-30, 31-90, >90) avec montant, nombre de
dossiers, part en %. Le `bucket` correspond aux tranches de retard en jours.

### 3. Échéances du jour — `GET /vision/echeances`
Query : `?jour=AAAA-MM-JJ&limit=100`. Permissions : agent / chef_agence / cic.
```json
{
  "jour": "2026-09-14",
  "items": [{
    "outstanding_loan_id": 12, "member_id": 7, "member_code": "MEM-007",
    "outstanding": 450000, "days_late": 3, "due_on": "2026-09-11",
    "bucket": "1-7", "priorite": "P2", "niveau": 1,
    "action": "Appel J+1, visite J+3, documentation SIG",
    "responsable": "Chargé de crédit", "jour": "2026-09-14"
  }]
}
```
C'est la "grille de suivi journalier des échéances" (outil 01 de la boîte à outils FUCEC) :
**à extraire chaque matin**, colonne "Action menée" obligatoire pour tout dossier en retard.
`priorite` ∈ {`P1`, `P2`, `P3`, `S`} — P1 = encours > 2M **ET** retard > 8 j → action le jour
même ; P2 → sous 48 h ; P3 → dans la semaine ; S = surveillance → visite planifiée.

### 4. Visites à faire — `GET /vision/visites`
Query : `?as_of=AAAA-MM-JJ&limit=50`. Permissions : agent / chef_agence / cic.
```json
{
  "as_of": "2026-09-14",
  "items": [{
    "outstanding_loan_id": 12, "member_id": 7, "member_code": "MEM-007",
    "visite": "V1", "cible": "2026-09-14", "jours_de_retard": 3, "statut": "a_planifier"
  }]
}
```
Codes visite : `V1` (première visite post-décaissement, check-list 10 points),
`V2` (visite de suivi), `V3` (visite de remboursement / recouvrement).
La check-list V1 officielle FUCEC (outil 02) : présence, activité visible, investissements
constatés, montant cohérent, usage conforme, échéances connues — **alerte remontée si une
case est "Non"**. Règle : 2 NON = visite J+3, 3 NON = escalade N2.

### 5. Enregistrer une visite — `POST /vision/visites` (201)
Permissions : agent / chef_agence / cic. Body :
```json
{
  "member_id": 7,
  "visit_code": "V1",
  "visit_on": "2026-09-14",
  "officer_id": 1,
  "signal_code": "COM_EVITEMENT",
  "signal": "texte libre",
  "visit_status": "realisee",
  "next_on": "2026-09-17",
  "action_taken": "Appel passé, promesse de paiement J+2"
}
```
Contraintes de validation : `visit_code` ∈ {`V1`,`V2`,`V3`} (pattern `^V[123]$`),
`visit_status` ∈ {`planifiee`,`realisee`,`manquee`}. Réponse : l'objet visite créé avec
son `id`. **Cas d'erreur : 404 "Membre introuvable" si member_id inconnu.**

### 6. Référentiel des 12 signaux FUCEC — `GET /vision/signaux`
Permissions : agent / chef_agence / cic. Aucun paramètre.
```json
{
  "model_version": "referential-fucec-v1",
  "items": [
    { "code": "ACT_BAISSE_STOCK", "famille": "activite", "libelle": "Baisse visible des stocks ou de l'achalandage" },
    { "code": "COM_EVITEMENT", "famille": "comportement", "libelle": "Évitement : ne répond plus, absent aux visites" },
    { "code": "ENV_SINISTRE", "famille": "environnement", "libelle": "Sinistre (incendie, inondation, vol) touchant l'activité" }
  ]
}
```
Il y a **12 signaux** en 3 familles (`activite`, `comportement`, `environnement`).
Sers-t'en pour alimenter le sélecteur de `signal_code` du POST /vision/visites.
Famille = regroupement visuel naturel (3 colonnes ou 3 groupes).
Règle métier : **on capte l'événement avant l'échéance manquée** — un retard de 2 jours
n'est jamais rien, c'est déjà un signal.

### 7. Recalcul PAR (chef / cic seulement) — `POST /vision/par/recalcul`
Query : `?as_of=AAAA-MM-JJ`. **Permissions : chef_agence et cic uniquement**
(403 sinon). Réponse :
```json
{
  "as_of": "2026-09-14",
  "snapshots": [{ "agency_id": 1, "par1": 2.1, "par30": 3.4, "par90": 0.8,
                  "encours_brut": 480000000, "as_of": "2026-09-14" }]
}
```
Bouton "Recalculer le PAR" — à masquer pour le rôle `agent`.

### 8. Alertes ML consultatives (optionnel) — `GET /portefeuille/alertes`
Query : `?limit=20`. **Permissions : chef_agence et cic** + nécessite `ML_ENABLED=1`
 côté serveur (sinon 403/503 "ML désactivé"). Enrichissement consultatif, **jamais
 décisionnel**. À afficher dans un encart "analyse ML" clairement séparé.

## Contraintes UI / UX

- **Pas de décision automatique** : le système ne décide jamais seul. M6 est un outil
  d'aide à la décision pour le chef d'agence / le CIC.
- Affiche **toujours** la date de calcul (`as_of`) — c'est une donnée à date.
- Montants en **FCFA** : formate avec séparateur de milliers + suffixe "F"
  (ex. `480 000 000 F`). Ce sont des montants importants, le séparateur est vital.
- Le PAR est un **pourcentage avec 1 décimale** (ex. `3,4 %`) — chaque point de PAR
  compte ("Chaque point de PAR = des millions perdus = des emplois menacés").
- Badges : `acceptable` = vert, `alerte` = orange, `critique` = rouge.
- Navigation : pour un membre donné (`member_id`), tu peux croiser avec
  `GET /membres/{membre_id}` (fiche membre), `GET /membres/{membre_id}/prets`,
  `GET /membres/{membre_id}/suivi`, `GET /membres/{membre_id}/incidents`.
- Étiquettes en **français**, l'API utilise des clés françaises
  (`statut`, `montant_demande`, `situation_fiscale`, `jours_de_retard`...).
- PWA : l'app doit rester utilisable en mode dégradé (réseau lent/instable).
  Privilégie des états de chargement/erreur explicites plutôt qu'un spinner infini.

## Définition de done

1. Tableau de bord M6 avec les 3 PAR + encours brut + badge de zone par agence.
2. Tableau aging 5 buckets.
3. Liste des échéances du jour avec badge de priorité (P1/P2/P3/S) et niveau N1-N4.
4. Liste des visites à faire + formulaire d'enregistrement de visite (POST /vision/visites)
   avec sélecteur de signal alimenté par /vision/signaux.
5. Bouton recalcul PAR (masqué pour `agent`).
6. Top 5 des retards en page d'accueil du module.
