# Identifiants EN — notes FR

Les **noms de tables et colonnes** sont en anglais. Les **COMMENT ON** (psql `\d+`) et ce fichier restent en français.

Les **codes métier** (statuts, gravité, rôles, N1/N2/N3) restent ceux du moteur / de l’API pour ne pas casser scoring et front.

| Table EN | Ancien nom | Rôle |
|----------|------------|------|
| `agency` | agence | Agence / topologie shared\|split |
| `credit_product` | produit_credit | Produits + seuil caution |
| `app_user` | utilisateur | agent / chef_agence / cic |
| `member` | membre | `external_code` = NUM_CLIENT |
| `account` | compte | Compte épargne / opérations |
| `account_movement` | mouvement_compte | N derniers mouvements |
| `savings_snapshot` | epargne_snapshot | Soldes moy. 3/6/12 mois |
| `past_credit` | credit_passe | Historique crédits |
| `incident` | incident | Incidents / contentieux |
| `member_guarantee` | garantie_membre | Garanties matérielles |
| `credit_application` | demande_credit | Demande du jour |
| `household` | menage | Collecte A |
| `activity` | activite | Collecte B |
| `economic_model` | modele_economique | Collecte C |
| `market` | marche | Collecte D |
| `income_expense` | revenu_charge | Collecte E (CA=`revenue`, CMV=`cogs`) |
| `wealth` | patrimoine | Patrimoine + 5 signaux |
| `monthly_cashflow` | tresorerie_mensuelle | Trésorerie 12 mois |
| `application_guarantee` | garantie_demande | Garanties dossier |
| `financial_ratio` | ratio_financier | EBE, CAF, RCSD, 6 ratios |
| `bic_consent` | consentement_bic | Consentement + scan |
| `bic_report` | rapport_bic | Endettement ailleurs |
| `supporting_document` | piece_justificative | Pièces + qualité OCR |
| `guarantor` | cautionnaire | Cautionnaire |
| `application_guarantor` | demande_caution | Lien demande ↔ caution |
| `guarantor_review` | evaluation_cautionnaire | Capacité de relais |
| `score_result` | score_resultat | Score / plafond / message |
| `amortization_line` | tableau_amortissement | Échéancier |
| `decision` | decision | Avis 3 niveaux |
| `audit_log` | journal_audit | Trace |
| `digiscore_member_map` | idem | Liaison SI ADD-only |
| `outstanding_loan` | *(nouveau)* | Crédits décaissés / PAR |
| `portfolio_followup` | suivi_portefeuille | V1–V3 + signaux |
| `par_indicator` | par_indicateur | PAR 30/90 |
| `recovery_case` | recouvrement | 4 niveaux |
| `recovery_action` | *(nouveau)* | Journal d’actions M7 |

L’API HTTP garde les clés JSON existantes (contrat front).
