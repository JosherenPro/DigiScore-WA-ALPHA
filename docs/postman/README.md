# Tests API DigiScore-WA (Swagger + Postman)

## Prérequis

1. `docker compose up -d` (Postgres + Adminer + `db-seed`). Premier `up` : 1–2 min si volumétrie.
2. API locale (pas dans Compose) :

```bash
cp -n .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
```

| URL | Usage |
|-----|--------|
| http://localhost:8000/health | Liveness |
| http://localhost:8000/docs | Swagger |
| http://localhost:8000/openapi.json | Contrat live |
| [../openapi.json](../openapi.json) | Export figé (régénérer via `python backend/scripts/export_openapi.py`) |

JWT : `POST /auth/login` `{ "login": "agent", "password": "demo" }` → `Authorization: Bearer <access_token>`.

Logins : `agent` · `chef` · `cic`. Mot de passe : **`demo`**.

Listes paginées : `{ items, page, page_size, total }`.

## Collection Postman

Fichier : [DigiScore-WA.postman_collection.json](DigiScore-WA.postman_collection.json)

Import → Postman → *Import* → ce JSON. Variable `baseUrl` = `http://localhost:8000`.

IDs seed `02_metier.sql` (stables tant qu’on n’a pas `down -v` + autre seed) :

| Variable | Valeur | Membre |
|----------|--------|--------|
| `demande_mem001` | 1 | MEM-001 Kodjo Mensah — bon payeur |
| `demande_mem004` | 4 | MEM-004 Aisha Slim — thin-file |
| `demande_mem009` | 9 | MEM-009 Isaac Gbeglo — 10 M, CIC |

## Scénario smoke (ordre)

1. **Santé** — `GET /health` → `{ "status": "ok" }`.
2. **3 rôles** — `POST /auth/login` avec `"login": "agent"` puis `chef` puis `cic`.
3. **Lookup** — `GET /membres?q=MEM-001&page=1&page_size=30` → enveloppe `{ items, page, page_size, total }` (plus une liste nue).
3b. **Référentiels** — `GET /agences`, `/institutions` (pas e-money), `/referentiels`, `/moi`.
3c. **Fiche** — `GET /membres/1/historique` contient `mouvements[]` (agence). MEM-012 : `/comptes-externes` = BTCI, distinct de `/mouvements`.
4. **MEM-001** — `POST /demandes/1/analyser` puis `/soumettre` → file **chef** (`MONTANT_OK` typique). Mémo + amortissement.
5. **MEM-004** — fiche `thin_file: true` ; analyser → `KNOCKOUT_RCSD` (la capacité insuffisante est prioritaire).
6. **MEM-009** — analyser → `VOIE_EXCEPTIONNELLE` ; soumettre → file **cic**.
7. **Files** — `GET /files/chef` et `/files/cic` (paginés).
8. **M6 / M7** — `GET /vision/portefeuille` et `/vision/recouvrement`.

Volumétrie : `GET /membres?q=VOL-` doit renvoyer `total` >> 12 si `LOAD_VOLUME=1`. Compte SQL : `SELECT COUNT(*) FROM member WHERE external_code LIKE 'VOL-%';`

## Réponses listes (breaking)

`GET /membres`, `GET /demandes`, `GET /files/chef`, `GET /files/cic` renvoient :

```json
{ "items": [ ... ], "page": 1, "page_size": 30, "total": 12 }
```

`page_size` max = 100. Recherche membres : `external_code`, nom, prénom, **`account.account_no`**.
