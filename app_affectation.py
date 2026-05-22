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

# ✅ IMPORTANT : ajouter les postes possibles
df["postes_possibles_list"] = df.index.map(get_postes_possibles)
df["nb_postes_possibles"] = df["postes_possibles_list"].apply(len)
df["postes_possibles"] = df["postes_possibles_list"].apply(lambda x: " | ".join(x))

# -------------------------
# DIAGNOSTIC DES NON AFFECTÉS
# -------------------------
def diagnostiquer(personne):
    postes_possibles = get_postes_possibles(personne)

    if len(postes_possibles) == 0:
        return "❌ Aucun poste compatible"

    postes_disponibles = [
        poste for poste in postes_possibles
        if capacite.get(poste, 0) > 0
    ]

    if len(postes_disponibles) == 0:
        return "⚠️ Postes compatibles saturés"

    return "🔄 Conflit d'affectation"

df["diagnostic"] = df.index.map(diagnostiquer)

# -------------------------
# AFFICHAGE
# -------------------------
st.subheader("📊 Résultats globaux")

st.write("✅ Affectés :", df["poste"].notna().sum())
st.write("❌ Non affectés :", df["poste"].isna().sum())

# -------------------------
# TABLEAU COMPLET DES AFFECTÉS
# -------------------------
st.subheader("✅ Personnes affectées")

df_affectes = df[df["poste"].notna()]

df_affectes_display = df_affectes.reset_index()

st.dataframe(
    df_affectes_display[["index", "poste", "nb_postes_possibles", "postes_possibles"]]
    .rename(columns={
        "index": "Personne",
        "poste": "Poste affecté",
        "nb_postes_possibles": "Nb options",
        "postes_possibles": "Postes possibles"
    })
)

# -------------------------
# OCCUPATION AVEC CAPACITÉ
# -------------------------
st.subheader("🏭 Occupation des postes")

occupation = df_affectes["poste"].value_counts().reset_index()
occupation.columns = ["Poste", "Nb personnes"]

occupation["Capacité"] = occupation["Poste"].map(capacite)
occupation["Capacité"] = occupation["Capacité"].fillna(0)

occupation["Reste"] = occupation["Capacité"] - occupation["Nb personnes"]

# ✅ ajouter postes absents
for p in capacite:
    if p not in occupation["Poste"].values:
        occupation = pd.concat([
            occupation,
            pd.DataFrame({
                "Poste": [p],
                "Nb personnes": [0],
                "Capacité": [capacite[p]],
                "Reste": [capacite[p]]
            })
        ])

occupation["Reste"] = occupation["Capacité"] - occupation["Nb personnes"]
occupation = occupation.sort_values("Nb personnes", ascending=False).reset_index(drop=True)
st.dataframe(occupation)

# -------------------------
# CAS CRITIQUES
# -------------------------
st.subheader("⚠️ Cas critiques (≤2 options)")

critique = df[df["nb_postes_possibles"] <= 2]

st.dataframe(critique[["nb_postes_possibles", "postes_possibles"]])


# -------------------------
# ANALYSE
# -------------------------
st.subheader("🧠 Indicateurs")

st.write("Taux d'affectation :", round(df["poste"].notna().mean() * 100, 1), "%")
st.write("Personnes avec ≤2 options :", (df["nb_postes_possibles"] <= 2).sum())
st.write("Personnes sans solution :", (df["nb_postes_possibles"] == 0).sum())

# -------------------------
# ANALYSE DES NON AFFECTÉS
# -------------------------
st.subheader("🧠 Analyse des non affectés")

analyse = df[df["poste"].isna()]["diagnostic"].value_counts().reset_index()
analyse.columns = ["Cause", "Nb personnes"]

st.dataframe(analyse)

nb_sans_solution = (df["nb_postes_possibles"] == 0).sum()
nb_non_affectes = df["poste"].isna().sum()

# -------------------------
# PRIORISATION ERGONOMIQUE
# -------------------------
st.subheader("🧍 Classement des postes à assouplir (contraintes)")

nb_personnes_test = st.slider("Nb de personnes à tester", 1, 20, 5)

resultats_ergo = []

# personnes non affectées
non_aff = df[
    (df["poste"].isna()) &
    (df["diagnostic"] == "🔄 Conflit d'affectation")
].index.tolist()

for poste_test in postes:

    # copie matching
    matching_sim = matching.copy()

    # on prend un échantillon de non affectés
    import random
    personnes_test = random.sample(non_aff, min(nb_personnes_test, len(non_aff)))

    # rendre compatibles artificiellement
    for p in personnes_test:
        if poste_test in matching_sim.index:
            matching_sim.loc[poste_test, p] = 0

    # relancer affectation simple
    places_restantes_sim = capacite.copy()
    affectation_sim = {}

    for p in personnes_tries:
        compatibles = [
            poste for poste in postes
            if matching_sim.loc[poste, p] == 0 and places_restantes_sim.get(poste, 0) > 0
        ]

        if compatibles:
            affectation_sim[p] = compatibles[0]
            places_restantes_sim[compatibles[0]] -= 1
        else:
            affectation_sim[p] = None

    # calcul gain
    nb_avant = df["poste"].notna().sum()
    nb_apres = sum(v is not None for v in affectation_sim.values())

    gain = nb_apres - nb_avant

    resultats_ergo.append({
        "Poste": poste_test,
        "Gain personnes": gain
    })

st.write("Nb personnes testées :", len(personnes_test))
st.write("Nb personnes en conflit :", len(non_aff))

df_ergo = pd.DataFrame(resultats_ergo)

df_ergo = df_ergo.sort_values("Gain personnes", ascending=False)

st.dataframe(df_ergo)

st.write("Sans solution théorique :", nb_sans_solution)
st.write("Non affectés :", nb_non_affectes)
st.write("Marge améliorable :", nb_non_affectes - nb_sans_solution)
