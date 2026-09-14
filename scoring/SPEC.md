# SPEC moteur DigiScore-WA

Fonction pure : `digiscore.pipeline.run(dossier) -> ScoreResult`. Le package n'accède ni à la BDD ni au réseau. Le ML est hors routage, knock-outs et décision MVP.

## Contrat

**Entrée `DossierInput`** :

```text
membre: { id, anciennete_mois, statut }
compte: { solde, date_ouverture_jours, statut }
historique: { credits_passes[], incidents[], epargne_moy_3m, epargne_moy_6m,
              nb_mouvements_90j, credits_ailleurs, preuves_externes_ok }
demande: { montant, duree_mois, objet, produit_id, plafond_produit, seuil_caution,
           exceptionnel, situation_fiscale, exclusion_esg, nb_cautions_eligibles, nb_cautions_min }
analyse: { ca, cmv, charges_exploitation, revenus/charges ménage, trésorerie[],
           patrimoine, preuves N1–N3 }
```

**Sortie `ScoreResult`** : `eligible`, `thin_file`, `score_global` (0–100), `criteres[]`, `knockouts[]`, `montant_demande`, `montant_eligible`, `montant_max_suggestion`, `message_code`, `message_humain`, `explication[]`, `zone`, `financials`.

Les champs et `message_code` sont un contrat avec le backend et le frontend : aucun renommage sans coordination.

## Calculs et zones

```text
EBE  = CA − CMV − charges_exploitation
CAF  = EBE + produits_financiers + (revenu_perso − charge_familiale)
RCSD = CAF / (charge_credits_en_cours + service_credit_sollicite)
```

Le service demandé est annualisé avec un taux simple indicatif de 1,8 %/an. RCSD < 1,00 est un knockout ; RCSD ≥ 1,50 est le seuil de confort utilisé pour le plafond.

Le score est la somme pondérée des notes /100 : financier 25 %, capacité 20 %, historique 20 %, activité 15 %, garanties 10 %, documents 10 %. Les zones sont : 0–40 rejet recommandé, 41–70 analyse/CIC, 71–100 approbation recommandée.

## Garde-fous et plafond

Les knock-outs sont évalués avant le résultat métier : compte/membre inactif, ESG, preuves externes manquantes, fiscalité/BIC, caution, RCSD et incidents graves. Leur priorité suit cet ordre. Un knockout impose `eligible=false`, `zone="rejet"`, `montant_eligible=0` et aucune suggestion.

Un thin-file est un membre de moins de 3 mois, ou sans crédit soldé avec épargne 6 mois < 80 000 FCFA et moins de 3 mouvements sur 90 jours.

```text
montant_eligible = min(plafond_produit, capacité épargne + CAF + historique, capacité RCSD)
```
corrige
La capacité RCSD retire d'abord le service des dettes existantes. Thin-file : min(épargne × 3, 250 000 FCFA), avec un plancher de 50 000 FCFA. Score < 40 : ×0,40 ; zone grise : ×0,75. Le montant est arrondi vers le bas à 10 000 FCFA. Une suggestion n'est produite que pour score ≥ 80, profil non thin-file et capacité au moins 15 % supérieure à la demande. À partir de 8 000 000 FCFA, ou si le produit est exceptionnel, le code est `VOIE_EXCEPTIONNELLE` et la décision reste humaine/CIC.

## Messages et exécution

Codes supportés : `NON_MEMBRE`, `COMPTE_INACTIF`, `HISTORIQUE_INSUFFISANT`, `EPARGNE_SOUS_SEUIL`, `INCIDENTS_RECENTS`, `MONTANT_PLAFONNE`, `MONTANT_OK`, `UPSELL_POSSIBLE`, `VOIE_EXCEPTIONNELLE`, `REJET_SCORE`, `CAUTION_REQUISE`, `BIC_OU_FISCAL_MANQUANT`, `PREUVES_EXTERNES_MANQUANTES`, `KNOCKOUT_RCSD`, `KNOCKOUT_ESG`.

Depuis la racine : `pip install -r requirements.txt && pytest scoring/tests`. Depuis `scoring/` : `pytest`.
