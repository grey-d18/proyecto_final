"""Configuración de la app: rutas de carpetas y lectura de claves.

¿Por qué existe este archivo?
    Para que todos los demás módulos lean la configuración de UN solo lugar.
    Si mañana cambias el modelo de Gemini o de Whisper, solo tocas el .env
    (en tu laptop) o las variables de entorno del servidor (en producción).

¿De dónde salen los valores?
    1. Primero se busca en las variables de entorno (el archivo .env en tu laptop,
       o las variables del servidor).
    2. Si no están, se usa el valor por defecto.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# --- Rutas ----------------------------------------------------------------
# RAIZ es la carpeta del proyecto (la que contiene api/, nucleo/ y web/).
RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
SINTETICOS = DATOS / "sinteticos"            # datos inventados para el demo (scripts/generar_sinteticos.py)
FUENTES = DATOS / "fuentes"                  # datos reales: SIGERSOL y precios del trabajo de campo
AUDIOS_PREGUNTAS = RAIZ / "web" / "audios"     # preguntas habladas (scripts/generar_voces.py); la app web las sirve tal cual
BASE_DATOS = DATOS / "registro.db"           # SQLite: se crea sola la primera vez

# Lee el archivo .env (si existe) y carga sus valores como variables de entorno.
load_dotenv(RAIZ / ".env")


def leer_ajuste(nombre: str, por_defecto: str | None = None) -> str | None:
    """Devuelve un ajuste buscándolo en el entorno y, si no está, el valor por defecto."""
    return os.environ.get(nombre) or por_defecto


# --- Ajustes que usa la app ----------------------------------------------------
GEMINI_MODELO = leer_ajuste("GEMINI_MODELO", "gemini-3.5-flash-lite")
WHISPER_MODELO = leer_ajuste("WHISPER_MODELO", "small")


def hay_clave_gemini() -> bool:
    """True si hay una clave de la API de Gemini configurada (sin mostrarla nunca)."""
    clave = leer_ajuste("GEMINI_API_KEY")
    return bool(clave) and clave != "pon-aqui-tu-clave"
