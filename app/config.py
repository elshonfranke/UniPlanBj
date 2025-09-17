import os

# filepath: c:\Users\Frankel\hackathon\UniPlanBj\app\config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'un_secret_unique_et_long_ici'
    # Exemple de connexion à Supabase (PostgreSQL)
    # On s'assure que la variable d'environnement DATABASE_URL est bien définie.
    # Si elle est manquante, l'application ne démarrera pas, ce qui est un comportement sûr.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("La variable d'environnement DATABASE_URL n'est pas définie. Veuillez la configurer dans votre fichier .env.")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_PIN = '200716'
    VAPID_PRIVATE_KEY = 'Ed2-cT_5rJoGwzlcaQILuibHyB4751wVQiCzJ-EMXr0'
    VAPID_PUBLIC_KEY = 'BAr-rAH_LpggiOQFSOi9ja_oUb3VTqwql0112ibYbpkHCzbGSiWz2WXVESputlXPzuwaFfP6u2YemrJNEOjaQTQ'
    VAPID_CLAIMS = {
        'sub': 'mailto:votre.email@example.com'
}
    # Configuration de Flask-Mail (exemple avec Gmail)
    # IMPORTANT: Utilisez des variables d'environnement en production
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # Votre adresse e-mail
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # Le mot de passe d'application de votre e-mail
    MAIL_DEFAULT_SENDER = MAIL_USERNAME