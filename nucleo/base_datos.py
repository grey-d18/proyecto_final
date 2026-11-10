"""Dónde se guardan las fichas: una base de datos SQLite.

SQLite es una base de datos que vive en un solo archivo (datos/registro.db) y
viene incluida en Python: no hay que instalar ni pagar un servidor.

La primera vez que se abre la app, la tabla se llena con 60 recicladores
SINTÉTICOS (inventados, ver scripts/generar_sinteticos.py) para que el panel de la
municipalidad tenga datos que mostrar. Las fichas nuevas del demo se suman a esos.

Nota: en Streamlit Community Cloud el archivo se borra cuando la app se reinicia.
Para el demo está bien; en producción se usaría una base en la nube (por ejemplo,
Postgres en Supabase).
"""
import json
import sqlite3
from datetime import datetime

import pandas as pd

from nucleo.config import BASE_DATOS, DATOS
from nucleo.extraccion import FichaReciclador

COLUMNAS_LISTA = ["materiales", "equipo_proteccion", "campos_dudosos"]


def conectar() -> sqlite3.Connection:
    """Abre la base y crea la tabla si todavía no existe."""
    conexion = sqlite3.connect(BASE_DATOS)
    conexion.execute(
        """CREATE TABLE IF NOT EXISTS recicladores (
            codigo TEXT PRIMARY KEY,
            fecha_registro TEXT,
            origen TEXT,               -- 'sintético' o 'registro por voz'
            metodo TEXT,               -- 'Claude …' o 'Reglas simples'
            nombre_completo TEXT, dni TEXT, edad INTEGER,
            distrito_vivienda TEXT, sector_vivienda TEXT, zonas_trabajo TEXT,
            dias_por_semana INTEGER, anios_reciclando INTEGER,
            materiales TEXT,           -- lista guardada como texto JSON
            kg_semana REAL, vende_a TEXT,
            pertenece_asociacion INTEGER, nombre_asociacion TEXT,
            equipo_proteccion TEXT,    -- lista guardada como texto JSON
            campos_dudosos TEXT, observaciones TEXT,
            capacitado INTEGER DEFAULT 0
        )"""
    )
    # Si la tabla está vacía, cargamos los recicladores sintéticos.
    if conexion.execute("SELECT COUNT(*) FROM recicladores").fetchone()[0] == 0:
        sinteticos = pd.read_csv(DATOS / "recicladores_sinteticos.csv", dtype={"dni": str})
        sinteticos.to_sql("recicladores", conexion, if_exists="append", index=False)
        conexion.commit()
    return conexion


def nuevo_codigo(conexion: sqlite3.Connection) -> str:
    """Código correlativo del registro, por ejemplo RMR-2026-0061."""
    total = conexion.execute("SELECT COUNT(*) FROM recicladores").fetchone()[0]
    return f"RMR-{datetime.now():%Y}-{total + 1:04d}"


def guardar_ficha(ficha: FichaReciclador, metodo: str) -> str:
    """Guarda una ficha nueva y devuelve su código de registro."""
    fila = ficha.model_dump()
    for columna in COLUMNAS_LISTA:  # SQLite no guarda listas: las pasamos a texto JSON
        fila[columna] = json.dumps(fila[columna], ensure_ascii=False)
    with conectar() as conexion:
        codigo = nuevo_codigo(conexion)
        fila |= {
            "codigo": codigo,
            "fecha_registro": f"{datetime.now():%Y-%m-%d %H:%M}",
            "origen": "registro por voz",
            "metodo": metodo,
        }
        columnas = ", ".join(fila)
        marcadores = ", ".join(f":{c}" for c in fila)
        conexion.execute(f"INSERT INTO recicladores ({columnas}) VALUES ({marcadores})", fila)
    return codigo


def marcar_capacitado(codigo: str) -> bool:
    """Marca que un reciclador aprobó la capacitación. Devuelve False si el código no existe."""
    with conectar() as conexion:
        cursor = conexion.execute(
            "UPDATE recicladores SET capacitado = 1 WHERE codigo = ?", (codigo.strip().upper(),)
        )
    return cursor.rowcount == 1


def leer_todos() -> pd.DataFrame:
    """Devuelve todas las fichas como tabla de pandas, con las listas ya convertidas."""
    with conectar() as conexion:
        tabla = pd.read_sql("SELECT * FROM recicladores ORDER BY fecha_registro DESC", conexion)
    for columna in COLUMNAS_LISTA:
        tabla[columna] = tabla[columna].apply(lambda texto: json.loads(texto) if texto else [])
    return tabla
