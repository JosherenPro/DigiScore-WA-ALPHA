# DigiScore-WA

Copilote d’éligibilité et de **plafond de crédit** pour les institutions membres de la CIF (FUCEC-Togo = échantillon, pas la seule cible). Hackathon CIF DigiCoop-WA+, Équipe Alpha, thématique 02.

Le système **ne décide jamais seul**. Score **/100**, zones 0–40 / 41–70 / 71–100. Circuit **Agent → Chef d’agence → CIC**.

## Stack

| Couche | Choix |
|--------|--------|
| Frontend | React + Vite + TypeScript (PWA) |
| Backend | FastAPI (`uvicorn` local) |
| Moteur | Package Python `scoring/` (règles, pas de ML) |
| BDD | PostgreSQL 16 + Docker Compose (`db-seed` CSV) |

## Démarrer

```bash
docker compose up -d
# laptop lent : LOAD_VOLUME=0 docker compose up -d
# reset BDD : docker compose down -v

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
# autre terminal
cd frontend && npm install && npm run dev
```

Compose lance **Postgres + Adminer + db-seed**. L’API n’est pas dans Compose.

- Premier `up` : long si génération 120k CSV v2 (histoires uniques) + COPY. CSV gitignorés. Laptop : `VOLUME_MEMBERS=5000 docker compose up -d`.
- `up` suivants : instantanés si `seed_meta.volume_loaded=v2`. Volume v1 : `docker compose down -v` puis `up`.
- `LOAD_VOLUME=0` : 12 profils démo seulement.

| URL | Service |
|-----|---------|
| http://localhost:5173 | PWA |
| http://localhost:8000/docs | Swagger |
| http://localhost:8000/health | Liveness API |
| http://localhost:8080 | Adminer (serveur `postgres`, user/mdp `digiscore`) |

`.env` : `DATABASE_URL`, `VITE_API_URL` — copier [.env.example](.env.example).

Logins démo : `agent` / `chef` / `cic`, mot de passe **`demo`**. Header `Authorization: Bearer <token>`.

Sécu SI (pilote, pas de code) : [docs/SECURITE_ECHANGES_PILOTE.md](docs/SECURITE_ECHANGES_PILOTE.md).

## Cas démo (pitch 3 minutes)

| Membre | Scénario |
|--------|----------|
| MEM-001 Kodjo Mensah | Bon payeur → score haut, `MONTANT_OK` → chef valide |
| MEM-004 Aisha Slim | Thin-file + RCSD insuffisant → `KNOCKOUT_RCSD` |
| MEM-009 Isaac Gbeglo | 10 M + cautions → file **CIC** voie exceptionnelle |
| MEM-010 Compte Gele | Compte gelé → aucune demande |

## Guides collègues

| Fichier | Public |
|---------|--------|
| [docs/ARCHI.md](docs/ARCHI.md) | Tous — sidecar, ports, flux, IN/OUT |
| [docs/GUIDE_SCORING.md](docs/GUIDE_SCORING.md) | Moteur — contrat `DossierInput` / `ScoreResult`, pas de SQL |
| [docs/GUIDE_FRONTEND.md](docs/GUIDE_FRONTEND.md) | UI — clés JSON, pagination, pages → endpoints |
| [docs/PROMPT_AGENT_FRONTEND.md](docs/PROMPT_AGENT_FRONTEND.md) | Brief à coller dans l’agent IA du front |
| [docs/SYNTHESE_RESPONSABLE_FRONTEND.md](docs/SYNTHESE_RESPONSABLE_FRONTEND.md) | Note front — Bearer, `.items`, mapping écrans |
| [docs/SYNTHESE_RESPONSABLE_SCORING.md](docs/SYNTHESE_RESPONSABLE_SCORING.md) | Note scoring — 14 bugs à eux, ML masqué |
| [docs/DONNEES_RESPONSABLE_MODELE.md](docs/DONNEES_RESPONSABLE_MODELE.md) | Scoring — mix 120k, deux cahiers, dates, reco vs décision |
| [docs/PLAN_ROBUSTESSE_DONNEES.md](docs/PLAN_ROBUSTESSE_DONNEES.md) | Data — dates schéma avant CSV « plus réels » |
| [docs/SECURITE_ECHANGES_PILOTE.md](docs/SECURITE_ECHANGES_PILOTE.md) | HMAC agence **si retenus** (spec, pas le code démo) |
| [docs/postman/README.md](docs/postman/README.md) | Smoke Swagger / Postman |

## Plan H0–H72

| Bloc | Focus |
|------|--------|
| H0–H8 | Schéma membre + seeds + SPEC plafond |
| H8–H24 | UI membre + collecte + CAF/RCSD |
| H24–H40 | Score + plafond + messages |
| H40–H52 | Mémo, décision, amortissement |
| H52–H60 | Maquettes M6/M7 |
| H60–gel | E2E + pitch |

**IN 72 h** : M1–M5, 12 profils, 3 rôles, sidecar documenté. **OUT** : core banking / BIC / Flooz live, ML réel, M6/M7 temps réel, SSO, i18n éwé.

## Contraintes CIF

- Sidecar : pas de greffe sur le transactionnel, tables `digiscore_*` ADD-only.
- Android / Windows, PWA mode dégradé, données **synthétiques**.
- Git + README ; gel J3 14h.

## Ressources

| | Démo | Pilote |
|--|------|--------|
| CPU | 2–4 vCPU | 4–8 vCPU |
| RAM | 4–8 Go | 8–16 Go |
| Disque | 10–20 Go | 50–100 Go SSD |

## Docs

- [CDC](docs/CDC_DigiScore-WA_complet.md) · [Guide équipe](docs/GUIDE_EQUIPE.md) · [Architecture (court)](docs/architecture.md)
- [Mapping SI](docs/mapping_si.md) · [Workflow](docs/workflow-roles.md) · [Pitch](docs/PITCH_DIFFERENCIATION.md)
- [SPEC scoring](scoring/SPEC.md) · [OpenAPI](docs/openapi.json)
