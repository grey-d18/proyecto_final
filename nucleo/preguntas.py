"""Las preguntas del registro por voz.

En lugar de llenar y firmar un formulario en papel, el reciclador ESCUCHA cada
pregunta (con voz grabada, porque puede no saber leer) y responde hablando.

¿Qué se pide y por qué?
    Solo lo que exige el art. 34 b) del Reglamento de la Ley 29419 (D. S. 005-2010-MINAM,
    modificado por el D. S. 001-2022-MINAM) para el registro de recicladores: nombres, DNI,
    fecha de nacimiento, edad, género, dirección, teléfono, correo y cargo en la
    organización. Además, lo que la municipalidad usa para organizar la recolección:
    materiales, zona, días y horario, y con qué trabaja (vehículo y equipo de protección).

    - La edad no se pregunta: se calcula con la fecha de nacimiento.
    - El correo puede quedar vacío y el cargo es «socio» si no se dice otro.
    - Estado civil, estudios, ingresos y seguro son opcionales: NO se preguntan.

Son 6 preguntas abiertas (antes eran 8). Como la gente responde con rodeos y a veces
dice varios datos juntos, después de cada respuesta la IA revisa qué campos ya están
llenos (ver nucleo/entrevista.py):
    - si una respuesta ya llenó los campos de una pregunta siguiente, esa se salta;
    - si al final falta un dato, se repregunta UNA sola vez (REPREGUNTAS);
    - si sigue vacío, queda «por completar». Nunca se pregunta en bucle.

Cada pregunta es un diccionario con:
    clave    -> nombre interno (para guardar la respuesta y para el audio)
    texto    -> lo que se muestra en pantalla
    voz      -> lo que dice el audio, si es distinto del texto
    ejemplo  -> una respuesta de ejemplo, en letra pequeña
    campos   -> qué campos de la ficha llena (si ya están llenos, la pregunta se salta)
    segundos -> cuánto puede durar la respuesta hablada (si no, SEGUNDOS_POR_DEFECTO)

Los audios están en web/audios/<clave>.mp3 y se generan con scripts/generar_voces.py
(voz neuronal es-PE-CamilaNeural, acento peruano).
"""

SEGUNDOS_POR_DEFECTO = 30

PREGUNTAS = [
    {
        "clave": "dni",
        "texto": "¿Cuál es su número de DNI?",
        "voz": "¿Cuál es su número de DNI? Dígalo despacio, número por número.",
        "ejemplo": "Cuatro cinco siete ocho, uno dos tres cuatro",
        "campos": ["dni"],
    },
    {
        "clave": "nombre_nacimiento",
        "segundos": 40,
        "texto": "Dígame su nombre completo, su fecha de nacimiento y si es mujer u hombre.",
        "ejemplo": "Rosa Elena Quispe Ramos, nací el 3 de mayo de 1978, soy mujer",
        # El género se pide aquí (lo dice la persona; nunca se adivina por el nombre). No está en
        # «campos»: si el nombre y la fecha ya se dijeron antes, esta pregunta se salta igual y el
        # género, si falta, se repregunta al final (re_genero).
        "campos": ["nombre_completo", "fecha_nacimiento"],
    },
    {
        "clave": "vivienda_celular",
        "segundos": 50,
        "texto": "¿Dónde vive y cuál es su celular?",
        "ejemplo": "En la calle Los Pinos 245, El Porvenir. Mi celular es 987 654 321",
        "campos": ["direccion", "telefono"],
    },
    {
        "clave": "trabajo",
        "segundos": 50,
        "texto": "¿Qué materiales recoge, en qué zona y en qué días y horario?",
        "ejemplo": "Cartón y botellas en el centro de Trujillo, de lunes a sábado de 6 a 11 de la mañana",
        "campos": ["materiales", "zona_trabajo", "dias_trabajo", "horario"],
    },
    {
        "clave": "equipo",
        "segundos": 50,
        "texto": "¿Qué usa para recoger su material? Por ejemplo: un carrito, un triciclo o un saco.",
        "ejemplo": "Con mi triciclo y unos sacos",
        "campos": ["equipo"],
    },
    {
        # Estar en una asociación es un requisito para formalizarse: la municipalidad
        # necesita saber cuántos no lo están. No es obligatorio: si no responde, no se repregunta.
        "clave": "asociacion",
        "texto": "¿Está en alguna asociación de recicladores? Si es así, ¿en cuál?",
        "ejemplo": "Sí, en la asociación Manos Unidas. O: No, en ninguna",
        "campos": ["asociacion"],
    },
]

