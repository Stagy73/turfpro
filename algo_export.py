"""
algo_export.py — Export des formules algo vers README et JSON
Génère un README_ALGOS.md + algos.json pour partage via Git
"""
import json
import os
from datetime import datetime
from utils_algo import FORMULES_PRESET


# Map des variables utilisables dans les formules
VARIABLES_DOC = {
    # IA
    'IA_Gagnant': "Proba IA de gagner (0-100)",
    'IA_Couple': "Proba IA couplé (0-100)",
    'IA_Trio': "Proba IA trio (0-100)",
    'IA_Multi': "Proba IA multi (0-100)",
    'IA_Quinte': "Proba IA quinté (0-100)",
    'Note_IA_Decimale': "Note IA globale (0-10)",
    'IMDC': "Indice de confiance IA",
    # Borda / Rangs
    'Borda': "Score Borda (consensus classement)",
    'Borda_Rank': "Rang Borda dans la course (1=meilleur)",
    'Cote_Rank': "Rang par cote (1=favori)",
    'Popularite_Rank': "Rang popularité (1=plus joué)",
    'IA_Couple_Rank': "Rang IA Couple",
    'IA_Trio_Rank': "Rang IA Trio",
    'ELO_Cheval_Rank': "Rang ELO cheval",
    # Cotes / Popularité
    'Cote': "Cote PMU du cheval",
    'Cote_BZH': "Cote BZH (estimation)",
    'Popularite': "Indice de popularité",
    'Evo_Popul': "Évolution popularité",
    # ELO
    'ELO_Cheval': "Score ELO du cheval",
    'ELO_Jockey': "Score ELO du jockey",
    'ELO_Entraineur': "Score ELO de l'entraîneur",
    'ELO_Proprio': "Score ELO du propriétaire",
    'ELO_Eleveur': "Score ELO de l'éleveur",
    # Performance
    'Taux_Victoire': "Taux de victoire (%)",
    'Taux_Place': "Taux de placé (%)",
    'Taux_Incident': "Taux d'incidents (%)",
    'Turf_Points': "Points Turf",
    'TPch_90': "Turf Points cheval 90j",
    'Synergie_JCh': "Synergie jockey-cheval",
    'Sigma_Horse': "Volatilité du cheval",
    # Autres
    'Courses_courues': "Nombre de courses courues",
    'nombre_victoire': "Nombre de victoires",
    'nombre_place': "Nombre de placés",
    'Repos': "Jours depuis dernière course",
    'Moy_Alloc': "Allocation moyenne des courses",
}


def generer_readme(run_query, project_root):
    """Génère README_ALGOS.md avec toutes les formules."""
    algos_db = run_query("SELECT nom, formule FROM algos ORDER BY nom")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = []
    lines.append("# 🧪 Algo Builder — Catalogue des Formules")
    lines.append("")
    lines.append(f"> Généré automatiquement le {now}")
    lines.append(">")
    lines.append("> Ce fichier est régénéré à chaque sauvegarde d'algo dans Algo Builder.")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Presets
    lines.append("## 📦 Formules Preset (intégrées)")
    lines.append("")
    for nom, formule in FORMULES_PRESET.items():
        clean_nom = nom.replace("🎯 ", "").replace("🎲 ", "").replace("🏇 ", "").replace("📊 ", "").replace("🔷 ", "")
        lines.append(f"### {nom}")
        lines.append("")
        lines.append("```")
        lines.append(formule)
        lines.append("```")
        lines.append("")
        # Extraire les variables utilisées
        vars_used = [v for v in VARIABLES_DOC if v in formule]
        if vars_used:
            lines.append("**Variables :** " + ", ".join(f"`{v}`" for v in vars_used))
            lines.append("")
        lines.append("---")
        lines.append("")
    
    # Algos custom
    if not algos_db.empty:
        lines.append("## 🔧 Formules Personnalisées")
        lines.append("")
        for _, row in algos_db.iterrows():
            lines.append(f"### {row['nom']}")
            lines.append("")
            lines.append("```")
            lines.append(row['formule'])
            lines.append("```")
            lines.append("")
            vars_used = [v for v in VARIABLES_DOC if v in row['formule']]
            if vars_used:
                lines.append("**Variables :** " + ", ".join(f"`{v}`" for v in vars_used))
                lines.append("")
            lines.append("---")
            lines.append("")
    
    # Référence variables
    lines.append("## 📖 Référence des Variables")
    lines.append("")
    lines.append("| Variable | Description |")
    lines.append("|----------|-------------|")
    for var, desc in sorted(VARIABLES_DOC.items()):
        lines.append(f"| `{var}` | {desc} |")
    lines.append("")
    
    # Syntaxe
    lines.append("## 🛠️ Syntaxe des Formules")
    lines.append("")
    lines.append("Les formules utilisent la syntaxe Python. Fonctions disponibles : `log()`, `sqrt()`, `max()`, `min()`, `abs()`.")
    lines.append("")
    lines.append("Les variables `*_Rank` sont le rang dans la course (1 = meilleur). Pour utiliser les rangs inversés : `(6 - Variable_Rank)` donne un score de 5 pour le rang 1, 4 pour le rang 2, etc.")
    lines.append("")
    lines.append("Division sécurisée par la cote : `50 / (Cote if Cote > 0 else 1)`")
    lines.append("")
    lines.append("## 🎯 Conseils")
    lines.append("")
    lines.append("**Découverte clé** : le nombre de partants est LE facteur le plus discriminant.")
    lines.append("")
    lines.append("| Partants | Taux CG attendu |")
    lines.append("|----------|----------------|")
    lines.append("| 5-8 | ~23% |")
    lines.append("| 8-10 | ~20% |")
    lines.append("| 10-12 | ~10% |")
    lines.append("| 14-18 | ~4% |")
    lines.append("")
    lines.append("Formule optimale Duo : `(6 - Borda_Rank) * 1 + (6 - Cote_Rank) * 2 + (6 - Popularite_Rank) * 2` avec filtre 5-10 partants.")
    lines.append("")
    
    content = "\n".join(lines)
    
    # Écrire le fichier
    readme_path = os.path.join(project_root, "README_ALGOS.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return readme_path, content


def generer_json(run_query, project_root):
    """Génère algos.json avec toutes les formules pour import/export."""
    algos_db = run_query("SELECT nom, formule FROM algos ORDER BY nom")
    
    data = {
        "generated": datetime.now().isoformat(),
        "presets": {nom: formule for nom, formule in FORMULES_PRESET.items()},
        "custom": {},
    }
    
    if not algos_db.empty:
        for _, row in algos_db.iterrows():
            data["custom"][row['nom']] = {
                "formule": row['formule'],
                "variables": [v for v in VARIABLES_DOC if v in row['formule']],
            }
    
    json_path = os.path.join(project_root, "algos.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return json_path, data


def auto_save_readme(run_query, project_root):
    """Appelé automatiquement après chaque sauvegarde d'algo."""
    try:
        generer_readme(run_query, project_root)
        generer_json(run_query, project_root)
        print(f"  [AUTO-SAVE] README_ALGOS.md + algos.json mis à jour")
    except Exception as e:
        print(f"  [AUTO-SAVE] Erreur: {e}")