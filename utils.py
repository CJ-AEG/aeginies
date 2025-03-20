import streamlit as st

def apply_styles():
    st.markdown(
        """
        <style>
            body, button, input, select, textarea {
                font-family: 'Arial', sans-serif !important;
            }
            div[data-testid="stDataFrame"] * {
                font-family: 'Arial', sans-serif !important;
                font-size: 14px !important;
            }
            h1, h2, h3 {
                color: #002D62 !important;
            }
            button {
                background-color: #0047AB !important;
                color: #FFFFFF !important;
                border-radius: 12px !important;
                padding: 12px 24px !important;
                font-size: 16px !important;
                font-weight: bold !important;
            }
            button:hover {
                background-color: #003580 !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
