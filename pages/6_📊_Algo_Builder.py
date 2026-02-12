import streamlit as st
import pandas as pd
import numpy as np
import json
import re
from utils import run_query, get_conn
from strategies import calculer_score_couple, detecter_trio 

st.set_page_config(layout="wide", page_title="Algo Builder")

st.markdown('<p style="font-weight:900; font-size:2.2rem; color:#1E293B; border-bottom:4px solid #3A7BD5;">🧪 Algo Builder - Stratégies & Backtest</p>', unsafe_allow_html=True)

# --- FONCTIONS BDD ---
def save_algo(nom, formule):
    run_query("INSERT OR REPLACE INTO algos (nom, formule) VALUES (?, ?)", (nom, formule), commit=True)

def delete_algo(nom):
    run_query("DELETE FROM algos WHERE nom = ?", (nom,), commit=True)

def parse_classement(val):
    if val is None:
        return 0
    try:
        if pd.isna(val):
            return 0
    except (TypeError, ValueError):
        pass
    s = str(val).strip().upper()
    if s in ("", "D", "NR", "NP", "DAI", "DB", "AR", "T", "RET", "DIS", "SOL", "NONE", "NAN", "0", "0.0"):
        return 0
    match = re.search(r'\d+', s)
    if match:
        return int(match.group())
    return 0

# --- FILTRES LATERAUX ---
date_today = st.date_input("Date du test", value=pd.Timestamp.now())
raw_data = run_query("SELECT id, date, hippodrome, course_num, numero, cheval, cote, json_data, classement FROM selections WHERE date = ?", (str(date_today),))

algos_df = run_query("SELECT * FROM algos")
liste_algos = ["--- Nouveau ---"] + (algos_df['nom'].tolist() if not algos_df.empty else [])

col_side, col_main = st.columns([1, 2])

with col_side:
    selected = st.selectbox("Algorithme :", liste_algos)
    mode_affichage = st.radio("Mode d'affichage :", ["Standard (Simple)", "Duo (Combiné)"])

current_nom, current_form = ("", "")
if selected != "--- Nouveau ---":
    r = algos_df[algos_df['nom'] == selected].iloc[0]
    current_nom, current_form = r['nom'], r['formule']

with col_main:
    with st.container(border=True):
        nom_algo = st.text_input("Nom de l'algorithme", value=current_nom)
        formule_raw = st.text_area("Formule (Python syntax)", value=current_form, height=100)
        b1, b2, b3 = st.columns([1, 1, 2])
        if b1.button("💾 Sauver"): save_algo(nom_algo, formule_raw); st.rerun()
        if b2.button("🗑️ Effacer") and selected != "--- Nouveau ---": delete_algo(selected); st.rerun()
        btn_run = b3.button("🚀 LANCER L'ANALYSE", type="primary", use_container_width=True)

