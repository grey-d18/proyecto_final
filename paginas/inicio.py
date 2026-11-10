"""Portada: qué es ReciclaVoz y para quién es."""
import streamlit as st

from nucleo.base_datos import leer_todos

st.title("♻️ ReciclaVoz")
st.subheader("Formalizamos a recicladores informales con un registro por voz, sin papeles.")

st.markdown(
    """
En el Perú hay unos **53 000 recicladores informales** y solo unos **13 800 trabajadores formales**
del reciclaje (WIEGO, 2021; Banco Mundial, *What a Waste 3.0*). La Ley 29419 pide a las municipalidades
registrarlos y formalizarlos, pero el registro es en papel: fichas largas, firmas, copias de DNI.
Muchas personas que reciclan leen con dificultad, no tienen tiempo de hacer cola y desconfían del trámite.

**ReciclaVoz cambia el formulario por una conversación:**
"""
)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### 🎙️ 1. Responde hablando")
    st.write("La app hace 8 preguntas. La persona responde grabándose desde un celular. "
             "Whisper convierte la voz en texto.")
with col2:
    st.markdown("### 🤖 2. La IA llena la ficha")
    st.write("Claude ordena las respuestas en la ficha del Registro Municipal y marca lo que hay que "
             "confirmar. Se entrega una constancia en PDF.")
with col3:
    st.markdown("### 📊 3. La municipalidad ve el mapa")
    st.write("El panel muestra cuántos recicladores hay, dónde viven, qué recogen y quién necesita "
             "guantes o capacitación.")

st.divider()
fichas = leer_todos()
a, b, c = st.columns(3)
a.metric("Recicladores en el registro", len(fichas))
b.metric("Registrados por voz en este demo", int((fichas["origen"] == "registro por voz").sum()))
c.metric("Kilos recuperados por semana (estimado)", f"{fichas['kg_semana'].sum():,.0f}")

st.caption(
    "Demo con datos sintéticos (personas inventadas) y precios del trabajo de campo de la tesis de la "
    "autora en El Porvenir, Trujillo (2026). No usa datos personales reales."
)
