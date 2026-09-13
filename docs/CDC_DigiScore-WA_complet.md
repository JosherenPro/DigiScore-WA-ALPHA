# DigiScore-WA — Cahier des charges complet

**Équipe Alpha · Thématique 02 Scoring microcrédit · CIF DigiCoop-WA+ · Lomé, septembre 2026**  
**Cible :** institutions membres de la CIF (FUCEC-Togo = échantillon d’existant, pas la seule cible)  
**Score :** /100 · seuils 40 / 70 (décision encadreurs)

---

## 1. Contexte et problématique

Les SFD du réseau CIF évaluent encore largement le risque de microcrédit de façon manuelle, hétérogène et lente, alors que le retard se joue dès J+1.

- ~3 h pour instruire un dossier
- ~8 % d’impayés de portefeuille
- Tout demandeur doit ouvrir un **compte membre** ; l’historique institutionnel existe souvent mais n’est pas exploité comme moteur d’éligibilité / de plafond
- Cas sans historique interne, BIC/fiscalité et cautionnaires restent très papier

**Problématique :** objectiver l’éligibilité et le plafond à partir du comportement du membre (interne ou preuves externes), sans remplacer la décision humaine (Agent ? Chef d’agence ? CIC), de façon déployable chez les SFD CIF en 72 h de prototype.

---

## 2. Existant et besoin

Cycle observé (9 composantes) : collecte A–E + N1/N2/N3 ? analyse économique ? analyse financière (CAF, RCSD, 6 ratios, trésorerie, patrimoine) ? risques ? documents (BIC, fiscalité) ? décision / mémo / comité ? amortissement ? suivi PAR ? recouvrement 4 niveaux.

Besoin : digitaliser cette méthode. Ajouter un moteur type **crédit télécom** (éligible / montant / message) et une chaîne de validation réelle.

---

## 3. Solution

DigiScore-WA (WA = West Africa) est un **copilote** d’octroi :

Compte membre ? historique interne **ou** preuves externes ? formulaire ? score /100 + plafond + message ? Agent ? Chef d’agence ? CIC.

| Module | Contenu | 72 h |
|--------|---------|------|
| M1 Collecte | Wizard A–E, N1–N3, upload pièces | Fonctionnel |
| M2 Analyse | CAF, RCSD, 6 ratios, trésorerie, patrimoine | Fonctionnel |
| M3 Score & plafond | 6 critères /100, knock-outs, messages | Fonctionnel |
| M4 Mémo | Mémo + fiche comité | Fonctionnel |
| M5 Décision | Circuit 3 niveaux + amortissement | Fonctionnel |
| M6 / M7 | Suivi PAR & recouvrement | Maquette |

---

## 4. Différenciation / innovation

1. **Plafond type crédit télécom** — pas seulement oui/non : montant éligible + message explicite
2. **Membre + historique** comme source de vérité ; voie **preuves externes** si pas d’historique interne
3. **BIC / fiscalité** + **cautionnaires évalués** au-delà d’un seuil
4. **Gouvernance Agent ? Chef ? CIC** avec audit / override motivé
5. **ML explicable optionnel** — le ML éclaire, l’humain décide ; hors routage MVP
6. **Sidecar SI** : mapping, adapters, tables `digiscore_*` ADD-only

**Phrase pitch :** le crédit mobile appliqué aux institutions CIF — éligibilité et plafond depuis l’historique du membre, score /100, cautions/BIC, décision humaine, sans toucher au cœur transactionnel.

---

## 5. Modèle de décision

```text
EBE  = CA ? CMV ? Charges_exploitation
CAF  = EBE + Produits_financiers + (Revenus_perso ? Charges_familiales)
RCSD = CAF / (Dettes_en_cours + Service_credit_sollicite)
```

- RCSD ? 1,50 recommandé · **RCSD < 1,00 = knock-out**
- 6 ratios : marge brute, BN/CA, solvabilité (>1), rotation stocks, participation (>35 %), FR (>150 %)
- Trésorerie 12 mois : cumul ? 0 chaque mois
- Patrimoine : situation nette > 0 + 5 signaux

