import streamlit as st
import pandas as pd
import numpy as np
import json
import re
from utils import run_query, get_conn
from collections import Counter

st.set_page_config(layout="wide", page_title="Debug JSON")

st.markdown('<p style="font-weight:900; font-size:2.2rem; color:#1E293B; border-bottom:4px solid #3A7BD5;">🔍 Debug - Exploration JSON</p>', unsafe_allow_html=True)

# --- Configuration ---
st.markdown("### 📅 Sélection des données")
col1, col2 = st.columns(2)
with col1:
    date_start = st.date_input("Du", value=pd.Timestamp.now() - pd.Timedelta(days=7))
with col2:
    date_end = st.date_input("Au", value=pd.Timestamp.now())

limit = st.slider("Nombre de lignes à analyser", 10, 1000, 100)

if st.button("🚀 CHARGER & ANALYSER", type="primary", use_container_width=True):
    
    # Charger les données
    query = f"""
    SELECT id, date, hippodrome, course_num, numero, cheval, cote, json_data, classement 
    FROM selections 
    WHERE date BETWEEN ? AND ? 
    AND json_data IS NOT NULL
    LIMIT {limit}
    """
    
    raw_data = run_query(query, (str(date_start), str(date_end)))
    
    if raw_data.empty:
        st.error("❌ Aucune donnée trouvée")
        st.stop()
    
    st.success(f"✅ {len(raw_data)} lignes chargées")
    
    # --- PARTIE 1: LISTE DES CHAMPS ---
    st.divider()
    st.markdown("## 📋 PARTIE 1 - Tous les champs disponibles")
    
    all_keys = Counter()
    sample_values = {}
    data_types = {}
    
    # Parser tous les JSON
    for idx, row in raw_data.iterrows():
        if row['json_data']:
            try:
                json_obj = json.loads(row['json_data'])
                for key, value in json_obj.items():
                    all_keys[key] += 1
                    
                    # Échantillons
                    if key not in sample_values:
                        sample_values[key] = []
                    if len(sample_values[key]) < 3:
                        sample_values[key].append(str(value)[:50])
                    
                    # Type
                    if key not in data_types:
                        vtype = type(value).__name__
                        # Détecter si numérique dans string
                        if vtype == 'str':
                            try:
                                float(str(value).replace(',', '.'))
                                vtype = 'numeric_str'
                            except:
                                pass
                        data_types[key] = vtype
            except Exception as e:
                st.warning(f"⚠️ Erreur ligne {idx}: {e}")
    
    # Créer tableau résumé
    fields_data = []
    for key, count in all_keys.most_common():
        pct = round(count / len(raw_data) * 100, 1)
        fields_data.append({
            'Champ': key,
            'Occurrences': f"{count}/{len(raw_data)} ({pct}%)",
            'Type': data_types.get(key, '?'),
            'Exemples': ' | '.join(sample_values.get(key, [])[:3])
        })
    
    df_fields = pd.DataFrame(fields_data)
    
    st.markdown(f"### 🎯 {len(all_keys)} champs distincts trouvés")
    
    # Filtres
    search = st.text_input("🔍 Filtrer par nom", placeholder="ex: IA, Cote, Taux, ELO...")
    
    df_display = df_fields.copy()
    if search:
        df_display = df_display[df_display['Champ'].str.contains(search, case=False, na=False)]
    
    st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)
    
    # Export liste
    with st.expander("📋 Copier-coller la liste complète"):
        numeric_fields = [k for k, v in data_types.items() if v in ['int', 'float', 'numeric_str']]
        st.code("\n".join(sorted(numeric_fields)), language="text")
    
    # --- PARTIE 2: EXEMPLE JSON BRUT ---
    st.divider()
    st.markdown("## 📄 PARTIE 2 - Exemple de JSON brut")
    
    # Prendre le premier JSON non vide
    sample_json = None
    sample_row = None
    for _, row in raw_data.iterrows():
        if row['json_data']:
            try:
                sample_json = json.loads(row['json_data'])
                sample_row = row
                break
            except:
                pass
    
    if sample_json:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Infos de la course:**")
            st.write(f"- Date: {sample_row['date']}")
            st.write(f"- Hippodrome: {sample_row['hippodrome']}")
            st.write(f"- Course: {sample_row['course_num']}")
            st.write(f"- N°: {sample_row['numero']} - {sample_row['cheval']}")
            st.write(f"- Cote: {sample_row['cote']}")
            st.write(f"- Classement: {sample_row['classement']}")
        
        with col2:
            st.markdown("**JSON complet (copier-coller):**")
            json_str = json.dumps(sample_json, indent=2, ensure_ascii=False)
            st.code(json_str, language="json", line_numbers=True)
    
    # --- PARTIE 3: CORRÉLATIONS ---
    st.divider()
    st.markdown("## 📊 PARTIE 3 - Corrélations avec le classement")
    
    if st.button("🧮 CALCULER LES CORRÉLATIONS", use_container_width=True):
        
        with st.spinner("Analyse en cours..."):
            
            # Construire dataset
            analysis_rows = []
            
            for _, row in raw_data.iterrows():
                if not row['json_data'] or not row['classement']:
                    continue
                
                try:
                    classement = int(row['classement'])
                    if classement <= 0:
                        continue
                    
                    json_obj = json.loads(row['json_data'])
                    data_row = {
                        'classement': classement,
                        'course_id': f"{row['date']}_{row['hippodrome']}_{row['course_num']}"
                    }
                    
                    # Extraire tous les champs numériques
                    for key, value in json_obj.items():
                        try:
                            # Essayer de convertir en float
                            if isinstance(value, (int, float)):
                                data_row[key] = float(value)
                            elif isinstance(value, str):
                                val_clean = value.replace(',', '.').strip()
                                if val_clean and val_clean.replace('.', '').replace('-', '').isdigit():
                                    data_row[key] = float(val_clean)
                        except:
                            pass
                    
                    analysis_rows.append(data_row)
                    
                except Exception as e:
                    continue
            
            if len(analysis_rows) < 10:
                st.error("⚠️ Pas assez de données valides pour l'analyse")
                st.stop()
            
            df_analysis = pd.DataFrame(analysis_rows)
            st.success(f"✅ {len(df_analysis)} lignes analysées sur {len(df_analysis['course_id'].unique())} courses")
            
            # Calculer corrélations
            correlations = []
            
            for col in df_analysis.columns:
                if col in ['classement', 'course_id']:
                    continue
                
                # Besoin d'au moins 10 valeurs
                valid_count = df_analysis[col].notna().sum()
                if valid_count < 10:
                    continue
                
                try:
                    corr = df_analysis['classement'].corr(df_analysis[col])
                    
                    if pd.isna(corr):
                        continue
                    
                    # Stats
                    col_data = df_analysis[col].dropna()
                    
                    # Top 3 vs Autres
                    top3 = df_analysis[df_analysis['classement'] <= 3][col].dropna()
                    others = df_analysis[df_analysis['classement'] > 3][col].dropna()
                    
                    mean_top3 = top3.mean() if len(top3) > 0 else 0
                    mean_others = others.mean() if len(others) > 0 else 0
                    
                    correlations.append({
                        'Champ': col,
                        'Corrélation': round(corr, 4),
                        'Corr_Abs': abs(corr),
                        'Prédit_Bien': '✅ OUI' if abs(corr) > 0.2 else '❌ Non',
                        'Direction': '📉 Plus haut = mieux' if corr < 0 else '📈 Plus bas = mieux',
                        'Moy_Top3': round(mean_top3, 2),
                        'Moy_Autres': round(mean_others, 2),
                        'Écart': round(abs(mean_top3 - mean_others), 2),
                        'Min': round(col_data.min(), 2),
                        'Max': round(col_data.max(), 2),
                        'Valeurs': valid_count
                    })
                    
                except Exception as e:
                    continue
            
            df_corr = pd.DataFrame(correlations).sort_values('Corr_Abs', ascending=False)
            
            # Afficher TOP 15
            st.markdown("### 🏆 TOP 15 - Meilleurs prédicteurs")
            st.caption("💡 Corrélation forte (> 0.3) = excellent prédicteur | Négatif = plus c'est haut, mieux c'est")
            
            top15 = df_corr.head(15)
            st.dataframe(
                top15[['Champ', 'Corrélation', 'Prédit_Bien', 'Direction', 'Moy_Top3', 'Moy_Autres', 'Écart']], 
                use_container_width=True, 
                hide_index=True
            )
            
            # --- SUGGESTIONS DE FORMULES ---
            st.divider()
            st.markdown("## 💡 FORMULES GÉNÉRÉES AUTOMATIQUEMENT")
            
            # Prendre top 5 avec corrélation > 0.15
            top_predictors = df_corr[df_corr['Corr_Abs'] > 0.15].head(5)
            
            if len(top_predictors) > 0:
                
                # Formule 1: Pondérée par corrélation
                formula1_parts = []
                for _, row in top_predictors.iterrows():
                    weight = round(abs(row['Corrélation']) * 100, 1)
                    # Si corrélation positive, on inverse (car classement 1 = meilleur)
                    if row['Corrélation'] > 0:
                        formula1_parts.append(f"-{row['Champ']} * {weight}")
                    else:
                        formula1_parts.append(f"{row['Champ']} * {weight}")
                
                formula1 = " + ".join(formula1_parts)
                
                with st.container(border=True):
                    st.markdown("**🎯 Formule #1 - Pure Corrélation**")
                    st.code(formula1, language="python")
                    st.caption("Basée uniquement sur les corrélations statistiques")
                
                # Formule 2: Avec Cote
                if 'Cote' in df_analysis.columns or 'cote' in df_analysis.columns:
                    formula2_parts = ["80 / (Cote if Cote > 0 else 1)"]
                    
                    for _, row in top_predictors.head(3).iterrows():
                        if row['Champ'].lower() not in ['cote', 'cote_bzh']:
                            weight = round(abs(row['Corrélation']) * 60, 1)
                            if row['Corrélation'] > 0:
                                formula2_parts.append(f"-{row['Champ']} * {weight}")
                            else:
                                formula2_parts.append(f"{row['Champ']} * {weight}")
                    
                    formula2 = " + ".join(formula2_parts)
                    
                    with st.container(border=True):
                        st.markdown("**💰 Formule #2 - Cote + Top 3**")
                        st.code(formula2, language="python")
                        st.caption("Mix cote + 3 meilleurs prédicteurs")
                
                # Formule 3: Version complexe
                formula3_parts = []
                for _, row in top_predictors.head(4).iterrows():
                    field = row['Champ']
                    weight = round(abs(row['Corrélation']) * 50, 1)
                    
                    # Utiliser rank si disponible
                    if f"{field}_Rank" in df_analysis.columns:
                        formula3_parts.append(f"(100 / {field}_Rank if {field}_Rank > 0 else 0) * {weight}")
                    else:
                        if row['Corrélation'] > 0:
                            formula3_parts.append(f"-{field} * {weight}")
                        else:
                            formula3_parts.append(f"{field} * {weight}")
                
                formula3 = " + ".join(formula3_parts)
                
                with st.container(border=True):
                    st.markdown("**🚀 Formule #3 - Hybride Rank**")
                    st.code(formula3, language="python")
                    st.caption("Utilise les Rank quand disponibles")
                
            else:
                st.warning("⚠️ Aucun prédicteur fort trouvé (corrélation < 0.15)")
            
            # Export complet
            st.divider()
            csv = df_corr.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                "📥 Télécharger l'analyse complète (CSV)",
                csv,
                f"correlations_{date_start}_{date_end}.csv",
                "text/csv",
                use_container_width=True
            )

else:
    st.info("👆 Cliquez pour commencer l'analyse de vos données JSON")
    
    st.markdown("""
    ---
    
    ### 🎯 Ce que fait cet outil:
    
    **PARTIE 1 - Liste des champs:**
    - Liste TOUS les champs présents dans vos JSON
    - Affiche des exemples de valeurs
    - Détecte les types de données
    
    **PARTIE 2 - JSON brut:**
    - Affiche un exemple complet de JSON
    - **Vous pouvez me le copier-coller** pour analyse approfondie
    
    **PARTIE 3 - Corrélations:**
    - Calcule quels champs prédisent le mieux le classement
    - Compare Top 3 vs Autres
    - **Génère automatiquement des formules optimisées**
    
    ### 💡 Comment l'utiliser:
    
    1. Sélectionnez une période (ex: 7 derniers jours)
    2. Cliquez sur "CHARGER & ANALYSER"
    3. Explorez les 3 parties
    4. Copiez les formules générées dans votre Algo Builder!
    
    ### 🔥 Astuce PRO:
    
    Si vous voyez des champs intéressants mais que les corrélations sont faibles, **copiez-moi un exemple de JSON** (Partie 2) et je créerai une formule sur-mesure ultra-optimisée!
    """)