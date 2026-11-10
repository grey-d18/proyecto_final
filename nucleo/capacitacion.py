"""Contenido de la sección de capacitación.

Está escrito como datos (listas y diccionarios) y no dentro de la página, para que
se pueda corregir o ampliar el contenido sin tocar el código de la interfaz.
"""

# Módulos de capacitación: título, ícono y puntos clave.
MODULOS = [
    {
        "titulo": "Cuídate primero",
        "icono": "🧤",
        "puntos": [
            "Usa guantes gruesos: en la basura hay vidrio roto, jeringas y latas con filo.",
            "Usa mascarilla al abrir bolsas: evita respirar polvo y hongos.",
            "Ponte la vacuna contra el tétanos y la hepatitis B : pregunta en tu centro de salud.",
            "Lávate las manos antes de comer y al terminar la jornada.",
            "Usa chaleco con cinta reflectiva si trabajas de noche o cerca de pistas.",
        ],
    },
    {
        "titulo": "Separa y gana más",
        "icono": "♻️",
        "puntos": [
            "El material limpio y seco se paga mejor: el cartón mojado pesa más, pero el acopiador lo castiga.",
            "Separa por tipo: botella PET aparte del plástico duro, cobre aparte del fierro.",
            "Aplasta botellas y latas: entra más en el saco y pagas menos flete.",
            "Junta varios días antes de vender si tienes dónde guardar: vender al por mayor da mejor precio.",
        ],
    },
    {
        "titulo": "Tus derechos",
        "icono": "📜",
        "puntos": [
            "La Ley 29419 reconoce al reciclador como trabajador y pide a las municipalidades formalizarlo.",
            "Inscribirte en el Registro Municipal te permite entrar a los programas de segregación en la fuente.",
            "Organizarte en una asociación te ayuda a negociar precios y a conseguir equipo.",
        ],
    },
]

# Cómo reconocer cada material.
MATERIALES = [
    {"material": "Botella (PET)", "como_reconocerlo": "Botellas transparentes de agua y gaseosa. Símbolo ♳ (número 1).",
     "consejo": "Sin tapa y aplastada."},
    {"material": "Plástico duro", "como_reconocerlo": "Baldes, tinas, jabas, botellas de lejía. Símbolos ♴ (2) y ♷ (5).",
     "consejo": "Separado del PET: se paga distinto."},
    {"material": "Cartón", "como_reconocerlo": "Cajas de tiendas y mercados.",
     "consejo": "Seco y doblado. El cartón mojado se rechaza."},
    {"material": "Papel", "como_reconocerlo": "Hojas de oficina, cuadernos, periódico.",
     "consejo": "El papel blanco se paga mejor que el periódico."},
    {"material": "Fierro (chatarra)", "como_reconocerlo": "Se pega al imán. Varillas, ollas viejas, partes de autos.",
     "consejo": "Pesa mucho y se paga poco: conviene juntar bastante."},
    {"material": "Aluminio", "como_reconocerlo": "No se pega al imán. Latas de gaseosa, marcos de ventana.",
     "consejo": "Vale unas 10 veces más que el fierro."},
    {"material": "Cobre", "como_reconocerlo": "Color rojizo. Está dentro de cables y motores.",
     "consejo": "Es el material más caro. Pela el cable (sin quemarlo: el humo es tóxico)."},
]

# Preguntas del quiz: pregunta, opciones y la respuesta correcta.
QUIZ = [
    {"pregunta": "¿Cómo sabes si un metal es fierro y no aluminio?",
     "opciones": ["Por el color", "Porque se pega al imán", "Porque pesa poco"],
     "correcta": "Porque se pega al imán"},
    {"pregunta": "¿Qué cartón se paga mejor?",
     "opciones": ["El mojado, porque pesa más", "El seco y doblado", "Da igual"],
     "correcta": "El seco y doblado"},
    {"pregunta": "Para sacar el cobre de un cable, lo mejor es…",
     "opciones": ["Quemarlo", "Pelarlo", "Venderlo con todo y forro"],
     "correcta": "Pelarlo"},
]
