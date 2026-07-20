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
        # FONCTION D'AFFECTATION
        # =========================

        def calcul_affectation(blocages=None):

            if blocages is None:
                blocages = {}

            places_restantes = capacite.copy()

            affectation = {}
            non_affectes = []

            # ----------------------
            # Personnes bloquées
            # ----------------------

            for personne, poste in blocages.items():

                if personne not in personnes:
                    continue

                if poste not in postes.values:
                    continue

                # Forçage absolu de l'affectation
                affectation[personne] = poste

                # Décompte capacité
                if poste not in places_restantes:
                    places_restantes[poste] = 0

                places_restantes[poste] -= 1
           
            # ----------------------
            # Affectation standard
            # ----------------------

            for p in personnes_tries:

                if p in affectation:
                    continue

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

                    # Tentative swap
                    all_compat = get_postes_possibles(p)

                    placé = False

                    for poste in all_compat:

                        occupantes = [
                            pers for pers, pos in affectation.items()
                            if pos == poste
                        ]

                        for occ in occupantes:

                            # ne jamais déplacer une personne bloquée
                            if occ in blocages:
                                continue

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

            return affectation

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
        affectation = calcul_affectation()

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

        # AFFECTES
        
        df_export = df[df["poste"].notna()].copy()
        df_export = df_export.reset_index()
        df_export = df_export.rename(columns={"index": "Matricule"})
        
        df_export = df_export[[
            "Matricule",
            "poste",
            "postes_possibles",
            "nb_postes_possibles",
        ]]

        excel_data = to_excel(df_export)

        st.download_button(
            label="📥 Télécharger le tableau en Excel",
            data=excel_data,
            file_name=f"resultats_affection_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # NON AFFECTES

        df_non_affectes = df[df["poste"].isna()].copy()
        df_non_affectes = df_non_affectes.dropna(how="all")
        df_non_affectes = df_non_affectes.reset_index()
        df_non_affectes = df_non_affectes.rename(columns={"index": "Matricule"})

        
        df_non_affectes = df_non_affectes[[
            "Matricule",
            "postes_possibles",
            "nb_postes_possibles",
            "diagnostic"
        ]]

        st.download_button(
            "📥 Télécharger les non affectés",
            to_excel(df_non_affectes),
            "non_affectes.xlsx"
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
        
        df_occ_export = occupation.copy()
        
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
        # SIMULATION AVEC BLOCAGES
        # =========================

        st.subheader("🔒 Simulation avec personnes bloquées")

        blocage_file = st.file_uploader(
            "Charger le fichier de blocage",
            type=["xlsx"],
            key="blocage"
        )

        if blocage_file is not None:

            # -------------------------
            # Lecture du fichier
            # -------------------------

            df_blocage = pd.read_excel(blocage_file)

            st.write("### Personnes bloquées chargées")
            st.dataframe(df_blocage)

            blocages = dict(
                zip(
                    df_blocage["Matricule"].astype(str).str.strip(),
                    df_blocage["poste bloqué"].astype(str).str.strip()
                )
            )

            # -------------------------
            # Vérification simple
            # -------------------------

            blocages_valides = {}

            for personne, poste in blocages.items():

                if personne not in personnes:
                    st.warning(f"{personne} absent de la matrice")
                    continue

                if poste not in postes.values:
                    st.warning(f"{poste} absent de la matrice")
                    continue

                # IMPORTANT :
                # on ne vérifie PAS le matching
                # le blocage est forcé

                blocages_valides[personne] = poste

            blocages = blocages_valides

            # -------------------------
            # Recalcul complet
            # -------------------------

            affectation_bloquee = calcul_affectation(blocages)

            # -------------------------
            # Création du dataframe
            # -------------------------

            df_bloque = pd.DataFrame.from_dict(
                affectation_bloquee,
                orient="index",
                columns=["poste"]
            )

            # mêmes colonnes que le tableau principal
            
            def get_postes_possibles_blocage(personne):

                if personne in blocages:
                    return [blocages[personne]]

                return [
                    poste
                    for poste in postes
                    if matching.loc[poste, personne] == 0
                ]
            
            df_bloque["postes_possibles_list"] = (
                df_bloque.index.map(get_postes_possibles_blocage)
            )

            st.write("### Vérification des blocages")

            for personne, poste in blocages.items():

                if personne in matching.columns and poste in matching.values:

                    st.write(
                        f"{personne} -> {poste} | matching = "
                        f"{matching.loc[poste, personne]}"
                    )

                else:

                    st.warning(
                        f"{personne} ou {poste} introuvable"
                    )


            df_bloque["nb_postes_possibles"] = (
                df_bloque["postes_possibles_list"]
                .apply(len)
            )

            df_bloque["postes_possibles"] = (
                df_bloque["postes_possibles_list"]
                .apply(lambda x: " | ".join(x))
            )

            df_bloque["blocage"] = (
                df_bloque.index.isin(blocages.keys())
            )

            # -------------------------
            # RESULTAT PRINCIPAL
            # -------------------------

            st.subheader("✅ Résultat avec blocages")

            df_bloque_affiches = (
                df_bloque[df_bloque["poste"].notna()]
                .reset_index()
            )

            df_bloque_affiches = df_bloque_affiches.rename(
                columns={
                    "index": "Matricule",
                    "poste": "Poste affecté",
                    "nb_postes_possibles": "Nb options",
                    "postes_possibles": "Postes possibles",
                    "blocage": "Blocage"
                }
            )

            st.dataframe(
                df_bloque_affiches[
                    [
                        "Matricule",
                        "Poste affecté",
                        "Blocage",
                        "Nb options",
                        "Postes possibles"
                    ]
                ]
            )

            # -------------------------
            # EXPORT EXCEL
            # -------------------------

            export_blocage = (
                df_bloque_affiches[
                    [
                        "Matricule",
                        "Poste affecté",
                        "Blocage",
                        "Nb options",
                        "Postes possibles"
                    ]
                ]
            )

            st.download_button(
                label="📥 Télécharger les affectations avec blocages",
                data=to_excel(export_blocage),
                file_name=f"affectations_avec_blocages_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            

            # -------------------------
            # NON AFFECTES APRES BLOCAGES
            # -------------------------

            df_non_affectes_blocage = df_bloque[
                df_bloque["poste"].isna()
            ].copy()

            df_non_affectes_blocage = (
                df_non_affectes_blocage
                .reset_index()
            )

            df_non_affectes_blocage = (
                df_non_affectes_blocage.rename(
                    columns={
                        "index": "Matricule"
                    }
                )
            )

            # Colonnes identiques à l'export non affectés initial

            df_non_affectes_blocage = (
                df_non_affectes_blocage[
                    [
                        "Matricule",
                        "postes_possibles",
                        "nb_postes_possibles"
                    ]
                ]
            )

            st.subheader("❌ Non affectés après blocages")
            st.dataframe(df_non_affectes_blocage)
            
            st.download_button(
                label="📥 Télécharger les non affectés avec blocages",
                data=to_excel(df_non_affectes_blocage),
                file_name=f"non_affectes_avec_blocages_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # -------------------------
            # COMPARAISON
            # -------------------------

            comparaison = pd.DataFrame({
                "Poste initial": df["poste"],
                "Poste bloqué": df_bloque["poste"]
            })

            comparaison["Changement"] = (
                comparaison["Poste initial"]
                != comparaison["Poste bloqué"]
            )

            comparaison["Bloqué"] = (
                comparaison.index.isin(blocages.keys())
            )

            score_initial = df["poste"].notna().sum()
            score_bloque = df_bloque["poste"].notna().sum()

            nb_changements = (
                comparaison["Changement"] == True
            ).sum()

            nb_blocages = len(blocages)

            # -------------------------
            # KPI
            # -------------------------

            st.subheader("📊 Comparaison des scénarios")

            col1, col2, col3, col4, col5 = st.columns(5)

            col1.metric(
                "Affectés avant",
                int(score_initial)
            )

            col2.metric(
                "Affectés après",
                int(score_bloque)
            )

            col3.metric(
                "Impact",
                int(score_bloque - score_initial)
            )

            col4.metric(
                "Personnes bloquées",
                int(nb_blocages)
            )

            col5.metric(
                "Personnes déplacées",
                int(nb_changements)
            )

            # -------------------------
            # DETAIL DES CHANGEMENTS
            # -------------------------

            comparaison = comparaison.reset_index()

            comparaison.rename(
                columns={
                    "index": "Matricule"
                },
                inplace=True
            )

            st.subheader("⚠️ Affectations modifiées")

            changements = comparaison[
                comparaison["Changement"] == True
            ]

            st.dataframe(changements)

            # -------------------------
            # EXPORT COMPARAISON
            # -------------------------

            st.download_button(
                label="📥 Télécharger la comparaison",
                data=to_excel(comparaison),
                file_name=f"comparaison_blocages_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )   


else:
    st.info("👉 Charge ta matrice pour commencer")
