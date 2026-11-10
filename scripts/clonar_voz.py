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
    uv venv qwen --python 3.12 && VIRTUAL_ENV=qwen uv pip install qwen-tts soundfile faster-whisper

Archivos de referencia (NO se suben a GitHub: la carpeta audios/ está en .gitignore):
    audios/referencia.wav   unos 10 a 25 s de tu voz, hablando natural
    audios/referencia.txt   lo que dices en esa grabación, palabra por palabra

Uso, desde la carpeta del proyecto (en CPU tarda ~30 s por audio; en "mps" fue mucho más lento):
    qwen/bin/python scripts/clonar_voz.py                  # todos los audios
    qwen/bin/python scripts/clonar_voz.py dni aviso_recojo # solo algunos
Control de calidad: a veces el modelo acelera al final y se "come" la última palabra
(pasaba con «¿A cuál?»). Por eso cada audio se escucha con Whisper: si no se entiende la
frase completa, se genera otra vez (hasta INTENTOS veces) y se guarda la mejor toma.
Además se agrega medio segundo de silencio al final para que el audio no corte en seco.
"""
import difflib
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from faster_whisper import WhisperModel
from qwen_tts import Qwen3TTSModel

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from nucleo.preguntas import AVISOS, PREGUNTAS  # noqa: E402

REFERENCIA = RAIZ / "audios" / "referencia.wav"
DESTINO = RAIZ / "datos" / "audios_preguntas"  # = nucleo.config.AUDIOS_PREGUNTAS
MODELO = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"  # la versión pequeña (0.6 mil millones de parámetros)
INTENTOS = 4            # tomas como máximo por audio
PARECIDO_MINIMO = 0.9   # 1.0 = Whisper entendió exactamente la frase
SILENCIO_FINAL = 0.5    # segundos de silencio al final

# Lo que se dice en cada audio. Se usa "voz" si la pregunta la tiene: ahí el texto está
# escrito como SE PRONUNCIA (el modelo leía «DNI» en inglés y «Quispe» como «Cuispe»).
TEXTOS = {p["clave"]: p.get("voz", p["texto"]) for p in PREGUNTAS} | AVISOS
# Para comparar con lo que entiende Whisper sirve el texto hablado o el de pantalla
# (Whisper escribe «DNI», no «de ene i»): nos quedamos con el que más se parezca.
ESCRITO = {p["clave"]: p["texto"] for p in PREGUNTAS} | AVISOS


def simplificar(texto: str) -> list[str]:
    """Minúsculas, sin tildes ni signos: «¿A cuál?» → ['a', 'cual']."""
    texto = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", texto)


def parecido(esperado: str, escuchado: str) -> float:
    """Qué tanto se parece lo que entendió Whisper a lo que debía decir (0 a 1).
    Si falta la última palabra (el final cortado), la toma no sirve."""
    a, b = simplificar(esperado), simplificar(escuchado)
    if not b or a[-1] not in b[-3:]:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()

if __name__ == "__main__":
    elegidas = sys.argv[1:] or list(TEXTOS)
    texto_referencia = REFERENCIA.with_suffix(".txt").read_text(encoding="utf-8").strip()
    DESTINO.mkdir(parents=True, exist_ok=True)

    modelo = Qwen3TTSModel.from_pretrained(MODELO, device_map="cpu", dtype=torch.float32)
    # La "huella" de la voz se calcula una sola vez y se reutiliza para cada frase.
    voz = modelo.create_voice_clone_prompt(ref_audio=str(REFERENCIA), ref_text=texto_referencia)

    oido = WhisperModel("small", device="cpu", compute_type="int8")

    for clave in elegidas:
        archivo = DESTINO / f"{clave}.wav"
        mejor = (-1.0, None, 0)
        for intento in range(1, INTENTOS + 1):
            audios, frecuencia = modelo.generate_voice_clone(
                text=TEXTOS[clave], language="Spanish", voice_clone_prompt=voz
            )
            toma = np.concatenate([audios[0], np.zeros(int(SILENCIO_FINAL * frecuencia), dtype=audios[0].dtype)])
            sf.write(archivo, toma, frecuencia)
            # Whisper escucha a 16 kHz: convertimos una copia y se la pasamos como números.
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
                            str(archivo), str(archivo)], check=True)
            onda, _ = sf.read(archivo, dtype="float32")
            segmentos, _ = oido.transcribe(onda, language="es")
            escuchado = " ".join(seg.text for seg in segmentos)
            nota = max(parecido(TEXTOS[clave], escuchado), parecido(ESCRITO[clave], escuchado))
            print(f"  {clave} toma {intento}: {nota:.2f} → {escuchado.strip()}", flush=True)
            if nota > mejor[0]:
                mejor = (nota, toma, frecuencia)
            if nota >= PARECIDO_MINIMO:
                break
        sf.write(archivo, mejor[1], mejor[2])
        # WAV mono de 16 bits a 16 kHz: pesa poco y el navegador lo reproduce sin problema.
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
                        str(archivo), str(archivo)], check=True)
        aviso = "" if mejor[0] >= PARECIDO_MINIMO else "  ⚠️ revisar a oído"
        print(f"{archivo.name}: {TEXTOS[clave]} (nota {mejor[0]:.2f}){aviso}", flush=True)
