"""Mi ruta: dónde vender y qué recoger, cerca de la casa del reciclador.

«Cerca» = en el mismo distrito donde vive (el que dio en su registro). No usamos GPS
porque muchos recicladores no tienen celular: la app la puede usar un familiar, la
asociación o el registrador municipal.

1. Tabla de precios: por cada material, el último precio que ingresó un acopiador,
   el menor precio del día y en qué local está.
2. Mapa: 🏪 los locales de acopio y ♻️ los recojos que piden los vecinos.
"""
import folium
import streamlit as st
from streamlit_folium import st_folium

from nucleo.base_datos import leer_acopios, recojos_disponibles, tabla_de_precios
from nucleo.interfaz import barra_reciclador, reciclador_actual
from nucleo.ubicacion import CENTROS

yo = reciclador_actual()
barra_reciclador(yo)
distrito = yo["distrito_vivienda"]
st.title(f"🗺️ Mi ruta · {distrito}")

# --- 1. Precios -----------------------------------------------------------------------
st.subheader("Precios de hoy")
precios = tabla_de_precios(distrito)
if precios.empty:
    st.info("Todavía no hay precios de hoy.")
else:
    st.dataframe(
        precios, hide_index=True, width="stretch",
        column_config={
            "Último precio": st.column_config.NumberColumn(format="S/ %.2f"),
            "Menor precio hoy": st.column_config.NumberColumn(format="S/ %.2f"),
        },
    )
    st.caption("Precios en soles por kilo que ingresan los acopiadores en la app (datos inventados para el demo).")

# --- 2. Mapa ----------------------------------------------------------------------------
st.subheader("Locales de acopio y recojos cerca")
acopios = leer_acopios(distrito)
if acopios.empty:
    acopios = leer_acopios()  # si no hay acopios en su distrito, mostramos todos
recojos = recojos_disponibles(distrito, yo["codigo"])

mapa = folium.Map(location=CENTROS.get(distrito, CENTROS["Trujillo"]), zoom_start=15, tiles="OpenStreetMap")
for _, acopio in acopios.iterrows():
    folium.Marker(
        [acopio["lat"], acopio["lon"]], tooltip=f"🏪 {acopio['nombre']}",
        popup=f"{acopio['nombre']}<br>{acopio['direccion']}",
        icon=folium.Icon(color="blue", icon="shopping-cart", prefix="fa"),
    ).add_to(mapa)
for _, recojo in recojos.iterrows():
    folium.Marker(
        [recojo["lat"], recojo["lon"]], tooltip=f"♻️ {recojo['descripcion']} ({recojo['peso_kg']:.0f} kg)",
        icon=folium.Icon(color="green", icon="recycle", prefix="fa"),
    ).add_to(mapa)
st_folium(mapa, height=420, width="stretch", returned_objects=[])
st.caption("🔵 locales de acopio · 🟢 reciclaje para recoger")