### Score /100

`score = ? (note_i/100) × poids_i × 100`

| Critère | Poids |
|---------|-------|
| Analyse financière | 25 % |
| Capacité de remboursement | 20 % |
| Historique de remboursement | 20 % |
| Risque d’activité | 15 % |
| Garanties (+ cautions) | 10 % |
| Qualité documentaire (+ BIC/fiscal) | 10 % |

| Score | Zone | Reco |
|-------|------|------|
| 0–40 | Risque élevé | Rejet recommandé |
| 41–70 | Risque moyen | Analyse / CIC |
| 71–100 | Risque faible | Approbation recommandée |

Knock-outs : RCSD < 1 · ESG · incohérence critique · incidents graves · BIC/fiscal exigible manquant · seuil caution sans cautionnaire éligible.

### Workflows

| Score | Chef | CIC |
|-------|------|-----|
| ? 40 ou KO | Confirme rejet ou override | Si override |
| 41–70 | Avis | **Obligatoire** |
| > 70 et montant OK | Validation simplifiée | Selon politique |
| Voie exceptionnelle (~8–10 M+) | Ne clôture pas seul | **Obligatoire** |

---

## 6. Architecture et intégrabilité SI

**Stack MVP :** React PWA · FastAPI · package `scoring` (règles) · PostgreSQL / Docker.

**Sidecar :** lecture via API/passerelle + mapping ; écriture uniquement dans `digiscore_*` (CREATE/INSERT). Interdit : ALTER/DROP du SI partenaire, greffe transactionnelle.

| Étape | Livrable |
|-------|----------|
| Conception H0 | Sidecar + schéma + mapping + interface Adapter |
| Dev 72 h | AdapterStub + mêmes endpoints qu’en pilote |
| Pilote | Adapter réel + CREATE tables + atelier DSI |

Perf : lookup indexé n° compte, historiques paginés, échelle > 1 M membres.

**Ressources démo :** 2–4 vCPU · 4–8 Go RAM · Docker.  
**Pilote :** 4–8 vCPU · 8–16 Go · SSD 50–100 Go · API lecture + CREATE TABLE.

---

## 7. Données

Tables cœur : `agence`, `produit_credit`, `membre`, `compte`, `mouvement_compte`, `credit_passe`, `incident`.  
BIC/fiscal : `consentement_bic`, `rapport_bic`, `piece_justificative`.  
Cautions : `cautionnaire`, `demande_caution`, `evaluation_cautionnaire`.  
Décision : `demande_credit`, `score_resultat`, `decision`, `journal_audit`.

Seeds 12 profils (bon payeur, plafonné, incidents, thin-file, saisonnier, zone grise, RCSD KO, gros montant + cautions, compte gelé, override, BIC/preuves).

---

## 8. IN / OUT 72 h

**IN :** M1–M5, score /100, plafond, 3 rôles, upload pièces, cautions + flags BIC (seed), maquettes M6/M7, README + compose.

**OUT :** connecteurs live core banking / BIC / YAS-Flooz / SYSCOFOP · ML sur données réelles · M6/M7 temps réel · multi-tenant / SSO / i18n éwé.

---

## 9. Conformité et impact

Traçabilité des scores et overrides (audit BCEAO). Amortissement jamais au-delà de la capacité (RCSD + trésorerie). Données hackathon **synthétiques uniquement**.

Impacts pédagogiques (à confirmer en pilote) : 3 h ? 45 min · 8 % ? 5 % d’impayés · suivi 70 % automatisé (vision).

---

## 10. Annexes

`docs/architecture.md` · `docs/GUIDE_EQUIPE.md` · `docs/workflow-roles.md` · `docs/mapping_si.md` · `docs/PITCH_DIFFERENCIATION.md` · `scoring/SPEC.md`
