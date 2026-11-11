"""De las respuestas habladas a una ficha ordenada (herramienta del curso: sesión 08,
LLMs con salidas estructuradas).

El problema: la gente no responde como un formulario. Dice «vivo por Río Seco, ahí
en El Porvenir, cerca del mercado» o «cartón, botellas y a veces latitas». La ficha
necesita distrito_vivienda = "El Porvenir" y materiales = ["Cartón", "Botella PET", "Aluminio"].

La solución: le damos a Gemini (Google, plan gratuito) las preguntas y las
respuestas transcritas, y le exigimos que devuelva JSON con un esquema fijo (la
clase FichaReciclador). Con las "salidas estructuradas" la API obliga al modelo a
respetar ese esquema, y además lo validamos con Pydantic: el código nunca recibe
texto suelto que tenga que adivinar.

Plan B: si no hay clave de la API (o falla internet), extraer_con_reglas() llena la
ficha con reglas simples (buscar números y palabras clave). Es menos inteligente,
pero el demo nunca se queda colgado.

Después, completar() revisa lo que llegó (DNI de 8 cifras, celular de 9, edad calculada)
y anota los «faltantes»: los campos del art. 34 b) que nadie dijo. Con esa lista,
nucleo/entrevista.py decide qué preguntar después.
"""
import re
import unicodedata
from datetime import date
from typing import Literal

from google import genai
from pydantic import BaseModel, Field

from nucleo.catalogos import DISTRITOS_TRUJILLO, EQUIPOS, MATERIALES, TRANSPORTES
from nucleo.config import GEMINI_MODELO, hay_clave_gemini, leer_ajuste
from nucleo.preguntas import TODAS

# --- 1. El esquema de la ficha ------------------------------------------------
# Literal[...] limita los valores posibles: el modelo solo puede elegir de esta lista.
# Las listas salen de nucleo/catalogos.py, así todas las pantallas usan los mismos nombres.
Material = Literal[tuple(MATERIALES + ["Otro"])]
Equipo = Literal[tuple(EQUIPOS)]
Transporte = Literal[tuple(TRANSPORTES + ["Otro"])]
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
Dia = Literal[tuple(DIAS_SEMANA)]

# Los campos que exige el art. 34 b) del Reglamento de la Ley 29419 (y los que usa la
# municipalidad para organizar la recolección). Si alguno queda vacío, es un «faltante».
# «horario» = hora_desde y hora_hasta; «equipo» = vehículo o equipo de protección.
# El correo puede quedar vacío, la edad se calcula y el cargo es «socio» por defecto.
OBLIGATORIOS = ["dni", "nombre_completo", "fecha_nacimiento", "genero", "direccion", "telefono",
                "materiales", "zona_trabajo", "dias_trabajo", "horario", "equipo"]


class DatosDichos(BaseModel):
    """Lo que la IA saca de las respuestas. None o lista vacía = la persona no lo dijo."""

    nombre_completo: str | None = Field(None, description="Nombres y apellidos, con mayúscula inicial")
    dni: str | None = Field(None, description="Exactamente 8 dígitos, sin espacios ni puntos")
    fecha_nacimiento: str | None = Field(None, description="Fecha de nacimiento en formato AAAA-MM-DD")
    genero: Literal["Femenino", "Masculino"] | None = Field(
        None, description="Solo si la persona lo dice o se refiere a sí misma en femenino o masculino («soy recicladora»). Nunca lo deduzcas del nombre")
    direccion: str | None = Field(None, description="Dirección donde vive: calle o barrio, número y distrito")
    distrito_vivienda: str | None = Field(None, description="Distrito donde vive")
    sector_vivienda: str | None = Field(None, description="Sector, barrio o asentamiento donde vive")
    telefono: str | None = Field(None, description="Celular: 9 dígitos que empiezan con 9, sin espacios")
    correo: str | None = Field(None, description="Correo electrónico, si lo dice")
    materiales: list[Material] = Field(default_factory=list, description="Materiales que recoge")
    zona_trabajo: str | None = Field(None, description="Zona, barrio o distrito donde recoge")
    dias_trabajo: list[Dia] = Field(default_factory=list, description="Días de la semana en que trabaja")
    hora_desde: str | None = Field(None, description="Hora en que empieza a trabajar, formato 24 h HH:MM")
    hora_hasta: str | None = Field(None, description="Hora en que termina, formato 24 h HH:MM")
    medio_transporte: list[Transporte] = Field(default_factory=list, description="Vehículo o con qué mueve los materiales")
    equipo_proteccion: list[Equipo] = Field(default_factory=list, description="Equipo de protección que dice usar")
    pertenece_asociacion: bool | None = Field(None, description="True solo si dice pertenecer a una asociación u organización")
    nombre_asociacion: str | None = Field(None, description="Nombre de la asociación, si lo dice")
    cargo: str | None = Field(None, description="Cargo en la asociación, solo si lo dice (presidente, tesorera…)")
    faltantes: list[str] = Field(default_factory=list, description=f"Campos obligatorios que nadie dijo, de esta lista: {OBLIGATORIOS}")
    campos_dudosos: list[str] = Field(
        default_factory=list, description="Campos que no quedaron claros y la persona debe confirmar")
    observaciones: str = Field("", description="Una o dos frases con lo importante que no cabe en otros campos")


