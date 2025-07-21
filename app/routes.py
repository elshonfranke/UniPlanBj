from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user, login_user
from app import db # Importe l'instance de la base de données
# ...existing code...
from app.models import Utilisateur, Cours, CoursAffectation, Notification, RoleEnum, Filiere, Niveau, Groupe
from app import login_manager
# ...existing code...
from flask import request, flash, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import Utilisateur
from werkzeug.security import generate_password_hash

# ...existing code...

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

@main_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # 1. Récupération des données du formulaire
        prenom = request.form.get('prenom')
        nom = request.form.get('nom')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        # 2. Vérification des champs obligatoires
        if not (prenom and nom and email and password and role):
            flash("Tous les champs sont obligatoires.", "danger")
            return render_template('auth/register.html')

        # 3. Vérification de l'unicité de l'email
        if Utilisateur.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
            return render_template('auth/register.html')

        # 4. Création et sauvegarde de l'utilisateur
        user = Utilisateur(
            prenom=prenom,
            nom=nom,
            email=email,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()

        # 5. Message de succès et redirection vers la connexion
        flash("Inscription réussie, vous pouvez vous connecter.", "success")
        return redirect(url_for('main.login'))

    # 6. Affichage du formulaire d'inscription (GET)
    return render_template('auth/register.html')
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = Utilisateur.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Connexion réussie !", "success")
            return redirect(url_for('main.dashboard'))
        else:
            flash("Email ou mot de passe incorrect.", "danger")
            return render_template("auth/login.html")
    return render_template("auth/login.html")


