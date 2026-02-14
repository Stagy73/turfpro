import streamlit as st
import pandas as pd
import sys
import os

import pathlib
_root = str(pathlib.Path(__file__).resolve().parent.parent)
sys.path.insert(0, _root)

from utils import run_query
from engine import (
    charger_donnees, preparer_dataframe, appliquer_filtres,
    calculer_colonnes, calculer_scores, get_courses
)
from utils_algo import FORMULES_PRESET, DISC_MAP, disc_txt
from algo_mode_simple import render_simple
from algo_mode_duo import render_duo
from algo_mode_trio import render_trio
from algo_mode_borda4 import render_borda4

st.set_page_config(layout="wide", page_title="Algo Builder")
st.markdown(
    '<p style="font-weight:900; font-size:2.2rem; color:#1E293B; '
    'border-bottom:4px solid #3A7BD5;">Algo Builder - Strategies & Backtest</p>',
    unsafe_allow_html=True
)


def save_algo(nom, formule):
    run_query(
        "INSERT OR REPLACE INTO algos (nom, formule) VALUES (?, ?)",
        (nom, formule), commit=True
    )


def delete_algo(nom):
    run_query("DELETE FROM algos WHERE nom = ?", (nom,), commit=True)


col_side, col_main = st.columns([1, 2])

with col_side:
    st.markdown("**Periode**")
    mode_date = st.radio(
        "", ["1 jour", "Plage"],
        horizontal=True, label_visibility="collapsed"
    )
    if mode_date == "1 jour":
        date_start = st.date_input("Date", value=pd.Timestamp.now())
        date_end = date_start
    else:
        date_start = st.date_input(
            "Du", value=pd.Timestamp.now() - pd.Timedelta(days=7)
        )
        date_end = st.date_input("Au", value=pd.Timestamp.now())

    st.divider()
    algos_df = run_query("SELECT * FROM algos")
    liste_algos = (
        ["--- Nouveau ---"]
        + list(FORMULES_PRESET.keys())
        + (algos_df['nom'].tolist() if not algos_df.empty else [])
    )
    selected = st.selectbox("Algorithme :", liste_algos)
    mode_affichage = st.radio(
        "Mode :",
        [
            "Simple (1 cheval)",
            "Duo (2 chevaux)",
            "Trio + Folie (3+1)",
            "Borda 4 chevaux",
        ]
    )

    st.divider()
    st.markdown("**Filtres**")
    _raw = run_query(
        "SELECT DISTINCT hippodrome FROM selections "
        "WHERE date BETWEEN ? AND ?",
        (str(date_start), str(date_end))
    )
    all_hippos = (
        sorted(_raw['hippodrome'].unique().tolist())
        if not _raw.empty else []
    )
    filter_hippo = st.multiselect(
        "Hippodrome", all_hippos, default=[], placeholder="Tous"
    )
    filter_disc = st.multiselect(
        "Discipline",
        ["A - Attele", "M - Monte", "P - Plat", "O - Obstacle"],
        default=[], placeholder="Toutes"
    )
    filter_partants = st.slider("Nb Partants", 1, 20, (1, 20))

    st.divider()
    st.markdown("**Reglages Folie**")
    folie_cote_min = st.slider("Cote min folie", 5, 30, 10)
    folie_taux_min = st.slider("Taux Place min %", 0, 50, 20)

    filtre_confiance_on = False
    seuil_concordance = 4
    filtre_unanime = False
    if mode_affichage == "Duo (2 chevaux)":
        st.divider()
        st.markdown("**Filtre Confiance Duo**")
        filtre_confiance_on = st.toggle("Activer filtre", value=False)
        fc1, fc2 = st.columns(2)
        with fc1:
            seuil_concordance = st.slider("Concordance min", 0, 6, 4)
        with fc2:
            filtre_unanime = st.toggle(
                "Unanimite F=IA=H", value=False
            )

current_nom, current_form = ("", "")
if selected in FORMULES_PRESET:
    current_nom, current_form = selected, FORMULES_PRESET[selected]
elif selected != "--- Nouveau ---":
    r = algos_df[algos_df['nom'] == selected].iloc[0]
    current_nom, current_form = r['nom'], r['formule']

with col_main:
    with st.container(border=True):
        nom_algo = st.text_input("Nom", value=current_nom)
        formule_raw = st.text_area(
            "Formule", value=current_form, height=80
        )
        b1, b2, b3 = st.columns([1, 1, 2])
        if b1.button("Sauver"):
            save_algo(nom_algo, formule_raw)
            st.rerun()
        if b2.button("Effacer"):
            if (selected not in FORMULES_PRESET
                    and selected != "--- Nouveau ---"):
                delete_algo(selected)
                st.rerun()
        btn_run = b3.button(
            "LANCER", type="primary", use_container_width=True
        )

if btn_run:
    raw_data = charger_donnees(run_query, date_start, date_end)
    if raw_data.empty:
        st.warning("Aucune donnee.")
        st.stop()

    try:
        df = preparer_dataframe(raw_data)
        df = appliquer_filtres(
            df, filter_hippo, filter_disc, filter_partants
        )
        if df.empty:
            st.warning("Aucune course apres filtres.")
            st.stop()

        df = calculer_colonnes(df)
        df = calculer_scores(df, formule_raw)
        all_courses, courses_avec, courses_sans = get_courses(df)

        st.divider()
        st.caption(
            f"{len(all_courses)} courses "
            f"({len(courses_avec)} terminees) | "
            f"{disc_txt(df)} | "
            f"{filter_partants[0]}-{filter_partants[1]} partants"
        )

        if mode_affichage == "Simple (1 cheval)":
            render_simple(
                df, courses_avec, courses_sans,
                date_start, date_end
            )
        elif mode_affichage == "Duo (2 chevaux)":
            render_duo(
                df, courses_avec, courses_sans,
                date_start, date_end,
                filtre_confiance_on,
                seuil_concordance,
                filtre_unanime
            )
        elif mode_affichage == "Trio + Folie (3+1)":
            render_trio(
                df, courses_avec, courses_sans,
                date_start, date_end,
                folie_cote_min, folie_taux_min
            )
        elif mode_affichage == "Borda 4 chevaux":
            render_borda4(
                df, courses_avec, courses_sans,
                date_start, date_end
            )

    except Exception as e:
        st.error(f"Erreur : {e}")
        import traceback
        st.code(traceback.format_exc())