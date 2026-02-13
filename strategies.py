import pandas as pd
import numpy as np


def calculer_score_couple(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'Note_IA_Decimale' in df.columns and 'Synergie_JCh_Rank' in df.columns:
        df['score_potentiel'] = (df['Note_IA_Decimale'] * 0.7) + (20 - df['Synergie_JCh_Rank'])
    else:
        df['score_potentiel'] = 0
    return df


def calculer_confiance_duo(df_course, col_score='SCORE'):
    """
    Confiance basée sur la CONCORDANCE entre les 3 méthodes (F, IA, H).
    Retourne (concordance, detail)
    - concordance : 0-6
    - detail : dict
    """
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
    concordance = f_ia + f_h + ia_h

    union_all = duo_f | duo_ia | duo_h
    unanime = (duo_f == duo_ia == duo_h) if duo_ia and duo_h else False
    intersect_all = duo_f & duo_ia & duo_h if duo_ia and duo_h else set()

    detail = {
        'duo_f': duo_f, 'duo_ia': duo_ia, 'duo_h': duo_h,
        'f_ia': f_ia, 'f_h': f_h, 'ia_h': ia_h,
        'unanime': unanime, 'nb_uniques': len(union_all),
        'chevaux_consensus': intersect_all,
    }
    return concordance, detail


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


def analyser_performance_backtest(df_course):
    if 'classement' not in df_course.columns:
        return "Résultats non importés"
    podium = df_course[df_course['classement'].isin([1, 2, 3])].sort_values('classement')
    return podium[['Numero', 'Cheval', 'classement']].values.tolist()