from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from app.config import Config # Importe votre classe de configuration

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Nom de la vue de connexion, si l'utilisateur n'est pas authentifié

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) # Charge les configurations depuis config.py

    # Initialise les extensions avec l'application Flask
    db.init_app(app)
    login_manager.init_app(app)

    from . import models

    # Importation et enregistrement des Blueprints (si vous en utilisez, sinon les routes directes)
    from app.routes import main_bp
    #from app.routes import auth_bp # Supposons que vous ayez un blueprint pour l'authentification

    app.register_blueprint(main_bp)
    #app.register_blueprint(auth_bp, url_prefix='/auth') # Les routes auth seront sous /auth/login, etc.

    # Optionnel: Créer la base de données si elle n'existe pas
    # Ceci est utile pour la première exécution ou les tests
    with app.app_context():
        db.create_all() # Crée toutes les tables définies dans models.py

    return app
