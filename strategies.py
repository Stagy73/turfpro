"""
strategies.py — Fonctions de stratégie pour Algo Builder
Concordance F/IA/H pour tous les modes
"""
import pandas as pd
import numpy as np


# =====================================================
# CONCORDANCE DUO (2 chevaux)
# =====================================================
def calculer_confiance_duo(df_course, col_score='SCORE'):
    if df_course is None or df_course.empty or len(df_course) < 3:
        return 0, {}
    duo_f = set(df_course.nlargest(2, col_score)['Numero'].astype(int).tolist())
    if 'IA_Borda_Rank' in df_course.columns:
        duo_ia = set(df_course.nsmallest(2, 'IA_Borda_Rank')['Numero'].astype(int).tolist())
    elif 'IA_Couple_Rank' in df_course.columns:
        duo_ia = set(df_course.nsmallest(2, 'IA_Couple_Rank')['Numero'].astype(int).tolist())
    else:
        duo_ia = set()
    if 'HYBRIDE' in df_course.columns:
        duo_h = set(df_course.nlargest(2, 'HYBRIDE')['Numero'].astype(int).tolist())
    else:
        duo_h = set()
    f_ia = len(duo_f & duo_ia)
    f_h = len(duo_f & duo_h)
    ia_h = len(duo_ia & duo_h)
    concordance = f_ia + f_h + ia_h  # 0-6
    unanime = (duo_f == duo_ia == duo_h) if duo_ia and duo_h else False
    detail = {
        'duo_f': duo_f, 'duo_ia': duo_ia, 'duo_h': duo_h,
        'f_ia': f_ia, 'f_h': f_h, 'ia_h': ia_h,
        'unanime': unanime,
        'nb_uniques': len(duo_f | duo_ia | duo_h),
        'chevaux_consensus': duo_f & duo_ia & duo_h if duo_ia and duo_h else set(),
    }
    return concordance, detail


# =====================================================
# CONCORDANCE SIMPLE (1 cheval)
# Combine : accord F/IA/H sur le N°1 + écart de score
# Score 0-5 : accord (0-3) + bonus écart (0-2)
# =====================================================
def calculer_confiance_simple(df_course, col_score='SCORE'):
    if df_course is None or df_course.empty or len(df_course) < 2:
        return 0, {}
    n1_f = int(df_course.nlargest(1, col_score).iloc[0]['Numero'])
    if 'IA_Borda_Rank' in df_course.columns:
        n1_ia = int(df_course.nsmallest(1, 'IA_Borda_Rank').iloc[0]['Numero'])
    elif 'IA_Gagnant' in df_course.columns:
        n1_ia = int(df_course.nlargest(1, 'IA_Gagnant').iloc[0]['Numero'])
    else:
        n1_ia = -1
    if 'HYBRIDE' in df_course.columns:
        n1_h = int(df_course.nlargest(1, 'HYBRIDE').iloc[0]['Numero'])
    else:
        n1_h = -1

    # Accord entre méthodes (0-3)
    accord = 0
    if n1_f == n1_ia:
        accord += 1
    if n1_f == n1_h:
        accord += 1
    if n1_ia == n1_h and n1_ia != -1:
        accord += 1
    unanime = (n1_f == n1_ia == n1_h) and n1_ia != -1

    # Écart de score entre N°1 et N°2 (bonus 0-2)
    scores_sorted = df_course[col_score].sort_values(ascending=False).values
    if len(scores_sorted) >= 2 and scores_sorted[0] != 0:
        ecart_pct = (scores_sorted[0] - scores_sorted[1]) / abs(scores_sorted[0]) * 100
    else:
        ecart_pct = 0
    bonus_ecart = 2 if ecart_pct > 20 else (1 if ecart_pct > 10 else 0)

    concordance = accord + bonus_ecart  # 0-5
    detail = {
        'n1_f': n1_f, 'n1_ia': n1_ia, 'n1_h': n1_h,
        'unanime': unanime, 'ecart_pct': round(ecart_pct, 1),
        'accord': accord, 'bonus_ecart': bonus_ecart,
    }
    return concordance, detail


