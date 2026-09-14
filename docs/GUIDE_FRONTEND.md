# Guide frontend — DigiScore-WA

**Brief agent IA (A→Z, à coller tel quel)** : [PROMPT_AGENT_FRONTEND.md](PROMPT_AGENT_FRONTEND.md).  
**Note courte (auth + `.items`)** : [SYNTHESE_RESPONSABLE_FRONTEND.md](SYNTHESE_RESPONSABLE_FRONTEND.md).

Tu consommes **uniquement** l’API JSON. Les formules (CAF, RCSD, EBE, score /100, plafond) sont calculées par le package `scoring` via le back. **Interdit** de les recoder dans React.

## Lancer

```bash
docker compose up -d          # BDD (+ CSV volume si LOAD_VOLUME=1)
# API (autre terminal)
source .venv/bin/activate     # pip install -r requirements.txt déjà fait
cd backend && uvicorn app.main:app --reload --port 8000
# UI
cd frontend && npm install && npm run dev
```

| Variable | Valeur |
|----------|--------|
| `VITE_API_URL` | `http://localhost:8000` ([../frontend/.env.example](../frontend/.env.example)) |

Swagger : http://localhost:8000/docs  
OpenAPI figé : [openapi.json](openapi.json)  
Postman + scénarios : [postman/README.md](postman/README.md)

Logins démo : `agent` / `chef` / `cic`, mot de passe **`demo`**.

Header : `Authorization: Bearer <access_token>` (réponse de `POST /auth/login`).

Sans token → 401. Agent sur `/files/cic` → 403.

**P0 pagination** : les listes sont `{ items, page, page_size, total }` — itère sur `.items` (membres, demandes, files, **mouvements**).

## JSON FR, pas les colonnes SQL

La BDD est en anglais (`member.external_code`). L’API reste en français. Exemples :

| API (à binder) | SQL (ne pas utiliser) |
|----------------|------------------------|
| `code_externe` | `member.external_code` |
| `montant_demande` | `credit_application.requested_amount` |
| `epargne_moy_6m` | `savings_snapshot.avg_balance_6m` |
| `message_code` / `message_humain` | `score_result.message_code` |
| `montant_eligible` | `score_result.eligible_amount` |

Statuts membre / compte : `actif`, `gele` (et éventuellement `radie`). Une demande est impossible si membre ou compte ≠ `actif` (`COMPTE_INACTIF` / `NON_MEMBRE`).

Statuts demande : `brouillon`, `analyse`, `soumis_chef`, `renvoye`, `soumis_cic`, `accorde`, `conditionne`, `refuse`, `clos`.

## Pagination (120k membres)

`GET /membres` et `GET /demandes` (et files chef/CIC) ne renvoient **plus** un tableau nu :

```json
{ "items": [ ... ], "page": 1, "page_size": 30, "total": 120012 }
```

Query : `q`, `page`, `page_size` (max 100). `q` cherche `code_externe`, nom, prénom, **numéro de compte**.

Ne charge pas 120k d’un coup. Infinite scroll / pager sur `total`.

## Pages obligatoires → endpoints

| Écran | Endpoint | Notes |
|-------|----------|--------|
| Login 3 rôles | `POST /auth/login` | `{ "login": "agent", "password": "demo" }` → token + `user` |
| Lookup membre | `GET /membres?q=&page=&page_size=` | Afficher `statut` (geler = pas de nouvelle demande) |
| Fiche | `GET /membres/{id}` | Agence, compte local, totaux, `nb_comptes_externes`, `thin_file` |
| Historique | `GET /membres/{id}/historique` | Crédits + incidents + **30 mvts agence** + résumé ailleurs (pas un alias de la fiche) |
| Mouvements agence | `GET /membres/{id}/mouvements?page=` | `{ items, page, page_size, total }` |
| Ailleurs (COOPEC/banque/IMF) | `GET /membres/{id}/comptes-externes` · `/mouvements-externes` | **Pas** Flooz / T-Money ; pas mélangé au livre agence |
| Agences / IF / enums | `GET /agences` · `/institutions` · `/referentiels` · `/moi` | Bearer ; `/moi` = même `user` que le login |
| Produits | `GET /produits` | Seuil caution, flag exceptionnel |
| Dossier | `GET /demandes/{id}` | Membre, produit, collecte A–E, trésorerie 12 mois, score courant |
| Historique score | `GET /demandes/{id}/scores` | Lignes `score_result_history` |
| Wizard A–E | `POST /demandes` puis `POST /demandes/{id}/collecte` | Clés collecte = `ca`, `cmv`, `charges_exploitation`… |
| Pièces / OCR | `POST /demandes/{id}/pieces` | `qualite_ocr` `flou`/`sombre`/`coupe` → 400, refaire la photo |
| Résultat demandé vs éligible | `POST /demandes/{id}/analyser` + `GET /demandes/{id}` | Afficher `montant_demande` vs `score.montant_eligible`, zone, `message_humain` |
| Mémo | `GET /demandes/{id}/memo` | 6 rubriques déjà listées |
| Amortissement | `GET /demandes/{id}/amortissement` | Sur le montant **éligible** |
| Soumission | `POST /demandes/{id}/soumettre` | → `file`: `chef` ou `cic` |
| File chef | `GET /files/chef?page=` | Décision `POST /demandes/{id}/decision` |
| File CIC | `GET /files/cic?page=` | Idem, niveau `cic` |
| Maquette M6 | `GET /vision/portefeuille` | PAR + alertes (pas live) |
| Maquette M7 | `GET /vision/recouvrement` | 4 niveaux |

Décision : `{ niveau, avis, motif, override }` — **plus de `utilisateur_id`** (pris dans le JWT). Motif **obligatoire** si écart à la recommandation.

Zones score (affichage, déjà dans `score.zone`) : `rejet` · `analyse` · `approbation`.

## Ce que tu ne touches pas

- `scoring/` et toute formule financière
- `backend/db/schema.sql` / seeds
- Renommer un `message_code` (ping scoring + back)
- Brancher un autre backend que `VITE_API_URL`

Cas démo pitch : MEM-001 (chef), MEM-004 (thin-file), MEM-009 (CIC), MEM-010 (compte gelé, aucune demande).
