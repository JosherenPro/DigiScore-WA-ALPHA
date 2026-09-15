# Réponses de l'API DigiScore-WA — référence frontend

> Généré automatiquement depuis l'API réelle (Base : `http://localhost:8000`, ML activé, volume de données synthétique 120k membres / 20k demandes). Les JSON ci-dessous sont de **vraies réponses capturées** — c'est exactement ce que reçoit le front.

**Conventions**

- **Auth** : header `Authorization: Bearer <token>` (token de `POST /auth/login`). Sans token → `401`.
- **Logins démo** : `agent` / `direct` / `cic` — mots de passe `agent`, `direct`, `cic`.
- **Pagination** : les listes sont `{ items, page, page_size, total }` — itérer sur `.items` (page_size max 100).
- **Clés en français** : l'API parle FR (`code_externe`, `montant_demande`, `message_humain`…), pas les colonnes SQL EN.
- **Statuts demande** : `brouillon`, `analyse`, `soumis_chef`, `renvoye`, `soumis_cic`, `accorde`, `conditionne`, `refuse`, `clos`.
- **Zones de score** : `rejet` (≤ 40) · `analyse` (41–70) · `approbation` (≥ 71).
- **Avis de décision** : `soumettre`, `renvoyer`, `escalader`, `accorder`, `valider`, `conditionner`, `refuser`.
- **Niveaux** : `agent` → `chef_agence` → `cic`.
- **ML shadow** : les routes `/ml/*` et `/anomalies` sont **consultatives** — elles ne modifient jamais le score, l'éligibilité ni la décision. Désactivées si `ML_ENABLED=0` (→ `503`).

**Codes d'erreur usuels**

