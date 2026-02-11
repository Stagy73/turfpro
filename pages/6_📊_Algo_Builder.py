import streamlit as st
import pandas as pd
import numpy as np
import json
from utils import run_query, get_conn

st.set_page_config(layout="wide", page_title="Algo Builder")

st.markdown('<p style="font-weight:900; font-size:2.2rem; color:#1E293B; border-bottom:4px solid #3A7BD5;">🧪 Algo Builder - Stratégies</p>', unsafe_allow_html=True)

def save_algo(nom, formule):
    run_query("INSERT OR REPLACE INTO algos (nom, formule) VALUES (?, ?)", (nom, formule), commit=True)

def delete_algo(nom):
    run_query("DELETE FROM algos WHERE nom = ?", (nom,), commit=True)

date_today = st.date_input("Date du test", value=pd.Timestamp.now())
raw_data = run_query("SELECT * FROM selections WHERE date = ?", (str(date_today),))

algos_df = run_query("SELECT * FROM algos")
liste_algos = ["--- Nouveau ---"] + (algos_df['nom'].tolist() if not algos_df.empty else [])

col_side, col_main = st.columns([1, 2])

with col_side:
    selected = st.selectbox("Charger :", liste_algos)
    mode_affichage = st.radio("Mode d'affichage :", ["Standard (Simple)", "Duo (Couplé)"])

current_nom = ""
current_form = ""
if selected != "--- Nouveau ---":
    r = algos_df[algos_df['nom'] == selected].iloc[0]
    current_nom, current_form = r['nom'], r['formule']

with col_main:
    with st.container(border=True):
        nom_algo = st.text_input("Nom", value=current_nom)
        formule_raw = st.text_area("Formule", value=current_form, height=100)

        b1, b2, b3 = st.columns([1, 1, 2])
        if b1.button("💾 Sauver", use_container_width=True):
            save_algo(nom_algo, formule_raw)
            st.rerun()
        if b2.button("🗑️ Effacer", use_container_width=True) and selected != "--- Nouveau ---":
            delete_algo(selected)
            st.rerun()
        btn_run = b3.button("🚀 LANCER LE TEST", type="primary", use_container_width=True)

