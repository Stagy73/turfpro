import streamlit as st
import pandas as pd
import json
import re
from utils import get_conn, clean_float, clean_text

st.set_page_config(layout="wide", page_title="Importation & Résultats")

st.markdown("""
<style>
    .main-title { font-weight: 900; font-size: 2.2rem; color: #1E293B; border-bottom: 4px solid #3A7BD5; padding-bottom:10px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📥 Importation & Mise à jour Résultats</p>', unsafe_allow_html=True)

file = st.file_uploader("Charger le fichier CSV (Courses ou Résultats)", type=["csv"])

if file:
    try:
        df = pd.read_csv(file, sep=';', engine='python', on_bad_lines='skip')
        st.success(f"✅ Fichier chargé : {len(df)} lignes.")
        
        cols = df.columns.tolist()
        
        # --- Auto-détection de la colonne Rank ---
        def find_col(candidates, columns):
            for c in candidates:
                if c in columns:
                    return columns.index(c)
            return 0

        with st.expander("⚙️ Configuration des colonnes", expanded=True):
            c1, c2, c3 = st.columns(3)
            m_date = c1.selectbox("Date", cols, index=find_col(['date'], cols))
            m_hippo = c2.selectbox("Hippodrome", cols, index=find_col(['hippodrome'], cols))
            m_cheval = c3.selectbox("Cheval", cols, index=find_col(['Cheval'], cols))
            
            c4, c5 = st.columns(2)
            m_num = c4.selectbox("N° Cheval", cols, index=find_col(['Numero'], cols))
            m_course = c5.selectbox("Code Course (R1C1)", cols, index=find_col(['Course'], cols))
            
            # Colonne résultat : auto-détecte Rank
            rang_options = ["--- Aucun ---"] + cols
            default_rang = 0
            for candidate in ['Rank', 'Rang', 'Arrivee', 'Classement', 'classement']:
                if candidate in cols:
                    default_rang = cols.index(candidate) + 1  # +1 car "--- Aucun ---" est en position 0
                    break
            m_rang = st.selectbox("📊 Colonne Résultat / Classement", rang_options, index=default_rang)

        # --- MODE D'IMPORT ---
        st.divider()
        mode = st.radio("Mode d'importation :", [
            "🔄 Import complet (données + résultats si disponibles)",
            "🏁 Mise à jour résultats uniquement (ne crée pas de doublons)"
        ])

        if st.button("🚀 Lancer", type="primary", use_container_width=True):
            conn = get_conn()
            success_import = 0
            success_update = 0
            skipped = 0

            for _, row in df.iterrows():
                try:
                    val_num = int(row[m_num])
                    val_date = str(row[m_date])
                    val_course = str(row[m_course])
                    
                    # Vérifier si le cheval existe déjà
                    check = conn.execute(
                        "SELECT id, classement FROM selections WHERE date=? AND course_num=? AND numero=?", 
                        (val_date, val_course, val_num)
                    ).fetchone()

                    # --- Extraction du classement depuis la colonne choisie ---
                    rang_val = 0
                    if m_rang != "--- Aucun ---":
                        raw_rang = row.get(m_rang, None)
                        if raw_rang is not None and pd.notna(raw_rang):
                            s = str(raw_rang).strip().upper()
                            if s not in ("", "D", "NR", "NP", "DAI", "DB", "AR", "T", "RET", "DIS", "SOL"):
                                match = re.search(r'\d+', s)
                                if match:
                                    rang_val = int(match.group())

                    if check:
                        # Le cheval existe déjà → mettre à jour le classement si on en a un
                        existing_classement = check[1]
                        if rang_val > 0 and (existing_classement is None or existing_classement == 0 or pd.isna(existing_classement)):
                            conn.execute(
                                "UPDATE selections SET classement = ? WHERE id = ?",
                                (rang_val, check[0])
                            )
                            success_update += 1
                        else:
                            skipped += 1
                    
                    elif mode.startswith("🔄"):
                        # Mode import complet : créer la ligne
                        raw_dict = row.to_dict()
                        clean_dict = {str(k).replace(' ', '_'): v for k, v in raw_dict.items()}
                        # Nettoyer les NaN du JSON
                        clean_dict = {k: (v if pd.notna(v) else None) for k, v in clean_dict.items()}
                        full_row_json = json.dumps(clean_dict)
                        
                        conn.execute("""INSERT INTO selections 
                            (date, hippodrome, course_num, cheval, numero, cote, json_data, classement) 
                            VALUES (?,?,?,?,?,?,?,?)""",
                            (val_date, clean_text(row[m_hippo]), val_course, 
                             clean_text(row[m_cheval]), val_num, clean_float(str(row.get('Cote', 0))), 
                             full_row_json, rang_val if rang_val > 0 else None))
                        success_import += 1
                    else:
                        # Mode résultats uniquement : on skip si le cheval n'existe pas
                        skipped += 1

                except Exception as e:
                    continue
            
            conn.commit()
            conn.close()

            # --- Résumé ---
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("📥 Nouveaux imports", success_import)
            col_r2.metric("🏁 Résultats mis à jour", success_update)
            col_r3.metric("⏭️ Ignorés (doublons)", skipped)
            
            if success_update > 0 or success_import > 0:
                st.success(f"✨ Terminé !")
                if success_update > 0:
                    st.balloons()
            else:
                st.warning("Aucune modification effectuée.")

        # --- OUTIL DE NETTOYAGE DOUBLONS ---
        with st.expander("🧹 Nettoyer les doublons existants en base"):
            st.caption("Supprime les lignes en double pour une même date/course/numéro en gardant celle avec le classement.")
            if st.button("🧹 Nettoyer les doublons", type="secondary"):
                conn = get_conn()
                # Garde l'ID avec le meilleur classement (non null > null, plus grand id en cas d'égalité)
                deleted = conn.execute("""
                    DELETE FROM selections 
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id,
                                ROW_NUMBER() OVER (
                                    PARTITION BY date, course_num, numero 
                                    ORDER BY 
                                        CASE WHEN classement IS NOT NULL AND classement != 0 THEN 0 ELSE 1 END,
                                        id DESC
                                ) as rn
                            FROM selections
                        ) WHERE rn = 1
                    )
                """).rowcount
                conn.commit()
                conn.close()
                st.success(f"🧹 {deleted} doublons supprimés !")
                st.rerun()

    except Exception as e:
        st.error(f"Erreur : {e}")
        import traceback
        st.code(traceback.format_exc())