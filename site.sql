-- Création de la base de données (si elle n'existe pas)
CREATE DATABASE IF NOT EXISTS UNIPLANBJ;

-- Utiliser la base de données
USE UNIPLANBJ;

-- Table pour les Filières (ex: Informatique, Génie Civil, Droit)
CREATE TABLE filieres (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom_filiere VARCHAR(100) NOT NULL UNIQUE
);

-- Table pour les Niveaux (ex: L1, L2, L3, M1, M2)
CREATE TABLE niveaux (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom_niveau VARCHAR(20) NOT NULL UNIQUE
);

-- Table pour les Groupes (pour les TD/TP, ex: Groupe A, Groupe B)
CREATE TABLE groupes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom_groupe VARCHAR(50) NOT NULL,
    niveau_id INT NOT NULL,
    
    CONSTRAINT fk_groupe_niveau
        FOREIGN KEY (niveau_id) REFERENCES niveaux(id)
        ON DELETE CASCADE, -- Si un niveau est supprimé, ses groupes sont aussi supprimés
    
    UNIQUE (nom_groupe, niveau_id) -- Un groupe 'A' ne peut exister qu'une seule fois par niveau
);

-- Table pour les Utilisateurs (Étudiants, Enseignants, Admin)
CREATE TABLE utilisateurs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    mot_de_passe_hash VARCHAR(128) NOT NULL,
    role ENUM('etudiant', 'enseignant', 'administrateur') DEFAULT 'etudiant',
    filiere_id INT, -- NULL pour admin/enseignant
    niveau_id INT, -- NULL pour admin/enseignant, pour les étudiants le niveau principal
    groupe_id INT, -- NULL pour admin/enseignant, pour les étudiants leur groupe principal
    
    CONSTRAINT fk_utilisateur_filiere
        FOREIGN KEY (filiere_id) REFERENCES filieres(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_utilisateur_niveau
        FOREIGN KEY (niveau_id) REFERENCES niveaux(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_utilisateur_groupe
        FOREIGN KEY (groupe_id) REFERENCES groupes(id)
        ON DELETE SET NULL
);

-- Table pour les Salles de Cours (ex: Amphi A, Salle B101)
CREATE TABLE salles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom_salle VARCHAR(50) NOT NULL UNIQUE,
    capacite INT
);

-- Table pour les Matières (ex: Programmation Python, Algorithmique)
CREATE TABLE matieres (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom_matiere VARCHAR(100) NOT NULL,
    code_matiere VARCHAR(20) NOT NULL UNIQUE, -- Code unique pour la matière (ex: INF101)
    description TEXT
);

-- Table pour les Cours (représente une SÉANCE de cours spécifique à une date et heure)
CREATE TABLE cours (
    id INT AUTO_INCREMENT PRIMARY KEY,
    matiere_id INT NOT NULL,
    enseignant_id INT NOT NULL, -- L'ID de l'utilisateur qui est l'enseignant
    salle_id INT NOT NULL,
    
    date_cours DATE NOT NULL,
    heure_debut TIME NOT NULL,
    heure_fin TIME NOT NULL,
    -- duree_minutes INT, -- Peut être calculée à partir de heure_debut et heure_fin
    description TEXT,
    
    CONSTRAINT fk_cours_matiere
        FOREIGN KEY (matiere_id) REFERENCES matieres(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_cours_enseignant
        FOREIGN KEY (enseignant_id) REFERENCES utilisateurs(id)
        ON DELETE RESTRICT, -- Empêche la suppression d'un enseignant s'il a des cours
    CONSTRAINT fk_cours_salle
        FOREIGN KEY (salle_id) REFERENCES salles(id)
        ON DELETE RESTRICT -- Empêche la suppression d'une salle si elle est utilisée
);

-- Table de liaison pour les Cours et leurs Affectations spécifiques (filière/niveau/groupe)
-- Un cours peut être pour une filière entière, un niveau d'une filière, ou un groupe spécifique.
CREATE TABLE cours_affectations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cours_id INT NOT NULL,
    filiere_id INT, -- NULL si le cours n'est pas spécifiquement lié à une filière ici
    niveau_id INT, -- NULL si le cours n'est pas spécifiquement lié à un niveau ici
    groupe_id INT, -- NULL si le cours n'est pas spécifiquement lié à un groupe ici
    
    CONSTRAINT fk_affectation_cours
        FOREIGN KEY (cours_id) REFERENCES cours(id)
        ON DELETE CASCADE, -- Si le cours est supprimé, son affectation est supprimée
    CONSTRAINT fk_affectation_filiere
        FOREIGN KEY (filiere_id) REFERENCES filieres(id)
        ON DELETE CASCADE, -- Si une filière est supprimée, les affectations la concernant sont supprimées
    CONSTRAINT fk_affectation_niveau
        FOREIGN KEY (niveau_id) REFERENCES niveaux(id)
        ON DELETE CASCADE, -- Si un niveau est supprimé, les affectations le concernant sont supprimées
    CONSTRAINT fk_affectation_groupe
        FOREIGN KEY (groupe_id) REFERENCES groupes(id)
        ON DELETE CASCADE -- Si un groupe est supprimé, les affectations le concernant sont supprimées
);

-- Table pour les Notifications
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titre VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
    destinataire_role ENUM('etudiant', 'enseignant', 'administrateur', 'all') NOT NULL,
    destinataire_id INT, -- NULL si la notification est pour un rôle complet ('all', 'etudiant', etc.)
    est_lue BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT fk_notification_utilisateur
        FOREIGN KEY (destinataire_id) REFERENCES utilisateurs(id)
        ON DELETE CASCADE -- Si l'utilisateur spécifique est supprimé, ses notifications sont supprimées
);