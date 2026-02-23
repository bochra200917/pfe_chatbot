# Chatbot Intelligent connecté à Dolibarr – Version 1

## Description

Ce projet consiste à développer un chatbot intelligent capable d’interroger la base de données Dolibarr afin d’extraire des informations comptables et commerciales de manière automatisée.

La Version 1 (V1) implémente les fonctionnalités principales d’interrogation SQL dynamique avec journalisation complète des requêtes.

---

## Fonctionnalités implémentées (V1)

- Extraction des factures entre deux dates
- Extraction des factures pour un client spécifique
- Calcul du total des ventes par période (mois/année)
- Détection des factures avec montants négatifs (avoirs)
- Journalisation des requêtes exécutées (logs JSON)
- Mesure du temps d’exécution des requêtes

---

## Technologies utilisées

- Python 3.13.7
- MySQL (Base Dolibarr)
- PyMySQL
- python-dotenv
- JSON (logging)

---

## Installation

### Cloner le projet

git clone <url_du_projet>
cd <nom_du_projet>

### Créer un environnement virtuel

python -m venv venv

### Activer l’environnement (Windows)

venv\Scripts\activate

### Installer les dépendances

pip install -r requirements.txt

---

## Configuration

Créer un fichier `.env` à la racine du projet avec :

DB_HOST=localhost  
DB_USER=votre_user  
DB_PASSWORD=votre_mot_de_passe  
DB_NAME=votre_base_dolibarr  

---

## Lancer les tests

python test_chatbot.py

---

## Exemples de requêtes supportées

- factures entre 2026-01-01 et 2026-01-07  
- factures pour le client Mickael  
- total ventes janvier 2026  
- factures avec montants négatifs  

---

## Journalisation

Chaque requête exécutée est enregistrée avec :

- Timestamp  
- Question utilisateur  
- Requête SQL générée  
- Temps d’exécution  
- Nombre de lignes retournées  
- Statut d’exécution  

---

## Évolutions prévues (V2)

- Intégration d’un module NLP  
- Interface graphique  
- Visualisation des données  
- Gestion des rôles utilisateurs  

---

## Contexte académique

Projet réalisé dans le cadre d’un Projet de Fin d’Études (PFE).