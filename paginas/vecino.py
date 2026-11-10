"""Vecino: «tengo reciclaje para que alguien lo recoja».

El vecino describe lo que tiene, el peso aproximado y una foto, dice dónde está y
elige a un reciclador específico o deja «cualquiera de la zona». El pedido aparece
en «Recoger reciclaje» de los recicladores de ese distrito, con la burbuja de aviso.
"""
import io

import streamlit as st
from PIL import Image

from nucleo.base_datos import crear_recojo, recicladores_del_distrito, recojos_del_vecino
from nucleo.catalogos import DISTRITOS_TRUJILLO
from nucleo.interfaz import volver
from nucleo.ubicacion import elegir_ubicacion

volver("paginas/inicio.py")
st.title("🏠 Pedir un recojo")


def achicar_foto(archivo) -> bytes:
    """Reduce la foto a 600 px de ancho como máximo: pesa poco y carga rápido en la tabla."""
    imagen = Image.open(archivo).convert("RGB")
    imagen.thumbnail((600, 600))
    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=80)
    return salida.getvalue()


vecino = st.text_input("Su nombre", placeholder="Carmen Díaz")
descripcion = st.text_input("¿Qué tiene para reciclar?", placeholder="Cajas de cartón y botellas")
peso = st.number_input("Peso aproximado (kg)", min_value=0.0, max_value=500.0, value=5.0, step=1.0)
foto = st.file_uploader("Foto (en el celular puede tomarla con la cámara)", type=["jpg", "jpeg", "png"])
distrito = st.selectbox("Distrito", DISTRITOS_TRUJILLO, index=DISTRITOS_TRUJILLO.index("El Porvenir"))

st.markdown("**¿Dónde está el reciclaje?**")
ubicacion = elegir_ubicacion("vecino", distrito, "Debe estar en el lugar donde está el reciclaje.")

recicladores = recicladores_del_distrito(distrito)
opciones = {"Cualquiera de la zona": None} | dict(zip(recicladores["nombre_completo"], recicladores["codigo"]))
elegido = st.selectbox("¿Quién lo recoge?", list(opciones))

if st.button("Pedir recojo", type="primary", width="stretch"):
    if not vecino or not descripcion:
        st.error("Escriba su nombre y qué tiene para reciclar.")
    elif ubicacion is None:
        st.error("Falta la ubicación: comparta su ubicación o escriba la dirección.")
    else:
        direccion, lat, lon = ubicacion
        crear_recojo(vecino, distrito, direccion, lat, lon, descripcion, peso,
                     achicar_foto(foto) if foto else None, opciones[elegido])
        st.session_state.vecino = vecino
        st.success("Listo. Los recicladores de la zona ya pueden ver su pedido.")

# --- Mis pedidos --------------------------------------------------------------------------
if st.session_state.get("vecino"):
    pedidos = recojos_del_vecino(st.session_state.vecino)
    if not pedidos.empty:
        st.subheader("Mis pedidos")
        st.dataframe(pedidos.rename(columns={"fecha_hora": "Fecha", "descripcion": "Qué", "peso_kg": "Kg",
                                             "estado": "Estado"}), hide_index=True, width="stretch")
