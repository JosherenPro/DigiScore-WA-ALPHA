# Données enrichies — responsable modèle / scoring

À : owner `scoring/` (moteur règles **et** modèle plus tard)  
De : backend / BDD  
Objet : ce qui a été mis en base pour que tu puisses **tester tous les cas**, pas pour entraîner maintenant.

Le package `scoring/` n’a **pas** été modifié. `/analyser` appelle toujours `dossier_builder` → `run(DossierInput)`.  
`GET /capabilities` : tout à `false`. `ML_ENABLED=0`. Pas de 120k `score_result` précalculés.

Notes déjà là : bugs moteur [SYNTHESE_RESPONSABLE_SCORING.md](SYNTHESE_RESPONSABLE_SCORING.md) · contrat `run()` [GUIDE_SCORING.md](GUIDE_SCORING.md) · schéma EN [../backend/db/NAMING.md](../backend/db/NAMING.md).

---

## 1. À retenir en 30 secondes

1. **Deux livres**, jamais fusionnés : mouvements **agence** vs extraits **ailleurs** (autre COOPEC / banque / IMF). Pas Flooz / T-Money.
2. **120k vies distinctes** (RNG par membre), **mix de remplissage** : thin-file, gelé, retards, saisonnier, gros historique, standard. Ce n’est **pas** 120k × le même relevé plus ou moins long.
3. Colonnes **dates** pour construire plus tard PAR / snapshots point-in-time / trésorerie calendaire.
4. Reco moteur (`score_result`) ≠ validation humaine (`credit_application.status` + `decision`).
5. Entraîner un modèle sur ce générateur = apprendre le générateur. Jour FUCEC = extraits réels dans les **mêmes** tables.

Ancre temporelle du seed : **2026-09-13**. Seed RNG : `20260913`.

---

## 2. Deux populations

| Jeu | Codes | Rôle |
|-----|--------|------|
| Golden pitch | `MEM-001` … `MEM-012` | Recette moteur + démo jury. IDs 1–12 **stables**. |
| Volume | `VOL-0000001` … | Pagination, mix de cas, features **plus tard**. |

Demandes golden : id **1–9** = MEM-001…009 ; **pas** de demande MEM-010 (compte gelé) ; demande **10** = MEM-011 ; **11** = MEM-012.

Volume : ~20k dossiers A–E (`VOLUME_APPLICATIONS`, défaut 20000), **pas** 120k collectes. Recouvrement seulement profils `late`.

Reload (histoires v1 clonées → v2 uniques) :

```bash
docker compose down -v && docker compose up -d
# laptop : VOLUME_MEMBERS=5000 docker compose up -d
```

Marqueur : `seed_meta.volume_loaded = 'v2'`. Un `up` sans `-v` ne régénère pas.

Adminer : http://localhost:8080 — serveur `postgres`, user/mdp/base `digiscore`.

---

## 3. Mix de cas (volontaire)

Profil = `i % 100` pour `VOL-{i:07d}` (`backend/db/seed/generate_volume_csv.py` → `profile_of`).

| Profil | `i % 100` | ~ part | Agence (`account_movement`) | Ailleurs (`external_*`) | Crédits / incidents |
|--------|-----------|--------|-----------------------------|-------------------------|---------------------|
| `thin` | 0–6 | ~7 % | 0–6, parfois **aucun** | souvent 0 ; parfois 1 relevé (cas MEM-012) | rarement |
| `frozen` | 7–11 | ~5 % | peu, compte `gele` | 0 | pas de nouvelle demande |
| `late` | 12–19 | ~8 % | moyen, irrégulier | parfois | impayés + incidents uniques + suivi/recouvrement |
| `seasonal` | 20–29 | ~10 % | creux juin–août | parfois | interne, produit agricole si demande |
| `ancien` | 30–69 | ~40 % | **36–180**, unique | parfois 12–48 lignes | 1–3 crédits internes |
| `standard` | 70–99 | reste | 8–36, unique | **majorité sans** ailleurs | 0–1 crédit |

~30–40 % des membres (hors gelés) ont **un** compte ailleurs. Les autres : **zéro** ligne `external_*`.

SQL profil volume :

```sql
SELECT CASE
         WHEN (ltrim(substr(external_code, 5), '0')::int % 100) < 7  THEN 'thin'
         WHEN (ltrim(substr(external_code, 5), '0')::int % 100) < 12 THEN 'frozen'
         WHEN (ltrim(substr(external_code, 5), '0')::int % 100) < 20 THEN 'late'
         WHEN (ltrim(substr(external_code, 5), '0')::int % 100) < 30 THEN 'seasonal'
         WHEN (ltrim(substr(external_code, 5), '0')::int % 100) < 70 THEN 'ancien'
         ELSE 'standard'
       END AS profil,
       COUNT(*)
FROM member
WHERE external_code LIKE 'VOL-%'
GROUP BY 1
ORDER BY 1;
```

Exemples à pêcher :

