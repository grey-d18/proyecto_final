"""Ubicaciones: centro de cada distrito y «escribir mi dirección».

Dos formas de ubicar un local o un pedido, ambas gratis:

1. Usar mi ubicación (GPS del celular o ubicación de la laptop): la pide el navegador
   con la función estándar navigator.geolocation (ver la interfaz). Solo sirve si la
   persona está EN el lugar en ese momento.

2. Escribir mi dirección (este archivo)
   Le preguntamos a Nominatim, el buscador gratuito de direcciones de OpenStreetMap,
   dónde queda esa dirección. Ojo: la dirección escrita viaja a OpenStreetMap.
   En asentamientos humanos muchas direcciones no existen en el mapa: en ese caso
   usamos el centro del distrito como aproximación.
"""
from functools import cache

import requests

# Centro aproximado de cada distrito de la provincia de Trujillo (latitud, longitud).
CENTROS = {
    "Trujillo": (-8.112, -79.029), "El Porvenir": (-8.079, -79.001),
    "Florencia de Mora": (-8.080, -79.023), "La Esperanza": (-8.077, -79.045),
    "Alto Trujillo": (-8.061, -78.990), "Víctor Larco Herrera": (-8.135, -79.048),
    "Huanchaco": (-8.079, -79.120), "Moche": (-8.171, -79.009), "Laredo": (-8.089, -78.960),
    "Salaverry": (-8.223, -78.977), "Poroto": (-8.012, -78.770), "Simbal": (-7.976, -78.814),
}


@cache  # la misma dirección no se busca dos veces
def buscar_direccion(direccion: str, distrito: str) -> tuple[float, float] | None:
    """Convierte una dirección escrita en coordenadas con Nominatim (OpenStreetMap)."""
    try:
        respuesta = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{direccion}, {distrito}, Trujillo, La Libertad, Perú",
                    "format": "json", "limit": 1, "countrycodes": "pe"},
            # Nominatim pide identificar la app; usamos un nombre genérico, sin datos personales.
            headers={"User-Agent": "ReciclaVoz-demo/1.0"},
            timeout=10,
        )
        resultados = respuesta.json()
    except Exception:
        return None
    if not resultados:
        return None
    return float(resultados[0]["lat"]), float(resultados[0]["lon"])
