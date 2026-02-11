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
    .main-title { font-weight: 900; font-size: 2.5rem; color: #000; border-bottom: 3px solid #3A7BD5; padding-bottom:10px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📝 Gestion des Paris Pro</p>', unsafe_allow_html=True)

# --- SECURITÉ : MISE À JOUR DE LA BASE ---
conn = get_conn()
cursor = conn.cursor()
try:
    cursor.execute("SELECT type_pari FROM paris LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE paris ADD COLUMN type_pari TEXT DEFAULT 'Simple'")
    cursor.execute("ALTER TABLE paris ADD COLUMN mode_pari TEXT DEFAULT 'Gagnant'")
    conn.commit()

# --- RÉCUPÉRATION DES DONNÉES DYNAMIQUES ---
def get_dropdown_data(selected_date):
    df_prog = pd.read_sql("SELECT DISTINCT date, hippodrome, course_num FROM selections WHERE date = ?", 
                          conn, params=(str(selected_date),))
    return df_prog

# --- FORMULAIRE DE SAISIE ---
with st.expander("➕ Placer un nouveau pari", expanded=True):
    with st.form("manual_entry"):
        c1, c2, c3 = st.columns(3)
        date_select = c1.date_input("Date")
        
        prog_data = get_dropdown_data(date_select)
        hippo_list = sorted(prog_data['hippodrome'].unique().tolist())
        hippo = c2.selectbox("Hippodrome", hippo_list if hippo_list else ["Aucun programme trouvé"])
        
        course_list = sorted(prog_data[prog_data['hippodrome'] == hippo]['course_num'].unique().tolist())
        course = c3.selectbox("Course", course_list if course_list else ["-"])
        
        st.divider()
        g1, g2 = st.columns([2, 1])
        
        # Liste complète des types de paris
        type_pari = g1.selectbox("Type de Pari", 
                                ["Simple Gagnant", "Simple Placé", "Couplé Gagnant", "Couplé Placé", 
                                 "Trio", "Trio Ordre", "2/4", "Z4", "Z5", "Multi", "Quarté", "Quinté"])
        
        chev = g2.text_input("Chevaux joués (ex: 1-4-8)")
        
        st.divider()
        f1, f2, f3 = st.columns(3)
        mise = f1.number_input("Mise Totale (€)", 1.0, step=0.5)
        res = f2.selectbox("Résultat", ["En cours", "Gagné", "Perdu"])
        rapport = f3.number_input("Rapport total encaissé (€)", 0.0, step=0.1)

        if st.form_submit_button("💾 Enregistrer le pari"):
            gn = (rapport - mise) if res == "Gagné" else (-mise if res == "Perdu" else 0)
            
            # On enregistre le type complet (ex: "Simple Placé") dans la colonne type_pari
            conn.execute("""INSERT INTO paris 
                         (date, hippodrome, course_num, cheval, cote, mise, resultat, rapport, gain_net, type_pari, mode_pari) 
                         VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                       (str(date_select), hippo, course, chev, 0.0, float(mise), res, float(rapport), float(gn), type_pari, "-"))
            conn.commit()
            st.success(f"Pari {type_pari} enregistré !")
            st.rerun()

st.divider()

# --- HISTORIQUE & MODIFICATIONS ---
st.subheader("📋 Historique & Modifications")
df = pd.read_sql("SELECT * FROM paris ORDER BY id DESC", conn)

if not df.empty:
    df['type_pari'] = df['type_pari'].fillna('Simple')
    df['label'] = df['date'].astype(str) + " | " + df['type_pari'] + " | " + df['cheval']
    
    pari_select = st.selectbox("Choisir un pari à gérer", df['label'].tolist())
    pari_data = df[df['label'] == pari_select].iloc[0]
    pari_id = int(pari_data['id'])

    col_edit, col_del = st.columns([2, 1])

    with col_edit:
        with st.expander("✏️ Modifier le résultat"):
            with st.form("edit_form"):
                e1, e2, e3 = st.columns(3)
                new_res = e1.selectbox("Résultat", ["Gagné", "Perdu", "En cours"], 
                                     index=["Gagné", "Perdu", "En cours"].index(pari_data['resultat']) if pari_data['resultat'] in ["Gagné", "Perdu", "En cours"] else 0)
                new_mise = e2.number_input("Mise (€)", value=float(pari_data['mise']))
                new_rap = e3.number_input("Rapport (€)", value=float(pari_data['rapport']))
                
                if st.form_submit_button("💾 Mettre à jour"):
                    new_gn = (new_rap - new_mise) if new_res == "Gagné" else (-new_mise if new_res == "Perdu" else 0)
                    conn.execute("""UPDATE paris SET resultat=?, mise=?, rapport=?, gain_net=? WHERE id=?""",
                               (new_res, new_mise, new_rap, new_gn, pari_id))
                    conn.commit()
                    st.success("Modifié !")
                    st.rerun()

    with col_del:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Supprimer", use_container_width=True):
            conn.execute("DELETE FROM paris WHERE id=?", (pari_id,))
            conn.commit()
            st.warning("Supprimé.")
            st.rerun()

    st.dataframe(df.drop(columns=['label', 'id']), use_container_width=True)
else:
    st.info("Aucun pari enregistré.")