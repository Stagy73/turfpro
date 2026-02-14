"""
algo_mode_borda4.py — Mode Borda 4 chevaux avec pastille concordance
"""
import streamlit as st
import pandas as pd
from strategies import calculer_confiance_borda4, get_pastille_borda4
from utils_algo import get_arrivee


def render_borda4(df, courses_avec, courses_sans, date_start, date_end,
                  filtre_pastille=None):

    if filtre_pastille is None:
        filtre_pastille = []
    pastille_map = {"🟢 Haute": "Haute", "🟡 Moyenne": "Moyenne", "🔴 Basse": "Basse"}
    pastilles_actives = [pastille_map[p] for p in filtre_pastille if p in pastille_map]

    if courses_avec:
        stats = {'couple_gagnant': 0, 'couple_place': 0, 'trio_ordre': 0,
                 'trio_desordre': 0, 'total': 0, 'skip': 0, 'played': 0}
        rows_export = []

        for cid in courses_avec:
            df_c = df[df['ID_C'] == cid]
            if 'Borda' in df_c.columns and df_c['Borda'].sum() > 0:
                top4_borda = df_c.nlargest(4, 'Borda')
            elif 'Borda_Rank' in df_c.columns:
                top4_borda = df_c.nsmallest(4, 'Borda_Rank')
            else:
                continue

            concordance, detail = calculer_confiance_borda4(df_c, 'SCORE')
            unanime = detail.get('unanime', False)
            conf_icon, conf_label = get_pastille_borda4(concordance, unanime)

            stats['total'] += 1

            # Filtre pastille
            if pastilles_actives and conf_label not in pastilles_actives:
                stats['skip'] += 1
                continue

            nums_borda = [int(r['Numero']) for _, r in top4_borda.iterrows()]
            arrivee_df = df_c[df_c['classement'] > 0].sort_values('classement')
            if len(arrivee_df) < 3:
                continue

            arrivee = [int(r['Numero']) for _, r in arrivee_df.head(3).iterrows()]
            top3_set = set(arrivee)
            stats['played'] += 1
            set_borda_4 = set(nums_borda[:4])
            top2_arrivee = set(arrivee[:2])

            couple_gagnant = len(set_borda_4 & top2_arrivee) >= 2
            couple_place = len(set_borda_4 & top3_set) >= 2

            if couple_gagnant:
                stats['couple_gagnant'] += 1; stats['couple_place'] += 1; couple_ok = "🥇 Gagnant"
            elif couple_place:
                stats['couple_place'] += 1; couple_ok = "✅ Placé"
            else:
                couple_ok = "❌"

            trio_ordre = len(nums_borda) >= 3 and nums_borda[:3] == arrivee[:3]
            trio_desordre = len(set_borda_4 & top3_set) >= 3

            if trio_ordre:
                stats['trio_ordre'] += 1; stats['trio_desordre'] += 1; trio_ok = "🥇 Ordre"
            elif trio_desordre:
                stats['trio_desordre'] += 1; trio_ok = "✅ Désordre"
            else:
                trio_ok = "❌"

            rows_export.append({
                'Course': cid, 'Conf': conf_icon, 'Conf_Label': conf_label,
                'Concordance': concordance,
                'Borda_1': nums_borda[0] if len(nums_borda) > 0 else 0,
                'Borda_2': nums_borda[1] if len(nums_borda) > 1 else 0,
                'Borda_3': nums_borda[2] if len(nums_borda) > 2 else 0,
                'Borda_4': nums_borda[3] if len(nums_borda) > 3 else 0,
                'Couplé': couple_ok, 'Trio': trio_ok,
                'Arrivée': " - ".join(map(str, arrivee))
            })

        st.markdown("### 📊 Performance Borda 4 chevaux")

        if pastilles_actives:
            st.info(f"🎯 **Filtre pastille** : {stats['played']} jouées / {stats['total']} total ({stats['skip']} skip) — {', '.join(pastilles_actives)}")

        with st.container(border=True):
            k1, k2, k3, k4 = st.columns(4)
            t = stats['played']; p = lambda n: f"{round(n/t*100)}%" if t else "0%"
            k1.metric("🥇 Couplé Gagnant", f"{stats['couple_gagnant']}/{t}", p(stats['couple_gagnant']))
            k2.metric("✅ Couplé Placé", f"{stats['couple_place']}/{t}", p(stats['couple_place']))
            k3.metric("🥇 Trio Ordre", f"{stats['trio_ordre']}/{t}", p(stats['trio_ordre']))
            k4.metric("✅ Trio Désordre", f"{stats['trio_desordre']}/{t}", p(stats['trio_desordre']))

        # Résumé pastilles
        nb_v = sum(1 for r in rows_export if r['Conf_Label'] == 'Haute')
        nb_o = sum(1 for r in rows_export if r['Conf_Label'] == 'Moyenne')
        nb_r = sum(1 for r in rows_export if r['Conf_Label'] == 'Basse')
        st.caption(f"🟢 {nb_v} haute | 🟡 {nb_o} moyenne | 🔴 {nb_r} basse")

        st.divider()
        st.markdown(f"### 🏁 Détail ({len(rows_export)})")
        for row in rows_export:
            cid = row['Course']
            arrivee_nums = [int(x) for x in row['Arrivée'].split(' - ')]
            top3_set = set(arrivee_nums)
            borda_nums = [row['Borda_1'], row['Borda_2'], row['Borda_3'], row['Borda_4']]
            icon = "🥇" if "Ordre" in row['Trio'] else ("✅" if "Désordre" in row['Trio'] or "Placé" in row['Couplé'] else "❌")
            with st.container(border=True):
                st.write(f"**{icon} {row['Conf']} {cid}** — Conc:{row['Concordance']}")
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.markdown("**🔷 Top 4 Borda** — " + " — ".join(
                        [f":green[**{n}**]✓" if n in top3_set else f":red[**{n}**]✗" for n in borda_nums]
                    ))
                    st.caption(f"Couplé: {row['Couplé']} | Trio: {row['Trio']}")
                with c2:
                    st.markdown(f"**🏁** ### {row['Arrivée']}")

    if courses_sans:
        st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
        for cid in courses_sans:
            df_c = df[df['ID_C'] == cid]
            concordance, detail = calculer_confiance_borda4(df_c, 'SCORE')
            conf_icon, conf_label = get_pastille_borda4(concordance, detail.get('unanime', False))
            if pastilles_actives and conf_label not in pastilles_actives:
                continue
            if 'Borda' in df_c.columns and df_c['Borda'].sum() > 0:
                top4 = df_c.nlargest(4, 'Borda')
            elif 'Borda_Rank' in df_c.columns:
                top4 = df_c.nsmallest(4, 'Borda_Rank')
            else:
                continue
            with st.container(border=True):
                st.write(f"**{conf_icon} {cid}** — Conc:{concordance}")
                st.success(f"**🔷 Borda:** {' - '.join(str(int(r['Numero'])) for _, r in top4.iterrows())}")

    if courses_avec:
        st.download_button("📥 CSV Borda 4", pd.DataFrame(rows_export).to_csv(index=False, sep=';').encode('utf-8'),
                           f"export_borda4_{date_start}_{date_end}.csv", "text/csv", use_container_width=True)