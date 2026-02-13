import streamlit as st
import pandas as pd
import numpy as np
import json
import re
from utils import run_query, get_conn
from strategies import calculer_score_couple, detecter_trio, calculer_confiance_duo

st.set_page_config(layout="wide", page_title="Algo Builder")

st.markdown('<p style="font-weight:900; font-size:2.2rem; color:#1E293B; border-bottom:4px solid #3A7BD5;">🧪 Algo Builder - Stratégies & Backtest</p>', unsafe_allow_html=True)

FORMULES_PRESET = {
    "🎯 Simple Optimisé (Gagnant)": "IA_Gagnant * 50 + Note_IA_Decimale * 2 + 50 / (Cote if Cote > 0 else 1) + Synergie_JCh * 0.2",
    "🎲 Duo Optimisé (Couplé)": "(6 - IA_Couple_Rank) * 4 + (6 - Borda_Rank) * 2.5 + (6 - Cote_Rank) * 2 + (6 - Note_IA_Decimale_Rank) * 1.5",
    "🏇 Trio Optimisé": "IA_Multi * 40 + IA_Trio * 18 + 40 / (Cote if Cote > 0 else 1) + Taux_Place * 0.10",
    "📊 F11 Polyvalente": "IA_Trio * 18 + Borda * 2.5 + Note_IA_Decimale * 2 + Synergie_JCh * 0.5 + Taux_Place * 0.12 + Taux_Victoire * 0.12 + 60 / (Cote if Cote > 0 else 1) + IA_Gagnant * 15",
    "🔷 Borda Pure": "Borda * 10 + 50 / (Cote if Cote > 0 else 1)",
}

DISC_MAP = {'A': 'Attelé', 'M': 'Monté', 'P': 'Plat', 'O': 'Obstacle', 'C': 'Course', '': 'Inconnu'}

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
    except Exception:
        pass
    s = str(val).strip().upper()
    if s in ("", "D", "NR", "NP", "DAI", "DB", "AR", "T", "RET", "DIS", "SOL", "NONE", "NAN", "0", "0.0"):
        return 0
    m = re.search(r'\d+', s)
    return int(m.group()) if m else 0

def to_numeric_col(s):
    return pd.to_numeric(s.astype(str).str.replace(',', '.').str.strip(), errors='coerce').fillna(0.0)

def normalize_course_num(cn):
    cn = str(cn).strip().upper()
    m = re.match(r'(R\d+)?(C\d+)', cn)
    if m:
        return f"{m.group(1) or ''}{m.group(2)}"
    return cn

def get_folie_v2(df_c, excl, method='elo', cote_min=10, tp_min=20):
    cands = df_c[~df_c['Numero'].isin(excl)]
    if cands.empty or 'Cote' not in cands.columns:
        return pd.DataFrame()
    pool = cands[cands['Cote'] > cote_min]
    if pool.empty:
        return pd.DataFrame()
    if 'Taux_Place' in pool.columns and not pool[pool['Taux_Place'] >= tp_min].empty:
        pool = pool[pool['Taux_Place'] >= tp_min]
    if method == 'score' and 'SCORE' in pool.columns:
        return pool.nlargest(1, 'SCORE')
    elif 'ELO_Cheval_Rank' in pool.columns:
        return pool.nsmallest(1, 'ELO_Cheval_Rank')
    return pool.head(1)

def get_confiance(scores):
    if len(scores) < 3:
        return "?"
    gap = scores[0] - scores[2]
    return "🟢" if gap >= 50 else ("🟡" if gap >= 30 else "🔴")

def colored_nums(nums_list, ref_set):
    return " — ".join(f":green[**{n}**]✓" if n in ref_set else f":red[**{n}**]✗" for n in nums_list)

def nums_str(df_sub):
    return " - ".join(str(int(r['Numero'])) for _, r in df_sub.iterrows())

def get_arrivee(dfc):
    dc = dfc[dfc['classement'] > 0].sort_values('classement')
    return " - ".join(str(int(r['Numero'])) for _, r in dc.iterrows()) if not dc.empty else None

def eval_formula(df, formula_str):
    f_py = formula_str.replace('?', ' if ').replace(':', ' else ').replace('""', '0')
    def calc(row):
        ctx = row.to_dict()
        ctx.update({'log': np.log, 'sqrt': np.sqrt, 'max': max, 'min': min, 'abs': abs})
        try:
            return float(eval(f_py, {"__builtins__": {}}, ctx))
        except Exception:
            return 0.0
    return df.apply(calc, axis=1)

def safe_rapport(val):
    if val is None or str(val).strip() in ('', '0', '0.0', 'nan', 'None'):
        return 0.0
    s = str(val).replace(',', '.').strip()
    try:
        return float(s)
    except Exception:
        return 0.0

# --- FIX SAFE ACCESS (évite IndexError si moins de 3 chevaux) ---
def safe_num(df_sub, idx, col='Numero', default=0):
    try:
        if df_sub is None or len(df_sub) <= idx:
            return default
        v = df_sub.iloc[idx].get(col, default)
        return int(v) if pd.notna(v) else default
    except Exception:
        return default

def safe_float(df_sub, idx, col, default=0.0):
    try:
        if df_sub is None or len(df_sub) <= idx:
            return default
        v = df_sub.iloc[idx].get(col, default)
        return float(v) if pd.notna(v) else default
    except Exception:
        return default

# --- SIDEBAR ---
col_side, col_main = st.columns([1, 2])

