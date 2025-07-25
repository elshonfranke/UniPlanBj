import os

# filepath: c:\Users\Frankel\hackathon\UniPlanBj\app\config.py
class Config:
    SECRET_KEY = 'un_secret_unique_et_long_ici'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://uniplan:4011@localhost/UNIPLANBJ'
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # PIN de sécurité pour les actions administrateur. À CHANGER EN PRODUCTION!
    ADMIN_PIN = '200716'

    # Configuration de Flask-Mail (exemple avec Gmail)
    # IMPORTANT: Utilisez des variables d'environnement en production
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # Votre adresse e-mail
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # Le mot de passe d'application de votre e-mail
    MAIL_DEFAULT_SENDER = MAIL_USERNAME