# =====================================================
# CONCORDANCE TRIO (3 chevaux)
# Combien de chevaux communs entre les top3 F, IA, H ?
# concordance 0-9 : 9=unanime (3 paires * 3 chevaux communs)
# =====================================================
def calculer_confiance_trio(df_course, col_score='SCORE'):
    if df_course is None or df_course.empty or len(df_course) < 4:
        return 0, {}
    trio_f = set(df_course.nlargest(3, col_score)['Numero'].astype(int).tolist())
    if 'IA_Borda_Rank' in df_course.columns:
        trio_ia = set(df_course.nsmallest(3, 'IA_Borda_Rank')['Numero'].astype(int).tolist())
    else:
        trio_ia = set()
    if 'HYBRIDE' in df_course.columns:
        trio_h = set(df_course.nlargest(3, 'HYBRIDE')['Numero'].astype(int).tolist())
    else:
        trio_h = set()
    f_ia = len(trio_f & trio_ia)
    f_h = len(trio_f & trio_h)
    ia_h = len(trio_ia & trio_h)
    concordance = f_ia + f_h + ia_h  # 0-9
    unanime = (trio_f == trio_ia == trio_h) if trio_ia and trio_h else False
    detail = {
        'trio_f': trio_f, 'trio_ia': trio_ia, 'trio_h': trio_h,
        'f_ia': f_ia, 'f_h': f_h, 'ia_h': ia_h,
        'unanime': unanime,
    }
    return concordance, detail


# =====================================================
# CONCORDANCE BORDA4 (4 chevaux)
# Combien de chevaux Borda4 sont aussi dans top4 F et top4 H ?
# concordance 0-8
# =====================================================
def calculer_confiance_borda4(df_course, col_score='SCORE'):
    if df_course is None or df_course.empty or len(df_course) < 5:
        return 0, {}
    if 'Borda' in df_course.columns and df_course['Borda'].sum() > 0:
        top4_borda = set(df_course.nlargest(4, 'Borda')['Numero'].astype(int).tolist())
    elif 'Borda_Rank' in df_course.columns:
        top4_borda = set(df_course.nsmallest(4, 'Borda_Rank')['Numero'].astype(int).tolist())
    else:
        return 0, {}
    top4_f = set(df_course.nlargest(4, col_score)['Numero'].astype(int).tolist())
    if 'HYBRIDE' in df_course.columns:
        top4_h = set(df_course.nlargest(4, 'HYBRIDE')['Numero'].astype(int).tolist())
    else:
        top4_h = set()
    b_f = len(top4_borda & top4_f)
    b_h = len(top4_borda & top4_h)
    concordance = b_f + b_h  # 0-8
    unanime = (top4_borda == top4_f == top4_h) if top4_h else False
    detail = {'top4_borda': top4_borda, 'top4_f': top4_f, 'top4_h': top4_h, 'unanime': unanime}
    return concordance, detail


# =====================================================
# PASTILLE COMMUNE
# =====================================================
def get_pastille_simple(concordance, unanime):
    """Simple : 0-5 (accord + écart). Haute=unanime+écart, Moyenne=accord partiel, Basse=désaccord."""
    if concordance >= 4:
        return "🟢", "Haute"
    elif concordance >= 2:
        return "🟡", "Moyenne"
    else:
        return "🔴", "Basse"


def get_pastille_duo(concordance, unanime):
    """Duo : 0-6, unanime si F=IA=H."""
    if unanime:
        return "🟢", "Haute"
    elif concordance >= 4:
        return "🟡", "Moyenne"
    else:
        return "🔴", "Basse"


def get_pastille_trio(concordance, unanime):
    """Trio : 0-9, unanime si les 3 méthodes = même trio."""
    if unanime:
        return "🟢", "Haute"
    elif concordance >= 6:
        return "🟡", "Moyenne"
    else:
        return "🔴", "Basse"


def get_pastille_borda4(concordance, unanime):
    """Borda4 : 0-8."""
    if unanime:
        return "🟢", "Haute"
    elif concordance >= 6:
        return "🟡", "Moyenne"
    else:
        return "🔴", "Basse"


# =====================================================
# UTILITAIRES
# =====================================================
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


def calculer_score_couple(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'Note_IA_Decimale' in df.columns and 'Synergie_JCh_Rank' in df.columns:
        df['score_potentiel'] = (df['Note_IA_Decimale'] * 0.7) + (20 - df['Synergie_JCh_Rank'])
    else:
        df['score_potentiel'] = 0
    return df


def detecter_trio(df_course):
    if df_course is None or df_course.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    if 'IA_Trio_Rank' in df_course.columns:
        bases = df_course.nsmallest(2, 'IA_Trio_Rank')
    else:
        bases = df_course.head(2)
    restant = df_course[~df_course['Numero'].isin(bases['Numero'])]
    if 'Borda_Rank' in restant.columns:
        outsiders = restant.nsmallest(2, 'Borda_Rank')
    else:
        outsiders = restant.head(2)
    candidats_folie = restant[~restant['Numero'].isin(outsiders['Numero'])]
    if 'Cote' in candidats_folie.columns and 'ELO_Cheval_Rank' in candidats_folie.columns:
        coup_de_folie = candidats_folie[
            (candidats_folie['Cote'] > 15) & (candidats_folie['ELO_Cheval_Rank'] <= 5)
        ].head(1)
    else:
        coup_de_folie = pd.DataFrame()
    return bases, outsiders, coup_de_folie