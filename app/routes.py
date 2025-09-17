from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from app import db, mail, socketio
from app import login_manager
from flask_mail import Message
from app.models import Utilisateur, Filiere, Niveau, Groupe, Cours, CoursAffectation, Notification, DisponibiliteEnseignant, Matiere, Salle, Conversation, Message, Enseigne, PushSubscription
from datetime import datetime, timedelta
from .decorators import role_required
from sqlalchemy import or_, and_, func # Importation des fonctions pour les requêtes complexes
from sqlalchemy.exc import IntegrityError # Pour gérer les erreurs de contrainte unique
from flask_socketio import emit, join_room, leave_room
import os
import secrets
from PIL import Image
from pywebpush import webpush, WebPushException
import json
import uuid
from werkzeug.utils import secure_filename

# Crée un Blueprint pour les routes principales
main_bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.context_processor
def inject_global_vars():
    """Injecte des variables globales dans le contexte de tous les templates."""
    if current_user.is_authenticated:
        # Compte les notifications personnelles non lues
        unread_notifications = Notification.query.filter_by(destinataire_id=current_user.id, est_lue=False).count()
        # Compte les messages privés non lus
        unread_messages = current_user.new_messages_count()
        return dict(unread_count=unread_notifications, unread_messages_count=unread_messages)
    return dict(unread_count=0, unread_messages_count=0)

def save_profile_picture(form_picture):
    """
    Sauvegarde et redimensionne la photo de profil de l'utilisateur.
    Génère un nom de fichier aléatoire pour éviter les conflits.
    """
    random_hex = secrets.token_hex(8)
    # Garder l'extension du fichier original
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    # S'assurer que le dossier de destination existe
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)

    # Redimensionner l'image pour économiser de l'espace et standardiser
    output_size = (150, 150)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

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

    # Redirection vers le tableau de bord enseignant
    if current_user.role == 'enseignant':
        return redirect(url_for('main.enseignant_dashboard'))

    # Si on arrive ici, l'utilisateur est un étudiant
    emploi_du_temps = []
    prochain_cours = None
    
    # Logique améliorée pour récupérer l'emploi du temps d'un étudiant
    if current_user.filiere_id and current_user.niveau_id:
        # Requête pour trouver toutes les affectations pertinentes pour l'étudiant :
        # Celles pour sa filière/niveau (cours magistraux)
        # ET celles pour son groupe spécifique (TD/TP), s'il en a un.
        query_conditions = [
            and_(
                CoursAffectation.filiere_id == current_user.filiere_id,
                CoursAffectation.niveau_id == current_user.niveau_id,
                CoursAffectation.groupe_id == None
            )
        ]
        if current_user.groupe_id:
            query_conditions.append(CoursAffectation.groupe_id == current_user.groupe_id)
        
        affectations = CoursAffectation.query.filter(or_(*query_conditions)).all()
        
        if affectations:
            cours_ids = {affectation.cours_id for affectation in affectations} # Utilisation d'un set pour éviter les doublons
            
            # Récupérer les cours correspondants et les trier
            emploi_du_temps = Cours.query.filter(Cours.id.in_(cours_ids)).order_by(Cours.date_cours, Cours.heure_debut).all()

            # Trouver le prochain cours
            now = datetime.now()
            prochain_cours = Cours.query.filter(
                Cours.id.in_(cours_ids),
                Cours.date_cours >= now.date()
            ).order_by(Cours.date_cours, Cours.heure_debut).filter(
                (Cours.date_cours > now.date()) | ((Cours.date_cours == now.date()) & (Cours.heure_fin > now.time()))
            ).first()

    # Récupérer les notifications pertinentes pour l'utilisateur connecté
    notifications = Notification.query.filter(
        or_(
            Notification.destinataire_role == 'all', # Notifications pour tout le monde
            Notification.destinataire_role == current_user.role, # Notifications pour son rôle
            Notification.destinataire_id == current_user.id # Notifications personnelles
        )
    ).order_by(Notification.date_creation.desc()).limit(5).all()

    return render_template('utilisateur/dashboard.html', emploi_du_temps=emploi_du_temps, prochain_cours=prochain_cours, notifications=notifications)

@socketio.on('connect')
@login_required
def test_connect():
    print('Client connecté')

@socketio.on('disconnect')
def test_disconnect():
    print('Client déconnecté')

@socketio.on('join')
@login_required
def on_join(data):
    """Le client rejoint une room pour une conversation spécifique."""
    conversation_id = data.get('conversation_id')
    if conversation_id:
        room = str(conversation_id)
        join_room(room)

@socketio.on('leave')
@login_required
def on_leave(data):
    """Le client quitte une room."""
    conversation_id = data.get('conversation_id')
    if conversation_id:
        room = str(conversation_id)
        leave_room(room)
        
@main_bp.route('/')
def loading():
    """Affiche la page de chargement qui redirige vers la page d'accueil."""
    # Si un utilisateur authentifié arrive ici, on le redirige directement
    # vers son tableau de bord pour ne pas lui remontrer le chargement.
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('loading.html')

@main_bp.route('/home')
@main_bp.route('/base') # On garde cette route pour la compatibilité
def home():
    """Affiche la page d'accueil principale (anciennement index)."""
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

def send_reset_email(user):
    """
    Fonction d'aide pour envoyer l'email de réinitialisation.
    Retourne True si l'envoi a réussi, False sinon.
    """
    # Vérification cruciale : les identifiants mail sont-ils configurés ?
    if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
        current_app.logger.error("ERREUR DE CONFIGURATION : MAIL_USERNAME ou MAIL_PASSWORD ne sont pas définis. L'email de réinitialisation ne peut pas être envoyé.")
        flash("La fonctionnalité de réinitialisation de mot de passe n'est pas configurée sur le serveur. Veuillez contacter un administrateur.", "danger")
        return False

    token = user.get_reset_token()
    msg = Message('Demande de réinitialisation de mot de passe - UniPlanBJ',
                  recipients=[user.email])
    msg.html = render_template('email/reset_password.html', user=user, token=token)
    try:
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Échec de l'envoi de l'email de réinitialisation : {e}")
        flash("Une erreur est survenue lors de l'envoi de l'email. Veuillez réessayer plus tard ou contacter un administrateur.", "danger")
        return False

