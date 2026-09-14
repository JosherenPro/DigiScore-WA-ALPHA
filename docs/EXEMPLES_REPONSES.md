# Exemples de corps de réponse — moteur de scoring et couche ML

Sorties **réelles** produites en rejouant les cas de démo à travers
`digiscore.pipeline.run()` et `digiscore.ml.run_ml_assistance()`.

- Commit : `5efdfa7`
- Régénérable : voir la section « Reproduire » en fin de document.
- Aucune donnée client : tous les dossiers sont synthétiques.

Ces corps correspondent à ce que renvoie `POST /demandes/{id}/analyser`
(`response_model=ScoreResult`). Les clés JSON sont en français, c'est le
contrat front.

---

## Vue d'ensemble

| Cas | Situation | `message_code` | `zone` | `eligible` | Score | Plafond (FCFA) |
|---|---|---|---|---|---:|---:|
| `MEM-001` | Bon payeur, demande dans le plafond | `UPSELL_POSSIBLE` | approbation | oui | 83.7 | 870 000 |
| `MEM-002` | Montant au-dela du plafond calcule | `MONTANT_PLAFONNE` | approbation | oui | 78.8 | 1 840 000 |
| `MEM-003` | Incident de remboursement grave | `INCIDENTS_RECENTS` | rejet | non | 79.7 | 0 |
| `MEM-004` | Thin-file bloque par le RCSD | `KNOCKOUT_RCSD` | rejet | non | 27.1 | 0 |
| `MEM-008` | Capacite de remboursement insuffisante | `KNOCKOUT_RCSD` | rejet | non | 67.7 | 0 |
| `MEM-009` | Montant exceptionnel, voie CIC | `VOIE_EXCEPTIONNELLE` | approbation | oui | 73.2 | 8 760 000 |
| `MEM-010` | Compte gele | `COMPTE_INACTIF` | rejet | non | 83.7 | 0 |
| `KO-ESG` | Activite exclue (ESG) | `KNOCKOUT_ESG` | rejet | non | 83.7 | 0 |
| `KO-CAUTION` | Cautionnaire eligible manquant | `CAUTION_REQUISE` | rejet | non | 63.9 | 0 |
| `KO-PREUVES` | Credits ailleurs sans justificatifs | `PREUVES_EXTERNES_MANQUANTES` | rejet | non | 74.2 | 0 |

---

## Corps complets — `POST /demandes/{id}/analyser`

### `MEM-001` — Bon payeur, demande dans le plafond

```json
{
  "eligible": true,
  "thin_file": false,
  "score_global": 83.7,
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
    {
      "code": "historique",
      "note": 82.0,
      "poids": 0.2,
      "contribution": 16.4
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 65.0,
      "poids": 0.1,
      "contribution": 6.5
    },
    {
      "code": "documents",
      "note": 84.0,
      "poids": 0.1,
      "contribution": 8.4
    }
  ],
  "knockouts": [],
  "montant_demande": 500000.0,
  "montant_eligible": 870000.0,
  "montant_max_suggestion": 870000.0,
  "message_code": "UPSELL_POSSIBLE",
  "message_humain": "Capacite estimee jusqu'a 870 000 FCFA (suggestion, non automatique).",
  "explication": [
    "Score 83.7/100 - zone approbation",
    "RCSD 2.633 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 870 000 FCFA"
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
    "situation_nette": 0,
    "nb_signaux": 0
  }
}
```

### `MEM-002` — Montant au-dela du plafond calcule

