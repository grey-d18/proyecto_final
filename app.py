"""ReciclaVoz: punto de entrada de la app.

Para correrla en tu laptop (desde la carpeta del proyecto, en la terminal de VS Code):
    source .venv/bin/activate
    streamlit run app.py

Este archivo solo registra las páginas. No hay menú lateral (position="hidden"):
la persona avanza apretando botones grandes, y cada botón la lleva a otra página
con st.switch_page(). Cada página vive en paginas/, y la lógica (voz, IA, base de
datos, PDF, mapas) está en nucleo/.

    Inicio ─┬─ Soy reciclador ─┬─ Registro
            │                  ├─ Capacitación
            │                  ├─ Mi ruta
            │                  └─ Recoger reciclaje (pedidos de los vecinos)
            ├─ Soy vecino ────── Pedir un recojo
            ├─ Soy acopiador ─── Mis precios y mi local
            └─ (más) Soy municipalidad ── Panel municipal
"""
import streamlit as st

from nucleo.interfaz import poner_estilo

st.set_page_config(page_title="ReciclaVoz", page_icon="♻️", layout="centered")
poner_estilo()

paginas = st.navigation(
    [
        st.Page("paginas/inicio.py", title="Inicio", icon="🏠", default=True),
        st.Page("paginas/reciclador.py", title="Reciclador", icon="🛒"),
        st.Page("paginas/registro.py", title="Registro", icon="🎙️"),
        st.Page("paginas/capacitacion.py", title="Capacitación", icon="📚"),
        st.Page("paginas/mi_ruta.py", title="Mi ruta", icon="🗺️"),
        st.Page("paginas/recoger.py", title="Recoger reciclaje", icon="🚚"),
        st.Page("paginas/vecino.py", title="Vecino", icon="🏠"),
        st.Page("paginas/acopiador.py", title="Acopiador", icon="🏪"),
        st.Page("paginas/municipalidad.py", title="Municipalidad", icon="📊"),
    ],
    position="hidden",  # sin menú lateral: se navega con botones
)
paginas.run()
