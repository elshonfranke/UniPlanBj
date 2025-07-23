from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """
    Décorateur qui restreint l'accès aux utilisateurs ayant des rôles spécifiques.
    """
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # D'abord, on vérifie si l'utilisateur est connecté
            if not current_user.is_authenticated:
                flash("Veuillez vous connecter pour accéder à cette page.", "info")
                return redirect(url_for('main.login'))
            
            # Ensuite, on vérifie si l'utilisateur a l'un des rôles requis
            if current_user.role not in roles:
                flash("Vous n'avez pas les permissions nécessaires pour accéder à cette page.", 'danger')
                return redirect(url_for('main.dashboard'))
            
            # Si tout est bon, on exécute la fonction de la route originale
            return f(*args, **kwargs)
        return decorated_function
    return wrapper