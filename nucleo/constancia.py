"""La constancia de inscripción en PDF.

En lugar de firmar papeles, el reciclador se lleva (o recibe por WhatsApp) una
constancia con su código de registro. Usamos la librería fpdf2, que dibuja el PDF
línea por línea.

Nota técnica: las fuentes que trae fpdf2 (Helvetica) aceptan tildes y eñes, pero no
emojis; por eso el texto de la constancia no lleva emojis.
"""
from datetime import datetime

from fpdf import FPDF

from nucleo.extraccion import FichaReciclador


def texto(valor) -> str:
    """Convierte cualquier valor de la ficha en texto legible."""
    if valor is None or valor == []:
        return "No indicado"
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, list):
        return ", ".join(valor)
    if isinstance(valor, float):
        return f"{valor:,.0f}"
    return str(valor)


def crear_constancia(ficha: FichaReciclador, codigo: str) -> bytes:
    """Arma el PDF y lo devuelve como bytes (para el botón de descarga)."""
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # Encabezado
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 10, "EcoBarrio", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "Constancia de inscripción - Registro Municipal de Recicladores",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Código: {codigo}    Fecha: {datetime.now():%d/%m/%Y %H:%M}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Tabla con los datos de la ficha
    filas = [
        ("Nombre completo", ficha.nombre_completo),
        ("DNI", ficha.dni),
        ("Edad", ficha.edad),
        ("Distrito de vivienda", ficha.distrito_vivienda),
        ("Sector", ficha.sector_vivienda),
        ("Materiales", ficha.materiales),
        ("Recoge y mueve con", ficha.medio_transporte),
        ("Pertenece a una asociación", ficha.pertenece_asociacion),
        ("Asociación", ficha.nombre_asociacion),
        ("Equipo de protección", ficha.equipo_proteccion),
    ]
    for etiqueta, valor in filas:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 7, etiqueta, border="B")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 7, texto(valor), border="B", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0, 5,
        "La persona registrada dio su consentimiento verbal, grabado en audio, para el "
        "tratamiento de sus datos personales con fines de inscripción en el Registro "
        "Municipal de Recicladores (Ley 29419 y D. S. 005-2010-MINAM; Ley 29733 de "
        "Protección de Datos Personales). Documento generado en un demo: no tiene validez oficial.",
    )
    return bytes(pdf.output())
