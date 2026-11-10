"""Registro por voz: el flujo principal del producto.

Paso 0      bienvenida (se escucha) y consentimiento.
Pasos 1-8   una pregunta por pantalla. La pregunta SE ESCUCHA sola (voz grabada,
            porque la persona puede no saber leer). Debajo, un ejemplo de respuesta.
            La persona aprieta el micrófono, habla y lo vuelve a apretar para terminar
            (st.audio_input, la grabadora de Streamlit). Whisper convierte la voz en texto.
Paso final  la IA llena la ficha, se revisa, se guarda y se descarga la constancia PDF.

¿Qué es st.session_state?
    Streamlit vuelve a ejecutar este archivo de arriba abajo cada vez que alguien
    aprieta un botón. st.session_state es la "memoria" que sobrevive entre esas
    ejecuciones: ahí guardamos en qué paso vamos y las respuestas.
"""
import hashlib

import streamlit as st

from nucleo.base_datos import buscar_reciclador, guardar_ficha
from nucleo.config import hay_clave_gemini
from nucleo.constancia import crear_constancia
from nucleo.catalogos import DISTRITOS_TRUJILLO, EQUIPOS, MATERIALES, TRANSPORTES
from nucleo.extraccion import FichaReciclador, extraer_ficha
from nucleo.interfaz import hablar, volver
from nucleo.preguntas import PREGUNTAS
from nucleo.voz import transcribir

TOTAL = len(PREGUNTAS)

# --- Memoria de la página --------------------------------------------------------
st.session_state.setdefault("paso", 0)
st.session_state.setdefault("ficha", None)
st.session_state.setdefault("codigo", None)
# Las respuestas se guardan en un diccionario aparte porque Streamlit borra el valor de un
# cuadro de texto cuando ese cuadro deja de mostrarse (al pasar a la siguiente pregunta).
st.session_state.setdefault("respuestas", {})


def ir_a(paso: int) -> None:
    # Antes de cambiar de pregunta guardamos lo que hay en el cuadro de texto: si la persona
    # escribe y aprieta «Siguiente» de inmediato, este es el único momento en que el texto existe.
    for clave in list(st.session_state):
        if clave.startswith("texto_"):
            st.session_state.respuestas[clave.removeprefix("texto_")] = st.session_state[clave]
    st.session_state.paso = paso
    if paso == TOTAL + 1:
        st.session_state.ficha = None  # al terminar, la ficha se vuelve a llenar con las respuestas actuales


def reiniciar() -> None:
    """Borra todo para registrar a otra persona."""
    for clave in list(st.session_state):
        if clave.startswith(("texto_", "grabacion_", "hash_")) or clave in (
                "ficha", "codigo", "metodo", "uso", "respuestas", "reciclador"):
            del st.session_state[clave]
    st.session_state.paso = 0


def procesar_audio(clave: str, audio_bytes: bytes) -> None:
    """Transcribe un audio solo si es nuevo (comparamos su huella digital o 'hash')."""
    huella = hashlib.md5(audio_bytes).hexdigest()
    if st.session_state.get(f"hash_{clave}") == huella:
        return  # ya lo transcribimos antes: no gastamos tiempo otra vez
    with st.spinner("Escuchando…"):
        texto = transcribir(audio_bytes)
    st.session_state.respuestas[clave] = texto
    st.session_state[f"texto_{clave}"] = texto  # para que aparezca en el cuadro de texto
    st.session_state[f"hash_{clave}"] = huella


paso = st.session_state.paso
yo = buscar_reciclador(st.session_state["reciclador"]) if st.session_state.get("reciclador") else None
volver("paginas/reciclador.py" if yo else "paginas/inicio.py")

# --- Si la persona ya está inscrita: su constancia --------------------------------------
if yo and paso == 0 and not st.session_state.codigo:
    st.title("🎙️ Registro")
    st.success(f"Usted ya está inscrito con el código **{yo['codigo']}**.")
    st.button("Registrar a otra persona", on_click=reiniciar)
    st.stop()

# --- Paso 0: bienvenida y consentimiento ---------------------------------------------
if paso == 0:
    st.title("🎙️ Registro de recicladores")
    hablar("bienvenida_registro")
    st.markdown(f"Le haremos **{TOTAL} preguntas**. Escuche cada una y responda hablando. "
                "Sus datos solo se usan para el Registro Municipal de Recicladores.")
    acepta = st.checkbox("Acepto registrarme y que se usen mis datos para el registro.")
    st.button("▶ Empezar", type="primary", disabled=not acepta, on_click=ir_a, args=(1,), width="stretch")
    if not hay_clave_gemini():
        st.caption("Sin clave de Gemini: la ficha se llenará con reglas simples.")

