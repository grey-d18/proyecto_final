"""Panel municipal: lo que la municipalidad paga por ver (herramienta del curso:
dashboards, sesión 05, y mapas con Folium, sesión 06).

Responde las preguntas que hace la gerencia de residuos sólidos:
    ¿Cuántos recicladores hay y dónde viven?
    ¿Qué materiales recogen y cuántos kilos recuperan?
    ¿Quién no tiene equipo de protección ni capacitación?
    ¿Cómo se compara con lo que el distrito reporta al MINAM (SIGERSOL)?
"""
import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from nucleo.base_datos import leer_todos
from nucleo.config import DATOS

# Centro aproximado de cada distrito, para dibujar los círculos del mapa.
CENTROS = {
    "Trujillo": (-8.112, -79.029), "El Porvenir": (-8.079, -79.001),
    "Florencia de Mora": (-8.080, -79.023), "La Esperanza": (-8.077, -79.045),
    "Alto Trujillo": (-8.061, -78.990), "Víctor Larco Herrera": (-8.135, -79.048),
    "Huanchaco": (-8.079, -79.120), "Moche": (-8.171, -79.009), "Laredo": (-8.089, -78.960),
    "Salaverry": (-8.223, -78.977), "Poroto": (-8.012, -78.770), "Simbal": (-7.976, -78.814),
}

st.title("📊 Panel municipal")
st.caption("Municipalidades de la provincia de Trujillo · datos sintéticos + registros hechos en este demo")

fichas = leer_todos()

# --- Filtro ---------------------------------------------------------------------------
distritos = sorted(fichas["distrito_vivienda"].dropna().unique())
elegidos = st.multiselect("Filtrar por distrito", distritos, placeholder="Todos los distritos")
if elegidos:
    fichas = fichas[fichas["distrito_vivienda"].isin(elegidos)]

# --- Indicadores clave ------------------------------------------------------------------
sin_guantes = fichas["equipo_proteccion"].apply(lambda e: "Guantes" not in e)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Inscritos", len(fichas))
k2.metric("Kilos por semana", f"{fichas['kg_semana'].sum():,.0f}")
k3.metric("En una asociación", f"{fichas['pertenece_asociacion'].fillna(0).mean():.0%}")
k4.metric("Sin guantes", f"{sin_guantes.mean():.0%}")
k5.metric("Capacitados", f"{fichas['capacitado'].mean():.0%}")

# --- Gráficos --------------------------------------------------------------------------
izquierda, derecha = st.columns(2)
with izquierda:
    por_distrito = fichas.groupby("distrito_vivienda").agg(
        inscritos=("codigo", "count"), kg_semana=("kg_semana", "sum")).reset_index()
    st.plotly_chart(
        px.bar(por_distrito.sort_values("inscritos"), x="inscritos", y="distrito_vivienda",
               orientation="h", title="Inscritos por distrito", color_discrete_sequence=["#2E7D32"],
               labels={"inscritos": "Recicladores", "distrito_vivienda": ""}),
        width="stretch",
    )
with derecha:
    # explode() separa la lista de materiales: una fila por cada material de cada persona.
    materiales = fichas.explode("materiales")["materiales"].value_counts().reset_index()
    st.plotly_chart(
        px.bar(materiales.sort_values("count"), x="count", y="materiales", orientation="h",
               title="¿Qué recogen? (personas por material)", color_discrete_sequence=["#66BB6A"],
               labels={"count": "Recicladores", "materiales": ""}),
        width="stretch",
    )

# --- Mapa --------------------------------------------------------------------------------
st.subheader("¿Dónde viven los recicladores inscritos?")
mapa = folium.Map(location=[-8.09, -79.02], zoom_start=12, tiles="OpenStreetMap")
for _, fila in por_distrito.iterrows():
    if fila["distrito_vivienda"] in CENTROS:
        folium.CircleMarker(
            CENTROS[fila["distrito_vivienda"]], radius=6 + fila["inscritos"] ** 0.5 * 4,
            color="#2E7D32", fill=True, fill_opacity=0.5,
            tooltip=f"{fila['distrito_vivienda']}: {fila['inscritos']} inscritos, "
                    f"{fila['kg_semana']:,.0f} kg por semana",
        ).add_to(mapa)
st_folium(mapa, height=400, width="stretch", returned_objects=[])

# --- Contexto oficial: SIGERSOL ----------------------------------------------------------
st.subheader("Lo que recuperan los recicladores frente a lo que reporta el distrito")
sigersol = pd.read_csv(DATOS / "sigersol_trujillo_distritos.csv")
sigersol = sigersol[sigersol["anio"] == sigersol["anio"].max()]
sigersol["distrito"] = sigersol["distrito"].str.title().replace({"Victor Larco Herrera": "Víctor Larco Herrera"})
comparacion = por_distrito.merge(sigersol, left_on="distrito_vivienda", right_on="distrito", how="left")
comparacion["t_anio_recicladores"] = comparacion["kg_semana"] * 52 / 1000
st.dataframe(
    comparacion[["distrito_vivienda", "inscritos", "t_anio_recicladores", "valorizado_t", "generado_t"]]
    .rename(columns={
        "distrito_vivienda": "Distrito", "inscritos": "Inscritos",
        "t_anio_recicladores": "Toneladas al año (recicladores inscritos)",
        "valorizado_t": f"Valorizado oficial {int(sigersol['anio'].max())} (t)",
        "generado_t": f"Residuos generados {int(sigersol['anio'].max())} (t)",
    }).round(0),
    hide_index=True, width="stretch",
)
st.caption("SIGERSOL (MINAM), datos abiertos por distrito. Las toneladas de los recicladores son una estimación "
           "con lo que cada persona dijo que junta por semana: muestran el reciclaje que las cifras oficiales no ven.")

# --- Lista de inscritos (con el DNI oculto) ---------------------------------------------
st.subheader("Inscritos")
lista = fichas.copy()
lista["dni"] = lista["dni"].astype(str).str[:2] + "******"  # protegemos el dato personal
lista["materiales"] = lista["materiales"].str.join(", ")
lista["equipo_proteccion"] = lista["equipo_proteccion"].str.join(", ")
columnas = ["codigo", "fecha_registro", "origen", "nombre_completo", "dni", "distrito_vivienda",
            "materiales", "kg_semana", "equipo_proteccion", "capacitado"]
st.dataframe(lista[columnas], hide_index=True, width="stretch")
st.download_button("Descargar CSV", lista[columnas].to_csv(index=False).encode("utf-8"),
                   file_name="registro_recicladores.csv", mime="text/csv")
