# app/models.py
from app import db # Importe l'objet db de votre __init__.py
from datetime import datetime # Pour les champs de date/heure
from werkzeug.security import generate_password_hash, check_password_hash # Pour le hachage des mots de passe
from flask_login import UserMixin # Pour faciliter l'intégration avec Flask-Login
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from flask import current_app
from enum import Enum 
from sqlalchemy import or_, Enum as SQLAlchemyEnum
# Modèle pour les Filières (ex: Informatique, Génie Civil, Droit)
class RoleEnum(Enum):
    ETUDIANT = "etudiant"
    ENSEIGNANT = "enseignant"
    ADMINISTRATEUR = "administrateur"

class DestinataireRoleEnum(Enum):
    ETUDIANT = "etudiant"
    ENSEIGNANT = "enseignant"
    ADMINISTRATEUR = "administrateur"
    ALL = "all"
class Filiere(db.Model):
    __tablename__ = 'filieres' # Nom de la table dans la BDD, correspond au SQL
    id = db.Column(db.Integer, primary_key=True)
    nom_filiere = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Relations inverses:
    # Un groupe appartient à une filière
    groupes = db.relationship('Groupe', backref='filiere_obj', lazy='dynamic')
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
    # Une affectation de cours peut concerner un niveau
    cours_affectations = db.relationship('CoursAffectation', backref='niveau_obj', lazy='dynamic')

    def __repr__(self):
        return f'<Niveau {self.nom_niveau}>'