| Code | Signification |
|------|---------------|
| `400` | Règle métier (ex. `NON_MEMBRE`, `COMPTE_INACTIF`, pièce floue, avis inconnu, motif d'override obligatoire) |
| `401` | Token manquant ou invalide |
| `403` | Rôle insuffisant (ex. agent sur `/files/cic`, agent sur une décision `cic`) |
| `404` | Ressource introuvable |
| `422` | Validation (bornes, enums, scénario ML inconnu, page_size > 100) |
| `503` | Capacités ML désactivées |

---

## Santé & capacités

### `GET /health`

**Liveness + état de la base. Public (pas de token).**

- **Rôles** : public
- **Paramètres** : —
- **Réponse `200`** :
```json
{
  "status": "ok",
  "service": "digiscore-wa",
  "database": "ok"
}
```

### `GET /capabilities`

**Capacités ML actives côté serveur (drapeaux consultatifs). Public.**

- **Rôles** : public
- **Paramètres** : —
- **Réponse `200`** :
```json
{
  "ml_scorecard": true,
  "anomalies": true,
  "simulation": true,
  "early_warning": true,
  "model_version": "scorecard-v3"
}
```

---

## Auth

### `POST /auth/login`

**Connexion. Renvoie le `access_token` (JWT) + le profil `user`.**

- **Rôles** : public
- **Body attendu** :
```json
{
  "login": "agent",
  "password": "agent"
}
```

- **Réponse `200`** :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwibG9naW4iOiJhZ2VudCIsInJvbGUiOiJhZ2VudCIsImFnZW5jeV9pZCI6MSwiZXhwIjoxNzg5NDQyMjAzfQ.YC982dqV5crWisCW0A0Hs7OmJCymHakMI1No1GG_5Nw",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "login": "agent",
    "nom": "Ama Agent",
    "role": "agent",
    "agence_id": 1
  }
}
```

### `GET /moi`

**Profil de l'utilisateur connecté (même objet que `login.user`).**

- **Rôles** : agent / chef / cic
- **Paramètres** : —
- **Réponse `200`** :
```json
{
  "id": 1,
  "login": "agent",
  "nom": "Ama Agent",
  "role": "agent",
  "agence_id": 1
}
```

---

## Référentiels

### `GET /agences`

**Liste des agences.**

- **Rôles** : agent / chef / cic
- **Paramètres** : —
- **Réponse `200`** :
```json
[
  {
    "id": 1,
    "code": "AGE-LME-01",
    "nom": "COOPEC Demo Lome Centre",
    "ville": "Lome",
    "topologie": "shared"
  },
  {
    "id": 2,
    "code": "AGE-KPA-01",
    "nom": "COOPEC Demo Kpalime",
    "ville": "Kpalime",
    "topologie": "split"
  }
]
```

### `GET /institutions`

**Autres institutions financières (COOPEC, banques, IMF — pas le mobile money).**

- **Rôles** : agent / chef / cic
- **Paramètres** : —
- **Réponse `200`** :
```json
[
  {
    "id": 1,
    "code": "IF-COOPEC-KPA",
    "nom": "COOPEC Kpalime Union",
    "ville": "Kpalime",
    "type": "coopec"
  },
  {
    "id": 2,
    "code": "IF-COOPEC-SOK",
    "nom": "COOPEC Sokode",
    "ville": "Sokode",
    "type": "coopec"
  },
  "... (3 autres elements - tronque pour lisibilite)"
]
```

### `GET /referentiels`

**Toutes les enums : statuts, avis, niveaux, zones, preuves, types de pièces, qualité OCR. **À utiliser pour peupler les selects du front.****

- **Rôles** : agent / chef / cic
- **Paramètres** : —
- **Réponse `200`** :
```json
{
  "statuts_membre": [
    "actif",
    "gele",
    "... (1 autres elements - tronque pour lisibilite)"
  ],
  "statuts_demande": [
    "brouillon",
    "analyse",
    "... (7 autres elements - tronque pour lisibilite)"
  ],
  "avis": [
    "soumettre",
    "valider",
    "... (5 autres elements - tronque pour lisibilite)"
  ],
  "niveaux": [
    "agent",
    "chef_agence",
    "... (1 autres elements - tronque pour lisibilite)"
  ],
  "zones": [
    "rejet",
    "analyse",
    "... (1 autres elements - tronque pour lisibilite)"
  ],
  "preuves": [
    "N1",
    "N2",
    "... (1 autres elements - tronque pour lisibilite)"
  ],
  "types_piece": [
    "BIC",
    "FISCAL",
    "... (6 autres elements - tronque pour lisibilite)"
  ],
  "qualite_ocr": [
    "ok",
    "flou",
    "... (2 autres elements - tronque pour lisibilite)"
  ]
}
```

### `GET /produits`

**Produits de crédit (plafond, seuil de caution, flag exceptionnel).**

- **Rôles** : agent / chef / cic
- **Paramètres** : —
- **Réponse `200`** :
```json
[
  {
    "id": 1,
    "code": "COM-STD",
    "libelle": "Credit commerce standard",
    "montant_max": 3000000.0,
    "seuil_montant_caution": 2000000.0,
    "exceptionnel": false
  },
  {
    "id": 2,
    "code": "AGR-SAI",
    "libelle": "Credit agricole saisonnier",
    "montant_max": 2500000.0,
    "seuil_montant_caution": 2000000.0,
    "exceptionnel": false
  },
  "... (1 autres elements - tronque pour lisibilite)"
]
```

---

## M1 — Collecte d'informations (membres & dossier)

### `GET /membres`

**Recherche de membres paginée. `q` cherche sur code externe, nom, prénom et numéro de compte.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `q` (texte libre) · `page` (≥1) · `page_size` (1–100, défaut 30)
- **Réponse `200`** :
```json
{
  "items": [
    {
      "id": 1,
      "code_externe": "MEM-001",
      "nom": "Mensah",
      "prenom": "Kodjo",
      "statut": "actif",
      "date_adhesion": "2021-03-01",
      "agence_id": 1
    }
  ],
  "page": 1,
  "page_size": 2,
  "total": 1
}
```

### `GET /membres/{id}`

**Fiche membre complète : identité, agence, compte, crédits passés, incidents, totaux, `thin_file`, garanties.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id numérique du membre (ex. 1)
- **Réponse `200`** :
```json
{
  "id": 1,
  "code_externe": "MEM-001",
  "nom": "Mensah",
  "prenom": "Kodjo",
  "telephone": "90111111",
  "adresse": null,
  "occupation": "commercant",
  "statut": "actif",
  "zone": "urbaine",
  "date_adhesion": "2021-03-01",
  "anciennete_mois": 66,
  "thin_file": false,
  "agence": {
    "id": 1,
    "code": "AGE-LME-01",
    "nom": "COOPEC Demo Lome Centre",
    "ville": "Lome"
  },
  "compte": {
    "numero": "CPT-001",
    "statut": "actif",
    "solde": 450000.0,
    "epargne_moy_6m": 400000.0
  },
  "credits_passes": [
    {
      "montant": 400000.0,
      "statut": "solde",
      "nb_retards": 0,
      "jours_max_retard": 0,
      "source": "interne",
      "institution": null,
      "date_octroi": "2024-01-10"
    },
    {
      "montant": 600000.0,
      "statut": "solde",
      "nb_retards": 0,
      "jours_max_retard": 0,
      "source": "interne",
      "institution": null,
      "date_octroi": "2025-03-01"
    }
  ],
  "incidents": [],
  "nb_mouvements": 46,
  "nb_credits_passes": 2,
  "nb_demandes": 4,
  "nb_comptes_externes": 0,
  "garanties": [
    {
      "nature": "Stock commerce",
      "valeur": 350000.0
    }
  ]
}
```

### `GET /membres/{id}/historique`

**Historique : crédits + incidents + 30 derniers mouvements agence + résumés.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id membre
- **Réponse `200`** :
```json
{
  "id": 1,
  "code_externe": "MEM-001",
  "credits_passes": [
    {
      "montant": 400000.0,
      "statut": "solde",
      "nb_retards": 0,
      "jours_max_retard": 0,
      "source": "interne",
      "institution": null
    },
    {
      "montant": 600000.0,
      "statut": "solde",
      "nb_retards": 0,
      "jours_max_retard": 0,
      "source": "interne",
      "institution": null
    }
  ],
  "incidents": [],
  "mouvements": [
    {
      "date": "2026-08-01",
      "type": "depot",
      "montant": 80000.0,
      "libelle": "Depot boutique Mensah 08"
    },
    {
      "date": "2026-07-01",
      "type": "depot",
      "montant": 82000.0,
      "libelle": "Depot boutique Mensah 07"
    },
    "... (28 autres elements - tronque pour lisibilite)"
  ],
  "total_mouvements": 46,
  "nb_comptes_externes": 0
}
```

### `GET /membres/{id}/mouvements`

**Mouvements du compte agence, paginés.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` · `page` · `page_size`
- **Réponse `200`** :
```json
{
  "items": [
    {
      "date": "2026-08-01",
      "type": "depot",
      "montant": 80000.0,
      "libelle": "Depot boutique Mensah 08"
    },
    {
      "date": "2026-07-01",
      "type": "depot",
      "montant": 82000.0,
      "libelle": "Depot boutique Mensah 07"
    }
  ],
  "page": 1,
  "page_size": 2,
  "total": 46
}
```

### `GET /membres/{id}/credits-passes`

**Crédits passés (statut, retards, source interne/externe).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id membre
- **Réponse `200`** :
```json
[
  {
    "montant": 400000.0,
    "statut": "solde",
    "nb_retards": 0,
    "jours_max_retard": 0,
    "source": "interne",
    "institution": null,
    "date_octroi": "2024-01-10"
  },
  {
    "montant": 600000.0,
    "statut": "solde",
    "nb_retards": 0,
    "jours_max_retard": 0,
    "source": "interne",
    "institution": null,
    "date_octroi": "2025-03-01"
  }
]
```

### `GET /membres/{id}/incidents`

**Incidents (gravité, détail, date).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id membre
- **Réponse `200`** :
```json
[]
```

### `GET /membres/{id}/garanties`

**Garanties enregistrées.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id membre
- **Réponse `200`** :
```json
[
  {
    "nature": "Stock commerce",
    "valeur": 350000.0
  }
]
```

### `GET /membres/{id}/prets`

**Prêts en cours (encours, retard).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id membre
- **Réponse `200`** :
```json
[]
```

### `GET /membres/{id}/demandes`

