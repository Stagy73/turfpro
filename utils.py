import sqlite3
import re
import pandas as pd

# Chemin vers la base de données locale
DB_PATH = "turf_analytics.db"

def get_conn():
    """Crée une connexion à la base de données SQLite."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialise la structure de la base de données."""
    conn = get_conn()
    
    # Table 1 : Sélections (Pour le programme importé le matin)
    conn.execute("""CREATE TABLE IF NOT EXISTS selections (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        date TEXT, 
        hippodrome TEXT, 
        course_num TEXT, 
        cheval TEXT, 
        numero INTEGER, 
        cote REAL, 
        musique TEXT DEFAULT '', 
        corde TEXT DEFAULT '', 
        ferreur TEXT DEFAULT '')""")
    
    # Table 2 : Paris (Pour tes résultats réels et ton historique financier)
    conn.execute("""CREATE TABLE IF NOT EXISTS paris (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        date TEXT, 
        hippodrome TEXT, 
        course_num TEXT, 
        cheval TEXT, 
        numero INTEGER, 
        cote REAL, 
        mise REAL, 
        resultat TEXT, 
        rapport REAL, 
        gain_net REAL)""")
    
    conn.commit()
    conn.close()

def get_course_label(val):
    """
    Nettoie les codes techniques des fichiers CSV.
    Exemple : 'R1C101' devient 'C1'.
    """
    try:
        s = str(val)
        # Cherche le numéro après le 'C'
        match = re.search(r'C(\d+)', s)
        if match:
            c_num = match.group(1)
            # Si le code est R1C101, on extrait juste le '1'
            return f"C{c_num[0]}" if len(c_num) > 1 else f"C{c_num}"
        return s
    except: 
        return "C?"

def clean_float(value):
    """
    Nettoie les nombres et arrondit à 1 chiffre après la virgule.
    Exemple : '41000,0' devient 41000.0 ou '7,42' devient 7.4.
    """
    try:
        if isinstance(value, str):
            # Remplace la virgule par un point et retire les symboles €
            value = value.replace(',', '.').replace('€', '').strip()
        
        # On transforme en nombre et on arrondit à 1 décimale
        return round(float(value), 1)
    except: 
        return 0.0