```sql
-- Thin sans mouvement agence
SELECT m.external_code, COUNT(mv.id) AS nb_mvt
FROM member m
JOIN account a ON a.member_id = m.id
LEFT JOIN account_movement mv ON mv.account_id = a.id
WHERE m.external_code LIKE 'VOL-%'
  AND (ltrim(substr(m.external_code, 5), '0')::int % 100) < 7
GROUP BY m.id
HAVING COUNT(mv.id) = 0
LIMIT 5;

-- Avec relevé ailleurs
SELECT m.external_code, fi.code, fi.kind, COUNT(em.id) AS nb_ext
FROM member m
JOIN external_account ea ON ea.member_id = m.id
JOIN financial_institution fi ON fi.id = ea.institution_id
JOIN external_account_movement em ON em.account_id = ea.id
GROUP BY m.id, fi.code, fi.kind
LIMIT 5;
```

Golden utile moteur :

| Code | Cas |
|------|-----|
| MEM-001 | bon payeur, historique agence dense |
| MEM-004 | thin-file local |
| MEM-009 | gros ticket, voie CIC |
| MEM-010 | `gele` — pas de demande |
| MEM-012 | peu/pas de mvts **ici**, relevé **BTCI** (`source=externe`) |

---

## 4. Deux cahiers — ne pas fusionner

Kodjo est membre de **cette** COOPEC (où l’agent ouvre DigiScore). Il peut aussi avoir un compte dans **une autre** IF.

| Cahier | Tables | Ce que c’est |
|--------|--------|----------------|
| Ici (core local) | `account`, `account_movement`, `savings_snapshot` | Épargne / ops de **l’agence** (`member.agency_id`) |
| Ailleurs | `financial_institution`, `external_account`, `external_account_movement`, `external_savings_snapshot` | Extraits autre COOPEC / banque / IMF |

`financial_institution.kind` ∈ `{coopec, banque, microfinance}` seulement. Seed : `IF-COOPEC-KPA`, `IF-COOPEC-SOK`, `IF-BTCI`, `IF-UTB`, `IF-WAGES`.

`past_credit.institution_id` : NULL = crédit de l’agence ; renseigné = chez qui (MEM-012 → BTCI).  
`past_credit.source` : `interne` \| `externe` \| `bic`.

**Pourquoi séparé.** Coller un « retrait autre COOPEC » dans `account_movement` fausse le solde agence, rend le thin-file interne illisible, et DigiScore n’est pas le core de tout le monde.

**Aujourd’hui `dossier_builder` ne lit pas `external_*`.** Il passe :

- `historique.credits_ailleurs` = flag `credit_application.has_external_credits`
- `historique.preuves_externes_ok`
- crédits passés **sans** nom d’IF
- `epargne_moy_*` = snapshot **agence** seulement
- `nb_mouvements_90j` = **proxy** (4 ou 1 selon le snapshot), pas un vrai COUNT 90 j

Les lignes ailleurs sont en base pour **toi plus tard** (feature « historique hors agence ») et pour le front (preuve / BIC). Si tu veux les injecter dans `DossierInput` : étendre le type **et ping le back**.

Hors scope : Flooz, T-Money, wallets, mobile money (vague suivante).

---

## 5. Colonnes dates (cibles constructibles)

Sans dates, `days_late` est un entier décoratif. Maintenant :

| Table | Colonnes | Usage modèle |
|--------|----------|----------------|
| `outstanding_loan` | `disbursed_on`, `due_on`, `observed_on` | PAR30 à 90 j du **décaissement**, pas un label tiré au sort |
| `savings_snapshot` | `as_of` + `UNIQUE(account_id, as_of)` | photo datée ; ou agréger `account_movement.moved_on` |
| `monthly_cashflow` | `period_month` (en plus de `month_no` 1..12) | choc saisonnier **calendaire** (juin–août rural) |
| `external_savings_snapshot` | `as_of` | même idée, cahier ailleurs |

Déjà datés avant cette vague : `account_movement.moved_on`, `past_credit.granted_on` / `closed_on`, `incident.occurred_on`, `member.joined_on`, `account.opened_on`, `credit_application.applied_at`, `decision.decided_at`.

Exemple PAR constructible (volume `late` / golden MEM-003) :

```sql
SELECT m.external_code, ol.principal, ol.outstanding, ol.days_late,
       ol.disbursed_on, ol.due_on, ol.observed_on,
       (ol.observed_on - ol.disbursed_on) AS age_credit_j
FROM outstanding_loan ol
JOIN member m ON m.id = ol.member_id
WHERE ol.status = 'impaye';
```

Le snapshot **n’est pas** une série temporelle : 1 photo à l’ancre. Pour une vraie courbe, lire `account_movement`.

---

## 6. Ce que chaque table te donne

### Identité / compte (100 % des membres)

`member` : `external_code`, `joined_on`, `status` (`actif`/`gele`/`radie`), `area` (`urbaine`/`rurale`), `occupation`, `agency_id`.  
`account` : `account_no`, `opened_on`, `status`, `current_balance`.  
`digiscore_member_map` : liaison sidecar (ADD-only).

### Historique agence