class FichaReciclador(DatosDichos):
    """Una fila del Registro Municipal de Recicladores: lo dicho más lo que calcula la app."""

    edad: int | None = None                  # se calcula con la fecha de nacimiento
    # Opcionales del registro: NO se preguntan (quedan en null si no se dicen).
    estado_civil: str | None = None
    grado_instruccion: str | None = None
    ingreso_mensual: float | None = None
    seguro_salud: str | None = None
    por_completar: list[str] = Field(default_factory=list)  # faltantes que siguieron vacíos tras repreguntar
    declaracion_jurada_en: str | None = None  # fecha y hora en que dijo «sí, acepto»
    declaracion_dicha: str | None = None      # lo que dijo, tal cual


INSTRUCCIONES = f"""Eres el asistente del Registro Municipal de Recicladores de una municipalidad de Trujillo, Perú.
Recibes las preguntas del registro y las respuestas de un reciclador, transcritas de su voz con Whisper.
Llena la ficha solo con lo que la persona dijo. No inventes datos: si algo no se dijo, déjalo en null o en una lista vacía.
Un dato puede aparecer en la respuesta a otra pregunta (por ejemplo, el nombre al dar el DNI): úsalo igual.
La transcripción puede tener errores: corrige nombres de lugares de Trujillo ({", ".join(DISTRITOS_TRUJILLO)}).
Convierte números dichos en palabras a cifras: el DNI tiene 8 dígitos («cuarenta y cinco, setenta y ocho…» → 4578…),
el celular 9 dígitos y empieza con 9, la fecha de nacimiento va como AAAA-MM-DD.
Horario en 24 h: «de 6 a 11 de la mañana» → 06:00 a 11:00; «de lunes a sábado» son seis días.
«Plástico PET» es Botella PET; «metales» o «chatarra» es Fierro / chatarra.
En faltantes pon los campos de esta lista que nadie dijo: {OBLIGATORIOS}.
Si un dato parece mal transcrito (un DNI que no tiene 8 dígitos), anótalo en campos_dudosos.
Escribe las observaciones en español sencillo."""


def armar_mensaje(respuestas: dict[str, str]) -> str:
    """Junta cada pregunta con su respuesta en un solo texto para el modelo."""
    lineas = []
    for clave, respuesta in respuestas.items():
        pregunta = TODAS.get(clave, {}).get("texto", clave)
        lineas.append(f"Pregunta: {pregunta}\nRespuesta: {respuesta.strip() or '(sin respuesta)'}")
    return "\n\n".join(lineas)


