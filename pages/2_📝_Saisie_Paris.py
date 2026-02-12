import streamlit as st
import pandas as pd
import sqlite3
from utils import get_conn

st.set_page_config(layout="wide")

# --- STYLE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;900&display=swap');
    .stApp { background-color: #F8FAFC; color: #000; font-family: 'Outfit', sans-serif; }
    .main-title { font-weight: 900; font-size: 2.2rem; color: #000; border-bottom: 4px solid #3A7BD5; padding-bottom:10px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📝 Gestion des Paris Pro</p>', unsafe_allow_html=True)

# --- FONCTION SQL SÉCURISÉE ---
def run_query(query, params=(), commit=False):
    conn = get_conn()
    cursor = conn.cursor()
    result = None
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
        else:
            result = cursor.fetchall()
            if cursor.description:
                cols = [column[0] for column in cursor.description]
                result = pd.DataFrame(result, columns=cols)
    except Exception as e:
        st.error(f"Erreur SQL : {e}")
    finally:
        cursor.close()
        conn.close()
    return result

# --- INITIALISATION ---
with get_conn() as conn:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(paris)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    for col in ["type_pari", "mode_pari"]:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE paris ADD COLUMN {col} TEXT DEFAULT '-'")
    conn.commit()

# --- FORMULAIRE DE SAISIE ---
with st.expander("➕ Placer un nouveau pari", expanded=True):
    # ÉTAPE 1 : Sélection de la Date et Hippodrome HORS FORMULAIRE pour l'interactivité
    c1, c2, c3 = st.columns(3)
    date_select = c1.date_input("Date")
    
    # Récupération des données selon la date
    prog_data = run_query("SELECT DISTINCT hippodrome, course_num FROM selections WHERE date = ?", (str(date_select),))
    
    if prog_data is not None and not prog_data.empty:
        # Sélection de l'hippodrome
        hippo_list = sorted(prog_data['hippodrome'].unique().tolist())
        hippo = c2.selectbox("Hippodrome", hippo_list)
        
        # ÉTAPE 2 : Filtrage dynamique des courses selon l'hippodrome choisi
        courses_filtrees = prog_data[prog_data['hippodrome'] == hippo]['course_num'].unique().tolist()
        
        # Nettoyage pour n'avoir que C1, C2... (enlève les préfixes R1 si présents)
        course_list = sorted([str(c).replace('R1', '').replace('R2', '').replace('R3', '').replace('R4', '') for c in courses_filtrees])
        course = c3.selectbox("Course", course_list)
    else:
        hippo = c2.selectbox("Hippodrome", ["Aucun programme"])
        course = c3.selectbox("Course", ["-"])

    # ÉTAPE 3 : Le reste des champs dans un formulaire pour validation groupée
    with st.form("manual_entry_details"):
        st.divider()
        g1, g2 = st.columns([2, 1])
        type_pari = g1.selectbox("Type de Pari", ["Simple Gagnant", "Simple Placé", "Couplé Gagnant", "Couplé Placé", "Trio", "2/4", "Multi", "Quinté"])
        chev = g2.text_input("Chevaux joués (ex: 1-4-8)")
        
        st.divider()
        f1, f2, f3 = st.columns(3)
        mise = f1.number_input("Mise Totale (€)", 1.0, step=0.5)
        res = f2.selectbox("Résultat", ["En cours", "Gagné", "Perdu"])
        rapport = f3.number_input("Rapport total (€)", 0.0, step=0.1)

        if st.form_submit_button("💾 Enregistrer le pari"):
            if hippo != "Aucun programme":
                gn = (rapport - mise) if res == "Gagné" else (-mise if res == "Perdu" else 0)
                query = """INSERT INTO paris (date, hippodrome, course_num, cheval, cote, mise, resultat, rapport, gain_net, type_pari, mode_pari) 
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)"""
                run_query(query, (str(date_select), hippo, course, chev, 0.0, float(mise), res, float(rapport), float(gn), type_pari, "-"), commit=True)
                st.success(f"Pari enregistré pour {hippo} {course} !")
                st.rerun()
            else:
                st.error("Veuillez sélectionner un hippodrome valide.")

st.divider()

# --- HISTORIQUE & MODIFICATIONS ---
st.subheader("📋 Historique & Modifications")
df = run_query("SELECT * FROM paris ORDER BY id DESC")

if df is not None and not df.empty:
    df['label'] = df['id'].astype(str) + " | " + df['date'].astype(str) + " | " + df['hippodrome'] + " | " + df['course_num']
    pari_select = st.selectbox("Sélectionner un pari :", df['label'].tolist())
    pari_data = df[df['label'] == pari_select].iloc[0]
    
    col_edit, col_del = st.columns([2, 1])
    with col_edit:
        with st.expander("✏️ Modifier"):
            with st.form("edit_form"):
                new_res = st.selectbox("Résultat", ["Gagné", "Perdu", "En cours"], index=["Gagné", "Perdu", "En cours"].index(pari_data['resultat']))
                new_mise = st.number_input("Mise", value=float(pari_data['mise']))
                new_rap = st.number_input("Rapport", value=float(pari_data['rapport']))
                if st.form_submit_button("Valider"):
                    new_gn = (new_rap - new_mise) if new_res == "Gagné" else (-new_mise if new_res == "Perdu" else 0)
                    run_query("UPDATE paris SET resultat=?, mise=?, rapport=?, gain_net=? WHERE id=?", (new_res, new_mise, new_rap, new_gn, int(pari_data['id'])), commit=True)
                    st.rerun()
    
    with col_del:
        if st.button("🗑️ Supprimer"):
            run_query("DELETE FROM paris WHERE id=?", (int(pari_data['id']),), commit=True)
            st.rerun()

    st.dataframe(df.drop(columns=['label']), use_container_width=True)