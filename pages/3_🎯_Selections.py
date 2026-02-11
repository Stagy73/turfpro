import streamlit as st
import pandas as pd
import json
import numpy as np
from utils import run_query, get_conn

st.set_page_config(layout="wide")

# --- STYLE CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;900&display=swap');
    .stApp { background-color: #F8FAFC; font-family: 'Outfit', sans-serif; }
    .main-title { font-weight: 900; font-size: 2.2rem; border-bottom: 4px solid #3A7BD5; padding-bottom:10px; color: #1E293B; }
    .course-header { background-color: #3A7BD5; color: white; padding: 10px; border-radius: 8px; margin-top: 25px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🎯 Sélections Personnalisées & Analyse IA</p>', unsafe_allow_html=True)

# --- FILTRE DATE ---
date_sel = st.date_input("Choisir une date", value=pd.Timestamp.now())
raw_data = run_query("SELECT * FROM selections WHERE date = ?", (str(date_sel),))

if raw_data is not None and not raw_data.empty:
    
    # --- DÉPAQUETAGE DES DONNÉES JSON ---
    list_dicts = []
    for _, row in raw_data.iterrows():
        try:
            if 'json_data' in row and row['json_data']:
                list_dicts.append(json.loads(row['json_data']))
            else:
                list_dicts.append({
                    "Numero": row.get('numero'), "Cheval": row.get('cheval'), 
                    "Cote": row.get('cote'), "Course": row.get('course_num'),
                    "hippodrome": row.get('hippodrome'), "ferrure": row.get('ferreur')
                })
        except: continue
    
    df_full = pd.DataFrame(list_dicts)

    # --- NETTOYAGE DES DONNÉES ---
    # Conversion des virgules en points pour les colonnes numériques
    cols_num = [c for c in df_full.columns if any(x in c.upper() for x in ['IA', 'TAUX', 'COTE', 'SIGMA', 'ELO', 'GAINS'])]
    for col in cols_num:
        df_full[col] = pd.to_numeric(df_full[col].astype(str).str.replace(',', '.'), errors='coerce')

    # --- CONFIGURATION SIDEBAR ---
    st.sidebar.header("📋 Affichage")
    toutes_les_cols = df_full.columns.tolist()
    
    pref = ['Course', 'Numero', 'Cheval', 'Cote', 'IA_Gagnant', 'ferrure', 'Musique']
    initial_selection = [c for c in pref if c in toutes_les_cols]

    display_cols = st.sidebar.multiselect("Colonnes à afficher :", options=toutes_les_cols, default=initial_selection)

    # --- FILTRE HIPPODROME ---
    hippos = sorted(df_full['hippodrome'].unique().tolist())
    hippo_choice = st.selectbox("Hippodrome", hippos)

    df_hippo = df_full[df_full['hippodrome'] == hippo_choice].copy()
    col_course_key = 'Course' if 'Course' in df_hippo.columns else 'course_num'
    courses = sorted(df_hippo[col_course_key].unique().tolist())

    # --- AFFICHAGE DES TABLEAUX ---
    for c in courses:
        st.markdown(f'<div class="course-header">🏁 Course {c}</div>', unsafe_allow_html=True)
        df_course = df_hippo[df_hippo[col_course_key] == c].sort_values('Numero').copy()

        if display_cols:
            # On prépare le style
            styler = df_course[display_cols].style
            
            # 1. Dégradé de vert pour l'IA (Correction de l'erreur ici)
            if 'IA_Gagnant' in display_cols:
                styler = styler.background_gradient(subset=['IA_Gagnant'], cmap='Greens')

            # 2. Formatage des nombres (IA en %, Cotes à 1 décimale)
            format_dict = {}
            for col in display_cols:
                if any(x in col.upper() for x in ['IA', 'TAUX']):
                    format_dict[col] = "{:.1%}" # Transforme 0.12 en 12.0%
                elif any(x in col.upper() for x in ['COTE', 'SIGMA', 'ELO']):
                    format_dict[col] = "{:.1f}"

            styler = styler.format(format_dict, na_rep="-")

            # 3. Style pour les ferrures
            if 'ferrure' in display_cols:
                def color_ferrure(val):
                    v = str(val).upper()
                    if 'D4' in v or 'ANTERIEURS_POSTERIEURS' in v: return 'color: #B91C1C; font-weight: bold;'
                    if 'DA' in v or 'DP' in v: return 'color: #B45309; font-weight: bold;'
                    return ''
                styler = styler.map(color_ferrure, subset=['ferrure'])

            st.dataframe(styler, use_container_width=True, hide_index=True)
        else:
            st.warning("Veuillez sélectionner au moins une colonne.")

else:
    st.info("Aucune donnée disponible. Importez un fichier CSV pour cette date.")