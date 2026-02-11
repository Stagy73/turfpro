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

# --- FONCTION SQL SÉCURISÉE (ANTI-LOCK) ---
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
        # On ignore les erreurs de colonnes déjà existantes
        if "already exists" not in str(e) and "duplicate column name" not in str(e):
            st.error(f"Erreur SQL : {e}")
    finally:
        cursor.close()
        conn.close()
    return result

# --- INITIALISATION INTELLIGENTE ---
# On vérifie si les colonnes existent avant de les ajouter (évite les bandeaux rouges)
with get_conn() as conn:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(paris)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    if "type_pari" not in existing_cols:
        cursor.execute("ALTER TABLE paris ADD COLUMN type_pari TEXT DEFAULT 'Simple Gagnant'")
    if "mode_pari" not in existing_cols:
        cursor.execute("ALTER TABLE paris ADD COLUMN mode_pari TEXT DEFAULT '-'")
    conn.commit()

# --- FORMULAIRE DE SAISIE ---
with st.expander("➕ Placer un nouveau pari", expanded=True):
    with st.form("manual_entry"):
        c1, c2, c3 = st.columns(3)
        date_select = c1.date_input("Date")
        
        prog_data = run_query("SELECT DISTINCT hippodrome, course_num FROM selections WHERE date = ?", (str(date_select),))
        hippo_list = sorted(prog_data['hippodrome'].unique().tolist()) if prog_data is not None and not prog_data.empty else []
        hippo = c2.selectbox("Hippodrome", hippo_list if hippo_list else ["Aucun programme"])
        
        course_list = sorted(prog_data[prog_data['hippodrome'] == hippo]['course_num'].unique().tolist()) if hippo_list else []
        course = c3.selectbox("Course", course_list if course_list else ["-"])
        
        st.divider()
        g1, g2 = st.columns([2, 1])
        type_pari = g1.selectbox("Type de Pari", ["Simple Gagnant", "Simple Placé", "Couplé Gagnant", "Couplé Placé", "Trio", "Trio Ordre", "2/4", "Z4", "Z5", "Multi", "Quarté", "Quinté"])
        chev = g2.text_input("Chevaux joués (ex: 1-4-8)")
        
        st.divider()
        f1, f2, f3 = st.columns(3)
        mise = f1.number_input("Mise Totale (€)", 1.0, step=0.5)
        res = f2.selectbox("Résultat", ["En cours", "Gagné", "Perdu"])
        rapport = f3.number_input("Rapport total (€)", 0.0, step=0.1)

        if st.form_submit_button("💾 Enregistrer le pari"):
            gn = (rapport - mise) if res == "Gagné" else (-mise if res == "Perdu" else 0)
            query = """INSERT INTO paris (date, hippodrome, course_num, cheval, cote, mise, resultat, rapport, gain_net, type_pari, mode_pari) 
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)"""
            run_query(query, (str(date_select), hippo, course, chev, 0.0, float(mise), res, float(rapport), float(gn), type_pari, "-"), commit=True)
            st.success("Enregistré !")
            st.rerun()

st.divider()

# --- HISTORIQUE & MODIFICATIONS (LA ZONE QUI MANQUAIT) ---
st.subheader("📋 Historique & Modifications")
df = run_query("SELECT * FROM paris ORDER BY id DESC")

if df is not None and not df.empty:
    # On force des valeurs par défaut pour les colonnes vides
    df['type_pari'] = df['type_pari'].fillna('Simple')
    df['cheval'] = df['cheval'].fillna('-')
    
    # Création du label pour le menu de sélection
    df['label'] = df['id'].astype(str) + " | " + df['date'].astype(str) + " | " + df['type_pari'] + " | " + df['cheval']
    
    # MENU DÉROULANT DE SÉLECTION (Textbox)
    pari_select = st.selectbox("Sélectionner un pari à modifier ou supprimer :", df['label'].tolist())
    
    # Récupération du pari sélectionné
    pari_data = df[df['label'] == pari_select].iloc[0]
    pari_id = int(pari_data['id'])

    col_edit, col_del = st.columns([2, 1])

    with col_edit:
        with st.expander("✏️ Modifier le résultat", expanded=False):
            with st.form("edit_form"):
                e1, e2, e3 = st.columns(3)
                index_res = ["Gagné", "Perdu", "En cours"].index(pari_data['resultat']) if pari_data['resultat'] in ["Gagné", "Perdu", "En cours"] else 0
                new_res = e1.selectbox("Résultat", ["Gagné", "Perdu", "En cours"], index=index_res)
                new_mise = e2.number_input("Mise (€)", value=float(pari_data['mise']))
                new_rap = e3.number_input("Rapport (€)", value=float(pari_data['rapport']))
                
                if st.form_submit_button("💾 Valider"):
                    new_gn = (new_rap - new_mise) if new_res == "Gagné" else (-new_mise if new_res == "Perdu" else 0)
                    run_query("UPDATE paris SET resultat=?, mise=?, rapport=?, gain_net=? WHERE id=?", (new_res, new_mise, new_rap, new_gn, pari_id), commit=True)
                    st.success("Mis à jour !")
                    st.rerun()

    with col_del:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Supprimer ce pari", use_container_width=True):
            run_query("DELETE FROM paris WHERE id=?", (pari_id,), commit=True)
            st.warning(f"Pari n°{pari_id} supprimé.")
            st.rerun()

    # Tableau visuel
    st.dataframe(df.drop(columns=['label'], errors='ignore'), use_container_width=True)
else:
    st.info("Aucun pari trouvé dans la base de données.")