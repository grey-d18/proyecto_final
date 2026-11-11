"""Pruebas del registro por voz (se corren con: uv run --with pytest pytest tests/).

Usan las reglas simples, no Gemini: así no necesitan internet ni clave, y siempre dan
el mismo resultado.
"""
import pytest

from nucleo import extraccion
from nucleo.entrevista import avanzar
from nucleo.extraccion import dni_desde_texto, extraer_ficha


@pytest.fixture(autouse=True)
def sin_gemini(monkeypatch):
    monkeypatch.setattr(extraccion, "hay_clave_gemini", lambda: False)


def test_una_respuesta_llena_varios_campos_y_se_salta_la_pregunta():
    # Al dar el DNI, también dijo su nombre y su fecha de nacimiento.
    respuestas = {"dni": "Mi DNI es 45781234, me llamo Rosa Elena Quispe Ramos y nací el 3 de mayo de 1978"}
    paso = avanzar(respuestas, hechas=["dni"])
    ficha = paso["ficha"]
    assert ficha.dni == "45781234"
    assert ficha.nombre_completo == "Rosa Elena Quispe Ramos"
    assert ficha.fecha_nacimiento == "1978-05-03"
    assert ficha.edad is not None and ficha.edad >= 48       # la edad se calcula, no se pregunta
    assert paso["saltadas"] == ["nombre_nacimiento"]          # la pregunta 2 se salta…
    assert paso["siguiente"]["clave"] == "vivienda_celular"   # …y se pasa a la 3


@pytest.mark.parametrize("dicho", [
    "cuatro cinco siete ocho uno dos tres cuatro",
    "cuarenta y cinco, setenta y ocho, doce, treinta y cuatro",
    "Mi DNI es 45 78 12 34",
    "cuatro cinco siete ocho, 1234",
])
def test_dni_dicho_en_palabras(dicho):
    assert dni_desde_texto(dicho) == "45781234"


def test_dni_que_no_tiene_8_digitos_no_se_acepta():
    assert dni_desde_texto("cuatro cinco siete") is None
    ficha, _, _ = extraer_ficha({"dni": "cuatro cinco siete"})
    assert ficha.dni is None
    assert "dni" in ficha.faltantes


def test_faltante_se_repregunta_una_vez_y_queda_por_completar():
    respuestas = {
        "dni": "45781234",
        "nombre_nacimiento": "Rosa Quispe Ramos, nací el 3 de mayo de 1978, soy recicladora",
        "vivienda_celular": "Calle Los Pinos 245, El Porvenir. Mi celular es 987654321",
        "trabajo": "Cartón y botellas en el centro de Trujillo, de lunes a sábado de 6 a 11 de la mañana",
        "equipo": "no me acuerdo",  # no dice con qué trabaja
        "asociacion": "no, en ninguna",
    }
    hechas = list(respuestas)
    paso = avanzar(respuestas, hechas)
    assert paso["siguiente"]["clave"] == "re_equipo"          # se repregunta…
    respuestas["re_equipo"] = "eh… no sé"
    paso = avanzar(respuestas, hechas + ["re_equipo"])
    assert paso["siguiente"] is None                           # …una sola vez, sin bucle
    assert paso["ficha"].por_completar == ["equipo"]           # y queda «por completar»


def test_la_entrevista_nunca_entra_en_bucle():
    respuestas, hechas = {}, []
    siguiente = {"clave": "dni"}
    while siguiente:
        hechas.append(siguiente["clave"])
        respuestas[siguiente["clave"]] = ""
        siguiente = avanzar(respuestas, hechas)["siguiente"]
        assert len(hechas) <= 16
    assert len(hechas) == len(set(hechas))                    # ninguna pregunta se repite


RESTO = {
    "nombre_nacimiento": "Rosa Quispe Ramos, nací el 3 de mayo de 1978, soy mujer",
    "trabajo": "cartón en el centro de Trujillo de lunes a sábado de 6 a 11",
    "equipo": "triciclo y guantes",
    "asociacion": "no, en ninguna",
}


def test_un_celular_con_una_cifra_de_menos_no_se_toma_como_dni():
    # DNI con 7 cifras y celular con 8: el celular NO debe terminar como DNI.
    respuestas = {"dni": "cuatro cinco siete ocho uno dos tres",
                  "vivienda_celular": "Calle Los Pinos 245, El Porvenir, mi celular es 98765432", **RESTO}
    paso = avanzar(respuestas, hechas=list(respuestas))
    assert paso["ficha"].dni is None
    assert paso["ficha"].telefono is None
    assert paso["siguiente"]["clave"] == "re_dni"            # se repregunta el DNI


def test_si_el_modelo_pone_el_celular_como_dni_se_descarta():
    from nucleo.extraccion import DatosDichos, completar
    respuestas = {"dni": "cuatro cinco siete", "vivienda_celular": "mi celular es 98765432"}
    ficha = completar(DatosDichos(dni="98765432"), respuestas)
    assert ficha.dni is None


def test_el_genero_se_dice_en_la_pregunta_2():
    respuestas = {"dni": "45781234", "nombre_nacimiento": "Rosa Elena Quispe Ramos, nací el 3 de mayo de 1978, soy mujer"}
    paso = avanzar(respuestas, hechas=list(respuestas))
    assert paso["ficha"].genero == "Femenino"
    assert paso["siguiente"]["clave"] == "vivienda_celular"


def test_la_pregunta_6_anota_la_asociacion():
    from nucleo.extraccion import asociacion_desde_texto
    assert asociacion_desde_texto("Sí, en la asociación Manos Unidas") == (True, "Manos Unidas")
    assert asociacion_desde_texto("No, en ninguna") == (False, None)
    assert asociacion_desde_texto("") == (None, None)
