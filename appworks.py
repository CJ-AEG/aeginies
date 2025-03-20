import streamlit as st
import pandas as pd
import numpy as np
import requests
import io
import plotly.express as px
from PIL import Image

# ✅ Configuration de la page (MUST BE FIRST)
st.set_page_config(layout="wide")
st.title("AEG INIES Finder - Prototype SaaS")

# ✅ Charger le fichier CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ✅Charger le logo
logo = Image.open("logo_aeg.jpg")

# ✅Affichage dans la barre latérale
st.sidebar.image(logo, use_column_width=True)

# ✅ Déclaration globale du dataframe
df = pd.DataFrame()


# ✅ Charger automatiquement le fichier depuis GitHub
@st.cache_data
def load_data_from_repo():
    global df  # ✅ Déclaré comme global
    url = 'https://raw.githubusercontent.com/CJ-AEG/aeginies/main/base_inies_complete.xlsx'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            file = io.BytesIO(response.content)
            df = pd.read_excel(file, sheet_name="Sheet1", engine='openpyxl')
            return df
        else:
            st.error(f"❌ Erreur de chargement du fichier : {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"⚠️ Erreur lors du chargement : {e}")
        return pd.DataFrame()

# ✅ Charger le fichier automatiquement au lancement
df = load_data_from_repo()
if not df.empty:
    st.success("✅ Base de données chargée automatiquement depuis GitHub !")

# ✅ Affichage de la base de données initiale au chargement
if not df.empty:
    st.write("### 🔎 Données initiales chargées :")
    st.dataframe(df)

# ✅ Section sidebar pour importer un fichier Excel
with st.sidebar:
    st.write("📂 **Optionnel : Importer un fichier Excel**")
    uploaded_file = st.file_uploader("Importer un fichier Excel", type=["xlsx"])
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file, sheet_name="Sheet1", engine='openpyxl')
        st.success("✅ Fichier chargé avec succès !")
        st.write("### 🔎 Données importées :")
        st.dataframe(df)

# ✅ Fonction de traitement des données après recherche
def process_data(filtered_data):
    global df   # ✅ Déclaré comme global

    if filtered_data.empty:
        st.warning("⚠️ Aucun élément trouvé.")
        return

    # ✅ Conversion explicite en float (gestion d'erreur)
    filtered_data['Impact CO₂ (kg)'] = pd.to_numeric(filtered_data['Impact CO₂ (kg)'], errors='coerce').fillna(0)
    filtered_data['D-Bénéfices'] = pd.to_numeric(filtered_data['D-Bénéfices'], errors='coerce').fillna(0)
    filtered_data['Durée de Vie'] = pd.to_numeric(
        filtered_data['Durée de Vie'].str.replace('ans', '').str.strip(), 
        errors='coerce'
    ).fillna(50)

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
    ).astype(str)

    # ✅ Marquer la valeur maximale et minimale
    if not filtered_data.empty:
        max_idx = filtered_data['Z-Score'].idxmax()
        min_idx = filtered_data['Z-Score'].idxmin()

        filtered_data.loc[max_idx, 'Catégorie'] = f"{filtered_data.loc[max_idx, 'Catégorie']} (Valeur maximale)"
        filtered_data.loc[min_idx, 'Catégorie'] = f"{filtered_data.loc[min_idx, 'Catégorie']} (Valeur minimale)"

    # ✅ Affichage direct du tableau traité
    st.write(f"### 🔎 {len(filtered_data)} résultats trouvés :")
    st.dataframe(filtered_data)

    # ✅ Affichage du graphique Z-Score
    fig = px.histogram(
        filtered_data,
        x='Z-Score',
        nbins=20,
        color='Catégorie',
        color_discrete_map={
            'Bas carbone': '#2ca02c',
            'Intermédiaire': '#ff7f0e',
            'Haut carbone': '#d62728',
            'Bas carbone (Valeur minimale)': '#1f77b4',
            'Haut carbone (Valeur maximale)': '#9467bd'
        }
    )
    fig.update_xaxes(range=[-3, 3])
    st.plotly_chart(fig)

# ✅ Champ de recherche
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
            # ✅ Lancer le traitement automatiquement après la recherche
            process_data(filtered_data)
    else:
        st.warning("⚠️ Veuillez d'abord charger un fichier Excel valide avant de lancer une recherche.")
