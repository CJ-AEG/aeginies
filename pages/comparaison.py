import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from PIL import Image
import base64

# ✅ Configuration de la page
st.set_page_config(layout="wide")

# ✅ Charger le logo
logo = Image.open("logo_aeg.jpg")

# ✅ Convertir en base64 pour le rendre cliquable
with open("logo_aeg.jpg", "rb") as img_file:
    logo_base64 = base64.b64encode(img_file.read()).decode()

# ✅ Affichage du logo en tant que bouton cliquable
st.sidebar.markdown(
    f"""
    <a href="/" target="_self">
        <img src="data:image/png;base64,{logo_base64}" style="width: 100%; height: auto;">
    </a>
    """,
    unsafe_allow_html=True
)


# ✅ Charger automatiquement le fichier depuis GitHub
@st.cache_data
def load_data_from_repo():
    url = 'https://raw.githubusercontent.com/CJ-AEG/aeginies/main/base_inies_complete.xlsx'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            file = io.BytesIO(response.content)
            df = pd.read_excel(file, sheet_name="Sheet1", engine='openpyxl')
            return df
        else:
            st.error(f"⚠️ Erreur lors du chargement du fichier : {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"⚠️ Erreur lors du chargement : {e}")
        return pd.DataFrame()

# ✅ Charger les données
df = load_data_from_repo()

# ✅ Vérifier que la base de données est disponible
if df.empty:
    st.warning("⚠️ Base de données vide !")
    st.stop()

# ✅ Créer une colonne combinée pour recherche par nom ou ID
df['Produit (ID)'] = df['Nom du produit'] + " (ID: " + df['ID INIES'].astype(str) + ")"

# ✅ Titre de la page
st.title("🔎 Comparaison de produits")

# ✅ Colonnes côte à côte pour la sélection
col1, col2 = st.columns(2)

# ✅ Sélection du premier produit (clé unique)
with col1:
    product_1 = st.selectbox(
        "🛒 Sélectionner le premier produit :", 
        df['Produit (ID)'].unique(),
        key="product_1"
    )

# ✅ Sélection du second produit (clé unique)
with col2:
    product_2 = st.selectbox(
        "🛒 Sélectionner le second produit :", 
        df['Produit (ID)'].unique(),
        key="product_2"
    )

# ✅ Vérification que les produits sont différents
if product_1 == product_2:
    st.warning("⚠️ Les produits doivent être différents pour lancer la comparaison.")
    st.stop()

# ✅ Filtrer les deux produits sélectionnés par nom du produit
product_1_name = product_1.split(" (ID: ")[0]
product_2_name = product_2.split(" (ID: ")[0]

filtered_df = df[df['Nom du produit'].isin([product_1_name, product_2_name])].copy()

# ✅ Nettoyage des colonnes (forcer en float)
filtered_df['Impact CO₂ (kg)'] = pd.to_numeric(filtered_df['Impact CO₂ (kg)'], errors='coerce').fillna(0)
filtered_df['D-Bénéfices'] = pd.to_numeric(filtered_df['D-Bénéfices'], errors='coerce').fillna(0)
filtered_df['Durée de Vie'] = pd.to_numeric(
    filtered_df['Durée de Vie'].str.replace('ans', '', regex=True).str.strip(),
    errors='coerce'
).fillna(50)

# ✅ Ajouter l'impact total normalisé
filtered_df['Impact total normalisé'] = (
    (filtered_df['Impact CO₂ (kg)'] + filtered_df['D-Bénéfices']) * (50 / filtered_df['Durée de Vie'])
)

# ✅ Vérification des colonnes disponibles
available_columns = ['Type de Déclaration', 'Impact CO₂ (kg)', 'D-Bénéfices', 'Impact total normalisé']
if 'Z-Score' in filtered_df.columns:
    available_columns.append('Z-Score')
if 'Catégorie' in filtered_df.columns:
    available_columns.append('Catégorie')

# ✅ Affichage du tableau comparatif sous forme de colonnes
st.write("### 📊 Tableau comparatif")
st.dataframe(
    filtered_df.set_index('Nom du produit')[available_columns].transpose()
)

# ✅ Créer un DataFrame pour le graphique groupé
comparison_data = pd.DataFrame({
    'Nom du produit': [product_1_name, product_2_name],
    'Impact CO₂ (kg)': filtered_df['Impact CO₂ (kg)'].values,
    'D-Bénéfices': filtered_df['D-Bénéfices'].values,
    'Impact total normalisé': filtered_df['Impact total normalisé'].values
})

# ✅ Transformer les données pour un graphique groupé
comparison_data_melted = comparison_data.melt(
    id_vars='Nom du produit', 
    value_vars=['Impact CO₂ (kg)', 'D-Bénéfices', 'Impact total normalisé'],
    var_name='Variable',
    value_name='Valeur'
)

# ✅ Créer le graphique à barres groupé
fig = px.bar(
    comparison_data_melted,
    x='Variable',                   # Les variables en abscisse
    y='Valeur',
    color='Nom du produit',         # Les produits en couleur
    barmode='group',                # Mode groupé
    title="🔎 Comparaison des produits"
)

# ✅ Personnalisation du style du graphique
fig.update_layout(
    xaxis_title="Type d'impact",
    yaxis_title="Valeur",
    legend_title="Produit",
    bargap=0.2
)

# ✅ Afficher le graphique
st.plotly_chart(fig)


# ✅ Bouton de retour à l'accueil
if st.button("🏠 Retour à l'accueil"):
    st.switch_page("appworks.py")

