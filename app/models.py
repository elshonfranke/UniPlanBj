# app/models.py
from app import db # Importe l'objet db de votre __init__.py
from datetime import datetime # Pour les champs de date/heure
from werkzeug.security import generate_password_hash, check_password_hash # Pour le hachage des mots de passe
from flask_login import UserMixin # Pour faciliter l'intégration avec Flask-Login
from enum import Enum 
# Modèle pour les Filières (ex: Informatique, Génie Civil, Droit)
class RoleEnum(Enum):
    ETUDIANT = "etudiant"
    ENSEIGNANT = "enseignant"
    ADMINISTRATEUR = "administrateur"
class Filiere(db.Model):
    __tablename__ = 'filieres' # Nom de la table dans la BDD, correspond au SQL
    id = db.Column(db.Integer, primary_key=True)
    nom_filiere = db.Column(db.String(100), unique=True, nullable=False)

    # Relations inverses:
    # Un utilisateur peut appartenir à une filière
    utilisateurs = db.relationship('Utilisateur', backref='filiere_obj', lazy='dynamic')
    # Une affectation de cours peut concerner une filière
    cours_affectations = db.relationship('CoursAffectation', backref='filiere_obj', lazy='dynamic')

    def __repr__(self):
        return f'<Filiere {self.nom_filiere}>'

# Modèle pour les Niveaux (ex: L1, L2, L3, M1, M2)
class Niveau(db.Model):
    __tablename__ = 'niveaux' # Nom de la table dans la BDD
    id = db.Column(db.Integer, primary_key=True)
    nom_niveau = db.Column(db.String(20), unique=True, nullable=False)

    # Relations inverses:
    # Un groupe appartient à un niveau
    groupes = db.relationship('Groupe', backref='niveau_obj', lazy='dynamic')
    # Un utilisateur (étudiant) peut avoir un niveau
    utilisateurs = db.relationship('Utilisateur', backref='niveau_obj', lazy='dynamic')
    # Une affectation de cours peut concerner un niveau
    cours_affectations = db.relationship('CoursAffectation', backref='niveau_obj', lazy='dynamic')

    def __repr__(self):
        return f'<Niveau {self.nom_niveau}>'

# Modèle pour les Groupes (pour les TD/TP, ex: Groupe A, Groupe B)
class Groupe(db.Model):
    __tablename__ = 'groupes' # Nom de la table dans la BDD
    id = db.Column(db.Integer, primary_key=True)
    nom_groupe = db.Column(db.String(50), nullable=False)
    niveau_id = db.Column(db.Integer, db.ForeignKey('niveaux.id'), nullable=False)

    # Contrainte d'unicité composite pour s'assurer qu'un groupe est unique par niveau
    __table_args__ = (db.UniqueConstraint('nom_groupe', 'niveau_id', name='_nom_groupe_niveau_uc'),)

    # Relations inverses:
    # Un utilisateur (étudiant) peut appartenir à un groupe
    utilisateurs = db.relationship('Utilisateur', backref='groupe_obj', lazy='dynamic')
    # Une affectation de cours peut concerner un groupe
    cours_affectations = db.relationship('CoursAffectation', backref='groupe_obj', lazy='dynamic')

    def __repr__(self):
        return f'<Groupe {self.nom_groupe} (Niveau {self.niveau_obj.nom_niveau})>'


# Modèle pour les Utilisateurs (Étudiants, Enseignants, Admin)
# UserMixin fournit des implémentations génériques pour les propriétés requises par Flask-Login
class Utilisateur(db.Model, UserMixin):
    __tablename__ = 'utilisateurs' # Nom de la table dans la BDD
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    mot_de_passe_hash = db.Column(db.String(128), nullable=False)
    # Utilisation de db.Enum pour le type ENUM de MySQL
    role = db.Column(db.Enum('etudiant', 'enseignant', 'administrateur'), default='etudiant', nullable=False)
    
    # Clés étrangères, nullable pour les enseignants/admins
    filiere_id = db.Column(db.Integer, db.ForeignKey('filieres.id'), nullable=True)
    niveau_id = db.Column(db.Integer, db.ForeignKey('niveaux.id'), nullable=True)
    groupe_id = db.Column(db.Integer, db.ForeignKey('groupes.id'), nullable=True)

    # Relations directes pour les cours enseignés et les notifications reçues
    enseigne_cours = db.relationship('Cours', backref='enseignant_obj', foreign_keys='Cours.enseignant_id', lazy='dynamic')
    notifications_recues = db.relationship('Notification', backref='destinataire_obj', foreign_keys='Notification.destinataire_id', lazy='dynamic')

    # Méthodes pour le hachage et la vérification des mots de passe
    def set_password(self, password):
        self.mot_de_passe_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.mot_de_passe_hash, password)

    # Méthode requise par Flask-Login pour obtenir l'ID de l'utilisateur sous forme de chaîne
    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<Utilisateur {self.prenom} {self.nom} ({self.role})>'


