# Mapping SI — DigiScore-WA

Contrat de champs pour le pilote. En 72 h l’`AdapterStub` lit Postgres. En pilote : mêmes noms internes, source = API / export agence.

## Membre et compte

| Champ partenaire (exemples) | DigiScore | Notes |
|-----------------------------|-----------|-------|
| `NUM_CLIENT` / `CODE_MEMBRE` | `member.external_code` | Lookup indexé |
| `NOM`, `PRENOM` | `member.last_name`, `first_name` | |
| `DATE_ADHESION` | `member.joined_on` | Ancienneté |
| `STATUT_MEMBRE` | `member.status` | actif / gele / radie |
| `CODE_AGENCE` | `agency.code` → `member.agency_id` | Multi-topologie |
| `NUM_COMPTE` | `account.account_no` | Lookup indexé |
| `SOLDE` | `account.current_balance` | Lecture seule SI |
| `STATUT_COMPTE` | `account.status` | Gelé = garde-fou |

## Historique

| Champ partenaire | DigiScore |
|------------------|-----------|
| Écritures compte | `account_movement` (N dernières) |
| Soldes moyens | `savings_snapshot` (3 / 6 / 12 mois) |
| Crédits clôturés / en cours | `past_credit` |
| Impayés / contentieux | `incident` |

## Octroi (ADD-only, jamais dans le cœur)

| Objet DigiScore | Usage |
|-----------------|-------|
| `credit_application` | Dossier du jour |
| `score_result` | Score /100 + plafond + message |
| `decision` | Avis agent / chef / CIC |
| `audit_log` | Qui, quoi, motif |
| `digiscore_member_map` | Liaison ID interne ↔ `external_code` |

## BIC / fiscal / cautions

| Source | Champ DigiScore |
|--------|-----------------|
| Consentement BIC | `bic_consent` |
| Rapport BIC (fichier ou API) | `bic_report` (`source=simulate` en démo) |
| Quittance / patente | `supporting_document.document_type=FISCAL` |
| Cautionnaires | `guarantor` + `guarantor_review` |

## Règles d’intégration

1. Mapping validé avec la DSI (atelier 1–2 jours).
2. Adapter interchangeable : stub → API, même contrat `DossierInput`.
3. Zéro script `ALTER` / `DROP` sur le schéma tiers.
4. Timeouts / retry documentés sur les appels passerelle.
