import streamlit as st
import pandas as pd
import json
from utils import get_conn, get_course_label, clean_float, clean_text

st.set_page_config(layout="wide", page_title="Importation Totale")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;900&display=swap');
    .stApp { background-color: #F8FAFC; color: #000; font-family: 'Outfit', sans-serif; }
    .main-title { font-weight: 900; font-size: 2.2rem; color: #000; border-bottom: 4px solid #3A7BD5; padding-bottom:10px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📥 Importation Totale & Maintenance</p>', unsafe_allow_html=True)

# --- ZONE D'IMPORTATION ---
file = st.file_uploader("Charger le fichier export_turfbzh (CSV)", type=["csv"])

if file:
    try:
        # Lecture avec séparateur point-virgule (détecté dans ton CSV)
        df = pd.read_csv(file, sep=';', engine='python', on_bad_lines='skip')
        st.success(f"✅ Fichier chargé : {len(df)} lignes détectées.")
        
        cols = df.columns.tolist()
        st.subheader("⚙️ Configuration du mapping")
        
        # On définit les index par défaut en cherchant les noms exacts du CSV
        c1, c2, c3 = st.columns(3)
        idx_date = cols.index('date') if 'date' in cols else 0
        idx_hippo = cols.index('hippodrome') if 'hippodrome' in cols else 0
        idx_cheval = cols.index('Cheval') if 'Cheval' in cols else 0
        
        m_date = c1.selectbox("Colonne Date", cols, index=idx_date)
        m_hippo = c2.selectbox("Colonne Hippodrome", cols, index=idx_hippo)
        m_cheval = c3.selectbox("Colonne Cheval", cols, index=idx_cheval)
        
        c4, c5, c6 = st.columns(3)
        idx_num = cols.index('Numero') if 'Numero' in cols else 0
        idx_cote = cols.index('Cote') if 'Cote' in cols else 0
        idx_course = cols.index('Course') if 'Course' in cols else 0
        
        m_num = c4.selectbox("Colonne N° Cheval", cols, index=idx_num)
        m_cote = c5.selectbox("Colonne Cote", cols, index=idx_cote)
        m_course = c6.selectbox("Colonne Code Course", cols, index=idx_course)

        if st.button("🚀 Lancer l'importation complète", type="primary", use_container_width=True):
            conn = get_conn()
            # Nettoyage des anciennes données pour éviter les doublons sur les dates importées
            dates_a_effacer = df[m_date].unique()
            for d in dates_a_effacer:
                conn.execute("DELETE FROM selections WHERE date = ?", (str(d),))

            success_count = 0
            for _, row in df.iterrows():
                try:
                    # Préparation du dictionnaire JSON complet
                    # On nettoie les noms de colonnes (espaces -> underscores) pour l'Algo Builder
                    raw_dict = row.to_dict()
                    clean_dict = {str(k).replace(' ', '_'): v for k, v in raw_dict.items()}
                    full_row_json = json.dumps(clean_dict)
                    
                    # Nettoyage des valeurs numériques
                    val_cote = clean_float(str(row[m_cote]).replace(',', '.'))
                    val_num = int(row[m_num])
                    
                    conn.execute("""INSERT INTO selections 
                        (date, hippodrome, course_num, cheval, numero, cote, musique, corde, ferreur, json_data) 
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (str(row[m_date]), 
                         clean_text(row[m_hippo]), 
                         str(row[m_course]), # On garde le format R1C1
                         clean_text(row[m_cheval]), 
                         val_num, 
                         val_cote,
                         str(row.get('Musique', '')), 
                         str(row.get('Place_Corde', '')), 
                         str(row.get('ferrure', '')), 
                         full_row_json))
                    success_count += 1
                except Exception as e:
                    continue
            
            conn.commit()
            conn.close()
            st.balloons()
            st.success(f"✅ Importation terminée : {success_count} chevaux enregistrés avec TOUTES les statistiques (IA, ELO, Taux).")
    except Exception as e:
        st.error(f"Erreur lors de l'importation : {e}")

st.divider()

# --- ZONE DE MAINTENANCE ---
st.subheader("🛠️ Maintenance de la Base")
col_m1, col_m2 = st.columns(2)

with col_m1:
    if st.button("🔧 Réparer les cotes à zéro", use_container_width=True):
        try:
            conn = get_conn()
            conn.execute("UPDATE paris SET cote = 1.0 WHERE cote = 0 OR cote IS NULL")
            conn.commit()
            conn.close()
            st.success("✅ Cotes réparées !")
        except Exception as e:
            st.error(f"Erreur : {e}")

with col_m2:
    if st.button("🔥 Vider toutes les Sélections", use_container_width=True):
        try:
            conn = get_conn()
            conn.execute("DELETE FROM selections")
            conn.commit()
            conn.close()
            st.success("✅ Table vidée.")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")