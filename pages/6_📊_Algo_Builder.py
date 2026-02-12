import streamlit as st
import pandas as pd
import numpy as np
import json
import re
from utils import run_query, get_conn
from strategies import calculer_score_couple, detecter_trio 

st.set_page_config(layout="wide", page_title="Algo Builder")

st.markdown('<p style="font-weight:900; font-size:2.2rem; color:#1E293B; border-bottom:4px solid #3A7BD5;">🧪 Algo Builder - Stratégies & Backtest</p>', unsafe_allow_html=True)

# --- FONCTIONS UTILITAIRES ---
def save_algo(nom, formule):
    run_query("INSERT OR REPLACE INTO algos (nom, formule) VALUES (?, ?)", (nom, formule), commit=True)

def delete_algo(nom):
    run_query("DELETE FROM algos WHERE nom = ?", (nom,), commit=True)

def parse_classement(val):
    if val is None: return 0
    try:
        if pd.isna(val): return 0
    except (TypeError, ValueError): pass
    s = str(val).strip().upper()
    if s in ("", "D", "NR", "NP", "DAI", "DB", "AR", "T", "RET", "DIS", "SOL", "NONE", "NAN", "0", "0.0"):
        return 0
    match = re.search(r'\d+', s)
    return int(match.group()) if match else 0

def to_numeric_col(series):
    return pd.to_numeric(series.astype(str).str.replace(',', '.').str.strip(), errors='coerce').fillna(0.0)

def normalize_course_num(cn):
    """
    FIX A: Normalise course_num pour éviter doublons.
    'C1' et 'R2C1' pour le même hippodrome → on garde le format RxCy.
    Si pas de R, on utilise juste Cx.
    """
    cn = str(cn).strip().upper()
    m = re.match(r'(R\d+)?(C\d+)', cn)
    if m:
        reunion = m.group(1) or ''
        course = m.group(2)
        return f"{reunion}{course}"
    return cn

def get_folie_v2(df_course, exclude_nums, method='elo', cote_min=10, taux_place_min=20):
    """
    FIX D: Folie améliorée
    - Seuil cote abaissé: > 10 au lieu de > 15
    - Filtre Taux_Place > 20% pour éviter les tocards
    - Fallback sans filtre Taux_Place si rien trouvé
    """
    cands = df_course[~df_course['Numero'].isin(exclude_nums)]
    if cands.empty or 'Cote' not in cands.columns: return pd.DataFrame()
    
    # Pool principal: cote > seuil + taux place correct
    pool = cands[cands['Cote'] > cote_min]
    if pool.empty: return pd.DataFrame()
    
    # Filtre taux place si disponible
    if 'Taux_Place' in pool.columns and not pool[pool['Taux_Place'] >= taux_place_min].empty:
        pool_filtered = pool[pool['Taux_Place'] >= taux_place_min]
    else:
        pool_filtered = pool
    
    if pool_filtered.empty: pool_filtered = pool
    
    if method == 'score' and 'SCORE' in pool_filtered.columns:
        return pool_filtered.nlargest(1, 'SCORE')
    elif 'ELO_Cheval_Rank' in pool_filtered.columns:
        return pool_filtered.nsmallest(1, 'ELO_Cheval_Rank')
    return pool_filtered.head(1)

def get_confiance(scores):
    """
    FIX C: Score de confiance basé sur l'écart entre S1 et S3.
    Grand écart = forte séparation = plus confiant.
    """
    if len(scores) < 3: return "?"
    gap = scores[0] - scores[2]
    if gap >= 50: return "🟢 Forte"
    elif gap >= 30: return "🟡 Moyenne"
    else: return "🔴 Faible"

def nums_str(df_sub):
    return " - ".join(str(int(r['Numero'])) for _, r in df_sub.iterrows())

def get_arrivee(dfc):
    dc = dfc[dfc['classement'] > 0].sort_values('classement')
    return " - ".join(str(int(r['Numero'])) for _, r in dc.iterrows()) if not dc.empty else None

# --- FILTRES ---
date_today = st.date_input("Date du test", value=pd.Timestamp.now())
raw_data = run_query("SELECT id, date, hippodrome, course_num, numero, cheval, cote, json_data, classement FROM selections WHERE date = ?", (str(date_today),))

algos_df = run_query("SELECT * FROM algos")
liste_algos = ["--- Nouveau ---"] + (algos_df['nom'].tolist() if not algos_df.empty else [])

col_side, col_main = st.columns([1, 2])

with col_side:
    selected = st.selectbox("Algorithme :", liste_algos)
    mode_affichage = st.radio("Mode :", ["Simple (1 cheval)", "Duo (2 chevaux)", "Trio + Folie (3+1)"])
    st.divider()
    st.markdown("**⚙️ Réglages Folie**")
    folie_cote_min = st.slider("Cote minimum folie", 5, 30, 10)
    folie_taux_min = st.slider("Taux Placé min (%)", 0, 50, 20)

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

