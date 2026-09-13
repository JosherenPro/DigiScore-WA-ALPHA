# Workflow Agent → Chef d’agence → CIC

Le système ne décide jamais seul. Chaque avis est horodaté (`decision` + `journal_audit`).

## Rôles

| Login | Rôle | Mission |
|-------|------|---------|
| `agent` | Agent de crédit | Lookup membre, formulaire, analyse, mémo, soumission |
| `chef` | Chef d’agence | File à valider : valider / refuser / renvoyer / escalader CIC |
| `cic` | Comité d’octroi | Accorder / conditionner / refuser |

## États demande

`brouillon` → `analyse` → `soumis_chef` | `soumis_cic` → `accorde` | `conditionne` | `refuse` | `renvoye`

## Routage après soumission agent

| Zone / cas | File |
|------------|------|
| Score 0–40 ou knockout | Chef (confirme rejet ou override motivé → CIC) |
| Score 41–70 | CIC obligatoire |
| Score 71–100, montant ≤ éligible, non exceptionnel | Chef (validation simplifiée possible) |
| Montant ≥ 8 M ou produit exceptionnel | CIC obligatoire |

Chef ne clôture seul que si zone approbation, pas de voie exceptionnelle, montant < 8 M.

## API

| Méthode | Route | Qui |
|---------|-------|-----|
| POST | `/demandes/{id}/analyser` | Agent |
| POST | `/demandes/{id}/soumettre` | Agent |
| GET | `/files/chef` | Chef |
| GET | `/files/cic` | CIC |
| POST | `/demandes/{id}/decision` | Chef / CIC |

Override : `motif` obligatoire si l’avis s’écarte de la recommandation.

## Écrans

1. Agent : recherche → fiche historique → wizard → score/plafond/message → mémo → Soumettre
2. Chef : file → détail → Valider / Refuser / Renvoyer / Envoyer CIC
3. CIC : file → fiche 1 page → Accorder / Conditionner / Refuser
