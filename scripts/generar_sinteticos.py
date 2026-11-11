"""Genera los datos SINTÉTICOS del demo (nada de esto es real).

    datos/sinteticos/recicladores.csv  60 recicladores inscritos
    datos/sinteticos/acopios.csv       8 locales de acopio (nombres y ubicaciones inventados)
    datos/sinteticos/precios.csv       precios del día que "ingresaron" los acopiadores
    datos/sinteticos/vecinos.csv       40 vecinos inscritos (teléfonos y correos inventados)
    datos/sinteticos/recojos.csv       5 pedidos de recojo que esperan reciclador ahora
    datos/sinteticos/recojos_historial.csv  recojos de junio a noviembre (para el resumen del mes)


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
# Un segundo generador para vecinos y recojos: así agregarlos no cambia a los recicladores.
azar2 = random.Random(20261112)

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
# Centro aproximado de cada distrito (para ubicar a los vecinos inventados cerca).
CENTROS = {"El Porvenir": (-8.079, -79.001), "Florencia de Mora": (-8.080, -79.023),
           "La Esperanza": (-8.077, -79.045), "Alto Trujillo": (-8.061, -78.990),
           "Trujillo": (-8.112, -79.029), "Víctor Larco Herrera": (-8.135, -79.048),
           "Huanchaco": (-8.079, -79.120), "Moche": (-8.171, -79.009)}
# Horarios típicos para recoger: días, desde, hasta y cómo lo diría el vecino.
HORARIOS = [
    (["Lunes", "Miércoles", "Viernes"], "07:00", "09:00", "Lunes, miércoles y viernes de 7 a 9 de la mañana"),
    (["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"], "07:00", "08:00", "De lunes a viernes de 7 a 8 de la mañana"),
    (["Sábado"], "08:00", "12:00", "Los sábados en la mañana, de 8 a 12"),
    (["Martes", "Jueves"], "14:00", "17:00", "Martes y jueves de 2 a 5 de la tarde"),
    (["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"], "18:00", "20:00", "Cualquier día menos domingo, de 6 a 8 de la noche"),
    (["Sábado", "Domingo"], "09:00", "13:00", "El fin de semana, de 9 a 1"),
]
DESCRIPCIONES = [("Cartón de cajas", 6), ("Botellas de plástico", 3), ("Periódicos y cuadernos viejos", 5),
                 ("Latas de aluminio", 2), ("Cartón y botellas", 8), ("Fierros viejos", 15),
                 ("Botellas de vidrio", 6), ("Cartón de una mudanza", 12)]


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


def un_vecino(numero: int, nombre: str | None = None, distrito: str | None = None,
             lugar: tuple[float, float] | None = None, mes: int | None = None) -> dict:
    distrito = distrito or azar2.choices(list(DISTRITOS), weights=DISTRITOS.values())[0]
    mes = mes or azar2.randint(6, 10)
    nombre = nombre or f"{azar2.choice(NOMBRES)} {azar2.choice(APELLIDOS)}"
    lat, lon = lugar or (CENTROS[distrito][0] + azar2.uniform(-0.008, 0.008),
                         CENTROS[distrito][1] + azar2.uniform(-0.008, 0.008))
    usuario = nombre.lower().split()[-1].translate(str.maketrans("áéíóúñ", "aeioun"))
    return {
        "codigo": f"VEC-2026-{numero:04d}",
        "fecha_registro": f"2026-{mes:02d}-{azar2.randint(1, 9 if mes == 11 else 28):02d} 18:00",
        "origen": "sintético",
        "nombre": nombre, "distrito": distrito, "direccion": f"{distrito} (dirección inventada)",
        "lat": round(lat, 5), "lon": round(lon, 5),
        "correo": f"{usuario}{numero}@ejemplo.pe",           # dominio de ejemplo: no es de nadie
        "telefono": f"900{azar2.randint(100000, 999999)}",   # 900…: números inventados
    }


def historial_de_recojos(vecinos: pd.DataFrame, recicladores: pd.DataFrame) -> list[dict]:
    """Recojos de junio a noviembre, cada mes un poco más (la app se va conociendo)."""
    por_mes = {6: 8, 7: 14, 8: 20, 9: 26, 10: 32, 11: 12}
    filas = []
    for mes, cantidad in por_mes.items():
        for _ in range(cantidad):
            dia = azar2.randint(1, 9 if mes == 11 else 28)
            fecha = f"2026-{mes:02d}-{dia:02d} {azar2.randint(7, 19):02d}:{azar2.choice(['00', '30'])}"
            candidatos = vecinos[vecinos["fecha_registro"] <= fecha]
            if candidatos.empty:  # a inicios de junio todavía nadie se inscribió: los primeros
                candidatos = vecinos.sort_values("fecha_registro").head(3)
            vecino = candidatos.sample(1, random_state=azar2.randint(0, 9999)).iloc[0]
            cerca = recicladores[(recicladores["distrito_vivienda"] == vecino["distrito"])
                                 & (recicladores["fecha_registro"] <= fecha)]
            if cerca.empty:
                cerca = recicladores[recicladores["fecha_registro"] <= fecha]
            reciclador = cerca.sample(1, random_state=azar2.randint(0, 9999)).iloc[0]
            dias, desde, hasta, dicho = azar2.choice(HORARIOS)
            descripcion, kg = azar2.choice(DESCRIPCIONES)
            # Los antiguos ya se recogieron; algunos de estos días todavía están en camino.
            recogido = not (mes == 11 and dia >= 8 and azar2.random() < 0.5)
            asignado = f"2026-{mes:02d}-{dia:02d} {min(int(fecha[11:13]) + 2, 21):02d}:00"
            filas.append({
                "fecha_hora": fecha, "vecino_codigo": vecino["codigo"], "vecino": vecino["nombre"],
                "distrito": vecino["distrito"], "direccion": vecino["direccion"],
                "lat": vecino["lat"], "lon": vecino["lon"], "descripcion": descripcion,
                "peso_kg": max(1, round(kg * azar2.uniform(0.5, 1.6))),
                "dias": json.dumps(dias, ensure_ascii=False), "hora_desde": desde, "hora_hasta": hasta,
                "horario_dicho": dicho, "compartir_telefono": int(azar2.random() < 0.6),
                "estado": "recogido" if recogido else "asignado",
                "reciclador_asignado": reciclador["codigo"], "fecha_asignacion": asignado,
                "fecha_recogido": (f"2026-{mes:02d}-{min(dia + azar2.randint(0, 2), 28 if mes != 11 else 9):02d} "
                                   f"{desde}") if recogido else None,
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
    # Acopios: fecha en que se inscribieron (para contar los nuevos de cada mes).
    tablas["acopios.csv"]["fecha_registro"] = [f"2026-{m:02d}-05 09:00" for m in (6, 6, 7, 7, 8, 9, 10, 11)]

    # Vecinos: los 5 de los pedidos actuales (se inscribieron este mes) y 35 más.
    vecinos = [un_vecino(i, nombre, distrito, (la, lo), mes=11 if i > 2 else 10)
               for i, (nombre, distrito, la, lo, _d, _k) in enumerate(PEDIDOS, start=1)]
    vecinos += [un_vecino(i) for i in range(len(PEDIDOS) + 1, 41)]
    tablas["vecinos.csv"] = pd.DataFrame(vecinos)

    # Pedidos actuales: ligados a su vecino, con horario y si comparte el teléfono.
    actuales = tablas["recojos.csv"]
    actuales.insert(0, "vecino_codigo", [v["codigo"] for v in vecinos[:len(PEDIDOS)]])
    horarios = [azar2.choice(HORARIOS) for _ in range(len(actuales))]
    actuales["dias"] = [json.dumps(h[0], ensure_ascii=False) for h in horarios]
    actuales["hora_desde"] = [h[1] for h in horarios]
    actuales["hora_hasta"] = [h[2] for h in horarios]
    actuales["horario_dicho"] = [h[3] for h in horarios]
    actuales["compartir_telefono"] = [1, 1, 0, 1, 0]
    actuales["direccion"] = [v["direccion"] for v in vecinos[:len(PEDIDOS)]]

    tablas["recojos_historial.csv"] = pd.DataFrame(
        historial_de_recojos(tablas["vecinos.csv"], tablas["recicladores.csv"]))
    for archivo, tabla in tablas.items():
        tabla.to_csv(SINTETICOS / archivo, index=False)
        print(f"Guardado datos/sinteticos/{archivo} ({len(tabla)} filas)")
