"""Inicio: «¿Quién eres?». Tres botones grandes y, escondido en «más», la municipalidad.

La explicación del proyecto (problema, modelo de negocio…) está en el README:
la app es el producto, no una presentación del producto.
"""
import streamlit as st

from nucleo.interfaz import botones_grandes

st.markdown("<h1 style='text-align:center'>♻️ ReciclaVoz</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center'>¿Quién eres?</h3>", unsafe_allow_html=True)

botones_grandes([
    ("🛒  Soy reciclador", "paginas/reciclador.py"),
    ("🏠  Soy vecino", "paginas/vecino.py"),
    ("🏪  Soy acopiador", "paginas/acopiador.py"),
])

# «más»: un botón pequeño tipo enlace (type="tertiary") que muestra la opción de la municipalidad.
_, centro, _ = st.columns([2, 1, 2])
with centro:
    if st.button("más", type="tertiary", width="stretch"):
        st.session_state.ver_mas = not st.session_state.get("ver_mas", False)
if st.session_state.get("ver_mas"):
    _, centro, _ = st.columns([1, 2, 1])
    if centro.button("📊 Soy municipalidad", width="stretch"):
        st.switch_page("paginas/municipalidad.py")
