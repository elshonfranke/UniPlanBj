from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db # Importe l'instance de la base de données
# ...existing code...
from app.models import Utilisateur, Cours, CoursAffectation, Notification, RoleEnum, Filiere, Niveau, Groupe
from app import login_manager
# ...existing code...
# Crée un Blueprint pour les routes principales
main_bp = Blueprint('main', __name__)
@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))
@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Ici tu peux passer les variables nécessaires à ton template dashboard.html
    return render_template('dashboard.html')
@main_bp.route('/')
@main_bp.route('/base')
def index():
    # Route pour la page d'accueil publique
    # Redirige vers le tableau de bord si l'utilisateur est déjà connecté
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')
# ...existing code...



