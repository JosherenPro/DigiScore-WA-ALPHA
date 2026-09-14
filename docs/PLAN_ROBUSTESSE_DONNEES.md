# Plan — robustesse des données (back / BDD)

Pour nous (data + backend). Pas un brief scoring, pas un brief front.

Question posée : *si on enrichit les CSV « comme en conditions réelles », est-ce que ça règle les non-faits ?*

**Réponse courte :** seulement les trous de **calendrier** et de **cohérence temporelle**, et **après** des colonnes dates. Plus de lignes sans dates = les mêmes trous, en plus gros. Ça ne répare ni le `.items` front, ni les 14 bugs `scoring/`, ni un modèle entraîné sur du synthétique.

---

## Ce que plus de CSV règle / ne règle pas

| Non-fait | Enrichir CSV / schéma ? |
|----------|-------------------------|
| Front `.items` | Non — client |
| Bugs moteur (Monte Carlo, RCSD, zone 40, anomalies thin-file) | Non — `scoring/` |
| `historique()` sans mouvements | **Un peu** : `account_movement` existe ; 12 profils déjà seedés, volume pauvre. Exposer les N derniers (LIMIT) = vague C |
| Vision M6 sans pagination | Non (maquette petite). Dates PAR = **oui schéma** |
| `outstanding_loan` sans `disbursed_on` | **Schéma d’abord**, puis CSV. Remplir `days_late` sans date ≠ PAR30 à 90 j du décaissement |
| Snapshot épargne 1 ligne courante | `as_of` **ou** recalcul depuis `account_movement`. CSV plus joli sur l’état du jour = toujours une fuite ML |
| Trésorerie `month_no` 1..12 | Colonne `period_month DATE`, pas plus d’entiers relatifs |
| Entraîner un modèle sur 120k | **Non** — le générateur reste un générateur. Jour extraits FUCEC |

Les flux **déjà datés** (à réutiliser, pas à recréer) : `account_movement.moved_on`, `past_credit.granted_on` / `closed_on`, `incident.occurred_on`, `member.joined_on`, `account.opened_on`, `credit_application.applied_at`, `decision.decided_at`. Index `(account_id, moved_on DESC)` déjà là.

---

## Vague A — schéma ADD-only (comme l’auth)

Pas d’Alembic. `schema.sql` + `ALTER … IF NOT EXISTS` + script Python pour le volume Docker déjà peuplé. `down -v` seulement si on accepte de recharger les 120k.

| Table | Ajout | Pourquoi |
|--------|--------|----------|
| `outstanding_loan` | `disbursed_on DATE`, `due_on DATE`, `observed_on DATE` | Cible « PAR30 à 90 j du décaissement » **constructible** |
| `outstanding_loan` | remplir `application_id` quand on peut (colonne déjà nullable) | Relier l’issue à la demande |
| `savings_snapshot` | `as_of DATE` + viser `UNIQUE(account_id, as_of)` | Point-in-time ; sinon abandonner le snapshot et agréger les mouvements |
| `monthly_cashflow` | `period_month DATE` à côté de `month_no` | Aligner saison / choc daté |

Hors vague A : lever le `UNIQUE` de `score_result` / `financial_ratio` (déjà historisés en tables jumelles). Hors : tables ML (`resilience_simulation`, registre de modèles).

---

## Vague B — générateur cohérent

Fichiers : [backend/db/seed/generate_volume_csv.py](../backend/db/seed/generate_volume_csv.py), [load_volume_csv.py](../backend/db/seed/load_volume_csv.py). CSV gitignorés.

Ordre à respecter **par membre** :

1. `joined_on` / `opened_on`
2. mouvements d’épargne **après** ouverture
3. demande / décaissement **après** un historique minimum
4. `days_late` **cohérent** avec `disbursed_on` + `observed_on` (pas un entier tiré à part)

| Action | Limite |
|--------|--------|
| Lier une **partie** des `outstanding_loan` volume à une `credit_application` | Pas 120k dossiers complets A–E |
| Densifier `account_movement` | **Sous-échantillon** (ex. 2–5 k comptes), pas 120k × 5 ans |
| Varier `par_indicator.as_of` | Toujours un agrégat **agence**, pas un label membre |

Les 12 profils [02_metier.sql](../backend/db/seed/02_metier.sql) restent le golden pitch (MEM-001 … 012). Le volume sert la pagination et le « ça tient », pas le ML.

---

## État (vagues A / B / dense 120k)

**Fait.** Colonnes dates + deux cahiers (agence vs autres IF) + générateur unique par membre + API fiche / flux 3 acteurs.

Reload volume : `docker compose down -v && docker compose up -d`. Premier chargement **long**. Itération laptop : `VOLUME_MEMBERS=5000`. Marqueur `seed_meta.volume_loaded=v2`. CSV v1 (histoires clonées) **ne** se rechargent **pas** : `-v` obligatoire.

Deux livres séparés : `account_movement` (cette COOPEC) vs `external_account_movement` (autre COOPEC / banque / IMF). **Pas** Flooz / T-Money. ~30–40 % des VOL-* ont un compte ailleurs ; thin / gelé / late / saisonnier / ancien sont un **mix**, pas 120k × 180 mvts.

API : `GET /agences`, `/institutions`, `/referentiels`, `/moi` ; fiche enrichie ; `/historique` avec 30 mvts agence ; `/mouvements` paginé ; `/comptes-externes` ; `GET /demandes/{id}` collecte A–E + `/scores`.

Brief scoring (mix, tables, SQL) : [DONNEES_RESPONSABLE_MODELE.md](DONNEES_RESPONSABLE_MODELE.md).
