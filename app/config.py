import os
from sqlalchemy.engine.url import URL
from urllib.parse import quote_plus


 
# filepath: c:\Users\Frankel\hackathon\UniPlanBj\app\config.py
class Config:
    """
    Configuration class for the Flask app.
    Values are set here as defaults and can be overridden by environment variables.
    Flask will automatically map `FLASK_SECRET_KEY` env var to `SECRET_KEY`.
    """
    # Clé secrète pour la sécurité des sessions et des jetons CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-long-and-unique-secret-key-for-dev')

    # Les variables de la BDD (DB_USER, DB_PASSWORD, etc.) ne sont plus lues ici.
    # Elles seront injectées dans la configuration de l'application au démarrage.
    # Nous définissons ici des valeurs par défaut au cas où.
    DB_DIALECT = os.environ.get('DB_DIALECT', 'postgresql+psycopg')
    DB_USERNAME = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT')
    DB_NAME = os.environ.get('DB_NAME')

    # L'URI de la base de données sera construite dynamiquement
    # lorsque l'application est créée.
    SQLALCHEMY_DATABASE_URI = None

    @staticmethod
    def init_app(app):
        # Les prints sont utiles pour le débogage afin de vérifier les valeurs lues
        print("DB_USER:", repr(app.config['DB_USERNAME']))
        print("DB_PASSWORD:", repr(app.config['DB_PASSWORD']))
        print("DB_HOST:", repr(app.config['DB_HOST']))
        print("DB_PORT:", repr(app.config['DB_PORT']))
        print("DB_NAME:", repr(app.config['DB_NAME']))

        # Normaliser le driver PostgreSQL sur psycopg (v3)
        drivername = (app.config.get('DB_DIALECT') or 'postgresql+psycopg').strip()
        if 'psycopg2' in drivername:
            drivername = drivername.replace('psycopg2', 'psycopg')

        # Échappe les caractères spéciaux dans le mot de passe pour la connexion URL.
        password = str(app.config['DB_PASSWORD']) if app.config['DB_PASSWORD'] else None
        if password:
            password = quote_plus(password, encoding='utf-8')

        app.config['SQLALCHEMY_DATABASE_URI'] = URL.create(
            drivername=drivername,
            username=app.config['DB_USERNAME'],
            password=password,
            host=app.config['DB_HOST'],
            port=app.config['DB_PORT'],
            database=app.config['DB_NAME'],
            query={
                # Supabase requires SSL
                'sslmode': 'require',
            }
        )

        # Debug: print final URI without password for inspection
        try:
            uri_for_log = str(app.config['SQLALCHEMY_DATABASE_URI']).replace(password or '', '***')
            print("SQLALCHEMY_DATABASE_URI:", uri_for_log)
        except Exception as e:
            print("Could not stringify SQLALCHEMY_DATABASE_URI:", e)

        # Ensure SQLAlchemy passes SSL requirement to psycopg2
        app.config.setdefault('SQLALCHEMY_ENGINE_OPTIONS', {})
        engine_opts = app.config['SQLALCHEMY_ENGINE_OPTIONS']
        connect_args = dict(engine_opts.get('connect_args') or {})
        connect_args.setdefault('sslmode', 'require')
        # Force UTF-8 client encoding at connection time for psycopg2/libpq
        connect_args.setdefault('options', '-c client_encoding=UTF8')
        engine_opts['connect_args'] = connect_args
    

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # PIN de sécurité pour les actions admin sensibles
    ADMIN_PIN = os.environ.get('ADMIN_PIN', '200716')

    # Clés VAPID pour les notifications Push Web
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
    # Récupérer l'email pour les VAPID claims de manière sécurisée
    _vapid_email = os.environ.get('MAIL_USERNAME')
    VAPID_CLAIMS = {
        'sub': f"mailto:{_vapid_email}" if _vapid_email else "mailto:default@example.com"
    }
    
    # Configuration pour le client Supabase
    SUPABASE_URL = os.environ.get("SUPABASE_URL", None)
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", None)

    # Configuration de Flask-Mail (exemple avec Gmail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)