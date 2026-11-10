"""API de ReciclaVoz: el «motor» que usa la app web (carpeta web/).

La app web es solo HTML, CSS y JavaScript (se publica gratis en GitHub Pages) y no
puede correr Whisper ni guardar datos. Por eso le pide todo a esta API, que corre en
un servidor con Python (por ejemplo, Hugging Face Spaces).

Casi no hay lógica aquí: cada ruta llama a una función de nucleo/.
Esta capa solo traduce entre la web (JSON) y Python.

Para correrla en tu laptop (desde la carpeta del proyecto):
    .venv/bin/uvicorn api.main:app --reload --port 8000
y abre http://localhost:8000/docs para ver y probar todas las rutas.
"""
import io
import json
import os
import threading
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel

from nucleo import base_datos as bd
from nucleo.capacitacion import MATERIALES as GUIA_MATERIALES
from nucleo.capacitacion import MODULOS, QUIZ
from nucleo.catalogos import DISTRITOS_TRUJILLO, EQUIPOS, MATERIALES, TRANSPORTES
from nucleo.config import FUENTES
from nucleo.constancia import crear_constancia
from nucleo.extraccion import FichaReciclador, extraer_ficha
from nucleo.preguntas import PREGUNTAS
from nucleo.ubicacion import CENTROS, buscar_direccion
from nucleo.voz import cargar_modelo, transcribir

app = FastAPI(title="ReciclaVoz API", description="Registro de recicladores por voz")

# Qué páginas pueden usar esta API (CORS). En tu laptop, la web corre en localhost;
# en internet, en GitHub Pages. Se puede cambiar con la variable ORIGENES.
ORIGENES = os.environ.get("ORIGENES", "https://grey-d18.github.io").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def precargar_whisper() -> None:
    """Carga Whisper apenas arranca el servidor, en segundo plano: así la primera
    persona que habla no espera los segundos que tarda en cargar."""
    threading.Thread(target=cargar_modelo, daemon=True).start()


def filas(tabla: pd.DataFrame) -> list[dict]:
    """Convierte una tabla de pandas en una lista de diccionarios (los vacíos quedan en null)."""
    return json.loads(tabla.to_json(orient="records", force_ascii=False))


def reciclador_o_404(codigo: str) -> dict:
    reciclador = bd.buscar_reciclador(codigo.strip().upper())
    if reciclador is None:
        raise HTTPException(404, "No hay un reciclador con ese código.")
    for columna in bd.COLUMNAS_LISTA:
        reciclador[columna] = json.loads(reciclador[columna]) if reciclador[columna] else []
    return reciclador


# --- Datos fijos ----------------------------------------------------------------------
@app.get("/salud")
def salud() -> dict:
    return {"ok": True}


@app.get("/catalogos")
def catalogos() -> dict:
    """Listas que la web necesita para armar sus pantallas."""
    return {
        "distritos": DISTRITOS_TRUJILLO, "materiales": MATERIALES, "transportes": TRANSPORTES,
        "equipos": EQUIPOS, "centros": CENTROS,
        "preguntas": [{k: p[k] for k in ("clave", "texto", "ejemplo")} for p in PREGUNTAS],
    }


# --- Registro por voz -------------------------------------------------------------------
@app.post("/transcribir")
async def transcribir_audio(audio: UploadFile = File(...)) -> dict:
    """Recibe la grabación de una respuesta y devuelve lo que entendió Whisper."""
    extension = Path(audio.filename or "").suffix or ".webm"
    return {"texto": transcribir(await audio.read(), extension)}


class Respuestas(BaseModel):
    respuestas: dict[str, str]


@app.post("/ficha")
def llenar_ficha(datos: Respuestas) -> dict:
    """Ordena las respuestas en la ficha (Gemini, o reglas si no hay Gemini)."""
    ficha, metodo, _uso = extraer_ficha(datos.respuestas)
    return {"ficha": ficha.model_dump(), "metodo": metodo}


class FichaConfirmada(BaseModel):
    ficha: FichaReciclador
    metodo: str


@app.post("/recicladores")
def inscribir(datos: FichaConfirmada) -> dict:
    dni = datos.ficha.dni or ""
    if len(dni) != 8 or not dni.isdigit():
        raise HTTPException(422, "El DNI debe tener 8 números.")
    return {"codigo": bd.guardar_ficha(datos.ficha, datos.metodo)}


@app.get("/recicladores/ultimo")
def ultimo() -> dict | None:
    """El último inscrito: el demo pregunta «¿Es usted …?» al entrar."""
    return bd.ultimo_registrado()


@app.get("/recicladores")
def recicladores(distrito: str) -> list[dict]:
    return filas(bd.recicladores_del_distrito(distrito))


@app.get("/recicladores/{codigo}")
def reciclador(codigo: str) -> dict:
    return reciclador_o_404(codigo)


