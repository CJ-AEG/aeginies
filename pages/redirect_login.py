import streamlit as st
import time

st.info("🔄 Redirection vers la page de connexion...")

# ✅ Pause rapide pour l'effet visuel
time.sleep(1)

# ✅ Redirection manuelle avec du JS vers la racine du projet
st.markdown('<meta http-equiv="refresh" content="0;URL=/">', unsafe_allow_html=True)
