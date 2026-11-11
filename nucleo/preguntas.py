"""Las preguntas del registro por voz.

En lugar de llenar y firmar un formulario en papel, el reciclador ESCUCHA cada
pregunta (con voz grabada, porque puede no saber leer) y responde grabándose.
Una pregunta por pantalla, y son pocas (8): solo lo que pide la ley o lo que
usa la municipalidad en su panel.

¿De dónde salen las preguntas?
    La Ley 29419 (Ley que regula la actividad de los recicladores) y su reglamento
    (D. S. 005-2010-MINAM) piden que las municipalidades lleven un registro de
    recicladores y de sus asociaciones, y que trabajen con equipo de protección.
    Las preguntas recogen esos datos en lenguaje cotidiano.

Cada pregunta es un diccionario con:
    clave    -> nombre interno (se usa para guardar la respuesta y para el audio)
    texto    -> lo que se muestra en pantalla
    voz      -> lo que dice el audio, escrito como se pronuncia (si es distinto del texto)
    ejemplo  -> una respuesta de ejemplo, en letra pequeña debajo de la pregunta

Los audios están en web/audios/<clave>.mp3 y se generan con
scripts/generar_voces.py (voz neuronal es-PE-CamilaNeural, acento peruano).
"""

# Cuánto puede durar cada respuesta hablada, en segundos. Las preguntas que admiten respuestas
# largas (dirección, materiales, transporte, asociación) llevan su propio "segundos".
SEGUNDOS_POR_DEFECTO = 30

PREGUNTAS = [
    {
        "clave": "nombre",
        "texto": "¿Cuál es su nombre completo?",
        "ejemplo": "Me llamo Rosa Elena Quispe Ramos",
    },
    {
        "clave": "dni",
        "texto": "¿Cuál es su número de DNI?",
        "voz": "¿Cuál es su número de DNI? Dígalo despacio, número por número.",
        "ejemplo": "Mi DNI es cero cero cuatro cinco, siete ocho, uno dos",
    },
    {
        "clave": "edad",
        "texto": "¿Cuántos años tiene?",
        "ejemplo": "Tengo 47 años",
    },
    {
        "clave": "vivienda",
        "segundos": 40,
        "texto": "¿Dónde vive? Dígame su distrito y su barrio.",
        "ejemplo": "En El Porvenir, en Río Seco",
    },
    {
        "clave": "materiales",
        "segundos": 50,
        "texto": "¿Qué materiales recoge?",
        "ejemplo": "Cartón, botellas y fierro; a veces latas",
    },
    {
        "clave": "transporte",
        "segundos": 50,
        "texto": "¿Con qué recoge y mueve los materiales? Por ejemplo: un saco, un carrito o un triciclo.",
        "ejemplo": "Con un triciclo",
    },
    {
        "clave": "asociacion",
        "segundos": 50,
        "texto": "¿Pertenece a alguna asociación de recicladores? Por favor, indique cuál.",
        "ejemplo": "No, a ninguna",
    },
    {
        "clave": "proteccion",
        "texto": "¿Usa mascarilla o guantes para reciclar?",
        "ejemplo": "Guantes sí, mascarilla no",
    },
]

# Otros mensajes que la app dice en voz alta (mismo formato: clave y lo que se dice).
AVISOS = {
    "inicio": "¿Quién es usted? Toque «Soy reciclador», «Soy vecino» o «Soy acopiador».",
    "aviso_recojo": "Recuerde que tiene un máximo de tres días para hacer su recojo. "
                    "Si no, se asignará a otro reciclador de la zona.",
    "bienvenida_registro": "Le voy a hacer ocho preguntas para inscribirle en el registro "
                           "de recicladores. Apriete el micrófono y responda hablando.",
}
