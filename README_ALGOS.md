# 🧪 Algo Builder — Catalogue des Formules

> Généré automatiquement le 2026-02-14 17:55
>
> Ce fichier est régénéré à chaque sauvegarde d'algo dans Algo Builder.

---

## 📦 Formules Preset (intégrées)

### 🎯 Simple Optimisé (Gagnant)

```
IA_Gagnant * 50 + Note_IA_Decimale * 2 + 50 / (Cote if Cote > 0 else 1) + Synergie_JCh * 0.2
```

**Variables :** `IA_Gagnant`, `Note_IA_Decimale`, `Cote`, `Synergie_JCh`

---

### 🎲 Duo Optimisé (Couplé)

```
(6 - Borda_Rank) * 1 + (6 - Cote_Rank) * 2 + (6 - Popularite_Rank) * 2
```

**Variables :** `Borda`, `Borda_Rank`, `Cote_Rank`, `Popularite_Rank`, `Cote`, `Popularite`

---

### 🏇 Trio Optimisé

```
IA_Multi * 40 + IA_Trio * 18 + 40 / (Cote if Cote > 0 else 1) + Taux_Place * 0.10
```

**Variables :** `IA_Trio`, `IA_Multi`, `Cote`, `Taux_Place`

---

### 📊 F11 Polyvalente

```
IA_Trio * 18 + Borda * 2.5 + Note_IA_Decimale * 2 + Synergie_JCh * 0.5 + Taux_Place * 0.12 + Taux_Victoire * 0.12 + 60 / (Cote if Cote > 0 else 1) + IA_Gagnant * 15
```

**Variables :** `IA_Gagnant`, `IA_Trio`, `Note_IA_Decimale`, `Borda`, `Cote`, `Taux_Victoire`, `Taux_Place`, `Synergie_JCh`

---

### 🔷 Borda Pure

```
Borda * 10 + 50 / (Cote if Cote > 0 else 1)
```

**Variables :** `Borda`, `Cote`

---

## 🔧 Formules Personnalisées

###  F9 - Tout-en-un

```
IA_Couple * 20 + IA_Trio * 15 + Borda * 2 + (ELO_Cheval - 1500) / 10 + Synergie_JCh * 0.4 + Taux_Place * 0.1 + TPch_90 / 15 + 70 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Couple`, `IA_Trio`, `Borda`, `Cote`, `ELO_Cheval`, `Taux_Place`, `TPch_90`, `Synergie_JCh`

---

###  formule optimale pour ton Algo Builder

```
(6 - Borda_Rank) * 1 + (6 - Cote_Rank) * 2 + (6 - Popularite_Rank) * 2
```

**Variables :** `Borda`, `Borda_Rank`, `Cote_Rank`, `Popularite_Rank`, `Cote`, `Popularite`

---

### F10 - Value Bet

```
IA_Couple * 35 + IA_Gagnant * 25 + (Cote_BZH - Cote) * 5 + 100 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Gagnant`, `IA_Couple`, `Cote`, `Cote_BZH`

---

### F4 - IA + Borda + Cote ⭐

```
IA_Couple * 30 + Borda * 2.5 + Note_IA_Decimale * 2 + 100 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Couple`, `Note_IA_Decimale`, `Borda`, `Cote`

---

### F4 - IA + Borda + Cote ⭐value

```
IA_Couple * 20 + Borda * 3.5 + Note_IA_Decimale * 2 + 100 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Couple`, `Note_IA_Decimale`, `Borda`, `Cote`

---

### F5 - Multi-indicateurs 

```
IA_Trio * 18 + Borda * 2.5 + Note_IA_Decimale * 2 + Synergie_JCh * 0.5 + Taux_Place * 0.12 + Taux_Victoire * 0.12 + 60 / (Cote if Cote > 0 else 1) + IA_Gagnant * 15
```

**Variables :** `IA_Gagnant`, `IA_Trio`, `Note_IA_Decimale`, `Borda`, `Cote`, `Taux_Victoire`, `Taux_Place`, `Synergie_JCh`

---

### Joué pastille verte couplé placé plat francais 8-12 +=3 ans

```
IA_Trio * 15 + IA_Couple * 30 + IA_Gagnant * 20 + Taux_Place * 0.12 + Borda * 2.5 + 70 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Gagnant`, `IA_Couple`, `IA_Trio`, `Borda`, `Cote`, `Taux_Place`

---

### Plat couplé gagnant claude firefox

```
IA_Trio * 15 + IA_Couple * 30 + IA_Gagnant * 20 + Taux_Place * 0.12 + Borda * 2.5 + 70 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Gagnant`, `IA_Couple`, `IA_Trio`, `Borda`, `Cote`, `Taux_Place`