**Demandes du membre, paginées.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` · `page` · `page_size`
- **Réponse `200`** :
```json
{
  "items": [
    {
      "id": 20034,
      "membre": "Kodjo Mensah",
      "membre_id": 1,
      "montant_demande": 500000.0,
      "statut": "accorde",
      "score": 86.1,
      "message_code": "UPSELL_POSSIBLE",
      "zone": "approbation"
    },
    {
      "id": 20022,
      "membre": "Kodjo Mensah",
      "membre_id": 1,
      "montant_demande": -500.0,
      "statut": "brouillon",
      "score": null,
      "message_code": null,
      "zone": null
    },
    "... (2 autres elements - tronque pour lisibilite)"
  ],
  "page": 1,
  "page_size": 30,
  "total": 4
}
```

### `GET /membres/{id}/bic`

**Consentement et rapport BIC.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id membre
- **Réponse `200`** :
```json
{
  "consentement": {
    "statut": "signe",
    "signe_le": "2026-09-01",
    "scan": "seed/bic_consent_001.pdf"
  },
  "rapport": {
    "nb_credits_externes": 0,
    "nb_incidents": 0,
    "synthese": "RAS",
    "source": "simulate"
  }
}
```

### `GET /membres/{id}/suivi`

**Visites de suivi (M7).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id membre
- **Réponse `200`** :
```json
[
  {
    "visite": "V1",
    "date": "2026-09-14",
    "jours_retard": 0,
    "signal": null
  },
  {
    "visite": "V1",
    "date": "2026-09-14",
    "jours_retard": 0,
    "signal": null
  }
]
```

### `GET /membres/{id}/recouvrement`

**Dossiers de recouvrement du membre avec journal d'actions (M8).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id membre
- **Réponse `200`** :
```json
[]
```

### `GET /membres/{id}/comptes-externes`

**Comptes dans d'autres institutions (COOPEC/banque/IMF).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id membre
- **Réponse `200`** :
```json
[]
```

### `GET /membres/{id}/mouvements-externes`

**Mouvements des comptes externes, paginés.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` · `page` · `page_size`
- **Réponse `200`** :
```json
{
  "items": [],
  "page": 1,
  "page_size": 2,
  "total": 0
}
```

### `POST /demandes`

**Création d'une demande (statut initial `brouillon`). Peut embarquer la collecte complète (sinon `POST /demandes/{id}/collecte` ensuite).**

- **Rôles** : agent
- **Body attendu** :
```json
{
  "membre_id": 1,
  "produit_id": 1,
  "objet": "Fonds de roulement - boucherie",
  "montant_demande": 500000,
  "duree_mois": 12,
  "situation_fiscale": "en_regle",
  "credits_ailleurs": false,
  "preuves_externes_ok": false,
  "collecte": {
    "ca": 3600000,
    "cmv": 1800000,
    "charges_exploitation": 600000,
    "produits_financiers": 20000,
    "revenu_perso": 200000,
    "charge_familiale": 80000,
    "charge_credits_en_cours": 0,
    "fonds_propres": 800000,
    "total_dettes": 200000,
    "actif_total": 1500000,
    "actif_circulant": 700000,
    "passif_circulant": 250000,
    "stock_moyen": 300000,
    "resultat_net": 400000,
    "valeur_garanties": 350000,
    "preuve_revenu": "N3",
    "preuve_charge": "N2",
    "saisonnier": false,
    "type_activite": "commerce"
  }
}
```

- **Réponse `200`** :
```json
{
  "id": 20035,
  "statut": "brouillon"
}
```

### `GET /demandes`

**Liste des demandes paginée (filtres statut et membre).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `statut` (optionnel) · `membre_id` (optionnel) · `page` · `page_size`
- **Réponse `200`** :
```json
{
  "items": [
    {
      "id": 20034,
      "membre": "Kodjo Mensah",
      "membre_id": 1,
      "montant_demande": 500000.0,
      "statut": "accorde",
      "score": 86.1,
      "message_code": "UPSELL_POSSIBLE",
      "zone": "approbation"
    },
    {
      "id": 20022,
      "membre": "Kodjo Mensah",
      "membre_id": 1,
      "montant_demande": -500.0,
      "statut": "brouillon",
      "score": null,
      "message_code": null,
      "zone": null
    }
  ],
  "page": 1,
  "page_size": 2,
  "total": 20014
}
```

### `GET /demandes/{id}`

**Dossier complet : membre, produit, collecte A–E, trésorerie 12 mois, score courant, décisions, pièces.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "id": 20034,
  "membre_id": 1,
  "produit_id": 1,
  "objet": "Fonds de roulement - boucherie",
  "montant_demande": 500000.0,
  "duree_mois": 12,
  "statut": "accorde",
  "situation_fiscale": "en_regle",
  "membre": {
    "id": 1,
    "code_externe": "MEM-001",
    "nom": "Mensah",
    "prenom": "Kodjo"
  },
  "produit": {
    "id": 1,
    "code": "COM-STD",
    "libelle": "Credit commerce standard",
    "exceptionnel": false
  },
  "score": {
    "score_global": 86.1,
    "thin_file": false,
    "eligible": true,
    "montant_eligible": 870000.0,
    "montant_max_suggestion": 870000.0,
    "message_code": "UPSELL_POSSIBLE",
    "message_humain": "Capacite estimee jusqu'a 870 000 FCFA (suggestion, non automatique).",
    "criteres": [
      {
        "code": "financier",
        "note": 100.0,
        "poids": 0.25,
        "contribution": 25.0
      },
      {
        "code": "capacite",
        "note": 88.0,
        "poids": 0.2,
        "contribution": 17.6
      },
      "... (4 autres elements - tronque pour lisibilite)"
    ],
    "knockouts": [],
    "explication": [
      "Score 86.1/100 - zone approbation",
      "RCSD 2.633 (norme >= 1,50 ; knockout < 1)",
      "... (1 autres elements - tronque pour lisibilite)"
    ],
    "zone": "approbation"
  },
  "ratios": {
    "caf": 1340000.0,
    "rcsd": 2.633,
    "ebe": 1200000.0
  },
  "decisions": [
    {
      "niveau": "agent",
      "avis": "soumettre",
      "motif": null,
      "override": false
    },
    {
      "niveau": "chef_agence",
      "avis": "accorder",
      "motif": null,
      "override": false
    }
  ],
  "pieces": [
    {
      "type_piece": "BIC",
      "qualite_ocr": "ok"
    }
  ],
  "collecte": {
    "ca": 3600000.0,
    "cmv": 1800000.0,
    "charges_exploitation": 600000.0,
    "produits_financiers": 20000.0,
    "revenu_perso": 200000.0,
    "charge_familiale": 80000.0,
    "preuve_revenu": "N3",
    "preuve_charge": "N2",
    "modele": null,
    "marche": null
  },
  "tresorerie": [],
  "patrimoine": null,
  "menage": null,
  "activite": {
    "type": "commerce",
    "saisonnier": false,
    "description": null
  }
}
```

### `POST /demandes/{id}/collecte`

**Sauvegarde de la collecte A–E (idempotent : met à jour si déjà présente).**

- **Rôles** : agent
- **Paramètres** : `id` = id demande
- **Body attendu** :
```json
{
  "ca": 3600000,
  "cmv": 1800000,
  "charges_exploitation": 600000,
  "produits_financiers": 20000,
  "revenu_perso": 200000,
  "charge_familiale": 80000,
  "charge_credits_en_cours": 0,
  "fonds_propres": 800000,
  "total_dettes": 200000,
  "actif_total": 1500000,
  "actif_circulant": 700000,
  "passif_circulant": 250000,
  "stock_moyen": 300000,
  "resultat_net": 400000,
  "valeur_garanties": 350000,
  "preuve_revenu": "N3",
  "preuve_charge": "N2",
  "saisonnier": false,
  "type_activite": "commerce"
}
```

- **Réponse `200`** :
```json
{
  "ok": true
}
```

### `GET /demandes/{id}/collecte`

**Collecte enregistrée + trésorerie + patrimoine.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "collecte": {
    "ca": 3600000.0,
    "cmv": 1800000.0,
    "charges_exploitation": 600000.0,
    "produits_financiers": 20000.0,
    "revenu_perso": 200000.0,
    "charge_familiale": 80000.0,
    "preuve_revenu": "N3",
    "preuve_charge": "N2",
    "modele": null,
    "marche": null
  },
  "tresorerie": [],
  "patrimoine": null
}
```

