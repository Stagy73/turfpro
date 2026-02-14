"""
engine.py — Moteur Algo Builder
Chargement données, nettoyage, calcul des rangs, scores, hybride.
"""
import pandas as pd
import numpy as np
import json
import re


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


def safe_rapport(val):
    if val is None or str(val).strip() in ('', '0', '0.0', 'nan', 'None'):
        return 0.0
    s = str(val).replace(',', '.').strip()
    try:
        return float(s)
    except Exception:
        return 0.0


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


def charger_donnees(run_query, date_start, date_end):
    """Charge les données brutes depuis la BDD."""
    raw_data = run_query(
        "SELECT id, date, hippodrome, course_num, numero, cheval, cote, json_data, classement "
        "FROM selections WHERE date BETWEEN ? AND ?",
        (str(date_start), str(date_end))
    )
    return raw_data


def preparer_dataframe(raw_data):
    """Transforme raw_data en DataFrame nettoyé avec colonnes numériques et rangs."""
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

    # Rapports
    for rc in ['Rapport_SG', 'Rapport_SP']:
        if rc in df.columns:
            df[rc] = df[rc].apply(safe_rapport)
        else:
            df[rc] = 0.0

    # Discipline & partants
    if 'discipline' not in df.columns:
        df['discipline'] = ''
    if 'nombre_partants' not in df.columns:
        df['nombre_partants'] = 0
    df['nombre_partants'] = pd.to_numeric(
        df['nombre_partants'].astype(str).str.strip(), errors='coerce'
    ).fillna(0).astype(int)

    return df


def appliquer_filtres(df, filter_hippo, filter_disc, filter_partants):
    """Applique les filtres hippodrome, discipline, nb partants."""
    if filter_hippo:
        df = df[df['hippodrome'].isin(filter_hippo)]
    if filter_disc:
        disc_codes = [d[0] for d in filter_disc]
        df = df[df['discipline'].astype(str).str.strip().str.upper().isin(disc_codes)]
    df = df[df['nombre_partants'].between(filter_partants[0], filter_partants[1])]
    return df


def calculer_colonnes(df):
    """Nettoie les colonnes numériques et calcule tous les rangs."""
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

    # Rangs desc (plus c'est grand = rang 1)
    rank_desc = [
        'IA_Trio', 'Borda', 'ELO_Cheval', 'ELO_Jockey', 'ELO_Entraineur',
        'ELO_Proprio', 'ELO_Eleveur', 'Note_IA_Decimale', 'Synergie_JCh',
        'Taux_Victoire', 'Taux_Place', 'Turf_Points', 'TPch_90',
        'IA_Gagnant', 'IA_Couple', 'IA_Multi', 'IA_Quinte', 'Sigma_Horse',
        'Popularite'
    ]
    for c in rank_desc:
        cr = f"{c}_Rank"
        if c in df.columns and cr not in df.columns:
            df[cr] = df.groupby('ID_C')[c].rank(ascending=False, method='min')
        elif cr in df.columns:
            df[cr] = to_numeric_col(df[cr])

    # Rangs asc (plus c'est petit = rang 1)
    for c in ['Cote', 'Cote_BZH']:
        cr = f"{c}_Rank"
        if c in df.columns and cr not in df.columns:
            df[cr] = df.groupby('ID_C')[c].rank(ascending=True, method='min')
        elif cr in df.columns:
            df[cr] = to_numeric_col(df[cr])

    for c in df.columns:
        if c.endswith('_Rank'):
            df[c] = to_numeric_col(df[c])

    # IA_Borda combiné
    if 'IA_Trio_Rank' in df.columns and 'Borda_Rank' in df.columns:
        df['IA_Borda_Score'] = (1 / df['IA_Trio_Rank'].clip(lower=1)) + (1 / df['Borda_Rank'].clip(lower=1))
        df['IA_Borda_Rank'] = df.groupby('ID_C')['IA_Borda_Score'].rank(ascending=False, method='min').astype(int)

    return df


def calculer_scores(df, formule_raw):
    """Calcule SCORE, SCORE_Rank, HYBRIDE, HYBRIDE_Rank."""
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
    return df


def get_courses(df):
    """Retourne all_courses, courses_avec (terminées), courses_sans (en attente)."""
    all_courses = sorted(df['ID_C'].unique())
    courses_avec = [c for c in all_courses if (df[df['ID_C'] == c]['classement'] > 0).any()]
    courses_sans = [c for c in all_courses if c not in courses_avec]
    return all_courses, courses_avec, courses_sans