"""De las respuestas habladas a una ficha ordenada (herramienta del curso: sesión 08,
LLMs con salidas estructuradas).

El problema: la gente no responde como un formulario. Dice «trabajo como diez
años ya, desde que cerró la fábrica, salgo de lunes a sábado». La ficha necesita
anios_reciclando = 10 y dias_por_semana = 6.

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

from nucleo.config import GEMINI_MODELO, hay_clave_gemini, leer_ajuste
from nucleo.preguntas import PREGUNTAS

# --- 1. El esquema de la ficha ------------------------------------------------
# Literal[...] limita los valores posibles: el modelo solo puede elegir de esta lista.
Material = Literal[
    "Cartón", "Papel", "Botella PET", "Plástico duro", "Fierro / chatarra",
    "Cobre", "Aluminio", "Vidrio", "Otro",
]
Equipo = Literal["Guantes", "Mascarilla", "Chaleco", "Botas", "Uniforme"]

DISTRITOS_TRUJILLO = [
    "Trujillo", "El Porvenir", "Florencia de Mora", "La Esperanza", "Alto Trujillo",
    "Víctor Larco Herrera", "Huanchaco", "Moche", "Laredo", "Salaverry", "Poroto", "Simbal",
]


class FichaReciclador(BaseModel):
    """Una fila del Registro Municipal de Recicladores. None = la persona no lo dijo."""

    nombre_completo: str | None = Field(description="Nombres y apellidos, con mayúscula inicial")
    dni: str | None = Field(description="Exactamente 8 dígitos, sin espacios ni puntos")
    edad: int | None = Field(description="Edad en años")
    distrito_vivienda: str | None = Field(description="Distrito donde vive")
    sector_vivienda: str | None = Field(description="Sector, barrio o asentamiento donde vive")
    zonas_trabajo: str | None = Field(description="Zonas o calles por donde recicla")
    dias_por_semana: int | None = Field(description="Días que recicla por semana (1 a 7)")
    anios_reciclando: int | None = Field(description="Años que lleva reciclando")
    materiales: list[Material] = Field(description="Materiales que recoge")
    kg_semana: float | None = Field(description="Kilos que junta por semana, aproximado")
    vende_a: str | None = Field(description="A quién vende: acopiador, chatarrero, asociación, empresa…")
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


def numero_cerca_de(texto: str, palabras: list[str]) -> float | None:
    """Número que aparece justo antes de alguna palabra (ej.: «5 días» → 5)."""
    for palabra in palabras:
        coincidencia = re.search(rf"(\d+)\s*{palabra}", simplificar(texto))
        if coincidencia:
            return float(coincidencia.group(1))
    return None


def extraer_con_reglas(respuestas: dict[str, str]) -> FichaReciclador:
    """Llena la ficha sin LLM. Cada respuesta se lee buscando números y palabras clave."""
    r = {clave: respuestas.get(clave, "") for clave in (p["clave"] for p in PREGUNTAS)}

    # Nombre: quitamos frases como «me llamo» o «mi nombre es».
    nombre = re.sub(r"(?i)^(me llamo|mi nombre es|soy)\s+", "", r["nombre"].strip()).strip(" .")

    # DNI: juntamos todos los dígitos (Whisper a veces los separa con espacios).
    digitos = "".join(re.findall(r"\d", r["dni"]))
    if not digitos:  # el DNI se dijo en palabras: «cuatro cinco uno…»
        digitos = "".join(str(NUMEROS[p]) for p in simplificar(r["dni"]).split() if NUMEROS.get(p, 99) < 10)

    edad = primer_numero(r["edad"])
    distrito = next(
        (d for d in DISTRITOS_TRUJILLO if simplificar(d) in simplificar(r["vivienda"])), None
    )
    sector = re.search(r"(?i)sector\s+([\wáéíóúñ ]+)", r["vivienda"])

    texto_materiales = simplificar(r["materiales"])
    materiales = sorted({m for palabra, m in PALABRAS_MATERIAL.items() if palabra in texto_materiales})
    kg = numero_cerca_de(r["materiales"], ["kilos", "kg", "kilo"]) or primer_numero(r["materiales"])

    texto_venta = simplificar(r["venta"])
    en_asociacion = None
    if "asociacion" in texto_venta:
        en_asociacion = not re.search(r"\bno\b|ninguna", texto_venta)

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
        sector_vivienda=sector.group(1).strip().title() if sector else None,
        zonas_trabajo=r["trabajo"] or None,
        dias_por_semana=int(d) if (d := numero_cerca_de(r["trabajo"], ["dias", "dia"])) else None,
        anios_reciclando=int(a) if (a := numero_cerca_de(r["trabajo"], ["anos", "ano"])) else None,
        materiales=materiales,
        kg_semana=kg,
        vende_a=r["venta"] or None,
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
    return extraer_con_reglas(respuestas), "Reglas simples (sin LLM)", {}