---

## M4 — Documents d'octroi (pièces, cautions)

### `POST /demandes/{id}/pieces`

**Ajout d'une pièce (après OCR). `qualite_ocr` = `flou` / `sombre` / `coupe` → `400` : refaire la photo.**

- **Rôles** : agent
- **Paramètres** : `id` = id demande
- **Body attendu** :
```json
{
  "type_piece": "BIC",
  "fichier": "upload/bic_001.jpg",
  "qualite_ocr": "ok"
}
```

- **Réponse `200`** :
```json
{
  "ok": true
}
```

### `GET /demandes/{id}/pieces`

**Pièces du dossier.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
[
  {
    "type_piece": "BIC",
    "qualite_ocr": "ok",
    "fichier": "upload/bic_001.jpg"
  }
]
```

### `GET /demandes/{id}/cautions`

**Cautionnaires et avis de caution.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
[
  {
    "nature": "Saisie terrain",
    "valeur": 350000.0
  }
]
```

---

## M2/M3 — Analyse économique, financière & scoring

### `POST /demandes/{id}/analyser`

**Lance le moteur de scoring : score /100, critères, knockouts, éligibilité, plafond, ratios. Passe la demande en statut `analyse`. Idempotent (archive le score précédent dans l'historique).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "eligible": true,
  "thin_file": false,
  "score_global": 86.1,
  "criteres": [
    {
      "code": "financier",
      "note": 100.0,
      "poids": 0.25,
      "contribution": 25.0
    },
    {
      "code": "capacite",
      "note": 88.0,
      "poids": 0.2,
      "contribution": 17.6
    },
    "... (4 autres elements - tronque pour lisibilite)"
  ],
  "knockouts": [],
  "montant_demande": 500000.0,
  "montant_eligible": 870000.0,
  "montant_max_suggestion": 870000.0,
  "message_code": "UPSELL_POSSIBLE",
  "message_humain": "Capacite estimee jusqu'a 870 000 FCFA (suggestion, non automatique).",
  "explication": [
    "Score 86.1/100 - zone approbation",
    "RCSD 2.633 (norme >= 1,50 ; knockout < 1)",
    "... (1 autres elements - tronque pour lisibilite)"
  ],
  "zone": "approbation",
  "financials": {
    "ebe": 1200000.0,
    "caf": 1340000.0,
    "rcsd": 2.633,
    "marge_brute_pct": 50.0,
    "benefice_net_pct": 11.11,
    "solvabilite": 4.0,
    "rotation_stocks_jours": 60.8,
    "participation_pct": 53.33,
    "fonds_roulement_pct": 280.0,
    "nb_ratios_degrades": 0,
    "mois_critique": null,
    "situation_nette": 0.0,
    "nb_signaux": 0
  }
}
```

### `GET /demandes/{id}/score`

**Score courant (version courte pour affichage).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "score_global": 86.1,
  "thin_file": false,
  "eligible": true,
  "montant_eligible": 870000.0,
  "montant_max_suggestion": 870000.0,
  "message_code": "UPSELL_POSSIBLE",
  "message_humain": "Capacite estimee jusqu'a 870 000 FCFA (suggestion, non automatique).",
  "zone": "approbation",
  "engine_version": "rules-v1"
}
```

### `GET /demandes/{id}/scores`

