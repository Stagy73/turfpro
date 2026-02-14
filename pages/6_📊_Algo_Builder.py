import streamlit as st
import pandas as pd
import sys
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
from filtres_course import render_filtres_course, appliquer_filtres_course
from filtres_cheval import render_filtres_cheval, appliquer_filtres_cheval
from filtres_avance import render_filtres_avance, appliquer_filtres_avance

st.set_page_config(layout="wide", page_title="Algo Builder")
st.markdown(
    '<p style="font-weight:900; font-size:2.2rem; color:#1E293B; '
    'border-bottom:4px solid #3A7BD5;">🧪 Algo Builder</p>',
    unsafe_allow_html=True
)


def save_algo(nom, formule):
    run_query("INSERT OR REPLACE INTO algos (nom, formule) VALUES (?, ?)",
              (nom, formule), commit=True)

def delete_algo(nom):
    run_query("DELETE FROM algos WHERE nom = ?", (nom,), commit=True)


# =====================================================
# LIGNE 1 : Période + Algo + Mode
# =====================================================
algos_df = run_query("SELECT * FROM algos")
liste_algos = (
    ["--- Nouveau ---"]
    + list(FORMULES_PRESET.keys())
    + (algos_df['nom'].tolist() if not algos_df.empty else [])
)

r1a, r1b, r1c, r1d, r1e = st.columns([1, 1, 1, 2, 2])
with r1a:
    mode_date = st.radio("", ["1 jour", "Plage"], horizontal=True, label_visibility="collapsed")
with r1b:
    if mode_date == "1 jour":
        date_start = st.date_input("📅 Date", value=pd.Timestamp.now())
        date_end = date_start
    else:
        date_start = st.date_input("📅 Du", value=pd.Timestamp.now() - pd.Timedelta(days=7))
with r1c:
    if mode_date == "Plage":
        date_end = st.date_input("Au", value=pd.Timestamp.now())
    else:
        st.write("")
with r1d:
    selected = st.selectbox("Algorithme", liste_algos, label_visibility="collapsed")
with r1e:
    mode_affichage = st.radio(
        "Mode", ["Simple (1 cheval)", "Duo (2 chevaux)", "Trio + Folie (3+1)", "Borda 4 chevaux"],
        horizontal=True, label_visibility="collapsed"
    )

# =====================================================
# LIGNES 2-3-4 : Filtres modulaires
# =====================================================
filtres_c = render_filtres_course(date_start, date_end, run_query)
filtres_ch = render_filtres_cheval()
filtres_av = render_filtres_avance(mode_affichage)

st.divider()

# =====================================================
# FORMULE + LANCER
# =====================================================
current_nom, current_form = ("", "")
if selected in FORMULES_PRESET:
    current_nom, current_form = selected, FORMULES_PRESET[selected]
elif selected != "--- Nouveau ---":
    r = algos_df[algos_df['nom'] == selected].iloc[0]
    current_nom, current_form = r['nom'], r['formule']

fa, fb = st.columns([3, 1])
with fa:
    formule_raw = st.text_input("Formule", value=current_form)
with fb:
    nom_algo = st.text_input("Nom", value=current_nom)

ba, bb, bc = st.columns([1, 1, 3])
with ba:
    if st.button("💾 Sauver"):
        save_algo(nom_algo, formule_raw)
        st.rerun()
with bb:
    if st.button("🗑️ Effacer"):
        if selected not in FORMULES_PRESET and selected != "--- Nouveau ---":
            delete_algo(selected)
            st.rerun()
with bc:
    btn_run = st.button("🚀 LANCER", type="primary", use_container_width=True)