# Si al terminar las 6 preguntas un dato obligatorio sigue vacío, se pregunta UNA vez más,
# de forma corta y directa. La clave del campo que falta -> su repregunta.
REPREGUNTAS = {
    "dni": {"clave": "re_dni", "texto": "No entendí bien su DNI. ¿Me lo repite, número por número?",
            "ejemplo": "Cuatro cinco siete ocho, uno dos tres cuatro", "campos": ["dni"]},
    "nombre_completo": {"clave": "re_nombre", "texto": "¿Cuál es su nombre completo?",
                        "ejemplo": "Rosa Elena Quispe Ramos", "campos": ["nombre_completo"]},
    "fecha_nacimiento": {"clave": "re_nacimiento", "texto": "¿Cuál es su fecha de nacimiento? Día, mes y año.",
                         "ejemplo": "3 de mayo de 1978", "campos": ["fecha_nacimiento"]},
    "genero": {"clave": "re_genero", "texto": "Para su ficha, ¿es usted mujer u hombre?",
               "ejemplo": "Mujer", "campos": ["genero"]},
    "direccion": {"clave": "re_direccion", "texto": "¿Cuál es su dirección? Calle, número y distrito.",
                  "ejemplo": "Calle Los Pinos 245, El Porvenir", "campos": ["direccion"], "segundos": 40},
    "telefono": {"clave": "re_celular", "texto": "¿Cuál es su número de celular?",
                 "ejemplo": "987 654 321", "campos": ["telefono"]},
    "materiales": {"clave": "re_materiales", "texto": "¿Qué materiales recoge?",
                   "ejemplo": "Cartón, botellas y chatarra", "campos": ["materiales"]},
    "zona_trabajo": {"clave": "re_zona", "texto": "¿En qué zona o barrio recoge?",
                     "ejemplo": "En el centro de Trujillo", "campos": ["zona_trabajo"]},
    # Días y horario comparten una sola repregunta.
    "dias_trabajo": {"clave": "re_horario", "texto": "¿Qué días y en qué horario trabaja?",
                     "ejemplo": "De lunes a sábado, de 6 a 11 de la mañana", "campos": ["dias_trabajo", "horario"]},
    "horario": {"clave": "re_horario", "texto": "¿Qué días y en qué horario trabaja?",
                "ejemplo": "De lunes a sábado, de 6 a 11 de la mañana", "campos": ["dias_trabajo", "horario"]},
    "equipo": {"clave": "re_equipo", "texto": "¿Qué usa para recoger su material? Un carrito, un triciclo, un saco…",
               "ejemplo": "Con un carrito", "campos": ["equipo"]},
}

# Todas las preguntas posibles, por clave (las 6 del guion y las repreguntas).
TODAS = {p["clave"]: p for p in PREGUNTAS} | {r["clave"]: r for r in REPREGUNTAS.values()}

# Otros mensajes que la app dice en voz alta (mismo formato: clave y lo que se dice).
AVISOS = {
    "horario_recojo": "¿Qué días y a qué hora puede pasar el reciclador a recoger? Por ejemplo: lunes, miércoles y viernes, de siete a nueve de la mañana.",
    "inicio": "¿Quién es usted? Toque «Soy reciclador», «Soy vecino» o «Soy acopiador».",
    "aviso_recojo": "Recuerde que tiene un máximo de tres días para hacer su recojo. "
                    "Si no, se asignará a otro reciclador de la zona.",
    # El resumen de la ficha: Camila dice el inicio y el final (frases fijas); los datos
    # personales los lee la voz del propio celular, para que no salgan del teléfono.
    "resumen_inicio": "Escuche su ficha y revise que sus datos estén bien.",
    "resumen_final": "Si todo está bien, toque el micrófono y diga: sí, acepto. "
                     "Es su declaración jurada de que sus datos son verdaderos.",
    "bienvenida_registro": "Le voy a hacer seis preguntas para inscribirle en el registro de recicladores. "
                           "Su voz se graba solo para llenar su ficha. Toque el micrófono y responda hablando.",
}
