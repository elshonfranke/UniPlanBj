from functools import wraps
from flask import flash, redirect, url_for, session, request
from flask_login import current_user

def role_required(*roles):
    """
    Décorateur qui restreint l'accès aux utilisateurs ayant des rôles spécifiques.
    Pour les administrateurs, une vérification par PIN est également requise.
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
            
            # Si le rôle requis est 'administrateur', on vérifie le PIN,
            # sauf pour la page de vérification elle-même pour éviter une boucle.
            if 'administrateur' in roles and request.endpoint != 'main.admin_verify_pin':
                if not session.get('admin_pin_verified', False):
                    session['next_url_after_pin'] = request.full_path
                    flash("Pour des raisons de sécurité, veuillez entrer votre code PIN.", "info")
                    return redirect(url_for('main.admin_verify_pin'))
            
            # Si tout est bon, on exécute la fonction de la route originale
            return f(*args, **kwargs)
        return decorated_function
    return wrapper