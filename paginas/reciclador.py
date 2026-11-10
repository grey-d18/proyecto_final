"""Entrada del reciclador.

1. Si todavía no sabemos quién es: «¿Eres <último inscrito>?»  Sí → su menú.  No → Registro.
2. Si ya sabemos quién es: tres botones grandes (Registro, Capacitación, Mi ruta)
   y arriba «Recoger reciclaje» con la burbuja de pedidos disponibles.

No hay usuario ni contraseña: st.session_state.reciclador guarda el código de la
persona mientras use la app en ese navegador.
"""
import streamlit as st

from nucleo.base_datos import buscar_reciclador, ultimo_registrado
from nucleo.interfaz import barra_reciclador, botones_grandes, volver

codigo = st.session_state.get("reciclador")
reciclador = buscar_reciclador(codigo) if codigo else None

if reciclador is None:
    volver("paginas/inicio.py")
    ultimo = ultimo_registrado()
    st.write("")
    if ultimo:
        st.markdown(f"<h2 style='text-align:center'>¿Eres {ultimo['nombre_completo']}?</h2>",
                    unsafe_allow_html=True)
        _, si, no, _ = st.columns([1, 2, 2, 1])
        if si.button("Sí", type="primary", width="stretch"):
            st.session_state.reciclador = ultimo["codigo"]
            st.rerun()
        if no.button("No", width="stretch"):
            st.switch_page("paginas/registro.py")
    else:
        st.switch_page("paginas/registro.py")
else:
    barra_reciclador(reciclador)
    nombre = (reciclador["nombre_completo"] or "").split(" ")[0]
    st.markdown(f"<h2 style='text-align:center'>Hola, {nombre}</h2>", unsafe_allow_html=True)
    botones_grandes([
        ("🎙️  Registro", "paginas/registro.py"),
        ("📚  Capacitación", "paginas/capacitacion.py"),
        ("🗺️  Mi ruta", "paginas/mi_ruta.py"),
    ])
    _, centro, _ = st.columns([2, 1, 2])
    if centro.button("No soy yo", type="tertiary", width="stretch"):
        del st.session_state["reciclador"]
        st.rerun()
