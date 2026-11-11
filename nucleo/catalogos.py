"""Las listas fijas que usa toda la app: distritos, materiales, transporte y equipo.

Viven en UN solo lugar para que el registro, el acopiador, la ficha de la IA y los
datos sintéticos usen exactamente los mismos nombres. Si agregas un material, se
agrega en todas partes a la vez.
"""

DISTRITOS_TRUJILLO = [
    "Trujillo", "El Porvenir", "Florencia de Mora", "La Esperanza", "Alto Trujillo",
    "Víctor Larco Herrera", "Huanchaco", "Moche", "Laredo", "Salaverry", "Poroto", "Simbal",
]

MATERIALES = ["Cartón", "Papel", "Botella PET", "Plástico duro", "Fierro / chatarra", "Cobre", "Aluminio", "Vidrio", "Tetrapak"]

# Con qué recoge y mueve los materiales (reemplaza a «kilos por semana»: casi nadie lleva
# la cuenta de sus kilos, pero todos saben si usan saco, carrito o triciclo).
TRANSPORTES = ["Saco", "Carrito", "Carretilla", "Triciclo", "Mototaxi", "Motofurgón", "A pie"]

EQUIPOS = ["Guantes", "Mascarilla", "Chaleco", "Botas", "Uniforme"]
