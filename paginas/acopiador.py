"""Acopiador: ubica su local y publica sus precios del día.

Con esos precios se arma la tabla de «Mi ruta» que ven los recicladores: así pueden
comparar dónde les pagan mejor antes de caminar con su carga.
"""
import streamlit as st

from nucleo.base_datos import (actualizar_ubicacion_acopio, guardar_acopio, guardar_precios, leer_acopios,
                               precios_de_hoy)
from nucleo.catalogos import DISTRITOS_TRUJILLO, MATERIALES
from nucleo.interfaz import elegir_ubicacion, volver

AVISO_LOCAL = "Usted tiene que estar en su local para usar esta opción."
NUEVO = "➕ Mi local no está en la lista"

volver("paginas/inicio.py")
st.title("🏪 Acopiador")

# --- 1. ¿Cuál es su local? ----------------------------------------------------------------------
acopios = leer_acopios()
nombres = dict(zip(acopios["nombre"] + " · " + acopios["distrito"], acopios["id"]))
elegido = st.selectbox("Su local", [NUEVO] + list(nombres), index=1 if nombres else 0)

if elegido == NUEVO:
    st.subheader("Registrar mi local")
    nombre = st.text_input("Nombre del local", placeholder="Reciclajes Doña Rosa")
    distrito = st.selectbox("Distrito", DISTRITOS_TRUJILLO, index=DISTRITOS_TRUJILLO.index("El Porvenir"))
    ubicacion = elegir_ubicacion("acopio_nuevo", distrito, AVISO_LOCAL)
    if st.button("Guardar mi local", type="primary", width="stretch"):
        if not nombre or ubicacion is None:
            st.error("Falta el nombre del local o la ubicación.")
        else:
            guardar_acopio(nombre, distrito, *ubicacion)
            st.success("Local guardado. Ahora elíjalo en la lista para poner sus precios.")
            st.rerun()
    st.stop()

acopio_id = nombres[elegido]
acopio = acopios[acopios["id"] == acopio_id].iloc[0]
st.caption(f"📍 {acopio['direccion']} · {acopio['distrito']}")
with st.expander("Cambiar la ubicación de mi local"):
    ubicacion = elegir_ubicacion(f"acopio_{acopio_id}", acopio["distrito"], AVISO_LOCAL)
    if ubicacion and st.button("Guardar ubicación"):
        actualizar_ubicacion_acopio(acopio_id, *ubicacion)
        st.success("Ubicación actualizada.")

# --- 2. Precios de hoy ---------------------------------------------------------------------------
st.subheader("Mis precios de hoy (S/ por kilo)")
hoy = precios_de_hoy()
mios = hoy[hoy["acopio_id"] == acopio_id].sort_values("fecha_hora").groupby("material").last()
with st.form("precios"):
    st.caption("Deje en 0 los materiales que no compra.")
    columnas = st.columns(2)
    nuevos = {}
    for i, material in enumerate(MATERIALES):
        actual = float(mios["precio_soles_kg"].get(material, 0.0)) if not mios.empty else 0.0
        nuevos[material] = columnas[i % 2].number_input(material, min_value=0.0, max_value=100.0,
                                                        value=actual, step=0.05, format="%.2f")
    if st.form_submit_button("Publicar precios", type="primary", width="stretch"):
        guardar_precios(acopio_id, nuevos)
        st.success("Precios publicados. Los recicladores ya los ven en «Mi ruta».")
