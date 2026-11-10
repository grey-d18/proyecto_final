"""Dónde se guarda todo: una base de datos SQLite.

SQLite es una base de datos que vive en un solo archivo (datos/registro.db) y
viene incluida en Python: no hay que instalar ni pagar un servidor.

Tablas:
    recicladores  las fichas del registro (lo que llena la IA y confirma la persona)
    acopios       los locales de acopio (los registra el acopiador)
    precios       cada precio que un acopiador ingresa (material, S/ por kg, fecha y hora)
    recojos       los pedidos de los vecinos («tengo reciclaje para que alguien lo recoja»)

La primera vez que se abre la app, las tablas se llenan con datos SINTÉTICOS
(inventados, ver scripts/generar_sinteticos.py) para que el demo tenga qué mostrar.

Nota: en Streamlit Community Cloud el archivo se borra cuando la app se reinicia.
Para el demo está bien; en producción se usaría una base en la nube (por ejemplo,
Postgres en Supabase).
"""
import json
import sqlite3
from datetime import datetime, timedelta

import pandas as pd

from nucleo.config import BASE_DATOS, SINTETICOS
from nucleo.extraccion import FichaReciclador

COLUMNAS_LISTA = ["materiales", "medio_transporte", "equipo_proteccion", "campos_dudosos"]
VERSION_ESQUEMA = 2   # súbelo si cambian las tablas: la base vieja se borra y se vuelve a crear
DIAS_PARA_RECOGER = 3  # si el reciclador no recoge en 3 días, el pedido vuelve a estar disponible

