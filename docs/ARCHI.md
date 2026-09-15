# Architecture DigiScore-WA (collègues)

Copilote d’éligibilité et de **plafond** pour les SFD CIF. FUCEC = échantillon, pas la seule cible. Le système **ne décide jamais seul**.

## Sidecar

DigiScore vit **à côté** du SI, jamais dedans.

- Lecture membre / historique via passerelle (stub = Postgres local).
- Écriture seulement dans nos objets : `score_result`, `decision`, `audit_log`, `digiscore_member_map` (+ tables d’octroi que l’institution autorise).
- Interdit : `ALTER` / `DROP` sur le schéma partenaire, triggers sur le transactionnel, remplacer le core banking.
- Tables `digiscore_*` = **ADD-only**. Références SI = IDs métier (`member.external_code`), pas de FK physique obligatoire vers le core.

## Stack et ports

| Couche | Choix | Port |
|--------|--------|------|
| PWA | React + Vite + TypeScript | 5173 |
| API | FastAPI (`uvicorn` **local**, pas dans Compose) | 8000 |
| Moteur | Package `scoring/` — fonction pure | — |
| BDD | PostgreSQL 16 (Docker) | 5432 |
| Adminer | UI SQL | 8080 |

```text
Agent / Chef / CIC
        │
   React PWA :5173     VITE_API_URL=http://localhost:8000
        │
   FastAPI :8000
     ├── dossier_builder → digiscore.pipeline.run(dossier)
     └── PostgreSQL :5432
```

**Qui parle à qui**

| De | Vers | Contrat |
|----|------|---------|
| Front | API JSON | clés **FR** (`code_externe`, `montant_demande`…) — jamais les colonnes SQL |
| Back | `scoring` | `DossierInput` → `ScoreResult` via `run()` |
| Scoring | — | **aucun SQL**, aucune requête HTTP |
| Back | Postgres | identifiants **EN** (`member.external_code`) |

Le collègue scoring code le moteur, pas l’API. Le front n’implémente **aucune** formule CAF / RCSD / score.

## Schéma : EN en SQL, FR en métier

Identifiants de tables/colonnes = anglais. `COMMENT ON` et **codes métier** = français (`actif` / `gele`, `brouillon`, `soumis_chef`, `soumis_cic`, N1–N3, `solde` / `impaye`).

Carte complète : [../backend/db/NAMING.md](../backend/db/NAMING.md) · API endpoint par endpoint : [API_ENDPOINTS_REPONSES.md](API_ENDPOINTS_REPONSES.md).

Lookup indexés : `member.external_code`, `account.account_no`.

## Flux Agent → Chef → CIC

1. Agent : lookup membre (compte **actif** obligatoire) → wizard collecte A–E → `POST /analyser`.
2. Score **/100** : 0–40 rejet reco · 41–70 analyse / CIC · 71–100 approbation reco.
3. `POST /soumettre` route vers file **chef** ou **CIC** (`next_queue` : zone, `message_code`, montant / voie exceptionnelle).
4. Chef peut clôturer si la reco le permet ; sinon escalade CIC. Override = motif obligatoire.
5. Mémo + tableau d’amortissement sur le **montant éligible**.

Poids score : financier 25 · capacité 20 · historique 20 · activité 15 · garanties 10 · documents 10.

## Docker = BDD + données (pas l’API)

```bash
docker compose up -d
# LOAD_VOLUME=0 docker compose up -d     # laptop lent : 12 profils seulement
# Reset : docker compose down -v
```

1. `postgres` healthy → init `schema.sql` + `02_metier.sql` (MEM-001…012) + `03_auth_alter` + `04_data_alter`.
2. `db-seed` (one-shot) : génère CSV **v2** (histoires uniques, mix thin / ailleurs) s’ils manquent, puis COPY. Marqueur `seed_meta.volume_loaded=v2`. Volume v1 : **`docker compose down -v`** puis `up` (pas un skip silencieux).
3. Les CSV **ne se commitent pas**. Un `git clone` les régénère au premier `up`. Laptop : `VOLUME_MEMBERS=5000`.

L’API reste `uvicorn` local. `.env` : `DATABASE_URL`, `VITE_API_URL` — voir [../.env.example](../.env.example).

Swagger : http://localhost:8000/docs · contrat figé : [openapi.json](openapi.json) (pas le yaml) · collection : [postman/README.md](postman/README.md). Notes : [SYNTHESE_RESPONSABLE_FRONTEND.md](SYNTHESE_RESPONSABLE_FRONTEND.md) · [SYNTHESE_RESPONSABLE_SCORING.md](SYNTHESE_RESPONSABLE_SCORING.md).

## IN / OUT 72 h

**IN** : M1–M5, 12 profils démo, sidecar documenté, volumétrie optionnelle, maquettes M6/M7, **auth démo 3 rôles** (login + mot de passe + JWT) pour simuler Agent → Chef → CIC.

**OUT** : core banking / BIC / Flooz live, ML décisionnel, M6/M7 temps réel, **SSO institutionnel**, **HMAC SI** (spec seulement), i18n éwé, backend dans Compose.

Sécu des échanges **si retenus** : [SECURITE_ECHANGES_PILOTE.md](SECURITE_ECHANGES_PILOTE.md). DigiScore **ne remplace pas** le SI.

## Ce que tu ne touches pas

- **Scoring** : ne change pas un `message_code` sans ping back + front.
- **Front** : n’invente pas d’endpoint ; consomme OpenAPI.
- **Data** : pas d’`ALTER` improvisé ; le schéma est la source pour le back.
