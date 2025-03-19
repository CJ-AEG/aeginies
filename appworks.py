import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options
from tqdm import tqdm
import plotly.express as px

# ✅ Titre de l'application
st.set_page_config(layout="wide")
st.title("Analyse des Z-Scores - Prototype SaaS")

# ✅ Déclaration globale du dataframe
global df
df = pd.DataFrame()

# ✅ Fonction de cache pour stocker le fichier en mémoire temporaire
@st.cache_data
def load_data(file):
    df = pd.read_excel(file, sheet_name="Sheet1")
    return df

# ✅ Zone pour uploader un fichier Excel
uploaded_file = st.file_uploader("Importer un fichier Excel", type=["xlsx"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.success("✅ Fichier chargé avec succès !")

# ✅ Affichage des données importées AVANT traitement
if not df.empty:
    st.write("### 🔎 Données importées :")
    st.dataframe(df)

# ✅ Fonction pour récupérer les derniers IDs depuis l'API INIES
def fetch_latest_inies_data():
    url = "https://base-inies.fr/api/SearchProduits"
    payload = {
        "typeDeclaration": 0,
        "cov": 0,
        "onlineDate": 0,
        "lieuProduction": 0,
        "perfUF": 0,
        "norme": 0,
        "onlyArchive": False
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list):
                st.success(f"✅ {len(data)} IDs INIES récupérés avec succès !")
                return [str(item) for item in data]
            else:
                st.warning("⚠️ Format de données inattendu.")
                return []
        except json.JSONDecodeError:
            st.error("⚠️ Erreur de décodage JSON.")
            return []
    else:
        st.error(f"❌ Erreur d'accès à l'API INIES : {response.status_code} {response.reason}")
        return []

# ✅ Fonction de mise à jour des données (CORRECTION portée de df)
def update_inies_data():
    global df
    latest_ids = fetch_latest_inies_data()
    if not latest_ids:
        return
    
    if df.empty:
        existing_ids = set()
    else:
        existing_ids = set(df['ID INIES'].astype(str))

    new_entries = set(map(str, latest_ids)) - existing_ids

    if new_entries:
        st.info(f"🔄 Mise à jour en cours avec {len(new_entries)} nouveaux produits...")

        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Edge(options=options)

        product_data = []
        for id_inies in tqdm(new_entries, desc="Extraction"):
            try:
                driver.get(f"https://base-inies.fr/consultation/infos-produit/{id_inies}")
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="workSpace"]'))
                )
                time.sleep(2)

                # ✅ Produit
                try:
                    product_name = driver.find_element(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[3]/informations-generales-read-only/div/div[1]/div[2]/span[1]').text.strip()
                except:
                    product_name = "Nom introuvable"

                # ✅ Durée de vie (gestion d'erreur)
                try:
                    duree_vie = driver.find_element(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[3]/unite-fonctionnelle-read-only/div/div[3]/div[2]/span').text.strip().replace('ans', '').strip()
                    duree_vie = float(duree_vie) if duree_vie != '' else np.nan
                except:
                    duree_vie = np.nan

                # ✅ Impact CO2 + D-bénéfices (gestion d'erreur)
                try:
                    headers = driver.find_elements(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[3]/indicateurs-read-only//table/thead/tr/th')
                    columns = {header.text.strip(): idx + 1 for idx, header in enumerate(headers)}

                    impact_co2 = driver.find_element(By.XPATH, f'//*[@id="workSpace"]/div/infos-produit/div/div[3]/indicateurs-read-only//table/tbody/tr[1]/td[{columns["Total cycle de vie"]}]/span').text.strip()
                    impact_co2 = float(impact_co2) if impact_co2 != '-' else 0

                    d_benefices = driver.find_element(By.XPATH, f'//*[@id="workSpace"]/div/infos-produit/div/div[3]/indicateurs-read-only//table/tbody/tr[1]/td[{columns["D-Bénéfices et charges au-delà des frontières du système"]}]/span').text.strip()
                    d_benefices = float(d_benefices) if d_benefices != '-' else 0

                except:
                    impact_co2 = 0
                    d_benefices = 0

                product_data.append([id_inies, product_name, duree_vie, impact_co2, d_benefices])

            except Exception as e:
                st.warning(f"⚠️ Erreur lors de l'extraction de l'ID {id_inies} : {e}")

        driver.quit()

        new_df = pd.DataFrame(product_data, columns=['ID INIES', 'Nom du produit', 'Durée de Vie', 'Impact CO₂ (kg)', 'D-Bénéfices'])
        df = pd.concat([df, new_df], ignore_index=True)
        st.success("✅ Base de données mise à jour avec succès !")

# ✅ Traitement des données après recherche
def process_data(filtered_data):
    if filtered_data.empty:
        st.warning("⚠️ Aucun élément trouvé.")
        return

    # ✅ Conversion explicite en float (gestion d'erreur)
    filtered_data['Impact CO₂ (kg)'] = pd.to_numeric(filtered_data['Impact CO₂ (kg)'], errors='coerce').fillna(0)
    filtered_data['D-Bénéfices'] = pd.to_numeric(filtered_data['D-Bénéfices'], errors='coerce').fillna(0)

    # ✅ Conversion de la Durée de Vie en float
    filtered_data['Durée de Vie'] = pd.to_numeric(filtered_data['Durée de Vie'].str.replace('ans', '').str.strip(), errors='coerce').fillna(50)

    # ✅ Calcul de l'Impact total et de l'Impact normalisé
    filtered_data['Impact total'] = filtered_data['Impact CO₂ (kg)'] + filtered_data['D-Bénéfices']
    filtered_data['Impact normalisé'] = filtered_data['Impact total'] * (50 / filtered_data['Durée de Vie'])

    # ✅ Calcul du Z-Score
    mean = filtered_data['Impact normalisé'].mean()
    std = filtered_data['Impact normalisé'].std()
    filtered_data['Z-Score'] = (filtered_data['Impact normalisé'] - mean) / std

    # ✅ Catégorisation basée sur le Z-Score
    filtered_data['Catégorie'] = pd.cut(
        filtered_data['Z-Score'],
        bins=[-np.inf, -1, 1, np.inf],
        labels=['Bas carbone', 'Intermédiaire', 'Haut carbone']
    ).astype(str)  # ➡️ Convertir en str pour accepter les modifications dynamiques

    # ✅ Marquer la valeur maximale et minimale
    max_idx = filtered_data['Z-Score'].idxmax()
    min_idx = filtered_data['Z-Score'].idxmin()

    if not filtered_data.empty:
        # ✅ Forcer la conversion en str pour accepter les nouvelles catégories
        filtered_data.loc[max_idx, 'Catégorie'] = f"{filtered_data.loc[max_idx, 'Catégorie']} (Valeur maximale)"
        filtered_data.loc[min_idx, 'Catégorie'] = f"{filtered_data.loc[min_idx, 'Catégorie']} (Valeur minimale)"

    # ✅ Affichage du tableau final
    st.write("### ✅ Résultats après traitement des données :")
    st.dataframe(filtered_data)

    # ✅ Affichage du graphique Z-Score
    fig = px.histogram(
        filtered_data,
        x='Z-Score',
        nbins=20,
        color='Catégorie',
        color_discrete_map={
            'Bas carbone': '#2ca02c',     # Vert
            'Intermédiaire': '#ff7f0e',   # Orange
            'Haut carbone': '#d62728',    # Rouge
            'Bas carbone (Valeur minimale)': '#1f77b4', 
            'Haut carbone (Valeur maximale)': '#9467bd'
        }
    )
    fig.update_xaxes(range=[-3, 3])
    st.plotly_chart(fig)

# ✅ Boutons
if st.sidebar.button("🔄 Mettre à jour"):
    update_inies_data()

# Champ de recherche
search_term = st.text_input("Type d'élément à afficher (exemple : Plancher bois)")

if search_term:
    if df is not None and not df.empty:
        # ✅ Recherche intelligente (AND) basée sur chaque mot-clé
        terms = search_term.split()
        filtered_data = df[
            np.logical_and.reduce([df['Nom du produit'].str.contains(term, case=False, na=False) for term in terms])
        ]

        if filtered_data.empty:
            st.warning("⚠️ Aucun résultat trouvé.")
        else:
            st.write(f"### 🔎 {len(filtered_data)} résultats trouvés :")
            st.dataframe(filtered_data)

            # ✅ Lancer le traitement uniquement après une recherche réussie
            if st.button("🔎 Traiter les données"):
                process_data(filtered_data)
    else:
        st.warning("⚠️ Veuillez d'abord charger un fichier Excel valide avant de lancer une recherche.")