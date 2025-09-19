-- Création de la base de données (si elle n'existe pas)
-- Ce script est destiné à être exécuté sur une base de données PostgreSQL.
-- La création de la base de données (ex: CREATE DATABASE uniplanjb;) et la connexion (\c uniplanjb)
-- doivent être faites manuellement dans votre terminal psql avant d'exécuter ce script.

-- Création des types ENUM personnalisés pour la robustesse
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role_enum_type') THEN
        CREATE TYPE role_enum_type AS ENUM('etudiant', 'enseignant', 'administrateur');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'destinataire_role_enum_type') THEN
        CREATE TYPE destinataire_role_enum_type AS ENUM('etudiant', 'enseignant', 'administrateur', 'all');
    END IF;
END$$;

-- Table pour les Filières (ex: Informatique, Génie Civil, Droit)
CREATE TABLE filieres (
    id SERIAL PRIMARY KEY,
    nom_filiere VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

-- Table pour les Niveaux (ex: L1, L2, L3, M1, M2)
CREATE TABLE niveaux (
    id SERIAL PRIMARY KEY,
    nom_niveau VARCHAR(20) NOT NULL UNIQUE
);

-- Table pour les Groupes (pour les TD/TP, ex: Groupe A, Groupe B)
CREATE TABLE groupes (
    id SERIAL PRIMARY KEY,
    nom_groupe VARCHAR(50) NOT NULL,
    filiere_id INT NOT NULL REFERENCES filieres(id) ON DELETE CASCADE,
    niveau_id INT NOT NULL REFERENCES niveaux(id) ON DELETE CASCADE,
    UNIQUE (nom_groupe, filiere_id, niveau_id)
);

-- Table pour les Utilisateurs (Étudiants, Enseignants, Admin)
CREATE TABLE utilisateurs (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    mot_de_passe_hash VARCHAR(128) NOT NULL,
    role role_enum_type DEFAULT 'etudiant' NOT NULL,
    last_seen TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    picture VARCHAR(20) NOT NULL DEFAULT 'default.jpg',
    filiere_id INT REFERENCES filieres(id) ON DELETE SET NULL,
    niveau_id INT REFERENCES niveaux(id) ON DELETE SET NULL,
    groupe_id INT REFERENCES groupes(id) ON DELETE SET NULL
);

-- Table pour les Salles de Cours (ex: Amphi A, Salle B101)
CREATE TABLE salles (
    id SERIAL PRIMARY KEY,
    nom_salle VARCHAR(50) NOT NULL UNIQUE,
    capacite INT
);

-- Table pour les Matières (ex: Programmation Python, Algorithmique)
CREATE TABLE matieres (
    id SERIAL PRIMARY KEY,
    nom_matiere VARCHAR(100) NOT NULL,
    code_matiere VARCHAR(20) NOT NULL UNIQUE,
    description TEXT
);

-- Table pour les Cours (représente une SÉANCE de cours spécifique à une date et heure)
CREATE TABLE cours (
    id SERIAL PRIMARY KEY,
    matiere_id INT NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    enseignant_id INT NOT NULL REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    salle_id INT NOT NULL REFERENCES salles(id) ON DELETE RESTRICT,
    date_cours DATE NOT NULL,
    heure_debut TIME NOT NULL,
    heure_fin TIME NOT NULL,
    description TEXT
);

-- Table de liaison pour les Cours et leurs Affectations spécifiques (filière/niveau/groupe)
CREATE TABLE cours_affectations (
    id SERIAL PRIMARY KEY,
    cours_id INT NOT NULL REFERENCES cours(id) ON DELETE CASCADE,
    filiere_id INT REFERENCES filieres(id) ON DELETE CASCADE,
    niveau_id INT REFERENCES niveaux(id) ON DELETE CASCADE,
    groupe_id INT REFERENCES groupes(id) ON DELETE CASCADE
);

-- Table pour les Notifications
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    titre VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    date_creation TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    destinataire_role destinataire_role_enum_type NOT NULL,
    destinataire_id INT REFERENCES utilisateurs(id) ON DELETE CASCADE,
    est_lue BOOLEAN DEFAULT FALSE
);

-- Table pour les disponibilités des enseignants
CREATE TABLE disponibilites_enseignants (
    id SERIAL PRIMARY KEY,
    enseignant_id INT NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    jour_semaine VARCHAR(10) NOT NULL CHECK (jour_semaine IN ('Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi')),
    heure_debut TIME NOT NULL,
    heure_fin TIME NOT NULL,
    UNIQUE (enseignant_id, jour_semaine, heure_debut)
);

-- Table pour les abonnements aux notifications Push
CREATE TABLE push_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    subscription_json TEXT NOT NULL
);

-- Table de liaison pour les matières enseignées par un enseignant
CREATE TABLE enseigne (
    id SERIAL PRIMARY KEY,
    enseignant_id INT NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    matiere_id INT NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    filiere_id INT NOT NULL REFERENCES filieres(id) ON DELETE CASCADE,
    niveau_id INT NOT NULL REFERENCES niveaux(id) ON DELETE CASCADE,
    UNIQUE (enseignant_id, matiere_id, filiere_id, niveau_id)
);

-- Table pour les conversations de messagerie privée
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    participant1_id INT NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    participant2_id INT NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    last_message_time TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    UNIQUE (participant1_id, participant2_id)
);

-- Table pour les messages
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id INT NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    body TEXT,
    image_url VARCHAR(255),
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    is_read BOOLEAN DEFAULT FALSE NOT NULL,
    CHECK (body IS NOT NULL OR image_url IS NOT NULL)
);