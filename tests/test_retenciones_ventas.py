"""Pruebas de la retención que el CLIENTE AGENTE DE RETENCIÓN le practica al VENDEDOR.

Ecuador: cuando el cliente es agente de retención le retiene al vendedor una retención de
Impuesto a la Renta sobre el VALOR DE LA VENTA (subtotal − descuento) y una retención de IVA
sobre el VALOR DEL IVA de la factura, y le paga el NETO. Lo retenido queda a favor del vendedor
(anticipo de Renta y crédito tributario de IVA).

Las pruebas trabajan sobre la copia de la base demostrativa que entrega la fixture `db` y le
aplican el catálogo tributario oficial (database/parametros_tributarios_sri.py), que es el DATO
del que el módulo lee los porcentajes y las cuentas: se verifica la tarifa del SRI y la cuenta
que el propio catálogo configura (`impuestos.cuenta_venta_id`), nunca un número escrito a mano.
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
from services.accounting_service import AccountingService                        # noqa: E402
from services.sales_service import (SalesService, CONCEPTOS_VENTA_POR_CLAVE,     # noqa: E402
                                   TIPO_VENTA_SIN_RETENCION)
from services.tax_service import TaxService                                      # noqa: E402

PRODUCTO = 13            # mercadería de la empresa demostrativa
CLIENTE_AGENTE = 1       # cliente que actúa como agente de retención
CLIENTE_COMUN = 3        # cliente que no retiene
SERVICIO = 1
FECHA = "2026-04-15"
VENTA_EJEMPLO = 4000.00  # venta del compendio de la Unidad 3: 4.000,00 + IVA 15 %


@pytest.fixture()
def db_sri(db):
    """Copia de la base demostrativa con el catálogo tributario oficial del SRI aplicado."""
    aplicar_catalogo_sri(db, verboso=False)
    return db


# ------------------------------------------------------------------ utilidades de las pruebas
def _crear_venta(db, tipo_venta=TIPO_VENTA_SIN_RETENCION, agente=False, forma_pago="CREDITO",
                 cliente_id=CLIENTE_AGENTE, valor=VENTA_EJEMPLO):
    """Venta de una unidad a `valor` dólares: subtotal exacto, sin descuentos."""
    return SalesService.create_sale(
        1, cliente_id, [{"producto_id": PRODUCTO, "cantidad": 1, "precio_unitario": valor}],
        forma_pago=forma_pago, dias_credito=30, fecha=FECHA, db_path=db,
        tipo_venta=tipo_venta, cliente_agente_retencion=agente)


def _crear_servicio(db, tipo_venta=TIPO_VENTA_SIN_RETENCION, agente=False,
                    forma_pago="CREDITO", valor=VENTA_EJEMPLO):
    return SalesService.create_service_transaction(
        1, CLIENTE_AGENTE, SERVICIO, cantidad=1, tarifa=valor, forma_pago=forma_pago,
        dias_credito=30, fecha=FECHA, db_path=db,
        tipo_venta=tipo_venta, cliente_agente_retencion=agente)


def _conexion(db):
    return get_db_connection(db)


def _fila_venta(db, venta_id):
    conn = _conexion(db)
    try:
        fila = conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def _fila_servicio(db, servicio_tx_id):
    conn = _conexion(db)
    try:
        fila = conn.execute("SELECT * FROM transacciones_servicios WHERE id = ?",
                            (servicio_tx_id,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def _lineas_asiento(db, asiento_id):
    conn = _conexion(db)
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


def _cuenta_venta_del_catalogo(db, codigo_impuesto):
    """Cuenta del lado venta que el catálogo configuró para una retención (por código SRI).

    No se escribe el código de cuenta a mano: el plan de cuentas pedagógico puede tener ocupados
    los códigos previstos, así que la prueba lee la cuenta que el propio catálogo enlazó en
    `impuestos.cuenta_venta_id`.
    """
    conn = _conexion(db)
    try:
        fila = conn.execute("""
            SELECT c.id, c.codigo, c.nombre FROM impuestos i
            JOIN cuentas c ON c.id = i.cuenta_venta_id
            WHERE i.codigo = ?
        """, (codigo_impuesto,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def _cuenta_venta_por_tipo(db, tipo):
    """Igual que la anterior, pero localizando el impuesto por su TIPO (RET_RENTA_*, RET_IVA_*)."""
    conn = _conexion(db)
    try:
        fila = conn.execute("""
            SELECT c.id, c.codigo, c.nombre, i.codigo AS impuesto, i.porcentaje
            FROM impuestos i
            JOIN cuentas c ON c.id = i.cuenta_venta_id
            WHERE i.tipo = ?
        """, (tipo,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def _porcentaje_del_catalogo(db, codigo):
    return float(TaxService.get_tax_by_code(codigo, db_path=db)["porcentaje"])


def _totales(lineas):
    return (round(sum(l["debe"] for l in lineas), 2), round(sum(l["haber"] for l in lineas), 2))


def _debe_de(lineas, codigo_cuenta):
    for linea in lineas:
        if linea["codigo"] == codigo_cuenta:
            return round(linea["debe"], 2)
    return None


def _haber_de(lineas, codigo_cuenta):
    for linea in lineas:
        if linea["codigo"] == codigo_cuenta:
            return round(linea["haber"], 2)
    return None


# ------------------------------------------------------------------ 1) BIENES 2 % / 30 %
def test_venta_de_bienes_al_ejemplo_del_compendio(db_sri):
    """Venta a crédito de 4.000,00 + IVA 15 % con retenciones de 80,00 y 180,00: neto 4.340,00.

    Es el ejemplo de la Unidad 3: el comprador retiene 2 % de Renta (80,00) y 30 % del IVA
    (180,00) y paga 4.340,00.
    """
    venta_id, factura, total = _crear_venta(db_sri, "BIENES", agente=True)
    fila = _fila_venta(db_sri, venta_id)

    # Factura: 4.000,00 + IVA 15 % = 4.600,00
    assert fila["subtotal"] == pytest.approx(4000.00, abs=0.01)
    assert fila["iva_porcentaje"] == pytest.approx(15.0)
    assert fila["iva_valor"] == pytest.approx(600.00, abs=0.01)
    assert fila["total"] == pytest.approx(4600.00, abs=0.01)
    assert total == pytest.approx(4600.00, abs=0.01)
    assert factura.startswith("FAC-")

    # Retenciones: Renta 2 % de 4.000,00 = 80,00 | IVA 30 % de 600,00 = 180,00
    assert fila["cliente_agente_retencion"] == 1
    assert fila["tipo_venta"] == "BIENES"
    assert fila["retencion_renta_codigo"] == "RET-RENTA-02-BIE"
    assert fila["retencion_renta_porcentaje"] == pytest.approx(
        _porcentaje_del_catalogo(db_sri, "RET-RENTA-02-BIE"))
    assert fila["retencion_renta_valor"] == pytest.approx(80.00, abs=0.01)
    assert fila["retencion_iva_codigo"] == "RET-IVA-30-BIE"
    assert fila["retencion_iva_porcentaje"] == pytest.approx(
        _porcentaje_del_catalogo(db_sri, "RET-IVA-30-BIE"))
    assert fila["retencion_iva_valor"] == pytest.approx(180.00, abs=0.01)
    assert fila["total_retenciones"] == pytest.approx(260.00, abs=0.01)
    assert fila["neto_cobrar"] == pytest.approx(4340.00, abs=0.01)

    # Asiento: Debe CxC 4.340,00 + Retención de Renta por cobrar 80,00 + Retención de IVA por
    # cobrar 180,00 = Haber Ventas 4.000,00 + IVA Ventas 600,00
    cuenta_renta = _cuenta_venta_del_catalogo(db_sri, "RET-RENTA-02-BIE")
    cuenta_iva = _cuenta_venta_del_catalogo(db_sri, "RET-IVA-30-BIE")
    lineas = _lineas_asiento(db_sri, fila["asiento_id"])

    assert cuenta_renta and cuenta_iva, "El catálogo no enlazó las cuentas del lado venta"
    assert _debe_de(lineas, "1.1.04") == pytest.approx(4340.00, abs=0.01)     # CxC por el neto
    assert _debe_de(lineas, cuenta_renta["codigo"]) == pytest.approx(80.00, abs=0.01)
    assert _debe_de(lineas, cuenta_iva["codigo"]) == pytest.approx(180.00, abs=0.01)
    assert _haber_de(lineas, "4.1.01") == pytest.approx(4000.00, abs=0.01)
    assert _haber_de(lineas, "2.1.02") == pytest.approx(600.00, abs=0.01)
    assert _totales(lineas) == (4600.00, 4600.00)

    # Cuenta por cobrar y deuda del cliente: el NETO, no el total de la factura.
    conn = _conexion(db_sri)
    try:
        cxc = conn.execute("""SELECT * FROM cuentas_cobrar
                              WHERE numero_documento = ? ORDER BY id DESC LIMIT 1""",
                           (factura,)).fetchone()
    finally:
        conn.close()
    assert cxc["monto_original"] == pytest.approx(4340.00, abs=0.01)
    assert cxc["saldo_actual"] == pytest.approx(4340.00, abs=0.01)


def test_las_cuentas_de_retencion_del_asiento_son_las_del_catalogo(db_sri):
    """Las cuentas deudoras son las que el catálogo tributario configuró para el lado venta."""
    venta_id, _factura, _total = _crear_venta(db_sri, "BIENES", agente=True)
    fila = _fila_venta(db_sri, venta_id)
    lineas = _lineas_asiento(db_sri, fila["asiento_id"])

    conn = _conexion(db_sri)
    try:
        renta = conn.execute("""SELECT i.tipo, i.cuenta_venta_id, c.codigo FROM impuestos i
                                JOIN cuentas c ON c.id = i.cuenta_venta_id
                                WHERE i.codigo = 'RET-RENTA-02-BIE'""").fetchone()
        ret_iva = conn.execute("""SELECT i.tipo, i.cuenta_venta_id, c.codigo FROM impuestos i
                                  JOIN cuentas c ON c.id = i.cuenta_venta_id
                                  WHERE i.codigo = 'RET-IVA-30-BIE'""").fetchone()
    finally:
        conn.close()

    assert renta is not None and ret_iva is not None
    assert renta["tipo"] == "RET_RENTA_BIENES"
    assert ret_iva["tipo"] == "RET_IVA_BIENES"
    assert _debe_de(lineas, renta["codigo"]) == pytest.approx(80.00, abs=0.01)
    assert _debe_de(lineas, ret_iva["codigo"]) == pytest.approx(180.00, abs=0.01)


# ------------------------------------------------------------------ 2) SERVICIOS 3 % / 70 %
def test_venta_de_servicios_de_mano_de_obra_3_y_70(db_sri):
    """Servicio de 4.000,00: retención de Renta 3 % (120,00) y de IVA 70 % (420,00)."""
    tx_id, _factura, total = _crear_servicio(db_sri, "SERVICIOS_MANO_OBRA", agente=True)
    fila = _fila_servicio(db_sri, tx_id)

    assert fila["subtotal"] == pytest.approx(4000.00, abs=0.01)
    assert fila["iva_valor"] == pytest.approx(600.00, abs=0.01)
    assert fila["total"] == pytest.approx(4600.00, abs=0.01)
    assert total == pytest.approx(4600.00, abs=0.01)

    assert fila["retencion_renta_codigo"] == "RET-RENTA-03-SRV"
    assert fila["retencion_renta_porcentaje"] == pytest.approx(3.0)
    assert fila["retencion_renta_valor"] == pytest.approx(120.00, abs=0.01)     # 3 % de 4.000,00
    assert fila["retencion_iva_codigo"] == "RET-IVA-70-SRV"
    assert fila["retencion_iva_porcentaje"] == pytest.approx(70.0)
    assert fila["retencion_iva_valor"] == pytest.approx(420.00, abs=0.01)       # 70 % de 600,00
    assert fila["total_retenciones"] == pytest.approx(540.00, abs=0.01)
    assert fila["neto_cobrar"] == pytest.approx(4060.00, abs=0.01)

    cuenta_renta = _cuenta_venta_del_catalogo(db_sri, "RET-RENTA-03-SRV")
    cuenta_iva = _cuenta_venta_del_catalogo(db_sri, "RET-IVA-70-SRV")
    lineas = _lineas_asiento(db_sri, fila["asiento_id"])

    assert _debe_de(lineas, cuenta_renta["codigo"]) == pytest.approx(120.00, abs=0.01)
    assert _debe_de(lineas, cuenta_iva["codigo"]) == pytest.approx(420.00, abs=0.01)
    assert _debe_de(lineas, "1.1.04") == pytest.approx(4060.00, abs=0.01)
    # El ingreso del servicio va a la cuenta de servicios (4.1.02)
    assert _haber_de(lineas, "4.1.02") == pytest.approx(4000.00, abs=0.01)
    assert _haber_de(lineas, "2.1.02") == pytest.approx(600.00, abs=0.01)
    assert _totales(lineas) == (4600.00, 4600.00)

    conn = _conexion(db_sri)
    try:
        cxc = conn.execute("""SELECT * FROM cuentas_cobrar WHERE tipo_origen = 'SERVICIO'
                              AND origen_id = ? ORDER BY id DESC LIMIT 1""", (tx_id,)).fetchone()
    finally:
        conn.close()
    assert cxc["monto_original"] == pytest.approx(4060.00, abs=0.01)


# ------------------------------------------------------------------ 3) SIN AGENTE DE RETENCIÓN
def test_venta_a_cliente_que_no_es_agente_no_practica_retencion(db_sri):
    """El comportamiento anterior queda intacto: sin retenciones y se cobra el total."""
    venta_id, _factura, total = _crear_venta(db_sri, TIPO_VENTA_SIN_RETENCION, agente=False,
                                             cliente_id=CLIENTE_COMUN)
    fila = _fila_venta(db_sri, venta_id)

    assert fila["total"] == pytest.approx(4600.00, abs=0.01)
    assert fila["cliente_agente_retencion"] == 0
    assert fila["retencion_renta_valor"] == pytest.approx(0.00, abs=0.01)
    assert fila["retencion_iva_valor"] == pytest.approx(0.00, abs=0.01)
    assert fila["total_retenciones"] == pytest.approx(0.00, abs=0.01)
    assert fila["neto_cobrar"] == pytest.approx(4600.00, abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    assert [l["codigo"] for l in lineas] == ["1.1.04", "4.1.01", "2.1.02"]
    assert _totales(lineas) == (4600.00, 4600.00)

    conn = _conexion(db_sri)
    try:
        cxc = conn.execute("""SELECT * FROM cuentas_cobrar WHERE numero_documento = ?""",
                           (fila["numero_factura"],)).fetchone()
    finally:
        conn.close()
    assert cxc["monto_original"] == pytest.approx(4600.00, abs=0.01)


def test_un_concepto_de_retencion_sin_agente_no_retiene(db_sri):
    """Elegir el concepto no basta: si el cliente no es agente de retención, no se retiene."""
    venta_id, _factura, _total = _crear_venta(db_sri, "BIENES", agente=False, cliente_id=CLIENTE_COMUN)
    fila = _fila_venta(db_sri, venta_id)

    assert fila["tipo_venta"] == "BIENES"
    assert fila["total_retenciones"] == pytest.approx(0.00, abs=0.01)
    assert fila["neto_cobrar"] == pytest.approx(4600.00, abs=0.01)


def test_la_venta_por_defecto_conserva_el_comportamiento_anterior(db_sri):
    """Sin indicar concepto ni agente, la venta se registra como antes (SIN_RETENCION)."""
    venta_id, _factura, total = SalesService.create_sale(
        1, CLIENTE_COMUN, [{"producto_id": PRODUCTO, "cantidad": 1, "precio_unitario": 1000.00}],
        forma_pago="CREDITO", dias_credito=30, fecha=FECHA, db_path=db_sri)
    fila = _fila_venta(db_sri, venta_id)

    assert total == pytest.approx(1150.00, abs=0.01)
    assert fila["tipo_venta"] == TIPO_VENTA_SIN_RETENCION
    assert fila["neto_cobrar"] == pytest.approx(1150.00, abs=0.01)
    assert fila["total_retenciones"] == pytest.approx(0.00, abs=0.01)
    assert _totales(_lineas_asiento(db_sri, fila["asiento_id"])) == (1150.00, 1150.00)


# ------------------------------------------------------------------ 4) CAJA Y BANCO
def test_la_venta_al_contado_del_neto_no_descuadra_la_caja(db_sri):
    """Se cobra el neto: el movimiento de caja coincide con el débito a Caja del asiento."""
    venta_id, factura, _total = _crear_venta(db_sri, "BIENES", agente=True, forma_pago="EFECTIVO")
    fila = _fila_venta(db_sri, venta_id)
    lineas = _lineas_asiento(db_sri, fila["asiento_id"])

    conn = _conexion(db_sri)
    try:
        movimiento = conn.execute("""SELECT * FROM movimientos_caja
                                     WHERE numero_comprobante = ? AND tipo_movimiento = 'INGRESO_VENTA'""",
                                  (factura,)).fetchone()
        caja = conn.execute("SELECT * FROM cajas WHERE id = 1").fetchone()
    finally:
        conn.close()

    assert movimiento is not None, "La venta al contado debe generar su movimiento de caja"
    assert round(movimiento["monto"], 2) == pytest.approx(4340.00, abs=0.01)
    assert _debe_de(lineas, "1.1.01") == pytest.approx(4340.00, abs=0.01)
    # El saldo de la caja es el saldo real del Libro Mayor (no se descuadra)
    assert caja["saldo_actual"] == pytest.approx(
        AccountingService.get_account_balance(3, db_path=db_sri), abs=0.01)


def test_la_venta_por_transferencia_del_neto_no_descuadra_el_banco(db_sri):
    venta_id, factura, _total = _crear_venta(db_sri, "BIENES", agente=True, forma_pago="TRANSFERENCIA")
    fila = _fila_venta(db_sri, venta_id)
    lineas = _lineas_asiento(db_sri, fila["asiento_id"])

    conn = _conexion(db_sri)
    try:
        movimiento = conn.execute("""SELECT * FROM movimientos_bancarios
                                     WHERE numero_referencia = ?""", (factura,)).fetchone()
        banco = conn.execute("SELECT * FROM bancos WHERE id = 1").fetchone()
    finally:
        conn.close()

    assert movimiento is not None
    assert round(movimiento["monto"], 2) == pytest.approx(4340.00, abs=0.01)
    assert _debe_de(lineas, "1.1.02") == pytest.approx(4340.00, abs=0.01)
    assert banco["saldo_actual"] == pytest.approx(
        AccountingService.get_account_balance(4, db_path=db_sri), abs=0.01)


# ------------------------------------------------------------------ 5) TODO CUADRA SIEMPRE
@pytest.mark.parametrize("clave", sorted(CONCEPTOS_VENTA_POR_CLAVE))
def test_el_asiento_siempre_cuadra_y_el_neto_es_el_correcto(db_sri, clave):
    """Para cualquier concepto: Total Debe = Total Haber y neto = factura − retenciones.

    Se comprueba además la REGLA DE BASES: la retención de Renta se aplica al valor de la venta
    y la retención de IVA al valor del IVA de la factura, con los porcentajes del catálogo.
    """
    venta_id, _factura, _total = _crear_venta(db_sri, clave, agente=True)
    fila = _fila_venta(db_sri, venta_id)

    assert fila["subtotal"] == pytest.approx(4000.00, abs=0.01)
    assert fila["iva_valor"] == pytest.approx(600.00, abs=0.01)
    assert fila["total"] == pytest.approx(4600.00, abs=0.01)

    renta_esperada = iva_esperada = 0.0
    if fila["retencion_renta_codigo"]:
        porcentaje = _porcentaje_del_catalogo(db_sri, fila["retencion_renta_codigo"])
        renta_esperada = round(fila["subtotal"] * porcentaje / 100.0, 2)
        assert fila["retencion_renta_porcentaje"] == pytest.approx(porcentaje)
    if fila["retencion_iva_codigo"]:
        porcentaje = _porcentaje_del_catalogo(db_sri, fila["retencion_iva_codigo"])
        iva_esperada = round(fila["iva_valor"] * porcentaje / 100.0, 2)
        assert fila["retencion_iva_porcentaje"] == pytest.approx(porcentaje)

    assert fila["retencion_renta_valor"] == pytest.approx(renta_esperada, abs=0.01)
    assert fila["retencion_iva_valor"] == pytest.approx(iva_esperada, abs=0.01)
    assert fila["total_retenciones"] == pytest.approx(round(renta_esperada + iva_esperada, 2), abs=0.01)
    assert fila["neto_cobrar"] == pytest.approx(
        round(4600.00 - renta_esperada - iva_esperada, 2), abs=0.01)

    lineas = _lineas_asiento(db_sri, fila["asiento_id"])
    total_debe, total_haber = _totales(lineas)
    assert total_debe == pytest.approx(total_haber, abs=0.01)
    assert total_debe == pytest.approx(4600.00, abs=0.01)
    assert _haber_de(lineas, "4.1.01") == pytest.approx(4000.00, abs=0.01)
    assert _haber_de(lineas, "2.1.02") == pytest.approx(600.00, abs=0.01)
    assert _debe_de(lineas, "1.1.04") == pytest.approx(fila["neto_cobrar"], abs=0.01)


def test_la_retencion_de_renta_se_aplica_al_valor_de_la_venta_sin_iva(db_sri):
    """La base de la retención de Renta es el valor de la venta, no el total de la factura."""
    desglose = SalesService.calcular_desglose_venta(
        VENTA_EJEMPLO, tipo_venta="BIENES", cliente_agente_retencion=True,
        cuenta_cobro_id=SalesService.cuenta_cobro_venta("CREDITO"), db_path=db_sri)

    assert desglose["retencion_renta"]["base"] == pytest.approx(4000.00, abs=0.01)
    assert desglose["retencion_iva"]["base"] == pytest.approx(600.00, abs=0.01)
    assert desglose["retencion_renta"]["valor"] == pytest.approx(80.00, abs=0.01)
    assert desglose["retencion_iva"]["valor"] == pytest.approx(180.00, abs=0.01)
    assert desglose["total_factura"] == pytest.approx(4600.00, abs=0.01)
    assert desglose["neto_cobrar"] == pytest.approx(4340.00, abs=0.01)
    assert _totales(desglose["lineas"]) == (4600.00, 4600.00)


def test_el_desglose_previo_coincide_con_lo_que_se_contabiliza(db_sri):
    """El desglose que usa la interfaz es el mismo que se guarda al registrar la venta."""
    desglose = SalesService.calcular_desglose_venta(
        VENTA_EJEMPLO, tipo_venta="BIENES", cliente_agente_retencion=True, db_path=db_sri)

    assert desglose["retencion_renta"]["cuenta_codigo"] == _cuenta_venta_del_catalogo(
        db_sri, "RET-RENTA-02-BIE")["codigo"]
    assert desglose["retencion_iva"]["cuenta_codigo"] == _cuenta_venta_del_catalogo(
        db_sri, "RET-IVA-30-BIE")["codigo"]

    venta_id, _factura, _total = _crear_venta(db_sri, "BIENES", agente=True)
    fila = _fila_venta(db_sri, venta_id)

    assert fila["neto_cobrar"] == pytest.approx(desglose["neto_cobrar"], abs=0.01)
    assert fila["retencion_renta_valor"] == pytest.approx(desglose["retencion_renta"]["valor"], abs=0.01)
    assert fila["retencion_iva_valor"] == pytest.approx(desglose["retencion_iva"]["valor"], abs=0.01)


def test_concepto_de_venta_desconocido_es_rechazado(db_sri):
    with pytest.raises(ValueError, match="Concepto de retención desconocido"):
        SalesService.calcular_desglose_venta(1000.00, tipo_venta="LO_QUE_SEA", db_path=db_sri)


def test_los_conceptos_se_ofrecen_con_los_porcentajes_y_cuentas_del_catalogo(db_sri):
    opciones = {o["clave"]: o for o in SalesService.listar_conceptos_retencion_venta(db_path=db_sri)}

    assert set(opciones) == set(CONCEPTOS_VENTA_POR_CLAVE)
    assert opciones["BIENES"]["renta"]["codigo"] == "RET-RENTA-02-BIE"
    assert opciones["BIENES"]["renta"]["porcentaje"] == pytest.approx(2.0)
    assert opciones["BIENES"]["iva"]["porcentaje"] == pytest.approx(30.0)
    assert opciones["SERVICIOS_MANO_OBRA"]["renta"]["porcentaje"] == pytest.approx(3.0)
    assert opciones["SERVICIOS_MANO_OBRA"]["iva"]["porcentaje"] == pytest.approx(70.0)
    # La cuenta del lado venta viene del catálogo (impuestos.cuenta_venta_id), no del código
    assert opciones["BIENES"]["renta"]["cuenta_codigo"] == _cuenta_venta_del_catalogo(
        db_sri, "RET-RENTA-02-BIE")["codigo"]
    assert opciones["BIENES"]["iva"]["cuenta_codigo"] == _cuenta_venta_del_catalogo(
        db_sri, "RET-IVA-30-BIE")["codigo"]
    assert opciones["RIMPE_NEGOCIO_POPULAR"]["iva"] is None
    assert opciones["SIN_RETENCION"]["renta"] is None
    assert all(o["disponible"] for o in opciones.values())


# ------------------------------------------------------------------ 6) INTERFAZ (rutas)
def test_el_formulario_de_venta_muestra_el_desglose_de_retenciones(db_sri, admin_client):
    respuesta = admin_client.get("/ventas/nueva")
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)

    for texto in ("Retención Renta", "Retención IVA", "Neto por cobrar al cliente",
                  "cliente_agente_retencion", 'name="tipo_venta"',
                  "RET-RENTA-02-BIE", "RET-IVA-30-BIE", "BIENES", "SERVICIOS_MANO_OBRA"):
        assert texto in html, f"Falta en el formulario: {texto}"


def test_vista_previa_del_desglose_responde_el_calculo_del_servicio(db_sri, admin_client):
    respuesta = admin_client.post("/ventas/desglose", data={
        "subtotal": "4000", "tipo_venta": "BIENES", "forma_pago": "CREDITO",
        "cliente_agente_retencion": "1",
    })
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["ok"] is True
    desglose = datos["desglose"]

    assert desglose["iva_valor"] == pytest.approx(600.00, abs=0.01)
    assert desglose["retencion_renta"]["valor"] == pytest.approx(80.00, abs=0.01)
    assert desglose["retencion_iva"]["valor"] == pytest.approx(180.00, abs=0.01)
    assert desglose["total_factura"] == pytest.approx(4600.00, abs=0.01)
    assert desglose["total_retenciones"] == pytest.approx(260.00, abs=0.01)
    assert desglose["neto_cobrar"] == pytest.approx(4340.00, abs=0.01)


def test_la_vista_previa_expone_los_campos_que_muestra_el_formulario(db_sri, admin_client):
    """Contrato entre el desglose y el JavaScript del formulario: todas las claves que la
    pantalla pinta antes de guardar deben venir en la respuesta."""
    respuesta = admin_client.post("/ventas/desglose", data={
        "subtotal": "4000", "tipo_venta": "BIENES", "forma_pago": "CREDITO",
        "cliente_agente_retencion": "1"})
    desglose = respuesta.get_json()["desglose"]

    for clave in ("subtotal", "iva_codigo", "iva_porcentaje", "iva_valor", "total_factura",
                  "total_retenciones", "neto_cobrar", "retencion_renta", "retencion_iva",
                  "cliente_agente_retencion", "concepto_etiqueta", "lineas"):
        assert clave in desglose, f"El desglose no expone {clave}"

    for clave in ("codigo", "porcentaje", "valor", "base", "cuenta_codigo"):
        assert clave in desglose["retencion_renta"], f"Falta {clave} en la retención de Renta"
        assert clave in desglose["retencion_iva"], f"Falta {clave} en la retención de IVA"

    for linea in desglose["lineas"]:
        for clave in ("cuenta_codigo", "cuenta_nombre", "debe", "haber", "referencia"):
            assert clave in linea, f"Falta {clave} en la línea del asiento"


def test_la_vista_previa_rechaza_un_subtotal_invalido(db_sri, admin_client):
    respuesta = admin_client.post("/ventas/desglose", data={
        "subtotal": "no-es-un-numero", "tipo_venta": "BIENES"})
    assert respuesta.status_code == 400
    assert respuesta.get_json()["ok"] is False


def test_la_vista_previa_sin_agente_de_retencion_no_retiene(db_sri, admin_client):
    respuesta = admin_client.post("/ventas/desglose", data={
        "subtotal": "4000", "tipo_venta": "BIENES", "forma_pago": "CREDITO",
        "cliente_agente_retencion": "0"})
    desglose = respuesta.get_json()["desglose"]

    assert desglose["retencion_renta"] is None
    assert desglose["retencion_iva"] is None
    assert desglose["total_retenciones"] == pytest.approx(0.00, abs=0.01)
    assert desglose["neto_cobrar"] == pytest.approx(4600.00, abs=0.01)


def test_el_script_del_formulario_usa_elementos_y_campos_que_existen(db_sri, admin_client):
    """El cálculo en pantalla (antes de guardar) sólo puede usar elementos y campos reales."""
    html = admin_client.get("/ventas/nueva").get_data(as_text=True)
    inicio = html.index("URL_DESGLOSE")
    script = html[inicio:html.index("</script>", inicio)]

    ids_script = set(re.findall(r'getElementById\("([A-Za-z0-9_]+)"\)', script))
    ids_pagina = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
    assert ids_script, "El formulario no calcula el desglose en pantalla"
    assert not (ids_script - ids_pagina), f"El script usa elementos inexistentes: {ids_script - ids_pagina}"

    claves_script = set(re.findall(r"\b[dD]\.([a-z_]+)", script))
    claves_script |= set(re.findall(r"\b(?:renta|riva|l)\.([a-z_]+)", script))
    desglose = admin_client.post("/ventas/desglose", data={
        "subtotal": "4000", "tipo_venta": "BIENES", "forma_pago": "CREDITO",
        "cliente_agente_retencion": "1"}).get_json()["desglose"]
    campos = set(desglose) | set(desglose["retencion_renta"]) | set(desglose["retencion_iva"])
    campos |= set(desglose["lineas"][0]) | set(desglose["iva_cuenta"]) | set(desglose["cuenta_cobro"])
    desconocidos = claves_script - campos
    assert not desconocidos, f"El script lee campos que el desglose no entrega: {desconocidos}"


def test_el_listado_de_ventas_muestra_las_retenciones_y_el_neto(db_sri, admin_client):
    venta_id, factura, _total = _crear_venta(db_sri, "BIENES", agente=True)
    respuesta = admin_client.get("/ventas")
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)

    cuenta_renta = _cuenta_venta_del_catalogo(db_sri, "RET-RENTA-02-BIE")
    cuenta_iva = _cuenta_venta_del_catalogo(db_sri, "RET-IVA-30-BIE")
    for texto in (factura, "Retención Renta", "Retención IVA", "Neto por cobrar",
                  "RET-RENTA-02-BIE", "RET-IVA-30-BIE",
                  "4,340.00", "4,600.00", cuenta_renta["codigo"], cuenta_iva["codigo"]):
        assert texto in html, f"Falta en el listado: {texto}"


def test_el_detalle_de_la_venta_muestra_el_desglose_y_el_asiento(db_sri, admin_client):
    venta_id, factura, _total = _crear_venta(db_sri, "BIENES", agente=True)
    respuesta = admin_client.get(f"/ventas/{venta_id}")
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)

    cuenta_renta = _cuenta_venta_del_catalogo(db_sri, "RET-RENTA-02-BIE")
    cuenta_iva = _cuenta_venta_del_catalogo(db_sri, "RET-IVA-30-BIE")
    for texto in (factura, "Retención Renta", "Retención IVA", "Neto por cobrar",
                  "RET-RENTA-02-BIE", "RET-IVA-30-BIE",
                  cuenta_renta["codigo"], cuenta_iva["codigo"],
                  "4,340.00", "4,600.00", "4,000.00", "600.00", "agente de retención"):
        assert texto in html, f"Falta en el detalle: {texto}"


def test_el_detalle_de_una_venta_sin_retencion_lo_indica(db_sri, admin_client):
    venta_id, _factura, _total = _crear_venta(db_sri, TIPO_VENTA_SIN_RETENCION, agente=False,
                                              cliente_id=CLIENTE_COMUN)
    html = admin_client.get(f"/ventas/{venta_id}").get_data(as_text=True)

    assert "no es agente de retención" in html
    assert "4,600.00" in html


def test_registrar_venta_desde_la_interfaz_guarda_y_contabiliza_las_retenciones(db_sri, admin_client):
    respuesta = admin_client.post("/ventas/nueva", data={
        "cliente_id": str(CLIENTE_AGENTE), "forma_pago": "CREDITO", "dias_credito": "30",
        "metodo_kardex": "PROMEDIO", "tipo_venta": "BIENES", "cliente_agente_retencion": "1",
        "producto_id[]": [str(PRODUCTO)], "cantidad[]": ["1"], "precio[]": ["4000.00"],
        "descuento[]": ["0"],
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)
    assert "emitida y contabilizada correctamente" in html
    assert "neto por cobrar $4,340.00" in html

    conn = _conexion(db_sri)
    try:
        fila = conn.execute("SELECT * FROM ventas ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()

    assert fila["tipo_venta"] == "BIENES"
    assert fila["cliente_agente_retencion"] == 1
    assert fila["retencion_renta_valor"] == pytest.approx(80.00, abs=0.01)
    assert fila["retencion_iva_valor"] == pytest.approx(180.00, abs=0.01)
    assert fila["neto_cobrar"] == pytest.approx(4340.00, abs=0.01)
    assert _totales(_lineas_asiento(db_sri, fila["asiento_id"])) == (4600.00, 4600.00)


def test_registrar_servicio_con_retencion_desde_la_interfaz(db_sri, admin_client):
    respuesta = admin_client.post("/servicios", data={
        "cliente_id": str(CLIENTE_AGENTE), "servicio_id": str(SERVICIO), "cantidad": "1",
        "tarifa": "4000", "descripcion": "Servicio con retención",
        "forma_pago": "CREDITO", "tipo_venta": "SERVICIOS_MANO_OBRA",
        "cliente_agente_retencion": "1",
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    assert "registrada y contabilizada" in respuesta.get_data(as_text=True)

    conn = _conexion(db_sri)
    try:
        fila = conn.execute("SELECT * FROM transacciones_servicios ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()

    assert fila["retencion_renta_valor"] == pytest.approx(120.00, abs=0.01)
    assert fila["retencion_iva_valor"] == pytest.approx(420.00, abs=0.01)
    assert fila["neto_cobrar"] == pytest.approx(4060.00, abs=0.01)
    assert _totales(_lineas_asiento(db_sri, fila["asiento_id"])) == (4600.00, 4600.00)


def test_el_formulario_de_servicios_ofrece_el_concepto_y_la_retencion(db_sri, admin_client):
    html = admin_client.get("/servicios").get_data(as_text=True)

    for texto in ("cliente_agente_retencion", 'name="tipo_venta"', "Retención Renta",
                  "Retención IVA", "Neto por cobrar al cliente"):
        assert texto in html, f"Falta en el formulario de servicios: {texto}"
