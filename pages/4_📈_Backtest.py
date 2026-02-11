import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_conn

# Configuration de la page
st.set_page_config(layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;900&display=swap');
    .stApp { background-color: #F8FAFC; color: #000; font-family: 'Outfit', sans-serif; }
    .main-title { font-weight: 900; font-size: 2.5rem; color: #000; border-bottom: 3px solid #3A7BD5; }
    .stat-card { background: white; padding: 20px; border-radius: 10px; border: 1px solid #E2E8F0; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📈 Backtest Stratégique</p>', unsafe_allow_html=True)

# Chargement des données de paris (résultats réels)
conn = get_conn()
df = pd.read_sql("SELECT * FROM paris", conn)

if not df.empty:
    st.sidebar.header("⚙️ Paramètres du Test")
    
    # Filtres de simulation
    cote_min = st.sidebar.slider("Cote Minimum", 1.0, 50.0, 2.0)
    cote_max = st.sidebar.slider("Cote Maximum", 1.0, 100.0, 20.0)
    
    # Sélection de l'hippodrome
    hippos = ["Tous"] + sorted(df['hippodrome'].unique().tolist())
    hippo_filter = st.sidebar.selectbox("Filtrer par Hippodrome", hippos)

    # Application des filtres
    df_bt = df[(df['cote'] >= cote_min) & (df['cote'] <= cote_max)].copy()
    if hippo_filter != "Tous":
        df_bt = df_bt[df_bt['hippodrome'] == hippo_filter]

    if not df_bt.empty:
        # Calculs
        total_paris = len(df_bt)
        profit_total = df_bt['gain_net'].sum()
        total_mise = df_bt['mise'].sum()
        roi = (profit_total / total_mise * 100) if total_mise > 0 else 0
        win_rate = (len(df_bt[df_bt['resultat'] == 'Gagné']) / total_paris * 100)

        # Affichage des métriques
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Profit Simulé", f"{profit_total:.2f} €")
        c2.metric("ROI Simulé", f"{roi:.1f} %")
        c3.metric("Taux de réussite", f"{win_rate:.1f} %")
        c4.metric("Nb de Paris", total_paris)

        # Graphique de profit cumulé
        st.subheader("📈 Courbe de profit de la stratégie")
        df_bt = df_bt.reset_index()
        df_bt['cum_profit'] = df_bt['gain_net'].cumsum()
        
        fig = px.line(df_bt, x=df_bt.index, y='cum_profit', 
                     labels={'index': 'Nombre de paris', 'cum_profit': 'Profit cumulé (€)'},
                     title=f"Simulation : Cotes entre {cote_min} et {cote_max}")
        fig.update_traces(line_color='#1E40AF', line_width=3)
        st.plotly_chart(fig, use_container_width=True)

        # Détails des paris filtrés
        with st.expander("Voir le détail des paris de cette stratégie"):
            st.dataframe(df_bt[['date', 'hippodrome', 'course_num', 'cheval', 'cote', 'resultat', 'gain_net']], use_container_width=True)
    else:
        st.warning("⚠️ Aucun pari dans votre historique ne correspond à ces critères de cote.")
else:
    st.info("💡 Pour lancer un Backtest, vous devez d'abord avoir des paris enregistrés dans votre base de données (via l'onglet Saisie ou l'Import des résultats).")