import streamlit as st
import pandas as pd

st.title("🧠 Outil d'affectation ergonomique")

# IMPORT
cotation = pd.read_excel("cotations_bilan.xlsx", engine="openpyxl")
restrictions = pd.read_excel("restrictions_detaillees_extract_200526.xlsx", engine="openpyxl")
matching = pd.read_excel("ergo_matching_3.1.xlsx", engine="openpyxl")

# nettoyage
cotation = cotation.rename(columns={"Poste": "poste"})
restrictions = restrictions.rename(columns={"Matricule": "personne"})

matching = matching.rename(columns={"index": "personne"})
matching = matching.set_index("personne")

# capacité postes
capacite = cotation.set_index("poste")["nombre de places"].to_dict()

matching = matching.rename(columns={"index": "poste"})
matching = matching.set_index("poste")

# ✅ garder uniquement colonnes personnes
matching = matching.select_dtypes(include=['number'])

# ✅ TRANSPOSE
matching = matching.T

# ✅ maintenant :
# lignes = personnes
# colonnes = postes

# ✅ compatibilité réelle
compatibilite = (matching == 0)

# ✅ transformer en 1/0
compatibilite = compatibilite.astype(int)

nb_options = compatibilite.sum(axis=1)
personnes_tries = nb_options.sort_values().index.tolist()

# affectation
affectation = {}
places_restantes = capacite.copy()

for p in personnes_tries:
    postes_possibles = compatibilite.columns[compatibilite.loc[p] == 1]

    postes_possibles = sorted(
        postes_possibles,
        key=lambda x: places_restantes.get(x, 0),
        reverse=True
    )

    affecte = False
    for poste in postes_possibles:
        if places_restantes.get(poste, 0) > 0:
            affectation[p] = poste
            places_restantes[poste] -= 1
            affecte = True
            break

    if not affecte:
        affectation[p] = None

df_result = pd.DataFrame.from_dict(affectation, orient="index", columns=["poste"])
df_result["nb_options"] = nb_options

# UI
st.subheader("Résultats")

st.write("✅ Affectés :", df_result["poste"].notna().sum())
st.write("❌ Non affectés :", df_result["poste"].isna().sum())

st.subheader("Personnes critiques")
st.dataframe(df_result[df_result["nb_options"] <= 2])

st.subheader("Non affectés")
st.dataframe(df_result[df_result["poste"].isna()])