```json
{
  "eligible": true,
  "thin_file": false,
  "score_global": 78.8,
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
    {
      "code": "historique",
      "note": 72.0,
      "poids": 0.2,
      "contribution": 14.4
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 36.0,
      "poids": 0.1,
      "contribution": 3.6
    },
    {
      "code": "documents",
      "note": 84.0,
      "poids": 0.1,
      "contribution": 8.4
    }
  ],
  "knockouts": [],
  "montant_demande": 2900000.0,
  "montant_eligible": 1840000.0,
  "montant_max_suggestion": null,
  "message_code": "MONTANT_PLAFONNE",
  "message_humain": "Montant demande superieur au plafond : 1 840 000 FCFA proposes.",
  "explication": [
    "Score 78.8/100 - zone approbation",
    "RCSD 2.12 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 1 840 000 FCFA"
  ],
  "zone": "approbation",
  "financials": {
    "ebe": 1200000.0,
    "caf": 1340000.0,
    "rcsd": 2.12,
    "marge_brute_pct": 50.0,
    "benefice_net_pct": 11.11,
    "solvabilite": 4.0,
    "rotation_stocks_jours": 60.8,
    "participation_pct": 53.33,
    "fonds_roulement_pct": 280.0,
    "nb_ratios_degrades": 0,
    "mois_critique": null,
    "situation_nette": 0,
    "nb_signaux": 0
  }
}
```

### `MEM-003` — Incident de remboursement grave

> Knockout : INCIDENTS_RECENTS — `montant_eligible` forcé à 0 et `eligible: false`.

```json
{
  "eligible": false,
  "thin_file": false,
  "score_global": 79.7,
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
    {
      "code": "historique",
      "note": 62.0,
      "poids": 0.2,
      "contribution": 12.4
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 65.0,
      "poids": 0.1,
      "contribution": 6.5
    },
    {
      "code": "documents",
      "note": 84.0,
      "poids": 0.1,
      "contribution": 8.4
    }
  ],
  "knockouts": [
    {
      "code": "INCIDENTS_RECENTS",
      "detail": "1 incident(s) grave(s)"
    }
  ],
  "montant_demande": 500000.0,
  "montant_eligible": 0.0,
  "montant_max_suggestion": null,
  "message_code": "INCIDENTS_RECENTS",
  "message_humain": "Comportement de remboursement non conforme.",
  "explication": [
    "Score 79.7/100 - zone rejet",
    "RCSD 2.633 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 0 FCFA"
  ],
  "zone": "rejet",
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
    "situation_nette": 0,
    "nb_signaux": 0
  }
}
```

### `MEM-004` — Thin-file bloque par le RCSD

> Knockout : KNOCKOUT_RCSD — `montant_eligible` forcé à 0 et `eligible: false`.

```json
{
  "eligible": false,
  "thin_file": true,
  "score_global": 27.1,
  "criteres": [
    {
      "code": "financier",
      "note": 6.0,
      "poids": 0.25,
      "contribution": 1.5
    },
    {
      "code": "capacite",
      "note": 15.0,
      "poids": 0.2,
      "contribution": 3.0
    },
    {
      "code": "historique",
      "note": 25.0,
      "poids": 0.2,
      "contribution": 5.0
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 30.0,
      "poids": 0.1,
      "contribution": 3.0
    },
    {
      "code": "documents",
      "note": 48.0,
      "poids": 0.1,
      "contribution": 4.8
    }
  ],
  "knockouts": [
    {
      "code": "KNOCKOUT_RCSD",
      "detail": "RCSD=0.379"
    }
  ],
  "montant_demande": 400000.0,
  "montant_eligible": 0.0,
  "montant_max_suggestion": null,
  "message_code": "KNOCKOUT_RCSD",
  "message_humain": "RCSD inferieur a 1 : capacite de remboursement insuffisante.",
  "explication": [
    "Score 27.1/100 - zone rejet",
    "RCSD 0.379 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 0 FCFA",
    "Profil thin-file : historique institutionnel leger"
  ],
  "zone": "rejet",
  "financials": {
    "ebe": 200000.0,
    "caf": 230000.0,
    "rcsd": 0.379,
    "marge_brute_pct": 44.44,
    "benefice_net_pct": 4.44,
    "solvabilite": 0.625,
    "rotation_stocks_jours": 29.2,
    "participation_pct": 25.0,
    "fonds_roulement_pct": 133.33,
    "nb_ratios_degrades": 3,
    "mois_critique": null,
    "situation_nette": 40000.0,
    "nb_signaux": 0
  }
}
```