with col_side:
    st.markdown("**📅 Période**")
    mode_date = st.radio("", ["1 jour", "Plage"], horizontal=True, label_visibility="collapsed")
    if mode_date == "1 jour":
        date_start = st.date_input("Date", value=pd.Timestamp.now())
        date_end = date_start
    else:
        date_start = st.date_input("Du", value=pd.Timestamp.now() - pd.Timedelta(days=7))
        date_end = st.date_input("Au", value=pd.Timestamp.now())

    st.divider()
    algos_df = run_query("SELECT * FROM algos")
    liste_algos = ["--- Nouveau ---"] + list(FORMULES_PRESET.keys()) + (algos_df['nom'].tolist() if not algos_df.empty else [])
    selected = st.selectbox("Algorithme :", liste_algos)
    mode_affichage = st.radio("Mode :", ["Simple (1 cheval)", "Duo (2 chevaux)", "Trio + Folie (3+1)", "Borda 4 chevaux"])

    st.divider()
    st.markdown("**🔍 Filtres**")

    _raw = run_query("SELECT DISTINCT hippodrome FROM selections WHERE date BETWEEN ? AND ?", (str(date_start), str(date_end)))
    all_hippos = sorted(_raw['hippodrome'].unique().tolist()) if not _raw.empty else []

    filter_hippo = st.multiselect("Hippodrome", all_hippos, default=[], placeholder="Tous")
    filter_disc = st.multiselect("Discipline", ["A - Attelé", "M - Monté", "P - Plat", "O - Obstacle"], default=[], placeholder="Toutes")
    filter_partants = st.slider("Nb Partants", 1, 20, (1, 20))

    st.divider()
    st.markdown("**⚙️ Réglages Folie**")
    folie_cote_min = st.slider("Cote min folie", 5, 30, 10)
    folie_taux_min = st.slider("Taux Placé min %", 0, 50, 20)

    # --- FILTRE CONFIANCE DUO ---
    if mode_affichage == "Duo (2 chevaux)":
        st.divider()
        st.markdown("**🎯 Filtre Confiance Duo**")
        filtre_confiance_on = st.toggle("Activer filtre", value=False)
        fc1, fc2 = st.columns(2)
        with fc1:
            seuil_concordance = st.slider("Concordance min", 0, 6, 4, help="0-6 : chevaux communs entre F, IA et H")
        with fc2:
            filtre_unanime = st.toggle("Unanimité F=IA=H", value=False, help="Ne jouer que si les 3 méthodes donnent le même duo")
    else:
        # Valeurs par défaut pour éviter NameError
        filtre_confiance_on = False
        seuil_concordance = 4
        filtre_unanime = False

current_nom, current_form = ("", "")
if selected in FORMULES_PRESET:
    current_nom, current_form = selected, FORMULES_PRESET[selected]
elif selected != "--- Nouveau ---":
    r = algos_df[algos_df['nom'] == selected].iloc[0]
    current_nom, current_form = r['nom'], r['formule']

with col_main:
    with st.container(border=True):
        nom_algo = st.text_input("Nom", value=current_nom)
        formule_raw = st.text_area("Formule", value=current_form, height=80)
        b1, b2, b3 = st.columns([1, 1, 2])
        if b1.button("💾 Sauver"):
            save_algo(nom_algo, formule_raw)
            st.rerun()
        if b2.button("🗑️ Effacer") and selected not in FORMULES_PRESET and selected != "--- Nouveau ---":
            delete_algo(selected)
            st.rerun()
        btn_run = b3.button("🚀 LANCER", type="primary", use_container_width=True)

