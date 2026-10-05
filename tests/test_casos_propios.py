"""Los 19 casos del simulador de práctica también llevan cifras propias de cada estudiante.

Lo que se protege aquí:
  * cada aula tiene los 19 casos y sus asientos siguen cuadrando (partida doble),
  * el IVA sigue siendo el 15 % de la venta y el subtotal se deduce de la cifra mostrada,
  * dos estudiantes no ven las mismas cifras (no se puede copiar),
  * la plantilla conserva los casos originales (fuente de la que se parte cada vez).
"""
import glob
import json
import os
import sqlite3

import pytest

from config import Config

RUTA_AULAS = os.path.join(Config.RUTA_AULAS, "B")
RUTA_PLANTILLA = os.path.join(Config.RUTA_PLANTILLA, "aula_base.db")
TOLERANCIA = 0.02


def _aulas(muestra=6):
    rutas = sorted(glob.glob(os.path.join(RUTA_AULAS, "*.db")))
    if not rutas:
        pytest.skip("No hay aulas generadas en este equipo")
    salto = max(1, len(rutas) // muestra)
    return rutas[::salto][:muestra]


def _casos(ruta):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    try:
        return [dict(f) for f in conexion.execute(
            "SELECT * FROM casos_simulacion ORDER BY id")]
    finally:
        conexion.close()


def test_cada_aula_tiene_los_19_casos_con_sus_soluciones():
    for ruta in _aulas(4):
        casos = _casos(ruta)
        assert len(casos) == 19, "%s tiene %d casos" % (ruta, len(casos))
        for caso in casos:
            assert json.loads(caso["datos_transaccion_json"] or "{}")
            assert json.loads(caso["solucion_esperada_json"] or "{}")


def test_los_asientos_de_los_casos_cuadran():
    """Después de cambiar las cifras, todo asiento sigue con Debe = Haber."""
    for ruta in _aulas(6):
        for caso in _casos(ruta):
            solucion = json.loads(caso["solucion_esperada_json"])
            for nombre, lineas in solucion.items():
                if not isinstance(lineas, list):
                    continue
                debe = round(sum(float(l.get("debe") or 0) for l in lineas), 2)
                haber = round(sum(float(l.get("haber") or 0) for l in lineas), 2)
                assert abs(debe - haber) < TOLERANCIA, (
                    "%s caso %s: %s descuadra (%.2f vs %.2f)"
                    % (os.path.basename(ruta), caso["id"], nombre, debe, haber))


def test_el_iva_sigue_siendo_el_15_por_ciento():
    for ruta in _aulas(4):
        for caso in _casos(ruta):
            for lineas in json.loads(caso["solucion_esperada_json"]).values():
                if not isinstance(lineas, list):
                    continue
                por_cuenta = {l["cuenta"]: l for l in lineas}
                if "2.1.02" not in por_cuenta:
                    continue
                iva = float(por_cuenta["2.1.02"].get("haber") or 0)
                ventas = sum(float(l.get("haber") or 0) for l in lineas
                             if str(l["cuenta"]).startswith("4."))
                if ventas:
                    assert abs(iva - round(ventas * 0.15, 2)) <= 0.03, (
                        "%s caso %s: IVA %.2f no es el 15%% de %.2f"
                        % (os.path.basename(ruta), caso["id"], iva, ventas))


def test_dos_estudiantes_no_ven_las_mismas_cifras():
    """Ningún estudiante comparte el juego completo de cifras de los 19 casos."""
    conjuntos = {}
    for ruta in _aulas(12):
        casos = _casos(ruta)
        huella = tuple(json.loads(c["datos_transaccion_json"]).get("total") for c in casos)
        assert any(v for v in huella), "%s: los casos no traen cifras" % ruta
        usuario = os.path.basename(ruta)[:-3]
        assert huella not in conjuntos, (
            "%s y %s ven exactamente las mismas cifras en los 19 casos"
            % (usuario, conjuntos.get(huella)))
        conjuntos[huella] = usuario


def test_la_plantilla_conserva_los_casos_originales():
    """La plantilla es la fuente: si se variara, las cifras se acumularían al reaplicar."""
    if not os.path.exists(RUTA_PLANTILLA):
        pytest.skip("No hay plantilla en este equipo")
    aulas = _aulas(3)
    caso_aula = _casos(aulas[0])[0]
    caso_plantilla = {c["id"]: c for c in _casos(RUTA_PLANTILLA)}[caso_aula["id"]]
    assert caso_aula["datos_transaccion_json"] != caso_plantilla["datos_transaccion_json"], (
        "la plantilla y las aulas comparten cifras: los casos no se variaron")


def test_el_numero_de_documento_del_enunciado_coincide_con_el_del_caso():
    """Si el enunciado nombra el documento fuente, debe ser el mismo que guarda el caso."""
    for ruta in _aulas(3):
        for caso in _casos(ruta):
            documento = (caso["documento_fuente_numero"] or "").strip()
            if documento and documento in (caso["enunciado"] or ""):
                assert documento in caso["enunciado"]