---

### Plat couplé gagnant claude firefox  attelé pastille orange

```
IA_Trio * 15 + IA_Couple * 30 + IA_Gagnant * 20 + Taux_Place * 0.12 + Borda * 2.5 + 70 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Gagnant`, `IA_Couple`, `IA_Trio`, `Borda`, `Cote`, `Taux_Place`

---

### Plat couplé gagnant claude firefox  attelé plat v2

```
IA_Trio * 15 + IA_Couple * 30 + IA_Gagnant * 20 + Taux_Place * 0.12 + Borda * 2.5 + 70 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Gagnant`, `IA_Couple`, `IA_Trio`, `Borda`, `Cote`, `Taux_Place`

---

### Plat couplé gagnant claude firefox monté

```
IA_Trio * 15 + IA_Couple * 30 + IA_Gagnant * 20 + TPch_90 / 15 + Borda * 2.5 + 70 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Gagnant`, `IA_Couple`, `IA_Trio`, `Borda`, `Cote`, `TPch_90`

---

### Plat couplé gagnant claude firefox plat

```
IA_Trio * 15 + IA_Couple * 30 + IA_Gagnant * 20 + Taux_Place * 0.12 + Borda * 2.5 + 70 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Gagnant`, `IA_Couple`, `IA_Trio`, `Borda`, `Cote`, `Taux_Place`

---

### Simple

```
((IA_Gagnant * 2) + Sigma_Horse) / log(Cote + 1)
```

**Variables :** `IA_Gagnant`, `Cote`, `Sigma_Horse`

---

### Value Finder

```
((IA_Gagnant * 2) + Sigma_Horse) / log(Cote + 1)
```

**Variables :** `IA_Gagnant`, `Cote`, `Sigma_Horse`

---

### couplé v4

```
Note_IA_Decimale * 1.0 + IA_Gagnant * 60 + IA_Couple * 80 + Moy_TPch_90 * 0.1 + Synergie_JCh * 0.15 + Taux_Place * 10 + 50 / Cote + Borda * 0.12 + Turf_Points / 80 + (12 if Note_IA_Decimale_Rank == 1 else 6 if Note_IA_Decimale_Rank <= 3 else 0) + (8 if IA_Couple_Rank == 1 else 4 if IA_
```

**Variables :** `IA_Gagnant`, `IA_Couple`, `Note_IA_Decimale`, `Borda`, `IA_Couple_Rank`, `Cote`, `Taux_Place`, `Turf_Points`, `TPch_90`, `Synergie_JCh`

---

### duo 1 euro

```
Note_IA_Decimale * 2.0 + IA_Gagnant * 80 + Moy_TPch_90 / 10 + Synergie_JCh / 5 + (15 if Note_IA_Decimale_Rank == 1 else 8 if Note_IA_Decimale_Rank <= 3 else 0) + (10 if IA_Gagnant_Rank == 1 else 5 if IA_Gagnant_Rank <= 3 else 0) + 50 / Cote + Borda * 0.15
```

**Variables :** `IA_Gagnant`, `Note_IA_Decimale`, `Borda`, `Cote`, `TPch_90`, `Synergie_JCh`

---

### duov2

```
 IA_Couple * 30 + 100 / (Cote if Cote > 0 else 1)
```

**Variables :** `IA_Couple`, `Cote`

---

### premuim

```
(7 if ELO_Cheval_Rank < 2 else 3 if ELO_Cheval_Rank < 3 else 0) + (4 if ELO_Eleveur_Rank < 2 else 0) + (2 if Taux_Place >= 45 else 0) + (4 if Taux_Victoire >= 15 else 0) + (2 if IA_Trio_Rank < 2 else 6 if IA_Trio_Rank < 4 else 0)
```

**Variables :** `IA_Trio`, `IA_Trio_Rank`, `ELO_Cheval_Rank`, `ELO_Cheval`, `ELO_Eleveur`, `Taux_Victoire`, `Taux_Place`

---

### tenkakinju

```
(7 if ELO_Cheval_Rank < 2 else 3 if ELO_Cheval_Rank < 3 else 0) + (4 if ELO_Eleveur_Rank < 2 else 0) + (2 if Taux_de_Place >= 45 else 0) + (4 if Taux_de_Victoire >= 15 else 0) + (2 if IA_Trio_Rank < 2 else 6 if IA_Trio_Rank < 4 else 0)
```

**Variables :** `IA_Trio`, `IA_Trio_Rank`, `ELO_Cheval_Rank`, `ELO_Cheval`, `ELO_Eleveur`

---

### testing

