import pandas as pd
import numpy as np

def calculer_score_couple(df):
    """
    Calcule un score de base pour le couplé.
    FIX : Cette fonction DOIT exister pour satisfaire l'import de Algo Builder.
    """
    if df is None or df.empty:
        return df
    
    # On initialise la colonne pour éviter toute erreur de calcul ultérieure
    df = df.copy()
    if 'Note_IA_Decimale' in df.columns and 'Synergie_JCh_Rank' in df.columns:
        df['score_potentiel'] = (df['Note_IA_Decimale'] * 0.7) + (20 - df['Synergie_JCh_Rank'])
    else:
        df['score_potentiel'] = 0
        
    return df

def detecter_trio(df_course):
    """
    Logique combinée pour le Trio :
    1. Bases : Les 2 meilleurs selon l'IA Trio.
    2. Associés : Les 2 meilleurs selon l'indice Borda (hors bases).
    3. Coup de Folie : Un cheval à grosse cote avec un bon potentiel ELO.
    """
    if df_course is None or df_course.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # 1. LES BASES (IA_Trio_Rank)
    if 'IA_Trio_Rank' in df_course.columns:
        # On prend les 2 plus petits rangs (1 et 2)
        bases = df_course.nsmallest(2, 'IA_Trio_Rank')
    else:
        bases = df_course.head(2)
    
    # 2. LES ASSOCIÉS (Borda_Rank)
    restant = df_course[~df_course['Numero'].isin(bases['Numero'])]
    if 'Borda_Rank' in restant.columns:
        outsiders = restant.nsmallest(2, 'Borda_Rank')
    else:
        outsiders = restant.head(2)
    
    # 3. LE COUP DE FOLIE (Cote > 15 et bon ELO_Cheval_Rank)
    # On cherche dans ce qui reste (ni base, ni associé)
    candidats_folie = restant[~restant['Numero'].isin(outsiders['Numero'])]
    
    if 'Cote' in candidats_folie.columns and 'ELO_Cheval_Rank' in candidats_folie.columns:
        coup_de_folie = candidats_folie[
            (candidats_folie['Cote'] > 15) & 
            (candidats_folie['ELO_Cheval_Rank'] <= 5)
        ].head(1)
    else:
        coup_de_folie = pd.DataFrame()
    
    return bases, outsiders, coup_de_folie

def analyser_performance_backtest(df_course):
    """
    Compare les pronos aux résultats réels.
    Le classement réel vient de la colonne 'Rank' du CSV, mappée en 'classement'.
    """
    if 'classement' not in df_course.columns:
        return "Résultats non importés"
    
    # On récupère le podium officiel (rangs 1, 2 et 3)
    podium = df_course[df_course['classement'].isin([1, 2, 3])].sort_values('classement')
    return podium[['Numero', 'Cheval', 'classement']].values.tolist()