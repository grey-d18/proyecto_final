"""Registro por voz: el flujo principal del producto.

Paso 0: consentimiento.
Pasos 1 a 8: una pregunta por pantalla; la persona responde grabándose
            (Whisper transcribe) o escribiendo.
Paso 9: la IA llena la ficha, el registrador la revisa, se guarda y se descarga
        la constancia en PDF.

¿Qué es st.session_state?
    Streamlit vuelve a ejecutar este archivo de arriba abajo cada vez que alguien
    aprieta un botón. st.session_state es la "memoria" que sobrevive entre esas
    ejecuciones: ahí guardamos en qué paso vamos y las respuestas.
"""
import hashlib

import streamlit as st

from nucleo.base_datos import guardar_ficha
from nucleo.config import DATOS, hay_clave_gemini
from nucleo.constancia import crear_constancia
from nucleo.extraccion import DISTRITOS_TRUJILLO, FichaReciclador, extraer_ficha
from nucleo.preguntas import PREGUNTAS
from nucleo.voz import transcribir

AUDIOS_EJEMPLO = DATOS / "audios_ejemplo"  # voces de ejemplo generadas con scripts/generar_audios_ejemplo.py
TOTAL = len(PREGUNTAS)


# --- Memoria de la página --------------------------------------------------------
st.session_state.setdefault("paso", 0)
st.session_state.setdefault("ficha", None)
st.session_state.setdefault("codigo", None)
# Las respuestas se guardan en un diccionario aparte porque Streamlit borra el valor de un
# cuadro de texto cuando ese cuadro deja de mostrarse (al pasar a la siguiente pregunta).
st.session_state.setdefault("respuestas", {})


def ir_a(paso: int) -> None:
    st.session_state.paso = paso
    if paso == TOTAL + 1:
        st.session_state.ficha = None  # al terminar, la ficha se vuelve a llenar con las respuestas actuales


def reiniciar() -> None:
    """Borra todo para registrar a otra persona."""
    for clave in list(st.session_state):
        if clave.startswith(("texto_", "audio_", "hash_")) or clave in ("ficha", "codigo", "metodo", "uso", "respuestas"):
            del st.session_state[clave]
    st.session_state.paso = 0


def respuestas_actuales() -> dict[str, str]:
    return {p["clave"]: st.session_state.respuestas.get(p["clave"], "") for p in PREGUNTAS}


def procesar_audio(clave: str, audio_bytes: bytes) -> None:
    """Transcribe un audio solo si es nuevo (comparamos su huella digital o 'hash')."""
    huella = hashlib.md5(audio_bytes).hexdigest()
    if st.session_state.get(f"hash_{clave}") == huella:
        return  # ya lo transcribimos antes: no gastamos tiempo otra vez
    with st.spinner("Escuchando y transcribiendo con Whisper…"):
        texto = transcribir(audio_bytes)
    st.session_state.respuestas[clave] = texto
    st.session_state[f"texto_{clave}"] = texto  # para que aparezca en el cuadro de texto
    st.session_state[f"hash_{clave}"] = huella


# --- Encabezado --------------------------------------------------------------------
st.title("🎙️ Registro por voz")
st.caption("Registro Municipal de Recicladores · Ley 29419")
paso = st.session_state.paso
st.progress(min(paso, TOTAL) / TOTAL, text=f"Pregunta {min(paso, TOTAL)} de {TOTAL}" if paso else "Antes de empezar")

# --- Paso 0: consentimiento --------------------------------------------------------
if paso == 0:
    st.markdown(
        """
**Lea esto en voz alta a la persona:**

> «Le voy a hacer 8 preguntas para inscribirle en el Registro Municipal de Recicladores.
> Puede responder hablando. Su voz se convierte en texto en este equipo y sus datos solo
> se usan para el registro. Puede parar cuando quiera.»
"""
    )
    acepta = st.checkbox("La persona aceptó registrarse y que se usen sus datos para el registro.")
    st.button("Empezar ▶", type="primary", disabled=not acepta, on_click=ir_a, args=(1,))
    st.info(
        "Para el demo: use datos inventados o su propia voz. "
        + ("La ficha la llenará Gemini." if hay_clave_gemini()
           else "No hay clave de Gemini: la ficha se llenará con reglas simples.")
    )

# --- Pasos 1 a 8: una pregunta por pantalla ------------------------------------------
elif paso <= TOTAL:
    pregunta = PREGUNTAS[paso - 1]
    clave = pregunta["clave"]
    # Si volvemos a una pregunta ya respondida, ponemos su respuesta en el cuadro de texto.
    st.session_state.setdefault(f"texto_{clave}", st.session_state.respuestas.get(clave, ""))
    st.header(pregunta["texto"])
    st.caption(pregunta["ayuda"])

    col_voz, col_ejemplo = st.columns([3, 1])
    with col_voz:
        # st.audio_input muestra un micrófono en el navegador (funciona en el celular).
        audio = st.audio_input("Grabe la respuesta", key=f"audio_{clave}")
        if audio is not None:
            procesar_audio(clave, audio.getvalue())
    with col_ejemplo:
        ejemplo = AUDIOS_EJEMPLO / f"{clave}.wav"
        if ejemplo.exists():
            st.write("")
            if st.button("🔊 Usar voz de ejemplo", help="Transcribe una grabación de ejemplo (para el demo)"):
                procesar_audio(clave, ejemplo.read_bytes())
            st.audio(str(ejemplo))

    escrito = st.text_area("Lo que entendió Whisper (puede corregirlo o escribir aquí):", key=f"texto_{clave}", height=90)
    st.session_state.respuestas[clave] = escrito  # guardamos lo que quedó (corregido o escrito a mano)

    atras, adelante = st.columns(2)
    atras.button("◀ Anterior", on_click=ir_a, args=(paso - 1,), width="stretch")
    adelante.button(
        "Siguiente ▶" if paso < TOTAL else "Terminar y llenar la ficha ✅",
        type="primary", on_click=ir_a, args=(paso + 1,), width="stretch",
    )