if btn_run and not raw_data.empty:
    try:
        data = []
        for _, r in raw_data.iterrows():
            d = json.loads(r['json_data']) if r['json_data'] else {}
            # NORMALISATION DES NOMS : espaces → _, points supprimés, tirets → _
            clean = {}
            for k, v in d.items():
                new_k = str(k).replace(' ', '_').replace('.', '').replace('-', '_').replace('é', 'e').replace('è', 'e')
                # Supprimer doubles underscores
                while '__' in new_k:
                    new_k = new_k.replace('__', '_')
                new_k = new_k.strip('_')
                clean[new_k] = v
            id_c = f"{r['hippodrome']}_{r['course_num']}".upper()
            clean.update({
                'Numero': r['numero'], 'Cheval': r['cheval'],
                'ID_C': id_c, 'hippodrome': r['hippodrome'], 'Cote': r['cote']
            })
            data.append(clean)
        df = pd.DataFrame(data)

        # Aussi normaliser les noms de colonnes du DataFrame
        rename_map = {}
        for col in df.columns:
            new_col = col.replace('.', '').replace('-', '_').replace('é', 'e').replace('è', 'e')
            while '__' in new_col:
                new_col = new_col.replace('__', '_')
            new_col = new_col.strip('_')
            if new_col != col:
                rename_map[col] = new_col
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        # Alias courants pour Borda
        if 'Borda_Borda_par_Defaut' in df.columns and 'Borda' not in df.columns:
            df['Borda'] = df['Borda_Borda_par_Defaut']

        # CONVERSION NUMÉRIQUE — TOUTES les colonnes
        skip_cols = {'Cheval', 'hippodrome', 'ID_C', 'Musique', 'Driver', 'Entraineur',
                     'ferrure', 'Sexe', 'avis_entraineur', 'Classe_Groupe',
                     'supplemente', 'ExFav', 'inTQQ', 'Note_IA', 'code_course',
                     'Cle_Chrono', 'heure', 'date', 'discipline'}

        for col in df.columns:
            if col in skip_cols:
                continue
            converted = pd.to_numeric(
                df[col].astype(str).str.replace(',', '.').str.strip(),
                errors='coerce'
            )
            if converted.notna().sum() > len(df) * 0.3:
                df[col] = converted.fillna(0.0)
                if "Taux" in col and df[col].max() <= 1.1:
                    df[col] = df[col] * 100.0

        # RANKS AUTO par course
        rank_sources = [
            'ELO_Cheval', 'ELO_Jockey', 'ELO_Entraineur', 'ELO_Proprio', 'ELO_Eleveur',
            'IA_Gagnant', 'IA_Couple', 'IA_Trio', 'IA_Multi', 'IA_Quinte',
            'Note_IA_Decimale', 'Borda', 'Synergie_JCh', 'Cote_BZH',
            'Taux_Victoire', 'Taux_Place', 'Turf_Points', 'TPch_90',
            'Moy_TPch_365', 'Moy_TPch_90', 'Moy_TPJ_365', 'Moy_TPJ_90',
            'Sigma_Horse', 'IMDC',
        ]
        if 'Cote' in df.columns:
            df['Cote_Rank'] = df.groupby('ID_C')['Cote'].rank(ascending=True, method='min')

        for c in rank_sources:
            rank_col = f"{c}_Rank"
            if c in df.columns and rank_col not in df.columns:
                df[rank_col] = df.groupby('ID_C')[c].rank(ascending=False, method='min')

        # MOTEUR DE CALCUL
        f_py = formule_raw.replace('?', ' if ').replace(':', ' else ')
        f_py = f_py.replace('""', '0').replace("''", "0")

        def calculate(row):
            ctx = {}
            for k, v in row.to_dict().items():
                if isinstance(v, (int, float, np.integer, np.floating)):
                    ctx[k] = float(v)
                else:
                    ctx[k] = v
            ctx.update({'log': np.log, 'sqrt': np.sqrt, 'abs': np.abs, 'max': max, 'min': min})
            try:
                return float(eval(f_py, {"__builtins__": {}}, ctx))
            except Exception as ex:
                return 0.0

        df['SCORE'] = df.apply(calculate, axis=1)

        # DEBUG
        with st.expander("🔧 Debug — Variables disponibles"):
            num_cols = sorted([c for c in df.columns if df[c].dtype in ['float64', 'int64', 'float32']])
            rank_cols = sorted([c for c in df.columns if c.endswith('_Rank')])
            st.markdown(f"**{len(num_cols)} variables numériques** : `{'`, `'.join(num_cols)}`")
            st.markdown(f"**{len(rank_cols)} Ranks** : `{'`, `'.join(rank_cols)}`")
            if df['SCORE'].max() > 0:
                top = df.nlargest(1, 'SCORE').iloc[0]
                st.markdown(f"**Top** : {top['Cheval']} — Score **{top['SCORE']:.2f}**")
                for sv in ['Cote','ELO_Cheval','Note_IA_Decimale','IA_Gagnant','Borda',
                           'Synergie_JCh','Moy_TPch_90','Note_IA_Decimale_Rank','IA_Gagnant_Rank','Cote_Rank']:
                    if sv in df.columns: st.text(f"  {sv} = {top.get(sv, 'N/A')}")
            else:
                st.error("Score max = 0 ! Voici un échantillon pour debug :")
                sample_row = df.iloc[0]
                for sv in ['Cote','ELO_Cheval','Note_IA_Decimale','IA_Gagnant','Borda',
                           'Synergie_JCh','Moy_TPch_90','Moy_TPch_365']:
                    val = sample_row.get(sv, '❌ ABSENT')
                    st.text(f"  {sv} = {val} (type: {type(val).__name__})")

        st.divider()

        # AFFICHAGE
        if mode_affichage == "Duo (Couplé)":
            st.subheader("🏁 Couplés (Top 2 par course)")
            df_res = df[df['SCORE'] > 0].sort_values(['ID_C', 'SCORE'], ascending=[True, False])
            for course_id in df_res['ID_C'].unique():
                duo = df_res[df_res['ID_C'] == course_id].head(2)
                if len(duo) >= 2:
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 2])
                        c1.write(f"**📍 {course_id}**")
                        nums = duo['Numero'].tolist()
                        scores = duo['SCORE'].tolist()
                        chevaux = duo['Cheval'].tolist()
                        c2.markdown(f"### 🏇 {int(nums[0])} - {int(nums[1])}")
                        c2.caption(f"{chevaux[0]} ({scores[0]:.1f}) + {chevaux[1]} ({scores[1]:.1f})")
        else:
            df_results = df[df['SCORE'] > 0].sort_values(['ID_C', 'SCORE'], ascending=[True, False])
            if not df_results.empty:
                pronos = df_results[df_results['SCORE'] >= 19]
                if not pronos.empty:
                    st.subheader("🎯 Sélection Premium (Score >= 19)")
                    st.table(pronos[['hippodrome', 'ID_C', 'Numero', 'Cheval', 'SCORE']])

                st.subheader("📊 Toutes les courses")
                for h in df_results['hippodrome'].unique():
                    with st.expander(f"🏟️ {h}", expanded=True):
                        cols_show = ['ID_C', 'Numero', 'Cheval', 'SCORE', 'Cote']
                        for extra in ['Note_IA_Decimale', 'IA_Gagnant', 'ELO_Cheval', 'Borda']:
                            if extra in df_results.columns: cols_show.append(extra)
                        avail = [c for c in cols_show if c in df_results.columns]
                        st.dataframe(
                            df_results[df_results['hippodrome'] == h][avail],
                            use_container_width=True, hide_index=True
                        )
            else:
                st.warning("Tous les scores sont à 0.")

    except Exception as e:
        st.error(f"Erreur : {e}")
        import traceback
        st.code(traceback.format_exc())

elif btn_run:
    st.warning("Aucune donnée pour cette date.")