# =====================================================
# MOTEUR
# =====================================================
if btn_run:
    raw_data = run_query(
        "SELECT id, date, hippodrome, course_num, numero, cheval, cote, json_data, classement FROM selections WHERE date BETWEEN ? AND ?",
        (str(date_start), str(date_end))
    )
    if raw_data.empty:
        st.warning("Aucune donnée.")
        st.stop()

    try:
        raw_data['_classement_int'] = raw_data['classement'].apply(parse_classement)
        raw_data['_course_norm'] = raw_data['course_num'].apply(normalize_course_num)
        raw_data['_dedup_key'] = (
            raw_data['date'].astype(str) + "_" +
            raw_data['hippodrome'].astype(str) + "_" +
            raw_data['_course_norm'] + "_" +
            raw_data['numero'].astype(str)
        )
        raw_data = (
            raw_data.sort_values('_classement_int', ascending=False)
                    .drop_duplicates(subset='_dedup_key', keep='first')
                    .drop(columns=['_dedup_key'])
        )

        data = []
        for _, r in raw_data.iterrows():
            d = json.loads(r['json_data']) if r['json_data'] else {}
            clean = {str(k).replace(' ', '_').replace('.', '').replace('-', '_'): v for k, v in d.items()}
            for k in list(clean.keys()):
                if 'Borda' in k and k != 'Borda':
                    clean['Borda'] = clean[k]
            cn = normalize_course_num(r['course_num'])
            id_c = f"{r['date']}_{r['hippodrome']}_{cn}".upper()
            val_classement = r['_classement_int']
            if val_classement == 0:
                rj = clean.get('Rank', clean.get('rank', None))
                if rj is not None:
                    val_classement = parse_classement(rj)
            clean.update({
                'Numero': int(r['numero']),
                'Cheval': r['cheval'],
                'ID_C': id_c,
                'hippodrome': r['hippodrome'],
                'Cote': r['cote'],
                'classement': val_classement,
                'date': str(r['date'])
            })
            data.append(clean)

        df = pd.DataFrame(data)
        df['classement'] = pd.to_numeric(df['classement'], errors='coerce').fillna(0).astype(int)

        for rc in ['Rapport_SG', 'Rapport_SP']:
            if rc in df.columns:
                df[rc] = df[rc].apply(safe_rapport)
            else:
                df[rc] = 0.0

        if 'discipline' not in df.columns:
            df['discipline'] = ''
        if 'nombre_partants' not in df.columns:
            df['nombre_partants'] = 0
        df['nombre_partants'] = pd.to_numeric(df['nombre_partants'].astype(str).str.strip(), errors='coerce').fillna(0).astype(int)

        if filter_hippo:
            df = df[df['hippodrome'].isin(filter_hippo)]
        if filter_disc:
            disc_codes = [d[0] for d in filter_disc]
            df = df[df['discipline'].astype(str).str.strip().str.upper().isin(disc_codes)]
        df = df[df['nombre_partants'].between(filter_partants[0], filter_partants[1])]

        if df.empty:
            st.warning("Aucune course après filtres.")
            st.stop()

        num_cols = [
            'IA_Trio', 'Borda', 'ELO_Cheval', 'ELO_Jockey', 'ELO_Entraineur',
            'ELO_Proprio', 'ELO_Eleveur', 'Note_IA_Decimale', 'Synergie_JCh',
            'Cote', 'Taux_Victoire', 'Taux_Place', 'Taux_Incident',
            'Sigma_Horse', 'Moy_Alloc', 'IA_Gagnant', 'IA_Couple', 'IA_Multi',
            'IA_Quinte', 'IMDC', 'Popularite', 'Evo_Popul', 'Repos',
            'Turf_Points', 'TPch_90', 'Moy_TPch_365', 'Moy_TPch_90',
            'TPJ_365', 'TPJ_90', 'Moy_TPJ_365', 'Moy_TPJ_90',
            'Cote_BZH', 'Courses_courues', 'nombre_victoire', 'nombre_place',
            'incident', 'distanceRecord_sec', 'Rang_J'
        ]
        for c in num_cols:
            if c in df.columns:
                df[c] = to_numeric_col(df[c])

        for tc in ['Taux_Victoire', 'Taux_Place', 'Taux_Incident']:
            if tc in df.columns and df[tc].max() <= 1.0:
                df[tc] = df[tc] * 100

        rank_desc = [
            'IA_Trio', 'Borda', 'ELO_Cheval', 'ELO_Jockey', 'ELO_Entraineur',
            'ELO_Proprio', 'ELO_Eleveur', 'Note_IA_Decimale', 'Synergie_JCh',
            'Taux_Victoire', 'Taux_Place', 'Turf_Points', 'TPch_90',
            'IA_Gagnant', 'IA_Couple', 'IA_Multi', 'IA_Quinte', 'Sigma_Horse'
        ]
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
            if c.endswith('_Rank'):
                df[c] = to_numeric_col(df[c])

        if 'IA_Trio_Rank' in df.columns and 'Borda_Rank' in df.columns:
            df['IA_Borda_Score'] = (1 / df['IA_Trio_Rank'].clip(lower=1)) + (1 / df['Borda_Rank'].clip(lower=1))
            df['IA_Borda_Rank'] = df.groupby('ID_C')['IA_Borda_Score'].rank(ascending=False, method='min').astype(int)

        df['SCORE'] = eval_formula(df, formule_raw)
        df['SCORE_Rank'] = df.groupby('ID_C')['SCORE'].rank(ascending=False, method='min').astype(int)

        for cid in df['ID_C'].unique():
            mask = df['ID_C'] == cid
            df_c = df[mask]
            s_min, s_max = df_c['SCORE'].min(), df_c['SCORE'].max()
            df.loc[mask, 'SCORE_Norm'] = (df_c['SCORE'] - s_min) / (s_max - s_min) if s_max > s_min else 0.5

            if 'IA_Borda_Score' in df_c.columns:
                ib_min, ib_max = df_c['IA_Borda_Score'].min(), df_c['IA_Borda_Score'].max()
                df.loc[mask, 'IA_Borda_Norm'] = (df_c['IA_Borda_Score'] - ib_min) / (ib_max - ib_min) if ib_max > ib_min else 0.5
            else:
                df.loc[mask, 'IA_Borda_Norm'] = 0.0

            cmin = df_c['Cote'].min() if 'Cote' in df_c.columns else 5
            w_ia, w_f = (0.65, 0.35) if cmin < 3 else ((0.55, 0.45) if cmin < 5 else (0.35, 0.65))
            df.loc[mask, 'HYBRIDE'] = w_f * df.loc[mask, 'SCORE_Norm'] + w_ia * df.loc[mask, 'IA_Borda_Norm']

        df['HYBRIDE_Rank'] = df.groupby('ID_C')['HYBRIDE'].rank(ascending=False, method='min').astype(int)

        st.divider()
        all_courses = sorted(df['ID_C'].unique())
        courses_avec = [c for c in all_courses if (df[df['ID_C'] == c]['classement'] > 0).any()]
        courses_sans = [c for c in all_courses if c not in courses_avec]

        discs_found = df['discipline'].astype(str).str.strip().str.upper().unique()
        disc_txt = ", ".join(DISC_MAP.get(d, d) for d in discs_found if d)
        st.caption(f"📊 {len(all_courses)} courses ({len(courses_avec)} terminées) | {disc_txt} | {filter_partants[0]}-{filter_partants[1]} partants")

        # =====================================================
        # BORDA 4
        # =====================================================
        if mode_affichage == "Borda 4 chevaux":
            if courses_avec:
                stats = {'couple_gagnant': 0, 'couple_place': 0, 'trio_ordre': 0, 'trio_desordre': 0, 'total': 0}
                rows_export = []
                for cid in courses_avec:
                    df_c = df[df['ID_C'] == cid]
                    if 'Borda' in df_c.columns and df_c['Borda'].sum() > 0:
                        top4_borda = df_c.nlargest(4, 'Borda')
                    elif 'Borda_Rank' in df_c.columns:
                        top4_borda = df_c.nsmallest(4, 'Borda_Rank')
                    else:
                        continue
                    nums_borda = [int(r['Numero']) for _, r in top4_borda.iterrows()]
                    arrivee_df = df_c[df_c['classement'] > 0].sort_values('classement')
                    if len(arrivee_df) < 3:
                        continue
                    arrivee = [int(r['Numero']) for _, r in arrivee_df.head(3).iterrows()]
                    top3_set = set(arrivee)
                    stats['total'] += 1
                    set_borda_4 = set(nums_borda[:4])
                    top2_arrivee = set(arrivee[:2])
                    couple_gagnant = len(set_borda_4 & top2_arrivee) >= 2
                    couple_place = len(set_borda_4 & top3_set) >= 2
                    if couple_gagnant:
                        stats['couple_gagnant'] += 1
                        stats['couple_place'] += 1
                        couple_ok = "🥇 Gagnant"
                    elif couple_place:
                        stats['couple_place'] += 1
                        couple_ok = "✅ Placé"
                    else:
                        couple_ok = "❌"
                    trio_ordre = len(nums_borda) >= 3 and nums_borda[:3] == arrivee[:3]
                    trio_desordre = len(set_borda_4 & top3_set) >= 3
                    if trio_ordre:
                        stats['trio_ordre'] += 1
                        stats['trio_desordre'] += 1
                        trio_ok = "🥇 Ordre"
                    elif trio_desordre:
                        stats['trio_desordre'] += 1
                        trio_ok = "✅ Désordre"
                    else:
                        trio_ok = "❌"
                    rows_export.append({
                        'Course': cid,
                        'Borda_1': nums_borda[0] if len(nums_borda) > 0 else 0,
                        'Borda_2': nums_borda[1] if len(nums_borda) > 1 else 0,
                        'Borda_3': nums_borda[2] if len(nums_borda) > 2 else 0,
                        'Borda_4': nums_borda[3] if len(nums_borda) > 3 else 0,
                        'Couplé': couple_ok,
                        'Trio': trio_ok,
                        'Arrivée': " - ".join(map(str, arrivee))
                    })

                st.markdown("### 📊 Performance Borda 4 chevaux")
                with st.container(border=True):
                    k1, k2, k3, k4 = st.columns(4)
                    t = stats['total']
                    p = lambda n: f"{round(n/t*100)}%" if t else "0%"
                    k1.metric("🥇 Couplé Gagnant", f"{stats['couple_gagnant']}/{t}", p(stats['couple_gagnant']))
                    k2.metric("✅ Couplé Placé", f"{stats['couple_place']}/{t}", p(stats['couple_place']))
                    k3.metric("🥇 Trio Ordre", f"{stats['trio_ordre']}/{t}", p(stats['trio_ordre']))
                    k4.metric("✅ Trio Désordre", f"{stats['trio_desordre']}/{t}", p(stats['trio_desordre']))

                st.divider()
                st.markdown(f"### 🏁 Détail ({len(courses_avec)})")
                for row in rows_export:
                    cid = row['Course']
                    df_c = df[df['ID_C'] == cid]
                    arrivee_nums = [int(x) for x in row['Arrivée'].split(' - ')]
                    top3_set = set(arrivee_nums)
                    borda_nums = [row['Borda_1'], row['Borda_2'], row['Borda_3'], row['Borda_4']]
                    icon = "🥇" if "Ordre" in row['Trio'] else ("✅" if "Désordre" in row['Trio'] or "Placé" in row['Couplé'] else "❌")
                    with st.container(border=True):
                        st.write(f"**{icon} {cid}**")
                        c1, c2 = st.columns([3, 2])
                        with c1:
                            st.markdown("**🔷 Top 4 Borda** — " + " — ".join([f":green[**{n}**]✓" if n in top3_set else f":red[**{n}**]✗" for n in borda_nums]))
                            st.caption(f"Couplé: {row['Couplé']} | Trio: {row['Trio']}")
                        with c2:
                            st.markdown(f"**🏁** ### {row['Arrivée']}")

            if courses_sans:
                st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
                for cid in courses_sans:
                    df_c = df[df['ID_C'] == cid]
                    if 'Borda' in df_c.columns and df_c['Borda'].sum() > 0:
                        top4 = df_c.nlargest(4, 'Borda')
                    elif 'Borda_Rank' in df_c.columns:
                        top4 = df_c.nsmallest(4, 'Borda_Rank')
                    else:
                        continue
                    with st.container(border=True):
                        st.write(f"**📍 {cid}**")
                        st.success(f"**🔷 Borda:** {' - '.join(str(int(r['Numero'])) for _, r in top4.iterrows())}")

            if courses_avec:
                st.download_button(
                    "📥 CSV Borda 4",
                    pd.DataFrame(rows_export).to_csv(index=False, sep=';').encode('utf-8'),
                    f"export_borda4_{date_start}_{date_end}.csv",
                    "text/csv",
                    use_container_width=True
                )

        # =====================================================
        # SIMPLE
        # =====================================================
        elif mode_affichage == "Simple (1 cheval)":
            if courses_avec:
                st_f = {'g': 0, 't3': 0, 'n': 0, 'mise_g': 0, 'gain_g': 0, 'mise_p': 0, 'gain_p': 0}
                st_ib = {'g': 0, 't3': 0, 'n': 0, 'mise_g': 0, 'gain_g': 0, 'mise_p': 0, 'gain_p': 0}
                st_hyb = {'g': 0, 't3': 0, 'n': 0, 'mise_g': 0, 'gain_g': 0, 'mise_p': 0, 'gain_p': 0}
                rows_disp = []

                for cid in courses_avec:
                    df_c = df[df['ID_C'] == cid]
                    top1 = set(df_c[df_c['classement'] == 1]['Numero'].astype(int).tolist())
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                    g_row = df_c[df_c['classement'] == 1].iloc[0] if not df_c[df_c['classement'] == 1].empty else None

                    bf = df_c.nlargest(1, 'SCORE').iloc[0]
                    nf = int(bf['Numero'])

                    bib = df_c.nsmallest(1, 'IA_Borda_Rank').iloc[0] if 'IA_Borda_Rank' in df_c.columns else df_c.iloc[0]
                    nib = int(bib['Numero'])

                    bh = df_c.nlargest(1, 'HYBRIDE').iloc[0]
                    nh = int(bh['Numero'])

                    for n, sx in [(nf, st_f), (nib, st_ib), (nh, st_hyb)]:
                        sx['n'] += 1
                        sx['mise_g'] += 1
                        sx['mise_p'] += 1
                        if n in top1:
                            sx['g'] += 1
                            cr = df_c[df_c['Numero'] == n]
                            if not cr.empty:
                                rsg = float(cr.iloc[0].get('Rapport_SG', 0) or 0)
                                sx['gain_g'] += rsg if rsg > 0 else (float(cr.iloc[0]['Cote']) if pd.notna(cr.iloc[0]['Cote']) else 0)
                        if n in top3:
                            sx['t3'] += 1
                            cr = df_c[df_c['Numero'] == n]
                            if not cr.empty:
                                rsp = float(cr.iloc[0].get('Rapport_SP', 0) or 0)
                                sx['gain_p'] += rsp if rsp > 0 else round((float(cr.iloc[0]['Cote']) if pd.notna(cr.iloc[0]['Cote']) else 0) / 3, 1)

                    def v(n):
                        return "🥇" if n in top1 else ("✅" if n in top3 else "❌")

                    rsg_real = float(g_row.get('Rapport_SG', 0) or 0) if g_row is not None else 0
                    rsp_real = float(g_row.get('Rapport_SP', 0) or 0) if g_row is not None else 0

                    rows_disp.append({
                        'Course': cid,
                        'Formule': f"{v(nf)} N°{nf}",
                        'IA+B': f"{v(nib)} N°{nib}",
                        'Hybride': f"{v(nh)} N°{nh}",
                        'Gagnant': f"N°{int(g_row['Numero'])} {g_row['Cheval']}" if g_row is not None else "?",
                        'Cote': round(float(g_row['Cote']), 1) if g_row is not None and pd.notna(g_row['Cote']) else 0,
                        'R.SG': rsg_real,
                        'R.SP': rsp_real
                    })

                st.markdown("### 📊 Simple — Trouver le gagnant")
                with st.container(border=True):
                    k1, k2, k3, k4, k5, k6, k7, k8, k9 = st.columns(9)
                    t = st_f['n']
                    p = lambda n: f"{round(n/t*100)}%" if t else "0%"
                    k1.metric("🎯 F Gagn.", f"{st_f['g']}/{t}", p(st_f['g']))
                    k2.metric("🎯 F Top3", f"{st_f['t3']}/{t}", p(st_f['t3']))
                    k3.metric("🎯 F Échec", f"{t-st_f['t3']}/{t}", p(t-st_f['t3']), delta_color="inverse")
                    k4.metric("🤖 IA Gagn.", f"{st_ib['g']}/{t}", p(st_ib['g']))
                    k5.metric("🤖 IA Top3", f"{st_ib['t3']}/{t}", p(st_ib['t3']))
                    k6.metric("🤖 IA Échec", f"{t-st_ib['t3']}/{t}", p(t-st_ib['t3']), delta_color="inverse")
                    k7.metric("⚡ H Gagn.", f"{st_hyb['g']}/{t}", p(st_hyb['g']))
                    k8.metric("⚡ H Top3", f"{st_hyb['t3']}/{t}", p(st_hyb['t3']))
                    k9.metric("⚡ H Échec", f"{t-st_hyb['t3']}/{t}", p(t-st_hyb['t3']), delta_color="inverse")

                st.markdown("### 💰 Bilan Financier (1€ par course)")
                with st.container(border=True):
                    c1, c2, c3 = st.columns(3)
                    for col, label, emoji, sx in [(c1, "Formule", "🎯", st_f), (c2, "IA+Borda", "🤖", st_ib), (c3, "Hybride", "⚡", st_hyb)]:
                        with col:
                            roi_g = round((sx['gain_g'] - sx['mise_g']) / sx['mise_g'] * 100, 1) if sx['mise_g'] > 0 else 0
                            roi_p = round((sx['gain_p'] - sx['mise_p']) / sx['mise_p'] * 100, 1) if sx['mise_p'] > 0 else 0
                            benef_g = sx['gain_g'] - sx['mise_g']
                            benef_p = sx['gain_p'] - sx['mise_p']
                            st.markdown(f"**{emoji} {label}**")
                            st.markdown(f"🏆 **SG** : {sx['mise_g']:.0f}€ → {sx['gain_g']:.1f}€ → **{'🟢' if benef_g >= 0 else '🔴'} {benef_g:+.1f}€** (ROI {roi_g:+.1f}%)")
                            st.markdown(f"🥉 **SP** : {sx['mise_p']:.0f}€ → {sx['gain_p']:.1f}€ → **{'🟢' if benef_p >= 0 else '🔴'} {benef_p:+.1f}€** (ROI {roi_p:+.1f}%)")

                st.divider()
                st.dataframe(pd.DataFrame(rows_disp), use_container_width=True, hide_index=True)

            if courses_sans:
                st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
                wr = []
                for cid in courses_sans:
                    df_c = df[df['ID_C'] == cid]
                    bf = df_c.nlargest(1, 'SCORE').iloc[0]
                    bib = df_c.nsmallest(1, 'IA_Borda_Rank').iloc[0] if 'IA_Borda_Rank' in df_c.columns else df_c.iloc[0]
                    bh = df_c.nlargest(1, 'HYBRIDE').iloc[0]
                    wr.append({
                        'Course': cid,
                        'Formule': f"N°{int(bf['Numero'])} {bf['Cheval']}",
                        'IA+B': f"N°{int(bib['Numero'])} {bib['Cheval']}",
                        'Hybride': f"N°{int(bh['Numero'])} {bh['Cheval']}"
                    })
                st.dataframe(pd.DataFrame(wr), use_container_width=True, hide_index=True)

            if courses_avec:
                st.download_button(
                    "📥 CSV",
                    pd.DataFrame(rows_disp).to_csv(index=False, sep=';').encode('utf-8'),
                    f"export_simple_{date_start}_{date_end}.csv",
                    "text/csv",
                    use_container_width=True
                )

        # =====================================================
        # DUO AVEC FILTRE CONCORDANCE
        # =====================================================
        elif mode_affichage == "Duo (2 chevaux)":
            if courses_avec:
                st_f = {'cg': 0, 'cp': 0, 'n': 0, 'skip': 0, 'total': 0}
                st_ib = {'cg': 0, 'cp': 0, 'n': 0}
                st_hyb = {'cg': 0, 'cp': 0, 'n': 0}
                rows_export = []

                for cid in courses_avec:
                    df_c = df[df['ID_C'] == cid]
                    top2 = set(df_c[df_c['classement'].between(1, 2)]['Numero'].astype(int).tolist())
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())

                    duo_f = df_c.nlargest(2, 'SCORE')
                    sf = set(duo_f['Numero'].astype(int).tolist())

                    duo_ib = df_c.nsmallest(2, 'IA_Borda_Rank') if 'IA_Borda_Rank' in df_c.columns else df_c.head(2)
                    sib = set(duo_ib['Numero'].astype(int).tolist())

                    duo_hyb = df_c.nlargest(2, 'HYBRIDE')
                    sh = set(duo_hyb['Numero'].astype(int).tolist())

                    # --- CONCORDANCE ---
                    concordance, detail = calculer_confiance_duo(df_c, 'SCORE')
                    unanime = detail.get('unanime', False)

                    # Filtre
                    if filtre_confiance_on:
                        if filtre_unanime:
                            course_jouee = unanime
                        else:
                            course_jouee = concordance >= seuil_concordance
                    else:
                        course_jouee = True

                    st_f['total'] += 1
                    cg_f = sf.issubset(top2)
                    cp_f = sf.issubset(top3)

                    if course_jouee:
                        st_f['n'] += 1
                        if cg_f:
                            st_f['cg'] += 1
                        if cp_f:
                            st_f['cp'] += 1
                    else:
                        st_f['skip'] += 1

                    for sx, nums in [(st_ib, sib), (st_hyb, sh)]:
                        sx['n'] += 1
                        if nums.issubset(top2):
                            sx['cg'] += 1
                        if nums.issubset(top3):
                            sx['cp'] += 1

                    arrivee = get_arrivee(df_c)
                    cg_ib = sib.issubset(top2)
                    cp_ib = sib.issubset(top3)
                    cg_h = sh.issubset(top2)
                    cp_h = sh.issubset(top3)

                    # Icône
                    if unanime:
                        conf_icon = "🟢"
                    elif concordance >= 4:
                        conf_icon = "🟡"
                    else:
                        conf_icon = "🔴"

                    rows_export.append({
                        'Course': cid,
                        'Jouee': '✅' if course_jouee else '⏭️',
                        'Conf': conf_icon,
                        'Concordance': concordance,
                        'Unanime': '✅' if unanime else '',
                        'F_N1': safe_num(duo_f, 0),
                        'F_N2': safe_num(duo_f, 1),
                        'F_CG': "OUI" if cg_f else "NON",
                        'F_CP': "OUI" if cp_f else "NON",
                        'IB_CG': "OUI" if cg_ib else "NON",
                        'IB_CP': "OUI" if cp_ib else "NON",
                        'H_CG': "OUI" if cg_h else "NON",
                        'H_CP': "OUI" if cp_h else "NON",
                        'Arrivee': arrivee or ""
                    })

                st.markdown("### 📊 Duo — Couplé Gagnant / Placé")

                if filtre_confiance_on:
                    pct_jouees = round(st_f['n'] / st_f['total'] * 100) if st_f['total'] > 0 else 0
                    filtre_txt = "Unanimité F=IA=H" if filtre_unanime else f"Concordance ≥ {seuil_concordance}"
                    st.info(f"🎯 **Filtre actif** : {st_f['n']} jouées / {st_f['total']} total ({st_f['skip']} skip = {100-pct_jouees}%) — {filtre_txt}")

                with st.container(border=True):
                    k1, k2, k3, k4, k5, k6 = st.columns(6)
                    t_f = max(st_f['n'], 1)
                    t_all = max(st_ib['n'], 1)
                    p = lambda n, t: f"{round(n/t*100)}%" if t else "0%"
                    k1.metric("🎯 F CG", f"{st_f['cg']}/{st_f['n']}", p(st_f['cg'], t_f))
                    k2.metric("🎯 F CP", f"{st_f['cp']}/{st_f['n']}", p(st_f['cp'], t_f))
                    k3.metric("🤖 IA CG", f"{st_ib['cg']}/{st_ib['n']}", p(st_ib['cg'], t_all))
                    k4.metric("🤖 IA CP", f"{st_ib['cp']}/{st_ib['n']}", p(st_ib['cp'], t_all))
                    k5.metric("⚡ H CG", f"{st_hyb['cg']}/{st_hyb['n']}", p(st_hyb['cg'], t_all))
                    k6.metric("⚡ H CP", f"{st_hyb['cp']}/{st_hyb['n']}", p(st_hyb['cp'], t_all))

                st.divider()

                courses_jouees = [r for r in rows_export if r['Jouee'] == '✅']
                courses_skippees = [r for r in rows_export if r['Jouee'] == '⏭️']

                st.markdown(f"### 🏁 Courses jouées ({len(courses_jouees)})")
                for row in courses_jouees:
                    cid = row['Course']
                    df_c = df[df['ID_C'] == cid]
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())

                    duo_f = df_c.nlargest(2, 'SCORE')
                    duo_ib = df_c.nsmallest(2, 'IA_Borda_Rank') if 'IA_Borda_Rank' in df_c.columns else df_c.head(2)
                    duo_hyb = df_c.nlargest(2, 'HYBRIDE')

                    cg_f = row['F_CG'] == "OUI"
                    cp_f = row['F_CP'] == "OUI"
                    icon = "🥇" if cg_f else ("✅" if cp_f else "❌")

                    with st.container(border=True):
                        st.write(f"**{icon} {row['Conf']} {cid}** — Conc: {row['Concordance']} {row['Unanime']}")
                        c1, c2, c3, c4 = st.columns([3, 3, 3, 3])
                        with c1:
                            nlist = [int(r['Numero']) for _, r in duo_f.iterrows()]
                            v = "🥇CG" if cg_f else ("✅CP" if cp_f else "❌")
                            st.success(f"**🎯 F** {v}\n{colored_nums(nlist, top3)}")
                        with c2:
                            nlist = [int(r['Numero']) for _, r in duo_ib.iterrows()]
                            v = "🥇CG" if row['IB_CG'] == "OUI" else ("✅CP" if row['IB_CP'] == "OUI" else "❌")
                            st.warning(f"**🤖 IA** {v}\n{colored_nums(nlist, top3)}")
                        with c3:
                            nlist = [int(r['Numero']) for _, r in duo_hyb.iterrows()]
                            v = "🥇CG" if row['H_CG'] == "OUI" else ("✅CP" if row['H_CP'] == "OUI" else "❌")
                            st.info(f"**⚡ H** {v}\n{colored_nums(nlist, top3)}")
                        with c4:
                            st.write(f"**🏁**\n### {row['Arrivee']}")

                if courses_skippees and filtre_confiance_on:
                    with st.expander(f"⏭️ Courses skippées ({len(courses_skippees)})", expanded=False):
                        for row in courses_skippees:
                            cid = row['Course']
                            df_c = df[df['ID_C'] == cid]
                            top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                            duo_f = df_c.nlargest(2, 'SCORE')
                            cg_f = row['F_CG'] == "OUI"
                            cp_f = row['F_CP'] == "OUI"
                            result_icon = "🥇" if cg_f else ("✅" if cp_f else "❌")
                            nlist = [int(r['Numero']) for _, r in duo_f.iterrows()]
                            st.caption(f"{result_icon} {cid} — F: {colored_nums(nlist, top3)} — Conc: {row['Concordance']} — Arrivée: {row['Arrivee']}")

            if courses_sans:
                st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
                for cid in courses_sans:
                    df_c = df[df['ID_C'] == cid]
                    duo_f = df_c.nlargest(2, 'SCORE')
                    duo_hyb = df_c.nlargest(2, 'HYBRIDE')
                    concordance, detail = calculer_confiance_duo(df_c, 'SCORE')
                    unanime = detail.get('unanime', False)

                    if filtre_confiance_on:
                        jouable = (unanime if filtre_unanime else concordance >= seuil_concordance)
                    else:
                        jouable = True

                    if unanime:
                        conf_icon = "🟢"
                    elif concordance >= 4:
                        conf_icon = "🟡"
                    else:
                        conf_icon = "🔴"

                    with st.container(border=True):
                        status = "🎯 JOUER" if jouable else "⏭️ SKIP"
                        st.write(f"**{conf_icon} {cid}** — {status} — Conc: {concordance} {'✅ Unanime' if unanime else ''}")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.success(f"**🎯 F** {nums_str(duo_f)}")
                        with c2:
                            st.info(f"**⚡ H** {nums_str(duo_hyb)}")

            if courses_avec:
                st.download_button(
                    "📥 CSV Duo",
                    pd.DataFrame(rows_export).to_csv(index=False, sep=';').encode('utf-8'),
                    f"export_duo_{date_start}_{date_end}.csv",
                    "text/csv",
                    use_container_width=True
                )

        # =====================================================
        # TRIO
        # =====================================================
        else:
            if courses_avec:
                st_f = {'t3_2': 0, 't3_3': 0, 'folie_t3': 0, 'folie_n': 0, 'n': 0, 'mise': 0, 'gains_g': 0, 'gains_p': 0}
                st_ib = {'t3_2': 0, 't3_3': 0, 'folie_t3': 0, 'folie_n': 0, 'n': 0}
                st_hyb = {'t3_2': 0, 't3_3': 0, 'folie_t3': 0, 'folie_n': 0, 'n': 0, 'mise': 0, 'gains_g': 0, 'gains_p': 0}
                rows_export = []

                for cid in courses_avec:
                    df_c = df[df['ID_C'] == cid]
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                    top1 = set(df_c[df_c['classement'] == 1]['Numero'].astype(int).tolist())

                    trio_f = df_c.nlargest(3, 'SCORE')
                    nums_f = set(trio_f['Numero'].astype(int).tolist())
                    folie_f = get_folie_v2(df_c, nums_f, 'score', folie_cote_min, folie_taux_min)

                    trio_ib = df_c.nsmallest(3, 'IA_Borda_Rank') if 'IA_Borda_Rank' in df_c.columns else df_c.head(3)
                    nums_ib = set(trio_ib['Numero'].astype(int).tolist())
                    folie_ib = get_folie_v2(df_c, nums_ib, 'elo', folie_cote_min, folie_taux_min)

                    trio_hyb = df_c.nlargest(3, 'HYBRIDE')
                    nums_hyb = set(trio_hyb['Numero'].astype(int).tolist())
                    folie_hyb = get_folie_v2(df_c, nums_hyb, 'score', folie_cote_min, folie_taux_min)

                    confiance = get_confiance([safe_float(trio_f, i, 'SCORE', 0.0) for i in range(3)])

                    for td, sx, fd in [(trio_f, st_f, folie_f), (trio_ib, st_ib, folie_ib), (trio_hyb, st_hyb, folie_hyb)]:
                        nums = set(td['Numero'].astype(int).tolist()) if len(td) else set()
                        sx['n'] += 1
                        hit = len(nums & top3)
                        if hit >= 2:
                            sx['t3_2'] += 1
                        if hit == 3:
                            sx['t3_3'] += 1
                        if not fd.empty:
                            sx['folie_n'] += 1
                            if int(fd.iloc[0]['Numero']) in top3:
                                sx['folie_t3'] += 1

                    for td, sx in [(trio_f, st_f), (trio_hyb, st_hyb)]:
                        if len(td):
                            b1n = safe_num(td, 0)
                            b1c = float(td.iloc[0]['Cote']) if pd.notna(td.iloc[0].get('Cote', np.nan)) else 0
                            sx['mise'] += 2
                            if b1n in top1 and b1c > 0:
                                sx['gains_g'] += 2 * b1c
                            for _, b in td.iterrows():
                                sx['mise'] += 1
                                bc = float(b.get('Cote', 0)) if pd.notna(b.get('Cote', np.nan)) else 0
                                if int(b['Numero']) in top3 and bc > 0:
                                    sx['gains_p'] += bc / 3

                    hit_f = len(nums_f & top3)
                    hit_h = len(nums_hyb & top3)
                    arrivee = get_arrivee(df_c)

                    def fi(fd):
                        if fd.empty:
                            return 0, 0, ""
                        fn = int(fd.iloc[0]['Numero'])
                        fc = round(float(fd.iloc[0]['Cote']), 1) if pd.notna(fd.iloc[0].get('Cote', np.nan)) else 0
                        return fn, fc, "OUI" if fn in top3 else "NON"

                    ff_n, ff_c, ff_ok = fi(folie_f)
                    fh_n, fh_c, fh_ok = fi(folie_hyb)

                    # --- FIX: safe access même si trio_f n'a pas 3 lignes ---
                    rows_export.append({
                        'Course': cid,
                        'Conf': confiance,
                        'F_N1': safe_num(trio_f, 0),
                        'F_N2': safe_num(trio_f, 1),
                        'F_N3': safe_num(trio_f, 2),
                        'F_Hit': f"{hit_f}/3",
                        'F_Folie': ff_n,
                        'F_Folie_C': ff_c,
                        'F_Folie_OK': ff_ok,
                        'H_Hit': f"{hit_h}/3",
                        'H_Folie': fh_n,
                        'H_Folie_C': fh_c,
                        'H_Folie_OK': fh_ok,
                        'Arrivee': arrivee or ""
                    })

                st.markdown("### 📊 Trio + Folie")

                def show_kpi(lbl, em, sx):
                    with st.container(border=True):
                        st.markdown(f"**{em} {lbl}**")
                        nc = 5 if 'mise' in sx else 3
                        cols = st.columns(nc)
                        t = sx['n']
                        p = lambda n: f"{round(n/t*100)}%" if t else "0%"
                        cols[0].metric("2+/3", f"{sx['t3_2']}/{t}", p(sx['t3_2']))
                        cols[1].metric("3/3", f"{sx['t3_3']}/{t}", p(sx['t3_3']))
                        fn = sx['folie_n']
                        fp = lambda n: f"{round(n/fn*100)}%" if fn else "0%"
                        cols[2].metric("🔥Folie", f"{sx['folie_t3']}/{fn}", fp(sx['folie_t3']))
                        if 'mise' in sx and nc >= 5:
                            gt = sx['gains_g'] + sx['gains_p']
                            roi = round((gt - sx['mise']) / sx['mise'] * 100, 1) if sx['mise'] > 0 else 0
                            cols[3].metric("💰Mise", f"{sx['mise']:.0f}€")
                            cols[4].metric("📈ROI", f"{roi}%", f"{gt - sx['mise']:+.1f}€", delta_color="normal" if roi >= 0 else "inverse")

                show_kpi("Formule", "🎯", st_f)
                show_kpi("IA+Borda", "🤖", st_ib)
                show_kpi("Hybride", "⚡", st_hyb)

                st.divider()
                st.markdown(f"### 🏁 Courses ({len(courses_avec)})")
                for row in rows_export:
                    cid = row['Course']
                    df_c = df[df['ID_C'] == cid]
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())

                    trio_f = df_c.nlargest(3, 'SCORE')
                    trio_hyb = df_c.nlargest(3, 'HYBRIDE')

                    folie_f = get_folie_v2(df_c, set(trio_f['Numero'].astype(int).tolist()), 'score', folie_cote_min, folie_taux_min)
                    folie_hyb = get_folie_v2(df_c, set(trio_hyb['Numero'].astype(int).tolist()), 'score', folie_cote_min, folie_taux_min)

                    hf = int(str(row['F_Hit']).split('/')[0]) if row.get('F_Hit') else 0
                    hh = int(str(row['H_Hit']).split('/')[0]) if row.get('H_Hit') else 0
                    ok = max(hf, hh) >= 2
                    icon = "🥇" if max(hf, hh) == 3 else ("✅" if ok else "❌")

                    with st.container(border=True):
                        st.write(f"**{icon} {cid}** {row['Conf']} F:{row['F_Hit']} H:{row['H_Hit']}")
                        c1, c2, c3 = st.columns([4, 4, 4])
                        with c1:
                            nl = [int(r['Numero']) for _, r in trio_f.iterrows()]
                            ft = ""
                            if not folie_f.empty:
                                fn = int(folie_f.iloc[0]['Numero'])
                                fc = float(folie_f.iloc[0]['Cote']) if pd.notna(folie_f.iloc[0].get('Cote', np.nan)) else 0
                                ft = f"\n🔥{fn}(C:{fc}){'✓' if fn in top3 else '✗'}"
                            st.success(f"**🎯F** {row['F_Hit']}\n{colored_nums(nl, top3)}{ft}")
                        with c2:
                            nl = [int(r['Numero']) for _, r in trio_hyb.iterrows()]
                            ft = ""
                            if not folie_hyb.empty:
                                fn = int(folie_hyb.iloc[0]['Numero'])
                                fc = float(folie_hyb.iloc[0]['Cote']) if pd.notna(folie_hyb.iloc[0].get('Cote', np.nan)) else 0
                                ft = f"\n🔥{fn}(C:{fc}){'✓' if fn in top3 else '✗'}"
                            st.info(f"**⚡H** {row['H_Hit']}\n{colored_nums(nl, top3)}{ft}")
                        with c3:
                            st.warning(f"**🏁**\n### {row['Arrivee']}")

            if courses_sans:
                st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
                for cid in courses_sans:
                    df_c = df[df['ID_C'] == cid]
                    trio_f = df_c.nlargest(3, 'SCORE')
                    trio_hyb = df_c.nlargest(3, 'HYBRIDE')
                    folie_f = get_folie_v2(df_c, set(trio_f['Numero'].astype(int).tolist()), 'score', folie_cote_min, folie_taux_min)
                    conf = get_confiance([safe_float(trio_f, i, 'SCORE', 0.0) for i in range(3)])
                    with st.container(border=True):
                        st.write(f"**📍{cid}** {conf}")
                        c1, c2 = st.columns(2)
                        with c1:
                            txt = nums_str(trio_f)
                            if not folie_f.empty:
                                txt += f"\n🔥N°{int(folie_f.iloc[0]['Numero'])}(C:{round(float(folie_f.iloc[0]['Cote']), 1)})"
                            st.success(f"**🎯F**\n### {txt}")
                        with c2:
                            st.info(f"**⚡H**\n### {nums_str(trio_hyb)}")

            if courses_avec:
                st.download_button(
                    "📥 CSV Trio",
                    pd.DataFrame(rows_export).to_csv(index=False, sep=';').encode('utf-8'),
                    f"export_trio_{date_start}_{date_end}.csv",
                    "text/csv",
                    use_container_width=True
                )

    except Exception as e:
        st.error(f"Erreur : {e}")
        import traceback
        st.code(traceback.format_exc())
