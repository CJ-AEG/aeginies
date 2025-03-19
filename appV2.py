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
st.title("Analyse des Z-Scores - Aeginies")

# ✅ Déclaration globale du dataframe
global df
df = pd.DataFrame()

# ✅ Fonction pour charger automatiquement depuis GitHub
@st.cache_data
def load_data_from_repo():
    url = 'https://raw.githubusercontent.com/CJ-AEG/aeginies/main/base_inies_complete.xlsx'
    df = pd.read_excel(url, sheet_name="Sheet1")
    return df

# ✅ Fonction de cache pour le fichier uploadé
@st.cache_data
def load_data(file):
    df = pd.read_excel(file, sheet_name="Sheet1")
    return df

# ✅ Zone pour uploader un fichier Excel (optionnel)
uploaded_file = st.file_uploader("📂 Importer un fichier Excel", type=["xlsx"])

# ✅ Chargement des données depuis GitHub si aucun fichier n'est uploadé
if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.success("✅ Fichier chargé depuis le téléchargement !")
else:
    df = load_data_from_repo()
    st.success("✅ Base de données chargée automatiquement depuis le dépôt GitHub !")

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

# ✅ Fonction de mise à jour des données
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

                # ✅ Durée de vie
                try:
                    duree_vie = driver.find_element(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[3]/unite-fonctionnelle-read-only/div/div[3]/div[2]/span').text.strip().replace('ans', '').strip()
                    duree_vie = float(duree_vie) if duree_vie != '' else np.nan
                except:
                    duree_vie = np.nan

                # ✅ Impact CO2 + D-bénéfices
                try:
                    impact_co2 = float(driver.find_element(By.XPATH, '...').text)
                    d_benefices = float(driver.find_element(By.XPATH, '...').text)
                except:
                    impact_co2 = 0
                    d_benefices = 0

                product_data.append([id_inies, product_name, duree_vie, impact_co2, d_benefices])

            except Exception as e:
                st.warning(f"⚠️ Erreur lors de l'extraction de l'ID {id_inies} : {e}")

        driver.quit()

        new_df = pd.DataFrame(product_data, columns=['ID INIES', 'Nom du produit', 'Durée de Vie', 'Impact CO₂ (kg)', 'D-Bénéfices'])
        df = pd.concat([df, new_df], ignore_index=True).drop_duplicates(subset=['ID INIES'], keep='last')
        st.success("✅ Base de données mise à jour avec succès !")

# ✅ Fonction de traitement après recherche
def process_data(filtered_data):
    if filtered_data.empty:
        st.warning("⚠️ Aucun élément trouvé.")
        return

    # ✅ Conversion explicite en float (gestion d'erreur)
    filtered_data['Impact CO₂ (kg)'] = pd.to_numeric(filtered_data['Impact CO₂ (kg)'], errors='coerce').fillna(0)
    filtered_data['D-Bénéfices'] = pd.to_numeric(filtered_data['D-Bénéfices'], errors='coerce').fillna(0)

    filtered_data['Impact total'] = filtered_data['Impact CO₂ (kg)'] + filtered_data['D-Bénéfices']

    # ✅ Z-Score
    mean = filtered_data['Impact total'].mean()
    std = filtered_data['Impact total'].std()
    filtered_data['Z-Score'] = (filtered_data['Impact total'] - mean) / std

    # ✅ Catégorisation
    filtered_data['Catégorie'] = pd.cut(
        filtered_data['Z-Score'],
        bins=[-np.inf, -1, 1, np.inf],
        labels=['Bas carbone', 'Intermédiaire', 'Haut carbone']
    ).astype(str)

    # ✅ Affichage tableau
    st.write("### ✅ Résultats après traitement des données :")
    st.dataframe(filtered_data)

# ✅ Bouton de mise à jour
if st.sidebar.button("🔄 Mettre à jour"):
    update_inies_data()

# ✅ Champ de recherche
search_term = st.text_input("🔎 Type d'élément à afficher (exemple : Plancher bois)")

if search_term:
    terms = search_term.split()
    filtered_data = df[
        np.logical_and.reduce([df['Nom du produit'].str.contains(term, case=False, na=False) for term in terms])
    ]
    if not filtered_data.empty:
        st.dataframe(filtered_data)
        if st.button("🔎 Traiter les données"):
            process_data(filtered_data)

