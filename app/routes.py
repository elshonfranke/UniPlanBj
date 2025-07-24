from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_required, current_user, login_user, logout_user
from app import db
from app import login_manager
from app.models import Utilisateur, Filiere, Niveau, Groupe, Cours, CoursAffectation, Notification, DisponibiliteEnseignant, Matiere, Salle
from datetime import datetime, timedelta
from .decorators import role_required
from sqlalchemy import or_, and_ # Importation des fonctions pour les requêtes complexes
from sqlalchemy.exc import IntegrityError # Pour gérer les erreurs de contrainte unique

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

    # Compter les notifications personnelles non lues pour le badge
    # Note : ce système simple ne compte pas les notifications de rôle comme "non lues"
    # pour éviter de les marquer comme lues pour tout le monde.
    unread_count = Notification.query.filter_by(destinataire_id=current_user.id, est_lue=False).count()
    
    return render_template('utilisateur/dashboard.html', emploi_du_temps=emploi_du_temps, prochain_cours=prochain_cours, notifications=notifications, unread_count=unread_count)

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

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

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
    unread_count = Notification.query.filter_by(destinataire_id=current_user.id, est_lue=False).count()

    # Récupérer aussi la liste des cours pour l'afficher
    all_courses = Cours.query.order_by(Cours.date_cours.desc(), Cours.heure_debut.desc()).all()
    return render_template('admin/dashboard.html', users=users, pagination=pagination, courses=all_courses, online_users=online_users, notifications=admin_notifications, unread_count=unread_count)

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
    unread_count = Notification.query.filter_by(destinataire_id=current_user.id, est_lue=False).count()

    return render_template('enseignant/dashboard.html', disponibilites=disponibilites, emploi_du_temps=emploi_du_temps, notifications=notifications, unread_count=unread_count)

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

    if request.method == 'POST':
        # Vérification du code PIN avant toute modification
        submitted_pin = request.form.get('pin')
        if submitted_pin != current_app.config['ADMIN_PIN']:
            flash('Code PIN incorrect. Les modifications n\'ont pas été enregistrées.', 'danger')
            # On redirige vers la même page pour que l'admin puisse réessayer
            return redirect(url_for('main.edit_user', user_id=user_id))

        # Récupération des données du formulaire
        user_to_edit.prenom = request.form.get('prenom')
        user_to_edit.nom = request.form.get('nom')
        user_to_edit.email = request.form.get('email')
        new_role = request.form.get('role')

        # Empêcher un administrateur de changer son propre rôle pour éviter de se bloquer
        if user_to_edit.id == current_user.id and user_to_edit.role != new_role:
            flash("Vous ne pouvez pas changer votre propre rôle.", 'danger')
            return redirect(url_for('main.edit_user', user_id=user_id))
        
        user_to_edit.role = new_role
        db.session.commit()
        flash(f"Le profil de {user_to_edit.prenom} {user_to_edit.nom} a été mis à jour.", 'success')
        return redirect(url_for('main.admin_dashboard'))

    return render_template('admin/edit_user.html', user=user_to_edit)

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

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('admin_pin_verified', None) # Efface la vérification du PIN à la déconnexion
    return redirect(url_for('main.home')) # Redirige vers la nouvelle page d'accueil
