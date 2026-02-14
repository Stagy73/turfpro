"""
filtres_cheval.py — Filtres au niveau du cheval
Âge, Sexe, Ferrure, Avis Entraîneur, D4, Inédits, ExFav, Supplémenté
"""
import streamlit as st
import pandas as pd
import re


def compter_d4(musique):
    """Compte les D/0/incidents dans les 4 dernières courses de la musique."""
    if not musique or str(musique).strip() in ('', 'nan', 'None'):
        return -1  # -1 = pas de musique (inédit ou donnée manquante)
    s = str(musique).strip()
    s = re.sub(r'\(\d+\)', '|', s)
    results = re.findall(r'(\d+|D|Dm|Ar|T|Ret)[a-z]*', s, re.IGNORECASE)
    if not results:
        return -1
    count = 0
    for r in results[:4]:
        if r.upper() in ('D', 'DM', 'AR', 'T', 'RET', '0'):
            count += 1
    return count


def render_filtres_cheval():
    """Affiche les widgets filtres cheval et retourne les valeurs."""
    st.markdown(
        '<p style="margin:0;padding:2px 0;font-size:0.8rem;color:#666;">🐴 Cheval</p>',
        unsafe_allow_html=True
    )
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1, 1.5, 1.2, 1.2, 1, 1, 1, 1.2])
    with c1:
        filter_age = st.slider("Âge", 2, 12, (2, 12))
    with c2:
        filter_sexe = st.multiselect(
            "Sexe", ["M - Mâle", "H - Hongre", "F - Femelle"],
            default=[], placeholder="Tous"
        )
    with c3:
        filter_ferrure = st.multiselect(
            "Ferrure",
            ["Normal", "Déferré Ant.", "Déferré Post.", "Déferré A+P",
             "Protégé Ant.", "Protégé Post.", "Protégé A+P"],
            default=[], placeholder="Toutes"
        )
    with c4:
        filter_avis = st.multiselect(
            "Avis Entr.", ["POSITIF", "NEUTRE", "NEGATIF"],
            default=[], placeholder="Tous"
        )
    with c5:
        filter_d4 = st.slider("D4 max", 0, 4, 4,
                               help="Incidents max sur 4 dernières courses")
    with c6:
        exclure_inedits = st.toggle("Sans inédits", value=False)
    with c7:
        filter_exfav = st.selectbox("ExFav", ["Tous", "Oui", "Non"])
    with c8:
        filter_supplement = st.selectbox("Supplémenté", ["Tous", "Oui", "Non"])

    return {
        'age': filter_age,
        'sexe': filter_sexe,
        'ferrure': filter_ferrure,
        'avis': filter_avis,
        'd4': filter_d4,
        'inedits': exclure_inedits,
        'exfav': filter_exfav,
        'supplement': filter_supplement,
    }


def appliquer_filtres_cheval(df, filtres):
    """Applique les filtres cheval. Retourne df filtré."""
    n_avant = len(df)

    # Âge
    if filtres['age'] != (2, 12) and 'age' in df.columns:
        df['age'] = pd.to_numeric(
            df['age'].astype(str).str.replace(',', '.').str.strip(), errors='coerce'
        ).fillna(0).astype(int)
        df = df[df['age'].between(filtres['age'][0], filtres['age'][1])]
        print(f"  [FILTRE] Âge {filtres['age']}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # Sexe
    if filtres['sexe'] and 'Sexe' in df.columns:
        sexe_codes = [s[0] for s in filtres['sexe']]
        df = df[df['Sexe'].astype(str).str.strip().str.upper().isin(sexe_codes)]
        print(f"  [FILTRE] Sexe {sexe_codes}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # Ferrure
    if filtres['ferrure'] and 'ferrure' in df.columns:
        ferrure_map = {
            "Normal": "__NORMAL__",
            "Déferré Ant.": "DEFERRE_ANTERIEURS",
            "Déferré Post.": "DEFERRE_POSTERIEURS",
            "Déferré A+P": "DEFERRE_ANTERIEURS_POSTERIEURS",
            "Protégé Ant.": "PROTEGE_ANTERIEURS",
            "Protégé Post.": "PROTEGE_POSTERIEURS",
            "Protégé A+P": "PROTEGE_ANTERIEURS_POSTERIEURS",
        }
        codes = [ferrure_map.get(f) for f in filtres['ferrure'] if f != "Normal"]
        include_normal = "Normal" in filtres['ferrure']
        mask = df['ferrure'].astype(str).str.strip().isin(codes)
        if include_normal:
            mask = mask | df['ferrure'].isna() | (df['ferrure'].astype(str).str.strip().isin(['', 'nan']))
        df = df[mask]
        print(f"  [FILTRE] Ferrure {filtres['ferrure']}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # Avis Entraîneur
    if filtres['avis'] and 'avis_entraineur' in df.columns:
        df = df[df['avis_entraineur'].astype(str).str.strip().str.upper().isin(filtres['avis'])]
        print(f"  [FILTRE] Avis {filtres['avis']}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # D4 (musique)
    if filtres['d4'] < 4 and 'Musique' in df.columns:
        df['_d4'] = df['Musique'].apply(compter_d4)
        avant_d4 = len(df)
        # -1 = pas de musique, on les garde sauf si on exclut les inédits
        df = df[(df['_d4'] <= filtres['d4']) | (df['_d4'] == -1)]
        df = df.drop(columns=['_d4'])
        print(f"  [FILTRE] D4 max {filtres['d4']}: {avant_d4} -> {len(df)}")
        n_avant = len(df)

    # Exclure inédits
    if filtres['inedits'] and 'Courses_courues' in df.columns:
        df['Courses_courues'] = pd.to_numeric(
            df['Courses_courues'].astype(str).str.replace(',', '.'), errors='coerce'
        ).fillna(0)
        df = df[df['Courses_courues'] > 0]
        print(f"  [FILTRE] Sans inédits: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # ExFav
    if filtres['exfav'] != "Tous" and 'ExFav' in df.columns:
        df = df[df['ExFav'].astype(str).str.strip() == filtres['exfav']]
        print(f"  [FILTRE] ExFav={filtres['exfav']}: {n_avant} -> {len(df)}")
        n_avant = len(df)

    # Supplémenté
    if filtres['supplement'] != "Tous" and 'supplemente' in df.columns:
        df = df[df['supplemente'].astype(str).str.strip() == filtres['supplement']]
        print(f"  [FILTRE] Supplémenté={filtres['supplement']}: {n_avant} -> {len(df)}")

    return df