### `MEM-008` — Capacite de remboursement insuffisante

> Knockout : KNOCKOUT_RCSD — `montant_eligible` forcé à 0 et `eligible: false`.

```json
{
  "eligible": false,
  "thin_file": false,
  "score_global": 67.7,
  "criteres": [
    {
      "code": "financier",
      "note": 100.0,
      "poids": 0.25,
      "contribution": 25.0
    },
    {
      "code": "capacite",
      "note": 15.0,
      "poids": 0.2,
      "contribution": 3.0
    },
    {
      "code": "historique",
      "note": 82.0,
      "poids": 0.2,
      "contribution": 16.4
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 51.9,
      "poids": 0.1,
      "contribution": 5.19
    },
    {
      "code": "documents",
      "note": 84.0,
      "poids": 0.1,
      "contribution": 8.4
    }
  ],
  "knockouts": [
    {
      "code": "KNOCKOUT_RCSD",
      "detail": "RCSD=0.111"
    }
  ],
  "montant_demande": 800000.0,
  "montant_eligible": 0.0,
  "montant_max_suggestion": null,
  "message_code": "KNOCKOUT_RCSD",
  "message_humain": "RCSD inferieur a 1 : capacite de remboursement insuffisante.",
  "explication": [
    "Score 67.7/100 - zone rejet",
    "RCSD 0.111 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 0 FCFA"
  ],
  "zone": "rejet",
  "financials": {
    "ebe": -50000.0,
    "caf": 90000.0,
    "rcsd": 0.111,
    "marge_brute_pct": 31.25,
    "benefice_net_pct": 50.0,
    "solvabilite": 4.0,
    "rotation_stocks_jours": 199.1,
    "participation_pct": 53.33,
    "fonds_roulement_pct": 280.0,
    "nb_ratios_degrades": 0,
    "mois_critique": null,
    "situation_nette": 0,
    "nb_signaux": 0
  }
}
```

### `MEM-009` — Montant exceptionnel, voie CIC

```json
{
  "eligible": true,
  "thin_file": false,
  "score_global": 73.2,
  "criteres": [
    {
      "code": "financier",
      "note": 100.0,
      "poids": 0.25,
      "contribution": 25.0
    },
    {
      "code": "capacite",
      "note": 45.0,
      "poids": 0.2,
      "contribution": 9.0
    },
    {
      "code": "historique",
      "note": 82.0,
      "poids": 0.2,
      "contribution": 16.4
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 46.8,
      "poids": 0.1,
      "contribution": 4.68
    },
    {
      "code": "documents",
      "note": 84.0,
      "poids": 0.1,
      "contribution": 8.4
    }
  ],
  "knockouts": [],
  "montant_demande": 10000000.0,
  "montant_eligible": 8760000.0,
  "montant_max_suggestion": null,
  "message_code": "VOIE_EXCEPTIONNELLE",
  "message_humain": "Montant exceptionnel : passage CIC + garanties renforcees.",
  "explication": [
    "Score 73.2/100 - zone approbation",
    "RCSD 1.475 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 8 760 000 FCFA"
  ],
  "zone": "approbation",
  "financials": {
    "ebe": 7500000.0,
    "caf": 7640000.0,
    "rcsd": 1.475,
    "marge_brute_pct": 55.56,
    "benefice_net_pct": 2.22,
    "solvabilite": 4.0,
    "rotation_stocks_jours": 13.7,
    "participation_pct": 53.33,
    "fonds_roulement_pct": 280.0,
    "nb_ratios_degrades": 0,
    "mois_critique": null,
    "situation_nette": 0,
    "nb_signaux": 0
  }
}
```

### `MEM-010` — Compte gele

> Knockout : COMPTE_INACTIF — `montant_eligible` forcé à 0 et `eligible: false`.

