# PROMPT 3 — M5 : Tableau d'amortissement (module workflow, tous rôles)

## Contexte projet

Tu codes le module **M5 "Tableau d'amortissement"** de DigiScore-WA, copilote d'éligibilité
et de plafond de crédit pour les institutions CIF (FUCEC-Togo = échantillon démo,
hackathon CIF DigiCoop-WA+, équipe Alpha, thématique 02).

Le backend FastAPI existe **déjà**. Ton boulot : consommer l'API et afficher le tableau.
**Ne recalcule aucune mensualité côté front** — les formules actuarielles sont dans le
backend et **doivent** être identiques entre la simulation et le dossier final.

## Connexion API

- Base URL : `http://localhost:8000`
- Auth : `POST /auth/login` `{"login": "agent", "password": "demo"}` → `access_token`.
  Header : `Authorization: Bearer <token>` sur tous les appels (sinon 401).
- Logins : `agent` / `chef_agence` / `cic`, mot de passe `demo`.
- Swagger : `http://localhost:8000/docs`.

## Le métier : conventions Excel (l'unique source de vérité)

Le tableau reproduit **strictement** un onglet Excel de référence (onglets `Parametres` /
`Simulations`). Toute la logique est dans le service backend `amortissement.py` :

| Cellule Excel | Sens | Formule backend |
|---|---|---|
| **B5** | Capital | `montant` (paramètre de la requête) |
| **B6** | Durée en mois | `duree_mois` |
| **B7** | Taux nominal annuel (décimal) | défaut `0.14` = 14 % → `t = B7 / 12` |
| **B8** | Taux d'assurance annuel (décimal) | défaut `0.057` = 5,7 % |
| **B11** | Mensualité hors assurance | `K * t / (1 - (1 + t) ** -n)` |
| **B12** | Cotisation assurance mensuelle | `K * B8 / 12` — **constante**, assise sur le capital initial, pas sur le restant dû |
| **B13** | Mensualité totale | `B11 + B12` |
| **B14** | Coût total | `B13 * n - K` |

Deux subtilités importantes à respecter dans l'affichage :
1. **L'assurance est constante** sur toute la durée (B12 = `capital_initial × 0,057 / 12`),
   elle ne décroît pas avec le restant dû. À montrer dans le tableau mois par mois.
2. **Le dernier mois est ajusté** pour solder exactement le restant dû : sa mensualité
   diffère donc des autres. Ne l'affiche pas comme une anomalie.
3. Tous les montants sont **arrondis au franc CFA** (pas de centiimes).

Note métier : le moteur de scoring (RCSD, plafond) garde son taux simple 1,8 % —
l'amortissement est **un affichage M5, pas une entrée du moteur de règles**. Ne melange
pas les deux.

## Endpoint à utiliser

