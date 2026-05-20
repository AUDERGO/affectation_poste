import streamlit as st
import pandas as pd

st.title("🧠 Outil d'affectation ergonomique")

# -------------------------
# IMPORT
# -------------------------
cotation = pd.read_excel("cotations_bilan.xlsx", engine="openpyxl")
matching = pd.read_excel("ergo_matching_3.1.xlsx", engine="openpyxl")

# -------------------------
# STRUCTURE MATCHING
# -------------------------
# lignes = postes
# colonnes = personnes

postes = matching.iloc[:, 0].astype(str)
matching = matching.set_index(matching.columns[0])
personnes = list(matching.columns)

# -------------------------
# CAPACITÉS
# -------------------------
capacite = cotation.set_index("Poste")["nombre de places"].to_dict()
places_restantes = capacite.copy()

# -------------------------
# FONCTIONS MÉTIER
# -------------------------
def get_postes_possibles(personne):
    return [
        poste for poste in postes
        if matching.loc[poste, personne] == 0
    ]

# nombre d’options
nb_options = {p: len(get_postes_possibles(p)) for p in personnes}

# tri par difficulté (moins d'options en premier)
personnes_tries = sorted(personnes, key=lambda x: nb_options[x])

# -------------------------
# AFFECTATION AVEC RÉORGANISATION
# -------------------------
affectation = {}
non_affectes = []

for p in personnes_tries:

    compatibles = [
        poste for poste in postes
        if matching.loc[poste, p] == 0 and places_restantes.get(poste, 0) > 0
    ]

    # ✅ affectation simple
    if compatibles:
        poste = compatibles[0]
        affectation[p] = poste
        places_restantes[poste] -= 1

    else:
        # 🔥 tentative de "swap"
        all_compat = get_postes_possibles(p)

        placé = False

        for poste in all_compat:

            occupantes = [
                pers for pers, pos in affectation.items()
                if pos == poste
            ]

            for occ in occupantes:

                alternatives = [
                    alt for alt in postes
                    if (
                        alt != poste
                        and places_restantes.get(alt, 0) > 0
                        and matching.loc[alt, occ] == 0
                    )
                ]

                if alternatives:
                    new_poste = alternatives[0]

                    # déplacer occupant
                    affectation[occ] = new_poste
                    places_restantes[new_poste] -= 1
                    places_restantes[poste] += 1

                    # placer personne difficile
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
# DATAFRAME RESULTATS
# -------------------------
df = pd.DataFrame.from_dict(affectation, orient="index", columns=["poste"])
df["nb_options"] = df.index.map(nb_options)

# ✅ IMPORTANT : ajouter les postes possibles
df["postes_possibles_list"] = df.index.map(get_postes_possibles)
df["nb_postes_possibles"] = df["postes_possibles_list"].apply(len)

# version texte (facultative)
df["postes_possibles"] = df["postes_possibles_list"].apply(lambda x: " | ".join(x))

# -------------------------
# AFFICHAGE
# -------------------------
st.subheader("📊 Résultats globaux")

st.write("✅ Affectés :", df["poste"].notna().sum())
st.write("❌ Non affectés :", df["poste"].isna().sum())

# -------------------------
# CAS CRITIQUES
# -------------------------
st.subheader("⚠️ Cas critiques (≤2 options)")

critique = df[df["nb_postes_possibles"] <= 2]

st.dataframe(critique[["nb_postes_possibles", "postes_possibles"]])

# -------------------------
# NON AFFECTÉS (DETAIL CLAIR)
# -------------------------
st.subheader("❌ Non affectés")

for personne, row in df[df["poste"].isna()].iterrows():
    st.write("👤", personne)
    st.write("Nb options :", row["nb_postes_possibles"])
    st.write("Postes possibles :")

    for p in row["postes_possibles_list"]:
        st.write("➡️", p)

    st.write("---")

# -------------------------
# ANALYSE
# -------------------------
st.subheader("🧠 Indicateurs")

st.write("Taux d'affectation :", round(df["poste"].notna().mean() * 100, 1), "%")
st.write("Personnes avec ≤2 options :", (df["nb_postes_possibles"] <= 2).sum())
st.write("Personnes sans solution :", (df["nb_postes_possibles"] == 0).sum())