# --- Pasos 1 a 8: una pregunta por pantalla ------------------------------------------
elif paso <= TOTAL:
    pregunta = PREGUNTAS[paso - 1]
    clave = pregunta["clave"]
    # Si volvemos a una pregunta ya respondida, ponemos su respuesta en el cuadro de texto.
    st.session_state.setdefault(f"texto_{clave}", st.session_state.respuestas.get(clave, ""))

    st.progress(paso / TOTAL, text=f"Pregunta {paso} de {TOTAL}")
    st.markdown(f"## 🔊 {pregunta['texto']}")
    hablar(clave)  # la pregunta se escucha sola
    st.caption(f"Ejemplo: «{pregunta['ejemplo']}»")

    # El micrófono: st.audio_input es parte de la página (no una página incrustada como la
    # grabadora anterior), así que el navegador pide permiso UNA vez y no en cada pregunta.
    # Muestra el tiempo y la onda mientras graba; se aprieta otra vez para terminar.
    # sample_rate=16000: la frecuencia con la que escucha Whisper (archivo más liviano).
    audio = st.audio_input("Su respuesta", sample_rate=16000, key=f"grabacion_{clave}",
                           label_visibility="collapsed")
    st.markdown("<p style='text-align:center'><b>Apriete el micrófono y responda.</b><br>"
                "Cuando termine, apriételo otra vez.</p>", unsafe_allow_html=True)
    if audio:
        procesar_audio(clave, audio.getvalue())

    escrito = st.text_area("Lo que entendimos (puede corregirlo):", key=f"texto_{clave}", height=80)
    st.session_state.respuestas[clave] = escrito  # guardamos lo que quedó (corregido o escrito a mano)

    atras, adelante = st.columns(2)
    atras.button("◀ Anterior", on_click=ir_a, args=(paso - 1,), width="stretch")
    adelante.button("Siguiente ▶" if paso < TOTAL else "Terminar ✅", type="primary",
                    on_click=ir_a, args=(paso + 1,), width="stretch")

# --- Paso final: la IA llena la ficha y la persona la confirma ------------------------
else:
    respuestas = {p["clave"]: st.session_state.respuestas.get(p["clave"], "") for p in PREGUNTAS}
    if st.session_state.ficha is None:
        with st.spinner("Ordenando sus respuestas en la ficha…"):
            ficha, metodo, uso = extraer_ficha(respuestas)
        st.session_state.ficha, st.session_state.metodo, st.session_state.uso = ficha, metodo, uso

    ficha: FichaReciclador = st.session_state.ficha

    # Si ya se guardó, mostramos la constancia.
    if st.session_state.codigo:
        codigo = st.session_state.codigo
        st.balloons()
        st.header(f"✅ Inscrito con el código {codigo}")
        st.download_button("📄 Descargar constancia (PDF)", data=crear_constancia(ficha, codigo),
                           file_name=f"constancia_{codigo}.pdf", mime="application/pdf",
                           type="primary", width="stretch")
        if st.button("Ir a mi menú ▶", width="stretch"):
            st.session_state.paso, st.session_state.codigo = 0, None
            st.switch_page("paginas/reciclador.py")
        st.stop()

    st.header("Revise su ficha")
    st.caption(f"Llenada con: {st.session_state.metodo}"
               + (" · costo US$ 0 (plan gratuito de Gemini)" if st.session_state.uso else ""))
    if ficha.campos_dudosos:
        st.warning("Confirme estos datos: " + ", ".join(ficha.campos_dudosos))
    with st.expander("Ver las respuestas tal como se escucharon"):
        for p in PREGUNTAS:
            st.markdown(f"**{p['texto']}**  \n{respuestas[p['clave']] or '_(sin respuesta)_'}")

    # st.form agrupa los campos: nada se guarda hasta apretar el botón del final.
    with st.form("revisar_ficha"):
        nombre = st.text_input("Nombre completo", ficha.nombre_completo or "")
        c1, c2 = st.columns(2)
        dni = c1.text_input("DNI", ficha.dni or "", max_chars=8)
        edad = c2.number_input("Edad", 14, 100, ficha.edad or 30)
        opciones_distrito = DISTRITOS_TRUJILLO + ["Otro"]
        distrito = c1.selectbox(
            "Distrito donde vive", opciones_distrito,
            index=opciones_distrito.index(ficha.distrito_vivienda)
            if ficha.distrito_vivienda in opciones_distrito else len(opciones_distrito) - 1)
        sector = c2.text_input("Sector o barrio", ficha.sector_vivienda or "")
        materiales = st.multiselect("Materiales", MATERIALES + ["Otro"], ficha.materiales)
        transporte = st.multiselect("Recoge y mueve los materiales con", TRANSPORTES + ["Otro"],
                                    ficha.medio_transporte)
        c5, c6 = st.columns(2)
        asociacion = c5.checkbox("Pertenece a una asociación", bool(ficha.pertenece_asociacion))
        nombre_asoc = c6.text_input("¿Cuál?", ficha.nombre_asociacion or "")
        equipo = st.multiselect("Equipo de protección", EQUIPOS, ficha.equipo_proteccion)
        confirmado = st.form_submit_button("Guardar y crear constancia", type="primary", width="stretch")

    if confirmado:
        if len(dni) != 8 or not dni.isdigit():
            st.error("El DNI debe tener 8 números.")
        else:
            ficha_final = ficha.model_copy(update={
                "nombre_completo": nombre, "dni": dni, "edad": int(edad),
                "distrito_vivienda": distrito, "sector_vivienda": sector or None,
                "materiales": materiales,
                "medio_transporte": transporte, "pertenece_asociacion": asociacion,
                "nombre_asociacion": nombre_asoc or None, "equipo_proteccion": equipo,
            })
            st.session_state.ficha = ficha_final
            st.session_state.codigo = guardar_ficha(ficha_final, st.session_state.metodo)
            st.session_state.reciclador = st.session_state.codigo  # desde ahora la app sabe quién es
            st.rerun()

    st.button("◀ Volver a las preguntas", on_click=ir_a, args=(TOTAL,))
