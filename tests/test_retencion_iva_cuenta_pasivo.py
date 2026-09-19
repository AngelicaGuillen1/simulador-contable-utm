# -*- coding: utf-8 -*-
"""Las retenciones de IVA en COMPRAS deben acreditarse en una cuenta de PASIVO.

Trampa real del plan de cuentas pedagógico: existe una cuenta de retención de IVA pero
del lado contrario —«Retención en la Fuente de IVA por Cobrar»—, que es de ACTIVO y la
usa el vendedor cuando su cliente le retiene. Si el resolvedor no filtra la naturaleza,
al registrar una compra el sistema acredita una cuenta de activo en lugar del pasivo.

Cubre:
  1. Con la cuenta «por cobrar» presente, la retención de IVA de compras va a una cuenta
     de pasivo (naturaleza acreedora), nunca a la de activo.
  2. La retención de renta sigue yendo a su cuenta de pasivo.
  3. El catálogo se puede aplicar dos veces sin cambiar el resultado (idempotente).
"""
import pytest

from models import get_db_connection

CUENTA_ACTIVO = ("1.1.09", "Retención en la Fuente de IVA por Cobrar (Crédito Tributario)",
                 "DEUDORA", "ACTIVO_CORRIENTE")


def _crear(conn, codigo, nombre, naturaleza, clasificacion):
    columnas = [f[1] for f in conn.execute("PRAGMA table_info(cuentas)")]
    datos = {"codigo": codigo, "nombre": nombre, "naturaleza": naturaleza,
             "clasificacion": clasificacion, "acepta_movimiento": 1}
    if "activo" in columnas:
        datos["activo"] = 1
    campos = [c for c in datos if c in columnas]
    conn.execute("INSERT INTO cuentas (%s) VALUES (%s)" % (",".join(campos),
                ",".join("?" for _ in campos)), [datos[c] for c in campos])
    conn.commit()


def _retenciones(codigo_prefijo="RET-IVA"):
    conn = get_db_connection()
    try:
        return [dict(f) for f in conn.execute(
            """SELECT i.codigo AS impuesto, i.porcentaje, c.codigo AS cuenta, c.nombre,
                      c.naturaleza, c.clasificacion
                 FROM impuestos i LEFT JOIN cuentas c ON c.id = i.cuenta_contable_id
                WHERE i.codigo LIKE ? ORDER BY i.codigo""", (codigo_prefijo + "%",)).fetchall()]
    finally:
        conn.close()


@pytest.fixture()
def base_con_cuenta_de_activo(db):
    """Base donde YA existe la cuenta de retención de IVA del lado activo (confunde)."""
    conn = get_db_connection(db)
    try:
        if not conn.execute("SELECT 1 FROM cuentas WHERE codigo = ?", (CUENTA_ACTIVO[0],)).fetchone():
            _crear(conn, *CUENTA_ACTIVO)
    finally:
        conn.close()
    return db


def test_retencion_iva_de_compras_va_a_pasivo(base_con_cuenta_de_activo):
    from database.parametros_tributarios_sri import aplicar

    aplicar(base_con_cuenta_de_activo, verboso=False)
    filas = _retenciones("RET-IVA")
    assert filas, "El catálogo debe tener retenciones de IVA"
    for fila in filas:
        nombre = (fila["nombre"] or "").lower()
        naturaleza = (fila["naturaleza"] or "").upper()
        clasificacion = (fila["clasificacion"] or "").upper()
        assert "cobrar" not in nombre, (
            "La retención de IVA en compras no puede ir a una cuenta por cobrar (%s -> %s)"
            % (fila["impuesto"], fila["nombre"]))
        assert "ACREED" in naturaleza or "PASIVO" in clasificacion, (
            "%s debe acreditarse en una cuenta de pasivo, no en %s (%s)"
            % (fila["impuesto"], fila["nombre"], fila["clasificacion"]))


def test_retencion_de_renta_va_a_pasivo(base_con_cuenta_de_activo):
    from database.parametros_tributarios_sri import aplicar

    aplicar(base_con_cuenta_de_activo, verboso=False)
    for fila in _retenciones("RET-RENTA"):
        assert "ACREED" in (fila["naturaleza"] or "").upper() or \
               "PASIVO" in (fila["clasificacion"] or "").upper(), \
               "La retención de renta en compras es un pasivo (%s)" % fila["impuesto"]


def test_aplicar_dos_veces_no_cambia_el_resultado(base_con_cuenta_de_activo):
    from database.parametros_tributarios_sri import aplicar

    aplicar(base_con_cuenta_de_activo, verboso=False)
    primera = [(f["impuesto"], f["cuenta"]) for f in _retenciones("RET-")]
    aplicar(base_con_cuenta_de_activo, verboso=False)
    segunda = [(f["impuesto"], f["cuenta"]) for f in _retenciones("RET-")]
    assert primera == segunda, "Aplicar el catálogo dos veces no debe cambiar las cuentas"
