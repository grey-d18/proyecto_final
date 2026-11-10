"""Genera las voces de ejemplo con la voz de la fundadora, clonada con Qwen3-TTS.

¿Para qué?
    Son el respaldo del demo: si falla el micrófono o hay ruido en la sala, se aprieta
    "Usar voz de ejemplo" y Whisper transcribe estas grabaciones. Antes eran la voz
    robótica de macOS (scripts/generar_audios_ejemplo.py); ahora suenan como una
    persona real. Los datos que se dicen (Rosa Elena Quispe Ramos, DNI 00457812) son
    inventados.

¿Qué es Qwen3-TTS?
    Un modelo abierto y gratuito de Alibaba que convierte texto en voz. Con unos
    segundos de una grabación de referencia (y su transcripción) imita esa voz.
    Corre en la laptop: no se paga ninguna API.

No está en requirements.txt a propósito: la app no lo necesita (solo usa los .wav ya
generados) y PyTorch es demasiado pesado para el plan gratuito de Streamlit.
Se instala en un entorno aparte:
    uv venv qwen --python 3.12 && VIRTUAL_ENV=qwen uv pip install qwen-tts soundfile

Archivos de referencia (NO se suben a GitHub: la carpeta audios/ está en .gitignore):
    audios/referencia.wav   unos 10 a 25 s de tu voz, hablando natural
    audios/referencia.txt   lo que dices en esa grabación, palabra por palabra

Uso, desde la carpeta del proyecto (en CPU tarda ~30 s por audio; en "mps" fue mucho más lento):
    qwen/bin/python scripts/clonar_voz_ejemplo.py              # los 8 audios
    qwen/bin/python scripts/clonar_voz_ejemplo.py dni venta    # solo algunos
El modelo genera algo distinto cada vez: si un audio sale cortado, se vuelve a generar
solo ese y se comprueba con Whisper.
"""
import subprocess
import sys
from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

RAIZ = Path(__file__).resolve().parent.parent
REFERENCIA = RAIZ / "audios" / "referencia.wav"
DESTINO = RAIZ / "datos" / "audios_ejemplo"
MODELO = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"  # la versión pequeña (0.6 mil millones de parámetros)

# Escribimos como SE PRONUNCIA, no como se escribe: el modelo aprendió sobre todo con
# otros idiomas y leía «Quispe» como «Cuispe» y «DNI» en inglés. La app igual guarda la
# escritura correcta, porque Whisper (con sus hotwords) escribe «Quispe».
RESPUESTAS = {
    "nombre": "Me llamo Rosa Elena Kíspe Ramos.",
    "dni": "Mi de ene i es cero cero cuatro cinco, siete ocho, uno dos.",
    "edad": "Tengo cuarenta y siete años.",
    "vivienda": "Vivo en El Porvenir, en el sector Río Seco, cerca del mercado.",
    "trabajo": "Salgo por el centro de Trujillo y la avenida España, de lunes a sábado. "
               "Ya son como doce años que trabajo en esto.",
    "materiales": "Más que nada cartón, botellas y fierro. A veces latas. "
                  "Junto unos ciento ochenta kilos a la semana.",
    "venta": "Le vendo a un señor que tiene su acopio en el barrio. No, en asociación no estoy.",
    "proteccion": "Guantes sí uso, pero mascarilla no, me ahoga.",
}

if __name__ == "__main__":
    elegidas = sys.argv[1:] or list(RESPUESTAS)
    texto_referencia = REFERENCIA.with_suffix(".txt").read_text(encoding="utf-8").strip()

    modelo = Qwen3TTSModel.from_pretrained(MODELO, device_map="cpu", dtype=torch.float32)
    # La "huella" de la voz se calcula una sola vez y se reutiliza para cada frase.
    voz = modelo.create_voice_clone_prompt(ref_audio=str(REFERENCIA), ref_text=texto_referencia)

    for clave in elegidas:
        audios, frecuencia = modelo.generate_voice_clone(
            text=RESPUESTAS[clave], language="Spanish", voice_clone_prompt=voz
        )
        archivo = DESTINO / f"{clave}.wav"
        sf.write(archivo, audios[0], frecuencia)
        # Igual que las voces anteriores: WAV mono de 16 bits a 16 kHz (lo que prefiere Whisper).
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
                        str(archivo), str(archivo)], check=True)
        print(f"{archivo.name}: {RESPUESTAS[clave]}")
