"""Cada estudiante trabaja con su propia empresa: misma estructura, datos propios.

Lo que se protege aquí:
  * clientes, proveedores y bancos son los mismos EN CANTIDAD para todos (estructura igual),
  * pero con nombres, identificaciones y números de cuenta distintos (trabajo individual),
  * las identificaciones cumplen la estructura del SRI (cédula módulo 10, RUC módulo 11),
  * y la interfaz muestra el nombre de la empresa del aula, no uno fijo en la plantilla.
"""
import glob
import os
import re
import sqlite3

import pytest

from config import Config

RUTA_AULAS = os.path.join(Config.RUTA_AULAS, "B")


def _aulas(muestra=6):
    rutas = sorted(glob.glob(os.path.join(RUTA_AULAS, "*.db")))
    if not rutas:
        pytest.skip("No hay aulas generadas en este equipo")
    salto = max(1, len(rutas) // muestra)
    return rutas[::salto][:muestra]


def _valida_cedula(identificacion):
    if len(identificacion) != 10 or not identificacion.isdigit():
        return False
    suma = 0
    for posicion, digito in enumerate(identificacion[:9]):
        valor = int(digito) * (2 if posicion % 2 == 0 else 1)
        suma += valor - 9 if valor > 9 else valor
    return (10 - suma % 10) % 10 == int(identificacion[9])


def _valida_ruc(identificacion):
    if len(identificacion) != 13 or not identificacion.isdigit() or identificacion[2] != "9":
        return False
    if identificacion[10:] != "001":
        return False
    suma = sum(int(d) * p for d, p in zip(identificacion[:9], [4, 3, 2, 7, 6, 5, 4, 3, 2]))
    verificador = 11 - suma % 11
    verificador = 0 if verificador >= 10 else verificador
    return str(verificador) == identificacion[9]


def test_misma_estructura_en_todas_las_aulas():
    """Los libros de todos tienen el mismo plan, los mismos productos y los mismos terceros."""
    referencia = None
    for ruta in _aulas(8):
        conexion = sqlite3.connect(ruta)
        try:
            conteo = (conexion.execute("SELECT COUNT(*) FROM cuentas").fetchone()[0],
                      conexion.execute("SELECT COUNT(*) FROM productos").fetchone()[0],
                      conexion.execute("SELECT COUNT(*) FROM clientes").fetchone()[0],
                      conexion.execute("SELECT COUNT(*) FROM proveedores").fetchone()[0],
                      conexion.execute("SELECT COUNT(*) FROM bancos").fetchone()[0])
        finally:
            conexion.close()
        referencia = referencia or conteo
        assert conteo == referencia, "%s tiene otra estructura: %s" % (ruta, conteo)


def test_cada_empresa_es_distinta():
    """No puede haber dos estudiantes con la misma empresa (ni nombre ni RUC)."""
    nombres, rucs = set(), set()
    for ruta in _aulas(30):
        conexion = sqlite3.connect(ruta)
        try:
            razon, ruc = conexion.execute(
                "SELECT razon_social, ruc FROM empresas LIMIT 1").fetchone()
        finally:
            conexion.close()
        assert razon not in nombres, "empresa repetida: %s" % razon
        assert ruc not in rucs, "RUC repetido: %s" % ruc
        nombres.add(razon)
        rucs.add(ruc)


def test_identificaciones_con_estructura_del_sri():
    """Clientes y proveedores llevan cédula o RUC con dígito verificador válido."""
    revisados = 0
    for ruta in _aulas(5):
        conexion = sqlite3.connect(ruta)
        try:
            for tabla in ("clientes", "proveedores"):
                for (identificacion,) in conexion.execute(
                        "SELECT identificacion FROM %s" % tabla):
                    identificacion = str(identificacion)
                    if len(identificacion) == 10:
                        assert _valida_cedula(identificacion), "%s: %s" % (tabla, identificacion)
                    else:
                        assert _valida_ruc(identificacion), "%s: %s" % (tabla, identificacion)
                    revisados += 1
        finally:
            conexion.close()
    assert revisados >= 20, "se esperaban muchas identificaciones revisadas, hubo %d" % revisados


def test_sin_terceros_repetidos_dentro_del_aula():
    """Dentro de un mismo libro, los clientes y los proveedores no se repiten entre sí."""
    for ruta in _aulas(5):
        conexion = sqlite3.connect(ruta)
        try:
            clientes = [f[0] for f in conexion.execute(
                "SELECT nombre_razon_social FROM clientes")]
            proveedores = [f[0] for f in conexion.execute(
                "SELECT razon_social FROM proveedores")]
        finally:
            conexion.close()
        assert len(clientes) == len(set(clientes)), "clientes repetidos en %s" % ruta
        assert len(proveedores) == len(set(proveedores)), "proveedores repetidos en %s" % ruta


def test_la_plantilla_ya_no_lleva_el_nombre_fijo():
    """El nombre de la empresa se lee de la base: no puede estar escrito en la plantilla."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "templates", "base.html"), encoding="utf-8") as archivo:
        plantilla = archivo.read()
    assert "{{ empresa_nombre }}" in plantilla
    assert not re.search(r"Nueva Esperanza", plantilla)
