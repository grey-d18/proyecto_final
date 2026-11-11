# Hace que las pruebas encuentren nucleo/ y api/ (la raíz del proyecto).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
