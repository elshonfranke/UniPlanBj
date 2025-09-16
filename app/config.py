import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'un_secret_unique_et_long_ici'

    # Configuration de la base de données pour Railway
    # On utilise les noms de variables standards fournis par Railway (MYSQLHOST, MYSQLUSER, etc.)
    DB_USER = os.environ.get('MYSQLUSER')
    DB_PASSWORD = os.environ.get('MYSQLPASSWORD')
    DB_HOST = os.environ.get('MYSQLHOST')
    DB_NAME = os.environ.get('MYSQLDATABASE')
    DB_PORT = os.environ.get('MYSQLPORT', 3306)

    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_PIN = os.environ.get('ADMIN_PIN') or '200716' # Utiliser une variable d'environnement en priorité

    # Configuration Flask-Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = MAIL_USERNAME