**Historique des analyses (ligne par analyse ; vide tant qu'une seule analyse a été faite).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
[
  {
    "score_global": 86.1,
    "message_code": "UPSELL_POSSIBLE",
    "eligible": true,
    "montant_eligible": 870000.0,
    "engine_version": "rules-v1",
    "analyse_le": "2026-09-14 15:16:43.569199+00:00"
  }
]
```

### `GET /demandes/{id}/ratios`

**CAF, RCSD, EBE calculés par le moteur.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "caf": 1340000.0,
  "rcsd": 2.633,
  "ebe": 1200000.0
}
```

### `GET /demandes/{id}/tresorerie`

**Plan de trésorerie mensuel (12 mois).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
[]
```

### `GET /demandes/{id}/memo`

**Mémo de crédit : titres des 6 rubriques + analyse + score + avis.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "titre": "Memo de credit DigiScore-WA",
  "client": "Kodjo Mensah",
  "projet": "Fonds de roulement - boucherie",
  "demande": 500000.0,
  "analyse": {
    "caf": 1340000.0,
    "rcsd": 2.633,
    "ebe": 1200000.0
  },
  "score": {
    "score_global": 86.1,
    "thin_file": false,
    "eligible": true,
    "montant_eligible": 870000.0,
    "montant_max_suggestion": 870000.0,
    "message_code": "UPSELL_POSSIBLE",
    "message_humain": "Capacite estimee jusqu'a 870 000 FCFA (suggestion, non automatique).",
    "criteres": [
      {
        "code": "financier",
        "note": 100.0,
        "poids": 0.25,
        "contribution": 25.0
      },
      {
        "code": "capacite",
        "note": 88.0,
        "poids": 0.2,
        "contribution": 17.6
      },
      "... (4 autres elements - tronque pour lisibilite)"
    ],
    "knockouts": [],
    "explication": [
      "Score 86.1/100 - zone approbation",
      "RCSD 2.633 (norme >= 1,50 ; knockout < 1)",
      "... (1 autres elements - tronque pour lisibilite)"
    ],
    "zone": "approbation"
  },
  "avis": "Capacite estimee jusqu'a 870 000 FCFA (suggestion, non automatique).",
  "rubriques": [
    "1. Presentation client et projet",
    "2. Demande de credit",
    "... (4 autres elements - tronque pour lisibilite)"
  ]
}
```

---

## M5 — Décision d'octroi (circuit agent → chef → CIC)

### `POST /demandes/{id}/soumettre`

**L'agent soumet le dossier analysé. Le routage est automatique : zone `approbation` → file chef ; zone `analyse` ou montant ≥ 8M → file CIC ; knockout en bande 41–70 → CIC (prudence).**

- **Rôles** : agent
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "statut": "soumis_chef",
  "file": "chef"
}
```

**Transition `avis` → statut** (réponse de `POST /decision`) :

| avis | statut résultat | notes |
|------|-----------------|-------|
| `renvoyer` | `renvoye` | retour à l'agent |
| `escalader` | `soumis_cic` | monte au CIC |
| `accorder` / `valider` | `accorde` | le chef ne peut fermer que si zone `approbation` et montant < 8M, sinon escalade CIC |
| `conditionner` | `conditionne` | conditions à remplir |
| `refuser` | `refuse` | |

### `POST /demandes/{id}/decision`

**Décision d'un reviewer. `niveau: chef_agence` exige le rôle chef, `niveau: cic` exige le rôle cic. Écart à la recommandation (`override`) → `motif` obligatoire sinon `400`.**

- **Rôles** : chef (niveau chef_agence) / cic (niveau cic)
- **Paramètres** : `id` = id demande
- **Body attendu** :
```json
{
  "niveau": "chef_agence",
  "avis": "accorder",
  "motif": null,
  "override": false
}
```

- **Réponse `200`** :
```json
{
  "statut": "accorde",
  "override": false
}
```

### `GET /demandes/{id}/decisions`

**Journal des décisions du dossier.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
[
  {
    "niveau": "agent",
    "avis": "soumettre",
    "motif": null,
    "override": false
  },
  {
    "niveau": "chef_agence",
    "avis": "accorder",
    "motif": null,
    "override": false
  },
  "... (2 autres elements - tronque pour lisibilite)"
]
```

### `GET /demandes/{id}/audit`