### `GET /demandes/{demande_id}/amortissement`
Permissions : `agent`, `chef_agence`, `cic` (tous les rôles).
Query params (tous optionnels — ce sont les **lignes Simulations** d'Excel) :
- `montant` (float ≥ 0) — Capital B5. Défaut : montant **éligible** du score, sinon montant demandé.
- `duree_mois` (int 1..60) — B6. Défaut : durée de la demande.
- `taux_nominal` (float ≥ 0, défaut `0.14`) — B7.
- `taux_assurance` (float ≥ 0, défaut `0.057`) — B8.

Réponse :
```json
{
  "montant": 1360000,
  "duree_mois": 12,
  "taux_nominal": 0.14,
  "taux_assurance": 0.057,
  "mensualite_hors_assurance": 122110,
  "assurance_mensuelle": 6460,
  "mensualite_totale": 128570,
  "cout_total": 182845,
  "lignes": [
    { "numero": 1, "echeance": 122110, "capital": 106221, "interet": 15867,
      "assurance": 6460, "echeance_totale": 128570, "restant": 1253779 },
    { "numero": 12, "echeance": 122150, "capital": 106277, "interet": 143,
      "assurance": 6460, "echeance_totale": 128610, "restant": 0 }
  ]
}
```

**Comportement spécial (à reproduire fidèlement dans l'UI) :**
- **Sans** `montant` / `duree_mois` : le tableau est calculé sur le dossier et **persisté**
  en base (1 ligne par mois, table `amortization_line`).
- **Avec** un override (`montant` et/ou `duree_mois` et/ou taux) : tableau **calculé à la
  volée sans rien écrire** en base. C'est la "ligne Simulation" d'Excel.

## Le simulateur (feature principale)

Tu feras un **simulateur** : 4 champs (capital, durée, taux nominal, taux assurance) +
un tableau qui se recalcule à chaque changement (via `montant`/`duree_mois`/... en query).
Le but métier : laisser le chef d'agence comparer "si j'emprunte 1.36M sur 12 mois vs
1M sur 8 mois" avant de soumettre.

Comportements attendus :
- **Simulation = overrides** : dès que l'utilisateur touche à un champ, bascule en mode
  "simulation" (aucune persistance). Indique-le visuellement (badge "Simulation — non
  enregistrée" / bouton "Réinitialiser aux valeurs du dossier").
- **Valeurs par défaut** : au premier chargement (sans params), ce sont les valeurs du
  dossier (montant éligible si la demande a été analysée, sinon montant demandé).
- **Le bouton "Enregistrer le tableau"** ne doit apparaître que si l'on est sur les
  valeurs du dossier (pas en simulation) — car le backend ne persiste qu'en l'absence
  d'overrides.
- Validation : durée 1 à 60 mois, montant > 0, taux ≥ 0. Le backend valide déjà
  (`ge`/`le`), mais affiche les erreurs 422 proprement.
- Affiche les cellules équivalentes **B11 / B12 / B13 / B14** dans un résumé (cartes ou
  lignes) : mensualité hors assurance, assurance mensuelle, mensualité totale, coût total.

## Tableau mois par mois

Colonnes : **N°** (`numero`), **Mensualité** (`echeance`), **Capital amorti** (`capital`),
**Intérêts** (`interet`), **Assurance** (`assurance`), **Échéance totale**
(`echeance_totale`), **Capital restant dû** (`restant`).

- 1 ligne par mois, `numero` de 1 à `duree_mois`.
- La colonne `restant` doit décroître jusqu'à **0** exactement sur le dernier mois.
  C'est ta vérification visuelle de cohérence.
- Footer du tableau : totaux (capital = `montant`, intérêts + assurance = `cout_total`).

## Contraintes UI / UX

- Montants en **FCFA** avec séparateur de milliers + suffixe "F" (ex. `122 110 F`).
- Les taux sont **décimaux** côté API (0.14 = 14 %) mais doivent être affichés/saisis
  en **pourcentage** côté utilisateur (14 %), avec conversion propre.
- Précision : pas de décimales sur les montants (arrondis au franc CFA par le backend).
- Sur petits écrans (PWA mobile), le tableau mois par mois doit rester lisible —
  privilégie un affichage tableau scrollable horizontalement + les 4 cartes de résumé
  B11/B12/B13/B14 au-dessus.
- Étiquettes en **français**.
- L'utilisateur peut arriver depuis une demande (`demande_id`) : croisera avec
  `GET /demandes/{demande_id}` (statut, montant, score) si tu veux du contexte.

## Définition de done

1. Résumé B11/B12/B13/B14 (4 cartes) : mensualité, assurance, mensualité totale, coût total.
2. Simulateur : champs capital / durée / taux nominal / taux assurance → recalcul live
   du tableau (overrides query params), badge mode simulation.
3. Tableau mois par mois complet (capital, intérêts, assurance, échéance totale, restant).
4. Dernier mois soldant le restant dû à 0 (vérification automatique + visuelle).
5. Gestion du bouton "enregistrer" uniquement sur les valeurs du dossier.
