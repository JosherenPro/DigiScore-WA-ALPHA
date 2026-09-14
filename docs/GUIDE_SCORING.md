# Guide scoring — DigiScore-WA

Tu livres un **moteur pur**. Le back assemble le dossier et persiste le résultat. Tu ne parles pas à Postgres.

## Lancer la BDD (pour relire les cas, pas pour coder le package)

```bash
docker compose up -d
```

Adminer : http://localhost:8080 — serveur `postgres`, user/mdp/base `digiscore`.

Laptop lent : `LOAD_VOLUME=0 docker compose up -d` (12 profils, pas 120k).

`.env` à la racine : `DATABASE_URL=postgresql+psycopg://digiscore:digiscore@localhost:5432/digiscore` (le **back** s’en sert, pas `scoring/`).

## Package

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e scoring
pytest scoring/tests
```

Point d’entrée : `from digiscore.pipeline import run` → `run(dossier: DossierInput) -> ScoreResult`.

Spécification : [../scoring/SPEC.md](../scoring/SPEC.md). Types : [../scoring/digiscore/types.py](../scoring/digiscore/types.py).

## Interdit dans `scoring/`

- Import `psycopg` / SQLAlchemy / `DATABASE_URL`.
- Appels HTTP, lecture de fichiers SI.
- ML dans le routage, les knock-outs ou la décision (OUT 72 h).

Si tu as besoin d’un champ : étendre `DossierInput` et **ping le back** (`dossier_builder.py`). Le front n’a pas à connaître le SQL.

## Contrat

**Entrée `DossierInput`** (clés FR) : `membre`, `compte`, `historique`, `demande`, `analyse` (CA, CMV, trésorerie 12 mois, patrimoine, preuves N1–N3).

**Sortie `ScoreResult`** : `eligible`, `thin_file`, `score_global`, `criteres[]`, `knockouts[]`, `montant_demande`, `montant_eligible`, `montant_max_suggestion`, `message_code`, `message_humain`, `explication[]`, `zone`, `financials` (EBE, CAF, RCSD…).

Formules (rappel SPEC, **à implémenter ici seulement**) :

```text
EBE  = CA − CMV − charges_exploitation
CAF  = EBE + produits_financiers + (revenu_perso − charges_fam)
RCSD = CAF / service_dette          # ≥ 1,50 OK ; < 1,00 knockout
```

Zones : 0–40 rejet · 41–70 analyse/CIC · 71–100 approbation.

## Comment le back assemble

[`backend/app/services/dossier_builder.py`](../backend/app/services/dossier_builder.py) lit le schéma **EN** et construit le dict FR attendu par `run()`. Après `POST /demandes/{id}/analyser`, le back écrit `score_result` + `financial_ratio`.

Tu n’as pas besoin de FastAPI pour développer. Optionnel : API sur :8000 puis rejouer les 12 profils.

| Demande seed | Membre | Attendu typique |
|--------------|--------|-----------------|
| 1 | MEM-001 | `MONTANT_OK` / `UPSELL_POSSIBLE` |
| 4 | MEM-004 | `KNOCKOUT_RCSD` (thin-file avec capacité insuffisante) |
| 9 | MEM-009 | `VOIE_EXCEPTIONNELLE` → file CIC |

Swagger : http://localhost:8000/docs · Postman : [postman/README.md](postman/README.md).

## `message_code` — ne pas renommer seul

Liste actuelle (SPEC) : `NON_MEMBRE`, `COMPTE_INACTIF`, `HISTORIQUE_INSUFFISANT`, `EPARGNE_SOUS_SEUIL`, `INCIDENTS_RECENTS`, `MONTANT_PLAFONNE`, `MONTANT_OK`, `UPSELL_POSSIBLE`, `VOIE_EXCEPTIONNELLE`, `REJET_SCORE`, `CAUTION_REQUISE`, `BIC_OU_FISCAL_MANQUANT`, `PREUVES_EXTERNES_MANQUANTES`, `KNOCKOUT_RCSD`, `KNOCKOUT_ESG`.

Tout ajout / rename / suppression = ping **back + front** (workflow, libellés UI).

## Ce que tu ne touches pas

- `frontend/`
- routes FastAPI, schéma SQL, seeds Docker
- formules recopiées dans le front (le front affiche `ScoreResult`, il ne calcule pas)
