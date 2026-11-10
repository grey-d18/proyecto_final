"""De la voz al texto con Whisper (herramienta del curso: sesión 13).

Usamos faster-whisper, una versión de Whisper (OpenAI) que corre en el CPU de
la laptop o del servidor, sin pagar una API y sin que el audio salga del sistema.
Eso importa: el audio contiene la voz y el DNI de una persona.

Flujo:
    audio grabado (bytes) -> archivo temporal -> Whisper -> texto en español
"""
import tempfile

import streamlit as st
from faster_whisper import WhisperModel

from nucleo.config import WHISPER_MODELO

# Palabras que Whisper debe esperar. Se le pasan como "contexto inicial" para que
# escriba bien los nombres de materiales y lugares de Trujillo.
VOCABULARIO = (
    "Reciclaje en Trujillo, El Porvenir, Florencia de Mora, La Esperanza, Alto Trujillo, "
    "Víctor Larco, Huanchaco. Materiales: cartón, papel, botellas PET, plástico duro, "
    "fierro, chatarra, cobre, aluminio, vidrio. DNI, acopiador, asociación, guantes, mascarilla."
)

# Apellidos frecuentes en el Perú. Whisper aprendió sobre todo con textos en inglés y en
# español de otros países, así que confunde apellidos andinos: oía «Quispe Ramos» como
# «y esperamos». Los "hotwords" son palabras a las que Whisper les da prioridad.
# Un apellido que no esté en la lista igual puede salir mal: por eso el registrador revisa.
APELLIDOS = (
    "Quispe Ramos Huamán Mamani Flores Rodríguez Sánchez García Rojas Chávez Vásquez "
    "Díaz Cruz Castillo Mendoza Paredes Gutiérrez Torres Ruiz Condori Ccori Huanca "
    "Cárdenas Villanueva Alvarado Rengifo Zavaleta Cotrina Polo Lescano Castañeda Estrada"
)


@st.cache_resource(show_spinner="Cargando el modelo de voz (solo la primera vez)…")
def cargar_modelo() -> WhisperModel:
    """Carga Whisper UNA sola vez y lo guarda en memoria.

    @st.cache_resource hace que Streamlit no vuelva a cargar el modelo cada vez
    que alguien aprieta un botón (cargarlo tarda unos segundos).
    compute_type="int8" reduce la memoria que usa: así entra en el plan gratuito
    de Streamlit Community Cloud.
    """
    return WhisperModel(WHISPER_MODELO, device="cpu", compute_type="int8")


def transcribir(audio_bytes: bytes) -> str:
    """Recibe el audio grabado en el navegador y devuelve el texto que se dijo."""
    # Whisper lee archivos, así que guardamos los bytes en un archivo temporal.
    with tempfile.NamedTemporaryFile(suffix=".wav") as archivo:
        archivo.write(audio_bytes)
        archivo.flush()
        segmentos, _info = cargar_modelo().transcribe(
            archivo.name,
            language="es",            # forzamos español: evita que adivine otro idioma
            initial_prompt=VOCABULARIO,
            hotwords=APELLIDOS,       # prioriza apellidos peruanos (Quispe, Huamán…)
            vad_filter=True,          # ignora los silencios
            beam_size=5,
        )
        # Whisper devuelve el texto en pedazos (segmentos); los unimos.
        texto = " ".join(segmento.text.strip() for segmento in segmentos)
    return texto.strip()
