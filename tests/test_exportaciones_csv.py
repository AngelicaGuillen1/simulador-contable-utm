"""Exportaciones del balance de comprobación (y de los demás reportes) desde la vista del estudiante.

Estas rutas respondían 500 porque llamaban a la vista `export_csv` como si fuera una función normal
(está envuelta por @login_required, que solo acepta kwargs). Aquí se fija que vuelvan a entregar el
archivo y que la consulta del balance no modifique ningún registro.
"""
import sqlite3

import pytest


COLUMNAS_BALANCE = ["Código", "Cuenta", "Naturaleza", "Débitos", "Créditos",
                    "Saldo Deudor", "Saldo Acreedor"]


def _conteo(db):
    conexion = sqlite3.connect(db)
    try:
        return {tabla: conexion.execute("SELECT COUNT(*) FROM %s" % tabla).fetchone()[0]
                for tabla in ("asientos", "detalle_asientos", "cuentas")}
    finally:
        conexion.close()


@pytest.mark.parametrize("url, primera_columna", [
    ("/reportes/exportar/balance-csv", "Código"),
    ("/reportes/exportar/csv/balance", "Código"),
    ("/reportes/exportar/diario-csv", "N° Asiento"),
    ("/reportes/exportar/inventario-csv", "Código"),
])
def test_las_exportaciones_csv_responden(estudiante_client, url, primera_columna):
    respuesta = estudiante_client.get(url)
    assert respuesta.status_code == 200, "%s respondió %s" % (url, respuesta.status_code)
    assert "text/csv" in respuesta.headers.get("Content-Type", "")
    texto = respuesta.data.decode("utf-8-sig", "ignore")
    assert texto.splitlines()[0].startswith(primera_columna), texto.splitlines()[0]


def test_el_balance_trae_las_columnas_de_sumas_y_saldos(estudiante_client):
    respuesta = estudiante_client.get("/contabilidad/balance")
    assert respuesta.status_code == 200
    html = respuesta.data.decode("utf-8", "ignore")
    for texto in ("Cuadre de Sumas", "Cuadre de Saldos", "Débitos (Debe)", "Créditos (Haber)",
                  "Saldo Deudor", "Saldo Acreedor", "Exportar CSV", "Imprimir"):
        assert texto in html, "falta %s en el balance" % texto


def test_la_exportacion_excel_del_balance_responde(estudiante_client):
    respuesta = estudiante_client.get("/reportes/exportar/excel/balance")
    assert respuesta.status_code == 200, respuesta.status_code
    assert "spreadsheetml" in respuesta.headers.get("Content-Type", "")
    assert len(respuesta.data) > 1000


def test_consultar_y_exportar_el_balance_no_modifica_registros(estudiante_client, db):
    antes = _conteo(db)
    estudiante_client.get("/contabilidad/balance")
    estudiante_client.get("/reportes/exportar/balance-csv")
    estudiante_client.get("/reportes/exportar/excel/balance")
    despues = _conteo(db)
    assert antes == despues, "la consulta del balance escribió en la base: %s -> %s" % (antes, despues)
