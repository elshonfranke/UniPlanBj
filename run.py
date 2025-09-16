import os
from app import create_app  # Module où create_app est défini

app, socketio = create_app()

if __name__ == '__main__':
    # Railway fournit le port via la variable d'environnement PORT
    port = int(os.environ.get('PORT', 5000))
    
    # debug=True pour dev, enlever en prod
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
