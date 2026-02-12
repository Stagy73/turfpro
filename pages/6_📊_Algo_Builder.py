import streamlit as st
import pandas as pd
import numpy as np
import json
from utils import run_query, get_conn
# Importation des fonctions de calcul depuis votre nouveau fichier de stratégie
from strategies import calculer_score_couple, detecter_trio 

st.set_page_config(layout="wide", page_title="Algo Builder")

st.markdown('<p style="font-weight:900; font-size:2.2rem; color:#1E293B; border-bottom:4px solid #3A7BD5;">🧪 Algo Builder - Stratégies & Combinés</p>', unsafe_allow_html=True)

def save_algo(nom, formule):
    run_query("INSERT OR REPLACE INTO algos (nom, formule) VALUES (?, ?)", (nom, formule), commit=True)

def delete_algo(nom):
    run_query("DELETE FROM algos WHERE nom = ?", (nom,), commit=True)

# --- FILTRES LATERAUX ---
date_today = st.date_input("Date du test", value=pd.Timestamp.now())
raw_data = run_query("SELECT * FROM selections WHERE date = ?", (str(date_today),))

algos_df = run_query("SELECT * FROM algos")
liste_algos = ["--- Nouveau ---"] + (algos_df['nom'].tolist() if not algos_df.empty else [])

col_side, col_main = st.columns([1, 2])

with col_side:
    selected = st.selectbox("Charger un algorithme :", liste_algos)
    mode_affichage = st.radio("Mode d'affichage :", ["Standard (Simple)", "Duo (Combiné)"])

current_nom = ""
current_form = ""
if selected != "--- Nouveau ---":
    r = algos_df[algos_df['nom'] == selected].iloc[0]
    current_nom, current_form = r['nom'], r['formule']

with col_main:
    with st.container(border=True):
        nom_algo = st.text_input("Nom de l'algorithme", value=current_nom)
        formule_raw = st.text_area("Formule (Python syntax)", value=current_form, height=100)

        b1, b2, b3 = st.columns([1, 1, 2])
        if b1.button("💾 Sauver", use_container_width=True):
            save_algo(nom_algo, formule_raw)
            st.rerun()
        if b2.button("🗑️ Effacer", use_container_width=True) and selected != "--- Nouveau ---":
            delete_algo(selected)
            st.rerun()
        btn_run = b3.button("🚀 LANCER L'ANALYSE", type="primary", use_container_width=True)

# --- MOTEUR DE TRAITEMENT ---
if btn_run and not raw_data.empty:
    try:
        data = []
        for _, r in raw_data.iterrows():
            d = json.loads(r['json_data']) if r['json_data'] else {}
            # Normalisation des clés JSON pour correspondre aux variables attendues
            clean = {}
            for k, v in d.items():
                new_k = str(k).replace(' ', '_').replace('.', '').replace('-', '_').replace('é', 'e').replace('è', 'e')
                while '__' in new_k: new_k = new_k.replace('__', '_')
                new_k = new_k.strip('_')
                clean[new_k] = v
            
            id_c = f"{r['hippodrome']}_{r['course_num']}".upper()
            clean.update({
                'Numero': r['numero'], 'Cheval': r['cheval'],
                'ID_C': id_c, 'hippodrome': r['hippodrome'], 'Cote': r['cote']
            })
            data.append(clean)
        
        df = pd.DataFrame(data)

        # Normalisation des colonnes du DataFrame
        rename_map = {col: col.replace('.', '').replace('-', '_').replace('é', 'e').replace('è', 'e').strip('_') for col in df.columns}
        df.rename(columns=rename_map, inplace=True)

        if 'Borda_Borda_par_Defaut' in df.columns and 'Borda' not in df.columns:
            df['Borda'] = df['Borda_Borda_par_Defaut']

        # Conversion numérique propre
        skip_cols = {'Cheval', 'hippodrome', 'ID_C', 'Musique', 'Driver', 'Entraineur', 'ferrure', 'Sexe', 'date', 'discipline'}
        for col in df.columns:
            if col in skip_cols: continue
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.strip(), errors='coerce').fillna(0.0)

        # Génération automatique des Ranks (1 = Meilleur)
        rank_sources = [
            'ELO_Cheval', 'ELO_Jockey', 'ELO_Entraineur', 'IA_Gagnant', 'IA_Trio', 
            'Note_IA_Decimale', 'Borda', 'Synergie_JCh', 'Cote', 'Turf_Points'
        ]
        for c in rank_sources:
            rank_col = f"{c}_Rank"
            if c in df.columns:
                # Pour la Cote, le plus petit est le meilleur (Rank 1). Pour les points/ELO, le plus grand est le meilleur.
                asc = True if c == 'Cote' else False
                df[rank_col] = df.groupby('ID_C')[c].rank(ascending=asc, method='min')

        # Calcul du score personnalisé via la formule saisie
        f_py = formule_raw.replace('?', ' if ').replace(':', ' else ').replace('""', '0')
        def calculate(row):
            ctx = row.to_dict()
            ctx.update({'log': np.log, 'sqrt': np.sqrt, 'abs': np.abs, 'max': max, 'min': min})
            try: return float(eval(f_py, {"__builtins__": {}}, ctx))
            except: return 0.0

        df['SCORE'] = df.apply(calculate, axis=1)

        st.divider()

        # --- AFFICHAGE DES RÉSULTATS ---
        if mode_affichage == "Duo (Combiné)":
            st.subheader("🏁 Pronostics Combinés (Bases / Outsiders / Folies)")
            for course_id in df['ID_C'].unique():
                df_course = df[df['ID_C'] == course_id]
                
                # Appel de la logique avancée de strategies.py
                bases, outsiders, folie = detecter_trio(df_course)
                
                if not bases.empty:
                    with st.container(border=True):
                        st.write(f"**📍 Course : {course_id}**")
                        c1, c2, c3 = st.columns(3)
                        
                        with c1:
                            nums = bases['Numero'].astype(int).astype(str).tolist()
                            st.success(f"**💎 BASES**\n### {' - '.join(nums)}")
                        
                        with c2:
                            nums = outsiders['Numero'].astype(int).astype(str).tolist()
                            st.warning(f"**🏇 ASSOCIÉS**\n### {' - '.join(nums)}")
                        
                        with c3:
                            if not folie.empty:
                                num = str(int(folie['Numero'].iloc[0]))
                                cote = folie['Cote'].iloc[0]
                                st.error(f"**🔥 COUP DE FOLIE**\n### {num} (Cote: {cote})")
                            else:
                                st.write("*Aucun coup de folie*")
        else:
            # Mode Standard : Liste simple triée par score
            df_results = df[df['SCORE'] > 0].sort_values(['ID_C', 'SCORE'], ascending=[True, False])
            for h in df_results['hippodrome'].unique():
                with st.expander(f"🏟️ {h}", expanded=True):
                    st.dataframe(df_results[df_results['hippodrome'] == h], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erreur technique : {e}")
        st.code(importlib.import_traceback.format_exc())

elif btn_run:
    st.warning("Aucune donnée disponible pour cette date.")