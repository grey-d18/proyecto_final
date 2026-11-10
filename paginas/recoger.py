"""Recoger reciclaje: los pedidos de los vecinos que este reciclador puede tomar.

Tabla: descripción, peso, foto y «Lo recogeré». Al marcar el check, el pedido queda
asignado a esta persona y se escucha el aviso: tiene 3 días para recogerlo; si no,
el pedido vuelve a estar disponible para otro reciclador de la zona
(ver liberar_vencidos() en nucleo/base_datos.py).
"""
import base64
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from nucleo.base_datos import (DIAS_PARA_RECOGER, asignar_recojo, marcar_recogido, mis_recojos,
                               recojos_disponibles)
from nucleo.interfaz import hablar, reciclador_actual, volver

yo = reciclador_actual()
volver()
st.title("🚚 Recoger reciclaje")

# Aviso de los 3 días: se muestra y se escucha justo después de marcar «Lo recogeré».
if st.session_state.pop("recien_asignado", False):
    st.warning(f"⏰ Recuerde que tiene un máximo de {DIAS_PARA_RECOGER} días para hacer su recojo. "
               "Si no, se asignará a otro reciclador de la zona.")
    hablar("aviso_recojo")


def foto_como_imagen(foto: bytes | None) -> str | None:
    """La tabla muestra imágenes a partir de un texto «data:image/…;base64,…»."""
    if not foto:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(foto).decode()


# --- Pedidos disponibles ------------------------------------------------------------------
disponibles = recojos_disponibles(yo["distrito_vivienda"], yo["codigo"])
st.subheader(f"Para recoger en {yo['distrito_vivienda']}")
if disponibles.empty:
    st.info("Por ahora no hay reciclaje para recoger en su zona.")
else:
    tabla = pd.DataFrame({
        "id": disponibles["id"],
        "Descripción": disponibles["descripcion"],
        "Peso (kg)": disponibles["peso_kg"],
        "Foto": disponibles["foto"].apply(foto_como_imagen),
        "Lo recogeré": False,
    })
    editada = st.data_editor(
        tabla, hide_index=True, width="stretch", key="tabla_recojos",
        column_order=["Descripción", "Peso (kg)", "Foto", "Lo recogeré"],
        disabled=["Descripción", "Peso (kg)", "Foto"],  # solo se puede marcar el check
        column_config={
            "Foto": st.column_config.ImageColumn("Foto"),
            "Peso (kg)": st.column_config.NumberColumn(format="%.0f kg"),
            "Lo recogeré": st.column_config.CheckboxColumn("Lo recogeré ✔"),
        },
    )
    marcados = editada[editada["Lo recogeré"]]
    if not marcados.empty:
        for recojo_id in marcados["id"]:
            asignar_recojo(int(recojo_id), yo["codigo"])
        st.session_state.recien_asignado = True
        del st.session_state["tabla_recojos"]  # limpiamos los checks de la tabla
        st.rerun()

# --- Mis recojos asignados --------------------------------------------------------------------
mios = mis_recojos(yo["codigo"])
if not mios.empty:
    st.subheader("Mis recojos")
    for _, recojo in mios.iterrows():
        limite = datetime.strptime(recojo["fecha_asignacion"], "%Y-%m-%d %H:%M") + timedelta(days=DIAS_PARA_RECOGER)
        col_texto, col_boton = st.columns([3, 1])
        col_texto.markdown(f"**{recojo['descripcion']}** · {recojo['peso_kg']:.0f} kg · "
                           f"{recojo['direccion'] if pd.notna(recojo['direccion']) else recojo['distrito']}  \n"
                           f"Recoger hasta el {limite:%d/%m a las %H:%M}")
        if col_boton.button("Ya lo recogí", key=f"recogido_{recojo['id']}"):
            marcar_recogido(int(recojo["id"]))
            st.rerun()