```json
{
  "eligible": false,
  "thin_file": false,
  "score_global": 83.7,
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
    {
      "code": "historique",
      "note": 82.0,
      "poids": 0.2,
      "contribution": 16.4
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 65.0,
      "poids": 0.1,
      "contribution": 6.5
    },
    {
      "code": "documents",
      "note": 84.0,
      "poids": 0.1,
      "contribution": 8.4
    }
  ],
  "knockouts": [
    {
      "code": "COMPTE_INACTIF",
      "detail": "Membre ou statut non actif"
    }
  ],
  "montant_demande": 500000.0,
  "montant_eligible": 0.0,
  "montant_max_suggestion": null,
  "message_code": "COMPTE_INACTIF",
  "message_humain": "Compte gele ou inactif : aucune demande possible.",
  "explication": [
    "Score 83.7/100 - zone rejet",
    "RCSD 2.633 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 0 FCFA"
  ],
  "zone": "rejet",
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
    "situation_nette": 0,
    "nb_signaux": 0
  }
}
```

### `KO-ESG` — Activite exclue (ESG)

> Knockout : KNOCKOUT_ESG — `montant_eligible` forcé à 0 et `eligible: false`.

```json
{
  "eligible": false,
  "thin_file": false,
  "score_global": 83.7,
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
    {
      "code": "historique",
      "note": 82.0,
      "poids": 0.2,
      "contribution": 16.4
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 65.0,
      "poids": 0.1,
      "contribution": 6.5
    },
    {
      "code": "documents",
      "note": 84.0,
      "poids": 0.1,
      "contribution": 8.4
    }
  ],
  "knockouts": [
    {
      "code": "KNOCKOUT_ESG",
      "detail": "Exclusion ESG"
    }
  ],
  "montant_demande": 500000.0,
  "montant_eligible": 0.0,
  "montant_max_suggestion": null,
  "message_code": "KNOCKOUT_ESG",
  "message_humain": "Activite exclue (ESG) : rejet immediat.",
  "explication": [
    "Score 83.7/100 - zone rejet",
    "RCSD 2.633 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 0 FCFA"
  ],
  "zone": "rejet",
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
    "situation_nette": 0,
    "nb_signaux": 0
  }
}
```

### `KO-CAUTION` — Cautionnaire eligible manquant

> Knockout : CAUTION_REQUISE, KNOCKOUT_RCSD — `montant_eligible` forcé à 0 et `eligible: false`.

```json
{
  "eligible": false,
  "thin_file": false,
  "score_global": 63.9,
  "criteres": [
    {
      "code": "financier",
      "note": 100.0,
      "poids": 0.25,
      "contribution": 25.0
    },
    {
      "code": "capacite",
      "note": 15.0,
      "poids": 0.2,
      "contribution": 3.0
    },
    {
      "code": "historique",
      "note": 82.0,
      "poids": 0.2,
      "contribution": 16.4
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 13.8,
      "poids": 0.1,
      "contribution": 1.38
    },
    {
      "code": "documents",
      "note": 84.0,
      "poids": 0.1,
      "contribution": 8.4
    }
  ],
  "knockouts": [
    {
      "code": "CAUTION_REQUISE",
      "detail": "Cautionnaire eligible manquant"
    },
    {
      "code": "KNOCKOUT_RCSD",
      "detail": "RCSD=0.658"
    }
  ],
  "montant_demande": 2000000.0,
  "montant_eligible": 0.0,
  "montant_max_suggestion": null,
  "message_code": "CAUTION_REQUISE",
  "message_humain": "Montant au-dela du seuil : cautionnaire eligible obligatoire.",
  "explication": [
    "Score 63.9/100 - zone rejet",
    "RCSD 0.658 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 0 FCFA"
  ],
  "zone": "rejet",
  "financials": {
    "ebe": 1200000.0,
    "caf": 1340000.0,
    "rcsd": 0.658,
    "marge_brute_pct": 50.0,
    "benefice_net_pct": 11.11,
    "solvabilite": 4.0,
    "rotation_stocks_jours": 60.8,
    "participation_pct": 53.33,
    "fonds_roulement_pct": 280.0,
    "nb_ratios_degrades": 0,
    "mois_critique": null,
    "situation_nette": 0,
    "nb_signaux": 0
  }
}
```

