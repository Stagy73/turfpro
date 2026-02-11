import streamlit as st
import pandas as pd
import json
from utils import get_conn, get_course_label, clean_float, clean_text

st.set_page_config(layout="wide")

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
        df = pd.read_csv(file, sep=';', engine='python', on_bad_lines='skip')
        st.success(f"✅ Fichier chargé : {len(df)} lignes valides.")
        
        cols = df.columns.tolist()
        st.subheader("⚙️ Configuration du mapping")
        c1, c2, c3 = st.columns(3)
        m_date = c1.selectbox("Date", cols, index=cols.index('date') if 'date' in cols else 0)
        m_hippo = c2.selectbox("Hippodrome", cols, index=cols.index('hippodrome') if 'hippodrome' in cols else 0)
        m_cheval = c3.selectbox("Cheval", cols, index=cols.index('Cheval') if 'Cheval' in cols else 0)
        
        c4, c5, c6 = st.columns(3)
        m_num = c4.selectbox("N° Cheval", cols, index=cols.index('Numero') if 'Numero' in cols else 0)
        m_cote = c5.selectbox("Cote", cols, index=cols.index('Cote') if 'Cote' in cols else 0)
        m_course = c6.selectbox("Code Course", cols, index=cols.index('Course') if 'Course' in cols else 0)

        if st.button("🚀 Lancer l'importation complète", type="primary", use_container_width=True):
            conn = get_conn()
            # Supprimer les anciennes sélections pour les dates du fichier
            dates_a_effacer = df[m_date].unique()
            for d in dates_a_effacer:
                conn.execute("DELETE FROM selections WHERE date = ?", (str(d),))

            success_count = 0
            for _, row in df.iterrows():
                try:
                    # On transforme toute la ligne en dictionnaire puis en JSON
                    full_row_json = json.dumps(row.to_dict())
                    
                    conn.execute("""INSERT INTO selections 
                        (date, hippodrome, course_num, cheval, numero, cote, musique, corde, ferreur, json_data) 
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (str(row[m_date]), clean_text(row[m_hippo]), get_course_label(row[m_course]), 
                         clean_text(row[m_cheval]), int(row[m_num]), clean_float(row[m_cote]),
                         str(row.get('Musique', '')), str(row.get('Place_Corde', '')), 
                         str(row.get('ferrure', '')), full_row_json))
                    success_count += 1
                except: continue
            conn.commit()
            conn.close()
            st.balloons()
            st.success(f"Importation terminée : {success_count} chevaux enregistrés avec toutes leurs colonnes.")
    except Exception as e:
        st.error(f"Erreur lors de l'importation : {e}")

st.divider()

# --- ZONE DE MAINTENANCE (VIDER / RÉPARER) ---
st.subheader("🛠️ Maintenance de la Base")
col_m1, col_m2 = st.columns(2)

with col_m1:
    st.info("🔄 **Correction Backtest**")
    if st.button("🔧 Réparer les cotes à zéro", use_container_width=True):
        try:
            conn = get_conn()
            conn.execute("UPDATE paris SET cote = 1.0 WHERE cote = 0 OR cote IS NULL")
            conn.commit()
            conn.close()
            st.success("✅ Cotes réparées dans l'historique !")
        except Exception as e:
            st.error(f"Erreur : {e}")

with col_m2:
    st.warning("⚠️ **Zone de Nettoyage**")
    if st.button("🔥 Vider toutes les Sélections (Programme)", use_container_width=True):
        try:
            conn = get_conn()
            conn.execute("DELETE FROM selections")
            conn.commit()
            conn.close()
            st.success("✅ La table des sélections est maintenant vide.")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")