# --- 2. Extracción con Gemini ------------------------------------------------
def extraer_con_gemini(respuestas: dict[str, str]) -> tuple[DatosDichos, dict]:
    """Pide a Gemini la ficha. Devuelve los datos y el uso de tokens."""
    cliente = genai.Client(
        api_key=leer_ajuste("GEMINI_API_KEY"),
        # Se llama después de cada respuesta: si Gemini no contesta en 10 segundos (el mínimo que acepta; o está saturado),
        # no reintentamos y usamos las reglas, para que la persona no espere en «Revisando».
        http_options={"timeout": 10_000, "retry_options": {"attempts": 1}},
    )
    respuesta = cliente.models.generate_content(
        model=GEMINI_MODELO,
        contents=armar_mensaje(respuestas),
        config={
            "system_instruction": INSTRUCCIONES,
            "response_mime_type": "application/json",              # que responda solo JSON…
            "response_json_schema": DatosDichos.model_json_schema(),  # …con este molde exacto
            "temperature": 0,                                       # sin creatividad: mismos datos, misma ficha
        },
    )
    # Validamos con Pydantic: si un tipo no calza, lanza ValidationError y pasamos a las reglas.
    datos = DatosDichos.model_validate_json(respuesta.text)
    uso = {
        "tokens_entrada": respuesta.usage_metadata.prompt_token_count,
        "tokens_salida": respuesta.usage_metadata.candidates_token_count,
    }
    return datos, uso


# --- 3. Plan B: extracción con reglas -----------------------------------------
UNIDADES = {"cero": 0, "uno": 1, "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
            "seis": 6, "siete": 7, "ocho": 8, "nueve": 9}
ESPECIALES = {"diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
              "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
              "veintiuno": 21, "veintiun": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24,
              "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29}
DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
           "ochenta": 80, "noventa": 90}
NUMEROS = UNIDADES | ESPECIALES | DECENAS | {"cien": 100}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]

PALABRAS_MATERIAL = {
    "carton": "Cartón", "papel": "Papel", "botella": "Botella PET", "pet": "Botella PET",
    "plastico": "Plástico duro", "fierro": "Fierro / chatarra", "chatarra": "Fierro / chatarra",
    "metal": "Fierro / chatarra", "cobre": "Cobre", "aluminio": "Aluminio", "lata": "Aluminio",
    "vidrio": "Vidrio", "tetrapak": "Tetrapak", "tetra pak": "Tetrapak",
}
PALABRAS_TRANSPORTE = {
    "saco": "Saco", "costal": "Saco", "carrito": "Carrito", "carreta": "Carretilla",
    "carretilla": "Carretilla", "triciclo": "Triciclo", "motofurgon": "Motofurgón",
    "moto furgon": "Motofurgón", "mototaxi": "Mototaxi", "a pie": "A pie", "caminando": "A pie",
}
PALABRAS_EQUIPO = {
    "guante": "Guantes", "mascarilla": "Mascarilla", "chaleco": "Chaleco",
    "bota": "Botas", "uniforme": "Uniforme",
}


def simplificar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar palabras sin errores de acento."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def grupos_de_cifras(texto: str) -> list[str]:
    """Convierte números dichos en palabras a cifras y devuelve los grupos seguidos.

    «cuatro cinco, setenta y ocho, doce, tres cuatro» -> ["45781234"]
    «45 78 12 34 y tengo 47 años»                      -> ["45781234", "47"]
    Cada número dicho aporta sus cifras («setenta y ocho» -> 78); las palabras que no son
    números cortan el grupo (salvo «y», «guion», comas y espacios).
    """
    palabras = re.findall(r"\d+|[a-zñ]+", simplificar(texto))
    grupos, actual, i = [], "", 0
    while i < len(palabras):
        p = palabras[i]
        if p.isdigit():
            actual += p
        elif p in UNIDADES or p in ESPECIALES or p == "cien":
            actual += str(NUMEROS[p])
        elif p in DECENAS:
            # «setenta y ocho» = 78; «setenta» solo = 70
            if i + 2 < len(palabras) and palabras[i + 1] == "y" and palabras[i + 2] in UNIDADES \
                    and UNIDADES[palabras[i + 2]] > 0:
                actual += str(DECENAS[p] + UNIDADES[palabras[i + 2]])
                i += 2
            else:
                actual += str(DECENAS[p])
        elif p in ("y", "guion") and actual:
            pass  # «cuatro cinco y siete ocho»: el «y» no corta el número
        else:
            if actual:
                grupos.append(actual)
            actual = ""
        i += 1
    if actual:
        grupos.append(actual)
    return grupos


def dni_desde_texto(texto: str) -> str | None:
    """El DNI son exactamente 8 cifras seguidas (dichas en cifras o en palabras)."""
    return next((g for g in grupos_de_cifras(texto) if len(g) == 8), None)


