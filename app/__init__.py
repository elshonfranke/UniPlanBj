from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate # Importer Flask-Migrate
import os
from dotenv import load_dotenv
from flask_socketio import SocketIO
from supabase import create_client, Client

from app.config import Config # Importe votre classe de configuration

# Initialisation des extensions
db = SQLAlchemy() # Garder l'initialisation de SQLAlchemy
mail = Mail()
supabase: Client = None # Instance du client Supabase, initialisée dans create_app
login_manager = LoginManager()
login_manager.login_view = 'main.login' # Nom de la vue de connexion, si l'utilisateur n'est pas authentifié
socketio = SocketIO()

def create_app(db_config=None):
    # Charger les variables d'environnement depuis le fichier .env
    # Ne pas forcer l'encodage ici pour éviter les erreurs si le fichier est en ANSI/Windows
    load_dotenv()

    app = Flask(__name__)
    # Charge la configuration depuis l'objet Config, qui gère déjà les variables d'environnement.
    app.config.from_object(Config)

    if db_config:
        app.config.update(db_config)

    # Appeler la méthode statique pour finaliser la configuration (ex: construire l'URI de la BDD)
    # C'est ici que l'URI de la base de données sera réellement construite.
    Config.init_app(app)

    # Initialisation du client Supabase
    # On utilise une variable globale pour la rendre accessible dans toute l'application.
    global supabase
    supabase = create_client(app.config["SUPABASE_URL"], app.config["SUPABASE_KEY"])

    # Initialise les extensions avec l'application Flask
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    Migrate(app, db) # Initialiser Flask-Migrate
    socketio.init_app(app)

    @app.before_request
    def before_request_callback():
        """
        Met à jour le champ 'last_seen' de l'utilisateur avant chaque requête.
        """
        from flask_login import current_user
        from datetime import datetime
        if current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
            db.session.commit()

    # Importation et enregistrement des Blueprints et des commandes CLI
    from app.routes import main_bp
    from app import commands

    app.register_blueprint(main_bp)
    commands.init_app(app)

    return app, socketio
