
import streamlit as st
import pandas as pd

st.title("🧠 Outil d'affectation ergonomique")

# -------------------------
# IMPORT
# -------------------------
cotation = pd.read_excel("cotations_bilan.xlsx", engine="openpyxl")
matching = pd.read_excel("ergo_matching_3.1.xlsx", engine="openpyxl")

# -------------------------
# STRUCTURE MATCHING (COMME HTML)
# -------------------------
# lignes = postes
# colonnes = personnes

postes = matching.iloc[:,0].astype(str)
matching = matching.set_index(matching.columns[0])

personnes = list(matching.columns)

# -------------------------
# CAPACITÉS
# -------------------------
capacite = cotation.set_index("Poste")["nombre de places"].to_dict()

places_restantes = capacite.copy()

# -------------------------
# FONCTION COMPATIBILITÉ (clé)
# -------------------------
def get_postes_compatibles(personne):
    compat = []
    for i, poste in enumerate(postes):
        if poste in places_restantes and places_restantes[poste] > 0:
            if matching.loc[poste, personne] == 0:
                compat.append(poste)
    return compat

# -------------------------
# TRI DES PERSONNES (priorité)
# -------------------------
nb_options = {}

for p in personnes:
    nb_options[p] = sum(
        matching.loc[poste, p] == 0 for poste in postes
    )

personnes_tries = sorted(personnes, key=lambda x: nb_options[x])

# -------------------------
# AFFECTATION AVEC "SWAP" (comme HTML)
# -------------------------
affectation = {}
non_affectes = []

for p in personnes_tries:

    compatibles = get_postes_compatibles(p)

    # ✅ cas simple
    if compatibles:
        poste = compatibles[0]
        affectation[p] = poste
        places_restantes[poste] -= 1

    else:
        # 🔥 tentative de libération (logique HTML)
        all_compat = [
            poste for poste in postes
            if matching.loc[poste, p] == 0
        ]

        placé = False

        for poste in all_compat:
            # trouver occupant actuel
            occupantes = [
                person for person, pos in affectation.items()
                if pos == poste
            ]

            for occ in occupantes:
                # essayer de déplacer l'occupant
                alternatives = [
                    alt for alt in postes
                    if (
                        alt != poste and
                        places_restantes.get(alt,0) > 0 and
                        matching.loc[alt, occ] == 0
                    )
                ]

                if alternatives:
                    # ✅ déplacer
                    new_poste = alternatives[0]
                    affectation[occ] = new_poste
                    places_restantes[new_poste] -= 1
                    places_restantes[poste] += 1

                    # ✅ placer la personne difficile
                    affectation[p] = poste
                    places_restantes[poste] -= 1

                    placé = True
                    break

            if placé:
                break

        if not placé:
            affectation[p] = None
            non_affectes.append(p)

# -------------------------
# RESULTATS
# -------------------------
df = pd.DataFrame.from_dict(affectation, orient="index", columns=["poste"])
df["nb_options"] = df.index.map(nb_options)

# -------------------------
# DISPLAY
# -------------------------
st.subheader("📊 Résultats")

st.write("✅ Affectés :", df["poste"].notna().sum())
st.write("❌ Non affectés :", df["poste"].isna().sum())

st.subheader("⚠️ Cas critiques (≤2 options)")
st.dataframe(df[df["nb_options"] <= 2])

st.subheader("❌ Non affectés")
st.dataframe(df[df["poste"].isna()])

# -------------------------
# DEBUG optionnel
# -------------------------
# st.write(df.head())
