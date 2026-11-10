"""Ubicaciones: centro de cada distrito, «usar mi ubicación» y «escribir mi dirección».

Dos formas de ubicar un local o un pedido, ambas gratis:

1. Usar mi ubicación (GPS del celular o ubicación de la laptop)
   Usamos streamlit-js-eval, que ejecuta en el navegador la función estándar
   navigator.geolocation. El navegador pregunta «¿Permitir que este sitio conozca tu
   ubicación?». Solo sirve si la persona está EN el lugar en ese momento.

2. Escribir mi dirección
   Le preguntamos a Nominatim, el buscador gratuito de direcciones de OpenStreetMap,
   dónde queda esa dirección. Ojo: la dirección escrita viaja a OpenStreetMap.
   En asentamientos humanos muchas direcciones no existen en el mapa: en ese caso
   usamos el centro del distrito como aproximación.
"""
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

# Centro aproximado de cada distrito de la provincia de Trujillo (latitud, longitud).
CENTROS = {
    "Trujillo": (-8.112, -79.029), "El Porvenir": (-8.079, -79.001),
    "Florencia de Mora": (-8.080, -79.023), "La Esperanza": (-8.077, -79.045),
    "Alto Trujillo": (-8.061, -78.990), "Víctor Larco Herrera": (-8.135, -79.048),
    "Huanchaco": (-8.079, -79.120), "Moche": (-8.171, -79.009), "Laredo": (-8.089, -78.960),
    "Salaverry": (-8.223, -78.977), "Poroto": (-8.012, -78.770), "Simbal": (-7.976, -78.814),
}


@st.cache_data(show_spinner="Buscando la dirección…")  # la misma dirección no se busca dos veces
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


def elegir_ubicacion(clave: str, distrito: str, aviso_gps: str) -> tuple[str, float, float] | None:
    """Muestra los dos botones y devuelve (dirección, lat, lon) cuando la ubicación ya está lista.

    clave: nombre único para esta pantalla (Streamlit lo necesita para recordar el estado).
    """
    modo = st.radio("¿Cómo ubicamos el lugar?", ["📍 Usar mi ubicación", "✏️ Escribir mi dirección"],
                    key=f"modo_{clave}", horizontal=True)

    if modo.startswith("📍"):
        st.info(aviso_gps)
        if st.toggle("Compartir mi ubicación ahora", key=f"gps_{clave}"):
            datos = get_geolocation(component_key=f"geo_{clave}")  # devuelve None hasta que el navegador responde
            if datos and "coords" in datos:
                lat, lon = datos["coords"]["latitude"], datos["coords"]["longitude"]
                st.success(f"Ubicación lista ({lat:.4f}, {lon:.4f})")
                return "Ubicación del GPS", lat, lon
            if datos and "error" in datos:
                st.error("El navegador no dio la ubicación. Revise el permiso o escriba la dirección.")
            else:
                st.caption("Esperando que el navegador comparta la ubicación…")
        return None

    direccion = st.text_input("Dirección o referencia", key=f"dir_{clave}",
                              placeholder="Av. Pumacahua 1450")
    if not direccion:
        return None
    punto = buscar_direccion(direccion, distrito)
    if punto:
        st.success("Encontramos la dirección en el mapa.")
        return direccion, *punto
    st.warning("No encontramos esa dirección en el mapa. Usaremos el centro del distrito.")
    return direccion, *CENTROS.get(distrito, CENTROS["Trujillo"])
