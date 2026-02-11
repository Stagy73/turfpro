import streamlit as st
import pandas as pd
from utils import get_conn

st.set_page_config(layout="wide")

st.markdown("""
<style>
    .horse-row {
        background: white; border: 1px solid #E2E8F0; border-radius: 8px;
        padding: 15px 25px; margin-bottom: 10px; display: grid;
        grid-template-columns: 60px 250px 100px 220px 80px 150px;
        align-items: center; gap: 30px;
    }
    .horse-num { color: #1E40AF; font-weight: 900; font-size: 1.4rem; text-align: center; }
    .badge-cote { background: #F1F5F9; color: black; font-weight: 900; text-align: center; border-radius: 6px; padding: 5px; border: 1px solid #CBD5E1; }
    /* Styles pour les ferrures */
    .fer-d4 { color: #DC2626; font-weight: 900; } /* Rouge pour D4 */
    .fer-light { color: #EA580C; font-weight: 700; } /* Orange pour DA/DP */
    .fer-normal { color: #64748B; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Programme des Sélections")

df_s = pd.read_sql("SELECT * FROM selections ORDER BY date DESC, hippodrome, course_num, numero", get_conn())

if not df_s.empty:
    for date_val, df_date in df_s.groupby('date'):
        st.markdown(f"## 📅 {date_val}")
        for hippo, df_hippo in df_date.groupby('hippodrome'):
            with st.expander(f"🏟️ RÉUNION : {hippo.upper()}", expanded=True):
                courses = sorted(df_hippo['course_num'].unique())
                tabs = st.tabs([f"Course {c}" for c in courses])
                for i, c_id in enumerate(courses):
                    with tabs[i]:
                        df_c = df_hippo[df_hippo['course_num'] == c_id]
                        
                        for _, h in df_c.iterrows():
                            # Logique de couleur pour les ferrures
                            fer_raw = str(h['ferreur']).upper()
                            fer_class = "fer-normal"
                            if "DEFERRE_ANTERIEURS_POSTERIEURS" in fer_raw or "D4" in fer_raw:
                                fer_display = "D4 🔴"
                                fer_class = "fer-d4"
                            elif "DEFERRE" in fer_raw:
                                fer_display = "DA/DP 🟠"
                                fer_class = "fer-light"
                            else:
                                fer_display = fer_raw if fer_raw not in ["0", "NAN", "NONE", ""] else "-"

                            corde = h['corde'] if h['corde'] and str(h['corde']).strip() not in ["0", "nan", "None", ""] else "-"
                            
                            st.markdown(f"""
                            <div class="horse-row">
                                <div class="horse-num">{h['numero']}</div>
                                <div style="font-weight:800; color:black;">{h['cheval']}</div>
                                <div class="badge-cote">{h['cote']:.1f}</div>
                                <div style="font-family:monospace; color:#92400E; background:#FEF3C7; padding:4px 10px; border-radius:4px; text-align:center;">{h['musique']}</div>
                                <div style="text-align:center; font-weight:bold; color:black;">{corde}</div>
                                <div class=" {fer_class} " style="text-align:center;">{fer_display}</div>
                            </div>
                            """, unsafe_allow_html=True)
else:
    st.info("Aucun programme importé.")