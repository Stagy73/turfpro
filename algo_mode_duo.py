"""
algo_mode_duo.py — Mode Duo (2 chevaux) avec filtre concordance + pastille
"""
import streamlit as st
import pandas as pd
from engine import safe_num
from strategies import calculer_confiance_duo
from utils_algo import colored_nums, nums_str, get_arrivee


def get_pastille(concordance, unanime):
    """Retourne la pastille et son label."""
    if unanime:
        return "🟢", "Haute"
    elif concordance >= 4:
        return "🟡", "Moyenne"
    else:
        return "🔴", "Basse"


def render_duo(df, courses_avec, courses_sans, date_start, date_end,
               filtre_confiance_on, seuil_concordance, filtre_unanime,
               filtre_pastille=None):

    if filtre_pastille is None:
        filtre_pastille = []

    # Map pastille labels pour filtrage
    pastille_map = {
        "🟢 Haute": "Haute",
        "🟡 Moyenne": "Moyenne",
        "🔴 Basse": "Basse",
    }
    pastilles_actives = [pastille_map[p] for p in filtre_pastille if p in pastille_map]

    if courses_avec:
        st_f = {'cg': 0, 'cp': 0, 'n': 0, 'skip': 0, 'total': 0}
        st_ib = {'cg': 0, 'cp': 0, 'n': 0}
        st_hyb = {'cg': 0, 'cp': 0, 'n': 0}
        rows_export = []

        for cid in courses_avec:
            df_c = df[df['ID_C'] == cid]
            top2 = set(df_c[df_c['classement'].between(1, 2)]['Numero'].astype(int).tolist())
            top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())

            duo_f = df_c.nlargest(2, 'SCORE')
            sf = set(duo_f['Numero'].astype(int).tolist())
            duo_ib = df_c.nsmallest(2, 'IA_Borda_Rank') if 'IA_Borda_Rank' in df_c.columns else df_c.head(2)
            sib = set(duo_ib['Numero'].astype(int).tolist())
            duo_hyb = df_c.nlargest(2, 'HYBRIDE')
            sh = set(duo_hyb['Numero'].astype(int).tolist())

            concordance, detail = calculer_confiance_duo(df_c, 'SCORE')
            unanime = detail.get('unanime', False)
            conf_icon, conf_label = get_pastille(concordance, unanime)

            # --- Filtre concordance ---
            if filtre_confiance_on:
                course_jouee = unanime if filtre_unanime else concordance >= seuil_concordance
            else:
                course_jouee = True

            # --- Filtre pastille ---
            if pastilles_actives and conf_label not in pastilles_actives:
                course_jouee = False

            st_f['total'] += 1
            cg_f = sf.issubset(top2)
            cp_f = sf.issubset(top3)

            if course_jouee:
                st_f['n'] += 1
                if cg_f:
                    st_f['cg'] += 1
                if cp_f:
                    st_f['cp'] += 1
            else:
                st_f['skip'] += 1

            for sx, nums in [(st_ib, sib), (st_hyb, sh)]:
                sx['n'] += 1
                if nums.issubset(top2):
                    sx['cg'] += 1
                if nums.issubset(top3):
                    sx['cp'] += 1

            arrivee = get_arrivee(df_c)
            cg_ib = sib.issubset(top2)
            cp_ib = sib.issubset(top3)
            cg_h = sh.issubset(top2)
            cp_h = sh.issubset(top3)

            rows_export.append({
                'Course': cid,
                'Jouee': '✅' if course_jouee else '⏭️',
                'Conf': conf_icon,
                'Conf_Label': conf_label,
                'Concordance': concordance,
                'Unanime': '✅' if unanime else '',
                'F_N1': safe_num(duo_f, 0),
                'F_N2': safe_num(duo_f, 1),
                'F_CG': "OUI" if cg_f else "NON",
                'F_CP': "OUI" if cp_f else "NON",
                'IB_CG': "OUI" if cg_ib else "NON",
                'IB_CP': "OUI" if cp_ib else "NON",
                'H_CG': "OUI" if cg_h else "NON",
                'H_CP': "OUI" if cp_h else "NON",
                'Arrivee': arrivee or ""
            })

        # --- STATS ---
        st.markdown("### 📊 Duo — Couplé Gagnant / Placé")

        if filtre_confiance_on or pastilles_actives:
            pct = round(st_f['n'] / st_f['total'] * 100) if st_f['total'] > 0 else 0
            filtres = []
            if filtre_unanime:
                filtres.append("Unanimité F=IA=H")
            elif filtre_confiance_on:
                filtres.append(f"Concordance ≥ {seuil_concordance}")
            if pastilles_actives:
                filtres.append(f"Pastille: {', '.join(pastilles_actives)}")
            st.info(
                f"🎯 **Filtre actif** : {st_f['n']} jouées / {st_f['total']} total "
                f"({st_f['skip']} skip = {100-pct}%) — {' + '.join(filtres)}"
            )

        with st.container(border=True):
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            t_f = max(st_f['n'], 1)
            t_all = max(st_ib['n'], 1)
            p = lambda n, t: f"{round(n/t*100)}%" if t else "0%"
            k1.metric("🎯 F CG", f"{st_f['cg']}/{st_f['n']}", p(st_f['cg'], t_f))
            k2.metric("🎯 F CP", f"{st_f['cp']}/{st_f['n']}", p(st_f['cp'], t_f))
            k3.metric("🤖 IA CG", f"{st_ib['cg']}/{st_ib['n']}", p(st_ib['cg'], t_all))
            k4.metric("🤖 IA CP", f"{st_ib['cp']}/{st_ib['n']}", p(st_ib['cp'], t_all))
            k5.metric("⚡ H CG", f"{st_hyb['cg']}/{st_hyb['n']}", p(st_hyb['cg'], t_all))
            k6.metric("⚡ H CP", f"{st_hyb['cp']}/{st_hyb['n']}", p(st_hyb['cp'], t_all))

        st.divider()

        # --- Résumé pastilles ---
        nb_vert = sum(1 for r in rows_export if r['Conf_Label'] == 'Haute')
        nb_orange = sum(1 for r in rows_export if r['Conf_Label'] == 'Moyenne')
        nb_rouge = sum(1 for r in rows_export if r['Conf_Label'] == 'Basse')
        st.caption(
            f"🟢 {nb_vert} haute | 🟡 {nb_orange} moyenne | 🔴 {nb_rouge} basse"
        )

        # --- COURSES JOUÉES ---
        courses_jouees = [r for r in rows_export if r['Jouee'] == '✅']
        courses_skippees = [r for r in rows_export if r['Jouee'] == '⏭️']

        st.markdown(f"### 🏁 Courses jouées ({len(courses_jouees)})")
        for row in courses_jouees:
            cid = row['Course']
            df_c = df[df['ID_C'] == cid]
            top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
            duo_f = df_c.nlargest(2, 'SCORE')
            duo_ib = df_c.nsmallest(2, 'IA_Borda_Rank') if 'IA_Borda_Rank' in df_c.columns else df_c.head(2)
            duo_hyb = df_c.nlargest(2, 'HYBRIDE')
            cg_f = row['F_CG'] == "OUI"
            cp_f = row['F_CP'] == "OUI"
            icon = "🥇" if cg_f else ("✅" if cp_f else "❌")

            with st.container(border=True):
                st.write(
                    f"**{icon} {row['Conf']} {cid}** — "
                    f"Conc: {row['Concordance']} {row['Unanime']}"
                )
                c1, c2, c3, c4 = st.columns([3, 3, 3, 3])
                with c1:
                    nlist = [int(r['Numero']) for _, r in duo_f.iterrows()]
                    v = "🥇CG" if cg_f else ("✅CP" if cp_f else "❌")
                    st.success(f"**🎯 F** {v}\n{colored_nums(nlist, top3)}")
                with c2:
                    nlist = [int(r['Numero']) for _, r in duo_ib.iterrows()]
                    v = "🥇CG" if row['IB_CG'] == "OUI" else ("✅CP" if row['IB_CP'] == "OUI" else "❌")
                    st.warning(f"**🤖 IA** {v}\n{colored_nums(nlist, top3)}")
                with c3:
                    nlist = [int(r['Numero']) for _, r in duo_hyb.iterrows()]
                    v = "🥇CG" if row['H_CG'] == "OUI" else ("✅CP" if row['H_CP'] == "OUI" else "❌")
                    st.info(f"**⚡ H** {v}\n{colored_nums(nlist, top3)}")
                with c4:
                    st.write(f"**🏁**\n### {row['Arrivee']}")

        # --- COURSES SKIPPÉES ---
        if courses_skippees and (filtre_confiance_on or pastilles_actives):
            with st.expander(f"⏭️ Courses skippées ({len(courses_skippees)})", expanded=False):
                for row in courses_skippees:
                    cid = row['Course']
                    df_c = df[df['ID_C'] == cid]
                    top3 = set(df_c[df_c['classement'].between(1, 3)]['Numero'].astype(int).tolist())
                    duo_f = df_c.nlargest(2, 'SCORE')
                    cg_f = row['F_CG'] == "OUI"
                    cp_f = row['F_CP'] == "OUI"
                    icon = "🥇" if cg_f else ("✅" if cp_f else "❌")
                    nlist = [int(r['Numero']) for _, r in duo_f.iterrows()]
                    st.caption(
                        f"{icon} {row['Conf']} {cid} — "
                        f"F: {colored_nums(nlist, top3)} — "
                        f"Conc: {row['Concordance']} — {row['Arrivee']}"
                    )

    # --- EN ATTENTE ---
    if courses_sans:
        st.markdown(f"### ⏳ En attente ({len(courses_sans)})")
        for cid in courses_sans:
            df_c = df[df['ID_C'] == cid]
            duo_f = df_c.nlargest(2, 'SCORE')
            duo_hyb = df_c.nlargest(2, 'HYBRIDE')
            concordance, detail = calculer_confiance_duo(df_c, 'SCORE')
            unanime = detail.get('unanime', False)
            conf_icon, conf_label = get_pastille(concordance, unanime)

            if filtre_confiance_on:
                jouable = unanime if filtre_unanime else concordance >= seuil_concordance
            else:
                jouable = True
            if pastilles_actives and conf_label not in pastilles_actives:
                jouable = False

            with st.container(border=True):
                status = "🎯 JOUER" if jouable else "⏭️ SKIP"
                st.write(
                    f"**{conf_icon} {cid}** — {status} — "
                    f"Conc: {concordance} {'✅ Unanime' if unanime else ''}"
                )
                c1, c2 = st.columns(2)
                with c1:
                    st.success(f"**🎯 F** {nums_str(duo_f)}")
                with c2:
                    st.info(f"**⚡ H** {nums_str(duo_hyb)}")

    if courses_avec:
        st.download_button(
            "📥 CSV Duo",
            pd.DataFrame(rows_export).to_csv(index=False, sep=';').encode('utf-8'),
            f"export_duo_{date_start}_{date_end}.csv",
            "text/csv", use_container_width=True
        )