TABLAS = {
    "recicladores": """
        codigo TEXT PRIMARY KEY,
        fecha_registro TEXT,
        origen TEXT,               -- 'sintético' o 'registro por voz'
        metodo TEXT,               -- 'Gemini …' o 'Reglas simples'
        nombre_completo TEXT, dni TEXT, edad INTEGER,
        distrito_vivienda TEXT, sector_vivienda TEXT, zonas_trabajo TEXT,
        dias_por_semana INTEGER, anios_reciclando INTEGER,
        materiales TEXT,           -- lista guardada como texto JSON
        medio_transporte TEXT,     -- lista guardada como texto JSON
        pertenece_asociacion INTEGER, nombre_asociacion TEXT,
        equipo_proteccion TEXT,    -- lista guardada como texto JSON
        campos_dudosos TEXT, observaciones TEXT,
        capacitado INTEGER DEFAULT 0""",
    "acopios": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, distrito TEXT, direccion TEXT, lat REAL, lon REAL, horario TEXT""",
    "precios": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acopio_id INTEGER, material TEXT, precio_soles_kg REAL,
        fecha_hora TEXT            -- 'AAAA-MM-DD HH:MM'""",
    "recojos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT, vecino TEXT, distrito TEXT, direccion TEXT, lat REAL, lon REAL,
        descripcion TEXT, peso_kg REAL,
        foto BLOB,                 -- la imagen tal cual (bytes)
        reciclador_preferido TEXT, -- código del reciclador elegido, o vacío = cualquiera de la zona
        estado TEXT,               -- 'disponible', 'asignado' o 'recogido'
        reciclador_asignado TEXT, fecha_asignacion TEXT""",
}


def ahora() -> str:
    return f"{datetime.now():%Y-%m-%d %H:%M}"


def conectar() -> sqlite3.Connection:
    """Abre la base, crea las tablas si no existen y las llena con datos sintéticos."""
    conexion = sqlite3.connect(BASE_DATOS)
    # Si la base es de una versión anterior de la app (otras columnas), la rehacemos.
    if conexion.execute("PRAGMA user_version").fetchone()[0] != VERSION_ESQUEMA:
        for tabla in TABLAS:
            conexion.execute(f"DROP TABLE IF EXISTS {tabla}")
        conexion.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
    for tabla, columnas in TABLAS.items():
        # El salto de línea antes de ")" evita que un comentario «--» final se coma el paréntesis.
        conexion.execute(f"CREATE TABLE IF NOT EXISTS {tabla} ({columnas}\n)")

    if conexion.execute("SELECT COUNT(*) FROM recicladores").fetchone()[0] == 0:
        cargar_sinteticos(conexion)
    return conexion


def cargar_sinteticos(conexion: sqlite3.Connection) -> None:
    """Llena las tablas vacías con los CSV de la carpeta datos/sinteticos/."""
    pd.read_csv(SINTETICOS / "recicladores.csv", dtype={"dni": str}).to_sql(
        "recicladores", conexion, if_exists="append", index=False)
    pd.read_csv(SINTETICOS / "acopios.csv").to_sql("acopios", conexion, if_exists="append", index=False)

    # Los precios sintéticos solo traen la hora: les ponemos la fecha de HOY para que
    # la tabla «menor precio del día» siempre tenga datos.
    precios = pd.read_csv(SINTETICOS / "precios.csv")
    precios["fecha_hora"] = f"{datetime.now():%Y-%m-%d} " + precios.pop("hora")
    precios.to_sql("precios", conexion, if_exists="append", index=False)

    recojos = pd.read_csv(SINTETICOS / "recojos.csv")
    recojos["fecha_hora"] = recojos.pop("horas_atras").apply(
        lambda horas: f"{datetime.now() - timedelta(hours=int(horas)):%Y-%m-%d %H:%M}")
    recojos["estado"] = "disponible"
    recojos.to_sql("recojos", conexion, if_exists="append", index=False)
    conexion.commit()


# --- Recicladores ----------------------------------------------------------------------
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
        fila |= {"codigo": codigo, "fecha_registro": ahora(), "origen": "registro por voz", "metodo": metodo}
        columnas = ", ".join(fila)
        marcadores = ", ".join(f":{c}" for c in fila)
        conexion.execute(f"INSERT INTO recicladores ({columnas}) VALUES ({marcadores})", fila)
    return codigo


def marcar_capacitado(codigo: str) -> bool:
    """Marca que un reciclador aprobó la capacitación. Devuelve False si el código no existe."""
    with conectar() as conexion:
        cursor = conexion.execute(
            "UPDATE recicladores SET capacitado = 1 WHERE codigo = ?", (codigo.strip().upper(),))
    return cursor.rowcount == 1


def leer_todos() -> pd.DataFrame:
    """Devuelve todas las fichas como tabla de pandas, con las listas ya convertidas."""
    with conectar() as conexion:
        tabla = pd.read_sql("SELECT * FROM recicladores ORDER BY fecha_registro DESC", conexion)
    for columna in COLUMNAS_LISTA:
        tabla[columna] = tabla[columna].apply(lambda texto: json.loads(texto) if texto else [])
    return tabla


def ultimo_registrado() -> dict | None:
    """El último reciclador inscrito (para preguntar «¿Eres …?» al entrar)."""
    with conectar() as conexion:
        conexion.row_factory = sqlite3.Row
        fila = conexion.execute(
            "SELECT codigo, nombre_completo, distrito_vivienda FROM recicladores "
            "ORDER BY (origen = 'registro por voz') DESC, fecha_registro DESC LIMIT 1").fetchone()
    return dict(fila) if fila else None


def buscar_reciclador(codigo: str) -> dict | None:
    with conectar() as conexion:
        conexion.row_factory = sqlite3.Row
        fila = conexion.execute("SELECT * FROM recicladores WHERE codigo = ?", (codigo,)).fetchone()
    return dict(fila) if fila else None


def recicladores_del_distrito(distrito: str) -> pd.DataFrame:
    with conectar() as conexion:
        return pd.read_sql("SELECT codigo, nombre_completo FROM recicladores WHERE distrito_vivienda = ? "
                           "ORDER BY nombre_completo", conexion, params=(distrito,))


# --- Acopios y precios --------------------------------------------------------------------
def leer_acopios(distrito: str | None = None) -> pd.DataFrame:
    with conectar() as conexion:
        if distrito:
            return pd.read_sql("SELECT * FROM acopios WHERE distrito = ?", conexion, params=(distrito,))
        return pd.read_sql("SELECT * FROM acopios ORDER BY nombre", conexion)


def guardar_acopio(nombre: str, distrito: str, direccion: str, lat: float, lon: float) -> int:
    """Registra un local de acopio nuevo y devuelve su número (id)."""
    with conectar() as conexion:
        cursor = conexion.execute(
            "INSERT INTO acopios (nombre, distrito, direccion, lat, lon, horario) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, distrito, direccion, lat, lon, ""))
    return cursor.lastrowid


def actualizar_ubicacion_acopio(acopio_id: int, direccion: str, lat: float, lon: float) -> None:
    with conectar() as conexion:
        conexion.execute("UPDATE acopios SET direccion = ?, lat = ?, lon = ? WHERE id = ?",
                         (direccion, lat, lon, acopio_id))


def guardar_precios(acopio_id: int, precios: dict[str, float]) -> None:
    """Guarda los precios que el acopiador ingresó ahora (cada uno con fecha y hora)."""
    with conectar() as conexion:
        conexion.executemany(
            "INSERT INTO precios (acopio_id, material, precio_soles_kg, fecha_hora) VALUES (?, ?, ?, ?)",
            [(acopio_id, material, precio, ahora()) for material, precio in precios.items() if precio > 0])


def precios_de_hoy(distrito: str | None = None) -> pd.DataFrame:
    """Todos los precios ingresados HOY, con el nombre y la ubicación del acopio."""
    consulta = """SELECT p.material, p.precio_soles_kg, p.fecha_hora, a.id AS acopio_id,
                         a.nombre AS acopio, a.distrito, a.direccion, a.lat, a.lon
                  FROM precios p JOIN acopios a ON a.id = p.acopio_id
                  WHERE substr(p.fecha_hora, 1, 10) = ?"""
    parametros = [f"{datetime.now():%Y-%m-%d}"]
    if distrito:
        consulta += " AND a.distrito = ?"
        parametros.append(distrito)
    with conectar() as conexion:
        return pd.read_sql(consulta, conexion, params=parametros)


def tabla_de_precios(distrito: str | None = None) -> pd.DataFrame:
    """Una fila por material: último precio actualizado, menor precio del día y dónde está.

    Si en el distrito todavía no hay precios de hoy, se usan los de toda la ciudad.
    """
    precios = precios_de_hoy(distrito)
    if precios.empty:
        precios = precios_de_hoy()
    filas = []
    for material, grupo in precios.groupby("material"):
        ultimo = grupo.sort_values("fecha_hora").iloc[-1]       # el más reciente
        menor = grupo.sort_values("precio_soles_kg").iloc[0]    # el más bajo del día
        filas.append({
            "Material": material,
            "Último precio": ultimo["precio_soles_kg"],
            "Hora": ultimo["fecha_hora"][-5:],
            "Menor precio hoy": menor["precio_soles_kg"],
            "Dónde (menor precio)": menor["acopio"],
        })
    return pd.DataFrame(filas)


# --- Recojos (pedidos de los vecinos) ---------------------------------------------------
def liberar_vencidos(conexion: sqlite3.Connection) -> None:
    """Regla de los 3 días: si un pedido asignado no se recogió a tiempo, vuelve a estar disponible."""
    limite = f"{datetime.now() - timedelta(days=DIAS_PARA_RECOGER):%Y-%m-%d %H:%M}"
    conexion.execute(
        "UPDATE recojos SET estado = 'disponible', reciclador_asignado = NULL, fecha_asignacion = NULL "
        "WHERE estado = 'asignado' AND fecha_asignacion < ?", (limite,))


def crear_recojo(vecino: str, distrito: str, direccion: str, lat: float, lon: float,
                 descripcion: str, peso_kg: float, foto: bytes | None, preferido: str | None) -> int:
    with conectar() as conexion:
        cursor = conexion.execute(
            "INSERT INTO recojos (fecha_hora, vecino, distrito, direccion, lat, lon, descripcion, peso_kg, "
            "foto, reciclador_preferido, estado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'disponible')",
            (ahora(), vecino, distrito, direccion, lat, lon, descripcion, peso_kg, foto, preferido))
    return cursor.lastrowid


def recojos_disponibles(distrito: str, codigo: str) -> pd.DataFrame:
    """Pedidos que este reciclador puede tomar: los de su distrito para «cualquiera» y los que lo eligieron a él."""
    with conectar() as conexion:
        liberar_vencidos(conexion)
        return pd.read_sql(
            "SELECT * FROM recojos WHERE estado = 'disponible' AND "
            "((distrito = ? AND (reciclador_preferido IS NULL OR reciclador_preferido = '')) "
            " OR reciclador_preferido = ?) ORDER BY fecha_hora DESC",
            conexion, params=(distrito, codigo))


def mis_recojos(codigo: str) -> pd.DataFrame:
    with conectar() as conexion:
        liberar_vencidos(conexion)
        return pd.read_sql("SELECT * FROM recojos WHERE estado = 'asignado' AND reciclador_asignado = ? "
                           "ORDER BY fecha_asignacion", conexion, params=(codigo,))


def asignar_recojo(recojo_id: int, codigo: str) -> None:
    with conectar() as conexion:
        conexion.execute(
            "UPDATE recojos SET estado = 'asignado', reciclador_asignado = ?, fecha_asignacion = ? "
            "WHERE id = ? AND estado = 'disponible'", (codigo, ahora(), recojo_id))


def marcar_recogido(recojo_id: int) -> None:
    with conectar() as conexion:
        conexion.execute("UPDATE recojos SET estado = 'recogido' WHERE id = ?", (recojo_id,))


def recojos_del_vecino(vecino: str) -> pd.DataFrame:
    with conectar() as conexion:
        return pd.read_sql("SELECT fecha_hora, descripcion, peso_kg, estado FROM recojos WHERE vecino = ? "
                           "ORDER BY fecha_hora DESC", conexion, params=(vecino,))
