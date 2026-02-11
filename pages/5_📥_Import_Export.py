import streamlit as st
import pandas as pd
from utils import get_conn, get_course_label, clean_float

st.set_page_config(layout="wide")
st.title("📥 Importation des données")

file = st.file_uploader("Charger le fichier export_turfbzh", type=["csv"])

if file:
    try:
        # engine='python' + on_bad_lines='skip' pour ignorer la ligne 8 corrompue
        df = pd.read_csv(file, sep=';', engine='python', on_bad_lines='skip')
        st.success(f"Fichier chargé : {len(df)} lignes valides.")
        
        cols = df.columns.tolist()
        c1, c2, c3 = st.columns(3)
        m_date = c1.selectbox("Date", cols, index=cols.index('date') if 'date' in cols else 0)
        m_hippo = c2.selectbox("Hippodrome", cols, index=cols.index('hippodrome') if 'hippodrome' in cols else 0)
        m_cheval = c3.selectbox("Cheval", cols, index=cols.index('Cheval') if 'Cheval' in cols else 0)
        
        c4, c5, c6 = st.columns(3)
        m_num = c4.selectbox("N° Cheval", cols, index=cols.index('Numero') if 'Numero' in cols else 0)
        m_cote = c5.selectbox("Cote", cols, index=cols.index('Cote') if 'Cote' in cols else 0)
        m_course = c6.selectbox("Code Course", cols, index=cols.index('Course') if 'Course' in cols else 0)

        if st.button("🚀 Lancer l'importation du programme", type="primary"):
            conn = get_conn()
            for _, row in df.iterrows():
                try:
                    conn.execute("""INSERT INTO selections 
                        (date, hippodrome, course_num, cheval, numero, cote, musique, corde, ferreur) 
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                        (str(row[m_date]), str(row[m_hippo]), get_course_label(row[m_course]), 
                         str(row[m_cheval]), int(row[m_num]), clean_float(row[m_cote]),
                         str(row.get('Musique', '')), str(row.get('Place_Corde', '')), str(row.get('ferrure', ''))))
                except: continue
            conn.commit()
            st.success("Programme importé ! Allez dans 'Sélections' pour le voir.")
    except Exception as e:
        st.error(f"Erreur : {e}")