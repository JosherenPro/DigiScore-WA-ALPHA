# Note — responsable frontend

À : owner de la PWA `frontend/`  
De : backend  
Objet : contrat **actuel** (auth + pagination + **fiche / 2 cahiers**). Le squelette casse encore 3 écrans.

Guides : [GUIDE_FRONTEND.md](GUIDE_FRONTEND.md) · Swagger live : http://localhost:8000/docs · figé : [openapi.json](openapi.json) · Postman : [postman/README.md](postman/README.md).

Tu ne touches pas à `backend/`, `scoring/`, `schema.sql`. Tu consommes l’API JSON **FR**.

---

## P0 — ça casse la démo aujourd’hui

Quatre listes renvoient une **enveloppe**, plus un tableau nu :

```json
{ "items": [ ... ], "page": 1, "page_size": 30, "total": 120012 }
```

| Route | Usage écran |
|--------|-------------|
| `GET /membres` | lookup agent |
| `GET /demandes` | dossiers |
| `GET /files/chef` | file chef |
| `GET /files/cic` | file CIC |

Dans `frontend/src` il n’y a **aucune** lecture de `.items`. `rows.map` sur l’objet page → `TypeError` à l’accueil agent, recherche membre, files chef **et** CIC.

Corrige `api/client.ts` en premier. `page_size` max = 100. Recherche `q` : code membre, nom, prénom, **numéro de compte**. Ne charge pas 120k.

---

## Breaking auth (déjà en prod locale)

| Avant | Maintenant |
|--------|------------|
| `POST /auth/login` `{ login }` seul | `{ "login": "agent", "password": "demo" }` |
| pas de token | `{ access_token, token_type: "bearer", user }` |
| `utilisateur_id` en query / body | **interdit** — identité = JWT |

Tous les appels métier : `Authorization: Bearer <access_token>`.

Sans token → **401**. Agent sur `/files/cic` ou avis `niveau: "cic"` → **403**.

| Écran | `login` | `password` | `user.role` |
|--------|---------|------------|-------------|
| Agent | `agent` | `demo` | `agent` |
| Chef | `chef` | `demo` | `chef_agence` |
| CIC | `cic` | `demo` | `cic` |

Stocke **le token** + `user` (plus seulement `id`). Décision : `{ niveau, avis, motif, override }` — **pas** `utilisateur_id`. Soumettre : `POST /demandes/{id}/soumettre` **sans** query `utilisateur_id`.

Le contrat endpoint par endpoint [API_ENDPOINTS_REPONSES.md](API_ENDPOINTS_REPONSES.md) est aligné (plus de `utilisateur_id`).

---

## Mapping écran → API

| Écran | Appel | Note |
|--------|--------|------|
| Login | `POST /auth/login` | body login + password |
| Lookup | `GET /membres?q=&page=&page_size=` | itère `.items` ; `statut` `gele` = pas de nouvelle demande |
| Fiche | `GET /membres/{id}` | agence, compte **local**, totaux, `nb_comptes_externes`, `thin_file` |
| Historique | `GET /membres/{id}/historique` | crédits (`source` + institution), incidents, **30 mvts agence**, totaux ; **pas** un alias de la fiche |
| Mouvements agence | `GET /membres/{id}/mouvements?page=` | `{ items, page, page_size, total }` — livre **ici** |
| Ailleurs | `GET /membres/{id}/comptes-externes` · `/mouvements-externes` | autre COOPEC / banque / IMF — **jamais** mélangé au livre agence ; pas Flooz |
| Session | `GET /moi` | même `user` que le login |
| Produits | `GET /produits` | seuil caution, `exceptionnel` |
| Créer | `POST /demandes` | membre + produit |
| Collecte A–E | `POST /demandes/{id}/collecte` | clés FR (`ca`, `cmv`, …) |
| Pièces | `POST /demandes/{id}/pieces` | `qualite_ocr` ≠ `ok` → 400, reprendre la photo |
| Score | `POST /demandes/{id}/analyser` | afficher demandé vs `montant_eligible`, `zone`, `message_humain` |
| Dossier | `GET /demandes/{id}` | membre résumé, collecte A–E, trésorerie 12 mois, score **courant**, ratios |
| Scores | `GET /demandes/{id}/score` · `/scores` | courant vs historique `score_result_history` |
| Mémo | `GET /demandes/{id}/memo` | 6 rubriques, pas de PDF |
| Amortissement | `GET /demandes/{id}/amortissement` | sur le montant **éligible** |
| Soumettre | `POST /demandes/{id}/soumettre` | réponse `file`: `chef` ou `cic` |
| File chef | `GET /files/chef?page=` | `.items` |
| File CIC | `GET /files/cic?page=` | agent = 403 |
| Décision | `POST /demandes/{id}/decision` | motif si override ; avis inconnu = 400 |
| M6 / M7 | `GET /vision/portefeuille` · `/recouvrement` | maquette, titre « pas le live » |
| Flags | `GET /capabilities` | tout à `false` — **masquer** anomalies / simu / early-warning |
| Santé | `GET /health` | `database`: `ok` ou `down` |

---

## Référentiels

Bearer obligatoire.

| Route | Contenu |
|--------|---------|
| `GET /agences` | `id, code, nom, ville, topologie` |
| `GET /institutions` | autres IF seed (`coopec` / `banque` / `microfinance`) — **pas** mobile money |
| `GET /referentiels` | enums (statuts, avis, niveaux, zones, preuves, types_piece, `qualite_ocr`) |
| `GET /moi` | même payload `user` que le login |
| `GET /produits` | 3 produits seed |

**Pas** un dump SQL. **Pas** Flooz / T-Money / wallets. **Pas** cette vague : `/demandes/{id}/anomalies`, `/simuler`, `/portefeuille/alertes`. Si `capabilities.*` est `false`, l’écran n’offre pas le bouton.

---

## Swagger

| Source | Rôle |
|--------|------|
| http://localhost:8000/docs | **Live** — Authorize (Bearer) puis essayer |
| http://localhost:8000/openapi.json | Même schéma, généré par FastAPI 0.3.0 |
| [docs/openapi.json](openapi.json) | Copie figée du repo (`python backend/scripts/export_openapi.py`) |
| [docs/openapi.json](openapi.json) | Contrat figé — généré depuis le serveur lancé |

En cas de conflit : **live `/docs`** > `openapi.json` > ce MD.

---

## Cas pitch (souris)

1. **agent** → MEM-001 → analyser → score haut → soumettre → file **chef**.
2. MEM-004 → `thin_file` + message historique / RCSD.
3. MEM-009 → `VOIE_EXCEPTIONNELLE` → file **CIC**.
4. MEM-010 → **pas** de bouton nouvelle demande (`gele`).
5. Login **chef** : file, valider ou renvoyer (motif si écart).
6. Login **cic** : MEM-009, accorder / refuser.
7. Recherche `VOL-` : page de 30, `total` énorme, UI qui ne gèle pas.

Zones : `rejet` · `analyse` · `approbation` (déjà dans `score.zone`). Score **/100**.

Interdit : recalculer CAF / RCSD / plafond dans React. Tu **affiches** `score` et `ratios`.