def celular_desde_texto(texto: str) -> str | None:
    """Un celular peruano: 9 cifras que empiezan con 9."""
    return next((g for g in grupos_de_cifras(texto) if len(g) == 9 and g.startswith("9")), None)


def fecha_desde_texto(texto: str) -> str | None:
    """«3 de mayo de 1978», «tres de mayo del 78» o «03/05/1978» -> «1978-05-03»."""
    t = simplificar(texto)
    numerica = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", t)
    if numerica:
        dia, mes, anio = int(numerica[1]), int(numerica[2]), int(numerica[3])
    else:
        # los días en palabras («tres de mayo») se pasan a cifras
        for palabra in sorted(UNIDADES | ESPECIALES, key=len, reverse=True):
            t = re.sub(rf"\b{palabra}\b(?= de )", str(NUMEROS[palabra]), t)
        t = re.sub(r"\bprimero\b(?= de )", "1", t)
        dicha = re.search(rf"\b(\d{{1,2}}) de ({'|'.join(MESES)})(?: de| del)? (\d{{2,4}}|mil novecientos[a-z ]*|dos mil[a-z ]*)", t)
        if not dicha:
            return None
        dia, mes = int(dicha[1]), MESES.index(dicha[2]) + 1
        anio_texto = dicha[3]
        if anio_texto.isdigit():
            anio = int(anio_texto)
        else:  # «mil novecientos setenta y ocho»
            base = 1900 if anio_texto.startswith("mil novecientos") else 2000
            resto = anio_texto.removeprefix("mil novecientos").removeprefix("dos mil")
            cifras = grupos_de_cifras(resto)
            anio = base + (int(cifras[0]) if cifras else 0)
    if anio < 100:  # «del 78» -> 1978
        anio += 1900 if anio > date.today().year % 100 else 2000
    try:
        return date(anio, mes, dia).isoformat()
    except ValueError:
        return None


def edad_desde_fecha(fecha: str | None, hoy: date | None = None) -> int | None:
    if not fecha:
        return None
    hoy = hoy or date.today()
    nacio = date.fromisoformat(fecha)
    return hoy.year - nacio.year - ((hoy.month, hoy.day) < (nacio.month, nacio.day))


def nombre_desde_texto(texto: str, es_respuesta_al_nombre: bool) -> str | None:
    """«Mi nombre es Rosa Quispe, …» o, si responde a la pregunta del nombre, lo primero que dice."""
    dicho = re.search(r"(?i)\b(?:me llamo|mi nombre es|mi nombre completo es)\s+([^,.;]+)", texto)
    if dicho:
        nombre = dicho[1]
    elif es_respuesta_al_nombre:
        nombre = re.sub(r"(?i)^(hola|buenos d[ií]as|buenas tardes)[,.\s]*", "", texto.strip())
        nombre = re.split(r"[,.;]", nombre)[0]
        nombre = re.sub(r"(?i)^(yo\s+)?soy\s+", "", nombre)
    else:
        return None
    # «Rosa Quispe y nací el…» -> «Rosa Quispe»
    nombre = re.split(r"(?i)\s+(?:y\s+)?(?:nac[ií]|mi fecha|tengo|soy)\b", nombre)[0]
    nombre = re.sub(r"\d.*", "", nombre).strip(" .")
    return nombre.title() if len(nombre.split()) >= 2 else None


def buscar(diccionario: dict[str, str], texto: str) -> list[str]:
    """Valores del diccionario cuyas palabras clave aparecen en el texto (sin repetir)."""
    t = simplificar(texto)
    vistos = []
    for palabra, valor in diccionario.items():
        if re.search(rf"\b{palabra}", t) and valor not in vistos:
            vistos.append(valor)
    return vistos


