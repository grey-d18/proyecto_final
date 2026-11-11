"""Qué preguntar después: la entrevista se adapta a lo que la persona ya dijo.

Después de cada respuesta, la IA llena la ficha con TODO lo dicho hasta ahí
(nucleo/extraccion.py) y esta función decide la siguiente pregunta:

    1. Las 5 preguntas del guion, en orden. Si una respuesta anterior ya llenó todos los
       campos de una pregunta (por ejemplo, al dar el DNI dijo también su nombre y su fecha
       de nacimiento), esa pregunta se SALTA.
    2. Cuando se acaba el guion, cada dato obligatorio que falte se repregunta UNA sola vez.
    3. Si después de repreguntar sigue vacío, queda «por completar» y la entrevista termina.

Nunca hay bucle: cada pregunta (del guion o repregunta) se hace como máximo una vez, así
que la entrevista tiene como máximo 5 + 10 preguntas (si no se responde nada), y lo normal
es entre 5 y 7.
"""
from nucleo.extraccion import FichaReciclador, campo_vacio, extraer_ficha
from nucleo.preguntas import PREGUNTAS, REPREGUNTAS, SEGUNDOS_POR_DEFECTO


def siguiente_pregunta(ficha: FichaReciclador, hechas: list[str]) -> dict | None:
    """La próxima pregunta, o None si ya no hay nada que preguntar.

    hechas: las claves de las preguntas que ya se hicieron (del guion y repreguntas).
    """
    for pregunta in PREGUNTAS:
        if pregunta["clave"] in hechas:
            continue
        if any(campo_vacio(ficha, campo) for campo in pregunta["campos"]):
            return pregunta
        # si todos sus campos ya están llenos, la pregunta se salta
    for campo in ficha.faltantes:
        repregunta = REPREGUNTAS.get(campo)
        if repregunta and repregunta["clave"] not in hechas:
            return repregunta
    return None


def avanzar(respuestas: dict[str, str], hechas: list[str]) -> dict:
    """Llena la ficha con lo dicho hasta ahora y dice qué preguntar después.

    Devuelve un diccionario con la ficha, el método (Gemini o reglas), la siguiente
    pregunta (o None) y, si ya terminó, la lista de datos «por completar».
    """
    ficha, metodo, _uso = extraer_ficha(respuestas)
    siguiente = siguiente_pregunta(ficha, hechas)
    # Las del guion que no se hicieron y ya quedaron atrás: se saltaron porque sus datos ya estaban.
    hasta = PREGUNTAS.index(siguiente) if siguiente in PREGUNTAS else len(PREGUNTAS)
    saltadas = [p["clave"] for p in PREGUNTAS[:hasta] if p["clave"] not in hechas]
    if siguiente is None:
        ficha.por_completar = list(ficha.faltantes)
    return {
        "ficha": ficha,
        "metodo": metodo,
        "siguiente": None if siguiente is None else {
            "clave": siguiente["clave"], "texto": siguiente["texto"], "ejemplo": siguiente["ejemplo"],
            "segundos": siguiente.get("segundos", SEGUNDOS_POR_DEFECTO),
            "repregunta": siguiente not in PREGUNTAS,
        },
        "saltadas": saltadas,
    }
