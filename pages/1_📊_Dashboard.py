import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_conn

# Configuration de la page
st.set_page_config(layout="wide")

# STYLE CLAIR "JOURNAL" (Texte noir, contrastes nets)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;900&display=swap');
    
    .stApp { background-color: #F8FAFC; color: #000000; font-family: 'Outfit', sans-serif; }
    
    .main-title {
        font-weight: 900; font-size: 2.5rem; color: #000000;
        border-bottom: 4px solid #3A7BD5; padding-bottom: 10px; margin-bottom: 20px;
    }

    /* Boîtes de statistiques (Metrics) */
    .stat-box {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stat-label { color: #64748B; font-size: 0.9rem; text-transform: uppercase; font-weight: 600; }
    .stat-value { color: #000000; font-size: 1.8rem; font-weight: 900; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📊 Tableau de Bord Financier</p>', unsafe_allow_html=True)

# Connexion et récupération des données
conn = get_conn()
df = pd.read_sql("SELECT * FROM paris ORDER BY date DESC", conn)

if not df.empty:
    # --- CALCULS ---
    total_mises = df['mise'].sum()
    profit_net = df['gain_net'].sum()
    roi = (profit_net / total_mises * 100) if total_mises > 0 else 0
    
    courses_jouees = len(df)
    courses_gagnees = len(df[df['resultat'] == 'Gagné'])
    courses_perdues = len(df[df['resultat'] == 'Perdu'])
    taux_reussite = (courses_gagnees / courses_jouees * 100) if courses_jouees > 0 else 0

    # --- AFFICHAGE DES MÉTRIQUES (Top Bar) ---
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        color = "#16A34A" if profit_net >= 0 else "#DC2626"
        st.markdown(f'<div class="stat-box"><div class="stat-label">Profit Net</div><div class="stat-value" style="color:{color};">{profit_net:.2f} €</div></div>', unsafe_allow_html=True)
    
    with m2:
        st.markdown(f'<div class="stat-box"><div class="stat-label">ROI (%)</div><div class="stat-value" style="color:#3A7BD5;">{roi:+.1f} %</div></div>', unsafe_allow_html=True)
    
    with m3:
        st.markdown(f'<div class="stat-box"><div class="stat-label">Jouées</div><div class="stat-value">{courses_jouees}</div></div>', unsafe_allow_html=True)
    
    with m4:
        st.markdown(f'<div class="stat-box"><div class="stat-label">Gagnées</div><div class="stat-value" style="color:#16A34A;">{courses_gagnees}</div></div>', unsafe_allow_html=True)
    
    with m5:
        st.markdown(f'<div class="stat-box"><div class="stat-label">Perdues</div><div class="stat-value" style="color:#DC2626;">{courses_perdues}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # --- GRAPHIQUES ---
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("📈 Courbe de Capital")
        # Chronologie (du plus ancien au plus récent)
        df_chrono = df.iloc[::-1].copy()
        df_chrono['cum_profit'] = df_chrono['gain_net'].cumsum()
        
        fig = px.line(df_chrono, x=df_chrono.index, y='cum_profit', 
                     title="Progression du bénéfice cumulé",
                     labels={'index': 'Nombre de paris', 'cum_profit': 'Euros (€)'})
        fig.update_traces(line_color='#3A7BD5', line_width=4)
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("🎯 Répartition W/L")
        fig_pie = px.pie(df, names='resultat', 
                        color='resultat',
                        color_discrete_map={'Gagné': '#16A34A', 'Perdu': '#DC2626', 'En cours': '#94A3B8'},
                        hole=0.6)
        fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLEAU DÉTAILLÉ ---
    st.subheader("📋 Historique des derniers paris")
    # On affiche le tableau avec texte noir sur fond blanc
    st.dataframe(df[['date', 'hippodrome', 'course_num', 'cheval', 'cote', 'mise', 'resultat', 'gain_net']], 
                 use_container_width=True, 
                 hide_index=True)

else:
    st.info("💡 Aucune donnée de pari. Enregistrez vos résultats dans 'Saisie Paris' ou importez-les.")