🏇 Turf Analytics Pro
Application de gestion et d'analyse de paris hippiques développée avec Streamlit et SQLite. Ce projet permet d'importer des programmes de courses, de gérer ses paris (Simples, Couplés, Trios, Z4, etc.) et d'analyser ses performances financières.

📋 Fonctionnalités
Dashboard : Visualisation du Profit Net, ROI et taux de réussite via des graphiques dynamiques.

Sélections : Consultation du programme du jour (Musique, Corde, Ferrures avec code couleur).

Saisie Paris : Enregistrement manuel simplifié avec menus déroulants liés au programme importé.

Import/Export : Moteur robuste pour charger les fichiers CSV (type export_turfbzh) en ignorant les lignes corrompues.

Backtest : Simulation de stratégies basées sur l'historique des données.

🛠️ Installation en local
1. Prérequis
Assure-toi d'avoir Python 3.10+ installé sur ton système.

2. Cloner le projet
Code snippet

git clone git@github.com:Stagy73/turfpro.git
cd turfpro
3. Installer les dépendances
Installe les bibliothèques nécessaires avec pip :

Code snippet

pip install streamlit pandas plotly
4. Structure des fichiers
Le projet doit respecter l'arborescence suivante pour fonctionner :

Plaintext

.
├── app.py                # Page d'accueil et configuration
├── utils.py              # Fonctions SQL et nettoyage de données
├── turf_analytics.db     # Base de données SQLite (générée automatiquement)
└── pages/                # Dossier contenant les modules
    ├── 1_📊_Dashboard.py
    ├── 2_📝_Saisie_Paris.py
    ├── 3_🎯_Selections.py
    ├── 4_📈_Backtest.py
    └── 5_📥_Import_Export.py
🚀 Lancement
Pour démarrer l'application, utilise la commande suivante à la racine du projet :

Code snippet

streamlit run app.py
L'interface sera alors accessible dans ton navigateur à l'adresse : http://localhost:8501

📊 Utilisation
Étape 1 : Va dans l'onglet Import / Export pour charger ton fichier CSV du jour.

Étape 2 : Consulte tes chevaux dans Sélections.

Étape 3 : Enregistre tes mises réelles dans Saisie Paris.

Étape 4 : Analyse tes gains dans le Dashboard.