def extraer_con_reglas(respuestas: dict[str, str]) -> DatosDichos:
    """Llena la ficha sin LLM, buscando números y palabras clave en TODAS las respuestas.

    Así, si en la primera respuesta la persona ya dijo su nombre, se reconoce igual.
    """
    todo = " . ".join(respuestas.values())
    de = lambda *claves: " . ".join(respuestas.get(c, "") for c in claves)  # noqa: E731
    vivienda = de("vivienda_celular", "re_direccion")
    trabajo = de("trabajo", "re_materiales", "re_zona", "re_horario")
    con_que = de("equipo", "re_equipo") or todo

    nombre = None
    for clave in ("nombre_nacimiento", "re_nombre"):
        nombre = nombre or nombre_desde_texto(respuestas.get(clave, ""), es_respuesta_al_nombre=True)
    for texto in respuestas.values():
        nombre = nombre or nombre_desde_texto(texto, es_respuesta_al_nombre=False)

    t = simplificar(todo)
    genero = None
    if re.search(r"\b(soy mujer|mujer|femenino|recicladora|senora)\b", t):
        genero = "Femenino"
    elif re.search(r"\b(soy hombre|hombre|varon|masculino)\b", t):
        genero = "Masculino"

    # Dirección: lo que dijo antes del celular («vivo en … El Porvenir. Mi celular es …»)
    direccion = None
    if vivienda.strip():
        direccion = re.split(r"(?i)[,.;]?\s*(?:y\s+)?(?:mi\s+)?(?:celular|n[uú]mero|tel[eé]fono)\b", vivienda)[0]
        direccion = re.sub(r"(?i)^(yo\s+)?(vivo\s+)?(en\s+)?(la\s+|el\s+)?", "", direccion.strip()).strip(" .,")
        direccion = direccion[:1].upper() + direccion[1:] if re.search(r"[a-zA-Z]", direccion) else None
    distrito = next((d for d in DISTRITOS_TRUJILLO if simplificar(d) in simplificar(vivienda)), None)

    correo = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", re.sub(r"\s+arroba\s+", "@", todo))

    # Zona: un distrito nombrado al hablar del trabajo, o «zona / por / barrio X»
    zona = None
    if trabajo.strip():
        zona_dicha = re.search(r"(?i)\b(?:en la zona de|en el|en la|zona|por|barrio)\s+([^,.;]+?)(?=,|\.|;| de lunes| los | todos| de \d| desde|$)", trabajo)
        distrito_trabajo = next((d for d in DISTRITOS_TRUJILLO if simplificar(d) in simplificar(trabajo)), None)
        zona = (zona_dicha[1].strip() if zona_dicha else None) or distrito_trabajo

    horario = horario_con_reglas(trabajo) if trabajo.strip() else HorarioRecojo(dias=[], hora_desde=None, hora_hasta=None)

    materiales = buscar(PALABRAS_MATERIAL, trabajo or todo)
    if "plastico pet" in simplificar(trabajo or todo) and "Plástico duro" in materiales:
        materiales.remove("Plástico duro")  # «plástico PET» son botellas, no plástico duro
    transporte = buscar(PALABRAS_TRANSPORTE, con_que)
    if "Motofurgón" in transporte and "Mototaxi" in transporte and "mototaxi" not in simplificar(con_que):
        transporte.remove("Mototaxi")
    texto_epp = simplificar(con_que)
    equipo = [e for p, e in PALABRAS_EQUIPO.items() if p in texto_epp and f"{p} no" not in texto_epp
              and f"no uso {p}" not in texto_epp]

    return DatosDichos(
        nombre_completo=nombre,
        dni=dni_desde_texto(de("dni", "re_dni") or todo) or dni_desde_texto(todo),
        fecha_nacimiento=fecha_desde_texto(todo),
        genero=genero,
        direccion=direccion,
        distrito_vivienda=distrito,
        telefono=celular_desde_texto(vivienda) or celular_desde_texto(de("re_celular")) or celular_desde_texto(todo),
        correo=correo[0] if correo else None,
        materiales=sorted(materiales),
        zona_trabajo=zona,
        dias_trabajo=horario.dias,
        hora_desde=horario.hora_desde,
        hora_hasta=horario.hora_hasta,
        medio_transporte=transporte,
        equipo_proteccion=equipo,
        observaciones="Ficha llenada con reglas simples (sin LLM): revise cada campo.",
    )


# --- 4. Revisar, calcular y decir qué falta ------------------------------------------
def campo_vacio(ficha: DatosDichos, campo: str) -> bool:
    if campo == "horario":
        return not (ficha.hora_desde and ficha.hora_hasta)
    if campo == "equipo":
        return not (ficha.medio_transporte or ficha.equipo_proteccion)
    valor = getattr(ficha, campo)
    return valor is None or valor == "" or valor == []


