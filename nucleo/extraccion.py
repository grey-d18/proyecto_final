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
"""
import re
import unicodedata
from typing import Literal

from google import genai
from pydantic import BaseModel, Field

from nucleo.catalogos import DISTRITOS_TRUJILLO, EQUIPOS, MATERIALES, TRANSPORTES
from nucleo.config import GEMINI_MODELO, hay_clave_gemini, leer_ajuste
from nucleo.preguntas import PREGUNTAS

# --- 1. El esquema de la ficha ------------------------------------------------
# Literal[...] limita los valores posibles: el modelo solo puede elegir de esta lista.
# Las listas salen de nucleo/catalogos.py, así todas las pantallas usan los mismos nombres.
Material = Literal[tuple(MATERIALES + ["Otro"])]
Equipo = Literal[tuple(EQUIPOS)]
Transporte = Literal[tuple(TRANSPORTES + ["Otro"])]


class FichaReciclador(BaseModel):
    """Una fila del Registro Municipal de Recicladores. None = la persona no lo dijo."""

    nombre_completo: str | None = Field(description="Nombres y apellidos, con mayúscula inicial")
    dni: str | None = Field(description="Exactamente 8 dígitos, sin espacios ni puntos")
    edad: int | None = Field(description="Edad en años")
    distrito_vivienda: str | None = Field(description="Distrito donde vive")
    sector_vivienda: str | None = Field(description="Sector, barrio o asentamiento donde vive")
    materiales: list[Material] = Field(description="Materiales que recoge")
    medio_transporte: list[Transporte] = Field(description="Con qué recoge y mueve los materiales")
    pertenece_asociacion: bool | None = Field(description="True si dice pertenecer a una asociación")
    nombre_asociacion: str | None = Field(description="Nombre de la asociación, si lo dice")
    equipo_proteccion: list[Equipo] = Field(description="Equipo de protección que dice usar")
    campos_dudosos: list[str] = Field(
        description="Nombres de los campos que no quedaron claros y el registrador debe confirmar"
    )
    observaciones: str = Field(description="Una o dos frases con lo importante que no cabe en otros campos")


INSTRUCCIONES = f"""Eres el asistente del Registro Municipal de Recicladores de una municipalidad de Trujillo, Perú.
Recibes las preguntas del registro y las respuestas de un reciclador, transcritas de su voz con Whisper.
Llena la ficha solo con lo que la persona dijo. No inventes datos: si algo no se dijo, déjalo en null o en una lista vacía.
La transcripción puede tener errores: corrige nombres de lugares de Trujillo ({", ".join(DISTRITOS_TRUJILLO)})
y convierte números dichos en palabras a cifras («cuarenta y dos» → 42).
Si un dato parece mal transcrito (por ejemplo, un DNI que no tiene 8 dígitos), anótalo en campos_dudosos.
Escribe las observaciones en español sencillo."""


def armar_mensaje(respuestas: dict[str, str]) -> str:
    """Junta cada pregunta con su respuesta en un solo texto para el modelo."""
    lineas = []
    for pregunta in PREGUNTAS:
        respuesta = respuestas.get(pregunta["clave"], "").strip() or "(sin respuesta)"
        lineas.append(f"Pregunta: {pregunta['texto']}\nRespuesta: {respuesta}")
    return "\n\n".join(lineas)


# --- 2. Extracción con Gemini ------------------------------------------------
def extraer_con_gemini(respuestas: dict[str, str]) -> tuple[FichaReciclador, dict]:
    """Pide a Gemini la ficha. Devuelve la ficha y el uso de tokens."""
    cliente = genai.Client(
        api_key=leer_ajuste("GEMINI_API_KEY"),
        # Si Gemini no responde en 30 segundos, nos rendimos y usamos las reglas (el demo no se cuelga).
        http_options={"timeout": 30_000, "retry_options": {"attempts": 2}},
    )
    respuesta = cliente.models.generate_content(
        model=GEMINI_MODELO,
        contents=armar_mensaje(respuestas),
        config={
            "system_instruction": INSTRUCCIONES,
            "response_mime_type": "application/json",                 # que responda solo JSON…
            "response_json_schema": FichaReciclador.model_json_schema(),  # …con este molde exacto
            "temperature": 0,                                          # sin creatividad: mismos datos, misma ficha
        },
    )
    # Validamos con Pydantic: si falta un campo o un tipo no calza, lanza ValidationError.
    ficha = FichaReciclador.model_validate_json(respuesta.text)
    uso = {
        "tokens_entrada": respuesta.usage_metadata.prompt_token_count,
        "tokens_salida": respuesta.usage_metadata.candidates_token_count,
    }
    return ficha, uso


# --- 3. Plan B: extracción con reglas -----------------------------------------
NUMEROS = {
    "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "quince": 15,
    "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100,
}
PALABRAS_MATERIAL = {
    "carton": "Cartón", "papel": "Papel", "botella": "Botella PET", "pet": "Botella PET",
    "plastico": "Plástico duro", "fierro": "Fierro / chatarra", "chatarra": "Fierro / chatarra",
    "cobre": "Cobre", "aluminio": "Aluminio", "lata": "Aluminio", "vidrio": "Vidrio",
}
PALABRAS_TRANSPORTE = {
    "saco": "Saco", "costal": "Saco", "carrito": "Carrito", "carreta": "Carretilla",
    "carretilla": "Carretilla", "triciclo": "Triciclo", "mototaxi": "Mototaxi", "moto": "Mototaxi",
    "a pie": "A pie", "caminando": "A pie", "en la mano": "A pie",
}
PALABRAS_EQUIPO = {
    "guante": "Guantes", "mascarilla": "Mascarilla", "chaleco": "Chaleco",
    "bota": "Botas", "uniforme": "Uniforme",
}


def simplificar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar palabras sin errores de acento."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def primer_numero(texto: str) -> float | None:
    """Busca el primer número del texto, escrito en cifras o en palabras («cuarenta y cinco»)."""
    cifra = re.search(r"\d+(?:[.,]\d+)?", texto)
    if cifra:
        return float(cifra.group().replace(",", "."))
    total, encontrado = 0, False
    for palabra in simplificar(texto).split():
        if palabra in NUMEROS:
            total += NUMEROS[palabra]
            encontrado = True
        elif encontrado and palabra != "y":
            break
    return float(total) if encontrado else None



def extraer_con_reglas(respuestas: dict[str, str]) -> FichaReciclador:
    """Llena la ficha sin LLM. Cada respuesta se lee buscando números y palabras clave."""
    r = {clave: respuestas.get(clave, "") for clave in (p["clave"] for p in PREGUNTAS)}

    # Nombre: quitamos frases como «me llamo» o «mi nombre es». «Hombre es» aparece cuando
    # la grabación empieza tarde y se pierde el «mi» (ver README, limitaciones).
    nombre = re.sub(r"(?i)^(me llamo|(mi )?nombre es|hombre es|soy)\s+", "", r["nombre"].strip()).strip(" .")

    # DNI: juntamos todos los dígitos (Whisper a veces los separa con espacios o guiones).
    digitos = "".join(re.findall(r"\d", r["dni"]))
    if not digitos:  # el DNI se dijo en palabras: «cuatro cinco uno…»
        digitos = "".join(str(NUMEROS[p]) for p in simplificar(r["dni"]).split() if NUMEROS.get(p, 99) < 10)

    edad = primer_numero(r["edad"])

    # Vivienda: «En El Porvenir, en Río Seco». El distrito se busca en la lista; el barrio
    # es lo que queda al cortar por comas y por la palabra «en».
    distrito = next((d for d in DISTRITOS_TRUJILLO if simplificar(d) in simplificar(r["vivienda"])), None)
    pedazos = [p.strip() for p in re.split(r"[,;.]|\ben\b", r["vivienda"])]
    pedazos = [re.sub(r"(?i)^(yo\s+)?(vivo\s*)?(por\s+)?(el\s+)?(sector|barrio)?\s*", "", p)
               for p in pedazos if not (distrito and simplificar(distrito) in simplificar(p))]
    sector = ", ".join(p for p in pedazos if p)

    texto_materiales = simplificar(r["materiales"])
    materiales = sorted({m for palabra, m in PALABRAS_MATERIAL.items() if palabra in texto_materiales})

    texto_transporte = simplificar(r["transporte"])
    transporte = [t for p, t in PALABRAS_TRANSPORTE.items() if p in texto_transporte]

    # Asociación: «no» o «ninguna» = no pertenece; si nombra una, sí pertenece.
    texto_asoc = simplificar(r["asociacion"])
    en_asociacion = None
    if texto_asoc:
        en_asociacion = not re.search(r"^no\b|ninguna|\bno pertenezco", texto_asoc)

    texto_epp = simplificar(r["proteccion"])
    # Si dice «mascarilla no», no la contamos.
    equipo = [e for p, e in PALABRAS_EQUIPO.items() if p in texto_epp and f"{p} no" not in texto_epp]

    dudosos = []
    if len(digitos) != 8:
        dudosos.append("dni")
    if distrito is None:
        dudosos.append("distrito_vivienda")

    return FichaReciclador(
        nombre_completo=nombre.title() or None,
        dni=digitos[:8] or None,
        edad=int(edad) if edad else None,
        distrito_vivienda=distrito,
        sector_vivienda=sector.title() or None,
        materiales=materiales,
        medio_transporte=sorted(set(transporte)),
        pertenece_asociacion=en_asociacion,
        nombre_asociacion=None,
        equipo_proteccion=equipo,
        campos_dudosos=dudosos,
        observaciones="Ficha llenada con reglas simples (sin LLM): revise cada campo.",
    )


# --- 4. Función que usa la app ---------------------------------------------------
def extraer_ficha(respuestas: dict[str, str]) -> tuple[FichaReciclador, str, dict]:
    """Intenta con Gemini y, si no se puede, usa las reglas.

    Devuelve (ficha, método usado, uso de tokens).
    """
    if hay_clave_gemini():
        try:
            ficha, uso = extraer_con_gemini(respuestas)
            return ficha, f"Gemini ({GEMINI_MODELO})", uso
        except Exception as error:
            # Cualquier problema (sin internet, clave mala, límite gratuito superado, respuesta lenta
            # o un JSON que no calza con el molde) no debe romper el demo: pasamos a las reglas.
            print(f"Falló Gemini, uso reglas: {error}")
            # Mostramos el motivo en pantalla (el mensaje de error nunca incluye la clave).
            motivo = f"{type(error).__name__}: {str(error)[:120]}"
            return extraer_con_reglas(respuestas), f"Reglas simples (Gemini falló: {motivo})", {}
    return extraer_con_reglas(respuestas), "Reglas simples (sin LLM)", {}


# --- 5. Horario de recojo del vecino ------------------------------------------------
# El vecino dice cuándo puede pasar el reciclador («lunes, miércoles y viernes de 7 a 9») y
# lo convertimos en días y horas que el reciclador ve en la app. Igual que la ficha:
# Gemini con salida estructurada y, si no se puede, reglas simples.
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
Dia = Literal[tuple(DIAS_SEMANA)]


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
