"""Los estudiantes pueden cambiar el NOMBRE de sus cuentas, nunca el código.

Lo que se protege:
  * el estudiante renombra una cuenta de su plan y el cambio se ve en la pantalla,
  * el código y la naturaleza quedan intactos (el resto del sistema trabaja con el código),
  * un nombre vacío o demasiado largo se rechaza sin tocar la cuenta,
  * el cambio queda registrado en la auditoría.
"""
import re
import sqlite3

import pytest

from config import Config


def _primera_cuenta(cliente):
    """Toma de la pantalla el id y el código de la primera cuenta con botón de renombrar."""
    html = cliente.get("/contabilidad/cuentas").data.decode("utf-8", "ignore")
    coincidencia = re.search(
        r"data-url=\"/contabilidad/cuentas/(\d+)/editar\"[^>]*?data-codigo=\"([\d.]+)\"", html)
    assert coincidencia, "la pantalla del plan no ofrece el botón para renombrar"
    return int(coincidencia.group(1)), coincidencia.group(2)


def _cuenta(account_id):
    conexion = sqlite3.connect(Config.DATABASE_PATH)
    conexion.row_factory = sqlite3.Row
    try:
        return conexion.execute("SELECT codigo, nombre, naturaleza FROM cuentas WHERE id = ?",
                                (account_id,)).fetchone()
    finally:
        conexion.close()


def test_el_estudiante_renombra_su_cuenta_y_el_codigo_no_cambia(estudiante_client):
    account_id, codigo = _primera_cuenta(estudiante_client)
    antes = _cuenta(account_id)

    respuesta = estudiante_client.post(
        "/contabilidad/cuentas/%d/editar" % account_id,
        data={"nombre": "Caja Matriz Quito"}, follow_redirects=True)
    assert respuesta.status_code == 200

    despues = _cuenta(account_id)
    assert despues["nombre"] == "Caja Matriz Quito"
    assert despues["codigo"] == antes["codigo"] == codigo, "el código no debe cambiar"
    assert despues["naturaleza"] == antes["naturaleza"], "la naturaleza no debe cambiar"

    html = estudiante_client.get("/contabilidad/cuentas").data.decode("utf-8", "ignore")
    assert "Caja Matriz Quito" in html


def test_un_nombre_vacio_no_borra_el_nombre_actual(estudiante_client):
    account_id, _ = _primera_cuenta(estudiante_client)
    antes = _cuenta(account_id)
    estudiante_client.post("/contabilidad/cuentas/%d/editar" % account_id,
                           data={"nombre": "   "}, follow_redirects=True)
    assert _cuenta(account_id)["nombre"] == antes["nombre"]


def test_un_nombre_demasiado_largo_se_rechaza(estudiante_client):
    account_id, _ = _primera_cuenta(estudiante_client)
    antes = _cuenta(account_id)
    estudiante_client.post("/contabilidad/cuentas/%d/editar" % account_id,
                           data={"nombre": "X" * 200}, follow_redirects=True)
    assert _cuenta(account_id)["nombre"] == antes["nombre"]


def test_el_cambio_queda_en_la_auditoria(estudiante_client):
    account_id, _ = _primera_cuenta(estudiante_client)
    estudiante_client.post("/contabilidad/cuentas/%d/editar" % account_id,
                           data={"nombre": "Banco Principal de la Empresa"},
                           follow_redirects=True)
    conexion = sqlite3.connect(Config.DATABASE_PATH)
    try:
        filas = conexion.execute(
            "SELECT valor_anterior, valor_nuevo FROM auditoria WHERE accion = 'RENOMBRAR_CUENTA'"
        ).fetchall()
    finally:
        conexion.close()
    assert filas, "el renombrado no quedó registrado en la auditoría"
    assert "Banco Principal de la Empresa" in (filas[-1][1] or "")
