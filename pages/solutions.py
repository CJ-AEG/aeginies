import streamlit as st
import json
import os
from pathlib import Path
import pandas as pd
import numpy as np
from PIL import Image
import base64

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

# Chargement de la base INIES
if "df_inies" not in st.session_state:
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    file_path = os.path.join(base_path, "base_inies_complete.xlsx")
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        st.session_state["df_inies"] = df
    else:
        st.warning("⚠️ Fichier INIES introuvable à l'emplacement attendu : base_inies_complete.xlsx")

SOLUTIONS_FILE = Path("solutions_db.json")

def load_solutions():
    if SOLUTIONS_FILE.exists():
        with open(SOLUTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_solutions(data):
    def convert(obj):
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        elif isinstance(obj, (np.floating, float)):
            return float(obj)
        elif isinstance(obj, (np.ndarray, list)):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        return obj
    with open(SOLUTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(convert(data), f, indent=4, ensure_ascii=False)

def delete_solution(name, data):
    if name in data:
        del data[name]
        save_solutions(data)

def extract_product_id(option):
    if option and "(ID: " in option:
        return option.split("(ID: ")[-1].replace(")", "")
    return None


def search_products(df, query):
    if not query:
        return df
    words = query.lower().split()
    mask = pd.Series(True, index=df.index)
    for word in words:
        mask &= df["Nom du produit"].str.lower().str.contains(word, na=False, regex=False) | \
                df["ID INIES"].astype(str).str.contains(word, na=False, regex=False)
    return df[mask]

st.set_page_config(page_title="Solutions prédéfinies", layout="wide")
st.title("🧱 Gestion des solutions prédéfinies")

solutions = load_solutions()
view_tab, create_tab = st.tabs(["📂 Visualiser les solutions", "➕ Créer une solution"])

with view_tab:
    st.subheader("Solutions existantes")
    if not solutions:
        st.info("Aucune solution enregistrée pour le moment.")
    else:
        all_categories = sorted(set(content.get("categorie", "Non spécifiée") for content in solutions.values()))
        selected_cat = st.selectbox("Filtrer par catégorie", ["Toutes"] + all_categories)

        if "edit_solution" not in st.session_state:
            st.session_state.edit_solution = None
        if "edit_temp_produits" not in st.session_state:
            st.session_state.edit_temp_produits = {}
        if "saisie_libre_flags" not in st.session_state:
            st.session_state.saisie_libre_flags = {}

        for name, content in solutions.items():
            if selected_cat != "Toutes" and content.get("categorie") != selected_cat:
                continue

            st.markdown(f"### 🔹 {name}")
            st.markdown(f"**Catégorie :** {content.get('categorie', 'Non spécifiée')}")
            solution_qte = st.number_input(f"Quantité de la solution ({name})", min_value=0.0, value=1.0, step=0.1, key=f"solution_qte_{name}")
            produits = content.get("produits", [])

            if st.session_state.edit_solution == name:
                if name not in st.session_state.edit_temp_produits:
                    st.session_state.edit_temp_produits[name] = produits
                if name not in st.session_state.saisie_libre_flags:
                    st.session_state.saisie_libre_flags[name] = [False] * len(produits)

                new_produits = st.session_state.edit_temp_produits[name]
                libre_flags = st.session_state.saisie_libre_flags[name]
                df_inies = st.session_state.get("df_inies", pd.DataFrame())

                for i, p in enumerate(new_produits):
                    st.write(f"**Produit {i+1} :**")
                    libre_key = f"libre_{name}_{i}"
                    libre_flags[i] = st.checkbox("🔓 Mode saisie libre", value=libre_flags[i], key=libre_key)

                    if libre_flags[i]:
                        selected_nom = st.text_input(
                            f"Nom ou ID INIES du produit {i+1}",
                            value=p.get("nom", ""),
                            key=f"text_{name}_{i}"
                        )
                        selected_row = None
                        id_inies = ""
                    else:
                        options = [
                            f"{row['Nom du produit']} (ID: {row['ID INIES']})"
                            for _, row in df_inies.iterrows()
                        ]
                        default_val = p.get("nom", "")
                        selected_nom = st.selectbox(
                            f"Nom ou ID INIES du produit {i+1}",
                            options,
                            index=options.index(default_val) if default_val in options else 0,
                            key=f"dropdown_{name}_{i}"
                        )

                        id_inies = extract_product_id(selected_nom)
                        selected_row = (
                            df_inies[df_inies["ID INIES"].astype(str) == id_inies].iloc[0]
                            if id_inies and not df_inies.empty and id_inies in df_inies["ID INIES"].astype(str).values
                            else None
                        )

                    quantité = st.number_input(f"Quantité {i+1}", value=float(p.get("quantité", 0)), key=f"quantite_{name}_{i}")

                    if selected_row is not None:
                        impact_co2 = float(selected_row["Impact CO₂ (kg)"])
                        d_benefices = float(selected_row.get("D-Bénéfices", 0) or 0)
                        duree_vie = selected_row.get("Durée de Vie", 50)
                        try:
                            duree_vie = int(str(duree_vie).split()[0])
                        except:
                            duree_vie = 50
                        impact_normalisé = round((impact_co2 + d_benefices) * (50 / duree_vie) * float(quantité), 2)
                    else:
                        impact_normalisé = float(p.get("impact_normalisé", 0))
                        duree_vie = p.get("durée_vie", 50)
                        d_benefices = p.get("d_bénéfices", 0)

                    st.write(f"Impact CO₂ normalisé {i+1} : {impact_normalisé} kg")

                    new_produits[i] = {
                        "id_inies": str(id_inies),
                        "nom": str(selected_nom),
                        "quantité": float(quantité),
                        "impact_normalisé": float(impact_normalisé),
                        "durée_vie": int(duree_vie),
                        "d_bénéfices": float(d_benefices)
                    }

                    if st.button(f"❌ Supprimer produit {i+1}", key=f"remove_prod_{name}_{i}"):
                        new_produits.pop(i)
                        libre_flags.pop(i)
                        st.rerun()

                if st.button(f"➕ Ajouter un produit vide", key=f"add_prod_{name}"):
                    new_produits.append({
                        "id_inies": "",
                        "nom": "",
                        "quantité": 0.0,
                        "impact_normalisé": 0.0,
                        "durée_vie": 50,
                        "d_bénéfices": 0
                    })
                    libre_flags.append(False)
                    st.rerun()

                if st.button("📅 Sauvegarder", key=f"save_{name}"):
                    solutions[name]["produits"] = new_produits
                    save_solutions(solutions)
                    st.success("Modifications enregistrées.")
                    st.session_state.edit_solution = None
                    st.rerun()
                if st.button("❌ Annuler", key=f"cancel_{name}"):
                    st.session_state.edit_solution = None
                    st.rerun()
            else:
                df = pd.DataFrame(produits)
                df_affiche = df[["nom", "quantité", "impact_normalisé"]].rename(columns={
                    "nom": "Nom du produit",
                    "quantité": "Quantité",
                    "impact_normalisé": "Impact CO₂ normalisé (kg)"
                })
                st.dataframe(df_affiche, use_container_width=True)
                impact_total = df["impact_normalisé"].sum()
                st.markdown(f"**Impact total CO₂ normalisé :** {impact_total:.2f} kg")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"🖍️ Modifier", key=f"edit_{name}"):
                        st.session_state.edit_solution = name
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Supprimer", key=f"delete_{name}"):
                        delete_solution(name, solutions)
                        st.rerun()

with create_tab:
    st.subheader("Création d'une nouvelle solution")

    if "new_solution_produits" not in st.session_state:
        st.session_state.new_solution_produits = []

    solution_name = st.text_input("Nom de la solution", "")

    categories_possibles = [
        "Toitures", "Murs ossature bois", "Planchers", "Murs béton", "Menuiseries", "Autres"
    ]
    categorie = st.selectbox("Catégorie de la solution", categories_possibles)

    st.markdown("### Ajouter un produit à la solution")
    df_inies = st.session_state.get("df_inies", pd.DataFrame())

    if "saisie_libre_creation" not in st.session_state:
        st.session_state.saisie_libre_creation = False

    st.session_state.saisie_libre_creation = st.checkbox("🔓 Mode saisie libre", value=st.session_state.saisie_libre_creation)

    produit_nom = ""
    selected_row = None

    if st.session_state.saisie_libre_creation:
        produit_nom = st.text_input("Nom ou ID INIES du produit 1", "")
    else:
        options = [
            f"{row['Nom du produit']} (ID: {row['ID INIES']})"
            for _, row in df_inies.iterrows()
        ]
        produit_nom = st.selectbox("Nom ou ID INIES du produit 1", options)

        def extract_product_id(option):
            if "(ID: " in option:
                return option.split("(ID: ")[-1].replace(")", "")
            return None

        id_inies = extract_product_id(produit_nom)
        if id_inies and id_inies in df_inies["ID INIES"].astype(str).values:
            selected_row = df_inies[df_inies["ID INIES"].astype(str) == id_inies].iloc[0]
        else:
            selected_row = None

    quantité = st.number_input("Quantité", min_value=0.0, format="%.2f")

    if selected_row is not None:
        id_inies = selected_row["ID INIES"]
        impact_co2 = selected_row["Impact CO₂ (kg)"]
        d_benefices = selected_row.get("D-Bénéfices", 0) or 0
        duree_vie = selected_row.get("Durée de Vie", 50)
        try:
            duree_vie = int(str(duree_vie).split()[0])
        except:
            duree_vie = 50
        impact_normalisé = round((float(impact_co2) + float(d_benefices)) * (50 / duree_vie) * float(quantité), 2)
    else:
        id_inies = ""
        impact_normalisé = 0.0
        duree_vie = 50
        d_benefices = 0.0

    st.write(f"**Impact CO₂ normalisé : {impact_normalisé:.1f} kg**")

    if st.button("➕ Ajouter ce produit à la solution"):
        st.session_state.new_solution_produits.append({
            "id_inies": str(id_inies),
            "nom": str(produit_nom),
            "quantité": float(quantité),
            "impact_normalisé": float(impact_normalisé),
            "durée_vie": int(duree_vie),
            "d_bénéfices": float(d_benefices)
        })
        st.success("Produit ajouté.")

    if st.session_state.new_solution_produits:
        st.markdown("### Produits dans la solution")
        df_temp = pd.DataFrame(st.session_state.new_solution_produits)
        df_affiche = df_temp[["nom", "quantité", "impact_normalisé"]].rename(columns={
            "nom": "Nom du produit",
            "quantité": "Quantité",
            "impact_normalisé": "Impact CO₂ normalisé (kg)"
        })
        st.dataframe(df_affiche, use_container_width=True)

        total = df_temp["impact_normalisé"].sum()
        st.markdown(f"**Impact total estimé : {total:.2f} kg**")

        for i in range(len(st.session_state.new_solution_produits)):
            if st.button(f"❌ Supprimer le produit {i+1}", key=f"remove_{i}"):
                st.session_state.new_solution_produits.pop(i)
                st.rerun()

    if st.session_state.new_solution_produits and solution_name.strip():
        if st.button("💾 Enregistrer la solution"):
            if solution_name in solutions:
                st.warning("Une solution avec ce nom existe déjà.")
            else:
                solutions[solution_name] = {
                    "nom": solution_name,
                    "categorie": categorie,
                    "produits": st.session_state.new_solution_produits,
                }
                save_solutions(solutions)
                st.success("✅ Solution enregistrée avec succès.")
                st.session_state.new_solution_produits = []
                st.rerun()
