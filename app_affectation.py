import streamlit as st
import pandas as pd
import random

st.title("Outil d'affectation des postes")

from datetime import datetime

import io

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=True)
    processed_data = output.getvalue()
    return processed_data

# =========================
# 📂 UPLOAD MATRICE
# =========================
st.write("## 📂 Charger matrice de matching")

matrice_file = st.file_uploader("Matrice matching", type=["csv", "xlsx"])

if matrice_file is not None:

    # Lecture fichier
    if matrice_file.name.endswith(".csv"):
        matrice = pd.read_csv(matrice_file)
    else:
        matrice = pd.read_excel(matrice_file)

    # ✅ IMPORTANT : doit être dans le if
    matrice = matrice.rename(columns={"index": "Poste"})

    # ✅ DEBUG VISUEL (ajoute ça pour vérifier)
    st.write("### Aperçu matrice")
    st.dataframe(matrice.head())

    # ✅ STRUCTURE
    postes = matrice["Poste"].astype(str)
    matching = matrice.set_index("Poste")
    personnes = list(matching.columns)

    st.success("✅ Matrice chargée")

    # =========================
    # 📂 UPLOAD COTATION
    # =========================
    st.write("## 📂 Charger cotation (capacités postes)")
    cotation_file = st.file_uploader("Cotation", type=["xlsx"])

    if cotation_file is not None:

        cotation = pd.read_excel(cotation_file)

        # =========================
        # CAPACITÉS
        # =========================
        capacite = cotation.set_index("Poste")["nombre de places"].to_dict()
        places_restantes = capacite.copy()

        # =========================
        # FONCTIONS MÉTIER
        # =========================
        def get_postes_possibles(personne):
            return [
                poste for poste in postes
                if matching.loc[poste, personne] == 0
            ]

        # nombre d’options
        nb_options = {p: len(get_postes_possibles(p)) for p in personnes}

        # tri par difficulté (moins d'options en premier)
        personnes_tries = sorted(personnes, key=lambda x: nb_options[x])

        # =========================
        # AFFECTATION
        # =========================
        affectation = {}
        non_affectes = []

        for p in personnes_tries:

            compatibles = [
                poste for poste in postes
                if matching.loc[poste, p] == 0
                and places_restantes.get(poste, 0) > 0
            ]

            if compatibles:
                poste = compatibles[0]
                affectation[p] = poste
                places_restantes[poste] -= 1

            else:
                # 🔁 tentative swap
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

                            affectation[occ] = new_poste
                            places_restantes[new_poste] -= 1
                            places_restantes[poste] += 1

                            affectation[p] = poste
                            places_restantes[poste] -= 1

                            placé = True
                            break

                    if placé:
                        break

                if not placé:
                    affectation[p] = None
                    non_affectes.append(p)

        # =========================
        # TABLEAU RESULTAT
        # =========================
        df = pd.DataFrame.from_dict(affectation, orient="index", columns=["poste"])

        df["postes_possibles_list"] = df.index.map(get_postes_possibles)
        df["nb_postes_possibles"] = df["postes_possibles_list"].apply(len)
        df["postes_possibles"] = df["postes_possibles_list"].apply(lambda x: " | ".join(x))

        # =========================
        # DIAGNOSTIC
        # =========================
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

        # =========================
        # AFFICHAGE
        # =========================
        st.subheader("📊 Résultats globaux")

        st.write("✅ Affectés :", df["poste"].notna().sum())
        st.write("❌ Non affectés :", df["poste"].isna().sum())

        # =========================
        # AFFECTÉS
        # =========================
        st.subheader("✅ Personnes affectées")

        df_affectes = df[df["poste"].notna()].reset_index()

        st.dataframe(
            df_affectes[["index", "poste", "nb_postes_possibles", "postes_possibles"]]
            .rename(columns={
                "index": "Personne",
                "poste": "Poste affecté",
                "nb_postes_possibles": "Nb options",
                "postes_possibles": "Postes possibles"
            })
        )

        # ==========================
        # TELECHARGEMENT EXCEL
        # ==========================
        df_export = df.reset_index()
        
        df_export = df_export[[
            "index",
            "poste",
            "postes_possibles",
            "nb_postes_possibles",
            "diagnostic"
        ]]

        excel_data = to_excel(df_export)

        st.download_button(
            label="📥 Télécharger le tableau en Excel",
            data=excel_data,
            file_name=f"resultats_affection_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
         
        # =========================
        # OCCUPATION
        # =========================
        st.subheader("🏭 Occupation des postes")

        occupation = df_affectes["poste"].value_counts().reset_index()
        occupation.columns = ["Poste", "Nb personnes"]

        occupation["Capacité"] = occupation["Poste"].map(capacite).fillna(0)
        occupation["Reste"] = occupation["Capacité"] - occupation["Nb personnes"]

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

        occupation = occupation.sort_values("Nb personnes", ascending=False).reset_index(drop=True)
        st.dataframe(occupation)


        # ==========================
        # TELECHARGEMENT EXCEL
        # ==========================
        
        df_occ_export = df_occupation.reset_index()
        
        df_occ_export = df_occ_export[[          
            "Poste",          
            "Nb personnes", 
            "Capacité",
            "Reste"
        ]]

        excel_occ = to_excel(df_occ_export)

        st.download_button(
            label="📥 Télécharger le tableau en Excel",
            data=excel_occ,
            file_name=f"occupation_postes_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        
        # =========================
        # CAS CRITIQUES
        # =========================
        st.subheader("⚠️ Cas critiques (≤2 options)")

        critique = df[df["nb_postes_possibles"] <= 2]

        st.dataframe(critique[["nb_postes_possibles", "postes_possibles"]])

        # =========================
        # ANALYSE
        # =========================
        st.subheader("🧠 Indicateurs")

        st.write("Taux d'affectation :", round(df["poste"].notna().mean() * 100, 1), "%")
        st.write("Personnes avec ≤2 options :", (df["nb_postes_possibles"] <= 2).sum())
        st.write("Personnes sans solution :", (df["nb_postes_possibles"] == 0).sum())

        # =========================
        # NON AFFECTÉS
        # =========================
        st.subheader("🧠 Analyse des non affectés")

        analyse = df[df["poste"].isna()]["diagnostic"].value_counts().reset_index()
        analyse.columns = ["Cause", "Nb personnes"]
        st.dataframe(analyse)

        # =========================
        # PRIORISATION ERGONOMIQUE
        # =========================
        st.subheader("🧍 Classement des postes à assouplir")

        nb_personnes_test = st.slider("Nb de personnes à tester", 1, 20, 5)

        resultats_ergo = []

        non_aff = df[
            (df["poste"].isna()) &
            (df["diagnostic"] == "🔄 Conflit d'affectation")
        ].index.tolist()

        for poste_test in postes:

            matching_sim = matching.copy()
            personnes_test = random.sample(non_aff, min(nb_personnes_test, len(non_aff)))

            for p in personnes_test:
                if poste_test in matching_sim.index:
                    matching_sim.loc[poste_test, p] = 0

            places_restantes_sim = capacite.copy()
            affectation_sim = {}

            for p in personnes_tries:
                compatibles = [
                    poste for poste in postes
                    if matching_sim.loc[poste, p] == 0
                    and places_restantes_sim.get(poste, 0) > 0
                ]

                if compatibles:
                    affectation_sim[p] = compatibles[0]
                    places_restantes_sim[compatibles[0]] -= 1
                else:
                    affectation_sim[p] = None

            nb_avant = df["poste"].notna().sum()
            nb_apres = sum(v is not None for v in affectation_sim.values())

            resultats_ergo.append({
                "Poste": poste_test,
                "Gain personnes": nb_apres - nb_avant
            })

        df_ergo = pd.DataFrame(resultats_ergo).sort_values("Gain personnes", ascending=False)

        st.dataframe(df_ergo)

else:
    st.info("👉 Charge ta matrice pour commencer")
