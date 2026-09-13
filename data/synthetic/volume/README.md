# Jeu volumétrique SFD (~120 000 membres)

Simule un portefeuille COOPEC : membres, comptes, mouvements, crédits passés, incidents, BIC, demandes + collecte, suivi PAR / recouvrement.

```bash
# recommandé : service Compose db-seed (génère si absent, skip si seed_meta)
docker compose up -d
# manuel depuis la racine du repo
python backend/db/seed/generate_volume_csv.py
python backend/db/seed/load_volume_csv.py
```

Variables : `VOLUME_MEMBERS` (défaut 120000), `VOLUME_APPLICATIONS` (8000), `VOLUME_DIR`.

Les CSV sont générés localement (lourds, pas versionnés). Voir `MANIFEST.txt` après génération.
