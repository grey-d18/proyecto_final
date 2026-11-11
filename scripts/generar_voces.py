"""Genera los audios de las preguntas y avisos con una voz neuronal de acento peruano.

Voz: es-PE-CamilaNeural (Microsoft Azure Neural TTS), usada a través de la librería
edge-tts, que llama al mismo servicio que el «Leer en voz alta» del navegador Edge.
Es gratis y no pide cuenta ni clave. Solo hace falta internet al GENERAR los audios:
la app solo reproduce los .mp3 ya guardados.

¿Por qué esta voz y no la mía clonada? Primero se clonó la voz de la fundadora con
Qwen3-TTS (ver el README, sección «Texto a voz»): sonaba humana, pero la entonación
cambiaba de una pregunta a otra y a veces aceleraba y se comía la última palabra.
Camila suena natural, mantiene la misma entonación en todas las frases y tiene acento
peruano, lo que la hace más cercana para las personas que reciclan en Trujillo.

No está en requirements.txt a propósito: la app no la necesita. Uso, desde la carpeta
del proyecto (uv instala edge-tts en un entorno temporal):
    uv run --no-project --with edge-tts python scripts/generar_voces.py                  # todos
    uv run --no-project --with edge-tts python scripts/generar_voces.py dni vivienda     # solo algunos
"""
import asyncio
import sys
from pathlib import Path

import edge_tts

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # para poder importar nucleo/ al correrlo como script
from nucleo.config import AUDIOS_PREGUNTAS  # noqa: E402
from nucleo.preguntas import AVISOS, PREGUNTAS, REPREGUNTAS  # noqa: E402

VOZ = "es-PE-CamilaNeural"
VELOCIDAD = "-10%"  # un poco más lento que lo normal: se entiende mejor

# Lo que se dice en cada audio. Se usa "voz" si la pregunta la tiene (texto hablado
# distinto del que se ve en pantalla, por ejemplo con una indicación extra).
TEXTOS = ({p["clave"]: p.get("voz", p["texto"]) for p in PREGUNTAS}
          | {r["clave"]: r.get("voz", r["texto"]) for r in REPREGUNTAS.values()} | AVISOS)


async def generar(clave: str) -> None:
    archivo = AUDIOS_PREGUNTAS / f"{clave}.mp3"
    await edge_tts.Communicate(TEXTOS[clave], VOZ, rate=VELOCIDAD).save(str(archivo))
    print(f"{archivo.name}: {TEXTOS[clave]}", flush=True)


if __name__ == "__main__":
    elegidas = sys.argv[1:] or list(TEXTOS)
    AUDIOS_PREGUNTAS.mkdir(parents=True, exist_ok=True)
    for clave in elegidas:
        asyncio.run(generar(clave))
