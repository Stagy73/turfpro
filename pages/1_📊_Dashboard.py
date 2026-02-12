import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_conn

# Configuration de la page
st.set_page_config(layout="wide")

# STYLE (Identique au tien)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;900&display=swap');
    .stApp { background-color: #F8FAFC; color: #000000; font-family: 'Outfit', sans-serif; }
    .main-title {
        font-weight: 900; font-size: 2.5rem; color: #000000;
        border-bottom: 4px solid #3A7BD5; padding-bottom: 10px; margin-bottom: 20px;
    }
    .stat-box {
        background: white; border: 1px solid #E2E8F0; border-radius: 10px;
        padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stat-label { color: #64748B; font-size: 0.9rem; text-transform: uppercase; font-weight: 600; }
    .stat-value { color: #000000; font-size: 1.8rem; font-weight: 900; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📊 Tableau de Bord Financier</p>', unsafe_allow_html=True)

conn = get_conn()
df = pd.read_sql("SELECT * FROM paris ORDER BY date DESC", conn)

if not df.empty:
    # --- FILTRAGE DES DONNÉES ---
    # On crée un DataFrame spécifique pour les stats qui exclut les paris "En cours"
    df_stats = df[df['resultat'].isin(['Gagné', 'Perdu'])].copy()
    
    # On garde une trace des paris en cours pour information
    nb_en_cours = len(df[df['resultat'] == 'En cours'])
    mises_engagees = df[df['resultat'] == 'En cours']['mise'].sum()

    # --- CALCULS SUR LES PARIS TERMINÉS ---
    total_mises = df_stats['mise'].sum()
    profit_net = df_stats['gain_net'].sum()
    roi = (profit_net / total_mises * 100) if total_mises > 0 else 0
    
    courses_terminees = len(df_stats)
    courses_gagnees = len(df_stats[df_stats['resultat'] == 'Gagné'])
    courses_perdues = len(df_stats[df_stats['resultat'] == 'Perdu'])
    taux_reussite = (courses_gagnees / courses_terminees * 100) if courses_terminees > 0 else 0

    # --- AFFICHAGE DES MÉTRIQUES ---
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        color = "#16A34A" if profit_net >= 0 else "#DC2626"
        st.markdown(f'<div class="stat-box"><div class="stat-label">Profit Net</div><div class="stat-value" style="color:{color};">{profit_net:.2f} €</div></div>', unsafe_allow_html=True)
    
    with m2:
        st.markdown(f'<div class="stat-box"><div class="stat-label">ROI (%)</div><div class="stat-value" style="color:#3A7BD5;">{roi:+.1f} %</div></div>', unsafe_allow_html=True)
    
    with m3:
        # On affiche le total terminé, et en petit les paris en cours
        st.markdown(f'<div class="stat-box"><div class="stat-label">Terminés (En cours)</div><div class="stat-value">{courses_terminees} <span style="font-size:1rem; color:#94A3B8;">({nb_en_cours})</span></div></div>', unsafe_allow_html=True)
    
    with m4:
        st.markdown(f'<div class="stat-box"><div class="stat-label">Gagnées</div><div class="stat-value" style="color:#16A34A;">{courses_gagnees}</div></div>', unsafe_allow_html=True)
    
    with m5:
        st.markdown(f'<div class="stat-box"><div class="stat-label">Taux Réussite</div><div class="stat-value">{taux_reussite:.1f}%</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # --- GRAPHIQUES ---
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("📈 Courbe de Capital (Paris terminés)")
        # Chronologie uniquement sur les paris qui ont un impact financier réel
        df_chrono = df_stats.iloc[::-1].copy()
        df_chrono['cum_profit'] = df_chrono['gain_net'].cumsum()
        
        fig = px.line(df_chrono, x=range(len(df_chrono)), y='cum_profit', 
                     title="Bénéfice cumulé réel",
                     labels={'x': 'Nombre de paris terminés', 'cum_profit': 'Euros (€)'})
        fig.update_traces(line_color='#3A7BD5', line_width=4)
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("🎯 Répartition W/L")
        fig_pie = px.pie(df, names='resultat', 
                        color='resultat',
                        color_discrete_map={'Gagné': '#16A34A', 'Perdu': '#DC2626', 'En cours': '#94A3B8'},
                        hole=0.6)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLEAU DÉTAILLÉ (Affiche tout, y compris en cours) ---
    st.subheader("📋 Historique complet")
    st.dataframe(df[['date', 'hippodrome', 'course_num', 'cheval', 'cote', 'mise', 'resultat', 'gain_net']], 
                 use_container_width=True, 
                 hide_index=True)

else:
    st.info("💡 Aucune donnée disponible.")