# Modèle pour les Groupes (pour les TD/TP, ex: Groupe A, Groupe B)
class Groupe(db.Model):
    __tablename__ = 'groupes' # Nom de la table dans la BDD
    id = db.Column(db.Integer, primary_key=True)
    nom_groupe = db.Column(db.String(50), nullable=False)
    filiere_id = db.Column(db.Integer, db.ForeignKey('filieres.id'), nullable=False)
    niveau_id = db.Column(db.Integer, db.ForeignKey('niveaux.id'), nullable=False)

    # Contrainte d'unicité composite pour s'assurer qu'un groupe est unique par filière et par niveau
    __table_args__ = (db.UniqueConstraint('nom_groupe', 'filiere_id', 'niveau_id', name='_nom_groupe_filiere_niveau_uc'),)

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
    # Utilisation de SQLAlchemyEnum avec un Enum Python pour la compatibilité avec PostgreSQL
    role = db.Column(
        SQLAlchemyEnum(
            RoleEnum,
            name="role_enum_type",
            native_enum=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            validate_strings=True,
        ),
        default=RoleEnum.ETUDIANT,
        nullable=False,
    )
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    picture = db.Column(db.String(20), nullable=False, default='default.jpg')
    
    # Clé étrangère, nullable pour les enseignants/admins. Un étudiant est lié à un groupe.
    groupe_id = db.Column(db.Integer, db.ForeignKey('groupes.id'), nullable=True)
    # NOUVEAUX CHAMPS pour lier directement un étudiant à une filière/niveau.
    # C'est utile pour les requêtes et la logique du tableau de bord.
    # Nullable pour les non-étudiants.
    filiere_id = db.Column(db.Integer, db.ForeignKey('filieres.id'), nullable=True)
    niveau_id = db.Column(db.Integer, db.ForeignKey('niveaux.id'), nullable=True)

    # Relations pour accéder directement à l'objet Filiere et Niveau depuis un Utilisateur.
    # C'est ce qui permet à `current_user.filiere_obj` et `current_user.niveau_obj` de fonctionner.
    filiere_obj = db.relationship('Filiere', foreign_keys=[filiere_id], backref=db.backref('etudiants', lazy='dynamic'))
    niveau_obj = db.relationship('Niveau', foreign_keys=[niveau_id], backref=db.backref('etudiants', lazy='dynamic'))

    # Relations directes pour les cours enseignés et les notifications reçues
    enseigne_cours = db.relationship('Cours', backref='enseignant_obj', foreign_keys='Cours.enseignant_id', lazy='dynamic')
    notifications_recues = db.relationship('Notification', backref='destinataire_obj', foreign_keys='Notification.destinataire_id', lazy='dynamic')
    # Relation pour les disponibilités
    disponibilites = db.relationship('DisponibiliteEnseignant', backref='enseignant_obj', lazy='dynamic', cascade="all, delete-orphan")

    # Méthodes pour le hachage et la vérification des mots de passe
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='author', lazy='dynamic')

    @property
    def initial(self):
        """Retourne les initiales du prénom et du nom de l'utilisateur."""
        initials = ""
        if self.prenom:
            initials += self.prenom[0].upper()
        if self.nom:
            initials += self.nom[0].upper()
        return initials if initials else '?'

    def get_avatar_color(self):
        """
        Génère une couleur de fond pour l'avatar en fonction du nom.
        Cela garantit que chaque utilisateur aura toujours la même couleur.
        """
        # Liste de couleurs de fond agréables et lisibles avec du texte blanc
        colors = [
            '#1abc9c', '#2ecc71', '#3498db', '#9b59b6', '#34495e',
            '#f1c40f', '#e67e22', '#e74c3c', '#7f8c8d', '#2c3e50'
        ]
        # Utilise un simple hash sur le nom pour choisir une couleur de manière déterministe
        if not self.nom:
            return colors[0]
        hash_code = sum(ord(char) for char in self.nom)
        return colors[hash_code % len(colors)]

    def new_messages_count(self):
        """Compte les messages non lus où l'utilisateur est participant mais pas l'expéditeur."""
        conversations = Conversation.query.filter(
            or_(
                Conversation.participant1_id == self.id,
                Conversation.participant2_id == self.id
            )
        ).all()
        if not conversations:
            return 0
        conversation_ids = [c.id for c in conversations]
        
        count = Message.query.filter(Message.conversation_id.in_(conversation_ids), Message.sender_id != self.id, Message.is_read == False).count()
        return count

    def set_password(self, password):
        self.mot_de_passe_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.mot_de_passe_hash, password)

    # Méthode requise par Flask-Login pour obtenir l'ID de l'utilisateur sous forme de chaîne
    def get_id(self):
        return str(self.id)

    def get_reset_token(self):
        """Génère un token de réinitialisation de mot de passe."""
        s = Serializer(current_app.config['SECRET_KEY'])
        # Le token sera valide pour la durée spécifiée dans verify_reset_token (30 min par défaut)
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        """Vérifie le token de réinitialisation."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except Exception: # Un token invalide ou expiré lèvera une exception
            # Le token est invalide ou a expiré
            return None
        return Utilisateur.query.get(user_id)

    def __repr__(self):
        return f'<Utilisateur {self.prenom} {self.nom} ({self.role})>'


# ===================================================================
# ==                  MODÈLES POUR LA MESSAGERIE                   ==
# ===================================================================

class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    participant1_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    participant2_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    last_message_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    participant1 = db.relationship('Utilisateur', foreign_keys=[participant1_id], backref=db.backref('conversations_as_p1', lazy='dynamic'))
    participant2 = db.relationship('Utilisateur', foreign_keys=[participant2_id], backref=db.backref('conversations_as_p2', lazy='dynamic'))

    messages = db.relationship('Message', backref='conversation', lazy='dynamic', cascade="all, delete-orphan")

    # Pour empêcher les doublons de conversation (1,2) et (2,1)
    __table_args__ = (db.UniqueConstraint('participant1_id', 'participant2_id', name='_conversation_participants_uc'),)

    def unread_messages_for(self, user):
        """Compte les messages non lus pour un utilisateur spécifique dans cette conversation."""
        if user.id not in [self.participant1_id, self.participant2_id]:
            return 0
        # Compte les messages dans cette conversation où l'expéditeur n'est pas l'utilisateur actuel et qui ne sont pas lus.
        return self.messages.filter(Message.sender_id != user.id, Message.is_read == False).count()

    def get_other_participant(self, user):
        if user.id == self.participant1_id:
            return self.participant2
        elif user.id == self.participant2_id:
            return self.participant1
        return None

    def last_message(self):
        return self.messages.order_by(Message.timestamp.desc()).first()

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    body = db.Column(db.Text, nullable=True) # Le corps du message peut être vide si une image est envoyée
    image_url = db.Column(db.String(255), nullable=True) # Pour stocker l'URL de l'image
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    # S'assurer qu'un message a soit du texte, soit une image pour ne pas être vide
    __table_args__ = (
        db.CheckConstraint('body IS NOT NULL OR image_url IS NOT NULL', name='_message_content_check'),
    )

    def __repr__(self):
        return f'<Message {self.id}>'

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
    cours_affectations = db.relationship('CoursAffectation', backref='cours_obj', lazy='dynamic', cascade="all, delete-orphan")

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
    # Utilisation de SQLAlchemyEnum pour la compatibilité avec PostgreSQL
    destinataire_role = db.Column(
        SQLAlchemyEnum(
            DestinataireRoleEnum,
            name="destinataire_role_enum_type",
            native_enum=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    destinataire_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True) # Nullable si 'all' ou un rôle générique
    est_lue = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Notification "{self.titre[:20]}..." pour {self.destinataire_role}>'

# Modèle pour la table de liaison Enseigne
# Indique quelle matière un enseignant enseigne, pour quelle filière et quel niveau.
class Enseigne(db.Model):
    __tablename__ = 'enseigne'
    id = db.Column(db.Integer, primary_key=True)
    enseignant_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey('matieres.id'), nullable=False)
    filiere_id = db.Column(db.Integer, db.ForeignKey('filieres.id'), nullable=False)
    niveau_id = db.Column(db.Integer, db.ForeignKey('niveaux.id'), nullable=False)

    # Contrainte d'unicité pour éviter les doublons
    __table_args__ = (db.UniqueConstraint('enseignant_id', 'matiere_id', 'filiere_id', 'niveau_id', name='_enseignant_matiere_filiere_niveau_uc'),)

    # Relations pour un accès facile depuis l'objet Enseigne
    enseignant = db.relationship('Utilisateur', backref=db.backref('enseignements', lazy='dynamic', cascade="all, delete-orphan"))
    matiere = db.relationship('Matiere', backref=db.backref('enseignements', lazy='dynamic'))
    filiere = db.relationship('Filiere', backref=db.backref('enseignements', lazy='dynamic'))
    niveau = db.relationship('Niveau', backref=db.backref('enseignements', lazy='dynamic'))

    def __repr__(self):
        return f'<Enseigne {self.enseignant.nom} -> {self.matiere.nom_matiere}>'
# Modèle pour les disponibilités des enseignants
class DisponibiliteEnseignant(db.Model):
    __tablename__ = 'disponibilites_enseignants'
    id = db.Column(db.Integer, primary_key=True)
    enseignant_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    # Utilisation d'un Enum pour les jours de la semaine pour la robustesse
    jour_semaine = db.Column(db.Enum('Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', name='jour_semaine_enum', native_enum=False), nullable=False)
    heure_debut = db.Column(db.Time, nullable=False)
    heure_fin = db.Column(db.Time, nullable=False)

    # Un enseignant ne peut pas avoir deux fois la même disponibilité
    __table_args__ = (db.UniqueConstraint('enseignant_id', 'jour_semaine', 'heure_debut', name='_enseignant_dispo_uc'),)

    def __repr__(self):
        return f'<Disponibilite {self.enseignant_obj.nom} - {self.jour_semaine} {self.heure_debut}>'

# Modèle pour stocker les abonnements aux notifications Push
class PushSubscription(db.Model):
    __tablename__ = 'push_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    subscription_json = db.Column(db.Text, nullable=False)

    # Relation inverse pour un accès facile depuis l'objet Utilisateur
    user = db.relationship('Utilisateur', backref=db.backref('push_subscriptions', lazy='dynamic', cascade="all, delete-orphan"))