```
((6 - IA_Couple_Rank) * 4 + (6 - Borda_Rank) * 2.5 + (6 - Cote_Rank) * 2 + (6 - Note_IA_Decimale_Rank) * 1.5) * (1 if IA_Couple_Rank <= 3 else 0) * (1 if Cote_Rank <= 4 else 0) * (1 if Borda_Rank <= 4 else 0)
```

**Variables :** `IA_Couple`, `Note_IA_Decimale`, `Borda`, `Borda_Rank`, `Cote_Rank`, `IA_Couple_Rank`, `Cote`

---

### trio 5 chevaux

```
IA_Trio * 18 + Borda * 2.5 + Note_IA_Decimale * 2 + Synergie_JCh * 0.5 + Taux_Place * 0.12 + Taux_Victoire * 0.12 + 60 / (Cote if Cote > 0 else 1) + IA_Gagnant * 15
```

**Variables :** `IA_Gagnant`, `IA_Trio`, `Note_IA_Decimale`, `Borda`, `Cote`, `Taux_Victoire`, `Taux_Place`, `Synergie_JCh`

---

### trioV2

```
IA_Multi * 40 + IA_Trio * 18 + 40 / (Cote if Cote > 0 else 1) + Taux_Place * 0.10
```

**Variables :** `IA_Trio`, `IA_Multi`, `Cote`, `Taux_Place`

---

### 🎯 Simple Optimisé (Gagnant) plat pastille verte

```
IA_Gagnant * 50 + Note_IA_Decimale * 2 + 50 / (Cote if Cote > 0 else 1) + Synergie_JCh * 0.2
```

**Variables :** `IA_Gagnant`, `Note_IA_Decimale`, `Cote`, `Synergie_JCh`

---

## 📖 Référence des Variables

| Variable | Description |
|----------|-------------|
| `Borda` | Score Borda (consensus classement) |
| `Borda_Rank` | Rang Borda dans la course (1=meilleur) |
| `Cote` | Cote PMU du cheval |
| `Cote_BZH` | Cote BZH (estimation) |
| `Cote_Rank` | Rang par cote (1=favori) |
| `Courses_courues` | Nombre de courses courues |
| `ELO_Cheval` | Score ELO du cheval |
| `ELO_Cheval_Rank` | Rang ELO cheval |
| `ELO_Eleveur` | Score ELO de l'éleveur |
| `ELO_Entraineur` | Score ELO de l'entraîneur |
| `ELO_Jockey` | Score ELO du jockey |
| `ELO_Proprio` | Score ELO du propriétaire |
| `Evo_Popul` | Évolution popularité |
| `IA_Couple` | Proba IA couplé (0-100) |
| `IA_Couple_Rank` | Rang IA Couple |
| `IA_Gagnant` | Proba IA de gagner (0-100) |
| `IA_Multi` | Proba IA multi (0-100) |
| `IA_Quinte` | Proba IA quinté (0-100) |
| `IA_Trio` | Proba IA trio (0-100) |
| `IA_Trio_Rank` | Rang IA Trio |
| `IMDC` | Indice de confiance IA |
| `Moy_Alloc` | Allocation moyenne des courses |
| `Note_IA_Decimale` | Note IA globale (0-10) |
| `Popularite` | Indice de popularité |
| `Popularite_Rank` | Rang popularité (1=plus joué) |
| `Repos` | Jours depuis dernière course |
| `Sigma_Horse` | Volatilité du cheval |
| `Synergie_JCh` | Synergie jockey-cheval |
| `TPch_90` | Turf Points cheval 90j |
| `Taux_Incident` | Taux d'incidents (%) |
| `Taux_Place` | Taux de placé (%) |
| `Taux_Victoire` | Taux de victoire (%) |
| `Turf_Points` | Points Turf |
| `nombre_place` | Nombre de placés |
| `nombre_victoire` | Nombre de victoires |

## 🛠️ Syntaxe des Formules

Les formules utilisent la syntaxe Python. Fonctions disponibles : `log()`, `sqrt()`, `max()`, `min()`, `abs()`.

Les variables `*_Rank` sont le rang dans la course (1 = meilleur). Pour utiliser les rangs inversés : `(6 - Variable_Rank)` donne un score de 5 pour le rang 1, 4 pour le rang 2, etc.

Division sécurisée par la cote : `50 / (Cote if Cote > 0 else 1)`

## 🎯 Conseils

**Découverte clé** : le nombre de partants est LE facteur le plus discriminant.

| Partants | Taux CG attendu |
|----------|----------------|
| 5-8 | ~23% |
| 8-10 | ~20% |
| 10-12 | ~10% |
| 14-18 | ~4% |

Formule optimale Duo : `(6 - Borda_Rank) * 1 + (6 - Cote_Rank) * 2 + (6 - Popularite_Rank) * 2` avec filtre 5-10 partants.
