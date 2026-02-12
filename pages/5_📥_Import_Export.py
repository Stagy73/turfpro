import streamlit as st
import pandas as pd
import json
from utils import get_conn, clean_float, clean_text

st.set_page_config(layout="wide", page_title="Importation & Résultats")

# --- STYLE ---
st.markdown("""
<style>
    .main-title { font-weight: 900; font-size: 2.2rem; color: #1E293B; border-bottom: 4px solid #3A7BD5; padding-bottom:10px; }
    .status-box { padding: 20px; border-radius: 10px; background-color: #E2E8F0; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📥 Importation & Mise à jour Résultats</p>', unsafe_allow_html=True)

file = st.file_uploader("Charger le fichier CSV (Courses ou Résultats)", type=["csv"])

if file:
    try:
        df = pd.read_csv(file, sep=';', engine='python', on_bad_lines='skip')
        st.success(f"✅ Fichier chargé : {len(df)} lignes.")
        
        cols = df.columns.tolist()
        
        # --- CONFIGURATION DU MAPPING ---
        with st.expander("⚙️ Configuration des colonnes", expanded=True):
            c1, c2, c3 = st.columns(3)
            m_date = c1.selectbox("Date", cols, index=cols.index('date') if 'date' in cols else 0)
            m_hippo = c2.selectbox("Hippodrome", cols, index=cols.index('hippodrome') if 'hippodrome' in cols else 0)
            m_cheval = c3.selectbox("Cheval", cols, index=cols.index('Cheval') if 'Cheval' in cols else 0)
            
            c4, c5, c6 = st.columns(3)
            m_num = c4.selectbox("N° Cheval", cols, index=cols.index('Numero') if 'Numero' in cols else 0)
            m_course = c5.selectbox("Code Course (R1C1)", cols, index=cols.index('Course') if 'Course' in cols else 0)
            # Nouvelle colonne pour le résultat (souvent nommée 'Arrivee' ou 'Rang' dans les exports)
            m_rang = c6.selectbox("Colonne Résultat/Rang (Optionnel)", ["--- Aucun ---"] + cols, 
                                 index=(cols.index('Rang')+1) if 'Rang' in cols else 0)

        if st.button("🚀 Lancer l'importation / Mise à jour", type="primary", use_container_width=True):
            conn = get_conn()
            success_import = 0
            success_update = 0

            for _, row in df.iterrows():
                try:
                    val_num = int(row[m_num])
                    val_date = str(row[m_date])
                    val_course = str(row[m_course])
                    
                    # 1. Vérifier si le cheval existe déjà pour cette course
                    check = conn.execute(
                        "SELECT id FROM selections WHERE date=? AND course_num=? AND numero=?", 
                        (val_date, val_course, val_num)
                    ).fetchone()

                    if check and m_rang != "--- Aucun ---":
                        # MODE MISE À JOUR (Résultats)
                        rang_final = pd.to_numeric(row[m_rang], errors='coerce')
                        if not pd.isna(rang_final):
                            conn.execute(
                                "UPDATE selections SET classement = ? WHERE id = ?",
                                (int(rang_final), check[0])
                            )
                            success_update += 1
                    
                    elif not check:
                        # MODE NOUVEL IMPORT (Données du jour)
                        raw_dict = row.to_dict()
                        clean_dict = {str(k).replace(' ', '_'): v for k, v in raw_dict.items()}
                        full_row_json = json.dumps(clean_dict)
                        
                        conn.execute("""INSERT INTO selections 
                            (date, hippodrome, course_num, cheval, numero, cote, json_data) 
                            VALUES (?,?,?,?,?,?,?)""",
                            (val_date, clean_text(row[m_hippo]), val_course, 
                             clean_text(row[m_cheval]), val_num, clean_float(str(row.get('Cote', 0))), 
                             full_row_json))
                        success_import += 1
                except:
                    continue
            
            conn.commit()
            conn.close()
            st.success(f"✨ Terminé ! Imports : {success_import} | Résultats mis à jour : {success_update}")
            if success_update > 0: st.balloons()

    except Exception as e:
        st.error(f"Erreur : {e}")