`account_movement` : `moved_on`, `movement_type` (`depot`/`retrait`/`interet`), `amount`, `label` unique (`#{i}-{k}`). 0 à 180 lignes selon profil.  
`savings_snapshot` : `avg_balance_3m/6m/12m` dérivés **de ses** mvts (0 si vide) + `as_of`.

### Ailleurs (fraction)

1 IF, 12–48 mvts uniques, 1 snapshot. Labels préfixés `Ailleurs`.

### Crédit passé / incidents / garanties

`past_credit` : montant, durée, dates, `status` (`solde`/`en_cours`/`impaye`), retards, `source`, `institution_id`.  
`incident` : surtout `late` (détail unique par membre).  
`member_guarantee` : fraction `ancien`/`standard`.  
`bic_consent` / `bic_report` : si ailleurs (compteurs + texte, **pas** un relevé BIC live).

### Collecte A–E (sous-ensemble demandes)

Tables liées à `credit_application` : `household`, `activity`, `economic_model`, `market`, `income_expense` (CA=`revenue`, CMV=`cogs`, preuves N1–N3), `wealth` (5 signaux), `monthly_cashflow`, `application_guarantee`, `supporting_document` (`ocr_quality`).

Volume : libellés / montants dérivés de `i`, pas un tampon. Saisonnier : produit `AGR-SAI`, creux tréso mois 6–8.

### Suivi / recouvrement (late)

`outstanding_loan` + dates.  
`portfolio_followup` : visites V1–V3, `days_late`, `signal` unique.  
`recovery_case` : niveau 1–4, `action` unique (plus le clone « Relance Koffi Chef » sur VOL-1…3000).  
`par_indicator` : agrégat **agence**, pas un label membre.

---

## 7. Reco score vs validation humaine

Le modèle (règles aujourd’hui, ML plus tard) **ne valide pas** le crédit.

| Question | Table / colonne |
|----------|-----------------|
| Que dit le moteur ? | `score_result` : `eligible`, `eligible_amount`, `message_code`, `score_total`, `thin_file`, `engine_version` (`rules-v1`) |
| Anciennes analyses ? | `score_result_history` (copie **avant** ré-`/analyser`) |
| Ratios persistés | `financial_ratio` (EBE, CAF, RCSD…) + `financial_ratio_history` |
| Où en est le dossier ? | `credit_application.status` : `brouillon` → `analyse` → `soumis_chef`/`soumis_cic` → `accorde` / `conditionne` / `refuse` / `renvoye` / `clos` |
| Qui a tranché ? | `decision` : `level`, `opinion`, `is_override`, `reason`, `user_id`, `decided_at` |
| Trace | `audit_log` |

`score_result.eligible = true` **n’implique pas** `status = 'accorde'`.  
`decision.is_override = true` = l’humain n’a pas suivi la reco (motif obligatoire).

Le volume n’a **pas** 120k scores. Pour un label « accordé vs reco », il faut passer par `/analyser` puis `/decision` (ou le seed golden si une décision existe). Les `VOL-*` demandes sont en `brouillon`.

---

## 8. Ce que le moteur voit aujourd’hui (limites)

`dossier_builder.py` assemble le JSON FR. Trous utiles pour toi :

| En base | Pas (encore) dans `DossierInput` |
|---------|----------------------------------|
| Liste `account_movement` | seulement un proxy `nb_mouvements_90j` |
| `external_*` | seulement les flags déclaration / preuves |
| `past_credit.institution_id` / nom IF | crédits sans établissement |
| `period_month` | trésorerie surtout via `month_no` + inflow/outflow |
| `outstanding_loan` dates | pas branché au `run()` |
| `economic_model` / `market` | partiellement via activité / collecte E |

Tu n’as **pas** besoin de SQL dans `scoring/`. Tu étends `DossierInput` ; le back mappe.

---

## 9. Ce que ça ne fait pas

- Corriger les 14 défauts listés dans [SYNTHESE_RESPONSABLE_SCORING.md](SYNTHESE_RESPONSABLE_SCORING.md) (code moteur).
- Un jeu **réel** FUCEC. C’est un générateur reproductible (`SEED + i`).
- Mobile money.
- `ML_ENABLED=1`, fit scorecard, routes `/anomalies` / `/simuler`.
- Remplacer le SI partenaire.

Règle produit inchangée : **le ML éclaire, l’humain décide**. Jamais `eligible` / `zone` / `message_code` / knockouts / `next_queue` depuis un modèle.

---

## 10. Recette pour toi

1. `pytest scoring/tests` (golden).
2. Login `agent` / `demo` → Bearer → `POST /demandes/1/analyser` (MEM-001).
3. Relancer `/analyser` : 1 ligne `score_result_history`, 1 `score_result` courant.
4. SQL ci-dessus : au moins 1 thin à 0 mvt, 1 sans `external_*`, 1 avec.
5. Si tu ajoutes un champ au dossier : ping back (`dossier_builder`) **et** front si le JSON API change. Rename `message_code` = ping back + front.

Fichiers générateur : [generate_volume_csv.py](../backend/db/seed/generate_volume_csv.py), [load_volume_csv.py](../backend/db/seed/load_volume_csv.py), golden [02_metier.sql](../backend/db/seed/02_metier.sql).