### `KO-PREUVES` — Credits ailleurs sans justificatifs

> Knockout : PREUVES_EXTERNES_MANQUANTES — `montant_eligible` forcé à 0 et `eligible: false`.

```json
{
  "eligible": false,
  "thin_file": false,
  "score_global": 74.2,
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
    {
      "code": "historique",
      "note": 50.0,
      "poids": 0.2,
      "contribution": 10.0
    },
    {
      "code": "activite",
      "note": 65.0,
      "poids": 0.15,
      "contribution": 9.75
    },
    {
      "code": "garanties",
      "note": 65.0,
      "poids": 0.1,
      "contribution": 6.5
    },
    {
      "code": "documents",
      "note": 54.0,
      "poids": 0.1,
      "contribution": 5.4
    }
  ],
  "knockouts": [
    {
      "code": "PREUVES_EXTERNES_MANQUANTES",
      "detail": "Pieces externes exigibles absentes"
    }
  ],
  "montant_demande": 500000.0,
  "montant_eligible": 0.0,
  "montant_max_suggestion": null,
  "message_code": "PREUVES_EXTERNES_MANQUANTES",
  "message_humain": "Credits ailleurs declares sans pieces justificatives : refus.",
  "explication": [
    "Score 74.2/100 - zone rejet",
    "RCSD 2.633 (norme >= 1,50 ; knockout < 1)",
    "Plafond estime 0 FCFA"
  ],
  "zone": "rejet",
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
    "situation_nette": 0,
    "nb_signaux": 0
  }
}
```

---

## Couche ML — `run_ml_assistance()`

Consultatif. Ces champs **ne modifient jamais** `eligible`, `montant_eligible`,
`zone`, `message_code` ni les knockouts.

### Contrat quand le ML est désactivé (`ML_ENABLED=0`, défaut)

Les clés sont **identiques** à l'état actif, seules les valeurs sont nulles —
un consommateur n'a jamais de `KeyError`.

```json
{
  "enabled": false,
  "modele": null,
  "probabilite_defaut": null,
  "anomalies": [],
  "anomaly_score": null,
  "anomaly_scope_excluded": false,
  "plafond_ml": null
}
```

### `MEM-001` (bon payeur) — ML actif

```json
{
  "enabled": true,
  "modele": {
    "version": "scorecard-v2",
    "type": "logreg",
    "methode_explication": "contributions_logit",
    "score_global_ml": 98.6,
    "contributions": [
      {
        "feature": "rcsd",
        "value": 2.633,
        "coefficient": -0.57595,
        "contribution": -1.250782
      },
      {
        "feature": "montant_sur_plafond",
        "value": 0.1667,
        "coefficient": 0.229526,
        "contribution": -0.494538
      },
      {
        "feature": "anciennete_mois",
        "value": 48.0,
        "coefficient": -0.167301,
        "contribution": -0.25648
      },
      {
        "feature": "epargne_regularite",
        "value": 100.0,
        "coefficient": -0.146717,
        "contribution": -0.234502
      },
      {
        "feature": "incidents_graves",
        "value": 0.0,
        "coefficient": 0.379975,
        "contribution": -0.166698
      },
      {
        "feature": "note_financier",
        "value": 100.0,
        "coefficient": -0.062168,
        "contribution": -0.133926
      },
      {
        "feature": "note_documents",
        "value": 84.0,
        "coefficient": -0.06101,
        "contribution": -0.07548
      },
      {
        "feature": "note_historique",
        "value": 82.0,
        "coefficient": -0.057846,
        "contribution": -0.064556
      },
      {
        "feature": "note_capacite",
        "value": 88.0,
        "coefficient": -0.035814,
        "contribution": -0.052443
      },
      {
        "feature": "note_garanties",
        "value": 65.0,
        "coefficient": -0.050629,
        "contribution": -0.008748
      },
      {
        "feature": "note_activite",
        "value": 65.0,
        "coefficient": -0.004771,
        "contribution": -0.000912
      }
    ]
  },
  "probabilite_defaut": 0.013598,
  "anomalies": [
    {
      "feature": "solde_sur_revenu_mensuel",
      "z_score": 2.7153,
      "message": "Ecart inhabituel sur solde sur revenu mensuel (1.33)."
    },
    {
      "feature": "rcsd",
      "z_score": 2.6805,
      "message": "RCSD atypique (2.63) par rapport aux dossiers de reference."
    },
    {
      "feature": "log_revenus_sur_epargne",
      "z_score": -1.7632,
      "message": "Revenus declares 9.5x superieurs a l'epargne moyenne observee."
    }
  ],
  "anomaly_score": 0.57966,
  "anomaly_scope_excluded": false,
  "plafond_ml": {
    "enabled": true,
    "blocked_by_knockout": false,
    "model_version": "scorecard-v2",
    "plafond_regles": 870000.0,
    "plafond_ml_recommande": 870000,
    "probabilite_defaut": 0.013598,
    "facteur_prudence": 1.0,
    "explication": "Plafond ML indicatif : plafond règles réduit par une décote de 0 % liée au risque estimé."
  }
}
```