@app.get("/recicladores/{codigo}/constancia")
def constancia(codigo: str) -> Response:
    datos = reciclador_o_404(codigo)
    ficha = FichaReciclador.model_validate({c: datos.get(c) for c in FichaReciclador.model_fields}
                                           | {"observaciones": datos.get("observaciones") or ""})
    return Response(crear_constancia(ficha, datos["codigo"]), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="constancia_{datos["codigo"]}.pdf"'})


# --- Capacitación ---------------------------------------------------------------------
@app.get("/capacitacion")
def capacitacion() -> dict:
    campo = pd.read_csv(FUENTES / "precios_campo_el_porvenir.csv")
    return {
        "modulos": [{"titulo": m["titulo"], "puntos": m["puntos"]} for m in MODULOS],
        "materiales": GUIA_MATERIALES,
        # Al quiz se le quita la respuesta correcta: la revisa el servidor.
        "quiz": [{"pregunta": q["pregunta"], "opciones": q["opciones"]} for q in QUIZ],
        "precios_campo": filas(campo[["material", "precio_min_soles_kg", "precio_max_soles_kg",
                                      "exportacion_soles_kg"]].round(2)),
    }


class Quiz(BaseModel):
    respuestas: list[str | None]
    codigo: str | None = None


@app.post("/quiz")
def revisar_quiz(datos: Quiz) -> dict:
    correcciones = [{"pregunta": q["pregunta"], "correcta": q["correcta"]}
                    for q, r in zip(QUIZ, datos.respuestas + [None] * len(QUIZ)) if r != q["correcta"]]
    aprobo = not correcciones
    capacitado = bool(aprobo and datos.codigo and bd.marcar_capacitado(datos.codigo))
    return {"aciertos": len(QUIZ) - len(correcciones), "total": len(QUIZ),
            "correcciones": correcciones, "capacitado": capacitado}


# --- Acopios y precios --------------------------------------------------------------------
@app.get("/precios")
def precios(distrito: str | None = None) -> list[dict]:
    """Una fila por material: último precio, mayor precio del día y dónde."""
    tabla = bd.tabla_de_precios(distrito)
    return [{"material": f["Material"], "ultimo": f["Último precio"], "hora": f["Hora"],
             "mayor": f["Mayor precio hoy"], "donde": f["Dónde (mayor precio)"]} for f in filas(tabla)]


@app.get("/acopios")
def acopios(distrito: str | None = None) -> list[dict]:
    return filas(bd.leer_acopios(distrito))


class Lugar(BaseModel):
    direccion: str
    lat: float
    lon: float


class Acopio(Lugar):
    nombre: str
    distrito: str


@app.post("/acopios")
def nuevo_acopio(datos: Acopio) -> dict:
    return {"id": bd.guardar_acopio(datos.nombre, datos.distrito, datos.direccion, datos.lat, datos.lon)}


@app.put("/acopios/{acopio_id}/ubicacion")
def mover_acopio(acopio_id: int, datos: Lugar) -> dict:
    bd.actualizar_ubicacion_acopio(acopio_id, datos.direccion, datos.lat, datos.lon)
    return {"ok": True}


@app.get("/acopios/{acopio_id}/precios")
def precios_del_acopio(acopio_id: int) -> dict[str, float]:
    """Los precios de hoy de un local (el último de cada material)."""
    hoy = bd.precios_de_hoy()
    mios = hoy[hoy["acopio_id"] == acopio_id].sort_values("fecha_hora").groupby("material").last()
    return mios["precio_soles_kg"].to_dict()


class Precios(BaseModel):
    precios: dict[str, float]


@app.post("/acopios/{acopio_id}/precios")
def publicar_precios(acopio_id: int, datos: Precios) -> dict:
    bd.guardar_precios(acopio_id, datos.precios)
    return {"ok": True}


# --- Recojos ---------------------------------------------------------------------------
SIN_FOTO = ["foto"]  # la foto no va en las listas: se pide aparte, por su número


def recojos_json(tabla: pd.DataFrame) -> list[dict]:
    tabla = tabla.assign(tiene_foto=tabla["foto"].notna()).drop(columns=SIN_FOTO)
    return filas(tabla)


@app.get("/recojos/disponibles")
def recojos_disponibles(codigo: str) -> list[dict]:
    yo = reciclador_o_404(codigo)
    return recojos_json(bd.recojos_disponibles(yo["distrito_vivienda"], yo["codigo"]))


@app.get("/recojos/mios")
def mis_recojos(codigo: str) -> list[dict]:
    return recojos_json(bd.mis_recojos(codigo))


@app.get("/recojos")
def recojos_del_vecino(vecino: str) -> list[dict]:
    return filas(bd.recojos_del_vecino(vecino))


def achicar_foto(contenido: bytes) -> bytes:
    """Reduce la foto a 600 px como máximo: pesa poco y carga rápido."""
    imagen = Image.open(io.BytesIO(contenido)).convert("RGB")
    imagen.thumbnail((600, 600))
    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=80)
    return salida.getvalue()