# Modèle pour les Salles de Cours (ex: Amphi A, Salle B101)
class Salle(db.Model):
    __tablename__ = 'salles' # Nom de la table dans la BDD
    id = db.Column(db.Integer, primary_key=True)
    nom_salle = db.Column(db.String(50), unique=True, nullable=False)
    capacite = db.Column(db.Integer)

    # Relation inverse: un cours est associé à une salle
    cours = db.relationship('Cours', backref='salle_obj', lazy='dynamic')

    def __repr__(self):
        return f'<Salle {self.nom_salle}>'


# Modèle pour les Matières (ex: Programmation Python, Algorithmique)
class Matiere(db.Model):
    __tablename__ = 'matieres' # Nom de la table dans la BDD
    id = db.Column(db.Integer, primary_key=True)
    nom_matiere = db.Column(db.String(100), nullable=False)
    code_matiere = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)

    # Relation inverse: un cours est associé à une matière
    cours = db.relationship('Cours', backref='matiere_obj', lazy='dynamic')

    def __repr__(self):
        return f'<Matiere {self.nom_matiere} ({self.code_matiere})>'


# Modèle pour les Cours (représente une SÉANCE de cours spécifique à une date et heure)
class Cours(db.Model):
    __tablename__ = 'cours' # Nom de la table dans la BDD
    id = db.Column(db.Integer, primary_key=True)
    matiere_id = db.Column(db.Integer, db.ForeignKey('matieres.id'), nullable=False)
    enseignant_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    salle_id = db.Column(db.Integer, db.ForeignKey('salles.id'), nullable=False)
    
    date_cours = db.Column(db.Date, nullable=False) # Type Date pour la date seule
    heure_debut = db.Column(db.Time, nullable=False) # Type Time pour l'heure seule
    heure_fin = db.Column(db.Time, nullable=False) # Type Time pour l'heure seule
    description = db.Column(db.Text)

    # Relation inverse: une affectation de cours est associée à un cours
    cours_affectations = db.relationship('CoursAffectation', backref='cours_obj', lazy='dynamic')

    def __repr__(self):
        return f'<Cours {self.matiere_obj.code_matiere} - {self.date_cours} {self.heure_debut}>'


# Modèle pour la table de liaison Cours_Affectations
class CoursAffectation(db.Model):
    __tablename__ = 'cours_affectations' # Nom de la table dans la BDD
    id = db.Column(db.Integer, primary_key=True)
    cours_id = db.Column(db.Integer, db.ForeignKey('cours.id'), nullable=False)
    # Ces champs sont nullable car une affectation peut être plus générale
    filiere_id = db.Column(db.Integer, db.ForeignKey('filieres.id'), nullable=True)
    niveau_id = db.Column(db.Integer, db.ForeignKey('niveaux.id'), nullable=True)
    groupe_id = db.Column(db.Integer, db.ForeignKey('groupes.id'), nullable=True)

    # Vous pouvez ajouter une contrainte unique pour éviter les doublons d'affectation
    # __table_args__ = (db.UniqueConstraint('cours_id', 'filiere_id', 'niveau_id', 'groupe_id', name='_cours_affectation_uc'),)

    def __repr__(self):
        return f'<Affectation Cours {self.cours_id} - Fil: {self.filiere_id} Niv: {self.niveau_id} Grp: {self.groupe_id}>'


# Modèle pour les Notifications
class Notification(db.Model):
    __tablename__ = 'notifications' # Nom de la table dans la BDD
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Utilisation de db.Enum pour le type ENUM de MySQL
    destinataire_role = db.Column(db.Enum('etudiant', 'enseignant', 'administrateur', 'all'), nullable=False)
    destinataire_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True) # Nullable si 'all' ou un rôle générique
    est_lue = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Notification "{self.titre[:20]}..." pour {self.destinataire_role}>'
