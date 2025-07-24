import os

# filepath: c:\Users\Frankel\hackathon\UniPlanBj\app\config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'un_secret_unique_et_long_ici'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:Cyrusgnl2007@localhost/UNIPLANBJ'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # PIN de sécurité pour les actions administrateur. À CHANGER EN PRODUCTION!
    ADMIN_PIN = '200716'