# =====================================================
# MOTEUR
# =====================================================
if btn_run and not raw_data.empty:
    try:
        # Dédoublonnage
        raw_data['_classement_int'] = raw_data['classement'].apply(parse_classement)
        
        # FIX A: Normaliser course_num AVANT de construire ID_C
        raw_data['_course_norm'] = raw_data['course_num'].apply(normalize_course_num)
        raw_data['_dedup_key'] = raw_data['hippodrome'].astype(str) + "_" + raw_data['_course_norm'] + "_" + raw_data['numero'].astype(str)
        raw_data = raw_data.sort_values('_classement_int', ascending=False).drop_duplicates(subset='_dedup_key', keep='first').drop(columns=['_dedup_key'])
        
        nb_classes = (raw_data['_classement_int'] > 0).sum()
        if nb_classes > 0:
            st.info(f"✅ {nb_classes} classements détectés ({len(raw_data)} partants). Backtest actif.")
        else:
            st.warning("⚠️ Aucun classement trouvé pour cette date.")

        data = []
        for _, r in raw_data.iterrows():
            d = json.loads(r['json_data']) if r['json_data'] else {}
            clean = {str(k).replace(' ', '_').replace('.', '').replace('-', '_'): v for k, v in d.items()}
            for k in list(clean.keys()):
                if 'Borda' in k and k != 'Borda': clean['Borda'] = clean[k]
            
            # FIX A: Utiliser course_num normalisé pour ID_C
            cn = normalize_course_num(r['course_num'])
            id_c = f"{r['hippodrome']}_{cn}".upper()
            
            val_classement = r['_classement_int']
            if val_classement == 0:
                rj = clean.get('Rank', clean.get('rank', None))
                if rj is not None: val_classement = parse_classement(rj)
            clean.update({'Numero': int(r['numero']), 'Cheval': r['cheval'], 'ID_C': id_c,
                         'hippodrome': r['hippodrome'], 'Cote': r['cote'], 'classement': val_classement})
            data.append(clean)
        
        df = pd.DataFrame(data)
        df['classement'] = pd.to_numeric(df['classement'], errors='coerce').fillna(0).astype(int)

        # --- NETTOYAGE NUMÉRIQUE ---
        num_cols = ['IA_Trio', 'Borda', 'ELO_Cheval', 'ELO_Jockey', 'ELO_Entraineur',
                    'ELO_Proprio', 'ELO_Eleveur', 'Note_IA_Decimale', 'Synergie_JCh', 
                    'Cote', 'Taux_Victoire', 'Taux_Place', 'Taux_Incident',
                    'Sigma_Horse', 'Moy_Alloc', 'IA_Gagnant', 'IA_Couple', 'IA_Multi',
                    'IA_Quinte', 'IMDC', 'Popularite', 'Evo_Popul', 'Repos',
                    'Turf_Points', 'TPch_90', 'Moy_TPch_365', 'Moy_TPch_90',
                    'TPJ_365', 'TPJ_90', 'Moy_TPJ_365', 'Moy_TPJ_90',
                    'Cote_BZH', 'Courses_courues', 'nombre_victoire', 'nombre_place',
                    'incident', 'distanceRecord_sec', 'Rang_J']
        for c in num_cols:
            if c in df.columns: df[c] = to_numeric_col(df[c])
        for tc in ['Taux_Victoire', 'Taux_Place', 'Taux_Incident']:
            if tc in df.columns and df[tc].max() <= 1.0: df[tc] = df[tc] * 100

        rank_desc = ['IA_Trio', 'Borda', 'ELO_Cheval', 'ELO_Jockey', 'ELO_Entraineur',
                     'ELO_Proprio', 'ELO_Eleveur', 'Note_IA_Decimale', 'Synergie_JCh',
                     'Taux_Victoire', 'Taux_Place', 'Turf_Points', 'TPch_90',
                     'IA_Gagnant', 'IA_Couple', 'IA_Multi', 'IA_Quinte', 'Sigma_Horse']
        for c in rank_desc:
            cr = f"{c}_Rank"
            if c in df.columns and cr not in df.columns:
                df[cr] = df.groupby('ID_C')[c].rank(ascending=False, method='min')
            elif cr in df.columns:
                df[cr] = to_numeric_col(df[cr])
        for c in ['Cote', 'Cote_BZH']:
            cr = f"{c}_Rank"
            if c in df.columns and cr not in df.columns:
                df[cr] = df.groupby('ID_C')[c].rank(ascending=True, method='min')
            elif cr in df.columns:
                df[cr] = to_numeric_col(df[cr])
        for c in df.columns:
            if c.endswith('_Rank'): df[c] = to_numeric_col(df[c])

        if 'IA_Trio_Rank' in df.columns and 'Borda_Rank' in df.columns:
            df['IA_Borda_Score'] = (1 / df['IA_Trio_Rank'].clip(lower=1)) + (1 / df['Borda_Rank'].clip(lower=1))
            df['IA_Borda_Rank'] = df.groupby('ID_C')['IA_Borda_Score'].rank(ascending=False, method='min').astype(int)

        f_py = formule_raw.replace('?', ' if ').replace(':', ' else ').replace('""', '0')
        def calculate(row):
            ctx = row.to_dict()
            ctx.update({'log': np.log, 'sqrt': np.sqrt, 'max': max, 'min': min, 'abs': abs})
            try: return float(eval(f_py, {"__builtins__": {}}, ctx))
            except: return 0.0
        df['SCORE'] = df.apply(calculate, axis=1)
        df['SCORE_Rank'] = df.groupby('ID_C')['SCORE'].rank(ascending=False, method='min').astype(int)

        # =====================================================
        # FIX B: HYBRIDE - Score combiné Formule + IA pondéré par cote
        # Quand cotes serrées (favori cote haute) → Formule pèse plus
        # Quand gros favori (cote basse) → IA pèse plus
        # =====================================================
        def compute_hybride(df_c):
            cote_min = df_c['Cote'].min() if 'Cote' in df_c.columns else 5
            # Poids IA augmente quand le favori a une cote basse
            if cote_min < 3:
                w_ia = 0.65; w_f = 0.35
            elif cote_min < 5:
                w_ia = 0.55; w_f = 0.45
            else:
                w_ia = 0.35; w_f = 0.65
            return w_ia, w_f
        
        # Normaliser SCORE et IA_Borda_Score par course pour l'hybride
        for cid in df['ID_C'].unique():
            mask = df['ID_C'] == cid
            df_c = df[mask]
            # Normaliser SCORE entre 0 et 1 dans la course
            s_min, s_max = df_c['SCORE'].min(), df_c['SCORE'].max()
            if s_max > s_min:
                df.loc[mask, 'SCORE_Norm'] = (df_c['SCORE'] - s_min) / (s_max - s_min)
            else:
                df.loc[mask, 'SCORE_Norm'] = 0.5
            # Normaliser IA_Borda
            if 'IA_Borda_Score' in df_c.columns:
                ib_min, ib_max = df_c['IA_Borda_Score'].min(), df_c['IA_Borda_Score'].max()
                if ib_max > ib_min:
                    df.loc[mask, 'IA_Borda_Norm'] = (df_c['IA_Borda_Score'] - ib_min) / (ib_max - ib_min)
                else:
                    df.loc[mask, 'IA_Borda_Norm'] = 0.5
            else:
                df.loc[mask, 'IA_Borda_Norm'] = 0.0
            
            w_ia, w_f = compute_hybride(df_c)
            df.loc[mask, 'HYBRIDE'] = w_f * df.loc[mask, 'SCORE_Norm'] + w_ia * df.loc[mask, 'IA_Borda_Norm']
            df.loc[mask, '_w_formule'] = w_f
            df.loc[mask, '_w_ia'] = w_ia
        
        df['HYBRIDE_Rank'] = df.groupby('ID_C')['HYBRIDE'].rank(ascending=False, method='min').astype(int)

        st.divider()

        all_courses = sorted(df['ID_C'].unique())
        courses_avec = [c for c in all_courses if (df[df['ID_C'] == c]['classement'] > 0).any()]
        courses_sans = [c for c in all_courses if c not in courses_avec]

        st.caption(f"📊 {len(all_courses)} courses uniques ({len(courses_avec)} terminées, {len(courses_sans)} en attente)")

        # =====================================================
        # MODE SIMPLE (1 cheval)
        # =====================================================
        if mode_affichage == "Simple (1 cheval)":
            if courses_avec:
                st_f = {'g': 0, 't3': 0, 'n': 0}
                st_ib = {'g': 0, 't3': 0, 'n': 0}
                st_hyb = {'g': 0, 't3': 0, 'n': 0}
                rows_summary = []
                for cid in courses_avec:
                    df_c = df[df['ID_C'] == cid]
                    top1 = set(df_c[df_c['classement'] == 1]['Numero'].astype(int).tolist())
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                    g_row = df_c[df_c['classement'] == 1].iloc[0] if not df_c[df_c['classement'] == 1].empty else None

                    bf = df_c.nlargest(1, 'SCORE').iloc[0]; nf = int(bf['Numero'])
                    bib = df_c.nsmallest(1, 'IA_Borda_Rank').iloc[0] if 'IA_Borda_Rank' in df_c.columns else df_c.iloc[0]; nib = int(bib['Numero'])
                    bh = df_c.nlargest(1, 'HYBRIDE').iloc[0]; nh = int(bh['Numero'])

                    for n, st_x in [(nf, st_f), (nib, st_ib), (nh, st_hyb)]:
                        st_x['n'] += 1
                        if n in top1: st_x['g'] += 1
                        if n in top3: st_x['t3'] += 1

                    def v(n): return "🥇" if n in top1 else ("✅" if n in top3 else "❌")
                    w_f = df_c.iloc[0]['_w_formule'] if '_w_formule' in df_c.columns else 0.5
                    rows_summary.append({
                        'Course': cid,
                        'Formule_Num': nf, 'Formule_Cheval': bf['Cheval'], 'Formule_Cote': round(float(bf['Cote']),1) if pd.notna(bf['Cote']) else 0,
                        'Formule_Score': round(float(bf['SCORE']),2), 'Formule_Verdict': v(nf),
                        'IA_Borda_Num': nib, 'IA_Borda_Cheval': bib['Cheval'], 'IA_Borda_Cote': round(float(bib['Cote']),1) if pd.notna(bib['Cote']) else 0,
                        'IA_Borda_Verdict': v(nib),
                        'Hybride_Num': nh, 'Hybride_Cheval': bh['Cheval'], 'Hybride_Cote': round(float(bh['Cote']),1) if pd.notna(bh['Cote']) else 0,
                        'Hybride_Verdict': v(nh), 'Poids_F': round(w_f*100),
                        'Gagnant_Num': int(g_row['Numero']) if g_row is not None else 0,
                        'Gagnant_Cheval': g_row['Cheval'] if g_row is not None else "?",
                        'Gagnant_Cote': round(float(g_row['Cote']),1) if g_row is not None and pd.notna(g_row['Cote']) else 0,
                    })

                st.markdown("### 📊 Comparaison Simple")
                with st.container(border=True):
                    k1, k2, k3, k4, k5, k6, k7, k8, k9 = st.columns(9)
                    t = st_f['n']; p = lambda n: f"{round(n/t*100)}%" if t else "0%"
                    k1.metric("🎯 F Gagnant", f"{st_f['g']}/{t}", p(st_f['g']))
                    k2.metric("🎯 F Top3", f"{st_f['t3']}/{t}", p(st_f['t3']))
                    k3.metric("🎯 F Échec", f"{t-st_f['t3']}/{t}", p(t-st_f['t3']), delta_color="inverse")
                    k4.metric("🤖 IA Gagnant", f"{st_ib['g']}/{t}", p(st_ib['g']))
                    k5.metric("🤖 IA Top3", f"{st_ib['t3']}/{t}", p(st_ib['t3']))
                    k6.metric("🤖 IA Échec", f"{t-st_ib['t3']}/{t}", p(t-st_ib['t3']), delta_color="inverse")
                    k7.metric("⚡ Hyb Gagnant", f"{st_hyb['g']}/{t}", p(st_hyb['g']))
                    k8.metric("⚡ Hyb Top3", f"{st_hyb['t3']}/{t}", p(st_hyb['t3']))
                    k9.metric("⚡ Hyb Échec", f"{t-st_hyb['t3']}/{t}", p(t-st_hyb['t3']), delta_color="inverse")
                st.divider()
                
                display_rows = [{'Course': r['Course'],
                                 'Formule': f"{r['Formule_Verdict']} N°{r['Formule_Num']}",
                                 'IA+Borda': f"{r['IA_Borda_Verdict']} N°{r['IA_Borda_Num']}",
                                 '⚡Hybride': f"{r['Hybride_Verdict']} N°{r['Hybride_Num']} ({r['Poids_F']}%F)",
                                 'Gagnant': f"N°{r['Gagnant_Num']} {r['Gagnant_Cheval']}", 'Cote': r['Gagnant_Cote']}
                                for r in rows_summary]
                st.markdown("### 🏁 Résultats")
                st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

            if courses_sans:
                st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
                wr = []
                for cid in courses_sans:
                    df_c = df[df['ID_C'] == cid]
                    bf = df_c.nlargest(1, 'SCORE').iloc[0]
                    bib = df_c.nsmallest(1, 'IA_Borda_Rank').iloc[0] if 'IA_Borda_Rank' in df_c.columns else df_c.iloc[0]
                    bh = df_c.nlargest(1, 'HYBRIDE').iloc[0]
                    wr.append({'Course': cid, 'Formule': f"N°{int(bf['Numero'])} {bf['Cheval']}",
                              'IA+Borda': f"N°{int(bib['Numero'])} {bib['Cheval']}",
                              '⚡Hybride': f"N°{int(bh['Numero'])} {bh['Cheval']}"})
                st.dataframe(pd.DataFrame(wr), use_container_width=True, hide_index=True)

            if courses_avec:
                st.download_button("📥 CSV Simple", pd.DataFrame(rows_summary).to_csv(index=False, sep=';').encode('utf-8'),
                                   f"export_simple_{date_today}.csv", "text/csv", use_container_width=True)
            with st.expander("📝 Détail complet"):
                all_c = df.columns.tolist()
                defs = [c for c in ['ID_C','Numero','Cheval','SCORE','SCORE_Rank','HYBRIDE','HYBRIDE_Rank','IA_Borda_Rank','Cote','classement'] if c in all_c]
                ch = st.multiselect("Colonnes :", all_c, default=defs)
                if ch:
                    detail_df = df[ch].sort_values(['ID_C','SCORE'], ascending=[True,False])
                    st.dataframe(detail_df, use_container_width=True, hide_index=True)
                    st.download_button("📥 CSV Détail", detail_df.to_csv(index=False, sep=';').encode('utf-8'),
                                       f"export_detail_{date_today}.csv", "text/csv")

        # =====================================================
        # MODE DUO (2 chevaux)
        # =====================================================
        elif mode_affichage == "Duo (2 chevaux)":
            if courses_avec:
                st_f = {'g': 0, 't3': 0, 'n': 0}
                st_ib = {'g': 0, 't3': 0, 'n': 0}
                st_hyb = {'g': 0, 't3': 0, 'n': 0}
                rows_export = []
                
                for cid in courses_avec:
                    df_c = df[df['ID_C'] == cid]
                    top1 = set(df_c[df_c['classement'] == 1]['Numero'].astype(int).tolist())
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                    
                    duo_f = df_c.nlargest(2, 'SCORE'); df2 = set(duo_f['Numero'].astype(int).tolist())
                    duo_ib = df_c.nsmallest(2, 'IA_Borda_Rank') if 'IA_Borda_Rank' in df_c.columns else df_c.head(2)
                    dib = set(duo_ib['Numero'].astype(int).tolist())
                    duo_hyb = df_c.nlargest(2, 'HYBRIDE'); dh = set(duo_hyb['Numero'].astype(int).tolist())
                    
                    for s, nums in [(st_f, df2), (st_ib, dib), (st_hyb, dh)]:
                        s['n'] += 1
                        if nums & top1: s['g'] += 1
                        if nums & top3: s['t3'] += 1

                    ok_f = bool(df2 & top3); ok_ib = bool(dib & top3); ok_h = bool(dh & top3)
                    arrivee = get_arrivee(df_c)
                    rows_export.append({
                        'Course': cid,
                        'F_N1': int(duo_f.iloc[0]['Numero']), 'F_N2': int(duo_f.iloc[1]['Numero']),
                        'F_Top3': "OUI" if ok_f else "NON",
                        'IB_N1': int(duo_ib.iloc[0]['Numero']), 'IB_N2': int(duo_ib.iloc[1]['Numero']),
                        'IB_Top3': "OUI" if ok_ib else "NON",
                        'Hyb_N1': int(duo_hyb.iloc[0]['Numero']), 'Hyb_N2': int(duo_hyb.iloc[1]['Numero']),
                        'Hyb_Top3': "OUI" if ok_h else "NON",
                        'Arrivee': arrivee or "",
                    })

                st.markdown("### 📊 Comparaison Duo")
                with st.container(border=True):
                    k1, k2, k3, k4, k5, k6 = st.columns(6)
                    t = st_f['n']; p = lambda n: f"{round(n/t*100)}%" if t else "0%"
                    k1.metric("🎯 F Gagnant", f"{st_f['g']}/{t}", p(st_f['g']))
                    k2.metric("🎯 F Top3", f"{st_f['t3']}/{t}", p(st_f['t3']))
                    k3.metric("🤖 IA Gagnant", f"{st_ib['g']}/{t}", p(st_ib['g']))
                    k4.metric("🤖 IA Top3", f"{st_ib['t3']}/{t}", p(st_ib['t3']))
                    k5.metric("⚡ Hyb Gagnant", f"{st_hyb['g']}/{t}", p(st_hyb['g']))
                    k6.metric("⚡ Hyb Top3", f"{st_hyb['t3']}/{t}", p(st_hyb['t3']))
                st.divider()

                st.markdown(f"### 🏁 Courses terminées ({len(courses_avec)})")
                for row in rows_export:
                    cid = row['Course']
                    df_c = df[df['ID_C'] == cid]
                    duo_f = df_c.nlargest(2, 'SCORE')
                    duo_ib = df_c.nsmallest(2, 'IA_Borda_Rank') if 'IA_Borda_Rank' in df_c.columns else df_c.head(2)
                    duo_hyb = df_c.nlargest(2, 'HYBRIDE')
                    ok_f = row['F_Top3']=="OUI"; ok_ib = row['IB_Top3']=="OUI"; ok_h = row['Hyb_Top3']=="OUI"
                    with st.container(border=True):
                        best = "✅" if (ok_f or ok_h) else "❌"
                        st.write(f"**{best} 📍 {cid}**")
                        c1, c2, c3, c4 = st.columns([3, 3, 3, 3])
                        with c1: st.success(f"**🎯 FORMULE** {'✅' if ok_f else '❌'}\n### {nums_str(duo_f)}")
                        with c2: st.warning(f"**🤖 IA+B** {'✅' if ok_ib else '❌'}\n### {nums_str(duo_ib)}")
                        with c3: st.info(f"**⚡ HYBRIDE** {'✅' if ok_h else '❌'}\n### {nums_str(duo_hyb)}")
                        with c4: st.write(f"**🏁 ARRIVÉE**\n### {row['Arrivee']}")

            if courses_sans:
                st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
                for cid in courses_sans:
                    df_c = df[df['ID_C'] == cid]
                    duo_f = df_c.nlargest(2, 'SCORE')
                    duo_ib = df_c.nsmallest(2, 'IA_Borda_Rank') if 'IA_Borda_Rank' in df_c.columns else df_c.head(2)
                    duo_hyb = df_c.nlargest(2, 'HYBRIDE')
                    with st.container(border=True):
                        st.write(f"**📍 {cid}**")
                        c1, c2, c3 = st.columns(3)
                        with c1: st.success(f"**🎯 FORMULE**\n### {nums_str(duo_f)}")
                        with c2: st.warning(f"**🤖 IA+B**\n### {nums_str(duo_ib)}")
                        with c3: st.info(f"**⚡ HYBRIDE**\n### {nums_str(duo_hyb)}")

            if courses_avec:
                st.download_button("📥 CSV Duo", pd.DataFrame(rows_export).to_csv(index=False, sep=';').encode('utf-8'),
                                   f"export_duo_{date_today}.csv", "text/csv", use_container_width=True)

        # =====================================================
        # MODE TRIO + FOLIE (3+1)
        # =====================================================
        else:
            if courses_avec:
                st_f = {'t3_2plus': 0, 't3_3': 0, 'folie_t3': 0, 'folie_n': 0, 'n': 0,
                        'mise': 0.0, 'gains_g': 0.0, 'gains_p': 0.0}
                st_ib = {'t3_2plus': 0, 't3_3': 0, 'folie_t3': 0, 'folie_n': 0, 'n': 0}
                st_hyb = {'t3_2plus': 0, 't3_3': 0, 'folie_t3': 0, 'folie_n': 0, 'n': 0,
                          'mise': 0.0, 'gains_g': 0.0, 'gains_p': 0.0}
                rows_export = []

                for cid in courses_avec:
                    df_c = df[df['ID_C'] == cid]
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                    top1 = set(df_c[df_c['classement'] == 1]['Numero'].astype(int).tolist())

                    trio_f = df_c.nlargest(3, 'SCORE')
                    nums_f = set(trio_f['Numero'].astype(int).tolist())
                    folie_f = get_folie_v2(df_c, nums_f, method='score', cote_min=folie_cote_min, taux_place_min=folie_taux_min)
                    
                    if 'IA_Borda_Rank' in df_c.columns:
                        trio_ib = df_c.nsmallest(3, 'IA_Borda_Rank')
                    else:
                        trio_ib = df_c.head(3)
                    nums_ib = set(trio_ib['Numero'].astype(int).tolist())
                    folie_ib = get_folie_v2(df_c, nums_ib, method='elo', cote_min=folie_cote_min, taux_place_min=folie_taux_min)

                    trio_hyb = df_c.nlargest(3, 'HYBRIDE')
                    nums_hyb = set(trio_hyb['Numero'].astype(int).tolist())
                    folie_hyb = get_folie_v2(df_c, nums_hyb, method='score', cote_min=folie_cote_min, taux_place_min=folie_taux_min)

                    # FIX C: Confiance
                    scores_f = [float(trio_f.iloc[i]['SCORE']) for i in range(min(3, len(trio_f)))]
                    confiance = get_confiance(scores_f)

                    for trio_data, st_x, folie_data in [(trio_f, st_f, folie_f), (trio_ib, st_ib, folie_ib), (trio_hyb, st_hyb, folie_hyb)]:
                        nums = set(trio_data['Numero'].astype(int).tolist())
                        st_x['n'] += 1
                        hit = len(nums & top3)
                        if hit >= 2: st_x['t3_2plus'] += 1
                        if hit == 3: st_x['t3_3'] += 1
                        if not folie_data.empty:
                            st_x['folie_n'] += 1
                            if int(folie_data.iloc[0]['Numero']) in top3: st_x['folie_t3'] += 1

                    # ROI formule
                    if not trio_f.empty:
                        b1n = int(trio_f.iloc[0]['Numero']); b1c = float(trio_f.iloc[0]['Cote']) if pd.notna(trio_f.iloc[0]['Cote']) else 0
                        st_f['mise'] += 2.0
                        if b1n in top1 and b1c > 0: st_f['gains_g'] += 2.0 * b1c
                        for _, b in trio_f.iterrows():
                            st_f['mise'] += 1.0; bc = float(b['Cote']) if pd.notna(b['Cote']) else 0
                            if int(b['Numero']) in top3 and bc > 0: st_f['gains_p'] += bc / 3.0
                    # ROI hybride
                    if not trio_hyb.empty:
                        b1n = int(trio_hyb.iloc[0]['Numero']); b1c = float(trio_hyb.iloc[0]['Cote']) if pd.notna(trio_hyb.iloc[0]['Cote']) else 0
                        st_hyb['mise'] += 2.0
                        if b1n in top1 and b1c > 0: st_hyb['gains_g'] += 2.0 * b1c
                        for _, b in trio_hyb.iterrows():
                            st_hyb['mise'] += 1.0; bc = float(b['Cote']) if pd.notna(b['Cote']) else 0
                            if int(b['Numero']) in top3 and bc > 0: st_hyb['gains_p'] += bc / 3.0

                    folie_f_num = int(folie_f.iloc[0]['Numero']) if not folie_f.empty else 0
                    folie_f_cote = round(float(folie_f.iloc[0]['Cote']),1) if not folie_f.empty and pd.notna(folie_f.iloc[0]['Cote']) else 0
                    folie_ib_num = int(folie_ib.iloc[0]['Numero']) if not folie_ib.empty else 0
                    folie_hyb_num = int(folie_hyb.iloc[0]['Numero']) if not folie_hyb.empty else 0
                    folie_hyb_cote = round(float(folie_hyb.iloc[0]['Cote']),1) if not folie_hyb.empty and pd.notna(folie_hyb.iloc[0]['Cote']) else 0
                    arrivee = get_arrivee(df_c)

                    hit_f = len(nums_f & top3); hit_ib = len(nums_ib & top3); hit_hyb = len(nums_hyb & top3)
                    rows_export.append({
                        'Course': cid, 'Confiance': confiance,
                        'F_N1': int(trio_f.iloc[0]['Numero']), 'F_N2': int(trio_f.iloc[1]['Numero']), 'F_N3': int(trio_f.iloc[2]['Numero']),
                        'F_Hit': f"{hit_f}/3", 'F_Folie': folie_f_num, 'F_Folie_Cote': folie_f_cote,
                        'F_Folie_OK': "OUI" if folie_f_num in top3 else ("NON" if folie_f_num else ""),
                        'IB_N1': int(trio_ib.iloc[0]['Numero']), 'IB_N2': int(trio_ib.iloc[1]['Numero']), 'IB_N3': int(trio_ib.iloc[2]['Numero']),
                        'IB_Hit': f"{hit_ib}/3",
                        'Hyb_N1': int(trio_hyb.iloc[0]['Numero']), 'Hyb_N2': int(trio_hyb.iloc[1]['Numero']), 'Hyb_N3': int(trio_hyb.iloc[2]['Numero']),
                        'Hyb_Hit': f"{hit_hyb}/3", 'Hyb_Folie': folie_hyb_num, 'Hyb_Folie_Cote': folie_hyb_cote,
                        'Hyb_Folie_OK': "OUI" if folie_hyb_num in top3 else ("NON" if folie_hyb_num else ""),
                        'Arrivee': arrivee or "",
                    })

                # --- KPI TRIO ---
                st.markdown("### 📊 Comparaison Trio + Folie")
                
                def show_trio_kpi(label, emoji, st_x):
                    with st.container(border=True):
                        st.markdown(f"**{emoji} {label}**")
                        cols = st.columns(5 if 'mise' in st_x else 3)
                        t = st_x['n']; p = lambda n: f"{round(n/t*100)}%" if t else "0%"
                        cols[0].metric("2+ dans Top 3", f"{st_x['t3_2plus']}/{t}", p(st_x['t3_2plus']))
                        cols[1].metric("3/3 dans Top 3", f"{st_x['t3_3']}/{t}", p(st_x['t3_3']))
                        fn = st_x['folie_n']; fp = lambda n: f"{round(n/fn*100)}%" if fn else "0%"
                        cols[2].metric("🔥 Folie Top 3", f"{st_x['folie_t3']}/{fn}", fp(st_x['folie_t3']))
                        if 'mise' in st_x and len(cols) >= 5:
                            gt = st_x['gains_g'] + st_x['gains_p']
                            roi = round((gt - st_x['mise']) / st_x['mise'] * 100, 1) if st_x['mise'] > 0 else 0
                            cols[3].metric("💰 Mise", f"{st_x['mise']:.0f}€")
                            cols[4].metric("📈 ROI", f"{roi}%", f"{'+' if gt-st_x['mise']>=0 else ''}{gt-st_x['mise']:.1f}€",
                                         delta_color="normal" if roi >= 0 else "inverse")

                show_trio_kpi("Trio Formule", "🎯", st_f)
                show_trio_kpi("Trio IA+Borda", "🤖", st_ib)
                show_trio_kpi("Trio Hybride", "⚡", st_hyb)

                st.divider()

                # --- COURSES TERMINÉES ---
                st.markdown(f"### 🏁 Courses terminées ({len(courses_avec)})")
                for row in rows_export:
                    cid = row['Course']
                    df_c = df[df['ID_C'] == cid]
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                    
                    trio_f = df_c.nlargest(3, 'SCORE')
                    nums_f = set(trio_f['Numero'].astype(int).tolist())
                    folie_f = get_folie_v2(df_c, nums_f, method='score', cote_min=folie_cote_min, taux_place_min=folie_taux_min)
                    trio_hyb = df_c.nlargest(3, 'HYBRIDE')
                    nums_hyb = set(trio_hyb['Numero'].astype(int).tolist())
                    folie_hyb = get_folie_v2(df_c, nums_hyb, method='score', cote_min=folie_cote_min, taux_place_min=folie_taux_min)
                    
                    hit_f = int(row['F_Hit'][0]); hit_hyb = int(row['Hyb_Hit'][0])
                    best_hit = max(hit_f, hit_hyb)
                    ok = best_hit >= 2

                    with st.container(border=True):
                        st.write(f"**{'✅' if ok else '❌'} 📍 {cid}** — {row['Confiance']} — F:{row['F_Hit']} | Hyb:{row['Hyb_Hit']}")
                        c1, c2, c3 = st.columns([4, 4, 4])
                        with c1:
                            txt = nums_str(trio_f)
                            ft = ""
                            if not folie_f.empty:
                                fn = int(folie_f.iloc[0]['Numero']); fc = float(folie_f.iloc[0]['Cote']) if pd.notna(folie_f.iloc[0]['Cote']) else 0
                                ft = f"\n🔥 N°{fn} (Cote {fc}) {'✅' if fn in top3 else '❌'}"
                            st.success(f"**🎯 FORMULE** {row['F_Hit']}\n### {txt}{ft}")
                        with c2:
                            txt = nums_str(trio_hyb)
                            ft = ""
                            if not folie_hyb.empty:
                                fn = int(folie_hyb.iloc[0]['Numero']); fc = float(folie_hyb.iloc[0]['Cote']) if pd.notna(folie_hyb.iloc[0]['Cote']) else 0
                                ft = f"\n🔥 N°{fn} (Cote {fc}) {'✅' if fn in top3 else '❌'}"
                            st.info(f"**⚡ HYBRIDE** {row['Hyb_Hit']}\n### {txt}{ft}")
                        with c3:
                            st.warning(f"**🏁 ARRIVÉE**\n### {row['Arrivee']}")

            # --- EN ATTENTE ---
            if courses_sans:
                st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
                for cid in courses_sans:
                    df_c = df[df['ID_C'] == cid]
                    trio_f = df_c.nlargest(3, 'SCORE')
                    nums_f = set(trio_f['Numero'].astype(int).tolist())
                    folie_f = get_folie_v2(df_c, nums_f, method='score', cote_min=folie_cote_min, taux_place_min=folie_taux_min)
                    trio_hyb = df_c.nlargest(3, 'HYBRIDE')
                    nums_hyb = set(trio_hyb['Numero'].astype(int).tolist())
                    folie_hyb = get_folie_v2(df_c, nums_hyb, method='score', cote_min=folie_cote_min, taux_place_min=folie_taux_min)

                    scores_f = [float(trio_f.iloc[i]['SCORE']) for i in range(min(3, len(trio_f)))]
                    confiance = get_confiance(scores_f)

                    with st.container(border=True):
                        st.write(f"**📍 {cid}** — {confiance}")
                        c1, c2 = st.columns(2)
                        with c1:
                            txt = nums_str(trio_f)
                            if not folie_f.empty:
                                fn = int(folie_f.iloc[0]['Numero']); fc = float(folie_f.iloc[0]['Cote']) if pd.notna(folie_f.iloc[0]['Cote']) else 0
                                txt += f"\n🔥 N°{fn} (Cote {fc})"
                            st.success(f"**🎯 FORMULE**\n### {txt}")
                        with c2:
                            txt = nums_str(trio_hyb)
                            if not folie_hyb.empty:
                                fn = int(folie_hyb.iloc[0]['Numero']); fc = float(folie_hyb.iloc[0]['Cote']) if pd.notna(folie_hyb.iloc[0]['Cote']) else 0
                                txt += f"\n🔥 N°{fn} (Cote {fc})"
                            st.info(f"**⚡ HYBRIDE**\n### {txt}")

            if courses_avec:
                st.download_button("📥 CSV Trio+Folie", pd.DataFrame(rows_export).to_csv(index=False, sep=';').encode('utf-8'),
                                   f"export_trio_{date_today}.csv", "text/csv", use_container_width=True)

    except Exception as e:
        st.error(f"Erreur technique : {e}")
        import traceback
        st.code(traceback.format_exc())

elif btn_run:
    st.warning("Aucune donnée pour cette date.")