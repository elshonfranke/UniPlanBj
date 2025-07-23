from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from app.config import Config # Importe votre classe de configuration

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Nom de la vue de connexion, si l'utilisateur n'est pas authentifié

def seed_data(app):
    """Remplit la base de données avec les données initiales si nécessaire."""
    with app.app_context():
        from .models import Niveau
        # Vérifie si la table Niveau est vide
        if Niveau.query.count() == 0:
            print("Base de données 'Niveau' vide. Remplissage...")
            niveaux_a_ajouter = [
                Niveau(nom_niveau='Licence 1 (L1)'),
                Niveau(nom_niveau='Licence 2 (L2)'),
                Niveau(nom_niveau='Licence 3 (L3)'),
                Niveau(nom_niveau='Master 1 (M1)'),
                Niveau(nom_niveau='Master 2 (M2)')
            ]
            db.session.bulk_save_objects(niveaux_a_ajouter)
            db.session.commit()
            print("Niveaux d'étude ajoutés.")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) # Charge les configurations depuis config.py

    # Initialise les extensions avec l'application Flask
    db.init_app(app)
    login_manager.init_app(app)

    # Importation et enregistrement des Blueprints (si vous en utilisez, sinon les routes directes)
    from app.routes import main_bp

    app.register_blueprint(main_bp)

    # Crée les tables et remplit les données initiales
    with app.app_context():
        db.create_all() # Crée toutes les tables définies dans models.py
        seed_data(app) # Appelle la fonction pour remplir les données

    return app