def completar(datos: DatosDichos, respuestas: dict[str, str]) -> FichaReciclador:
    """Revisa lo que devolvió la IA (o las reglas), calcula la edad y anota los faltantes.

    No confiamos a ciegas en el modelo: el DNI y el celular se validan aquí, y la lista de
    faltantes se recalcula con OBLIGATORIOS (la del modelo solo es una pista).
    """
    ficha = FichaReciclador(**datos.model_dump())
    dudosos = set(ficha.campos_dudosos)
    todo = " . ".join(respuestas.values())

    # DNI: exactamente 8 cifras. Si el modelo no lo logró, probamos convertir las palabras.
    dni = re.sub(r"\D", "", ficha.dni or "")
    if len(dni) != 8:
        dni = dni_desde_texto(respuestas.get("re_dni") or respuestas.get("dni") or "") or dni_desde_texto(todo)
        if ficha.dni and not dni:
            dudosos.add("dni")
    ficha.dni = dni or None

    telefono = re.sub(r"\D", "", ficha.telefono or "")
    if telefono and not re.fullmatch(r"9\d{8}", telefono):
        dudosos.add("telefono")
        telefono = ""
    ficha.telefono = telefono or None

    formato_hora = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
    if not all(h is None or formato_hora.match(h) for h in (ficha.hora_desde, ficha.hora_hasta)):
        ficha.hora_desde = ficha.hora_hasta = None

    try:
        ficha.edad = edad_desde_fecha(ficha.fecha_nacimiento)
    except ValueError:  # una fecha que no existe
        ficha.fecha_nacimiento, ficha.edad = None, None
        dudosos.add("fecha_nacimiento")
    if ficha.edad is not None and not 12 <= ficha.edad <= 100:
        dudosos.add("fecha_nacimiento")

    if ficha.direccion and not ficha.distrito_vivienda:
        dudosos.add("distrito_vivienda")
    ficha.cargo = ficha.cargo or "socio"
    ficha.faltantes = [c for c in OBLIGATORIOS if campo_vacio(ficha, c)]
    ficha.campos_dudosos = sorted(dudosos)
    return ficha


def extraer_ficha(respuestas: dict[str, str]) -> tuple[FichaReciclador, str, dict]:
    """Intenta con Gemini y, si no se puede, usa las reglas.

    Devuelve (ficha, método usado, uso de tokens).
    """
    if hay_clave_gemini():
        try:
            datos, uso = extraer_con_gemini(respuestas)
            return completar(datos, respuestas), f"Gemini ({GEMINI_MODELO})", uso
        except Exception as error:
            # Cualquier problema (sin internet, clave mala, límite gratuito superado, respuesta lenta
            # o un JSON que no calza con el molde) no debe romper el demo: pasamos a las reglas.
            print(f"Falló Gemini, uso reglas: {error}")
            motivo = f"{type(error).__name__}: {str(error)[:120]}"
            return completar(extraer_con_reglas(respuestas), respuestas), f"Reglas simples (Gemini falló: {motivo})", {}
    return completar(extraer_con_reglas(respuestas), respuestas), "Reglas simples (sin LLM)", {}


# --- 5. Horario de recojo del vecino ------------------------------------------------
# El vecino dice cuándo puede pasar el reciclador («lunes, miércoles y viernes de 7 a 9») y
# lo convertimos en días y horas que el reciclador ve en la app. Igual que la ficha:
# Gemini con salida estructurada y, si no se puede, reglas simples.
class HorarioRecojo(BaseModel):
    """Cuándo puede pasar el reciclador a recoger. None = el vecino no lo dijo."""

    dias: list[Dia] = Field(description="Días de la semana en que se puede pasar a recoger")
    hora_desde: str | None = Field(description="Hora de inicio en formato 24 h HH:MM, por ejemplo 07:00 o 14:30")
    hora_hasta: str | None = Field(description="Hora de fin en formato 24 h HH:MM; después de hora_desde")


