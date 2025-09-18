# run.py
import os
from dotenv import load_dotenv
import sys

# --- SOLUTION DÉFINITIVE POUR UNICODEDECODEERROR SUR WINDOWS ---
# Force Python à utiliser l'encodage UTF-8 pour toutes les interactions.
if sys.version_info.major == 3 and sys.version_info.minor >= 7:
    os.environ['PYTHONUTF8'] = '1'

# Load environment variables from .env file
load_dotenv()

# Ensure PostgreSQL client uses UTF-8 when decoding any libpq text
os.environ.setdefault('PGCLIENTENCODING', 'UTF8')

from app import create_app

# La configuration est maintenant gérée directement dans create_app.
# Il suffit d'appeler la factory sans argument.
app, socketio = create_app()

if __name__ == '__main__':
    # Démarre le serveur de développement Flask
    # debug=True active le mode débogage (rechargement auto, débogueur interactif)
    # Utile pour le développement, mais JAMAIS en production !
    socketio.run(app, debug=True, port=5100)