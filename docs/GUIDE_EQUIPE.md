# Guide équipe DigiScore-WA

Monorepo unique. Chacun clone, `git pull`, lance Docker en local. Pas d’échange d’IP.

## Arborescence

| Dossier | Owner | Rôle |
|---------|-------|------|
| `backend/db/` | Data | `schema.sql` + seeds |
| `backend/app/` | Backend | FastAPI, adapters, persistance |
| `scoring/` | Scoring | Fonction pure `run(dossier)` |
| `frontend/` | Front | PWA React, affichage uniquement |
| `data/synthetic/` | Data | JSON sources + `cas_attendus.json` |
| `docs/` | Produit | CDC, archi, mapping, workflow |

## Ports

| Service | Port |
|---------|------|
| PostgreSQL | 5432 |
| FastAPI | 8000 |
| Vite | 5173 |
| Adminer | 8080 |

Connexion BDD : `postgresql://digiscore:digiscore@localhost:5432/digiscore`

## Démarrage

```bash
docker compose up -d
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest scoring/tests
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

OpenAPI : http://localhost:8000/docs · [ARCHI.md](ARCHI.md) · [GUIDE_SCORING.md](GUIDE_SCORING.md) · [GUIDE_FRONTEND.md](GUIDE_FRONTEND.md) · [GUIDE_ML_BACKEND_DATA.md](GUIDE_ML_BACKEND_DATA.md) · [SECURITE_ECHANGES_PILOTE.md](SECURITE_ECHANGES_PILOTE.md) · [postman/README.md](postman/README.md)

Notes adressées : [SYNTHESE_RESPONSABLE_SCORING.md](SYNTHESE_RESPONSABLE_SCORING.md) · [DONNEES_RESPONSABLE_MODELE.md](DONNEES_RESPONSABLE_MODELE.md) · [SYNTHESE_RESPONSABLE_FRONTEND.md](SYNTHESE_RESPONSABLE_FRONTEND.md) · [PLAN_ROBUSTESSE_DONNEES.md](PLAN_ROBUSTESSE_DONNEES.md).

Compose charge aussi le volume CSV (`db-seed`). Laptop lent : `LOAD_VOLUME=0 docker compose up -d`.

## Contrats

- Data → Back : `schema.sql` + seeds Docker. Back n’invente pas de tables.
- Scoring → Back : `from digiscore.pipeline import run`. Back assemble via `dossier_builder`.
- Back → Front : OpenAPI + `VITE_API_URL=http://localhost:8000`
- Reset BDD incompatible **ou** reload volume unique v2 : `docker compose down -v && docker compose up -d`

## Rôles démo

`agent` · `chef` · `cic` — mot de passe `demo`. JWT Bearer. Spec greffe SI : [SECURITE_ECHANGES_PILOTE.md](SECURITE_ECHANGES_PILOTE.md).

## Sync

- Data annonce tout reset `-v`.
- Scoring annonce tout changement de `message_code` / `DossierInput`.
- Back annonce tout breaking change d’URL.
- Front ne code aucune formule de score.
