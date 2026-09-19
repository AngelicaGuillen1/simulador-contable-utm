"""Pruebas de las retenciones de Renta y de IVA en el módulo de compras.

Ecuador: toda compra a un proveedor sujeto a retención genera comprobante de retención. La
retención de Renta se calcula sobre el VALOR DEL BIEN O SERVICIO (subtotal, sin IVA) y la
retención de IVA sobre el VALOR DEL IVA de la factura.

Las pruebas trabajan sobre la copia de la base demostrativa que entrega la fixture `db` y le
aplican el catálogo tributario oficial (database/parametros_tributarios_sri.py), que es el DATO
del que el módulo lee los porcentajes: se verifica la tarifa del SRI, no un número escrito en el
código del servicio.
"""
import os
import re
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from database.parametros_tributarios_sri import aplicar as aplicar_catalogo_sri  # noqa: E402
from models import get_db_connection                                             # noqa: E402
from services.purchase_service import (PurchaseService, CONCEPTOS_POR_CLAVE,     # noqa: E402
                                       TIPO_COMPRA_SIN_RETENCION)
from services.tax_service import TaxService                                      # noqa: E402

PRODUCTO = 12          # mercadería de la empresa demostrativa
PROVEEDOR = 3
FECHA = "2026-04-15"


@pytest.fixture()
def db_sri(db):
    """Copia de la base demostrativa con el catálogo tributario oficial del SRI aplicado."""
    aplicar_catalogo_sri(db, verboso=False)
    return db


# ------------------------------------------------------------------ utilidades de las pruebas
def _compra(db, tipo_compra, contribuyente_especial=False, factura="FAC-RET-0001",
            cantidad=100, costo_unitario=10.00, forma_pago="CREDITO"):
    """Compra de 100 unidades a $10.00 -> subtotal exacto de $1,000.00."""
    return PurchaseService.create_purchase(
        1, PROVEEDOR, factura,
        [{"producto_id": PRODUCTO, "cantidad": cantidad, "costo_unitario": costo_unitario}],
        forma_pago=forma_pago, dias_credito=30, fecha=FECHA, db_path=db,
        tipo_compra=tipo_compra, proveedor_contribuyente_especial=contribuyente_especial)


