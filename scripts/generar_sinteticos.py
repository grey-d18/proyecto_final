"""Genera 60 recicladores SINTÉTICOS para el demo (no son personas reales).

Las reglas del curso prohíben usar datos personales sin consentimiento, así que el
panel de la municipalidad se llena con personas inventadas. Para que se parezcan a
la realidad, las proporciones se inspiran en el trabajo de campo de la tesis en
El Porvenir (Trujillo): la mayoría no está en una asociación, casi nadie usa
mascarilla y lo más común es el cartón, la botella y el fierro.

Los DNI empiezan con "00" y se marcan como sintéticos.

Uso (desde la carpeta del proyecto):
    python scripts/generar_sinteticos.py
"""
import json
import random
from pathlib import Path

import pandas as pd

azar = random.Random(20261111)  # semilla fija: siempre salen los mismos datos

NOMBRES = ["Rosa", "María", "Juana", "Carmen", "Luz", "Elena", "Julia", "Teresa", "Pedro",
           "Juan", "Carlos", "José", "Luis", "Miguel", "Víctor", "Segundo", "Manuel", "Flor"]
APELLIDOS = ["Quispe", "Rodríguez", "Vásquez", "Castillo", "Alayo", "Gutiérrez", "Cruz",
             "Rojas", "Paredes", "Benites", "Sánchez", "Reyes", "Mendoza", "Polo", "Cabrera"]
# Peso de cada distrito: más recicladores en los distritos populares del norte.
DISTRITOS = {"El Porvenir": 30, "Florencia de Mora": 15, "La Esperanza": 20, "Alto Trujillo": 12,
             "Trujillo": 10, "Víctor Larco Herrera": 5, "Huanchaco": 4, "Moche": 4}
SECTORES = ["Río Seco", "Alan García", "Gran Chimú", "Wichanzao", "Manuel Arévalo", "Jerusalén", "Centro"]
ZONAS = ["Centro de Trujillo", "Mercado Mayorista", "Av. América", "Urb. California",
         "Mercado La Hermelinda", "Urb. El Golf", "Av. España"]
MATERIALES = ["Cartón", "Papel", "Botella PET", "Plástico duro", "Fierro / chatarra",
              "Cobre", "Aluminio", "Vidrio"]
PESO_MATERIAL = [0.85, 0.4, 0.8, 0.45, 0.6, 0.15, 0.35, 0.15]  # probabilidad de que lo recoja
COMPRADORES = ["Acopiador del barrio", "Chatarrero", "Local de acopio en El Porvenir", "Asociación"]


def un_reciclador(numero: int) -> dict:
    distrito = azar.choices(list(DISTRITOS), weights=DISTRITOS.values())[0]
    en_asociacion = azar.random() < 0.2
    equipo = [e for e, p in [("Guantes", 0.45), ("Mascarilla", 0.15), ("Chaleco", 0.1), ("Botas", 0.2)]
              if azar.random() < p or (en_asociacion and e in ("Guantes", "Chaleco"))]
    materiales = [m for m, p in zip(MATERIALES, PESO_MATERIAL) if azar.random() < p] or ["Cartón"]
    dia = azar.randint(1, 28)
    return {
        "codigo": f"RMR-2026-{numero:04d}",
        "fecha_registro": f"2026-{azar.randint(6, 10):02d}-{dia:02d} 10:00",
        "origen": "sintético",
        "metodo": "Datos sintéticos",
        "nombre_completo": f"{azar.choice(NOMBRES)} {azar.choice(APELLIDOS)} {azar.choice(APELLIDOS)}",
        "dni": f"00{azar.randint(100000, 999999)}",
        "edad": azar.randint(18, 72),
        "distrito_vivienda": distrito,
        "sector_vivienda": azar.choice(SECTORES),
        "zonas_trabajo": azar.choice(ZONAS),
        "dias_por_semana": azar.randint(3, 7),
        "anios_reciclando": azar.randint(1, 25),
        "materiales": json.dumps(materiales, ensure_ascii=False),
        "kg_semana": round(azar.uniform(40, 350)),
        "vende_a": "Asociación" if en_asociacion else azar.choice(COMPRADORES[:3]),
        "pertenece_asociacion": int(en_asociacion),
        "nombre_asociacion": "Asociación de Recicladores (sintética)" if en_asociacion else None,
        "equipo_proteccion": json.dumps(equipo, ensure_ascii=False),
        "campos_dudosos": "[]",
        "observaciones": "Registro sintético para el demo.",
        "capacitado": int(azar.random() < 0.25),
    }


if __name__ == "__main__":
    tabla = pd.DataFrame([un_reciclador(i) for i in range(1, 61)])
    destino = Path(__file__).resolve().parent.parent / "datos" / "recicladores_sinteticos.csv"
    tabla.to_csv(destino, index=False)
    print(f"Guardado {destino} con {len(tabla)} recicladores sintéticos")
