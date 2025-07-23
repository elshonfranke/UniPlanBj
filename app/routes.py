from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from app import db
from app import login_manager
from app.models import Utilisateur, Filiere, Niveau, Groupe, Cours, CoursAffectation, Notification
from datetime import datetime
from .decorators import role_required
from sqlalchemy import or_ # Importation de la fonction 'or_' pour les requêtes complexes

# Crée un Blueprint pour les routes principales
main_bp = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Si un étudiant arrive sur le tableau de bord sans avoir complété son profil,
    # on lui affiche un message pour l'inciter à le faire.
    if current_user.role == 'etudiant' and (not current_user.filiere_id or not current_user.niveau_id):
        flash('Pensez à compléter votre profil pour accéder à toutes les fonctionnalités !', 'info')

    # Redirection vers le tableau de bord admin si l'utilisateur est un administrateur
    if current_user.role == 'administrateur':
        return redirect(url_for('main.admin_dashboard'))

    emploi_du_temps = []
    prochain_cours = None
    
    # Logique pour récupérer l'emploi du temps d'un étudiant
    if current_user.role == 'etudiant' and current_user.filiere_id and current_user.niveau_id:
        # 1. Trouver le groupe de l'étudiant
        groupe_etudiant = Groupe.query.filter_by(
            filiere_id=current_user.filiere_id,
            niveau_id=current_user.niveau_id
        ).first()

        if groupe_etudiant:
            # 2. Récupérer les affectations de cours pour ce groupe
            affectations = CoursAffectation.query.filter_by(groupe_id=groupe_etudiant.id).all()
            cours_ids = [affectation.cours_id for affectation in affectations]
            
            # 3. Récupérer les cours correspondants et les trier
            emploi_du_temps = Cours.query.filter(Cours.id.in_(cours_ids)).order_by(Cours.date_cours, Cours.heure_debut).all()

            # 4. Trouver le prochain cours
            now = datetime.now()
            prochain_cours = Cours.query.filter(
                Cours.id.in_(cours_ids),
                Cours.date_cours >= now.date()
            ).order_by(Cours.date_cours, Cours.heure_debut).filter(
                (Cours.date_cours > now.date()) | ((Cours.date_cours == now.date()) & (Cours.heure_fin > now.time()))
            ).first()

    # Logique pour un enseignant
    elif current_user.role == 'enseignant':
        emploi_du_temps = Cours.query.filter_by(enseignant_id=current_user.id).order_by(Cours.date_cours, Cours.heure_debut).all()
        # Vous pouvez ajouter ici la logique pour trouver le prochain cours de l'enseignant

    # Récupérer les notifications pertinentes pour l'utilisateur connecté
    notifications = Notification.query.filter(
        or_(
            Notification.destinataire_role == 'all', # Notifications pour tout le monde
            Notification.destinataire_role == current_user.role, # Notifications pour son rôle
            Notification.destinataire_id == current_user.id # Notifications personnelles
        )
    ).order_by(Notification.date_creation.desc()).limit(5).all()
    
    return render_template('utilisateur/dashboard.html', emploi_du_temps=emploi_du_temps, prochain_cours=prochain_cours, notifications=notifications)

@main_bp.route('/')
@main_bp.route('/base')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        prenom = request.form.get('prenom')
        nom = request.form.get('nom')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if Utilisateur.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for('main.signup'))

        new_user = Utilisateur(prenom=prenom, nom=nom, email=email, role=role)
        new_user.set_password(password) # Utilisation de la méthode du modèle pour hacher le mot de passe
        
        db.session.add(new_user)
        db.session.commit()

        # Connexion automatique de l'utilisateur après l'inscription
        login_user(new_user)
        
        # Redirection intelligente basée sur le rôle
        if new_user.role == 'etudiant':
            flash('Inscription réussie ! Veuillez compléter votre profil.', 'success')
            return redirect(url_for('main.edit_profile'))
        else:
            flash('Inscription réussie ! Bienvenue.', 'success')
            return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = Utilisateur.query.filter_by(email=email).first()

        # Correction de la vérification du mot de passe
        if not user or not user.check_password(password):
            flash("Email ou mot de passe incorrect.", "danger")
            return redirect(url_for('main.login'))

        login_user(user, remember=remember)
        
        # Si l'utilisateur est un étudiant et que son profil est incomplet, on le redirige
        if user.role == 'etudiant' and (not user.filiere_id or not user.niveau_id):
             flash('Veuillez compléter votre profil pour continuer.', 'info')
             return redirect(url_for('main.edit_profile'))

        return redirect(url_for('main.dashboard'))

    return render_template('auth/login.html')

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

@main_bp.route('/admin_dashboard')
@login_required
@role_required('administrateur') # Seuls les administrateurs peuvent accéder
def admin_dashboard():
    # Récupère tous les utilisateurs et les trie par rôle puis par nom
    users = Utilisateur.query.order_by(Utilisateur.role, Utilisateur.nom).all()
    return render_template('admin/dashboard.html', users=users)

@main_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
@role_required('etudiant') # On utilise le décorateur pour restreindre l'accès
def edit_profile():
    if request.method == 'POST':
        filiere_nom = request.form.get('filiere')
        niveau_id = request.form.get('niveau_id')

        # Gestion de la filière : on la crée si elle n'existe pas
        filiere = Filiere.query.filter_by(nom_filiere=filiere_nom).first()
        if not filiere and filiere_nom:
            filiere = Filiere(nom_filiere=filiere_nom)
            db.session.add(filiere)
            db.session.flush() # Pour obtenir l'ID de la nouvelle filière avant le commit
        
        # CORRECTION : On assigne les ID, pas des objets inexistants
        current_user.filiere_id = filiere.id if filiere else None
        current_user.niveau_id = niveau_id if niveau_id else None

        db.session.commit()
        flash('Votre profil a été mis à jour avec succès !', 'success')
        return redirect(url_for('main.dashboard'))
    
    # On passe la liste des niveaux au template pour le menu déroulant
    niveaux = Niveau.query.all()
    return render_template('auth/edit_profile.html', niveaux=niveaux)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