def _fila_compra(db, compra_id):
    conn = get_db_connection(db)
    try:
        fila = conn.execute("SELECT * FROM compras WHERE id = ?", (compra_id,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def _lineas_asiento(db, asiento_id):
    conn = get_db_connection(db)
    try:
        filas = conn.execute("""
            SELECT c.codigo, c.nombre, d.debe, d.haber, d.referencia
            FROM detalle_asientos d
            JOIN cuentas c ON c.id = d.cuenta_id
            WHERE d.asiento_id = ?
            ORDER BY d.id ASC
        """, (asiento_id,)).fetchall()
        return [dict(f) for f in filas]
    finally:
        conn.close()


def _cuenta_retencion_iva(db):
    """Código de la cuenta que el catálogo del SRI asigna a la retención de IVA.

    No se escribe el código a mano: el plan de cuentas pedagógico puede tener ocupado el 2.1.04
    (por ejemplo con «Sueldos y Beneficios Sociales por Pagar»), así que la prueba lee la cuenta
    que el propio catálogo tributario configuró.
    """
    conn = get_db_connection(db)
    try:
        fila = conn.execute("""
            SELECT c.codigo FROM impuestos i
            JOIN cuentas c ON c.id = i.cuenta_contable_id
            WHERE i.codigo = 'RET-IVA-30-BIE'
        """).fetchone()
        return fila["codigo"] if fila else None
    finally:
        conn.close()


def _cuenta_retencion_renta(db):
    """Código de la cuenta configurada para la retención de Renta."""
    conn = get_db_connection(db)
    try:
        fila = conn.execute("""
            SELECT c.codigo FROM impuestos i
            JOIN cuentas c ON c.id = i.cuenta_contable_id
            WHERE i.codigo = 'RET-RENTA-02-BIE'
        """).fetchone()
        return fila["codigo"] if fila else None
    finally:
        conn.close()


def _porcentaje_catalogo(db, codigo):
    return float(TaxService.get_tax_by_code(codigo, db_path=db)["porcentaje"])


def _totales(lineas):
    return (round(sum(l["debe"] for l in lineas), 2), round(sum(l["haber"] for l in lineas), 2))


def _haber_de(lineas, codigo_cuenta):
    for linea in lineas:
        if linea["codigo"] == codigo_cuenta:
            return round(linea["haber"], 2)
    return None


def _debe_de(lineas, codigo_cuenta):
    for linea in lineas:
        if linea["codigo"] == codigo_cuenta:
            return round(linea["debe"], 2)
    return None


# ------------------------------------------------------------------ 1) BIENES 2 % / 30 %
def test_compra_de_bienes_retencion_renta_2_por_ciento_y_iva_30_por_ciento(db_sri):
    compra_id, factura, total = _compra(db_sri, "BIENES", factura="FAC-RET-BIE-01")
    fila = _fila_compra(db_sri, compra_id)

    # Factura: 1.000,00 + IVA 15 % = 1.150,00
    assert fila["subtotal"] == pytest.approx(1000.00, abs=0.01)
    assert fila["iva_porcentaje"] == pytest.approx(15.0)
    assert fila["iva_valor"] == pytest.approx(150.00, abs=0.01)
    assert fila["total"] == pytest.approx(1150.00, abs=0.01)
    assert total == pytest.approx(1150.00, abs=0.01)

    # Retenciones: Renta 2 % de 1.000,00 = 20,00 | IVA 30 % de 150,00 = 45,00
    assert fila["tipo_compra"] == "BIENES"
    assert fila["retencion_renta_codigo"] == "RET-RENTA-02-BIE"
    assert fila["retencion_renta_porcentaje"] == pytest.approx(
        _porcentaje_catalogo(db_sri, "RET-RENTA-02-BIE"))
    assert fila["retencion_renta_valor"] == pytest.approx(20.00, abs=0.01)
    assert fila["retencion_iva_codigo"] == "RET-IVA-30-BIE"
    assert fila["retencion_iva_porcentaje"] == pytest.approx(
        _porcentaje_catalogo(db_sri, "RET-IVA-30-BIE"))
    assert fila["retencion_iva_valor"] == pytest.approx(45.00, abs=0.01)
    assert fila["total_retenciones"] == pytest.approx(65.00, abs=0.01)
    assert fila["neto_pagar"] == pytest.approx(1085.00, abs=0.01)

    # Asiento: Debe 1.1.06 (1.000,00) + 1.1.07 (150,00) = Haber retención de Renta (20,00) +
    # retención de IVA (45,00) + 2.1.01 (1.085,00)
    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    assert _debe_de(lineas, "1.1.06") == pytest.approx(1000.00, abs=0.01)
    assert _debe_de(lineas, "1.1.07") == pytest.approx(150.00, abs=0.01)
    assert _haber_de(lineas, "2.1.03") == pytest.approx(20.00, abs=0.01)
    assert _haber_de(lineas, _cuenta_retencion_iva(db_sri)) == pytest.approx(45.00, abs=0.01)
    assert _haber_de(lineas, "2.1.01") == pytest.approx(1085.00, abs=0.01)
    assert _totales(lineas) == (1150.00, 1150.00)


def test_el_asiento_acredita_las_cuentas_de_retencion_del_catalogo(db_sri):
    """Las cuentas acreditadas son las que el catálogo tributario tiene configuradas."""
    compra_id, _factura, _total = _compra(db_sri, "BIENES", factura="FAC-RET-BIE-02")
    fila = _fila_compra(db_sri, compra_id)
    lineas = _lineas_asiento(db_sri, fila["asiento_id"])

    conn = get_db_connection(db_sri)
    try:
        cuenta_renta = conn.execute("""SELECT c.id, c.codigo FROM impuestos i
                                           JOIN cuentas c ON c.id = i.cuenta_contable_id
                                           WHERE i.codigo = 'RET-RENTA-02-BIE'""").fetchone()
        cuenta_iva = conn.execute("""SELECT c.id, c.codigo FROM impuestos i
                                         JOIN cuentas c ON c.id = i.cuenta_contable_id
                                         WHERE i.codigo = 'RET-IVA-30-BIE'""").fetchone()
        impuesto_renta = conn.execute(
            "SELECT cuenta_contable_id FROM impuestos WHERE codigo = 'RET-RENTA-02-BIE'").fetchone()
        impuesto_iva = conn.execute(
            "SELECT cuenta_contable_id FROM impuestos WHERE codigo = 'RET-IVA-30-BIE'").fetchone()
    finally:
        conn.close()

    assert impuesto_renta["cuenta_contable_id"] == cuenta_renta["id"]
    assert impuesto_iva["cuenta_contable_id"] == cuenta_iva["id"]
    assert _haber_de(lineas, "2.1.03") == pytest.approx(20.00, abs=0.01)
    assert _haber_de(lineas, _cuenta_retencion_iva(db_sri)) == pytest.approx(45.00, abs=0.01)


def test_la_cuenta_por_pagar_y_la_deuda_del_proveedor_son_el_neto(db_sri):
    conn = get_db_connection(db_sri)
    try:
        deuda_antes = conn.execute(
            "SELECT saldo_pendiente FROM proveedores WHERE id = ?", (PROVEEDOR,)).fetchone()["saldo_pendiente"]
    finally:
        conn.close()

    compra_id, factura, _total = _compra(db_sri, "BIENES", factura="FAC-RET-BIE-03")

    conn = get_db_connection(db_sri)
    try:
        cxp = conn.execute("SELECT * FROM cuentas_pagar WHERE compra_id = ?", (compra_id,)).fetchone()
        deuda_despues = conn.execute(
            "SELECT saldo_pendiente FROM proveedores WHERE id = ?", (PROVEEDOR,)).fetchone()["saldo_pendiente"]
    finally:
        conn.close()

    assert cxp["monto_original"] == pytest.approx(1085.00, abs=0.01)
    assert cxp["saldo_actual"] == pytest.approx(1085.00, abs=0.01)
    assert deuda_despues == pytest.approx(deuda_antes + 1085.00, abs=0.01)
    assert factura == "FAC-RET-BIE-03"


def test_compra_en_efectivo_paga_el_neto_y_no_el_total(db_sri):
    compra_id, _factura, _total = _compra(db_sri, "BIENES", factura="FAC-RET-BIE-04", forma_pago="EFECTIVO")
    fila = _fila_compra(db_sri, compra_id)
    lineas = _lineas_asiento(db_sri, fila["asiento_id"])

    assert _haber_de(lineas, "1.1.01") == pytest.approx(1085.00, abs=0.01)
    assert _totales(lineas) == (1150.00, 1150.00)


# ------------------------------------------------------------------ 2) SERVICIOS 3 % / 70 %
def test_compra_de_servicios_de_mano_de_obra_retencion_3_y_70(db_sri):
    compra_id, _factura, _total = _compra(db_sri, "SERVICIOS_MANO_OBRA", factura="FAC-RET-SRV-01")
    fila = _fila_compra(db_sri, compra_id)

    assert fila["retencion_renta_codigo"] == "RET-RENTA-03-SRV"
    assert fila["retencion_renta_porcentaje"] == pytest.approx(3.0)
    assert fila["retencion_renta_valor"] == pytest.approx(30.00, abs=0.01)     # 3 % de 1.000,00
    assert fila["retencion_iva_codigo"] == "RET-IVA-70-SRV"
    assert fila["retencion_iva_porcentaje"] == pytest.approx(70.0)
    assert fila["retencion_iva_valor"] == pytest.approx(105.00, abs=0.01)      # 70 % de 150,00
    assert fila["total_retenciones"] == pytest.approx(135.00, abs=0.01)
    assert fila["neto_pagar"] == pytest.approx(1015.00, abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    assert _haber_de(lineas, "2.1.03") == pytest.approx(30.00, abs=0.01)
    assert _haber_de(lineas, _cuenta_retencion_iva(db_sri)) == pytest.approx(105.00, abs=0.01)
    assert _haber_de(lineas, "2.1.01") == pytest.approx(1015.00, abs=0.01)
    assert _totales(lineas) == (1150.00, 1150.00)


# ------------------------------------------------------------------ 3) PROFESIONALES 10 % / 100 %
def test_compra_de_servicios_profesionales_retencion_10_y_100(db_sri):
    compra_id, _factura, _total = _compra(db_sri, "SERVICIOS_PROFESIONALES", factura="FAC-RET-PRO-01")
    fila = _fila_compra(db_sri, compra_id)

    assert fila["retencion_renta_codigo"] == "RET-RENTA-10-HON"
    assert fila["retencion_renta_porcentaje"] == pytest.approx(10.0)
    assert fila["retencion_renta_valor"] == pytest.approx(100.00, abs=0.01)    # 10 % de 1.000,00
    assert fila["retencion_iva_codigo"] == "RET-IVA-100-PRO"
    assert fila["retencion_iva_porcentaje"] == pytest.approx(100.0)
    assert fila["retencion_iva_valor"] == pytest.approx(150.00, abs=0.01)      # 100 % de 150,00
    assert fila["total_retenciones"] == pytest.approx(250.00, abs=0.01)
    assert fila["neto_pagar"] == pytest.approx(900.00, abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    assert _haber_de(lineas, "2.1.03") == pytest.approx(100.00, abs=0.01)
    assert _haber_de(lineas, _cuenta_retencion_iva(db_sri)) == pytest.approx(150.00, abs=0.01)
    assert _haber_de(lineas, "2.1.01") == pytest.approx(900.00, abs=0.01)
    assert _totales(lineas) == (1150.00, 1150.00)


# ------------------------------------------------------------------ 4) CONTRIBUYENTE ESPECIAL
def test_compra_de_bienes_a_contribuyente_especial_retencion_de_iva_10(db_sri):
    compra_id, _factura, _total = _compra(db_sri, "BIENES", contribuyente_especial=True,
                                          factura="FAC-RET-ESP-01")
    fila = _fila_compra(db_sri, compra_id)

    assert fila["proveedor_contribuyente_especial"] == 1
    # La retención de Renta se mantiene (2 %) y la de IVA baja al 10 %
    assert fila["retencion_renta_valor"] == pytest.approx(20.00, abs=0.01)
    assert fila["retencion_iva_codigo"] == "RET-IVA-10-BIE-ESP"
    assert fila["retencion_iva_porcentaje"] == pytest.approx(
        _porcentaje_catalogo(db_sri, "RET-IVA-10-BIE-ESP"))
    assert fila["retencion_iva_valor"] == pytest.approx(15.00, abs=0.01)       # 10 % de 150,00
    assert fila["neto_pagar"] == pytest.approx(1115.00, abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    assert _haber_de(lineas, _cuenta_retencion_iva(db_sri)) == pytest.approx(15.00, abs=0.01)
    assert _haber_de(lineas, "2.1.03") == pytest.approx(20.00, abs=0.01)
    assert _totales(lineas) == (1150.00, 1150.00)


def test_compra_de_servicios_a_contribuyente_especial_retencion_de_iva_20(db_sri):
    compra_id, _factura, _total = _compra(db_sri, "SERVICIOS_MANO_OBRA", contribuyente_especial=True,
                                          factura="FAC-RET-ESP-02")
    fila = _fila_compra(db_sri, compra_id)

    assert fila["retencion_renta_valor"] == pytest.approx(30.00, abs=0.01)     # 3 % se mantiene
    assert fila["retencion_iva_codigo"] == "RET-IVA-20-SRV-ESP"
    assert fila["retencion_iva_porcentaje"] == pytest.approx(20.0)
    assert fila["retencion_iva_valor"] == pytest.approx(30.00, abs=0.01)       # 20 % de 150,00
    assert fila["total_retenciones"] == pytest.approx(60.00, abs=0.01)
    assert fila["neto_pagar"] == pytest.approx(1090.00, abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    assert _totales(lineas) == (1150.00, 1150.00)


# ------------------------------------------------------------------ 5) RIMPE NEGOCIO POPULAR
def test_compra_a_rimpe_negocio_popular_sin_retencion_de_renta_ni_de_iva(db_sri):
    compra_id, _factura, _total = _compra(db_sri, "RIMPE_NEGOCIO_POPULAR", factura="FAC-RET-RIMPE-01")
    fila = _fila_compra(db_sri, compra_id)

    assert fila["retencion_renta_codigo"] == "RET-RENTA-00-RIMPE"
    assert fila["retencion_renta_porcentaje"] == pytest.approx(0.0)
    assert fila["retencion_renta_valor"] == pytest.approx(0.00, abs=0.01)
    assert fila["retencion_iva_codigo"] is None
    assert fila["retencion_iva_valor"] == pytest.approx(0.00, abs=0.01)
    assert fila["total_retenciones"] == pytest.approx(0.00, abs=0.01)
    assert fila["neto_pagar"] == pytest.approx(1150.00, abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    assert _haber_de(lineas, "2.1.03") is None
    assert _haber_de(lineas, _cuenta_retencion_iva(db_sri)) is None
    assert _haber_de(lineas, "2.1.01") == pytest.approx(1150.00, abs=0.01)
    assert _totales(lineas) == (1150.00, 1150.00)


# ------------------------------------------------------------------ 6) SIN RETENCIÓN
def test_compra_sin_retencion_no_acredita_cuentas_de_retencion(db_sri):
    compra_id, _factura, _total = _compra(db_sri, TIPO_COMPRA_SIN_RETENCION, factura="FAC-RET-NO-01")
    fila = _fila_compra(db_sri, compra_id)

    assert fila["tipo_compra"] == "SIN_RETENCION"
    assert fila["retencion_renta_valor"] == pytest.approx(0.00, abs=0.01)
    assert fila["retencion_iva_valor"] == pytest.approx(0.00, abs=0.01)
    assert fila["total_retenciones"] == pytest.approx(0.00, abs=0.01)
    assert fila["neto_pagar"] == pytest.approx(1150.00, abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    assert [l["codigo"] for l in lineas] == ["1.1.06", "1.1.07", "2.1.01"]
    assert _totales(lineas) == (1150.00, 1150.00)


def test_compra_por_defecto_conserva_el_comportamiento_anterior(db_sri):
    """Sin indicar el concepto, la compra se registra como SIN_RETENCION (como antes)."""
    compra_id, _factura, total = PurchaseService.create_purchase(
        1, PROVEEDOR, "FAC-RET-DEF-01",
        [{"producto_id": PRODUCTO, "cantidad": 100, "costo_unitario": 10.00}],
        forma_pago="CREDITO", dias_credito=30, fecha=FECHA, db_path=db_sri)
    fila = _fila_compra(db_sri, compra_id)

    assert total == pytest.approx(1150.00, abs=0.01)
    assert fila["tipo_compra"] == TIPO_COMPRA_SIN_RETENCION
    assert fila["neto_pagar"] == pytest.approx(1150.00, abs=0.01)
    assert fila["total_retenciones"] == pytest.approx(0.00, abs=0.01)


# ------------------------------------------------------------------ 7) TODOS LOS CONCEPTOS
@pytest.mark.parametrize("clave", sorted(CONCEPTOS_POR_CLAVE))
def test_el_asiento_cuadra_y_el_neto_es_correcto_en_todos_los_conceptos(db_sri, clave):
    """Para cualquier concepto: Total Debe = Total Haber y neto = factura − retenciones.

    Además se comprueba la REGLA DE BASES: la retención de Renta se aplica al subtotal y la
    retención de IVA al valor del IVA, usando los porcentajes del catálogo del SRI.
    """
    compra_id, _factura, _total = _compra(db_sri, clave, factura=f"FAC-RET-TODOS-{clave}")
    fila = _fila_compra(db_sri, compra_id)

    assert fila["subtotal"] == pytest.approx(1000.00, abs=0.01)
    assert fila["iva_valor"] == pytest.approx(150.00, abs=0.01)
    assert fila["total"] == pytest.approx(1150.00, abs=0.01)

    renta_esperada = iva_esperada = 0.0
    if fila["retencion_renta_codigo"]:
        porcentaje = _porcentaje_catalogo(db_sri, fila["retencion_renta_codigo"])
        renta_esperada = round(fila["subtotal"] * porcentaje / 100.0, 2)
        assert fila["retencion_renta_porcentaje"] == pytest.approx(porcentaje)
    if fila["retencion_iva_codigo"]:
        porcentaje = _porcentaje_catalogo(db_sri, fila["retencion_iva_codigo"])
        iva_esperada = round(fila["iva_valor"] * porcentaje / 100.0, 2)
        assert fila["retencion_iva_porcentaje"] == pytest.approx(porcentaje)

    assert fila["retencion_renta_valor"] == pytest.approx(renta_esperada, abs=0.01)
    assert fila["retencion_iva_valor"] == pytest.approx(iva_esperada, abs=0.01)
    assert fila["total_retenciones"] == pytest.approx(round(renta_esperada + iva_esperada, 2), abs=0.01)
    assert fila["neto_pagar"] == pytest.approx(round(1150.00 - renta_esperada - iva_esperada, 2), abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    total_debe, total_haber = _totales(lineas)
    assert total_debe == pytest.approx(total_haber, abs=0.01)
    assert total_debe == pytest.approx(1150.00, abs=0.01)
    assert _debe_de(lineas, "1.1.06") == pytest.approx(1000.00, abs=0.01)
    assert _debe_de(lineas, "1.1.07") == pytest.approx(150.00, abs=0.01)
    assert _haber_de(lineas, "2.1.01") == pytest.approx(fila["neto_pagar"], abs=0.01)


def test_concepto_de_retencion_desconocido_es_rechazado(db_sri):
    with pytest.raises(ValueError, match="Concepto de retención desconocido"):
        PurchaseService.calcular_desglose_compra(1000.00, tipo_compra="LO_QUE_SEA", db_path=db_sri)


def test_desglose_previo_coincide_con_lo_que_se_contabiliza(db_sri):
    """El desglose que usa la interfaz es el mismo que se guarda al registrar la compra."""
    desglose = PurchaseService.calcular_desglose_compra(
        1000.00, tipo_compra="BIENES", proveedor_contribuyente_especial=False,
        cuenta_pago_id=PurchaseService.cuenta_pago_compra("CREDITO"), db_path=db_sri)

    assert desglose["subtotal"] == pytest.approx(1000.00, abs=0.01)
    assert desglose["iva_valor"] == pytest.approx(150.00, abs=0.01)
    assert desglose["retencion_renta"]["valor"] == pytest.approx(20.00, abs=0.01)
    assert desglose["retencion_iva"]["valor"] == pytest.approx(45.00, abs=0.01)
    assert desglose["total_factura"] == pytest.approx(1150.00, abs=0.01)
    assert desglose["neto_pagar"] == pytest.approx(1085.00, abs=0.01)

    total_debe, total_haber = _totales(desglose["lineas"])
    assert total_debe == pytest.approx(1150.00, abs=0.01)
    assert total_haber == pytest.approx(1150.00, abs=0.01)
    codigos = [l["cuenta_codigo"] for l in desglose["lineas"]]
    assert "1.1.06" in codigos and "1.1.07" in codigos
    assert _cuenta_retencion_renta(db_sri) in codigos
    assert _cuenta_retencion_iva(db_sri) in codigos
    assert "2.1.01" in codigos

    compra_id, _factura, _total = _compra(db_sri, "BIENES", factura="FAC-RET-DESGLOSE")
    fila = _fila_compra(db_sri, compra_id)
    assert fila["neto_pagar"] == pytest.approx(desglose["neto_pagar"], abs=0.01)
    assert fila["retencion_renta_valor"] == pytest.approx(desglose["retencion_renta"]["valor"], abs=0.01)
    assert fila["retencion_iva_valor"] == pytest.approx(desglose["retencion_iva"]["valor"], abs=0.01)


def test_los_conceptos_se_ofrecen_con_los_porcentajes_del_catalogo(db_sri):
    opciones = {o["clave"]: o for o in PurchaseService.listar_conceptos_retencion(db_path=db_sri)}

    assert set(opciones) == set(CONCEPTOS_POR_CLAVE)
    assert opciones["BIENES"]["renta"]["codigo"] == "RET-RENTA-02-BIE"
    assert opciones["BIENES"]["renta"]["porcentaje"] == pytest.approx(2.0)
    assert opciones["BIENES"]["iva"]["porcentaje"] == pytest.approx(30.0)
    assert opciones["BIENES"]["iva_contribuyente_especial"]["porcentaje"] == pytest.approx(10.0)
    assert opciones["SERVICIOS_PROFESIONALES"]["iva"]["porcentaje"] == pytest.approx(100.0)
    assert opciones["RIMPE_NEGOCIO_POPULAR"]["iva"] is None
    assert opciones["SIN_RETENCION"]["renta"] is None
    assert all(o["disponible"] for o in opciones.values())


# ------------------------------------------------------------------ interfaz (rutas)
def test_el_formulario_de_compra_muestra_el_desglose_de_retenciones(db_sri, admin_client):
    respuesta = admin_client.get("/compras/nueva")
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)

    for texto in ("Retención Renta", "Retención IVA", "Neto a pagar al proveedor",
                  "proveedor_contribuyente_especial", 'name="tipo_compra"',
                  "RET-RENTA-02-BIE", "RET-IVA-30-BIE", "BIENES", "SERVICIOS_MANO_OBRA"):
        assert texto in html, f"Falta en el formulario: {texto}"


def test_vista_previa_del_desglose_responde_el_calculo_del_servicio(db_sri, admin_client):
    respuesta = admin_client.post("/compras/desglose", data={
        "subtotal": "1000", "tipo_compra": "BIENES", "forma_pago": "CREDITO",
        "proveedor_contribuyente_especial": "0",
    })
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["ok"] is True
    desglose = datos["desglose"]

    assert desglose["iva_valor"] == pytest.approx(150.00, abs=0.01)
    assert desglose["retencion_renta"]["valor"] == pytest.approx(20.00, abs=0.01)
    assert desglose["retencion_iva"]["valor"] == pytest.approx(45.00, abs=0.01)
    assert desglose["total_retenciones"] == pytest.approx(65.00, abs=0.01)
    assert desglose["neto_pagar"] == pytest.approx(1085.00, abs=0.01)


def test_la_vista_previa_expone_los_campos_que_muestra_el_formulario(db_sri, admin_client):
    """Contrato entre el desglose y el JavaScript del formulario: todas las claves que la
    pantalla pinta antes de guardar deben venir en la respuesta."""
    respuesta = admin_client.post("/compras/desglose", data={
        "subtotal": "1000", "tipo_compra": "BIENES", "forma_pago": "CREDITO"})
    desglose = respuesta.get_json()["desglose"]

    for clave in ("subtotal", "iva_codigo", "iva_porcentaje", "iva_valor", "total_factura",
                  "total_retenciones", "neto_pagar", "retencion_renta", "retencion_iva",
                  "proveedor_contribuyente_especial", "concepto_etiqueta", "lineas"):
        assert clave in desglose, f"El desglose no expone {clave}"

    for clave in ("codigo", "porcentaje", "valor", "base", "cuenta_codigo"):
        assert clave in desglose["retencion_renta"], f"Falta {clave} en la retención de Renta"
        assert clave in desglose["retencion_iva"], f"Falta {clave} en la retención de IVA"

    for linea in desglose["lineas"]:
        for clave in ("cuenta_codigo", "cuenta_nombre", "debe", "haber", "referencia"):
            assert clave in linea, f"Falta {clave} en la línea del asiento"


def test_la_vista_previa_rechaza_un_subtotal_invalido(db_sri, admin_client):
    respuesta = admin_client.post("/compras/desglose", data={
        "subtotal": "no-es-un-numero", "tipo_compra": "BIENES"})
    assert respuesta.status_code == 400
    assert respuesta.get_json()["ok"] is False


def test_vista_previa_con_contribuyente_especial_reduce_la_retencion_de_iva(db_sri, admin_client):
    respuesta = admin_client.post("/compras/desglose", data={
        "subtotal": "1000", "tipo_compra": "SERVICIOS_MANO_OBRA", "forma_pago": "CREDITO",
        "proveedor_contribuyente_especial": "1",
    })
    desglose = respuesta.get_json()["desglose"]

    assert desglose["retencion_renta"]["valor"] == pytest.approx(30.00, abs=0.01)
    assert desglose["retencion_iva"]["codigo"] == "RET-IVA-20-SRV-ESP"
    assert desglose["retencion_iva"]["valor"] == pytest.approx(30.00, abs=0.01)
    assert desglose["neto_pagar"] == pytest.approx(1090.00, abs=0.01)


def test_registrar_compra_desde_la_interfaz_guarda_y_contabiliza_las_retenciones(db_sri, admin_client):
    respuesta = admin_client.post("/compras/nueva", data={
        "proveedor_id": "6", "numero_factura": "FAC-UI-RET-01", "forma_pago": "CREDITO",
        "dias_credito": "30", "tipo_compra": "BIENES", "proveedor_contribuyente_especial": "1",
        "producto_id[]": ["12"], "cantidad[]": ["100"], "costo[]": ["10.00"], "descuento[]": ["0"],
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)
    assert "registrada" in html
    assert "neto al proveedor $1,115.00" in html

    conn = get_db_connection(db_sri)
    try:
        fila = conn.execute("SELECT * FROM compras WHERE numero_factura = ?", ("FAC-UI-RET-01",)).fetchone()
    finally:
        conn.close()

    assert fila is not None
    assert fila["tipo_compra"] == "BIENES"
    assert fila["proveedor_contribuyente_especial"] == 1
    assert fila["retencion_renta_valor"] == pytest.approx(20.00, abs=0.01)
    assert fila["retencion_iva_valor"] == pytest.approx(15.00, abs=0.01)
    assert fila["neto_pagar"] == pytest.approx(1115.00, abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    assert _totales(lineas) == (1150.00, 1150.00)


def test_el_detalle_de_la_compra_muestra_el_desglose_y_el_asiento(db_sri, admin_client):
    compra_id, factura, _total = _compra(db_sri, "BIENES", factura="FAC-RET-DET-01")
    respuesta = admin_client.get(f"/compras/{compra_id}")
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)

    # Las cuentas de retención se resuelven del catálogo (no se escriben a mano).
    cuentas_retencion = (_cuenta_retencion_renta(db_sri), _cuenta_retencion_iva(db_sri))
    for texto in (factura, "Retención Renta", "Retención IVA", "Neto al proveedor",
                  "RET-RENTA-02-BIE", "RET-IVA-30-BIE", *cuentas_retencion, "1,085.00"):
        assert texto in html, f"Falta en el detalle: {texto}"


def test_el_script_del_formulario_usa_elementos_y_campos_que_existen(db_sri, admin_client):
    """El cálculo en pantalla (antes de guardar) sólo puede usar elementos y campos reales."""
    html = admin_client.get("/compras/nueva").get_data(as_text=True)
    inicio = html.index("URL_DESGLOSE")
    script = html[inicio:html.index("</script>", inicio)]

    ids_script = set(re.findall(r'getElementById\("([A-Za-z0-9_]+)"\)', script))
    ids_pagina = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
    assert ids_script, "El formulario no calcula el desglose en pantalla"
    assert not (ids_script - ids_pagina), f"El script usa elementos inexistentes: {ids_script - ids_pagina}"

    claves_script = set(re.findall(r"\b[dD]\.([a-z_]+)", script))
    claves_script |= set(re.findall(r"\b(?:renta|riva|l)\.([a-z_]+)", script))
    desglose = admin_client.post("/compras/desglose", data={
        "subtotal": "1000", "tipo_compra": "BIENES", "forma_pago": "CREDITO"}).get_json()["desglose"]
    campos = set(desglose) | set(desglose["retencion_renta"]) | set(desglose["retencion_iva"])
    campos |= set(desglose["lineas"][0]) | set(desglose["iva_cuenta"]) | set(desglose["cuenta_pago"])
    desconocidos = claves_script - campos
    assert not desconocidos, f"El script lee campos que el desglose no entrega: {desconocidos}"
