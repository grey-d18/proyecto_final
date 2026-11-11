"""API de Recicla Contigo: el «motor» que usa la app web (carpeta web/).

La app web es solo HTML, CSS y JavaScript (se publica gratis en GitHub Pages) y no
puede correr Whisper ni guardar datos. Por eso le pide todo a esta API, que corre en
un servidor con Python (en la prueba, la laptop de la autora con un túnel de Cloudflare).

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
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel, Field

from nucleo import base_datos as bd
from nucleo.capacitacion import MATERIALES as GUIA_MATERIALES
from nucleo.capacitacion import MODULOS, QUIZ
from nucleo.catalogos import DISTRITOS_TRUJILLO, EQUIPOS, MATERIALES, TRANSPORTES
from nucleo.constancia import crear_constancia
from nucleo.extraccion import DIAS_SEMANA, FichaReciclador, extraer_ficha, extraer_horario
from nucleo.preguntas import PREGUNTAS, SEGUNDOS_POR_DEFECTO
from nucleo.ubicacion import CENTROS, buscar_direccion
from nucleo.voz import cargar_modelo, transcribir

app = FastAPI(title="Recicla Contigo API", description="Registro de recicladores por voz")

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
        "preguntas": [{"clave": p["clave"], "texto": p["texto"], "ejemplo": p["ejemplo"],
                       "segundos": p.get("segundos", SEGUNDOS_POR_DEFECTO)} for p in PREGUNTAS],
    }


# --- Registro por voz -------------------------------------------------------------------
@app.post("/transcribir")
async def transcribir_audio(audio: UploadFile = File(...)) -> dict:
    """Recibe la grabación de una respuesta y devuelve lo que entendió Whisper."""
    extension = Path(audio.filename or "").suffix or ".webm"
    # Whisper tarda unos segundos: lo corremos aparte (en otro hilo) para que, mientras tanto,
    # la API siga atendiendo a los demás (abrir pantallas, ver precios). Si varias personas
    # hablan a la vez, Whisper las atiende por turno.
    return {"texto": await run_in_threadpool(transcribir, await audio.read(), extension)}


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
    tabla["dias"] = tabla["dias"].apply(lambda d: json.loads(d) if d else [])
    return filas(tabla)


@app.get("/recojos/disponibles")
def recojos_disponibles(codigo: str) -> list[dict]:
    yo = reciclador_o_404(codigo)
    return recojos_json(bd.recojos_disponibles(yo["distrito_vivienda"], yo["codigo"]))


@app.get("/recojos/mios")
def mis_recojos(codigo: str) -> list[dict]:
    return recojos_json(bd.mis_recojos(codigo))


@app.get("/recojos")
def recojos_del_vecino(vecino_codigo: str) -> list[dict]:
    tabla = bd.recojos_del_vecino(vecino_codigo)
    tabla["dias"] = tabla["dias"].apply(lambda d: json.loads(d) if d else [])
    return filas(tabla)


# --- Vecinos ---------------------------------------------------------------------------
def ocultar(texto: str | None, visibles: int = 2) -> str:
    """Muestra solo el comienzo de un dato personal: 987654321 → 98*******."""
    texto = texto or ""
    return texto[:visibles] + "*" * max(0, len(texto) - visibles)


class Vecino(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    distrito: str
    direccion: str = Field(max_length=200)
    lat: float
    lon: float
    correo: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=120)
    telefono: str = Field(pattern=r"^9\d{8}$")   # celular peruano: 9 dígitos, empieza con 9
    acepto: bool                                 # aceptó que la municipalidad guarde sus datos


@app.post("/vecinos")
def inscribir_vecino(datos: Vecino) -> dict:
    if not datos.acepto:
        raise HTTPException(422, "Para inscribirse tiene que aceptar que la municipalidad guarde sus datos.")
    if datos.distrito not in DISTRITOS_TRUJILLO:
        raise HTTPException(422, "Ese distrito no es de la provincia de Trujillo.")
    codigo = bd.guardar_vecino(datos.nombre.strip(), datos.distrito, datos.direccion.strip(), datos.lat,
                               datos.lon, datos.correo.strip().lower(), datos.telefono)
    return {"codigo": codigo}


@app.get("/vecinos/{codigo}")
def vecino(codigo: str) -> dict:
    """Lo que la app necesita para el formulario. El correo y el teléfono van ocultos:
    los códigos son correlativos y cualquiera podría probar uno ajeno."""
    v = bd.buscar_vecino(codigo)
    if not v:
        raise HTTPException(404, "No hay un vecino con ese código.")
    return {"codigo": v["codigo"], "nombre": v["nombre"], "distrito": v["distrito"], "direccion": v["direccion"],
            "lat": v["lat"], "lon": v["lon"], "telefono": ocultar(v["telefono"]), "correo": ocultar(v["correo"], 3)}


class TextoHorario(BaseModel):
    texto: str = Field(max_length=500)


@app.post("/horario")
def entender_horario(datos: TextoHorario) -> dict:
    """«Lunes y miércoles de 7 a 9» → días y horas (Gemini con salida estructurada, o reglas)."""
    horario, metodo = extraer_horario(datos.texto)
    return {**horario.model_dump(), "metodo": metodo}


def achicar_foto(contenido: bytes) -> bytes:
    """Reduce la foto a 600 px como máximo: pesa poco y carga rápido."""
    imagen = Image.open(io.BytesIO(contenido)).convert("RGB")
    imagen.thumbnail((600, 600))
    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=80)
    return salida.getvalue()


@app.post("/recojos")
async def pedir_recojo(
    vecino_codigo: str = Form(...), descripcion: str = Form(..., max_length=200),
    peso_kg: float = Form(..., ge=0, le=500),
    direccion: str = Form(""), lat: float = Form(...), lon: float = Form(...),
    preferido: str = Form(""), foto: UploadFile | None = File(None),
    dias: str = Form(..., description='Lista JSON, por ejemplo ["Lunes", "Miércoles"]'),
    hora_desde: str = Form(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$"),
    hora_hasta: str = Form(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$"),
    horario_dicho: str = Form("", max_length=500),
    compartir_telefono: bool = Form(False),
) -> dict:
    if not bd.buscar_vecino(vecino_codigo):
        raise HTTPException(404, "Primero tiene que inscribirse como vecino.")
    try:
        lista_dias = [d for d in json.loads(dias) if d in DIAS_SEMANA]
    except (ValueError, TypeError):
        lista_dias = []
    if not lista_dias:
        raise HTTPException(422, "Elija al menos un día en que pueden pasar a recoger.")
    if hora_desde >= hora_hasta:
        raise HTTPException(422, "La hora «hasta» tiene que ser después de la hora «desde».")
    imagen = await run_in_threadpool(achicar_foto, await foto.read()) if foto else None
    nuevo = bd.crear_recojo(vecino_codigo, direccion, lat, lon, descripcion, peso_kg, imagen, preferido or None,
                            lista_dias, hora_desde, hora_hasta, horario_dicho, compartir_telefono)
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
# Todo sale de la propia app: recicladores, vecinos, acopios y recojos. Los datos personales
# (DNI, teléfono, correo) llegan ocultos: el panel no los necesita completos.
FRANJAS = [("Mañana", "00:00", "12:00"), ("Tarde", "12:00", "18:00"), ("Noche", "18:00", "24:00")]


def franja(hora: str | None) -> str | None:
    return next((nombre for nombre, desde, hasta in FRANJAS if hora and desde <= hora < hasta), None)


def dias_promedio_con_recojo(recogidos: pd.DataFrame) -> float:
    """En promedio, cuántos días distintos recogió algo cada reciclador (solo recojos hechos con la app)."""
    if recogidos.empty:
        return 0.0
    dias = recogidos.assign(dia=recogidos["fecha_recogido"].str[:10]).groupby("reciclador_asignado")["dia"].nunique()
    return round(float(dias.mean()), 1)


def datos_del_panel(distritos: str) -> dict[str, pd.DataFrame]:
    """Las cuatro tablas, filtradas por los distritos elegidos (vacío = todos)."""
    elegidos = [d for d in distritos.split(",") if d]
    tablas = {
        "recicladores": (bd.leer_todos(), "distrito_vivienda"),
        "vecinos": (bd.leer_tabla("vecinos"), "distrito"),
        "acopios": (bd.leer_tabla("acopios"), "distrito"),
        "recojos": (bd.leer_tabla("recojos"), "distrito"),
    }
    return {nombre: tabla[tabla[columna].isin(elegidos)] if elegidos else tabla
            for nombre, (tabla, columna) in tablas.items()}


@app.get("/panel")
def panel(distritos: str = "") -> dict:
    """Indicadores, gráficos y listas para la municipalidad. distritos: separados por comas."""
    d = datos_del_panel(distritos)
    fichas, vecinos, acopios, recojos = d["recicladores"], d["vecinos"], d["acopios"], d["recojos"]
    total = len(fichas) or 1
    recogidos = recojos[recojos["estado"] == "recogido"]
    precios = bd.leer_tabla("precios")

    # Acopios: qué compran y cuándo actualizaron sus precios por última vez
    lista_acopios = []
    for _, a in acopios.sort_values("nombre").iterrows():
        suyos = precios[precios["acopio_id"] == a["id"]]
        lista_acopios.append({
            "nombre": a["nombre"], "distrito": a["distrito"], "direccion": a["direccion"],
            "lat": a["lat"], "lon": a["lon"], "horario": a["horario"] or "—",
            "compra": sorted(suyos["material"].unique().tolist()),
            "ultima_actualizacion": suyos["fecha_hora"].max() if not suyos.empty else None,
        })

    pedidos_por_vecino = recojos["vecino_codigo"].value_counts()
    lista_vecinos = [{
        "codigo": v["codigo"], "fecha_registro": v["fecha_registro"], "nombre": v["nombre"],
        "distrito": v["distrito"], "telefono": ocultar(v["telefono"]), "correo": ocultar(v["correo"], 3),
        "pedidos": int(pedidos_por_vecino.get(v["codigo"], 0)),
    } for _, v in vecinos.sort_values("fecha_registro", ascending=False).iterrows()]

    dias_pedidos = recojos["dias"].dropna().apply(json.loads).explode().value_counts()
    franjas = recojos["hora_desde"].apply(franja).value_counts()

    lista = fichas.copy()
    lista["dni"] = lista["dni"].astype(str).str[:2] + "******"  # protegemos el dato personal
    columnas = ["codigo", "fecha_registro", "origen", "nombre_completo", "dni", "distrito_vivienda",
                "materiales", "medio_transporte", "equipo_proteccion", "capacitado"]

    todos = datos_del_panel("")
    con_datos = set(todos["recicladores"]["distrito_vivienda"]) | set(todos["vecinos"]["distrito"])
    meses = pd.concat([todos["recicladores"]["fecha_registro"], todos["vecinos"]["fecha_registro"],
                       todos["recojos"]["fecha_hora"]]).dropna().str[:7]
    return {
        "todos_los_distritos": [x for x in DISTRITOS_TRUJILLO if x in con_datos],
        "meses": sorted(meses.unique(), reverse=True),
        "indicadores": {
            "recicladores": len(fichas), "vecinos": len(vecinos), "acopios": len(acopios),
            "recojos_pedidos": len(recojos), "recojos_recogidos": len(recogidos),
            "kg_recogidos": round(float(recogidos["peso_kg"].sum())),
            # Quien solo tiene un saco carga poco: dato útil para entregar triciclos o carretillas.
            "solo_saco": int(fichas["medio_transporte"].apply(lambda t: t == ["Saco"] or not t).sum()),
            "en_asociacion": round(fichas["pertenece_asociacion"].fillna(0).sum() / total * 100),
            "sin_guantes": round(fichas["equipo_proteccion"].apply(lambda e: "Guantes" not in e).sum() / total * 100),
            "capacitados": round(fichas["capacitado"].sum() / total * 100),
        },
        "por_distrito": [{
            "distrito": x, "centro": CENTROS.get(x),
            "recicladores": int((fichas["distrito_vivienda"] == x).sum()),
            "vecinos": int((vecinos["distrito"] == x).sum()),
            "acopios": int((acopios["distrito"] == x).sum()),
            "recojos": int((recojos["distrito"] == x).sum()),
        } for x in DISTRITOS_TRUJILLO if x in con_datos],
        "materiales": [{"material": m, "personas": int(n)}
                       for m, n in fichas.explode("materiales")["materiales"].dropna().value_counts().items()],
        "recojos": {
            "por_franja": [{"franja": f, "pedidos": int(franjas.get(f, 0))} for f, _a, _b in FRANJAS],
            "por_dia": [{"dia": x, "pedidos": int(dias_pedidos.get(x, 0))} for x in DIAS_SEMANA],
            "pendientes": int((recojos["estado"] != "recogido").sum()),
        },
        "acopios": lista_acopios,
        "vecinos": lista_vecinos,
        "lista": filas(lista.sort_values("fecha_registro", ascending=False)[columnas]),
    }


@app.get("/panel/mes")
def resumen_del_mes(mes: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), distritos: str = "") -> dict:
    """Lo que pasó en un mes (AAAA-MM): inscritos nuevos, recojos y días con recojo."""
    d = datos_del_panel(distritos)
    del_mes = lambda tabla, columna: tabla[tabla[columna].fillna("").str[:7] == mes]  # noqa: E731
    pedidos = del_mes(d["recojos"], "fecha_hora")
    recogidos = del_mes(d["recojos"][d["recojos"]["estado"] == "recogido"], "fecha_recogido")
    anio, numero = map(int, mes.split("-"))
    anterior = f"{anio - (numero == 1)}-{12 if numero == 1 else numero - 1:02d}"
    recogidos_antes = d["recojos"][(d["recojos"]["estado"] == "recogido")
                                   & (d["recojos"]["fecha_recogido"].fillna("").str[:7] == anterior)]
    franjas = pedidos["hora_desde"].apply(franja).value_counts()
    por_distrito = recogidos["distrito"].value_counts()
    return {
        "mes": mes,
        "mes_en_curso": mes == f"{pd.Timestamp.now():%Y-%m}",
        "recicladores_nuevos": len(del_mes(d["recicladores"], "fecha_registro")),
        "vecinos_nuevos": len(del_mes(d["vecinos"], "fecha_registro")),
        "acopios_nuevos": len(del_mes(d["acopios"], "fecha_registro")),
        "recojos_pedidos": len(pedidos),
        "recojos_recogidos": len(recogidos),
        "recojos_recogidos_mes_anterior": len(recogidos_antes),
        "kg_recogidos": round(float(recogidos["peso_kg"].sum())),
        "recicladores_activos": int(recogidos["reciclador_asignado"].nunique()),
        "dias_promedio_con_recojo": dias_promedio_con_recojo(recogidos),
        "franja_mas_pedida": franjas.idxmax() if not franjas.empty else None,
        "distrito_con_mas_recojos": por_distrito.idxmax() if not por_distrito.empty else None,
    }
