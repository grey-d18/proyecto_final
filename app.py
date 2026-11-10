"""ReciclaVoz: punto de entrada de la app.

Para correrla en tu laptop (desde la carpeta del proyecto, en la terminal de VS Code):
    source .venv/bin/activate
    streamlit run app.py

Este archivo solo arma el menú. Cada sección vive en su propio archivo dentro de
la carpeta paginas/, y la lógica (voz, IA, base de datos, PDF) está en nucleo/.
"""
import streamlit as st

st.set_page_config(page_title="ReciclaVoz", page_icon="♻️", layout="wide")

# st.navigation crea el menú lateral. Cada st.Page apunta a un archivo de paginas/.
menu = st.navigation(
    [
        st.Page("paginas/inicio.py", title="Inicio", icon="🏠", default=True),
        st.Page("paginas/registro.py", title="Registro por voz", icon="🎙️"),
        st.Page("paginas/capacitacion.py", title="Capacitación y precios", icon="📚"),
        st.Page("paginas/municipalidad.py", title="Panel municipal", icon="📊"),
    ]
)
menu.run()
