"""Genera los datos SINTÉTICOS del demo (nada de esto es real).

    datos/sinteticos/recicladores.csv  60 recicladores inscritos
    datos/sinteticos/acopios.csv       8 locales de acopio (nombres y ubicaciones inventados)
    datos/sinteticos/precios.csv       precios del día que "ingresaron" los acopiadores
    datos/sinteticos/recojos.csv       5 pedidos de recojo de vecinos


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
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # para poder importar nucleo/ al correrlo como script
from nucleo.catalogos import MATERIALES  # noqa: E402
from nucleo.config import SINTETICOS  # noqa: E402

azar = random.Random(20261111)  # semilla fija: siempre salen los mismos datos

NOMBRES = ["Rosa", "María", "Juana", "Carmen", "Luz", "Elena", "Julia", "Teresa", "Pedro",
           "Juan", "Carlos", "José", "Luis", "Miguel", "Víctor", "Segundo", "Manuel", "Flor"]
APELLIDOS = ["Quispe", "Rodríguez", "Vásquez", "Castillo", "Alayo", "Gutiérrez", "Cruz",
             "Rojas", "Paredes", "Benites", "Sánchez", "Reyes", "Mendoza", "Polo", "Cabrera"]
# Peso de cada distrito: más recicladores en los distritos populares del norte.
DISTRITOS = {"El Porvenir": 30, "Florencia de Mora": 15, "La Esperanza": 20, "Alto Trujillo": 12,
             "Trujillo": 10, "Víctor Larco Herrera": 5, "Huanchaco": 4, "Moche": 4}
SECTORES = ["Río Seco", "Alan García", "Gran Chimú", "Wichanzao", "Manuel Arévalo", "Jerusalén", "Centro"]
PESO_MATERIAL = [0.85, 0.4, 0.8, 0.45, 0.6, 0.15, 0.35, 0.15]  # probabilidad de que lo recoja
TRANSPORTES = {"Saco": 35, "Carrito": 25, "Triciclo": 25, "Carretilla": 8, "Mototaxi": 4, "A pie": 3}

# Locales de acopio inventados, cerca del centro de cada distrito.
ACOPIOS = [
    ("Acopio Río Seco", "El Porvenir", -8.0745, -78.9985, "Calle Los Laureles 210"),
    ("Reciclajes Don Lucho", "El Porvenir", -8.0820, -79.0050, "Av. Pumacahua 1450"),
    ("Chatarrería El Norte", "El Porvenir", -8.0700, -79.0060, "Jr. Sinchi Roca 330"),
    ("Compra y Venta San Martín", "Florencia de Mora", -8.0790, -79.0235, "Av. 26 de Marzo 815"),
    ("Recicla Esperanza", "La Esperanza", -8.0760, -79.0440, "Av. Condorcanqui 2100"),
    ("Acopio Wichanzao", "La Esperanza", -8.0690, -79.0510, "Calle Los Ángeles 145"),
    ("Acopio Alto Trujillo", "Alto Trujillo", -8.0610, -78.9900, "Barrio 4, Mz. K"),
    ("Reciclados del Centro", "Trujillo", -8.1090, -79.0250, "Av. España 1620"),
]
# Precio de referencia en soles por kilo (trabajo de campo en El Porvenir cuando existe).
PRECIO_BASE = {"Cartón": 0.40, "Papel": 0.35, "Botella PET": 0.50, "Plástico duro": 0.80,
               "Fierro / chatarra": 0.40, "Cobre": 30.0, "Aluminio": 4.0, "Vidrio": 0.10}
PEDIDOS = [
    ("Vecina Carmen", "El Porvenir", -8.0770, -79.0010, "Cajas de cartón de una mudanza", 12),
    ("Vecino Jorge", "El Porvenir", -8.0805, -78.9960, "Botellas de plástico de una fiesta", 4),
    ("Tienda La Económica", "La Esperanza", -8.0740, -79.0470, "Cartón y papel de la tienda", 20),
    ("Vecina Lucía", "Florencia de Mora", -8.0810, -79.0200, "Latas de aluminio y botellas", 3),
    ("Taller Mecánico Ruiz", "Trujillo", -8.1060, -79.0300, "Fierros viejos y piezas de metal", 35),
]


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
        "materiales": json.dumps(materiales, ensure_ascii=False),
        "medio_transporte": json.dumps(azar.choices(list(TRANSPORTES), weights=TRANSPORTES.values()),
                                       ensure_ascii=False),
        "pertenece_asociacion": int(en_asociacion),
        "nombre_asociacion": "Asociación de Recicladores (sintética)" if en_asociacion else None,
        "equipo_proteccion": json.dumps(equipo, ensure_ascii=False),
        "campos_dudosos": "[]",
        "observaciones": "Registro sintético para el demo.",
        "capacitado": int(azar.random() < 0.25),
    }


def precios_del_dia() -> list[dict]:
    """Cada acopio compra algunos materiales y actualiza su precio 1 a 3 veces en el día.
    Solo se guarda la HORA: la app les pone la fecha de hoy al cargarlos."""
    filas = []
    for numero, (nombre, *_resto) in enumerate(ACOPIOS, start=1):
        compra = [m for m in PRECIO_BASE if azar.random() < 0.7] or ["Cartón"]
        for material in compra:
            for _ in range(azar.randint(1, 3)):
                filas.append({
                    "acopio_id": numero,
                    "material": material,
                    "precio_soles_kg": round(PRECIO_BASE[material] * azar.uniform(0.85, 1.15), 2),
                    "hora": f"{azar.randint(7, 16):02d}:{azar.choice(['00', '15', '30', '45'])}",
                })
    return filas


if __name__ == "__main__":
    tablas = {
        "recicladores.csv": pd.DataFrame([un_reciclador(i) for i in range(1, 61)]),
        "acopios.csv": pd.DataFrame(
            [{"id": i, "nombre": n, "distrito": d, "lat": la, "lon": lo, "direccion": dir_,
              "horario": "Lun-Sáb 7:00-17:00"} for i, (n, d, la, lo, dir_) in enumerate(ACOPIOS, start=1)]),
        "precios.csv": pd.DataFrame(precios_del_dia()),
        "recojos.csv": pd.DataFrame(
            [{"vecino": v, "distrito": d, "lat": la, "lon": lo, "descripcion": desc, "peso_kg": kg,
              "horas_atras": azar.randint(1, 30)} for v, d, la, lo, desc, kg in PEDIDOS]),
    }
    for archivo, tabla in tablas.items():
        tabla.to_csv(SINTETICOS / archivo, index=False)
        print(f"Guardado datos/sinteticos/{archivo} ({len(tabla)} filas)")
