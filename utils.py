import sqlite3
import re
import pandas as pd
import streamlit as st
import json

DB_PATH = "turf_analytics.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_conn() as conn:
        cursor = conn.cursor()
        # On ajoute json_data pour stocker "tout" l'import
        cursor.execute("""CREATE TABLE IF NOT EXISTS selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            date TEXT, 
            hippodrome TEXT, 
            course_num TEXT, 
            cheval TEXT, 
            numero INTEGER, 
            cote REAL, 
            musique TEXT, 
            corde TEXT, 
            ferreur TEXT,
            json_data TEXT)""") # <--- NOUVEAU
        
        cursor.execute("""CREATE TABLE IF NOT EXISTS paris (
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
            gain_net REAL,
            type_pari TEXT DEFAULT 'Simple Gagnant',
            mode_pari TEXT DEFAULT '-')""")
        conn.commit()

def clean_text(text):
    return str(text).strip().upper() if text and not pd.isna(text) else ""

def get_course_label(val):
    try:
        match = re.search(r'C(\d+)', str(val))
        if match:
            c_num = match.group(1)
            return f"C{c_num[0]}" if len(c_num) > 1 else f"C{c_num}"
        return str(val)
    except: return "C?"

def clean_float(value):
    try:
        if isinstance(value, str):
            value = value.replace(',', '.').replace('€', '').strip()
        num = round(float(value), 1)
        return num if num > 0 else 1.0
    except: return 1.0

def run_query(query, params=(), commit=False):
    conn = get_conn()
    cursor = conn.cursor()
    result = None
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
        else:
            data = cursor.fetchall()
            if cursor.description:
                cols = [column[0] for column in cursor.description]
                result = pd.DataFrame(data, columns=cols)
    except Exception as e:
        if "duplicate column name" not in str(e):
            st.error(f"Erreur SQL : {e}")
    finally:
        cursor.close()
        conn.close()
    return result