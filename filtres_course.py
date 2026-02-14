"""
filtres_course.py — Filtres au niveau de la course
Hippodrome, Discipline, Partants, Classe, Distance, Allocation
"""
import streamlit as st
import pandas as pd


def render_filtres_course(date_start, date_end, run_query):
    """Affiche les widgets filtres course et retourne les valeurs."""
    _raw = run_query(
        "SELECT DISTINCT hippodrome FROM selections WHERE date BETWEEN ? AND ?",
        (str(date_start), str(date_end))
    )
    all_hippos = sorted(_raw['hippodrome'].unique().tolist()) if not _raw.empty else []

    st.markdown(
        '<p style="margin:0;padding:2px 0;font-size:0.8rem;color:#666;">🔍 Course</p>',
        unsafe_allow_html=True
    )
    c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1.5, 1.5, 1.5, 1.5])
    with c1:
        filter_hippo = st.multiselect("Hippodrome", all_hippos, default=[], placeholder="Tous")
    with c2:
        filter_disc = st.multiselect(
            "Discipline", ["A - Attelé", "M - Monté", "P - Plat", "O - Obstacle"],
            default=[], placeholder="Toutes"
        )
    with c3:
        filter_partants = st.slider("Partants", 1, 20, (1, 20))
    with c4:
        filter_classe = st.multiselect(
            "Classe",
            ["Handicap", "Classe 2", "Classe 3", "Classe 4",
             "Maiden", "Course D", "Course R", "Course B",
             "Course E", "A réclamer"],
            default=[], placeholder="Toutes"
        )
    with c5:
        filter_distance = st.slider("Distance", 1000, 4000, (1000, 4000), step=100)
    with c6:
        filter_alloc = st.slider("Allocation", 0, 100000, (0, 100000), step=5000)

    return {
        'hippo': filter_hippo,
        'disc': filter_disc,
        'partants': filter_partants,
        'classe': filter_classe,
        'distance': filter_distance,
        'alloc': filter_alloc,
    }


def appliquer_filtres_course(df, filtres):
    """Applique les filtres course sur le DataFrame. Retourne df filtré."""
    n_avant = len(df)

    # Classe
    if filtres['classe'] and 'Classe_Groupe' in df.columns:
        df = df[df['Classe_Groupe'].astype(str).str.strip().isin(filtres['classe'])]
        print(f"  [FILTRE] Classe {filtres['classe']}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # Distance
    if 'distance' in df.columns and filtres['distance'] != (1000, 4000):
        df['distance'] = pd.to_numeric(
            df['distance'].astype(str).str.replace(',', '.'), errors='coerce'
        ).fillna(0)
        df = df[df['distance'].between(filtres['distance'][0], filtres['distance'][1])]
        print(f"  [FILTRE] Distance {filtres['distance']}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # Allocation
    if 'allocation' in df.columns and filtres['alloc'] != (0, 100000):
        df['allocation'] = pd.to_numeric(
            df['allocation'].astype(str).str.replace(',', '.'), errors='coerce'
        ).fillna(0)
        df = df[df['allocation'].between(filtres['alloc'][0], filtres['alloc'][1])]
        print(f"  [FILTRE] Allocation {filtres['alloc']}: {n_avant} -> {len(df)}")

    return df