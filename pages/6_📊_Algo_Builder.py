import streamlit as st
import pandas as pd
import numpy as np
from utils import get_conn, run_query, clean_text

st.set_page_config(layout="wide")

# --- STYLE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;900&display=swap');
    .stApp { background-color: #F8FAFC; color: #000; font-family: 'Outfit', sans-serif; }
    .main-title { font-weight: 900; font-size: 2.5rem; color: #000; border-bottom: 4px solid #3A7BD5; padding-bottom:10px; }
    .card { background: white; padding: 20px; border-radius: 10px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🧪 Algo Builder & Stratégies</p>', unsafe_allow_html=True)

# --- INITIALISATION DE LA TABLE DES FORMULES ---
with get_conn() as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS algos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nom TEXT UNIQUE, 
        formule TEXT, 
        description TEXT)""")
    conn.commit()

# --- CHARGEMENT DES DONNÉES DU JOUR ---
date_today = st.date_input("Date du test", value=pd.Timestamp.now())
df = run_query("SELECT * FROM selections WHERE date = ?", (str(date_today),))

# --- INTERFACE ---
col_sidebar, col_main = st.columns([1, 2])

with col_sidebar:
    st.subheader("📚 Ma Bibliothèque")
    
    # Liste des algos sauvés
    algos_df = run_query("SELECT * FROM algos")
    
    if not algos_df.empty:
        selected_algo_nom = st.selectbox("Charger un Algo :", ["--- Nouveau ---"] + algos_df['nom'].tolist())
    else:
        selected_algo_nom = "--- Nouveau ---"
    
    st.divider()
    st.info("📊 **Aide Mémoire**\n- `log()` = Logarithme (pour lisser)\n- `sqrt()` = Racine carrée\n- `abs()` = Valeur absolue\n- `* / + -` = Opérateurs")

with col_main:
    # Récupération des données si un algo est sélectionné
    current_nom = ""
    current_formule = ""
    current_desc = ""
    
    if selected_algo_nom != "--- Nouveau ---":
        row = algos_df[algos_df['nom'] == selected_algo_nom].iloc[0]
        current_nom = row['nom']
        current_formule = row['formule']
        current_desc = row['description']

    with st.container(border=True):
        st.subheader("🛠 Édition de l'Algo")
        nom_algo = st.text_input("Nom de la stratégie", value=current_nom)
        formule_algo = st.text_area("Formule (ex: (IA_GAGNANT * 2) / log(COTE+1))", value=current_formule)
        desc_algo = st.text_area("À quoi sert cette formule ? (Explication)", value=current_desc)
        
        c1, c2, c3 = st.columns(3)
        if c1.button("💾 Sauvegarder / Modifier", type="primary", use_container_width=True):
            run_query("INSERT OR REPLACE INTO algos (nom, formule, description) VALUES (?, ?, ?)", 
                      (nom_algo, formule_algo, desc_algo), commit=True)
            st.success("Stratégie enregistrée !")
            st.rerun()
            
        if c2.button("🗑 Supprimer", use_container_width=True):
            run_query("DELETE FROM algos WHERE nom = ?", (nom_algo,), commit=True)
            st.warning("Algo supprimé.")
            st.rerun()

        if c3.button("🚀 Tester l'Algo", use_container_width=True):
            if df is not None and not df.empty:
                try:
                    # Préparation des données (Renommage pour compatibilité)
                    df_calc = df.copy()
                    df_calc = df_calc.rename(columns={'cote': 'COTE', 'numero': 'NUM'})
                    
                    # Simulation de colonnes si absentes pour éviter les crashs
                    for col in ['IA_GAGNANT', 'SIGMA', 'TX_VICTOIRE', 'ELO_CHEVAL']:
                        if col not in df_calc.columns:
                            df_calc[col] = np.random.uniform(1, 10, len(df_calc))
                    
                    # CALCUL
                    df_calc['SCORE'] = df_calc.eval(formule_algo.replace('ln(', 'log('))
                    df_calc = df_calc.sort_values('SCORE', ascending=False)
                    
                    st.divider()
                    st.subheader(f"🏆 Résultats : {nom_algo}")
                    st.info(f"💡 **Objectif :** {desc_algo}")
                    
                    for hippo in df_calc['hippodrome'].unique():
                        st.write(f"**🏟️ {hippo}**")
                        view = df_calc[df_calc['hippodrome'] == hippo]
                        st.dataframe(view[['course_num', 'NUM', 'cheval', 'COTE', 'SCORE']].style.highlight_max(axis=0, subset=['SCORE'], color='#D1FAE5'), use_container_width=True)
                except Exception as e:
                    st.error(f"Erreur dans la formule : {e}")
            else:
                st.warning("Importez des données pour tester.")