@app.post("/recojos")
async def pedir_recojo(
    vecino: str = Form(...), descripcion: str = Form(...), peso_kg: float = Form(...),
    distrito: str = Form(...), direccion: str = Form(""), lat: float = Form(...), lon: float = Form(...),
    preferido: str = Form(""), foto: UploadFile | None = File(None),
) -> dict:
    imagen = achicar_foto(await foto.read()) if foto else None
    nuevo = bd.crear_recojo(vecino, distrito, direccion, lat, lon, descripcion, peso_kg, imagen, preferido or None)
    return {"id": nuevo}


@app.get("/recojos/{recojo_id}/foto")
def foto_del_recojo(recojo_id: int) -> Response:
    with bd.conectar() as conexion:
        fila = conexion.execute("SELECT foto FROM recojos WHERE id = ?", (recojo_id,)).fetchone()
    if not fila or not fila[0]:
        raise HTTPException(404, "Ese pedido no tiene foto.")
    return Response(fila[0], media_type="image/jpeg")


class Codigo(BaseModel):
    codigo: str


@app.post("/recojos/{recojo_id}/asignar")
def tomar_recojo(recojo_id: int, datos: Codigo) -> dict:
    bd.asignar_recojo(recojo_id, datos.codigo)
    return {"ok": True, "dias_para_recoger": bd.DIAS_PARA_RECOGER}


@app.post("/recojos/{recojo_id}/recogido")
def recojo_hecho(recojo_id: int) -> dict:
    bd.marcar_recogido(recojo_id)
    return {"ok": True}


@app.get("/ubicacion")
def ubicar(direccion: str, distrito: str) -> dict:
    """Dirección escrita → coordenadas (OpenStreetMap). Si no la encuentra, el centro del distrito."""
    punto = buscar_direccion(direccion, distrito)
    lat, lon = punto or CENTROS.get(distrito, CENTROS["Trujillo"])
    return {"lat": lat, "lon": lon, "encontrada": punto is not None}


# --- Panel municipal ------------------------------------------------------------------------
@app.get("/panel")
def panel(distritos: str = "") -> dict:
    """Indicadores, gráficos y lista para la municipalidad. distritos: separados por comas."""
    fichas = bd.leer_todos()
    elegidos = [d for d in distritos.split(",") if d]
    if elegidos:
        fichas = fichas[fichas["distrito_vivienda"].isin(elegidos)]
    total = len(fichas) or 1

    por_distrito = fichas["distrito_vivienda"].value_counts()
    materiales = fichas.explode("materiales")["materiales"].dropna().value_counts()

    sigersol = pd.read_csv(FUENTES / "sigersol_trujillo_distritos.csv")
    anio = int(sigersol["anio"].max())
    sigersol = sigersol[sigersol["anio"] == anio]
    sigersol["distrito"] = sigersol["distrito"].str.title().replace({"Victor Larco Herrera": "Víctor Larco Herrera"})
    oficial = sigersol.set_index("distrito")

    lista = fichas.copy()
    lista["dni"] = lista["dni"].astype(str).str[:2] + "******"  # protegemos el dato personal
    columnas = ["codigo", "fecha_registro", "origen", "nombre_completo", "dni", "distrito_vivienda",
                "materiales", "medio_transporte", "equipo_proteccion", "capacitado"]
    return {
        "todos_los_distritos": sorted(bd.leer_todos()["distrito_vivienda"].dropna().unique()),
        "indicadores": {
            "inscritos": len(fichas),
            # Quien solo tiene un saco carga poco: dato útil para entregar triciclos o carretillas.
            "solo_saco": int(fichas["medio_transporte"].apply(lambda t: t == ["Saco"] or not t).sum()),
            "en_asociacion": round(fichas["pertenece_asociacion"].fillna(0).sum() / total * 100),
            "sin_guantes": round(fichas["equipo_proteccion"].apply(lambda e: "Guantes" not in e).sum() / total * 100),
            "capacitados": round(fichas["capacitado"].sum() / total * 100),
        },
        "por_distrito": [
            {"distrito": d, "inscritos": int(n), "centro": CENTROS.get(d),
             "valorizado_t": None if d not in oficial.index else round(float(oficial.loc[d, "valorizado_t"])),
             "generado_t": None if d not in oficial.index else round(float(oficial.loc[d, "generado_t"])),
             "pct_valorizado": None if d not in oficial.index else round(float(oficial.loc[d, "pct_valorizado"]), 1)}
            for d, n in por_distrito.items()],
        "anio_sigersol": anio,
        "materiales": [{"material": m, "personas": int(n)} for m, n in materiales.items()],
        "lista": filas(lista.sort_values("fecha_registro", ascending=False)[columnas]),
    }
