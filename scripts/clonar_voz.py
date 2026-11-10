"""Genera los audios de las PREGUNTAS (y avisos) con la voz de la fundadora, clonada con Qwen3-TTS.

¿Para qué?
    Muchos recicladores no saben leer. Por eso cada pregunta del registro se escucha
    sola al aparecer en pantalla, y el aviso de los 3 días del recojo también se dice
    en voz alta. Una voz humana y cercana genera más confianza que una voz robótica.

¿Qué es Qwen3-TTS?
    Un modelo abierto y gratuito de Alibaba que convierte texto en voz. Con unos
    segundos de una grabación de referencia (y su transcripción) imita esa voz.
    Corre en la laptop: no se paga ninguna API.

No está en requirements.txt a propósito: la app no lo necesita (solo reproduce los .wav
ya generados) y PyTorch es demasiado pesado para el plan gratuito de Streamlit.
Se instala en un entorno aparte:
    uv venv qwen --python 3.12 && VIRTUAL_ENV=qwen uv pip install qwen-tts soundfile

Archivos de referencia (NO se suben a GitHub: la carpeta audios/ está en .gitignore):
    audios/referencia.wav   unos 10 a 25 s de tu voz, hablando natural
    audios/referencia.txt   lo que dices en esa grabación, palabra por palabra

Uso, desde la carpeta del proyecto (en CPU tarda ~30 s por audio; en "mps" fue mucho más lento):
    qwen/bin/python scripts/clonar_voz.py                  # todos los audios
    qwen/bin/python scripts/clonar_voz.py dni aviso_recojo # solo algunos
El modelo genera algo distinto cada vez: si un audio sale cortado, se vuelve a generar solo ese.
"""
import subprocess
import sys
from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from nucleo.preguntas import AVISOS, PREGUNTAS  # noqa: E402

REFERENCIA = RAIZ / "audios" / "referencia.wav"
DESTINO = RAIZ / "datos" / "audios_preguntas"
MODELO = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"  # la versión pequeña (0.6 mil millones de parámetros)

# Lo que se dice en cada audio. Se usa "voz" si la pregunta la tiene: ahí el texto está
# escrito como SE PRONUNCIA (el modelo leía «DNI» en inglés y «Quispe» como «Cuispe»).
TEXTOS = {p["clave"]: p.get("voz", p["texto"]) for p in PREGUNTAS} | AVISOS

if __name__ == "__main__":
    elegidas = sys.argv[1:] or list(TEXTOS)
    texto_referencia = REFERENCIA.with_suffix(".txt").read_text(encoding="utf-8").strip()
    DESTINO.mkdir(parents=True, exist_ok=True)

    modelo = Qwen3TTSModel.from_pretrained(MODELO, device_map="cpu", dtype=torch.float32)
    # La "huella" de la voz se calcula una sola vez y se reutiliza para cada frase.
    voz = modelo.create_voice_clone_prompt(ref_audio=str(REFERENCIA), ref_text=texto_referencia)

    for clave in elegidas:
        audios, frecuencia = modelo.generate_voice_clone(
            text=TEXTOS[clave], language="Spanish", voice_clone_prompt=voz
        )
        archivo = DESTINO / f"{clave}.wav"
        sf.write(archivo, audios[0], frecuencia)
        # WAV mono de 16 bits a 16 kHz: pesa poco y el navegador lo reproduce sin problema.
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
                        str(archivo), str(archivo)], check=True)
        print(f"{archivo.name}: {TEXTOS[clave]}", flush=True)