@main_bp.route('/reset_password', methods=['GET', 'POST'])
def request_reset_token():
    """Route pour demander un lien de réinitialisation."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = Utilisateur.query.filter_by(email=email).first()
        if user:
            success = send_reset_email(user)
            if not success:
                # Si l'envoi échoue, on reste sur la page pour que l'utilisateur voie le message d'erreur.
                return redirect(url_for('main.request_reset_token'))

        # Si l'utilisateur n'existe pas OU si l'envoi a réussi, on affiche le même message pour des raisons de sécurité.
        flash('Si un compte avec cet email existe, un lien de réinitialisation a été envoyé.', 'info')
        return redirect(url_for('main.login'))
    return render_template('auth/request_reset.html')

@main_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    """Route pour effectivement réinitialiser le mot de passe avec un token."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    user = Utilisateur.verify_reset_token(token)
    if user is None:
        flash('Le lien est invalide ou a expiré.', 'warning')
        return redirect(url_for('main.request_reset_token'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('main.reset_token', token=token))
        user.set_password(password)
        db.session.commit()
        flash('Votre mot de passe a été mis à jour ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('auth/reset_token.html', token=token)

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'picture' in request.files:
            file = request.files['picture']
            if file.filename == '':
                flash('Aucun fichier sélectionné.', 'warning')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                # Supprimer l'ancienne photo si ce n'est pas la photo par défaut
                if current_user.picture != 'default.jpg':
                    old_picture_path = os.path.join(current_app.root_path, 'static/profile_pics', current_user.picture)
                    if os.path.exists(old_picture_path):
                        os.remove(old_picture_path)
                
                picture_file = save_profile_picture(file)
                current_user.picture = picture_file
                db.session.commit()
                flash('Votre photo de profil a été mise à jour !', 'success')
                return redirect(url_for('main.profile'))
            else:
                flash('Type de fichier non autorisé. Veuillez choisir une image (jpg, png, gif).', 'danger')

    return render_template('auth/profile.html')

@main_bp.route('/profile/delete_picture', methods=['POST'])
@login_required
def delete_profile_picture():
    """Supprime la photo de profil de l'utilisateur et la remplace par celle par défaut."""
    if current_user.picture != 'default.jpg':
        # Construire le chemin vers l'ancienne photo
        picture_path = os.path.join(current_app.root_path, 'static/profile_pics', current_user.picture)
        
        # Essayer de supprimer le fichier physique
        try:
            if os.path.exists(picture_path):
                os.remove(picture_path)
        except OSError as e:
            # Log l'erreur si la suppression échoue, mais continuer
            current_app.logger.error(f"Erreur lors de la suppression du fichier image {picture_path}: {e}")

        # Mettre à jour la base de données
        current_user.picture = 'default.jpg'
        db.session.commit()
        flash('Votre photo de profil a été supprimée avec succès.', 'success')
    
    return redirect(url_for('main.profile'))

@main_bp.route('/profile/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 1. Vérifier si le mot de passe actuel est correct en utilisant la méthode du modèle
        if not current_user.check_password(current_password):
            flash('Votre mot de passe actuel est incorrect.', 'danger')
            return redirect(url_for('main.change_password'))

        # 2. Vérifier si les nouveaux mots de passe correspondent
        if new_password != confirm_password:
            flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('main.change_password'))
        
        # 3. Vérifier la longueur minimale du mot de passe
        if len(new_password) < 6:
            flash('Le nouveau mot de passe doit contenir au moins 6 caractères.', 'danger')
            return redirect(url_for('main.change_password'))

        # 4. Mettre à jour le mot de passe dans la BDD en utilisant la méthode sécurisée du modèle
        current_user.set_password(new_password)
        db.session.commit()

        flash('Votre mot de passe a été mis à jour avec succès.', 'success')
        return redirect(url_for('main.profile'))

    return render_template('auth/change_password.html')

@main_bp.route('/admin_dashboard')
@login_required
@role_required('administrateur') # Seuls les administrateurs peuvent accéder
def admin_dashboard():
    # Récupération des paramètres de recherche et de filtre depuis l'URL
    search_query = request.args.get('q', '')
    role_filter = request.args.get('role', '')

    # Requête de base pour tous les utilisateurs
    query = Utilisateur.query

    # Appliquer le filtre de recherche si un terme est fourni
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(or_(
            Utilisateur.prenom.ilike(search_term),
            Utilisateur.nom.ilike(search_term),
            Utilisateur.email.ilike(search_term)
        ))

    # Appliquer le filtre de rôle si un rôle est sélectionné
    if role_filter:
        query = query.filter(Utilisateur.role == role_filter)

    # Exécuter la requête avec pagination
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Utilisateur.role, Utilisateur.nom).paginate(page=page, per_page=10, error_out=False)
    users = pagination.items
    
    # Récupérer les utilisateurs actifs dans les 5 dernières minutes
    from datetime import timedelta
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    online_users = Utilisateur.query.filter(Utilisateur.last_seen > five_minutes_ago).order_by(Utilisateur.last_seen.desc()).all()

    # Récupérer les notifications pour l'admin
    admin_notifications = Notification.query.filter(
        or_(
            Notification.destinataire_role == 'all',
            Notification.destinataire_role == 'administrateur',
            Notification.destinataire_id == current_user.id
        )
    ).order_by(Notification.date_creation.desc()).limit(5).all()

    # Récupérer aussi la liste des cours pour l'afficher
    all_courses = Cours.query.order_by(Cours.date_cours.desc(), Cours.heure_debut.desc()).all()

    # Calcul des statistiques globales
    total_users = Utilisateur.query.count()
    total_courses = Cours.query.count()
    total_salles = Salle.query.count()
    total_matieres = Matiere.query.count()
    
    # Récupérer les annonces globales/de rôle pour la gestion
    announcements = Notification.query.filter(Notification.destinataire_id.is_(None)).order_by(Notification.date_creation.desc()).all()

    return render_template('admin/dashboard.html', users=users, pagination=pagination, courses=all_courses, online_users=online_users, notifications=admin_notifications, total_users=total_users, total_courses=total_courses, total_salles=total_salles, total_matieres=total_matieres, announcements=announcements)

@main_bp.route('/admin/schedule')
@login_required
@role_required('administrateur')
def schedule_viewer():
    # Get filters from URL
    filiere_id = request.args.get('filiere_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    enseignant_id = request.args.get('enseignant_id', type=int)
    salle_id = request.args.get('salle_id', type=int)
    week_offset = request.args.get('week', 0, type=int)

    # Calculate the start of the week
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    days_of_week = [start_of_week + timedelta(days=i) for i in range(7)]
    end_of_week = days_of_week[6]

    # Base query for courses within the selected week
    query = Cours.query.filter(Cours.date_cours.between(start_of_week, end_of_week))

    # Apply filters
    if enseignant_id:
        query = query.filter(Cours.enseignant_id == enseignant_id)
    if salle_id:
        query = query.filter(Cours.salle_id == salle_id)
    
    if filiere_id or niveau_id:
        query = query.join(Cours.cours_affectations)
        if filiere_id:
            query = query.filter(CoursAffectation.filiere_id == filiere_id)
        if niveau_id:
            query = query.filter(CoursAffectation.niveau_id == niveau_id)

    # Fetch and organize courses by day
    courses = query.order_by(Cours.heure_debut).all()
    schedule_by_day = [[] for _ in range(7)]
    for course in courses:
        day_index = course.date_cours.weekday()
        schedule_by_day[day_index].append(course)

    # Data for filter dropdowns
    filieres = Filiere.query.order_by(Filiere.nom_filiere).all()
    niveaux = Niveau.query.order_by(Niveau.id).all()
    enseignants = Utilisateur.query.filter_by(role='enseignant').order_by(Utilisateur.nom).all()
    salles = Salle.query.order_by(Salle.nom_salle).all()

    return render_template('admin/schedule_viewer.html', schedule_by_day=schedule_by_day, days_of_week=days_of_week, week_offset=week_offset, filieres=filieres, niveaux=niveaux, enseignants=enseignants, salles=salles, filiere_id=filiere_id, niveau_id=niveau_id, enseignant_id=enseignant_id, salle_id=salle_id)

@main_bp.route('/admin/statistics')
@login_required
@role_required('administrateur')
def admin_stats():
    """Affiche des statistiques sur les étudiants."""
    
    # Statistique 1: Nombre d'étudiants par filière (y compris celles avec 0 étudiant)
    stats_filiere = db.session.query(
        Filiere.nom_filiere,
        func.count(Utilisateur.id).label('nombre_etudiants')
    ).outerjoin(Utilisateur, and_(Filiere.id == Utilisateur.filiere_id, Utilisateur.role == 'etudiant'))\
    .group_by(Filiere.id)\
    .order_by(Filiere.nom_filiere)\
    .all()

    # Statistique 2: Nombre d'étudiants par niveau (y compris ceux avec 0 étudiant)
    stats_niveau = db.session.query(
        Niveau.nom_niveau,
        func.count(Utilisateur.id).label('nombre_etudiants')
    ).outerjoin(Utilisateur, and_(Niveau.id == Utilisateur.niveau_id, Utilisateur.role == 'etudiant'))\
    .group_by(Niveau.id)\
    .order_by(Niveau.id)\
    .all()

    # Statistique 3: Répartition détaillée par filière et niveau (uniquement les combinaisons avec étudiants)
    stats_detaillees = db.session.query(
        Filiere.nom_filiere,
        Niveau.nom_niveau,
        func.count(Utilisateur.id).label('nombre_etudiants')
    ).select_from(Utilisateur)\
    .join(Filiere, Utilisateur.filiere_id == Filiere.id)\
    .join(Niveau, Utilisateur.niveau_id == Niveau.id)\
    .filter(Utilisateur.role == 'etudiant')\
    .group_by(Filiere.nom_filiere, Niveau.nom_niveau)\
    .order_by(Filiere.nom_filiere, Niveau.id)\
    .all()

    return render_template('admin/statistics.html', stats_filiere=stats_filiere, stats_niveau=stats_niveau, stats_detaillees=stats_detaillees)

@main_bp.route('/admin/verify_pin', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def admin_verify_pin():
    if request.method == 'POST':
        submitted_pin = request.form.get('pin')
        if submitted_pin == current_app.config['ADMIN_PIN']:
            session['admin_pin_verified'] = True
            # Redirige vers l'URL initialement demandée ou le tableau de bord par défaut
            next_url = session.pop('next_url_after_pin', url_for('main.admin_dashboard'))
            flash('Vérification réussie.', 'success')
            return redirect(next_url)
        else:
            flash('Code PIN incorrect.', 'danger')
    
    return render_template('admin/admin_pin.html')

@main_bp.route('/admin/lock')
@login_required
@role_required('administrateur')
def admin_lock():
    """Verrouille la session admin en supprimant la vérification du PIN."""
    session.pop('admin_pin_verified', None)
    flash("Session administrateur verrouillée.", "info")
    return redirect(url_for('main.dashboard'))

@main_bp.route('/admin/availabilities')
@login_required
@role_required('administrateur')
def admin_availabilities():
    from collections import defaultdict
    # On récupère les disponibilités en chargeant directement les infos de l'enseignant pour optimiser
    availabilities = DisponibiliteEnseignant.query.join(Utilisateur).order_by(Utilisateur.nom, DisponibiliteEnseignant.jour_semaine).all()
    
    # On groupe les disponibilités par enseignant
    avail_by_teacher = defaultdict(list)
    for av in availabilities:
        avail_by_teacher[av.enseignant_obj].append(av)
        
    return render_template('admin/availabilities.html', avail_by_teacher=avail_by_teacher)

@main_bp.route('/admin/create_notification', methods=['POST'])
@login_required
@role_required('administrateur')
def create_notification():
    """Crée une notification globale ou ciblée par rôle."""
    title = request.form.get('title')
    message = request.form.get('message')
    role = request.form.get('role')  # 'all', 'etudiant', 'enseignant', 'administrateur'

    if not title or not message or not role:
        flash("Veuillez remplir tous les champs pour créer une annonce.", 'danger')
        return redirect(url_for('main.admin_dashboard'))

    # Validation du rôle pour s'assurer qu'il est valide
    if role not in ['all', 'etudiant', 'enseignant', 'administrateur']:
        flash("Rôle de destinataire invalide.", 'danger')
        return redirect(url_for('main.admin_dashboard'))

    new_notification = Notification(
        titre=title,
        message=message,
        destinataire_role=role,
        destinataire_id=None  # C'est une annonce de rôle/globale, pas personnelle
    )
    db.session.add(new_notification)
    db.session.commit()
    flash('Annonce créée et envoyée avec succès.', 'success')
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/notification/delete/<int:notification_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def delete_notification(notification_id):
    """Supprime une annonce globale ou de rôle."""
    notif_to_delete = Notification.query.get_or_404(notification_id)

    # Vérification de sécurité : ne permet de supprimer que les annonces globales/de rôle.
    if notif_to_delete.destinataire_id is not None:
        flash("Action non autorisée. Vous ne pouvez supprimer que les annonces générales.", 'danger')
        return redirect(url_for('main.admin_dashboard'))

    db.session.delete(notif_to_delete)
    db.session.commit()
    flash('Annonce supprimée avec succès.', 'success')
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/notification/edit/<int:notification_id>', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def edit_notification(notification_id):
    """Modifie une annonce existante."""
    notif_to_edit = Notification.query.get_or_404(notification_id)

    # Sécurité : ne permet d'éditer que les annonces générales
    if notif_to_edit.destinataire_id is not None:
        flash("Action non autorisée. Vous ne pouvez modifier que les annonces générales.", 'danger')
        return redirect(url_for('main.admin_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        role = request.form.get('role')

        if not title or not message or not role:
            flash("Veuillez remplir tous les champs.", 'danger')
            return render_template('admin/edit_notification.html', notification=notif_to_edit)

        if role not in ['all', 'etudiant', 'enseignant', 'administrateur']:
            flash("Rôle de destinataire invalide.", 'danger')
            return render_template('admin/edit_notification.html', notification=notif_to_edit)

        notif_to_edit.titre = title
        notif_to_edit.message = message
        notif_to_edit.destinataire_role = role
        db.session.commit()
        flash('Annonce modifiée avec succès.', 'success')
        return redirect(url_for('main.admin_dashboard'))

    return render_template('admin/edit_notification.html', notification=notif_to_edit)

@main_bp.route('/admin/create_course', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def create_course():
    if request.method == 'POST':
        # Récupération des données du formulaire
        matiere_id = request.form.get('matiere_id')
        enseignant_id = request.form.get('enseignant_id')
        salle_id = request.form.get('salle_id')
        date_cours_str = request.form.get('date_cours')
        heure_debut_str = request.form.get('heure_debut')
        heure_fin_str = request.form.get('heure_fin')
        description = request.form.get('description')
        groupes_ids = request.form.getlist('groupes_ids')

        date_cours = datetime.strptime(date_cours_str, '%Y-%m-%d').date()
        heure_debut = datetime.strptime(heure_debut_str, '%H:%M').time()
        heure_fin = datetime.strptime(heure_fin_str, '%H:%M').time()

        # --- Vérification des conflits ---
        # 1. Conflit pour l'enseignant
        conflit_enseignant = Cours.query.filter(
            Cours.enseignant_id == enseignant_id,
            Cours.date_cours == date_cours,
            Cours.heure_debut < heure_fin,
            Cours.heure_fin > heure_debut
        ).first()
        if conflit_enseignant:
            flash(f"Conflit d'horaire : L'enseignant est déjà occupé à ce créneau.", 'danger')
            return redirect(url_for('main.create_course'))

        # 2. Conflit pour la salle
        conflit_salle = Cours.query.filter(
            Cours.salle_id == salle_id,
            Cours.date_cours == date_cours,
            Cours.heure_debut < heure_fin,
            Cours.heure_fin > heure_debut
        ).first()
        if conflit_salle:
            flash(f"Conflit d'horaire : La salle est déjà occupée à ce créneau.", 'danger')
            return redirect(url_for('main.create_course'))

        # Création du cours
        nouveau_cours = Cours(
            matiere_id=matiere_id, enseignant_id=enseignant_id, salle_id=salle_id,
            date_cours=date_cours, heure_debut=heure_debut, heure_fin=heure_fin,
            description=description
        )
        db.session.add(nouveau_cours)
        db.session.flush() # Pour obtenir l'ID du nouveau cours

        # Création des affectations
        for groupe_id in groupes_ids:
            groupe = Groupe.query.get(groupe_id)
            affectation = CoursAffectation(cours_id=nouveau_cours.id, groupe_id=groupe.id, filiere_id=groupe.filiere_id, niveau_id=groupe.niveau_id)
            db.session.add(affectation)

        db.session.commit()
        flash('Le cours a été créé et publié avec succès.', 'success')
        return redirect(url_for('main.admin_dashboard'))

    # Préparation des données pour le formulaire en GET
    matieres = Matiere.query.order_by(Matiere.nom_matiere).all()
    enseignants = Utilisateur.query.filter_by(role='enseignant').order_by(Utilisateur.nom).all()
    salles = Salle.query.order_by(Salle.nom_salle).all()
    groupes = Groupe.query.join(Niveau).order_by(Niveau.id, Groupe.nom_groupe).all()
    return render_template('admin/create_course.html', matieres=matieres, enseignants=enseignants, salles=salles, groupes=groupes)

@main_bp.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def edit_course(course_id):
    course_to_edit = Cours.query.get_or_404(course_id)

    if request.method == 'POST':
        # Récupération des données
        course_to_edit.matiere_id = request.form.get('matiere_id')
        course_to_edit.enseignant_id = request.form.get('enseignant_id')
        course_to_edit.salle_id = request.form.get('salle_id')
        date_cours = datetime.strptime(request.form.get('date_cours'), '%Y-%m-%d').date()
        heure_debut = datetime.strptime(request.form.get('heure_debut'), '%H:%M').time()
        heure_fin = datetime.strptime(request.form.get('heure_fin'), '%H:%M').time()
        course_to_edit.description = request.form.get('description')

        # CORRECTION : Assigner les nouvelles dates et heures à l'objet cours
        course_to_edit.date_cours = date_cours
        course_to_edit.heure_debut = heure_debut
        course_to_edit.heure_fin = heure_fin

        # Logique de vérification des conflits (excluant le cours actuel)
        conflit_enseignant = Cours.query.filter(
            Cours.id != course_id,
            Cours.enseignant_id == course_to_edit.enseignant_id,
            Cours.date_cours == date_cours,
            Cours.heure_debut < heure_fin,
            Cours.heure_fin > heure_debut
        ).first()
        if conflit_enseignant:
            flash(f"Conflit: L'enseignant est déjà occupé à ce créneau.", 'danger')
            return redirect(url_for('main.edit_course', course_id=course_id))

        conflit_salle = Cours.query.filter(
            Cours.id != course_id,
            Cours.salle_id == course_to_edit.salle_id,
            Cours.date_cours == date_cours,
            Cours.heure_debut < heure_fin,
            Cours.heure_fin > heure_debut
        ).first()
        if conflit_salle:
            flash(f"Conflit: La salle est déjà occupée à ce créneau.", 'danger')
            return redirect(url_for('main.edit_course', course_id=course_id))

        # Mise à jour des affectations : simple et efficace
        # 1. Supprimer les anciennes affectations
        CoursAffectation.query.filter_by(cours_id=course_id).delete()
        # 2. Créer les nouvelles
        groupes_ids = request.form.getlist('groupes_ids')
        for groupe_id in groupes_ids:
            groupe = Groupe.query.get(groupe_id)
            affectation = CoursAffectation(cours_id=course_id, groupe_id=groupe.id, filiere_id=groupe.filiere_id, niveau_id=groupe.niveau_id)
            db.session.add(affectation)

        # Envoyer la notification de modification
        title = f"Cours modifié : {course_to_edit.matiere_obj.nom_matiere}"
        message = f"Le cours de {course_to_edit.matiere_obj.nom_matiere} a été mis à jour. Nouveau créneau : {course_to_edit.date_cours.strftime('%d/%m/%Y')} de {course_to_edit.heure_debut.strftime('%Hh%M')} à {course_to_edit.heure_fin.strftime('%Hh%M')}."
        send_course_notification(course_to_edit, title, message)

        db.session.commit()
        flash('Le cours a été mis à jour avec succès.', 'success')
        return redirect(url_for('main.admin_dashboard'))

    # Préparation des données pour le formulaire en GET
    matieres = Matiere.query.order_by(Matiere.nom_matiere).all()
    enseignants = Utilisateur.query.filter_by(role='enseignant').order_by(Utilisateur.nom).all()
    salles = Salle.query.order_by(Salle.nom_salle).all()
    groupes = Groupe.query.join(Niveau).order_by(Niveau.id, Groupe.nom_groupe).all()
    current_group_ids = [aff.groupe_id for aff in course_to_edit.cours_affectations]
    return render_template('admin/edit_course.html', course=course_to_edit, matieres=matieres, enseignants=enseignants, salles=salles, groupes=groupes, current_group_ids=current_group_ids)

@main_bp.route('/notifications')
@login_required
def notifications():
    """Affiche l'historique complet des notifications de l'utilisateur."""
    
    # Récupérer toutes les notifications pertinentes pour l'utilisateur
    user_notifications = Notification.query.filter(
        or_(
            Notification.destinataire_role == 'all',
            Notification.destinataire_role == current_user.role,
            Notification.destinataire_id == current_user.id
        )
    ).order_by(Notification.date_creation.desc()).all()

    # Marquer les notifications personnelles non lues de l'utilisateur comme lues
    personal_unread = Notification.query.filter_by(destinataire_id=current_user.id, est_lue=False)
    for notif in personal_unread:
        notif.est_lue = True
    db.session.commit()

    return render_template('utilisateur/notifications.html', notifications=user_notifications)

@main_bp.route('/enseignant/dashboard', methods=['GET', 'POST'])
@login_required
@role_required('enseignant')
def enseignant_dashboard():
    if request.method == 'POST':
        jour = request.form.get('jour_semaine')
        heure_debut_str = request.form.get('heure_debut')
        heure_fin_str = request.form.get('heure_fin')

        if jour and heure_debut_str and heure_fin_str:
            heure_debut = datetime.strptime(heure_debut_str, '%H:%M').time()
            heure_fin = datetime.strptime(heure_fin_str, '%H:%M').time()

            nouvelle_dispo = DisponibiliteEnseignant(
                enseignant_id=current_user.id, jour_semaine=jour, heure_debut=heure_debut, heure_fin=heure_fin
            )
            try:
                db.session.add(nouvelle_dispo)
                db.session.commit()
                flash('Disponibilité ajoutée avec succès.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('Cette disponibilité existe déjà.', 'danger')
            return redirect(url_for('main.enseignant_dashboard'))

    disponibilites = DisponibiliteEnseignant.query.filter_by(enseignant_id=current_user.id).order_by(DisponibiliteEnseignant.jour_semaine).all()
    emploi_du_temps = Cours.query.filter_by(enseignant_id=current_user.id).order_by(Cours.date_cours, Cours.heure_debut).all()
    
    # CORRECTION : Ajout de la logique de notification pour les enseignants
    notifications = Notification.query.filter(or_(Notification.destinataire_role == 'all', Notification.destinataire_role == 'enseignant', Notification.destinataire_id == current_user.id)).order_by(Notification.date_creation.desc()).limit(5).all()

    return render_template('enseignant/dashboard.html', disponibilites=disponibilites, emploi_du_temps=emploi_du_temps, notifications=notifications)

@main_bp.route('/enseignant/disponibilite/delete/<int:dispo_id>', methods=['POST'])
@login_required
@role_required('enseignant')
def delete_disponibilite(dispo_id):
    """Route pour supprimer une disponibilité d'un enseignant."""
    dispo_to_delete = DisponibiliteEnseignant.query.get_or_404(dispo_id)

    # Vérification de sécurité : l'enseignant ne peut supprimer que ses propres disponibilités.
    if dispo_to_delete.enseignant_id != current_user.id:
        flash("Vous n'êtes pas autorisé à effectuer cette action.", 'danger')
        return redirect(url_for('main.enseignant_dashboard'))

    db.session.delete(dispo_to_delete)
    db.session.commit()
    flash('La disponibilité a été supprimée avec succès.', 'success')
    return redirect(url_for('main.enseignant_dashboard'))

@main_bp.route('/teacher/profile/update', methods=['GET', 'POST'])
@login_required
@role_required('enseignant')
def update_teacher_profile():
    if request.method == 'POST':
        # --- 1. Mettre à jour les informations de base de l'utilisateur ---
        current_user.prenom = request.form.get('firstname')
        current_user.nom = request.form.get('lastname')

        # --- 2. Synchroniser les matières enseignées ---
        
        # Récupérer les listes d'IDs depuis le formulaire dynamique
        subject_ids = request.form.getlist('subject_id')
        filiere_ids = request.form.getlist('filiere_id')
        level_ids = request.form.getlist('level_id')

        # Stratégie "Supprimer et Recréer" : simple et robuste
        # D'abord, on supprime toutes les anciennes associations pour cet enseignant
        Enseigne.query.filter_by(enseignant_id=current_user.id).delete()

        # Ensuite, on ajoute les nouvelles associations soumises
        # On utilise un `set` pour éviter d'ajouter des doublons si l'utilisateur en a soumis
        new_teachings = set()
        for sub_id, fil_id, lev_id in zip(subject_ids, filiere_ids, level_ids):
            # S'assurer que les trois valeurs sont présentes et valides avant de les ajouter
            if sub_id and fil_id and lev_id:
                new_teachings.add((int(sub_id), int(fil_id), int(lev_id)))

        for sub_id, fil_id, lev_id in new_teachings:
            teaching_entry = Enseigne(
                enseignant_id=current_user.id,
                matiere_id=sub_id,
                filiere_id=fil_id,
                niveau_id=lev_id
            )
            db.session.add(teaching_entry)
        
        try:
            db.session.commit()
            flash('Votre profil a été mis à jour avec succès !', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue lors de la mise à jour : {e}', 'error')

        return redirect(url_for('main.update_teacher_profile'))

    # --- Pour une requête GET (quand l'enseignant charge la page) ---
    # Charger toutes les options pour les listes déroulantes
    matieres = Matiere.query.order_by(Matiere.nom_matiere).all()
    filieres = Filiere.query.order_by(Filiere.nom_filiere).all()
    niveaux = Niveau.query.order_by(Niveau.id).all()
    
    # Charger les associations existantes pour l'enseignant connecté
    enseignements_actuels = Enseigne.query.filter_by(enseignant_id=current_user.id).all()

    return render_template('enseignant/teacher_profile.html', matieres=matieres, filieres=filieres, niveaux=niveaux, enseignements_actuels=enseignements_actuels)

def send_course_notification(course, title, message_body):
    """
    Fonction d'aide pour envoyer des notifications à tous les utilisateurs concernés par un cours.
    """
    users_to_notify = set()

    # 1. Ajouter l'enseignant
    if course.enseignant_obj:
        users_to_notify.add(course.enseignant_obj)

    # 2. Trouver et ajouter tous les étudiants concernés par les affectations
    for aff in course.cours_affectations:
        query = Utilisateur.query.filter_by(role='etudiant')
        if aff.filiere_id:
            query = query.filter_by(filiere_id=aff.filiere_id)
        if aff.niveau_id:
            query = query.filter_by(niveau_id=aff.niveau_id)
        if aff.groupe_id:
            query = query.filter_by(groupe_id=aff.groupe_id)
        
        students = query.all()
        for student in students:
            users_to_notify.add(student)

    # 3. Créer et préparer les notifications pour la sauvegarde
    for user in users_to_notify:
        notification = Notification(
            titre=title,
            message=message_body,
            destinataire_id=user.id,
            destinataire_role=user.role
        )
        db.session.add(notification)

@main_bp.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def delete_course(course_id):
    course_to_delete = Cours.query.get_or_404(course_id)
    
    # Préparer la notification avant de supprimer le cours
    title = f"Cours annulé : {course_to_delete.matiere_obj.nom_matiere}"
    message = f"Le cours de {course_to_delete.matiere_obj.nom_matiere} qui était prévu le {course_to_delete.date_cours.strftime('%d/%m/%Y')} à {course_to_delete.heure_debut.strftime('%Hh%M')} a été annulé."
    send_course_notification(course_to_delete, title, message)

    db.session.delete(course_to_delete)
    db.session.commit()
    flash('Le cours a été supprimé avec succès.', 'success')
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def delete_user(user_id):
    # Vérification du code PIN soumis dans le formulaire du modal
    submitted_pin = request.form.get('pin')
    if submitted_pin != current_app.config['ADMIN_PIN']:
        flash('Code PIN incorrect. La suppression a été annulée.', 'danger')
        return redirect(url_for('main.admin_dashboard'))

    # Empêcher un administrateur de se supprimer lui-même
    if user_id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte administrateur.", 'danger')
        return redirect(url_for('main.admin_dashboard'))

    user_to_delete = Utilisateur.query.get_or_404(user_id)

    # Note : Pour une application en production, il faudrait gérer les dépendances
    # (ex: que faire des cours si on supprime un enseignant ?).

    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f"L'utilisateur {user_to_delete.prenom} {user_to_delete.nom} a été supprimé avec succès.", 'success')
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def edit_user(user_id):
    user_to_edit = Utilisateur.query.get_or_404(user_id)
    # On charge les groupes pour le formulaire d'édition
    groupes = Groupe.query.join(Filiere).join(Niveau).order_by(Filiere.nom_filiere, Niveau.id, Groupe.nom_groupe).all()

    if request.method == 'POST':
        # Vérification du code PIN avant toute modification
        submitted_pin = request.form.get('pin')
        if submitted_pin != current_app.config['ADMIN_PIN']:
            flash('Code PIN incorrect. Les modifications n\'ont pas été enregistrées.', 'danger')
            return redirect(url_for('main.edit_user', user_id=user_id))

        user_to_edit.prenom = request.form.get('prenom')
        user_to_edit.nom = request.form.get('nom')
        user_to_edit.email = request.form.get('email')
        new_role = request.form.get('role')

        if user_to_edit.id == current_user.id and user_to_edit.role != new_role:
            flash("Vous ne pouvez pas changer votre propre rôle.", 'danger')
            return redirect(url_for('main.edit_user', user_id=user_id))
        
        user_to_edit.role = new_role

        # Logique d'assignation de groupe pour les étudiants
        if user_to_edit.role == 'etudiant':
            groupe_id_str = request.form.get('groupe_id')
            if groupe_id_str and groupe_id_str.isdigit():
                groupe_id = int(groupe_id_str)
                groupe = Groupe.query.get(groupe_id)
                if groupe:
                    user_to_edit.groupe_id = groupe.id
                    # MISE À JOUR AUTOMATIQUE de la filière et du niveau de l'étudiant
                    user_to_edit.filiere_id = groupe.filiere_id
                    user_to_edit.niveau_id = groupe.niveau_id
                else:
                    # Cas où un ID de groupe invalide est envoyé
                    user_to_edit.groupe_id = None
                    user_to_edit.filiere_id = None
                    user_to_edit.niveau_id = None
            else:  # Si "" ou "None" est sélectionné pour le groupe
                user_to_edit.groupe_id = None
                user_to_edit.filiere_id = None
                user_to_edit.niveau_id = None
        else:  # Si le rôle n'est pas étudiant, on s'assure que les champs académiques sont vides
            user_to_edit.groupe_id = None
            user_to_edit.filiere_id = None
            user_to_edit.niveau_id = None

        db.session.commit()
        flash(f"Le profil de {user_to_edit.prenom} {user_to_edit.nom} a été mis à jour.", 'success')
        return redirect(url_for('main.admin_dashboard'))

    return render_template('admin/edit_user.html', user=user_to_edit, groupes=groupes)

# ===================================================================
# ==                  CRUD GESTION DES FILIÈRES                    ==
# ===================================================================
@main_bp.route('/admin/filieres', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def manage_filieres():
    if request.method == 'POST':
        nom_filiere = request.form.get('nom_filiere')
        description = request.form.get('description')
        if not nom_filiere:
            flash("Le nom de la filière est obligatoire.", 'danger')
        else:
            try:
                nouvelle_filiere = Filiere(nom_filiere=nom_filiere, description=description)
                db.session.add(nouvelle_filiere)
                db.session.commit()
                flash('Filière ajoutée avec succès.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('Cette filière existe déjà.', 'danger')
        return redirect(url_for('main.manage_filieres'))
    
    filieres = Filiere.query.order_by(Filiere.nom_filiere).all()
    return render_template('admin/manage_filieres.html', filieres=filieres)

@main_bp.route('/admin/filiere/edit/<int:filiere_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def edit_filiere(filiere_id):
    filiere = Filiere.query.get_or_404(filiere_id)
    filiere.nom_filiere = request.form.get('nom_filiere')
    filiere.description = request.form.get('description')
    try:
        db.session.commit()
        flash('Filière mise à jour avec succès.', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Ce nom de filière est déjà utilisé.', 'danger')
    return redirect(url_for('main.manage_filieres'))

@main_bp.route('/admin/filiere/delete/<int:filiere_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def delete_filiere(filiere_id):
    filiere = Filiere.query.get_or_404(filiere_id)
    # Suppression sécurisée : vérifier si la filière est utilisée
    if filiere.groupes.first() or Utilisateur.query.filter_by(filiere_id=filiere_id).first():
        flash("Impossible de supprimer cette filière car elle est associée à des groupes ou des étudiants.", 'danger')
    else:
        db.session.delete(filiere)
        db.session.commit()
        flash('Filière supprimée avec succès.', 'success')
    return redirect(url_for('main.manage_filieres'))

# ===================================================================
# ==                   CRUD GESTION DES NIVEAUX                    ==
# ===================================================================
@main_bp.route('/admin/niveaux', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def manage_niveaux():
    if request.method == 'POST':
        nom_niveau = request.form.get('nom_niveau')
        if not nom_niveau:
            flash("Le nom du niveau est obligatoire.", 'danger')
        else:
            try:
                nouveau_niveau = Niveau(nom_niveau=nom_niveau)
                db.session.add(nouveau_niveau)
                db.session.commit()
                flash('Niveau ajouté avec succès.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('Ce niveau existe déjà.', 'danger')
        return redirect(url_for('main.manage_niveaux'))

    niveaux = Niveau.query.order_by(Niveau.id).all()
    return render_template('admin/manage_niveaux.html', niveaux=niveaux)

@main_bp.route('/admin/niveau/edit/<int:niveau_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def edit_niveau(niveau_id):
    niveau = Niveau.query.get_or_404(niveau_id)
    niveau.nom_niveau = request.form.get('nom_niveau')
    try:
        db.session.commit()
        flash('Niveau mis à jour avec succès.', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Ce nom de niveau est déjà utilisé.', 'danger')
    return redirect(url_for('main.manage_niveaux'))

@main_bp.route('/admin/niveau/delete/<int:niveau_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def delete_niveau(niveau_id):
    niveau = Niveau.query.get_or_404(niveau_id)
    # Suppression sécurisée : vérifier si le niveau est utilisé
    if niveau.groupes.first() or Utilisateur.query.filter_by(niveau_id=niveau_id).first():
        flash("Impossible de supprimer ce niveau car il est associé à des groupes ou des étudiants.", 'danger')
    else:
        db.session.delete(niveau)
        db.session.commit()
        flash('Niveau supprimé avec succès.', 'success')
    return redirect(url_for('main.manage_niveaux'))

# ===================================================================
# ==                   CRUD GESTION DES GROUPES                    ==
# ===================================================================
@main_bp.route('/admin/groupes', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def manage_groupes():
    if request.method == 'POST':
        nom_groupe = request.form.get('nom_groupe')
        filiere_id = request.form.get('filiere_id', type=int)
        niveau_id = request.form.get('niveau_id', type=int)

        if not all([nom_groupe, filiere_id, niveau_id]):
            flash("Tous les champs sont obligatoires pour créer un groupe.", 'danger')
        else:
            try:
                nouveau_groupe = Groupe(nom_groupe=nom_groupe, filiere_id=filiere_id, niveau_id=niveau_id)
                db.session.add(nouveau_groupe)
                db.session.commit()
                flash('Groupe ajouté avec succès.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('Ce groupe existe déjà pour cette filière et ce niveau.', 'danger')
        return redirect(url_for('main.manage_groupes'))

    groupes = Groupe.query.join(Filiere).join(Niveau).order_by(Filiere.nom_filiere, Niveau.id, Groupe.nom_groupe).all()
    filieres = Filiere.query.order_by(Filiere.nom_filiere).all()
    niveaux = Niveau.query.order_by(Niveau.id).all()
    return render_template('admin/manage_groupes.html', groupes=groupes, filieres=filieres, niveaux=niveaux)

@main_bp.route('/admin/groupe/edit/<int:groupe_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def edit_groupe(groupe_id):
    groupe = Groupe.query.get_or_404(groupe_id)
    groupe.nom_groupe = request.form.get('nom_groupe')
    groupe.filiere_id = request.form.get('filiere_id', type=int)
    groupe.niveau_id = request.form.get('niveau_id', type=int)
    try:
        db.session.commit()
        flash('Groupe mis à jour avec succès.', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Un groupe avec ce nom existe déjà pour cette filière et ce niveau.', 'danger')
    return redirect(url_for('main.manage_groupes'))

@main_bp.route('/admin/groupe/delete/<int:groupe_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def delete_groupe(groupe_id):
    groupe = Groupe.query.get_or_404(groupe_id)
    # Suppression sécurisée : vérifier si le groupe est utilisé
    if groupe.utilisateurs.first():
        flash("Impossible de supprimer ce groupe car il est associé à des étudiants.", 'danger')
    else:
        db.session.delete(groupe)
        db.session.commit()
        flash('Groupe supprimé avec succès.', 'success')
    return redirect(url_for('main.manage_groupes'))

@main_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
@role_required('etudiant') # On utilise le décorateur pour restreindre l'accès
def edit_profile():
    if request.method == 'POST':
        # On récupère directement l'ID de la filière depuis le formulaire
        filiere_id = request.form.get('filiere_id')
        niveau_id = request.form.get('niveau_id')

        current_user.filiere_id = filiere_id
        current_user.niveau_id = niveau_id if niveau_id else None

        db.session.commit()
        flash('Votre profil a été mis à jour avec succès !', 'success')
        return redirect(url_for('main.dashboard'))
    
    # On passe la liste des filières et des niveaux au template
    filieres = Filiere.query.order_by(Filiere.nom_filiere).all()
    niveaux = Niveau.query.order_by(Niveau.id).all()
    return render_template('auth/edit_profile.html', filieres=filieres, niveaux=niveaux)

@main_bp.route('/admin/salles', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def manage_salles():
    if request.method == 'POST':
        nom_salle = request.form.get('nom_salle')
        capacite = request.form.get('capacite', type=int)

        # Vérifier si la salle existe déjà
        if Salle.query.filter_by(nom_salle=nom_salle).first():
            flash(f"La salle '{nom_salle}' existe déjà.", 'danger')
        else:
            nouvelle_salle = Salle(nom_salle=nom_salle, capacite=capacite)
            db.session.add(nouvelle_salle)
            db.session.commit()
            flash(f"La salle '{nom_salle}' a été ajoutée avec succès.", 'success')
        return redirect(url_for('main.manage_salles'))

    salles = Salle.query.order_by(Salle.nom_salle).all()
    return render_template('admin/manage_salles.html', salles=salles)

@main_bp.route('/admin/salle/edit/<int:salle_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def edit_salle(salle_id):
    salle_to_edit = Salle.query.get_or_404(salle_id)
    nom_salle = request.form.get('nom_salle')
    capacite = request.form.get('capacite', type=int)

    # Vérifier si le nouveau nom n'est pas déjà pris par une autre salle
    existing_salle = Salle.query.filter(Salle.nom_salle == nom_salle, Salle.id != salle_id).first()
    if existing_salle:
        flash(f"Le nom de salle '{nom_salle}' est déjà utilisé.", 'danger')
    else:
        salle_to_edit.nom_salle = nom_salle
        salle_to_edit.capacite = capacite
        db.session.commit()
        flash('La salle a été mise à jour avec succès.', 'success')
    return redirect(url_for('main.manage_salles'))

@main_bp.route('/admin/salle/delete/<int:salle_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def delete_salle(salle_id):
    salle_to_delete = Salle.query.get_or_404(salle_id)
    
    # Vérifier si la salle est utilisée par un cours
    if salle_to_delete.cours.first():
        flash(f"Impossible de supprimer la salle '{salle_to_delete.nom_salle}' car elle est utilisée dans au moins un cours.", 'danger')
        return redirect(url_for('main.manage_salles'))

    db.session.delete(salle_to_delete)
    db.session.commit()
    flash(f"La salle '{salle_to_delete.nom_salle}' a été supprimée.", 'success')
    return redirect(url_for('main.manage_salles'))

@main_bp.route('/admin/matieres', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def manage_matieres():
    if request.method == 'POST':
        nom_matiere = request.form.get('nom_matiere')
        code_matiere = request.form.get('code_matiere')
        description = request.form.get('description')

        # Vérifier si le code matière existe déjà
        if Matiere.query.filter_by(code_matiere=code_matiere).first():
            flash(f"Le code matière '{code_matiere}' existe déjà.", 'danger')
        else:
            nouvelle_matiere = Matiere(nom_matiere=nom_matiere, code_matiere=code_matiere, description=description)
            db.session.add(nouvelle_matiere)
            db.session.commit()
            flash(f"La matière '{nom_matiere}' a été ajoutée avec succès.", 'success')
        return redirect(url_for('main.manage_matieres'))

    matieres = Matiere.query.order_by(Matiere.nom_matiere).all()
    return render_template('admin/manage_matieres.html', matieres=matieres)


# ===================================================================
# ==                   ROUTES POUR LA MESSAGERIE                   ==
# ===================================================================

@main_bp.route('/inbox/')
@main_bp.route('/inbox/<int:conversation_id>')
@login_required
def inbox(conversation_id=None):
    # Récupérer toutes les conversations de l'utilisateur, triées par le message le plus récent
    conversations = Conversation.query.filter(
        or_(Conversation.participant1_id == current_user.id, Conversation.participant2_id == current_user.id)
    ).order_by(Conversation.last_message_time.desc()).all()

    active_conversation = None
    messages = []
    if conversation_id:
        active_conversation = Conversation.query.get_or_404(conversation_id)
        # Sécurité : vérifier que l'utilisateur fait bien partie de la conversation
        if current_user.id not in [active_conversation.participant1_id, active_conversation.participant2_id]:
            flash("Accès non autorisé à cette conversation.", "danger")
            return redirect(url_for('main.inbox'))
        
        messages = active_conversation.messages.order_by(Message.timestamp.asc()).all()

        # Marquer les messages reçus comme lus
        unread_messages_query = Message.query.filter(
            Message.conversation_id == conversation_id,
            Message.sender_id != current_user.id,
            Message.is_read == False
        )
        
        # Récupérer les IDs avant la mise à jour pour la notification
        message_ids_to_mark_as_read = [msg.id for msg in unread_messages_query.all()]

        if message_ids_to_mark_as_read:
            unread_messages_query.update({Message.is_read: True})
            db.session.commit()
            # Émettre un événement pour informer l'autre utilisateur que les messages ont été lus
            socketio.emit('messages_read', {'message_ids': message_ids_to_mark_as_read}, room=str(conversation_id))

    return render_template('utilisateur/inbox.html', conversations=conversations, active_conversation=active_conversation, messages=messages)

@main_bp.route('/message/start/<int:recipient_id>')
@login_required
def start_conversation(recipient_id):
    if recipient_id == current_user.id:
        flash("Vous ne pouvez pas démarrer une conversation avec vous-même.", "warning")
        return redirect(request.referrer or url_for('main.dashboard'))

    # Assurer un ordre constant pour les participants pour éviter les doublons (user1, user2) et (user2, user1)
    p1_id = min(current_user.id, recipient_id)
    p2_id = max(current_user.id, recipient_id)

    conversation = Conversation.query.filter_by(participant1_id=p1_id, participant2_id=p2_id).first()
    if not conversation:
        recipient = Utilisateur.query.get_or_404(recipient_id)
        conversation = Conversation(participant1_id=p1_id, participant2_id=p2_id)
        db.session.add(conversation)
        db.session.commit()
    
    return redirect(url_for('main.inbox', conversation_id=conversation.id))

@main_bp.route('/message/reply/<int:conversation_id>', methods=['POST'])
@login_required
def send_reply(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if current_user.id not in [conversation.participant1_id, conversation.participant2_id]:
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('main.inbox'))

    body = request.form.get('body')
    image_file = request.files.get('image')
    image_url = None

    # Vérifier si le message est vide (ni texte, ni image valide)
    if not body and (not image_file or not image_file.filename):
        flash("Vous ne pouvez pas envoyer un message vide.", "warning")
        return redirect(url_for('main.inbox', conversation_id=conversation_id))

    # Traitement de l'image si elle est présente et valide
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        # Générer un nom de fichier unique pour éviter les conflits
        unique_filename = str(uuid.uuid4()) + '_' + filename
        
        # Créer le dossier d'upload s'il n'existe pas
        upload_folder = os.path.join(current_app.root_path, 'static/uploads/messages')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Sauvegarder le fichier
        image_path = os.path.join(upload_folder, unique_filename)
        image_file.save(image_path)
        
        # Générer l'URL pour l'accès depuis le template
        image_url = url_for('static', filename=f'uploads/messages/{unique_filename}')

    elif image_file and not allowed_file(image_file.filename):
        flash("Type de fichier non autorisé. Seules les images (png, jpg, jpeg, gif) sont acceptées.", "danger")
        return redirect(url_for('main.inbox', conversation_id=conversation_id))

    # Créer le message en base de données
    msg = Message(
        author=current_user, 
        conversation=conversation, 
        body=body if body else None,
        image_url=image_url
    )
    conversation.last_message_time = datetime.utcnow()
    db.session.add(msg)
    db.session.commit() # On commit pour obtenir l'ID, le timestamp, etc.

    room = str(conversation.id)
    # On émet un message structuré à la room via Socket.IO
    socketio.emit('new_message', {
        'id': msg.id,
        'body': msg.body,
        'image_url': msg.image_url, # On ajoute l'URL de l'image
        'timestamp': msg.timestamp.isoformat() + 'Z', # Format ISO 8601 pour JS
        'sender': {
            'id': current_user.id,
            'prenom': current_user.prenom
        },
        'conversation_id': conversation.id
    }, room=room)

    return redirect(url_for('main.inbox', conversation_id=conversation_id))

@main_bp.route('/api/unread-messages-count')
@login_required
def unread_messages_count_api():
    """API endpoint to get the number of unread messages."""
    count = current_user.new_messages_count()
    return jsonify({'unread_messages_count': count})
@main_bp.route('/admin/matiere/edit/<int:matiere_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def edit_matiere(matiere_id):
    matiere_to_edit = Matiere.query.get_or_404(matiere_id)
    nom_matiere = request.form.get('nom_matiere')
    code_matiere = request.form.get('code_matiere')
    description = request.form.get('description')

    # Vérifier si le nouveau code n'est pas déjà pris par une autre matière
    existing_matiere = Matiere.query.filter(Matiere.code_matiere == code_matiere, Matiere.id != matiere_id).first()
    if existing_matiere:
        flash(f"Le code matière '{code_matiere}' est déjà utilisé.", 'danger')
    else:
        matiere_to_edit.nom_matiere = nom_matiere
        matiere_to_edit.code_matiere = code_matiere
        matiere_to_edit.description = description
        db.session.commit()
        flash('La matière a été mise à jour avec succès.', 'success')
    return redirect(url_for('main.manage_matieres'))

@main_bp.route('/admin/matiere/delete/<int:matiere_id>', methods=['POST'])
@login_required
@role_required('administrateur')
def delete_matiere(matiere_id):
    matiere_to_delete = Matiere.query.get_or_404(matiere_id)
    
    # Vérifier si la matière est utilisée par un cours pour éviter les erreurs
    if matiere_to_delete.cours.first():
        flash(f"Impossible de supprimer la matière '{matiere_to_delete.nom_matiere}' car elle est utilisée dans au moins un cours.", 'danger')
        return redirect(url_for('main.manage_matieres'))

    db.session.delete(matiere_to_delete)
    db.session.commit()
    flash(f"La matière '{matiere_to_delete.nom_matiere}' a été supprimée.", 'success')
    return redirect(url_for('main.manage_matieres'))


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('admin_pin_verified', None) # Efface la vérification du PIN à la déconnexion
    return redirect(url_for('main.home')) # Redirige vers la nouvelle page d'accueil

# ===================================================================
# ==                ROUTES POUR LES NOTIFICATIONS PUSH             ==
# ===================================================================

@main_bp.route('/api/vapid-public-key')
@login_required
def get_vapid_public_key():
    """Fournit la clé publique VAPID au client."""
    return current_app.config['VAPID_PUBLIC_KEY']

@main_bp.route('/api/subscribe', methods=['POST'])
@login_required
def subscribe_push():
    """Abonne un utilisateur aux notifications push."""
    subscription_data = request.get_json()
    if not subscription_data:
        return jsonify({'error': 'Aucune donnée d\'abonnement fournie'}), 400

    # Vérifier si l'abonnement existe déjà pour cet utilisateur
    endpoint = subscription_data.get('endpoint')
    existing_subscription = PushSubscription.query.filter_by(user_id=current_user.id).filter(PushSubscription.subscription_json.like(f'%"{endpoint}"%')).first()

    if not existing_subscription:
        new_subscription = PushSubscription(
            user_id=current_user.id,
            subscription_json=json.dumps(subscription_data)
        )
        db.session.add(new_subscription)
        db.session.commit()
        
    return jsonify({'success': True}), 201

def send_push_notification(user_id, title, body, url):
    """
    Fonction d'aide pour envoyer une notification push à un utilisateur spécifique.
    """
    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    if not subscriptions:
        return

    payload = {
        'title': title,
        'body': body,
        'url': url_for('main.dashboard', _external=True) # URL par défaut
    }

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=json.loads(sub.subscription_json),
                data=json.dumps(payload),
                vapid_private_key=current_app.config['VAPID_PRIVATE_KEY'],
                vapid_claims=current_app.config['VAPID_CLAIMS']
            )
        except WebPushException as ex:
            current_app.logger.error(f"Erreur d'envoi de notification push: {ex}")
            # Si l'abonnement est expiré ou invalide (code 410), on le supprime
            if ex.response and ex.response.status_code == 410:
                db.session.delete(sub)
                db.session.commit()
