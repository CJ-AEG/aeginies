import streamlit as st
import pandas as pd
import numpy as np
import requests
import io
import plotly.express as px
from PIL import Image
import base64
from streamlit_modal import Modal
from utils import apply_styles


# ✅ Configuration de la page (MUST BE FIRST)
st.set_page_config(layout="wide")
# st.title("AEG INIES Finder - Prototype SaaS")

# ✅ Vérification de connexion
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Vous devez être connecté pour accéder à cette page.")
    st.switch_page("pages/redirect_login.py")

# ✅ Créer une ligne avec deux colonnes pour le titre et le bouton
col1, col2 = st.columns([8, 2])

# ✅ Titre à gauche
with col1:
    st.title("🎯 AEG INIES Finder - Prototype SaaS")

# ✅ Bouton de déconnexion à droite
with col2:
    if st.button("🚪 Se déconnecter"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.switch_page("pages/redirect_login.py")

# ✅ Charger le fichier CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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

# ✅ Créer une fenêtre modale pour l'importation
modal = Modal("📥 Importer un fichier Excel", key="import_excel")

# ✅ Bouton pour ouvrir la popup
if st.sidebar.button("📥 Importer un fichier Excel"):
    modal.open()

# ✅ Contenu de la popup
if modal.is_open():
    with modal.container():
        st.write("**📂 Glissez le fichier ici**")
        uploaded_file = st.file_uploader("", type=["xlsx"])
        
        if uploaded_file is not None:
            df = pd.read_excel(uploaded_file, sheet_name="Sheet1", engine='openpyxl')
            st.success("✅ Fichier chargé avec succès !")
            modal.close()
            st.rerun()  # 🔥 Mettre à jour l'application après fermeture de la popup

		
        
        # ✅ Bouton pour fermer la popup
        if st.button("❌ Fermer"):
            modal.close()

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

# ✅ Vérifier que df n'est pas vide avant de filtrer
if not df.empty:

    # ✅ Barre de recherche + Filtrage par type de déclaration (NOUVEAU CODE)
    col1, col2 = st.columns([3, 2])

    # ✅ Champ de recherche
    with col1:
        st.markdown(
            "<h4 style='font-size:24px; font-weight:bold; color:#0047AB;'>🔎 Type d'élément à afficher :</h4>", 
            unsafe_allow_html=True
        )
        search_term = st.text_input("Exemple : Plancher bois")

    # ✅ Filtrage par type de déclaration
    with col2:
        st.markdown(
            "<h4 style='font-size:24px; font-weight:bold; color:#0047AB;'>📌 Filtrer par type de déclaration :</h4>", 
            unsafe_allow_html=True
        )
        type_declaration_options = ['Individuelle', 'Collective', 'DED', 'RE2020', 'EC']
        selected_types = st.multiselect(
            "",
            options=type_declaration_options,
            default=type_declaration_options
        )

    # ✅ Appliquer le filtrage directement après sélection
    filtered_df = df[df['Type de Déclaration'].isin(selected_types)]

    # ✅ Si recherche en plus du filtrage par type de déclaration
    if search_term:
        terms = search_term.split()

        # ✅ Filtrage amélioré basé sur "Nom du produit" ET "Unité Fonctionnelle"
        filtered_df = filtered_df[
            np.logical_and.reduce([
                filtered_df['Nom du produit'].str.contains(term, case=False, na=False) |
                filtered_df['Unité Fonctionnelle'].str.contains(term, case=False, na=False)
                for term in terms
            ])
        ]

    # ✅ Lancer le traitement si résultats disponibles
    if not filtered_df.empty:
        process_data(filtered_df)  # ✅ Laisse cette fonction gérer l'affichage du tableau + nombre de résultats

    else:
        st.warning("⚠️ Aucun résultat trouvé.")

else:
    st.warning("⚠️ Base de données vide ! Importez un fichier pour continuer.")


# ✅ Bouton pour afficher base de données complètes
if st.sidebar.button("📊 Afficher la base de données complète"):
    st.switch_page("pages/baseiniespage.py")

# ✅ Bouton pour accéder à la page de comparaison
if st.sidebar.button("🔎 Comparer des produits"):
    st.switch_page("pages/comparaison.py")


# ✅ Vérification de connexion
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Vous devez être connecté pour accéder à cette page.")
    st.stop()