# --- MOTEUR DE TRAITEMENT ---
if btn_run and not raw_data.empty:
    try:
        # Dédoublonnage
        raw_data['_classement_int'] = raw_data['classement'].apply(parse_classement)
        raw_data['_dedup_key'] = raw_data['hippodrome'].astype(str) + "_" + raw_data['course_num'].astype(str) + "_" + raw_data['numero'].astype(str)
        raw_data = raw_data.sort_values('_classement_int', ascending=False)
        raw_data = raw_data.drop_duplicates(subset='_dedup_key', keep='first')
        raw_data = raw_data.drop(columns=['_dedup_key'])
        
        nb_classes = (raw_data['_classement_int'] > 0).sum()
        if nb_classes > 0:
            st.info(f"✅ {nb_classes} classements détectés ({len(raw_data)} partants après dédoublonnage). Backtest actif.")
        else:
            st.warning("⚠️ Aucun classement trouvé en base pour cette date.")

        data = []
        for _, r in raw_data.iterrows():
            d = json.loads(r['json_data']) if r['json_data'] else {}
            # Nettoyage des clés (Espaces -> Underscore)
            clean = {str(k).replace(' ', '_').replace('.', '').replace('-', '_'): v for k, v in d.items()}
            
            # Gestion spécifique du Borda
            for k in list(clean.keys()):
                if 'Borda' in k and k != 'Borda':
                    clean['Borda'] = clean[k]
            
            id_c = f"{r['hippodrome']}_{r['course_num']}".upper()
            val_classement = r['_classement_int']
            if val_classement == 0:
                rank_json = clean.get('Rank', clean.get('rank', None))
                if rank_json is not None:
                    val_classement = parse_classement(rank_json)
            
            clean.update({
                'Numero': int(r['numero']), 'Cheval': r['cheval'],
                'ID_C': id_c, 'hippodrome': r['hippodrome'], 'Cote': r['cote'],
                'classement': val_classement
            })
            data.append(clean)
        
        df = pd.DataFrame(data)
        df['classement'] = pd.to_numeric(df['classement'], errors='coerce').fillna(0).astype(int)

        # --- NETTOYAGE NUMÉRIQUE ÉLARGI ---
        # On ajoute les colonnes nécessaires à votre formule spécifique
        cols_to_fix = [
            'IA_Trio', 'Borda', 'ELO_Cheval', 'ELO_Eleveur', 
            'Note_IA_Decimale', 'Synergie_JCh', 'Cote', 
            'Taux_Place', 'Taux_Victoire', 'Taux_de_Place', 'Taux_de_Victoire'
        ]
        
        for c in cols_to_fix:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.').str.strip(), errors='coerce').fillna(0.0)
            
            # Création automatique des Ranks pour les colonnes détectées
            if c in df.columns and '_Rank' not in c:
                asc = True if 'Cote' in c else False
                df[f"{c}_Rank"] = df.groupby('ID_C')[c].rank(ascending=asc, method='min')

        # --- CALCUL DU SCORE (FORMULE) ---
        f_py = formule_raw.replace('?', ' if ').replace(':', ' else ').replace('""', '0')
        def calculate(row):
            ctx = row.to_dict()
            ctx.update({'log': np.log, 'sqrt': np.sqrt, 'max': max, 'min': min})
            try: 
                return float(eval(f_py, {"__builtins__": {}}, ctx))
            except: 
                return 0.0
        
        df['SCORE'] = df.apply(calculate, axis=1)

        st.divider()

        # =====================================================
        # BLOC STATISTIQUES & KPI
        # =====================================================
        all_courses = df['ID_C'].unique()
        courses_avec = [c for c in all_courses if (df[df['ID_C'] == c]['classement'] > 0).any()]
        courses_sans = [c for c in all_courses if c not in courses_avec]

        if courses_avec and mode_affichage == "Duo (Combiné)":
            stats = {
                'nb_courses': len(courses_avec),
                'base_top3': 0, 'base_top1': 0, 'base_total': 0,
                'associe_top3': 0, 'associe_total': 0,
                'folie_top3': 0, 'folie_top1': 0, 'folie_total': 0,
                'trio_ok': 0, 'quinte_partiel': 0,
                'mise_totale': 0.0, 'gains_gagnant': 0.0, 'gains_place': 0.0,
            }

            for course_id in courses_avec:
                # IMPORTANT : On trie par SCORE avant de détecter le trio
                df_c = df[df['ID_C'] == course_id].sort_values('SCORE', ascending=False)
                bases, outsiders, folie = detecter_trio(df_c)
                
                arrivee_top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                arrivee_top1 = set(df_c[df_c['classement'] == 1]['Numero'].astype(int).tolist())

                if not bases.empty:
                    nums_bases = set(bases['Numero'].astype(int).tolist())
                    stats['base_total'] += 1
                    if nums_bases & arrivee_top3: stats['base_top3'] += 1
                    if nums_bases & arrivee_top1: stats['base_top1'] += 1

                if not outsiders.empty:
                    nums_assoc = set(outsiders['Numero'].astype(int).tolist())
                    stats['associe_total'] += 1
                    if nums_assoc & arrivee_top3: stats['associe_top3'] += 1

            # Affichage des KPI
            with st.container(border=True):
                k1, k2, k3, k4 = st.columns(4)
                pct_base = round(stats['base_top3'] / stats['base_total'] * 100) if stats['base_total'] > 0 else 0
                k1.metric("💎 Base Top 3", f"{stats['base_top3']}/{stats['base_total']}", f"{pct_base}%")
                pct_base1 = round(stats['base_top1'] / stats['base_total'] * 100) if stats['base_total'] > 0 else 0
                k2.metric("🥇 Base Gagnante", f"{stats['base_top1']}/{stats['base_total']}", f"{pct_base1}%")
                # ... autres metrics ...

            st.divider()

        # =====================================================
        # AFFICHAGE FINAL (TRIÉ PAR SCORE)
        # =====================================================
        if mode_affichage == "Duo (Combiné)":

            def get_arrivee(df_course):
                df_class = df_course[df_course['classement'] > 0].sort_values('classement')
                return " - ".join(str(int(r['Numero'])) for _, r in df_class.iterrows()) if not df_class.empty else None

            # --- COURSES TERMINÉES ---
            if courses_avec:
                st.markdown(f"### 🏁 Courses terminées ({len(courses_avec)})")
                for course_id in sorted(courses_avec):
                    # Tri par SCORE décroissant
                    df_c = df[df['ID_C'] == course_id].sort_values('SCORE', ascending=False)
                    bases, outsiders, folie = detecter_trio(df_c)
                    arrivee = get_arrivee(df_c)
                    
                    arrivee_top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                    icon = "✅" if (not bases.empty and set(bases['Numero'].astype(int).tolist()) & arrivee_top3) else "❌"
                    
                    with st.container(border=True):
                        st.write(f"**{icon} 📍 {course_id}**")
                        c1, c2, c3, c4 = st.columns([3, 3, 2, 3])
                        with c1:
                            # Affichage du Numéro + Score
                            nums = [f"{int(r['Numero'])} ({r['SCORE']:.1f} pts)" for _, r in bases.iterrows()] if not bases.empty else ["?"]
                            st.success(f"**💎 BASES**\n### {' / '.join(nums)}")
                        with c2:
                            nums = [str(int(r['Numero'])) for _, r in outsiders.iterrows()] if not outsiders.empty else ["?"]
                            st.warning(f"**🏇 ASSOCIÉS**\n### {' - '.join(nums)}")
                        with c3:
                            if not folie.empty:
                                f = folie.iloc[0]
                                st.error(f"**🔥 FOLIE**\n### {int(f['Numero'])} ({f['Cote']})")
                        with c4:
                            st.info(f"**🏁 ARRIVÉE**\n### {arrivee}")

            # --- COURSES EN ATTENTE ---
            if courses_sans:
                st.markdown(f"### ⏳ Courses en attente ({len(courses_sans)})")
                for course_id in sorted(courses_sans):
                    df_c = df[df['ID_C'] == course_id].sort_values('SCORE', ascending=False)
                    bases, outsiders, folie = detecter_trio(df_c)
                    with st.container(border=True):
                        st.write(f"**📍 {course_id}**")
                        c1, c2, c3 = st.columns([3, 3, 3])
                        with c1:
                            nums = [f"{int(r['Numero'])} ({r['SCORE']:.1f} pts)" for _, r in bases.iterrows()] if not bases.empty else ["?"]
                            st.success(f"**💎 BASES**\n### {' / '.join(nums)}")
                        with c2:
                            nums = [str(int(r['Numero'])) for _, r in outsiders.iterrows()] if not outsiders.empty else ["?"]
                            st.warning(f"**🏇 ASSOCIÉS**\n### {' - '.join(nums)}")
                        with c3:
                            if not folie.empty:
                                f = folie.iloc[0]
                                st.error(f"**🔥 FOLIE**\n### {int(f['Numero'])}")
        else:
            # Mode Standard : Score mis en avant en 2ème colonne
            display_df = df.sort_values(['ID_C', 'SCORE'], ascending=[True, False])
            cols = ['ID_C', 'SCORE', 'Numero', 'Cheval', 'Cote', 'classement']
            existing_cols = [c for c in cols if c in display_df.columns]
            st.dataframe(display_df[existing_cols], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erreur technique : {e}")
        import traceback
        st.code(traceback.format_exc())

elif btn_run:
    st.warning("Aucune donnée pour cette date.")