**Piste d'audit complète (création, analyse, soumission, décisions).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
[
  {
    "action": "create",
    "detail": "Fonds de roulement - boucherie"
  },
  {
    "action": "analyser",
    "detail": "UPSELL_POSSIBLE"
  },
  "... (5 autres elements - tronque pour lisibilite)"
]
```

### `GET /files/chef`

**File d'attente du chef (demandes `soumis_chef`).**

- **Rôles** : chef / cic
- **Paramètres** : `page` · `page_size`
- **Réponse `200`** :
```json
{
  "items": [
    {
      "id": 10,
      "membre": "Demo Override",
      "membre_id": 11,
      "montant_demande": 400000.0,
      "statut": "soumis_chef",
      "score": null,
      "message_code": null,
      "zone": null
    }
  ],
  "page": 1,
  "page_size": 2,
  "total": 1
}
```

### `GET /files/cic`

**File d'attente du CIC (demandes `soumis_cic`). **Réservée au rôle cic.****

- **Rôles** : cic
- **Paramètres** : `page` · `page_size`
- **Réponse `200`** :
```json
{
  "items": [],
  "page": 1,
  "page_size": 2,
  "total": 0
}
```

---

## M6 — Tableau d'amortissement

### `GET /demandes/{id}/amortissement`

**Tableau actuariel + assurance (taux nominal 14 %, assurance 5,7 %/an par défaut). Sans paramètres : calculé sur le montant éligible et persisté (1 ligne/mois). Avec `montant`/`duree_mois` : simulation à la volée, rien n'est écrit.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `montant` (≥0) · `duree_mois` (1–60) · `taux_nominal` (décimal annuel, défaut 0.14) · `taux_assurance` (défaut 0.057)
- **Réponse `200`** :
```json
{
  "montant": 870000.0,
  "duree_mois": 12,
  "taux_nominal": 0.14,
  "taux_assurance": 0.057,
  "mensualite_hors_assurance": 78115.0,
  "assurance_mensuelle": 4132.0,
  "mensualite_totale": 82247.0,
  "cout_total": 116960.0,
  "lignes": [
    {
      "numero": 1,
      "echeance": 78115,
      "capital": 67965,
      "interet": 10150,
      "assurance": 4132,
      "echeance_totale": 82247,
      "restant": 802035.0
    },
    {
      "numero": 2,
      "echeance": 78115,
      "capital": 68758,
      "interet": 9357,
      "assurance": 4132,
      "echeance_totale": 82247,
      "restant": 733277.0
    },
    "... (10 autres elements - tronque pour lisibilite)"
  ]
}
```

### `GET /demandes/{id}/amortissement` — variante simulation

**Même endpoint avec `montant=300000&duree_mois=6` : calcul à la volée, aucune ligne persistée.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `montant=300000` · `duree_mois=6`
- **Réponse `200` (simulation)** :
```json
{
  "montant": 300000.0,
  "duree_mois": 6,
  "taux_nominal": 0.14,
  "taux_assurance": 0.057,
  "mensualite_hors_assurance": 52061.0,
  "assurance_mensuelle": 1425.0,
  "mensualite_totale": 53486.0,
  "cout_total": 20917.0,
  "lignes": [
    {
      "numero": 1,
      "echeance": 52061,
      "capital": 48561,
      "interet": 3500,
      "assurance": 1425,
      "echeance_totale": 53486,
      "restant": 251439.0
    },
    {
      "numero": 2,
      "echeance": 52061,
      "capital": 49128,
      "interet": 2933,
      "assurance": 1425,
      "echeance_totale": 53486,
      "restant": 202311.0
    },
    "... (4 autres elements - tronque pour lisibilite)"
  ]
}
```

---

## M7 — Suivi du portefeuille

### `GET /vision/portefeuille`

**Vue portefeuille : PAR par agence + alertes.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `as_of` (date ISO, optionnel)
- **Réponse `200`** :
```json
{
  "module": "M6 portefeuille (calcule)",
  "as_of": "2026-09-14",
  "par": [
    {
      "agence_id": 1,
      "par1": 17.46,
      "par30": 10.42,
      "par90": 0.0,
      "encours_brut": 3096502885.0,
      "label": "critique"
    }
  ],
  "alertes": [
    {
      "signal": "Retard 48 j - niveau N3",
      "membre_id": 226,
      "member_code": "VOL-0000214",
      "days_late": 48,
      "niveau": 3,
      "priorite": "P2"
    },
    {
      "signal": "Retard 48 j - niveau N3",
      "membre_id": 324,
      "member_code": "VOL-0000312",
      "days_late": 48,
      "niveau": 3,
      "priorite": "P2"
    },
    "... (3 autres elements - tronque pour lisibilite)"
  ]
}
```

### `GET /vision/aging`

**Aging : buckets de retard, PAR1/30/90, encours brut.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `as_of` (optionnel)
- **Réponse `200`** :
```json
{
  "as_of": "2026-09-14",
  "par1": 17.46,
  "par30": 10.42,
  "par90": 0.0,
  "label": "critique",
  "encours_brut": 3096502885.0,
  "buckets": [
    {
      "bucket": "courant",
      "montant": 2555881991.0,
      "dossiers": 10211,
      "part_pct": 82.54
    },
    {
      "bucket": "1-7",
      "montant": 0.0,
      "dossiers": 0,
      "part_pct": 0.0
    },
    "... (3 autres elements - tronque pour lisibilite)"
  ]
}
```

### `GET /vision/echeances`

**Échéances du jour (ou d'un jour donné) avec bucket, priorité, niveau de recouvrement.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `jour` (date ISO, optionnel) · `limit` (1–500)
- **Réponse `200`** :
```json
{
  "jour": "2026-09-14",
  "items": [
    {
      "outstanding_loan_id": 9166,
      "member_id": 75628,
      "member_code": "VOL-0075616",
      "outstanding": 492597.0,
      "days_late": 48,
      "due_on": "2026-05-11",
      "bucket": "31-90",
      "priorite": "P2",
      "niveau": 3,
      "action": "Convocation formelle, échéancier écrit, garanties activées",
      "responsable": "Superviseur + Chef d'agence",
      "jour": "2026-09-14"
    },
    {
      "outstanding_loan_id": 13758,
      "member_id": 113428,
      "member_code": "VOL-0113416",
      "outstanding": 492130.0,
      "days_late": 48,
      "due_on": "2023-03-04",
      "bucket": "31-90",
      "priorite": "P2",
      "niveau": 3,
      "action": "Convocation formelle, échéancier écrit, garanties activées",
      "responsable": "Superviseur + Chef d'agence",
      "jour": "2026-09-14"
    }
  ]
}
```

### `GET /vision/visites`

**Visites à faire / réalisées.**

- **Rôles** : agent / chef / cic
- **Paramètres** : —
- **Réponse `200`** :
```json
{
  "as_of": "2026-09-14",
  "items": [
    {
      "outstanding_loan_id": 6623,
      "member_id": 54556,
      "member_code": "VOL-0054544",
      "visite": "V1",
      "cible": "2015-12-11",
      "jours_de_retard": 3930,
      "statut": "en_retard"
    },
    {
      "outstanding_loan_id": 10189,
      "member_id": 84252,
      "member_code": "VOL-0084240",
      "visite": "V1",
      "cible": "2015-12-11",
      "jours_de_retard": 3930,
      "statut": "en_retard"
    },
    "... (48 autres elements - tronque pour lisibilite)"
  ]
}
```

### `POST /vision/visites`

**Journalise une visite (V1/V2/V3).**

- **Rôles** : agent / chef / cic
- **Body attendu** :
```json
{
  "member_id": 1,
  "visit_code": "V1",
  "visit_status": "realisee",
  "signal_code": "SIG_CA_BAISSE",
  "signal": "Baisse du CA",
  "action_taken": "Relance telephonique"
}
```

- **Réponse `201`** :
```json
{
  "id": 9612,
  "member_id": 1,
  "visit_code": "V1",
  "visit_on": "2026-09-14",
  "visit_status": "realisee",
  "signal_code": "SIG_CA_BAISSE",
  "signal": "Baisse du CA",
  "action_taken": "Relance telephonique"
}
```

### `GET /vision/signaux`

**Référentiel des signaux d'alerte FUCEC.**

- **Rôles** : agent / chef / cic
- **Paramètres** : —
- **Réponse `200`** :
```json
{
  "model_version": "referential-fucec-v1",
  "items": [
    {
      "code": "ACT_BAISSE_STOCK",
      "famille": "activite",
      "libelle": "Baisse visible des stocks ou de l'achalandage"
    },
    {
      "code": "ACT_CHANGEMENT",
      "famille": "activite",
      "libelle": "Changement d'activité non déclaré"
    },
    "... (10 autres elements - tronque pour lisibilite)"
  ]
}
```

### `POST /vision/par/recalcul`

**Recalcule et fige les snapshots PAR à une date.**

- **Rôles** : chef / cic
- **Paramètres** : `as_of` (date ISO, optionnel)
- **Réponse `200`** :
```json
{
  "as_of": "2026-09-14",
  "snapshots": [
    {
      "agency_id": 1,
      "as_of": "2026-09-14",
      "encours_brut": 3096502885.0,
      "restructured_amount": 0.0,
      "par1": 17.46,
      "par30": 10.42,
      "par90": 0.0
    },
    {
      "agency_id": 2,
      "as_of": "2026-09-14",
      "encours_brut": 545372130.0,
      "restructured_amount": 0.0,
      "par1": 100.0,
      "par30": 59.88,
      "par90": 0.0
    },
    "... (1 autres elements - tronque pour lisibilite)"
  ]
}
```

---

## M8 — Gestion du recouvrement

### `GET /vision/recouvrement`

**Dossiers de recouvrement ouverts, triés par niveau décroissant.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `limit` (1–500, défaut 100)
- **Réponse `200`** :
```json
{
  "module": "M7 recouvrement (calcule)",
  "dossiers": [
    {
      "membre_id": 42324,
      "niveau": 3,
      "action": "Relance VOL-0042312",
      "responsable": "Agent-4"
    },
    {
      "membre_id": 111624,
      "niveau": 3,
      "action": "Relance VOL-0111612",
      "responsable": "Agent-4"
    }
  ]
}
```

### `GET /vision/recouvrement/dossiers`

**Dossiers enrichis : encours, jours de retard, priorité P1–P3/S, action, responsable, journal de récupération.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `niveau` (1–4) · `priorite` (P1|P2|P3|S) · `limit` (1–500, défaut 100)
- **Réponse `200`** :
```json
{
  "as_of": "2026-09-14",
  "total": 0,
  "items": []
}
```

### `POST /vision/recouvrement/{case_id}/actions`

**Journalise une action de recouvrement (relance, promesse, récupération) et recalcule niveau/priorité. `404` si case inconnu, `409` si dossier clos.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `case_id` = id du dossier
- **Body attendu** :
```json
{
  "action_type": "relance",
  "note": "Appel client - promesse de paiement",
  "promise_on": "2026-09-20",
  "promise_kept": false,
  "amount_recovered": 0
}
```

- **Réponse `200`** :
```json
{
  "case_id": 3386,
  "level": 3,
  "priority": "P2",
  "status": "ouvert",
  "next_on": "2026-09-21",
  "recovered_amount": 1000.0,
  "journal": [
    {
      "date": "2026-09-14",
      "type": "relance",
      "note": "appel client",
      "montant": 1000.0
    },
    {
      "date": "2026-09-14",
      "type": "relance",
      "note": "Appel client - promesse de paiement",
      "montant": 0.0
    }
  ]
}
```

---

## ML consultatif (shadow — ne modifie jamais la décision)

### `GET /demandes/{id}/anomalies`

**Détection d'anomalies documentaires (z-score par variable, sévérité). `scope_excluded: true` pour les thin files.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "model_version": "anomaly-v3",
  "scope_excluded": false,
  "anomaly_score": 1.0,
  "anomalies": [
    {
      "feature": "garanties_sur_demande",
      "value": 0.7,
      "reference_value": null,
      "z_score": 32.5576,
      "severity": "a_verifier",
      "message": "Ecart inhabituel sur garanties sur demande (0.70)."
    },
    {
      "feature": "patrimoine_sur_fonds_propres",
      "value": 1.875,
      "reference_value": null,
      "z_score": -12.1397,
      "severity": "a_verifier",
      "message": "Ecart inhabituel sur patrimoine sur fonds propres (1.88)."
    },
    "... (1 autres elements - tronque pour lisibilite)"
  ]
}
```