### `MEM-004` (thin-file) — ML actif

```json
{
  "enabled": true,
  "modele": {
    "version": "scorecard-v2",
    "type": "logreg",
    "methode_explication": "contributions_logit",
    "score_global_ml": 63.7,
    "contributions": [
      {
        "feature": "rcsd",
        "value": 0.379,
        "coefficient": -0.57595,
        "contribution": 1.127879
      },
      {
        "feature": "montant_sur_plafond",
        "value": 0.1333,
        "coefficient": 0.229526,
        "contribution": -0.526554
      },
      {
        "feature": "anciennete_mois",
        "value": 2.0,
        "coefficient": -0.167301,
        "contribution": 0.236296
      },
      {
        "feature": "epargne_regularite",
        "value": 100.0,
        "coefficient": -0.146717,
        "contribution": -0.234502
      },
      {
        "feature": "note_financier",
        "value": 6.0,
        "coefficient": -0.062168,
        "contribution": 0.194116
      },
      {
        "feature": "incidents_graves",
        "value": 0.0,
        "coefficient": 0.379975,
        "contribution": -0.166698
      },
      {
        "feature": "note_historique",
        "value": 25.0,
        "coefficient": -0.057846,
        "contribution": 0.120849
      },
      {
        "feature": "note_capacite",
        "value": 15.0,
        "coefficient": -0.035814,
        "contribution": 0.095448
      },
      {
        "feature": "note_garanties",
        "value": 30.0,
        "coefficient": -0.050629,
        "contribution": 0.090548
      },
      {
        "feature": "note_documents",
        "value": 48.0,
        "coefficient": -0.06101,
        "contribution": 0.047694
      },
      {
        "feature": "note_activite",
        "value": 65.0,
        "coefficient": -0.004771,
        "contribution": -0.000912
      }
    ]
  },
  "probabilite_defaut": 0.363329,
  "anomalies": [],
  "anomaly_score": 0.0,
  "anomaly_scope_excluded": true,
  "plafond_ml": {
    "enabled": true,
    "blocked_by_knockout": true,
    "model_version": "scorecard-v2",
    "plafond_regles": 0.0,
    "plafond_ml_recommande": null,
    "probabilite_defaut": 0.363329,
    "facteur_prudence": null,
    "explication": "Aucune recommandation ML : un knockout métier bloque le dossier."
  }
}
```

### `MEM-010` (compte gelé) — ML actif

