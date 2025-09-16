import os
from app import create_app  # Module où create_app est défini

app, socketio = create_app()

if __name__ == '__main__':
    # Railway fournit le port via la variable d'environnement PORT
    port = int(os.environ.get('PORT', 5000))
    
    # Le mode debug ne doit JAMAIS être activé en production.
    # Railway utilisera un serveur de production comme Gunicorn pour lancer l'application.
    # Ce bloc ne sera exécuté que si vous lancez le fichier avec `python run.py` localement.
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode)
