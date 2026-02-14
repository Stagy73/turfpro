"""
utils_algo.py — Fonctions d'affichage partagées pour Algo Builder
"""
import pandas as pd
import numpy as np

DISC_MAP = {'A': 'Attelé', 'M': 'Monté', 'P': 'Plat', 'O': 'Obstacle', 'H': 'Haies', 'S': 'Steeple', 'C': 'Course', '': 'Inconnu'}

FORMULES_PRESET = {
    "🎯 Simple Optimisé (Gagnant)": "IA_Gagnant * 50 + Note_IA_Decimale * 2 + 50 / (Cote if Cote > 0 else 1) + Synergie_JCh * 0.2",
    "🎲 Duo Optimisé (Couplé)": "(6 - Borda_Rank) * 1 + (6 - Cote_Rank) * 2 + (6 - Popularite_Rank) * 2",
    "🏇 Trio Optimisé": "IA_Multi * 40 + IA_Trio * 18 + 40 / (Cote if Cote > 0 else 1) + Taux_Place * 0.10",
    "📊 F11 Polyvalente": "IA_Trio * 18 + Borda * 2.5 + Note_IA_Decimale * 2 + Synergie_JCh * 0.5 + Taux_Place * 0.12 + Taux_Victoire * 0.12 + 60 / (Cote if Cote > 0 else 1) + IA_Gagnant * 15",
    "🔷 Borda Pure": "Borda * 10 + 50 / (Cote if Cote > 0 else 1)",
}


def colored_nums(nums_list, ref_set):
    return " — ".join(
        f":green[**{n}**]✓" if n in ref_set else f":red[**{n}**]✗"
        for n in nums_list
    )


def nums_str(df_sub):
    return " - ".join(str(int(r['Numero'])) for _, r in df_sub.iterrows())


def get_arrivee(dfc):
    dc = dfc[dfc['classement'] > 0].sort_values('classement')
    return " - ".join(str(int(r['Numero'])) for _, r in dc.iterrows()) if not dc.empty else None


def get_confiance(scores):
    if len(scores) < 3:
        return "?"
    gap = scores[0] - scores[2]
    return "🟢" if gap >= 50 else ("🟡" if gap >= 30 else "🔴")


def disc_txt(df):
    discs_found = df['discipline'].astype(str).str.strip().str.upper().unique()
    return ", ".join(DISC_MAP.get(d, d) for d in discs_found if d)