### `POST /demandes/{id}/simuler`

**Simulation de résilience (Monte-Carlo) : `p_incident`, trajectoires p10/p50/p90, mois critique, mécanique explicite. Déterministe pour un `seed` donné. Scénarios : `normal`, `prudent`, `central`, `optimiste`, `choc`, `maladie`, `inflation`, `mauvaise_recolte`, `intrants_+20` (ou dict custom `{type, intensite}`).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Body attendu** :
```json
{
  "scenario": "normal",
  "montant": 400000,
  "duree_mois": 12,
  "horizon_mois": 6,
  "iterations": 500,
  "seed": 42
}
```

- **Réponse `200`** :
```json
{
  "application_id": 20034,
  "scenario": "normal",
  "scenario_libelle": "Trajectoire normale",
  "description": "Aucun choc : trajectoire sur la base du plan de trésorerie.",
  "mecanique": {
    "revenus": 1.0,
    "charges": 1.0
  },
  "model_version": "resilience-v2",
  "seed": 42,
  "p_incident": 0.058,
  "p10": [
    8846.35,
    56284.74,
    "... (4 autres elements - tronque pour lisibilite)"
  ],
  "p50": [
    63370.84,
    127338.33,
    "... (4 autres elements - tronque pour lisibilite)"
  ],
  "p90": [
    112432.92,
    204262.77,
    "... (4 autres elements - tronque pour lisibilite)"
  ],
  "mois_critique": null,
  "explication": "Trajectoire médiane positive sur tout l'horizon simulé.",
  "montant": 400000.0,
  "duree_mois": 12,
  "horizon_mois": 6,
  "iterations": 500
}
```

### `POST /demandes/{id}/simulation/enregistrer`

**Même calcul que `/simuler` mais persisté (snapshot relisible).**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Body attendu** :
```json
{
  "scenario": "mauvaise_recolte",
  "montant": 400000,
  "duree_mois": 12,
  "horizon_mois": 6,
  "iterations": 300,
  "seed": 7
}
```

- **Réponse `201`** :
```json
{
  "application_id": 20034,
  "scenario": "mauvaise_recolte",
  "scenario_libelle": "Mévente prolongée",
  "description": "Stress conventionnel : perte de 40 % des revenus d'activité sur toute la durée (sécheresse, mévente) et charges +10 % (intrants, transport). Niveau illustratif, non calibré.",
  "mecanique": {
    "charges": 1.1,
    "revenus": 0.6
  },
  "model_version": "resilience-v2",
  "seed": 7,
  "p_incident": 1.0,
  "p10": [
    -108709.71,
    -200162.6,
    "... (4 autres elements - tronque pour lisibilite)"
  ],
  "p50": [
    -74944.14,
    -155285.93,
    "... (4 autres elements - tronque pour lisibilite)"
  ],
  "p90": [
    -41609.28,
    -98291.51,
    "... (4 autres elements - tronque pour lisibilite)"
  ],
  "mois_critique": 1,
  "explication": "100 % des simulations ne couvrent pas l'échéance du mois 1.",
  "montant": 400000.0,
  "duree_mois": 12,
  "horizon_mois": 6,
  "iterations": 300,
  "id": 35,
  "created_at": "2026-09-14T15:17:03.203177+00:00"
}
```

