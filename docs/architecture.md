# Architecture DigiScore-WA

Copilote d’éligibilité et de plafond pour les institutions CIF. Sidecar : à côté du SI, jamais dedans.

Guide collègues (complet) : [ARCHI.md](ARCHI.md).

## Stack

React PWA → FastAPI → package `scoring` (règles) → PostgreSQL.

```text
Agent / Chef / CIC
        │
   React PWA :5173
        │  VITE_API_URL
   FastAPI :8000
     ├── adapters/   stub aujourd’hui, API agence en pilote
     ├── dossier_builder → digiscore.pipeline.run
     └── PostgreSQL :5432  (tables métier + digiscore_*)
```

## Sidecar / anti-greffe

- Lecture membre / historique via passerelle API (stub = Postgres local).
- Écriture uniquement dans nos objets (`score_result`, `decision`, `audit_log`, `digiscore_member_map`).
- Interdit : ALTER / DROP des tables partenaires, triggers sur le transactionnel, remplacer le core banking.

## Topologies agences

`agency.topology` = `partagee` (une base, plusieurs points de vente) ou `divisee` (base locale + synchro). Le modèle porte `agency_id` ; DigiScore ne suppose pas une BDD nationale unique.

## ADD-only

En pilote : scripts `CREATE TABLE` pour les objets `digiscore_*` et les tables d’octroi que l’institution autorise. Références SI = IDs métier (`member.external_code`), pas de FK physique obligatoire vers le partenaire.

## Adapters

`AdapterHistorique` : interface unique. `AdapterStub` lit le seed. En pilote on swap `AdapterApiAgence` sans toucher au moteur ni au front.

## Perf 1M+

Index lookup `member.external_code` / `account.account_no`. Historique : LIMIT + `savings_snapshot`. Files paginées par `status`. Volumétrie : service Compose `db-seed` (`generate_volume_csv.py` + `load_volume_csv.py`). Flag `LOAD_VOLUME=0` = 12 profils seulement.

## Ressources

| Contexte | CPU | RAM | Disque |
|----------|-----|-----|--------|
| Démo laptop | 2–4 vCPU | 4–8 Go | 10–20 Go |
| Pilote agence | 4–8 vCPU | 8–16 Go | 50–100 Go SSD |

Pas de GPU, pas de cluster K8s au pilote, pas de droits DROP/ALTER partenaires.

Auth démo 3 rôles (JWT) : simule le flux. Greffe SI (HMAC agence) : [SECURITE_ECHANGES_PILOTE.md](SECURITE_ECHANGES_PILOTE.md) — **si retenus**, pas dans le code démo.
