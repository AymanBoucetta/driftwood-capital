# Backend — Document Copilot API

## Lancer le serveur

Toujours depuis le dossier `backend/`

uv run uvicorn app.main:app --reload
    - `--reload` : redémarre automatiquement à chaque sauvegarde de fichier
    - App accessible sur `http://127.0.0.1:8000`
    - Doc interactive (Swagger) : `http://127.0.0.1:8000/docs`


## Vérifier que ça tourne

http://127.0.0.1:8000/health    
    Doit retourner `{"status":"ok"}`.


## Gérer les dépendances

uv add <package> # ajouter une dépendance
uv add --dev <package> # ajouter une dépendance de dev (tests, lint...)
uv sync # réinstaller selon pyproject.toml / uv.lock


## Migrations base de données (Alembic)

uv run alembic revision --autogenerate -m "message" # générer une migration
uv run alembic upgrade head # appliquer les migrations

    !Toujours relire une migration générée avant de l'appliquer.


## Variables d'environnement

Toutes dans `backend/.env` (jamais dans `.env.example`, jamais commité). Voir `app/config.py` pour la liste des variables requises..