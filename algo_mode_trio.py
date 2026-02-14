"""
algo_mode_trio.py — Mode Trio + Folie (3+1)
"""
import streamlit as st
import pandas as pd
import numpy as np
from engine import safe_num, safe_float
from strategies import get_folie_v2
from utils_algo import colored_nums, nums_str, get_arrivee, get_confiance


def render_trio(df, courses_avec, courses_sans, date_start, date_end, folie_cote_min, folie_taux_min):

    if courses_avec:
        st_f = {'t3_2': 0, 't3_3': 0, 'folie_t3': 0, 'folie_n': 0, 'n': 0, 'mise': 0, 'gains_g': 0, 'gains_p': 0}
        st_ib = {'t3_2': 0, 't3_3': 0, 'folie_t3': 0, 'folie_n': 0, 'n': 0}
        st_hyb = {'t3_2': 0, 't3_3': 0, 'folie_t3': 0, 'folie_n': 0, 'n': 0, 'mise': 0, 'gains_g': 0, 'gains_p': 0}
        rows_export = []

        for cid in courses_avec:
            df_c = df[df['ID_C'] == cid]
            top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
            top1 = set(df_c[df_c['classement'] == 1]['Numero'].astype(int).tolist())

            trio_f = df_c.nlargest(3, 'SCORE'); nums_f = set(trio_f['Numero'].astype(int).tolist())
            folie_f = get_folie_v2(df_c, nums_f, 'score', folie_cote_min, folie_taux_min)

            trio_ib = df_c.nsmallest(3, 'IA_Borda_Rank') if 'IA_Borda_Rank' in df_c.columns else df_c.head(3)
            nums_ib = set(trio_ib['Numero'].astype(int).tolist())
            folie_ib = get_folie_v2(df_c, nums_ib, 'elo', folie_cote_min, folie_taux_min)

            trio_hyb = df_c.nlargest(3, 'HYBRIDE'); nums_hyb = set(trio_hyb['Numero'].astype(int).tolist())
            folie_hyb = get_folie_v2(df_c, nums_hyb, 'score', folie_cote_min, folie_taux_min)

            confiance = get_confiance([safe_float(trio_f, i, 'SCORE', 0.0) for i in range(3)])

            for td, sx, fd in [(trio_f, st_f, folie_f), (trio_ib, st_ib, folie_ib), (trio_hyb, st_hyb, folie_hyb)]:
                nums = set(td['Numero'].astype(int).tolist()) if len(td) else set()
                sx['n'] += 1; hit = len(nums & top3)
                if hit >= 2: sx['t3_2'] += 1
                if hit == 3: sx['t3_3'] += 1
                if not fd.empty:
                    sx['folie_n'] += 1
                    if int(fd.iloc[0]['Numero']) in top3: sx['folie_t3'] += 1

            for td, sx in [(trio_f, st_f), (trio_hyb, st_hyb)]:
                if len(td):
                    b1n = safe_num(td, 0)
                    b1c = float(td.iloc[0]['Cote']) if pd.notna(td.iloc[0].get('Cote', np.nan)) else 0
                    sx['mise'] += 2
                    if b1n in top1 and b1c > 0: sx['gains_g'] += 2 * b1c
                    for _, b in td.iterrows():
                        sx['mise'] += 1
                        bc = float(b.get('Cote', 0)) if pd.notna(b.get('Cote', np.nan)) else 0
                        if int(b['Numero']) in top3 and bc > 0: sx['gains_p'] += bc / 3

            hit_f = len(nums_f & top3); hit_h = len(nums_hyb & top3); arrivee = get_arrivee(df_c)

            def fi(fd):
                if fd.empty: return 0, 0, ""
                fn = int(fd.iloc[0]['Numero'])
                fc = round(float(fd.iloc[0]['Cote']), 1) if pd.notna(fd.iloc[0].get('Cote', np.nan)) else 0
                return fn, fc, "OUI" if fn in top3 else "NON"

            ff_n, ff_c, ff_ok = fi(folie_f); fh_n, fh_c, fh_ok = fi(folie_hyb)
            rows_export.append({
                'Course': cid, 'Conf': confiance,
                'F_N1': safe_num(trio_f, 0), 'F_N2': safe_num(trio_f, 1), 'F_N3': safe_num(trio_f, 2),
                'F_Hit': f"{hit_f}/3", 'F_Folie': ff_n, 'F_Folie_C': ff_c, 'F_Folie_OK': ff_ok,
                'H_Hit': f"{hit_h}/3", 'H_Folie': fh_n, 'H_Folie_C': fh_c, 'H_Folie_OK': fh_ok,
                'Arrivee': arrivee or ""
            })

        st.markdown("### 📊 Trio + Folie")

        def show_kpi(lbl, em, sx):
            with st.container(border=True):
                st.markdown(f"**{em} {lbl}**")
                nc = 5 if 'mise' in sx else 3; cols = st.columns(nc)
                t = sx['n']; p = lambda n: f"{round(n/t*100)}%" if t else "0%"
                cols[0].metric("2+/3", f"{sx['t3_2']}/{t}", p(sx['t3_2']))
                cols[1].metric("3/3", f"{sx['t3_3']}/{t}", p(sx['t3_3']))
                fn = sx['folie_n']; fp = lambda n: f"{round(n/fn*100)}%" if fn else "0%"
                cols[2].metric("🔥Folie", f"{sx['folie_t3']}/{fn}", fp(sx['folie_t3']))
                if 'mise' in sx and nc >= 5:
                    gt = sx['gains_g'] + sx['gains_p']
                    roi = round((gt - sx['mise']) / sx['mise'] * 100, 1) if sx['mise'] > 0 else 0
                    cols[3].metric("💰Mise", f"{sx['mise']:.0f}€")
                    cols[4].metric("📈ROI", f"{roi}%", f"{gt - sx['mise']:+.1f}€", delta_color="normal" if roi >= 0 else "inverse")

        show_kpi("Formule", "🎯", st_f); show_kpi("IA+Borda", "🤖", st_ib); show_kpi("Hybride", "⚡", st_hyb)

        st.divider()
        st.markdown(f"### 🏁 Courses ({len(courses_avec)})")
        for row in rows_export:
            cid = row['Course']; df_c = df[df['ID_C'] == cid]
            top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
            trio_f = df_c.nlargest(3, 'SCORE'); trio_hyb = df_c.nlargest(3, 'HYBRIDE')
            folie_f = get_folie_v2(df_c, set(trio_f['Numero'].astype(int).tolist()), 'score', folie_cote_min, folie_taux_min)
            folie_hyb = get_folie_v2(df_c, set(trio_hyb['Numero'].astype(int).tolist()), 'score', folie_cote_min, folie_taux_min)
            hf = int(str(row['F_Hit']).split('/')[0]); hh = int(str(row['H_Hit']).split('/')[0])
            ok = max(hf, hh) >= 2
            icon = "🥇" if max(hf, hh) == 3 else ("✅" if ok else "❌")
            with st.container(border=True):
                st.write(f"**{icon} {cid}** {row['Conf']} F:{row['F_Hit']} H:{row['H_Hit']}")
                c1, c2, c3 = st.columns([4, 4, 4])
                with c1:
                    nl = [int(r['Numero']) for _, r in trio_f.iterrows()]; ft = ""
                    if not folie_f.empty:
                        fn = int(folie_f.iloc[0]['Numero'])
                        fc = float(folie_f.iloc[0]['Cote']) if pd.notna(folie_f.iloc[0].get('Cote', np.nan)) else 0
                        ft = f"\n🔥{fn}(C:{fc}){'✓' if fn in top3 else '✗'}"
                    st.success(f"**🎯F** {row['F_Hit']}\n{colored_nums(nl, top3)}{ft}")
                with c2:
                    nl = [int(r['Numero']) for _, r in trio_hyb.iterrows()]; ft = ""
                    if not folie_hyb.empty:
                        fn = int(folie_hyb.iloc[0]['Numero'])
                        fc = float(folie_hyb.iloc[0]['Cote']) if pd.notna(folie_hyb.iloc[0].get('Cote', np.nan)) else 0
                        ft = f"\n🔥{fn}(C:{fc}){'✓' if fn in top3 else '✗'}"
                    st.info(f"**⚡H** {row['H_Hit']}\n{colored_nums(nl, top3)}{ft}")
                with c3:
                    st.warning(f"**🏁**\n### {row['Arrivee']}")

    if courses_sans:
        st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
        for cid in courses_sans:
            df_c = df[df['ID_C'] == cid]
            trio_f = df_c.nlargest(3, 'SCORE'); trio_hyb = df_c.nlargest(3, 'HYBRIDE')
            folie_f = get_folie_v2(df_c, set(trio_f['Numero'].astype(int).tolist()), 'score', folie_cote_min, folie_taux_min)
            conf = get_confiance([safe_float(trio_f, i, 'SCORE', 0.0) for i in range(3)])
            with st.container(border=True):
                st.write(f"**📍{cid}** {conf}")
                c1, c2 = st.columns(2)
                with c1:
                    txt = nums_str(trio_f)
                    if not folie_f.empty: txt += f"\n🔥N°{int(folie_f.iloc[0]['Numero'])}(C:{round(float(folie_f.iloc[0]['Cote']), 1)})"
                    st.success(f"**🎯F**\n### {txt}")
                with c2:
                    st.info(f"**⚡H**\n### {nums_str(trio_hyb)}")

    if courses_avec:
        st.download_button("📥 CSV Trio", pd.DataFrame(rows_export).to_csv(index=False, sep=';').encode('utf-8'),
                           f"export_trio_{date_start}_{date_end}.csv", "text/csv", use_container_width=True)