### `GET /demandes/{id}/simulations`

**Snapshots de simulation enregistrés.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
[
  {
    "application_id": 20034,
    "scenario": "mauvaise_recolte",
    "scenario_libelle": "Mévente prolongée",
    "description": "Stress conventionnel : perte de 40 % des revenus d'activité sur toute la durée (sécheresse, mévente) et charges +10 % (intrants, transport). Niveau illustratif, non calibré.",
    "mecanique": {
      "charges": 1.1,
      "revenus": 0.6
    },
    "model_version": "resilience-v2",
    "seed": 7,
    "p_incident": 1.0,
    "p10": [
      -108709.71,
      -200162.6,
      "... (4 autres elements - tronque pour lisibilite)"
    ],
    "p50": [
      -74944.14,
      -155285.93,
      "... (4 autres elements - tronque pour lisibilite)"
    ],
    "p90": [
      -41609.28,
      -98291.51,
      "... (4 autres elements - tronque pour lisibilite)"
    ],
    "mois_critique": 1,
    "explication": "100 % des simulations ne couvrent pas l'échéance du mois 1.",
    "montant": 400000.0,
    "duree_mois": 12,
    "horizon_mois": 6,
    "iterations": 300,
    "id": 35,
    "created_at": "2026-09-14T15:17:03.203177+00:00"
  }
]
```

### `GET /portefeuille/alertes`

**Early warning portefeuille : membres à risque (p_par30_90j, exposition, signaux).**

- **Rôles** : chef / cic
- **Paramètres** : `limit` (1–100, défaut 20)
- **Réponse `200`** :
```json
{
  "model_version": "early-warning-v1",
  "items": [
    {
      "application_id": null,
      "member_code": "VOL-0003614",
      "p_par30_90j": 0.733,
      "exposure": 71239.0,
      "days_late": 48,
      "signals": [
        "Retard > 30 j",
        "Encours impayé",
        "... (1 autres elements - tronque pour lisibilite)"
      ],
      "explication": "Risque consultatif : revue recommandée."
    },
    {
      "application_id": null,
      "member_code": "VOL-0096418",
      "p_par30_90j": 0.733,
      "exposure": 282488.0,
      "days_late": 48,
      "signals": [
        "Retard > 30 j",
        "Encours impayé",
        "... (1 autres elements - tronque pour lisibilite)"
      ],
      "explication": "Risque consultatif : revue recommandée."
    },
    "... (1 autres elements - tronque pour lisibilite)"
  ]
}
```

### `GET /demandes/{id}/ml/scorecard`

**Scorecard v3 en shadow : probabilité de défaut indicative, niveau de risque, top facteurs. Jamais décisionnel.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "model_version": "scorecard-v3",
  "mode": "shadow",
  "probabilite_defaut": 0.0,
  "score_global_ml": 100.0,
  "niveau_risque": "faible",
  "regles_knockout": false,
  "top_factors": [
    {
      "feature": "max_jours_retard",
      "contribution": -2.041376
    },
    {
      "feature": "note_garanties",
      "contribution": 0.67919
    },
    "... (1 autres elements - tronque pour lisibilite)"
  ],
  "contributions": [
    {
      "feature": "max_jours_retard",
      "value": 0.0,
      "coefficient": 5.493842,
      "contribution": -2.041376
    },
    {
      "feature": "note_garanties",
      "value": 65.0,
      "coefficient": 0.184638,
      "contribution": 0.67919
    },
    "... (18 autres elements - tronque pour lisibilite)"
  ],
  "warning": "Volume synthetique : pipeline technique OK, pas un risque reel. Ne decide jamais."
}
```

### `GET /demandes/{id}/ml/plafond`

**Plafond ML indicatif (décote du plafond règles par facteur de prudence). `blocked_by_knockout` si knockout.**

- **Rôles** : agent / chef / cic
- **Paramètres** : `id` = id demande
- **Réponse `200`** :
```json
{
  "enabled": true,
  "blocked_by_knockout": false,
  "model_version": "scorecard-v3",
  "plafond_regles": 870000.0,
  "plafond_ml_recommande": 870000.0,
  "probabilite_defaut": 0.0,
  "facteur_prudence": 1.0,
  "explication": "Plafond ML indicatif : plafond règles réduit par une décote de 0 % liée au risque estimé."
}
```

---

## Exemples d'erreurs (réponses réelles)

### `401` — sans token
```json
{
  "detail": "Token Bearer requis"
}
```

### `403` — agent sur une route réservée (`/files/cic`)
```json
{
  "detail": "Role agent non autorise"
}
```

### `404` — demande inexistante
```json
{
  "detail": "Demande introuvable"
}
```

### `422` — validation (`page_size > 100`)
```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": [
        "query",
        "page_size"
      ],
      "msg": "Input should be less than or equal to 100",
      "input": "101",
      "ctx": {
        "le": 100
      }
    }
  ]
}
```

### `422` — montant négatif sur `POST /demandes`
```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": [
        "body",
        "montant_demande"
      ],
      "msg": "Input should be greater than 0",
      "input": -100,
      "ctx": {
        "gt": 0.0
      }
    }
  ]
}
```

### `400` — pièce avec qualité OCR insuffisante
```json
{
  "detail": "Qualite photo insuffisante : recommencer la prise"
}
```

---

## Notes pratiques pour le front

- **Un seul appel pour la fiche** : `GET /demandes/{id}` contient déjà le score courant, les ratios, les décisions et les pièces — pas besoin d'enchaîner 4 requêtes.
- **Afficher `montant_demande` vs `score.montant_eligible`** après `POST /analyser` (c'est le cœur du pitch DigiScore).
- **Les `message_code` / `message_humain`** expliquent le verdict — les afficher tels quels, ne pas les recoder.
- **Le ML est shadow** : à présenter comme « éclairage », jamais comme décision.
- **Scénarios de démo** : bon payeur (score ~84, approbation), dossier limite (zone analyse → CIC), knockout RCSD (refus avec motif d'override).
- Docs liées : [GUIDE_FRONTEND.md](GUIDE_FRONTEND.md) (mapping écrans → endpoints), Swagger `/docs`, [openapi.json](openapi.json).
