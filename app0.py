import streamlit as st
from utils import init_db

# Configuration de la page (doit être la première commande Streamlit)
st.set_page_config(
    page_title="Turf Analytics Pro",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation de la base de données
init_db()

# --- STYLE CLAIR "JOURNAL" ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;900&display=swap');
    
    .stApp { background-color: #F8FAFC; color: #000000; font-family: 'Outfit', sans-serif; }
    
    .main-title {
        font-weight: 900; 
        font-size: 3rem; 
        color: #000000;
        border-bottom: 5px solid #3A7BD5; 
        padding-bottom: 10px;
    }
    
    .card {
        background-color: white;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🏇 TURF ANALYTICS PRO</p>', unsafe_allow_html=True)

st.markdown("""
<div class="card">
    <h2 style="color: #1E40AF;">Bienvenue dans votre outil de gestion Turf</h2>
    <p style="font-size: 1.1rem; color: #333;">
        Toutes vos fonctionnalités sont maintenant rangées dans le <b>menu à gauche</b> :
    </p>
    <ul style="font-size: 1rem; color: #444; line-height: 1.8;">
        <li>📈 <b>Dashboard</b> : Vos graphiques et bénéfices.</li>
        <li>📝 <b>Saisie Paris</b> : Enregistrez vos mises manuellement.</li>
        <li>🎯 <b>Sélections</b> : Votre programme complet par Réunion et Course.</li>
        <li>📥 <b>Import / Export</b> : Chargez vos fichiers CSV export_turfbzh.</li>
    </ul>
    <p style="margin-top: 20px; font-style: italic; color: #666;">
        Sélectionnez une page dans la barre latérale pour commencer.
    </p>
</div>
""", unsafe_allow_html=True)