```json
{
  "enabled": true,
  "modele": {
    "version": "scorecard-v2",
    "type": "logreg",
    "methode_explication": "contributions_logit",
    "score_global_ml": 98.9,
    "contributions": [
      {
        "feature": "rcsd",
        "value": 2.633,
        "coefficient": -0.57595,
        "contribution": -1.250782
      },
      {
        "feature": "montant_sur_plafond",
        "value": 0.1667,
        "coefficient": 0.229526,
        "contribution": -0.494538
      },
      {
        "feature": "anciennete_mois",
        "value": 70.0,
        "coefficient": -0.167301,
        "contribution": -0.492155
      },
      {
        "feature": "epargne_regularite",
        "value": 100.0,
        "coefficient": -0.146717,
        "contribution": -0.234502
      },
      {
        "feature": "incidents_graves",
        "value": 0.0,
        "coefficient": 0.379975,
        "contribution": -0.166698
      },
      {
        "feature": "note_financier",
        "value": 100.0,
        "coefficient": -0.062168,
        "contribution": -0.133926
      },
      {
        "feature": "note_documents",
        "value": 84.0,
        "coefficient": -0.06101,
        "contribution": -0.07548
      },
      {
        "feature": "note_historique",
        "value": 82.0,
        "coefficient": -0.057846,
        "contribution": -0.064556
      },
      {
        "feature": "note_capacite",
        "value": 88.0,
        "coefficient": -0.035814,
        "contribution": -0.052443
      },
      {
        "feature": "note_garanties",
        "value": 65.0,
        "coefficient": -0.050629,
        "contribution": -0.008748
      },
      {
        "feature": "note_activite",
        "value": 65.0,
        "coefficient": -0.004771,
        "contribution": -0.000912
      }
    ]
  },
  "probabilite_defaut": 0.010773,
  "anomalies": [
    {
      "feature": "solde_sur_revenu_mensuel",
      "z_score": 2.7153,
      "message": "Ecart inhabituel sur solde sur revenu mensuel (1.33)."
    },
    {
      "feature": "rcsd",
      "z_score": 2.6805,
      "message": "RCSD atypique (2.63) par rapport aux dossiers de reference."
    },
    {
      "feature": "log_revenus_sur_epargne",
      "z_score": -1.7632,
      "message": "Revenus declares 9.5x superieurs a l'epargne moyenne observee."
    }
  ],
  "anomaly_score": 0.57966,
  "anomaly_scope_excluded": false,
  "plafond_ml": {
    "enabled": true,
    "blocked_by_knockout": true,
    "model_version": "scorecard-v2",
    "plafond_regles": 0.0,
    "plafond_ml_recommande": null,
    "probabilite_defaut": 0.010773,
    "facteur_prudence": null,
    "explication": "Aucune recommandation ML : un knockout métier bloque le dossier."
  }
}
```

---

## Simulateur de résilience — `simulate_resilience()`

Déterministe : même dossier + même `seed` ⇒ réponse strictement identique.

### Scénario normal

```json
{
  "model_version": "resilience-v2",
  "seed": 72,
  "scenario": {
    "type": "normal",
    "intensite": 0.0
  },
  "montant": 500000.0,
  "duree_mois": 12,
  "trajectories": 2000,
  "p_incident": 0.023,
  "trajectoires": {
    "p10": [
      27303.61,
      83968.09,
      147007.74,
      208464.93,
      274287.03,
      343605.6,
      413026.91,
      481633.03,
      550293.42,
      620494.74,
      690844.25,
      760914.61
    ],
    "p50": [
      77709.66,
      154415.88,
      231010.53,
      311359.84,
      389134.94,
      468600.1,
      545527.31,
      623030.89,
      704223.91,
      778652.29,
      856153.28,
      933710.42
    ],
    "p90": [
      126759.14,
      223384.41,
      319833.39,
      410774.4,
      498102.44,
      591930.7,
      678148.38,
      765896.03,
      856638.75,
      939919.77,
      1021442.37,
      1109273.25
    ]
  },
  "mois_critique": null
}
```

### Choc de revenus −40 %

