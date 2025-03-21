import streamlit as st

# ✅ Créer des identifiants utilisateurs simples
USER_CREDENTIALS = {
    "admin": "password123",
    "user": "test123"
}

# ✅ Vérifier si l'utilisateur est connecté
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ✅ Interface de connexion si non connecté
if not st.session_state.logged_in:
    st.title("🔐 Connexion à l'application")

    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username  # ✅ Stocker le nom d'utilisateur
            st.success(f"✅ Connexion réussie ! Bienvenue, **{username}** 👋")

            # ✅ Rediriger automatiquement vers la page principale dans le dossier `pages/`
            st.switch_page("pages/appworks.py")
        else:
            st.error("❌ Identifiant ou mot de passe incorrect")

else:
    st.success(f"✅ Bienvenue, **{st.session_state.username}** !")
    st.switch_page("pages/appworks.py")
