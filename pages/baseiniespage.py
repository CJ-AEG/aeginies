import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import pandas as pd
import os
from PIL import Image
import base64
from utils import apply_styles


# ✅ Configuration de la page
st.set_page_config(layout="wide")

apply_styles()

# ✅ Vérification de connexion
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Vous devez être connecté pour accéder à cette page.")
    st.switch_page("login.py")

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

# ✅ Titre de la page
st.title("📊 Base de données complète")

# ✅ Charger le fichier Excel depuis le dossier principal
file_path = os.path.join(os.path.dirname(__file__), "../base_inies_complete.xlsx")

@st.cache_data
def load_data():
    try:
        df = pd.read_excel(file_path, sheet_name="Sheet1", engine='openpyxl')
        return df
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement du fichier : {e}")
        return pd.DataFrame()

# ✅ Charger les données
df = load_data()

# ✅ Affichage des données
if not df.empty:
    st.write(f"### 📌 {len(df)} produits dans la base de données complète :")
    st.dataframe(df)

else:
    st.warning("⚠️ Base de données vide ou problème de chargement.")

# ✅ Bouton pour revenir à la page principale
if st.button("🏠 Retour à l'accueil"):
    st.switch_page("appworks.py")
