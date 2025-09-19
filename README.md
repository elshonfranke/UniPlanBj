## UniPlanBJ

Application Flask de gestion d'emploi du temps et de notifications (étudiants, enseignants, administrateurs) avec Postgres (Supabase), WebSocket, et stockage d'images.

### Prérequis
- Python 3.11
- Accès à une base Postgres (Supabase recommandé)
- Outils de build (Windows: Visual C++ Build Tools si nécessaire)

### Configuration
1) Créez un fichier `.env` à la racine avec au minimum:
```
SECRET_KEY=dev-secret

# Base de données (Supabase)
DB_DIALECT=postgresql+psycopg
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=your_host.supabase.co
DB_PORT=5432
DB_NAME=postgres

# Mail (optionnel pour reset password)
MAIL_SERVER=smtp.googlemail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=

# Supabase (pour le stockage d'images / API)
SUPABASE_URL=
SUPABASE_KEY=

# VAPID (notifications push - optionnel)
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
```

Notes:
- Sous Windows, ne forcez pas `load_dotenv(encoding='utf-8')` si votre `.env` n'est pas encodé en UTF‑8.
- Supabase exige SSL: l'app force `sslmode=require`.
- Si votre hôte DB ne résout qu'en IPv6, activez IPv6 ou utilisez un endpoint IPv4 (PgBouncer) de Supabase.

### Installation
```
python -m venv venv
./venv/Scripts/Activate.ps1  # PowerShell
python -m pip install -r requirements.txt
```

### Initialisation de la base
Autogénérer et appliquer le schéma depuis les modèles:
```
python scripts/make_initial_migration.py
```
Ou appliquer les migrations existantes:
```
python scripts/upgrade_db.py
```

### Lancer l'application (développement)
```
python run.py
```
L'application démarre sur `http://127.0.0.1:5100`.

### Commandes utiles
- Créer un admin:
```
python -m flask --app wsgi:app create-admin <prenom> <nom> <email> <motdepasse>
```

### Dépannage
- UnicodeDecodeError: convertir `.env` en UTF‑8 ou retirer le forçage d'encodage.
- psycopg getaddrinfo failed: problème de DNS/IPv6. Activez IPv6 ou utilisez un endpoint IPv4 (PgBouncer).
- UndefinedTable: exécutez les migrations (voir Initialisation de la base).

### Technologies
- Flask, Flask‑SQLAlchemy, Flask‑Login, Flask‑Migrate
- Flask‑SocketIO
- SQLAlchemy 2.x, psycopg 3
- Supabase (Postgres + Storage)
