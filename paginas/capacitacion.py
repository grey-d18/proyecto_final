"""Capacitación y precios: lo que el reciclador gana al inscribirse.

Pestañas:
    1. Buenas prácticas (módulos cortos).
    2. Cómo reconocer cada material.
    3. Precios y dónde vender: precios del trabajo de campo en El Porvenir frente al
       precio de exportación, y un mapa de puntos de acopio (herramienta del curso:
       mapas con Folium, sesión 06).
    4. Quiz: si lo aprueba, queda marcado como "capacitado" en el registro.
"""
import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from nucleo.base_datos import marcar_capacitado
from nucleo.capacitacion import MATERIALES, MODULOS, QUIZ
from nucleo.config import DATOS
from nucleo.interfaz import volver

volver("paginas/reciclador.py" if st.session_state.get("reciclador") else "paginas/inicio.py")
st.title("📚 Capacitación y precios")

pestana_practicas, pestana_materiales, pestana_precios, pestana_quiz = st.tabs(
    ["🧤 Buenas prácticas", "♻️ Materiales", "💰 Precios y dónde vender", "✅ Quiz"]
)

# --- 1. Buenas prácticas -----------------------------------------------------------
with pestana_practicas:
    columnas = st.columns(len(MODULOS))
    for columna, modulo in zip(columnas, MODULOS):
        with columna:
            st.markdown(f"### {modulo['icono']} {modulo['titulo']}")
            for punto in modulo["puntos"]:
                st.markdown(f"- {punto}")

# --- 2. Materiales -------------------------------------------------------------------
with pestana_materiales:
    st.dataframe(
        pd.DataFrame(MATERIALES).rename(columns={
            "material": "Material", "como_reconocerlo": "Cómo reconocerlo", "consejo": "Consejo"}),
        hide_index=True, width="stretch",
    )

# --- 3. Precios y dónde vender -----------------------------------------------------
with pestana_precios:
    # Precios pagados por acopiadores en El Porvenir (tesis, 2026) y precio de exportación
    # del Perú en 2025 (UN Comtrade, valor FOB entre peso), los dos en soles por kilo.
    precios = pd.read_csv(DATOS / "precios_campo_el_porvenir.csv")
    precios["precio_campo"] = (precios["precio_min_soles_kg"] + precios["precio_max_soles_kg"]) / 2

    st.markdown("#### ¿Cuánto pagan por kilo en El Porvenir?")
    tabla = precios[["material", "precio_min_soles_kg", "precio_max_soles_kg",
                     "exportacion_soles_kg", "pct_max_del_precio_exportacion"]].rename(columns={
        "material": "Material", "precio_min_soles_kg": "Mínimo (S/ por kg)",
        "precio_max_soles_kg": "Máximo (S/ por kg)", "exportacion_soles_kg": "Exportación (S/ por kg)",
        "pct_max_del_precio_exportacion": "% del precio de exportación",
    })
    st.dataframe(tabla.round(2), hide_index=True, width="stretch")

    grafico = px.bar(
        precios.melt(id_vars="material", value_vars=["precio_campo", "exportacion_soles_kg"]),
        x="material", y="value", color="variable", barmode="group", log_y=True,
        labels={"material": "", "value": "Soles por kilo (escala logarítmica)", "variable": ""},
        color_discrete_map={"precio_campo": "#2E7D32", "exportacion_soles_kg": "#A5D6A7"},
    )
    grafico.for_each_trace(lambda t: t.update(
        name={"precio_campo": "Lo que pagan en El Porvenir", "exportacion_soles_kg": "Precio de exportación"}[t.name]))
    st.plotly_chart(grafico, width="stretch")
    st.caption(
        "Fuentes: trabajo de campo de la tesis de la autora en dos locales de El Porvenir (2026); "
        "UN Comtrade, exportaciones del Perú en 2025, convertidas con el tipo de cambio de 2025. "
        "El precio de exportación es de material clasificado y embalado: la comparación indica distancia, no margen."
    )

    st.markdown("#### ¿Dónde vender?")
    material = st.selectbox("¿Qué material quiere vender?", sorted(precios["material"]))
    puntos = pd.read_csv(DATOS / "puntos_acopio.csv")
    puntos = puntos[puntos["compra"].str.contains(material, regex=False)]

    mapa = folium.Map(location=[-8.085, -79.015], zoom_start=13, tiles="OpenStreetMap")
    precio_material = precios.set_index("material").loc[material, "precio_campo"]
    for _, punto in puntos.iterrows():
        folium.Marker(
            [punto["lat"], punto["lon"]],
            popup=f"<b>{punto['nombre']}</b><br>{punto['distrito']}<br>{punto['horario']}<br>"
                  f"{material}: S/ {precio_material:.2f} por kg (referencial)",
            tooltip=punto["nombre"], icon=folium.Icon(color="green", icon="recycle", prefix="fa"),
        ).add_to(mapa)
    st_folium(mapa, height=380, width="stretch", returned_objects=[])
    st.caption("Puntos de acopio ilustrativos, con ubicaciones aproximadas: en producción los registraría "
               "la municipalidad. Los precios son referenciales del trabajo de campo.")

# --- 4. Quiz -------------------------------------------------------------------------
with pestana_quiz:
    st.write("Responda las 3 preguntas. Si acierta todas, queda marcado como **capacitado** en el registro.")
    with st.form("quiz"):
        elegidas = [st.radio(item["pregunta"], item["opciones"], index=None) for item in QUIZ]
        codigo = st.text_input("Su código de registro (aparece en la constancia, ej. RMR-2026-0061)",
                               value=st.session_state.get("reciclador", ""))
        enviado = st.form_submit_button("Revisar respuestas", type="primary")

    if enviado:
        aciertos = sum(elegida == item["correcta"] for elegida, item in zip(elegidas, QUIZ))
        st.write(f"Acertó **{aciertos} de {len(QUIZ)}**.")
        for elegida, item in zip(elegidas, QUIZ):
            if elegida != item["correcta"]:
                st.write(f"❌ {item['pregunta']} → **{item['correcta']}**")
        if aciertos == len(QUIZ):
            if codigo and marcar_capacitado(codigo):
                st.success(f"¡Felicitaciones! {codigo.upper()} quedó marcado como capacitado.")
                st.balloons()
            elif codigo:
                st.warning("No encontré ese código en el registro.")
            else:
                st.success("¡Aprobó! Escriba su código para que quede en el registro.")
