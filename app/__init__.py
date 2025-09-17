from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate # Importer Flask-Migrate
import os
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv() # Charge les variables d'environnement depuis .env AVANT tout le reste

from app.config import Config # Importe votre classe de configuration

# Initialisation des extensions
db = SQLAlchemy() # Garder l'initialisation de SQLAlchemy
mail = Mail()
login_manager = LoginManager()
login_manager.login_view = 'main.login' # Nom de la vue de connexion, si l'utilisateur n'est pas authentifié
socketio = SocketIO()

def seed_data(app):
    """Remplit la base de données avec les données initiales si nécessaire."""
    with app.app_context():
        from .models import Niveau, Filiere
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
        
        # Vérifie si la table Filiere est vide
        if Filiere.query.count() == 0:
            print("Base de données 'Filiere' vide. Remplissage...")
            filieres_a_ajouter = [
                Filiere(nom_filiere='Intelligence Artificielle (IA)'),
                Filiere(nom_filiere='Système Embarqué et Internet des Objets (SEIOT)'),
                Filiere(nom_filiere='Génie Logiciel (GL)'),
                Filiere(nom_filiere='Sécurité en Informatique (SI)'),
                Filiere(nom_filiere='Internet et Multimédia (IM)'),
                Filiere(nom_filiere='SIRI')
            ]
            db.session.bulk_save_objects(filieres_a_ajouter)
            db.session.commit()
            print("Filières ajoutées.")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) # Charge les configurations depuis config.py

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

    # Importation et enregistrement des Blueprints (si vous en utilisez, sinon les routes directes)
    from app.routes import main_bp

    app.register_blueprint(main_bp)

    # La création des tables est maintenant gérée par Flask-Migrate.
    # db.create_all() est conservé ici pour la première exécution, mais
    # la bonne pratique est de le remplacer par les commandes de migration.
    # Nous le laissons pour l'instant pour assurer la création initiale.
    with app.app_context():
        # La création des tables et le remplissage des données sont maintenant gérés
        # par les commandes `flask db upgrade`.
        # seed_data(app) # Cet appel est maintenant géré par les migrations.
        pass

    return app, socketio
