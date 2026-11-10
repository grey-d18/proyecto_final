"""Piezas de pantalla que se repiten en varias páginas.

La app está pensada para personas que quizá no saben leer o usan poco el celular:
botones grandes con ícono, una sola acción por pantalla y mensajes que se escuchan.
"""
import base64

import streamlit as st

from nucleo.base_datos import buscar_reciclador, recojos_disponibles
from nucleo.config import AUDIOS_PREGUNTAS


# CSS = las reglas de estilo de la página. Aquí solo agrandamos los botones.
ESTILO = """
<style>
div.stButton > button, div.stDownloadButton > button, div.stFormSubmitButton > button {
    min-height: 3.4rem; border-radius: 14px;
}
div.stButton > button p, div.stDownloadButton > button p, div.stFormSubmitButton > button p {
    font-size: 1.1rem !important;
}
/* Los contenedores con key="grandes…" reciben la clase st-key-grandes…: botones más altos. */
[class*="st-key-grandes"] div.stButton > button { min-height: 5.5rem !important; }
[class*="st-key-grandes"] div.stButton > button p { font-size: 1.5rem !important; font-weight: 600; }
/* El botón «más» (tertiary) se queda pequeño y subrayado, como un enlace. */
button[kind="tertiary"] { min-height: 1.5rem !important; }
button[kind="tertiary"] p { font-size: 0.9rem !important; text-decoration: underline; }
</style>
"""


def poner_estilo() -> None:
    st.html(ESTILO)


@st.cache_data
def audio_en_base64(clave: str) -> str | None:
    """Lee el .mp3 y lo convierte en texto base64 (una sola vez: queda en caché)."""
    archivo = AUDIOS_PREGUNTAS / f"{clave}.mp3"
    return base64.b64encode(archivo.read_bytes()).decode() if archivo.exists() else None


def hablar(clave: str) -> None:
    """Reproduce en voz alta el audio datos/audios_preguntas/<clave>.mp3 al aparecer en pantalla.

    El audio va DENTRO de la página (base64) en una etiqueta <audio autoplay>, en vez de
    st.audio: así suena solo apenas aparece y no depende del servidor de archivos de
    Streamlit (que en la versión 1.60 fallaba al enviar audios por partes).
    El reproductor queda visible para volver a escucharlo.
    """
    datos = audio_en_base64(clave)
    if datos:
        st.html(f'<audio controls autoplay style="width:100%" src="data:audio/mpeg;base64,{datos}"></audio>')


def botones_grandes(opciones: list[tuple[str, str]]) -> None:
    """Botones grandes, uno debajo del otro, centrados. Cada opción es (texto, página destino)."""
    _, centro, _ = st.columns([1, 3, 1])
    with centro, st.container(key=f"grandes_{opciones[0][1].split('/')[-1][:-3]}"):
        for texto, destino in opciones:
            if st.button(texto, width="stretch", type="primary", key=f"ir_{destino}"):
                st.switch_page(destino)


def volver(destino: str = "paginas/reciclador.py", texto: str = "◀ Volver") -> None:
    if st.button(texto, key=f"volver_{destino}"):
        st.switch_page(destino)


def reciclador_actual() -> dict:
    """El reciclador que está usando la app. Si nadie dijo «soy yo», vuelve a preguntar."""
    codigo = st.session_state.get("reciclador")
    reciclador = buscar_reciclador(codigo) if codigo else None
    if reciclador is None:
        st.switch_page("paginas/reciclador.py")
    return reciclador


def barra_reciclador(reciclador: dict) -> None:
    """Arriba: «Volver» a la izquierda y «Recoger reciclaje» con su burbuja de aviso a la derecha."""
    izquierda, derecha = st.columns([1, 1])
    with izquierda:
        volver()
    with derecha:
        pendientes = len(recojos_disponibles(reciclador["distrito_vivienda"], reciclador["codigo"]))
        burbuja = f"  🔴 {pendientes}" if pendientes else ""
        if st.button(f"🚚 Recoger reciclaje{burbuja}", width="stretch"):
            st.switch_page("paginas/recoger.py")