INSTRUCCIONES_HORARIO = """Un vecino de Trujillo (Perú) dijo, con su voz, cuándo puede pasar un reciclador a recoger su reciclaje.
El texto viene de Whisper y puede tener errores. Devuelve los días y el rango de horas.
- «de lunes a viernes» son los cinco días; «fin de semana» es sábado y domingo; «todos los días» o «cualquier día» son los siete.
- Usa formato de 24 horas: «de 2 a 5 de la tarde» → 14:00 a 17:00; «de 6 a 8 de la noche» → 18:00 a 20:00.
- Si no dice mañana ni tarde, elige lo más lógico para recoger reciclaje (de 7 a 9 es de la mañana).
- Si no dice los días o las horas, deja la lista vacía o null. No inventes."""


def horario_con_gemini(texto: str) -> HorarioRecojo:
    cliente = genai.Client(api_key=leer_ajuste("GEMINI_API_KEY"),
                           http_options={"timeout": 20_000, "retry_options": {"attempts": 2}})
    respuesta = cliente.models.generate_content(
        model=GEMINI_MODELO,
        contents=texto,
        config={"system_instruction": INSTRUCCIONES_HORARIO, "response_mime_type": "application/json",
                "response_json_schema": HorarioRecojo.model_json_schema(), "temperature": 0},
    )
    return HorarioRecojo.model_validate_json(respuesta.text)


def horario_con_reglas(texto: str) -> HorarioRecojo:
    """Plan B: busca nombres de días, «de X a Y» y si es de la tarde o de la noche."""
    t = simplificar(texto)
    nombres = [simplificar(d) for d in DIAS_SEMANA]
    if re.search(r"todos los dias|cualquier dia|toda la semana", t):
        dias = list(DIAS_SEMANA)
    else:
        dias = set()
        if "fin de semana" in t:
            dias |= {"Sábado", "Domingo"}
        for a, b in re.findall(r"(lunes|martes|miercoles|jueves|viernes|sabado|domingo) a (lunes|martes|miercoles|jueves|viernes|sabado|domingo)", t):
            dias |= set(DIAS_SEMANA[nombres.index(a):nombres.index(b) + 1])
        dias |= {DIAS_SEMANA[i] for i, n in enumerate(nombres) if re.search(rf"\b{n}", t)}
        dias = [d for d in DIAS_SEMANA if d in dias]
    if "menos domingo" in t or "menos el domingo" in t:
        dias = DIAS_SEMANA[:6]

    # Las horas: «de 7 a 9», «de 7:30 a 9», «entre las 2 y las 5»
    for palabra, numero in NUMEROS.items():
        t = re.sub(rf"\b{palabra}\b", str(numero), t)
    rango = re.search(r"(?:de|desde|entre)(?: las?)? (\d{1,2})(?::(\d{2}))? (?:a|hasta|y)(?: las?)? (\d{1,2})(?::(\d{2}))?", t)
    if not rango:
        return HorarioRecojo(dias=dias, hora_desde=None, hora_hasta=None)
    h1, m1, h2, m2 = int(rango[1]), int(rango[2] or 0), int(rango[3]), int(rango[4] or 0)
    if re.search(r"tarde|noche", t) and h1 < 12:   # «de 2 a 5 de la tarde» → 14:00 a 17:00
        h1 += 12
        h2 += 12 if h2 < 12 else 0
    elif h2 <= h1 and h2 < 12:       # «de 9 a 1» → de 9:00 a 13:00
        h2 += 12
    if not (0 <= h1 < 24 and 0 < h2 < 24 and (h1, m1) < (h2, m2)):
        return HorarioRecojo(dias=dias, hora_desde=None, hora_hasta=None)
    return HorarioRecojo(dias=dias, hora_desde=f"{h1:02d}:{m1:02d}", hora_hasta=f"{h2:02d}:{m2:02d}")


def extraer_horario(texto: str) -> tuple[HorarioRecojo, str]:
    """Devuelve (horario, método usado). Nunca falla: si Gemini no responde, usa las reglas."""
    if hay_clave_gemini():
        try:
            horario = horario_con_gemini(texto)
            # Validamos el formato: si Gemini devolvió algo raro, lo corregimos con las reglas.
            formato = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
            if all(h is None or formato.match(h) for h in (horario.hora_desde, horario.hora_hasta)):
                return horario, f"Gemini ({GEMINI_MODELO})"
        except Exception as error:
            print(f"Falló Gemini (horario), uso reglas: {error}")
    return horario_con_reglas(texto), "Reglas simples"
