"""
algo_mode_simple.py — Mode Simple (1 cheval) avec pastille concordance
"""
import streamlit as st
import pandas as pd
import numpy as np
from engine import safe_num, safe_float
from strategies import calculer_confiance_simple, get_pastille_simple
from utils_algo import get_arrivee


def render_simple(df, courses_avec, courses_sans, date_start, date_end,
                  filtre_pastille=None):

    if filtre_pastille is None:
        filtre_pastille = []
    pastille_map = {"🟢 Haute": "Haute", "🟡 Moyenne": "Moyenne", "🔴 Basse": "Basse"}
    pastilles_actives = [pastille_map[p] for p in filtre_pastille if p in pastille_map]

    if courses_avec:
        st_f = {'g': 0, 't3': 0, 'n': 0, 'skip': 0, 'total': 0,
                'mise_g': 0, 'gain_g': 0, 'mise_p': 0, 'gain_p': 0}
        st_ib = {'g': 0, 't3': 0, 'n': 0, 'mise_g': 0, 'gain_g': 0, 'mise_p': 0, 'gain_p': 0}
        st_hyb = {'g': 0, 't3': 0, 'n': 0, 'mise_g': 0, 'gain_g': 0, 'mise_p': 0, 'gain_p': 0}
        rows_disp = []

        for cid in courses_avec:
            df_c = df[df['ID_C'] == cid]
            top1 = set(df_c[df_c['classement'] == 1]['Numero'].astype(int).tolist())
            top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
            g_row = df_c[df_c['classement'] == 1].iloc[0] if not df_c[df_c['classement'] == 1].empty else None

            concordance, detail = calculer_confiance_simple(df_c, 'SCORE')
            unanime = detail.get('unanime', False)
            conf_icon, conf_label = get_pastille_simple(concordance, unanime)

            # Filtre pastille
            if pastilles_actives and conf_label not in pastilles_actives:
                st_f['total'] += 1
                st_f['skip'] += 1
                continue

            bf = df_c.nlargest(1, 'SCORE').iloc[0]; nf = int(bf['Numero'])
            bib = df_c.nsmallest(1, 'IA_Borda_Rank').iloc[0] if 'IA_Borda_Rank' in df_c.columns else df_c.iloc[0]; nib = int(bib['Numero'])
            bh = df_c.nlargest(1, 'HYBRIDE').iloc[0]; nh = int(bh['Numero'])

            st_f['total'] += 1

            for n, sx in [(nf, st_f), (nib, st_ib), (nh, st_hyb)]:
                sx['n'] += 1; sx['mise_g'] += 1; sx['mise_p'] += 1
                if n in top1:
                    sx['g'] += 1
                    cr = df_c[df_c['Numero'] == n]
                    if not cr.empty:
                        rsg = float(cr.iloc[0].get('Rapport_SG', 0) or 0)
                        sx['gain_g'] += rsg if rsg > 0 else (float(cr.iloc[0]['Cote']) if pd.notna(cr.iloc[0]['Cote']) else 0)
                if n in top3:
                    sx['t3'] += 1
                    cr = df_c[df_c['Numero'] == n]
                    if not cr.empty:
                        rsp = float(cr.iloc[0].get('Rapport_SP', 0) or 0)
                        sx['gain_p'] += rsp if rsp > 0 else round((float(cr.iloc[0]['Cote']) if pd.notna(cr.iloc[0]['Cote']) else 0) / 3, 1)

            def v(n):
                return "🥇" if n in top1 else ("✅" if n in top3 else "❌")

            rsg_real = float(g_row.get('Rapport_SG', 0) or 0) if g_row is not None else 0
            rsp_real = float(g_row.get('Rapport_SP', 0) or 0) if g_row is not None else 0
            rows_disp.append({
                'Course': cid, 'Conf': conf_icon, 'Conf_Label': conf_label,
                'Formule': f"{v(nf)} N°{nf}", 'IA+B': f"{v(nib)} N°{nib}",
                'Hybride': f"{v(nh)} N°{nh}",
                'Gagnant': f"N°{int(g_row['Numero'])} {g_row['Cheval']}" if g_row is not None else "?",
                'Cote': round(float(g_row['Cote']), 1) if g_row is not None and pd.notna(g_row['Cote']) else 0,
                'R.SG': rsg_real, 'R.SP': rsp_real
            })

        st.markdown("### 📊 Simple — Trouver le gagnant")

        if pastilles_actives:
            st.info(f"🎯 **Filtre pastille** : {st_f['n']} jouées / {st_f['total']} total ({st_f['skip']} skip) — {', '.join(pastilles_actives)}")

        with st.container(border=True):
            k1, k2, k3, k4, k5, k6, k7, k8, k9 = st.columns(9)
            t = st_f['n']; p = lambda n: f"{round(n/t*100)}%" if t else "0%"
            k1.metric("🎯 F Gagn.", f"{st_f['g']}/{t}", p(st_f['g']))
            k2.metric("🎯 F Top3", f"{st_f['t3']}/{t}", p(st_f['t3']))
            k3.metric("🎯 F Échec", f"{t-st_f['t3']}/{t}", p(t-st_f['t3']), delta_color="inverse")
            k4.metric("🤖 IA Gagn.", f"{st_ib['g']}/{st_ib['n']}", p(st_ib['g']) if st_ib['n'] else "0%")
            k5.metric("🤖 IA Top3", f"{st_ib['t3']}/{st_ib['n']}", p(st_ib['t3']) if st_ib['n'] else "0%")
            k6.metric("🤖 IA Échec", f"{st_ib['n']-st_ib['t3']}/{st_ib['n']}", delta_color="inverse")
            k7.metric("⚡ H Gagn.", f"{st_hyb['g']}/{st_hyb['n']}", p(st_hyb['g']) if st_hyb['n'] else "0%")
            k8.metric("⚡ H Top3", f"{st_hyb['t3']}/{st_hyb['n']}", p(st_hyb['t3']) if st_hyb['n'] else "0%")
            k9.metric("⚡ H Échec", f"{st_hyb['n']-st_hyb['t3']}/{st_hyb['n']}", delta_color="inverse")

        st.markdown("### 💰 Bilan Financier (1€ par course)")
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            for col, label, emoji, sx in [(c1, "Formule", "🎯", st_f), (c2, "IA+Borda", "🤖", st_ib), (c3, "Hybride", "⚡", st_hyb)]:
                with col:
                    roi_g = round((sx['gain_g'] - sx['mise_g']) / sx['mise_g'] * 100, 1) if sx['mise_g'] > 0 else 0
                    roi_p = round((sx['gain_p'] - sx['mise_p']) / sx['mise_p'] * 100, 1) if sx['mise_p'] > 0 else 0
                    benef_g = sx['gain_g'] - sx['mise_g']; benef_p = sx['gain_p'] - sx['mise_p']
                    st.markdown(f"**{emoji} {label}**")
                    st.markdown(f"🏆 **SG** : {sx['mise_g']:.0f}€ → {sx['gain_g']:.1f}€ → **{'🟢' if benef_g >= 0 else '🔴'} {benef_g:+.1f}€** (ROI {roi_g:+.1f}%)")
                    st.markdown(f"🥉 **SP** : {sx['mise_p']:.0f}€ → {sx['gain_p']:.1f}€ → **{'🟢' if benef_p >= 0 else '🔴'} {benef_p:+.1f}€** (ROI {roi_p:+.1f}%)")

        # Résumé pastilles
        nb_v = sum(1 for r in rows_disp if r['Conf_Label'] == 'Haute')
        nb_o = sum(1 for r in rows_disp if r['Conf_Label'] == 'Moyenne')
        nb_r = sum(1 for r in rows_disp if r['Conf_Label'] == 'Basse')
        st.caption(f"🟢 {nb_v} haute | 🟡 {nb_o} moyenne | 🔴 {nb_r} basse")

        st.divider()
        df_disp = pd.DataFrame(rows_disp)
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

    if courses_sans:
        st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
        wr = []
        for cid in courses_sans:
            df_c = df[df['ID_C'] == cid]
            concordance, detail = calculer_confiance_simple(df_c, 'SCORE')
            conf_icon, conf_label = get_pastille_simple(concordance, detail.get('unanime', False))
            if pastilles_actives and conf_label not in pastilles_actives:
                continue
            bf = df_c.nlargest(1, 'SCORE').iloc[0]
            bib = df_c.nsmallest(1, 'IA_Borda_Rank').iloc[0] if 'IA_Borda_Rank' in df_c.columns else df_c.iloc[0]
            bh = df_c.nlargest(1, 'HYBRIDE').iloc[0]
            wr.append({
                'Course': cid, 'Conf': conf_icon,
                'Formule': f"N°{int(bf['Numero'])} {bf['Cheval']}",
                'IA+B': f"N°{int(bib['Numero'])} {bib['Cheval']}",
                'Hybride': f"N°{int(bh['Numero'])} {bh['Cheval']}"
            })
        if wr:
            st.dataframe(pd.DataFrame(wr), use_container_width=True, hide_index=True)

    if courses_avec:
        st.download_button("📥 CSV", pd.DataFrame(rows_disp).to_csv(index=False, sep=';').encode('utf-8'),
                           f"export_simple_{date_start}_{date_end}.csv", "text/csv", use_container_width=True)