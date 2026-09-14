# Manques identifiés — Backend DigiScore-WA

État des lieux du code actuel (`app/`, `db/`), pas une todolist de features métier (déjà couvertes par `db/README.md` — section "Hors BDD volontaire (OUT 72h)"). Ici : ce qui manque ou qui est fragile dans ce qui existe déjà.

## 🔴 Sécurité / Auth

- **Login sans mot de passe.** [routes.py:75-80](app/api/routes.py#L75-L80) authentifie juste par `login` (`"agent"`, `"chef"`, `"cic"`) — pas de mot de passe, pas de JWT, pas de session. Documenté comme volontaire dans `main.py` ("Login démo... Pas de JWT") mais aucun contrôle ne remplace ça : n'importe quel client qui connaît un login devient CIC.
- **`utilisateur_id` fourni par le client, jamais vérifié.** `soumettre()` ([routes.py:449](app/api/routes.py#L449)) et `decision()` (via `DecisionIn.utilisateur_id`, [dossier.py:44](app/schemas/dossier.py#L44)) prennent l'id utilisateur en paramètre de requête / body, sans lien avec une session authentifiée. Un agent peut signer une décision au nom d'un autre user_id.
- **Aucune autorisation par rôle sur les routes.** Rien n'empêche un "agent" d'appeler `/demandes/{id}/decision` avec `niveau: "cic"`, ou de lire `/files/cic`. Le rôle n'est vérifié nulle part côté serveur.
- **`AppUser` n'a pas de champ mot de passe** ([tables.py:31-37](app/models/tables.py#L31-L37)) — il faudrait `password_hash` si une vraie authentification est ajoutée un jour.

## 🟠 Fiabilité / Bugs

- **Date figée en dur.** `get_membre()` utilise `date(2026, 9, 13)` comme "aujourd'hui" ([routes.py:151](app/api/routes.py#L151)) au lieu de `date.today()`. Le calcul d'ancienneté (`anciennete_mois`, donc le flag `thin_file`) sera faux dès que cette date ne correspond plus au présent.
- **`decision()` ignore silencieusement un `avis` inconnu.** La chaîne if/elif ([routes.py:502-516](app/api/routes.py#L502-L516)) ne couvre que des valeurs précises (`renvoyer`, `escalader`, `accorder`, `valider`, `conditionner`, `refuser`) ; un avis mal orthographié ou hors liste ne déclenche aucune erreur — la `Decision` et l'`AuditLog` sont quand même enregistrés, mais `app.status` ne change pas, sans que l'appelant soit prévenu.
- **`/health` ne vérifie pas la DB.** ([main.py:34-36](app/main.py#L34-L36)) renvoie toujours `{"status": "ok"}` même si Postgres est injoignable — un healthcheck de déploiement ne détecterait pas une DB down.
- **Pas de retry/backoff sur la connexion DB au démarrage.** `create_engine(..., pool_pre_ping=True)` ([db.py:11](app/db.py#L11)) ne fait que vérifier la connexion avant chaque usage ; si Postgres n'est pas encore prêt au tout premier appel (cold start docker-compose), la requête échoue au lieu d'attendre/réessayer.
- **`historique()` duplique `get_membre()` sans rien ajouter** ([routes.py:194-196](app/api/routes.py#L194-L196)) — même réponse, même `response_model`, aucune donnée d'historique en plus (les mouvements de compte, `account_movement`, existent en base mais ne sont exposés nulle part).

## 🟡 Configuration / Ops

- **`.env` non chargé automatiquement.** `.env.example` existe mais rien n'utilise `python-dotenv` (absent de `requirements.txt`) — `DATABASE_URL` doit être exporté manuellement dans le shell avant de lancer uvicorn, sinon fallback silencieux sur `localhost:5432` (voir l'incident de connexion résolu plus tôt).
- **Pas de service `backend` dans `docker-compose.yml`.** Un `Dockerfile` existe ([Dockerfile](Dockerfile)) mais n'est référencé par aucun service compose — le backend ne tourne qu'en local via `uvicorn`, jamais conteneurisé avec le reste de la stack. À clarifier si c'est voulu pour la démo ou un oubli.
- **CORS origins en dur.** `allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]` ([main.py:25](app/main.py#L25)) — pas de variable d'env, à changer manuellement pour tout déploiement hors localhost.
- **Identifiants DB par défaut en clair dans le code** (`digiscore:digiscore`, [db.py:6-9](app/db.py#L6-L9)) — acceptable pour un environnement de démo isolé, à ne jamais réutiliser tel quel en prod.

## ⚪ Qualité / Maintenabilité

- **Aucun test.** Pas de dossier `tests/`, pas de `pytest` dans `requirements.txt` — aucune vérification automatisée du workflow (`analyser` → `soumettre` → `decision`) ni des règles de routage (`next_queue`, `can_chef_close`).
- **Pas de migrations de schéma.** `db/schema.sql` est appliqué tel quel au premier démarrage du conteneur (`docker-entrypoint-initdb.d`) — aucun outil (Alembic ou autre) pour faire évoluer le schéma sur une base déjà peuplée.
- **Pas de logging structuré ni de handler d'exception global.** Une erreur inattendue (ex. DB down) remonte telle quelle (trace Python complète en 500) — pas de mapping vers des réponses d'erreur JSON propres pour le front.
- **`/vision/portefeuille` et `/vision/recouvrement` ne paginent pas** ([routes.py:594-616](app/api/routes.py#L594-L616)) — tout est renvoyé d'un coup ; sans souci au volume actuel (maquette M6/M7), à revoir si ces tables grossissent.

---

*Généré le 2026-09-13 à partir d'une lecture du code (`app/`, `db/`). Les manques métier volontairement hors périmètre (connecteurs live, ML réel, tontine groupe) sont déjà listés dans [db/README.md](db/README.md).*