```json
{
  "model_version": "resilience-v2",
  "seed": 72,
  "scenario": {
    "type": "choc",
    "intensite": -0.4
  },
  "montant": 500000.0,
  "duree_mois": 12,
  "trajectories": 2000,
  "p_incident": 1.0,
  "trajectoires": {
    "p10": [
      -94858.07,
      -170751.41,
      -240583.92,
      -311742.91,
      -379767.33,
      -447191.28,
      -512015.34,
      -581782.82,
      -647252.53,
      -710913.92,
      -775175.67,
      -838892.65
    ],
    "p50": [
      -60530.9,
      -121287.59,
      -182690.89,
      -240935.78,
      -301728.12,
      -360989.48,
      -422165.09,
      -480678.36,
      -539876.21,
      -599584.13,
      -662696.39,
      -723536.75
    ],
    "p90": [
      -26686.29,
      -73513.25,
      -119977.12,
      -173265.03,
      -225977.62,
      -277346.06,
      -330697.41,
      -382357.32,
      -435128.82,
      -488927.52,
      -547590.63,
      -601349.18
    ]
  },
  "mois_critique": 1
}
```

### Maladie du chef de ménage

```json
{
  "model_version": "resilience-v2",
  "seed": 72,
  "scenario": {
    "type": "maladie",
    "intensite": 0.0
  },
  "montant": 500000.0,
  "duree_mois": 12,
  "trajectories": 2000,
  "p_incident": 1.0,
  "trajectoires": {
    "p10": [
      -91223.88,
      -162057.82,
      -226866.13,
      -292481.05,
      -354941.27,
      -418126.46,
      -476077.47,
      -540626.44,
      -600475.53,
      -658587.72,
      -716911.69,
      -776409.28
    ],
    "p50": [
      -54692.95,
      -109242.0,
      -164537.22,
      -216506.36,
      -271591.51,
      -324743.69,
      -380208.3,
      -432538.17,
      -485683.47,
      -539313.57,
      -595819.19,
      -651706.23
    ],
    "p90": [
      -18233.17,
      -58631.81,
      -97889.45,
      -144300.41,
      -190976.71,
      -234910.18,
      -281646.38,
      -326345.85,
      -372541.99,
      -421554.68,
      -473676.19,
      -520366.32
    ]
  },
  "mois_critique": 1
}
```

---

## Contrefactuels — `suggest_counterfactuals()`

Leviers minimaux pour atteindre un score cible. **Ne lève jamais un knockout.**

### Dossier sans knockout, sous la cible

```json
{
  "blocked_by_knockout": false,
  "base_score": 70.2,
  "items": [
    {
      "levier": "epargne_moy_6m",
      "unite": "FCFA",
      "variation_min": 240000.0,
      "nouvelle_valeur": 300000.0,
      "nouveau_score": 72.2,
      "nouveau_plafond": 870000.0,
      "message": "MONTANT_OK"
    },
    {
      "levier": "valeur_garanties",
      "unite": "FCFA",
      "variation_min": 50000.0,
      "nouvelle_valeur": 100000.0,
      "nouveau_score": 71.0,
      "nouveau_plafond": 870000.0,
      "message": "MONTANT_OK"
    },
    {
      "levier": "anciennete_mois",
      "unite": "mois",
      "variation_min": 26.0,
      "nouvelle_valeur": 36.0,
      "nouveau_score": 72.2,
      "nouveau_plafond": 870000.0,
      "message": "MONTANT_OK"
    }
  ]
}
```

### Dossier avec knockout — réponse bloquée

```json
{
  "blocked_by_knockout": true,
  "knockouts": [
    {
      "code": "KNOCKOUT_RCSD",
      "detail": "RCSD=0.379"
    }
  ],
  "base_score": 27.1,
  "items": []
}
```

---

## Reproduire

```bash
python3 -m pytest -q          # suite complète
python3 scripts/gen_exemples_reponses.py > docs/EXEMPLES_REPONSES.md
```

Le script est volontairement sans dépendance à la base : il construit les
dossiers en mémoire et n'appelle que le package `scoring/`.
