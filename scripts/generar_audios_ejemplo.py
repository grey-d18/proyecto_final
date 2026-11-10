"""Genera audios de ejemplo con la voz sintética de macOS (comando `say`).

Sirven como respaldo en el demo: si falla el micrófono o hay mucho ruido en la
sala, se aprieta "Usar voz de ejemplo" y Whisper transcribe estas grabaciones.
La persona es inventada (Rosa Elena Quispe Ramos), y el DNI también.

Solo funciona en Mac. Uso (desde la carpeta del proyecto):
    python scripts/generar_audios_ejemplo.py
"""
import subprocess
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "datos" / "audios_ejemplo"
VOZ = "Paulina" if "Paulina" in subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout else "Flo"

# Respuestas habladas como las diría una persona, con rodeos y números en palabras.
RESPUESTAS = {
    "nombre": "Me llamo Rosa Elena Quispe Ramos.",
    "dni": "Mi DNI es cero cero cuatro cinco, siete ocho, uno dos.",
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
    DESTINO.mkdir(parents=True, exist_ok=True)
    for clave, texto in RESPUESTAS.items():
        archivo = DESTINO / f"{clave}.wav"
        # --data-format=LEI16@16000 = WAV de 16 bits a 16 kHz, el formato que prefiere Whisper.
        subprocess.run(["say", "-v", VOZ, "-r", "165", "-o", str(archivo),
                        "--file-format=WAVE", "--data-format=LEI16@16000", texto], check=True)
        print(f"{archivo.name}: {texto}")
