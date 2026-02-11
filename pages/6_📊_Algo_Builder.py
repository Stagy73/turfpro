import streamlit as st
import pandas as pd
import numpy as np
import json
from utils import get_conn, run_query

st.set_page_config(layout="wide", page_title="Algo Builder Pro")

# --- STYLE CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;900&display=swap');
    .stApp { background-color: #F8FAFC; color: #000; font-family: 'Outfit', sans-serif; }
    .main-title { font-weight: 900; font-size: 2.5rem; color: #1E293B; border-bottom: 4px solid #3A7BD5; padding-bottom:10px; }
    .stTextArea textarea { font-family: 'Courier New', monospace; background-color: #F1F5F9; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🧪 Algo Builder & Stratégies</p>', unsafe_allow_html=True)

# --- INITIALISATION SQL ---
with get_conn() as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS algos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nom TEXT UNIQUE, 
        formule TEXT, 
        description TEXT)""")
    conn.commit()

# --- CHARGEMENT DES DONNÉES ---
date_today = st.date_input("Choisir une date pour le test", value=pd.Timestamp.now())
raw_data = run_query("SELECT * FROM selections WHERE date = ?", (str(date_today),))

# --- LAYOUT ---
col_sidebar, col_main = st.columns([1, 2])

with col_sidebar:
    st.subheader("📚 Ma Bibliothèque")
    algos_df = run_query("SELECT * FROM algos")
    
    selected_algo_nom = st.selectbox("Charger un Algo :", ["--- Nouveau ---"] + algos_df['nom'].tolist()) if not (algos_df is None or algos_df.empty) else "--- Nouveau ---"
    
    st.divider()
    st.info("📊 **Aide Mémoire**\n- `log(x)` : Logarithme\n- `sqrt(x)` : Racine carrée\n- Noms : IA_Gagnant, Cote, ELO_Cheval")

with col_main:
    current_nom, current_formule, current_desc = "", "", ""
    
    if selected_algo_nom != "--- Nouveau ---":
        row_algo = algos_df[algos_df['nom'] == selected_algo_nom].iloc[0]
        current_nom, current_formule, current_desc = row_algo['nom'], row_algo['formule'], row_algo['description']

    with st.container(border=True):
        st.subheader("🛠 Édition de l'Algo")
        nom_algo = st.text_input("Nom de la stratégie", value=current_nom)
        formule_algo = st.text_area("Formule mathématique", value=current_formule, placeholder="Ex: (IA_Gagnant * 100) / log(Cote + 1)")
        desc_algo = st.text_area("Explication", value=current_desc)
        
        c1, c2, c3 = st.columns(3)
        if c1.button("💾 Sauvegarder", type="primary", use_container_width=True):
            run_query("INSERT OR REPLACE INTO algos (nom, formule, description) VALUES (?, ?, ?)", (nom_algo, formule_algo, desc_algo), commit=True)
            st.rerun()
            
        if c2.button("🗑 Supprimer", use_container_width=True):
            run_query("DELETE FROM algos WHERE nom = ?", (nom_algo,), commit=True)
            st.rerun()

        if c3.button("🚀 Tester l'Algo", use_container_width=True):
            if not formule_algo.strip():
                st.error("Saisissez une formule.")
            elif raw_data is not None and not raw_data.empty:
                try:
                    # 1. Extraction JSON
                    list_dicts = []
                    for _, r in raw_data.iterrows():
                        d = json.loads(r['json_data']) if r['json_data'] else {}
                        d.update({
                            'Cote': r['cote'], 
                            'Numero': r['numero'], 
                            'Cheval': r['cheval'], 
                            'Course': r['course_num'], 
                            'hippodrome': r['hippodrome']
                        })
                        list_dicts.append(d)
                    
                    df_test = pd.DataFrame(list_dicts)

                    # 2. NETTOYAGE (Version SANS errors='ignore' pour supprimer le FutureWarning)
                    for col in df_test.columns:
                        if df_test[col].dtype == 'object':
                            # Nettoyage des virgules
                            df_test[col] = df_test[col].astype(str).str.replace(',', '.')
                            # Tentative de conversion propre
                            try:
                                df_test[col] = pd.to_numeric(df_test[col])
                            except (ValueError, TypeError):
                                continue # Si c'est du texte (ex: Cheval), on laisse tel quel sans erreur

                    # 3. MOTEUR DE CALCUL
                    def eval_algo(row, code):
                        context = row.to_dict()
                        context.update({'log': np.log, 'sqrt': np.sqrt, 'abs': np.abs})
                        # On supporte ln() et log()
                        safe_code = code.replace('ln(', 'log(')
                        return eval(safe_code, {"__builtins__": {}}, context)

                    df_test['SCORE'] = df_test.apply(lambda r: eval_algo(r, formule_algo), axis=1)
                    df_res = df_test.dropna(subset=['SCORE']).sort_values(['Course', 'SCORE'], ascending=[True, False])
                    
                    st.divider()
                    st.subheader(f"🏆 Résultats : {nom_algo}")
                    
                    for hippo in df_res['hippodrome'].unique():
                        st.markdown(f"### 🏟️ {hippo}")
                        view = df_res[df_res['hippodrome'] == hippo]
                        cols = ['Course', 'Numero', 'Cheval', 'Cote', 'SCORE']
                        if 'IA_Gagnant' in view.columns: cols.insert(4, 'IA_Gagnant')
                        
                        st.dataframe(
                            view[cols].style.background_gradient(subset=['SCORE'], cmap='YlGnBu').format({'SCORE': '{:.2f}'}), 
                            use_container_width=True, 
                            hide_index=True
                        )
                except Exception as e:
                    st.error(f"Erreur : {e}")
            else:
                st.warning("Aucune donnée pour cette date.")