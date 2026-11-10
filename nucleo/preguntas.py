"""Las preguntas del registro por voz.

En lugar de llenar y firmar un formulario en papel, el reciclador escucha (o lee)
cada pregunta y responde grabándose. Cada pregunta alimenta uno o más campos de la
ficha del Registro Municipal de Recicladores.

¿De dónde salen las preguntas?
    La Ley 29419 (Ley que regula la actividad de los recicladores) y su reglamento
    (D. S. 005-2010-MINAM) piden que las municipalidades lleven un registro de
    recicladores y de sus asociaciones, y que estos trabajen con equipo de
    protección. Las preguntas recogen esos datos en lenguaje cotidiano.

Cada pregunta es un diccionario con:
    clave    -> nombre interno (se usa para guardar la respuesta)
    texto    -> lo que se le pregunta a la persona
    ayuda    -> un ejemplo de respuesta, para que sepa qué decir
"""

PREGUNTAS = [
    {
        "clave": "nombre",
        "texto": "¿Cuál es su nombre completo?",
        "ayuda": "Por ejemplo: «Me llamo Rosa Elena Quispe Ramos».",
    },
    {
        "clave": "dni",
        "texto": "¿Cuál es su número de DNI?",
        "ayuda": "Diga los 8 números despacio. Para el demo use un DNI inventado.",
    },
    {
        "clave": "edad",
        "texto": "¿Cuántos años tiene?",
        "ayuda": "Por ejemplo: «Tengo 45 años».",
    },
    {
        "clave": "vivienda",
        "texto": "¿En qué distrito y en qué sector vive?",
        "ayuda": "Por ejemplo: «Vivo en El Porvenir, en el sector Río Seco».",
    },
    {
        "clave": "trabajo",
        "texto": "¿Por qué zonas recicla, cuántos días a la semana y desde hace cuántos años?",
        "ayuda": "Por ejemplo: «Recorro el centro de Trujillo, cinco días, hace ocho años».",
    },
    {
        "clave": "materiales",
        "texto": "¿Qué materiales recoge y cuántos kilos junta más o menos a la semana?",
        "ayuda": "Por ejemplo: «Cartón, botellas y fierro, como 150 kilos a la semana».",
    },
    {
        "clave": "venta",
        "texto": "¿A quién le vende lo que recoge? ¿Pertenece a alguna asociación de recicladores?",
        "ayuda": "Por ejemplo: «Le vendo a un acopiador del barrio. No estoy en ninguna asociación».",
    },
    {
        "clave": "proteccion",
        "texto": "¿Usa guantes, mascarilla u otro equipo de protección cuando trabaja?",
        "ayuda": "Por ejemplo: «Uso guantes, pero mascarilla no».",
    },
]
