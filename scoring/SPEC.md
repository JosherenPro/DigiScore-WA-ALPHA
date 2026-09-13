# SPEC moteur DigiScore-WA

Fonction pure : `digiscore.pipeline.run(dossier) ? ScoreResult`. Pas d’accès BDD. Pas de ML dans le routage, les knock-outs ou la décision.

## Entrée (`DossierInput`)

```text
membre: { id, anciennete_mois, statut }
compte: { solde, date_ouverture_jours, statut }
historique: { credits_passes[], incidents[], epargne_moy_3m, epargne_moy_6m,
              nb_mouvements_90j, credits_ailleurs, preuves_externes_ok }
demande: { montant, duree_mois, objet, produit_id, plafond_produit, seuil_caution,
           exceptionnel, situation_fiscale, exclusion_esg, nb_cautions_eligibles, nb_cautions_min }
analyse: { CA, CMV, charges, revenus/charges ménage, ratios bruts, tresorerie[],
           patrimoine, preuves N1–N3 }
```

## Sortie (`ScoreResult`)

`eligible`, `thin_file`, `score_global` (0–100), `criteres[]`, `knockouts[]`,
`montant_demande`, `montant_eligible`, `montant_max_suggestion`,
`message_code`, `message_humain`, `explication[]`, `zone`, `financials`.

## Formules

```text
EBE  = CA ? CMV ? Charges_exploitation
CAF  = EBE + Produits_financiers + (Revenus_perso ? Charges_familiales)
RCSD = CAF / (Dettes_en_cours + Service_credit_sollicite)
```

RCSD ? 1,50 confort · RCSD < 1,00 knock-out.

Score : `? (note_i/100) × poids_i × 100`  
Poids : financier 25 · capacité 20 · historique 20 · activité 15 · garanties 10 · documents 10.

Zones : 0–40 rejet reco · 41–70 analyse/CIC · 71–100 approbation reco.

## Thin-file

Ancienneté < 3 mois **ou** (0 crédit soldé **et** épargne/mouvements faibles).

## Plafond

```text
montant_eligible = min(plafond_produit, f(épargne, CAF, historique), capacité RCSD)
```

Thin-file : micro-plafond (épargne × 3, cap 250 000). Score < 40 : ×0,4. Zone grise : ×0,75.

## Messages

`NON_MEMBRE`, `COMPTE_INACTIF`, `HISTORIQUE_INSUFFISANT`, `EPARGNE_SOUS_SEUIL`,
`INCIDENTS_RECENTS`, `MONTANT_PLAFONNE`, `MONTANT_OK`, `UPSELL_POSSIBLE`,
`VOIE_EXCEPTIONNELLE`, `REJET_SCORE`, `CAUTION_REQUISE`, `BIC_OU_FISCAL_MANQUANT`,
`PREUVES_EXTERNES_MANQUANTES`, `KNOCKOUT_RCSD`, `KNOCKOUT_ESG`.

## Pipeline

Garde-fous ? financials ? thin-file ? scorecard ? knock-outs ? plafond ? messages.
