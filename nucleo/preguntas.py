"""Las preguntas del registro por voz.

En lugar de llenar y firmar un formulario en papel, el reciclador ESCUCHA cada
pregunta (con voz grabada, porque puede no saber leer) y responde grabándose.
Una pregunta por pantalla, y cada pregunta pide un solo dato.

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

Los audios están en datos/audios_preguntas/<clave>.wav y se generan con
scripts/clonar_voz.py (voz de la fundadora clonada con Qwen3-TTS).
"""

PREGUNTAS = [
    {
        "clave": "nombre",
        "texto": "¿Cuál es su nombre completo?",
        "ejemplo": "Me llamo Rosa Elena Quispe Ramos",
    },
    {
        "clave": "dni",
        "texto": "¿Cuál es su número de DNI?",
        "voz": "¿Cuál es su número de de ene i? Dígalo despacio, número por número.",
        "ejemplo": "Cero cero cuatro cinco, siete ocho, uno dos",
    },
    {
        "clave": "edad",
        "texto": "¿Cuántos años tiene?",
        "ejemplo": "Tengo 47 años",
    },
    {
        "clave": "distrito",
        "texto": "¿En qué distrito vive?",
        "ejemplo": "En El Porvenir",
    },
    {
        "clave": "sector",
        "texto": "¿En qué sector o barrio vive?",
        "ejemplo": "En Río Seco, cerca del mercado",
    },
    {
        "clave": "zonas",
        "texto": "¿Por qué zonas o calles sale a reciclar?",
        "ejemplo": "Por el centro de Trujillo y la avenida España",
    },
    {
        "clave": "dias",
        "texto": "¿Cuántos días a la semana sale a reciclar?",
        "ejemplo": "De lunes a sábado",
    },
    {
        "clave": "anios",
        "texto": "¿Hace cuántos años recicla?",
        "ejemplo": "Ya son como doce años",
    },
    {
        "clave": "materiales",
        "texto": "¿Qué materiales recoge?",
        "ejemplo": "Cartón, botellas y fierro; a veces latas",
    },
    {
        "clave": "transporte",
        "texto": "¿Con qué recoge y mueve los materiales? Por ejemplo: un saco, un carrito o un triciclo.",
        "ejemplo": "Con un triciclo",
    },
    {
        "clave": "asociacion",
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
    "aviso_recojo": "Recuerde que tiene un máximo de tres días para hacer su recojo. "
                    "Si no, se asignará a otro reciclador de la zona.",
    "bienvenida_registro": "Le voy a hacer doce preguntas para inscribirle en el registro "
                           "de recicladores. Apriete el micrófono y responda hablando.",
}
