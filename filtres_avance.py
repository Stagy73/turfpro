"""
filtres_avance.py — Filtres avancés
Repos, ELO Jockey, Rang Jockey, Place Corde, Pastille, Concordance Duo
"""
import streamlit as st
import pandas as pd


def render_filtres_avance(mode_affichage):
    """Affiche les widgets filtres avancés et retourne les valeurs."""
    st.markdown(
        '<p style="margin:0;padding:2px 0;font-size:0.8rem;color:#666;">⚡ Avancé</p>',
        unsafe_allow_html=True
    )
    c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 2])
    with c1:
        filter_repos = st.slider("Repos (j)", 0, 365, (0, 365))
    with c2:
        filter_elo_jockey = st.slider("ELO Jockey min", 0, 3000, 0, step=100)
    with c3:
        filter_rang_j = st.slider("Rang Jockey max", 1, 500, 500)
    with c4:
        filter_corde = st.slider("Place Corde", 1, 20, (1, 20))
    with c5:
        filtre_pastille = st.multiselect(
            "Pastille", ["🟢 Haute", "🟡 Moyenne", "🔴 Basse"],
            default=[], placeholder="Toutes"
        )
    with c6:
        filtre_confiance_on = False
        seuil_concordance = 4
        filtre_unanime = False
        folie_cote_min = 10
        folie_taux_min = 20
        if mode_affichage == "Trio + Folie (3+1)":
            fa, fb = st.columns(2)
            with fa:
                folie_cote_min = st.slider("Cote folie", 5, 30, 10)
            with fb:
                folie_taux_min = st.slider("TP folie %", 0, 50, 20)
        elif mode_affichage == "Duo (2 chevaux)":
            filtre_confiance_on = st.toggle("Concordance Duo", value=False)
            if filtre_confiance_on:
                da, db = st.columns(2)
                with da:
                    seuil_concordance = st.slider("Conc. min", 0, 6, 4)
                with db:
                    filtre_unanime = st.toggle("Unanimité", value=False)

    return {
        'repos': filter_repos,
        'elo_jockey': filter_elo_jockey,
        'rang_j': filter_rang_j,
        'corde': filter_corde,
        'pastille': filtre_pastille,
        'confiance_on': filtre_confiance_on,
        'seuil_conc': seuil_concordance,
        'unanime': filtre_unanime,
        'folie_cote_min': folie_cote_min,
        'folie_taux_min': folie_taux_min,
    }


def appliquer_filtres_avance(df, filtres):
    """Applique les filtres avancés. Retourne df filtré."""
    n_avant = len(df)

    # Repos
    if 'Repos' in df.columns and filtres['repos'] != (0, 365):
        df['Repos'] = pd.to_numeric(
            df['Repos'].astype(str).str.replace(',', '.'), errors='coerce'
        ).fillna(0)
        df = df[df['Repos'].between(filtres['repos'][0], filtres['repos'][1])]
        print(f"  [FILTRE] Repos {filtres['repos']}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # ELO Jockey
    if filtres['elo_jockey'] > 0 and 'ELO_Jockey' in df.columns:
        df['ELO_Jockey'] = pd.to_numeric(
            df['ELO_Jockey'].astype(str).str.replace(',', '.'), errors='coerce'
        ).fillna(0)
        df = df[df['ELO_Jockey'] >= filtres['elo_jockey']]
        print(f"  [FILTRE] ELO Jockey >= {filtres['elo_jockey']}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # Rang Jockey
    if filtres['rang_j'] < 500 and 'Rang_J' in df.columns:
        df['Rang_J'] = pd.to_numeric(
            df['Rang_J'].astype(str).str.replace(',', '.'), errors='coerce'
        ).fillna(999)
        df = df[df['Rang_J'] <= filtres['rang_j']]
        print(f"  [FILTRE] Rang Jockey <= {filtres['rang_j']}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # Place Corde
    if 'Place_Corde' in df.columns and filtres['corde'] != (1, 20):
        df['Place_Corde'] = pd.to_numeric(
            df['Place_Corde'].astype(str).str.replace(',', '.'), errors='coerce'
        ).fillna(0)
        df = df[df['Place_Corde'].between(filtres['corde'][0], filtres['corde'][1])]
        print(f"  [FILTRE] Corde {filtres['corde']}: {n_avant} -> {len(df)}")

    return df