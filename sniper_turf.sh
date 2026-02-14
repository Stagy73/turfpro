#!/bin/bash
# Aller dans le dossier du projet
cd ~/D/turfpro/

# 1. Télécharger la nouvelle base
curl -s -O https://www.turf.bzh/downloads/turfbzh_database.db

# 2. Créer le fichier de résultats du jour
echo "--- PRONOSTICS DU $(date +%Y-%m-%d) ---" > pronos_du_jour.txt

# 3. Extraire les pépites et les mettre dans le fichier
sqlite3 turfbzh_database.db "SELECT Course, Cheval, ROUND((IA_Gagnant * 200 + Note_IA_Decimale * 2 + 10 / (CASE WHEN Cote > 0 THEN Cote ELSE 1 END) + COALESCE(Synergie_JCh, 0) * 2), 2) AS Score FROM courses WHERE date = date('now') AND Score > 170 ORDER BY Score DESC;" >> pronos_du_jour.txt

echo "Terminé. Les pronos sont dans pronos_du_jour.txt"