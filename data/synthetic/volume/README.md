# Jeu volumétrique SFD (~120 000 membres uniques)

Histoires **différentes** (RNG par membre). Mix thin / gelé / late / saisonnier / ancien. Ledger ailleurs = autre COOPEC / banque / IMF seulement (**pas** Flooz). Demandes complètes : `VOLUME_APPLICATIONS` (défaut 20000).

```bash
# recommandé : service Compose db-seed (génère si absent, skip si seed_meta=v2)
docker compose up -d
# reset + reload v2 (obligatoire si volume v1 déjà chargé)
docker compose down -v && docker compose up -d
# manuel depuis la racine du repo
python backend/db/seed/generate_volume_csv.py
python backend/db/seed/load_volume_csv.py
```

Variables : `VOLUME_MEMBERS` (défaut 120000), `VOLUME_APPLICATIONS` (20000), `VOLUME_DIR`. Itération laptop : `VOLUME_MEMBERS=5000`.

Les CSV sont générés localement (lourds, pas versionnés). Voir `MANIFEST.txt` après génération.
