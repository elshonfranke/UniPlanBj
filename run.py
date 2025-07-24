# run.py
from app import create_app  # Change 'app' to the actual module name where create_app is defined

app = create_app()

if __name__ == '__main__':
    # Démarre le serveur de développement Flask
    # debug=True active le mode débogage (rechargement auto, débogueur interactif)
    # Utile pour le développement, mais JAMAIS en production !
    app.run(debug=True, port=5200)