# =====================================================
# MOTEUR
# =====================================================
if btn_run:
    print("\n" + "=" * 60)
    print("🚀 ALGO BUILDER - LANCEMENT")
    print("=" * 60)
    print(f"  Période: {date_start} -> {date_end}")
    print(f"  Mode: {mode_affichage}")
    print(f"  Formule: {formule_raw[:80]}...")

    raw_data = charger_donnees(run_query, date_start, date_end)
    if raw_data.empty:
        st.warning("Aucune donnée.")
        st.stop()

    print(f"\n📦 Données brutes: {len(raw_data)} lignes")

    try:
        df = preparer_dataframe(raw_data)
        print(f"📦 Après preparer_dataframe: {len(df)} lignes")

        # Colonnes disponibles
        print(f"📋 Colonnes dispo ({len(df.columns)}): {sorted(df.columns.tolist())[:30]}...")

        # Filtres de base (hippo, disc, partants)
        df = appliquer_filtres(
            df, filtres_c['hippo'], filtres_c['disc'], filtres_c['partants']
        )
        print(f"\n🔍 Après filtres de base (hippo/disc/partants): {len(df)} lignes")

        if df.empty:
            st.warning("Aucune course après filtres de base.")
            st.stop()

        # Filtres course avancés
        print("\n--- FILTRES COURSE ---")
        df = appliquer_filtres_course(df, filtres_c)
        print(f"  => Après filtres course: {len(df)} lignes")

        if df.empty:
            st.warning("Aucune donnée après filtres course.")
            st.stop()

        # Filtres cheval
        print("\n--- FILTRES CHEVAL ---")
        df = appliquer_filtres_cheval(df, filtres_ch)
        print(f"  => Après filtres cheval: {len(df)} lignes")

        if df.empty:
            st.warning("Aucune donnée après filtres cheval.")
            st.stop()

        # Filtres avancés
        print("\n--- FILTRES AVANCÉS ---")
        df = appliquer_filtres_avance(df, filtres_av)
        print(f"  => Après filtres avancés: {len(df)} lignes")

        if df.empty:
            st.warning("Aucune donnée après filtres avancés.")
            st.stop()

        # Calculs
        print("\n⚙️ Calcul colonnes + scores...")
        df = calculer_colonnes(df)
        df = calculer_scores(df, formule_raw)
        all_courses, courses_avec, courses_sans = get_courses(df)

        print(f"✅ {len(all_courses)} courses ({len(courses_avec)} terminées, {len(courses_sans)} en attente)")

        # Compteur filtres
        nb_filtres = sum([
            bool(filtres_c['hippo']), bool(filtres_c['disc']),
            filtres_c['partants'] != (1, 20), bool(filtres_c['classe']),
            filtres_c['distance'] != (1000, 4000), filtres_c['alloc'] != (0, 100000),
            filtres_ch['age'] != (2, 12), bool(filtres_ch['sexe']),
            bool(filtres_ch['ferrure']), bool(filtres_ch['avis']),
            filtres_ch['d4'] < 4, filtres_ch['inedits'],
            filtres_ch['exfav'] != "Tous", filtres_ch['supplement'] != "Tous",
            filtres_av['repos'] != (0, 365), filtres_av['elo_jockey'] > 0,
            filtres_av['rang_j'] < 500, filtres_av['corde'] != (1, 20),
            filtres_av['confiance_on'], bool(filtres_av['pastille']),
        ])
        badge = f" | 🔧 {nb_filtres} filtres" if nb_filtres else ""

        st.caption(
            f"📊 {len(all_courses)} courses "
            f"({len(courses_avec)} terminées) | "
            f"{disc_txt(df)} | "
            f"{filtres_c['partants'][0]}-{filtres_c['partants'][1]} partants"
            f"{badge}"
        )

        print(f"\n🎯 Dispatch -> {mode_affichage}")
        print("=" * 60 + "\n")

        # Dispatch
        if mode_affichage == "Simple (1 cheval)":
            render_simple(
                df, courses_avec, courses_sans,
                date_start, date_end,
                filtre_pastille=filtres_av['pastille']
            )
        elif mode_affichage == "Duo (2 chevaux)":
            render_duo(
                df, courses_avec, courses_sans,
                date_start, date_end,
                filtres_av['confiance_on'], filtres_av['seuil_conc'],
                filtres_av['unanime'], filtres_av['pastille']
            )
        elif mode_affichage == "Trio + Folie (3+1)":
            render_trio(
                df, courses_avec, courses_sans,
                date_start, date_end,
                filtres_av['folie_cote_min'], filtres_av['folie_taux_min'],
                filtre_pastille=filtres_av['pastille']
            )
        elif mode_affichage == "Borda 4 chevaux":
            render_borda4(
                df, courses_avec, courses_sans,
                date_start, date_end,
                filtre_pastille=filtres_av['pastille']
            )

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        st.error(f"Erreur : {e}")
        import traceback
        st.code(traceback.format_exc())
        print(traceback.format_exc())