# --- Paso 9: la IA llena la ficha y la persona la confirma ---------------------------
else:
    respuestas = respuestas_actuales()
    with st.expander("Ver las respuestas transcritas"):
        for p in PREGUNTAS:
            st.markdown(f"**{p['texto']}**  \n{respuestas[p['clave']] or '_(sin respuesta)_'}")

    if st.session_state.ficha is None:
        with st.spinner("La IA está ordenando las respuestas en la ficha…"):
            ficha, metodo, uso = extraer_ficha(respuestas)
        st.session_state.ficha, st.session_state.metodo, st.session_state.uso = ficha, metodo, uso

    ficha: FichaReciclador = st.session_state.ficha
    st.success(f"Ficha llenada con: **{st.session_state.metodo}**")
    if st.session_state.uso:
        uso = st.session_state.uso
        st.caption(f"Tokens: {uso['tokens_entrada']} de entrada y {uso['tokens_salida']} de salida. "
                   "Costo: US$ 0 (plan gratuito de Gemini).")
    if ficha.campos_dudosos:
        st.warning("Confirme con la persona estos datos: " + ", ".join(ficha.campos_dudosos))
    if ficha.observaciones:
        st.info(f"📝 {ficha.observaciones}")

    # Si ya se guardó, mostramos la constancia. Si no, el formulario para revisar.
    if st.session_state.codigo:
        codigo = st.session_state.codigo
        st.balloons()
        st.header(f"✅ Inscrito con el código {codigo}")
        st.download_button(
            "📄 Descargar constancia (PDF)", data=crear_constancia(ficha, codigo),
            file_name=f"constancia_{codigo}.pdf", mime="application/pdf", type="primary",
        )
        st.button("Registrar a otra persona", on_click=reiniciar)
    else:
        st.subheader("Revise la ficha antes de guardarla")
        # st.form agrupa los campos: nada se guarda hasta apretar el botón del final.
        with st.form("revisar_ficha"):
            c1, c2, c3 = st.columns(3)
            nombre = c1.text_input("Nombre completo", ficha.nombre_completo or "")
            dni = c2.text_input("DNI", ficha.dni or "", max_chars=8)
            edad = c3.number_input("Edad", 14, 100, ficha.edad or 30)
            opciones_distrito = DISTRITOS_TRUJILLO + ["Otro"]
            distrito = c1.selectbox(
                "Distrito de vivienda", opciones_distrito,
                index=opciones_distrito.index(ficha.distrito_vivienda) if ficha.distrito_vivienda in opciones_distrito else len(opciones_distrito) - 1,
            )
            sector = c2.text_input("Sector", ficha.sector_vivienda or "")
            zonas = c3.text_input("Zonas de trabajo", ficha.zonas_trabajo or "")
            dias = c1.number_input("Días por semana", 0, 7, ficha.dias_por_semana or 0)
            anios = c2.number_input("Años reciclando", 0, 70, ficha.anios_reciclando or 0)
            kg = c3.number_input("Kilos por semana", 0.0, 5000.0, float(ficha.kg_semana or 0))
            materiales = st.multiselect(
                "Materiales", ["Cartón", "Papel", "Botella PET", "Plástico duro", "Fierro / chatarra",
                               "Cobre", "Aluminio", "Vidrio", "Otro"], ficha.materiales,
            )
            vende_a = st.text_input("Vende a", ficha.vende_a or "")
            c4, c5 = st.columns(2)
            asociacion = c4.checkbox("Pertenece a una asociación", bool(ficha.pertenece_asociacion))
            nombre_asoc = c5.text_input("Nombre de la asociación", ficha.nombre_asociacion or "")
            equipo = st.multiselect(
                "Equipo de protección", ["Guantes", "Mascarilla", "Chaleco", "Botas", "Uniforme"],
                ficha.equipo_proteccion,
            )
            confirmado = st.form_submit_button("Guardar en el registro y crear constancia", type="primary")

        if confirmado:
            if len(dni) != 8 or not dni.isdigit():
                st.error("El DNI debe tener 8 números.")
            else:
                # Creamos la ficha final con lo que revisó el registrador.
                ficha_final = ficha.model_copy(update={
                    "nombre_completo": nombre, "dni": dni, "edad": int(edad),
                    "distrito_vivienda": distrito, "sector_vivienda": sector or None,
                    "zonas_trabajo": zonas or None, "dias_por_semana": int(dias) or None,
                    "anios_reciclando": int(anios) or None, "kg_semana": kg or None,
                    "materiales": materiales, "vende_a": vende_a or None,
                    "pertenece_asociacion": asociacion, "nombre_asociacion": nombre_asoc or None,
                    "equipo_proteccion": equipo,
                })
                st.session_state.ficha = ficha_final
                st.session_state.codigo = guardar_ficha(ficha_final, st.session_state.metodo)
                st.rerun()

        st.button("◀ Volver a las preguntas", on_click=ir_a, args=(TOTAL,))
