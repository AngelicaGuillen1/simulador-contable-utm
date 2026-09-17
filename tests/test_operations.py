"""Pruebas de los módulos operativos: ventas, servicios, compras, inventarios y tesorería."""
import pytest

from models import get_db_connection
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from services.sales_service import SalesService
from services.purchase_service import PurchaseService
from services.treasury_service import TreasuryService
from services.tax_service import TaxService
from tools.financial_tools import create_receivable, create_payable


def _stock(db, producto_id):
    return InventoryService.get_product(producto_id, db_path=db)["stock_actual"]


# ---------------------------------------------------------------- Inventarios
def test_compra_aumenta_stock_y_venta_lo_disminuye(db):
    stock_inicial = _stock(db, 12)

    PurchaseService.create_purchase(
        1, 3, "FAC-TEST-0001", [{"producto_id": 12, "cantidad": 20, "costo_unitario": 2.80}],
        forma_pago="TRANSFERENCIA", banco_id=1, fecha="2026-04-10", db_path=db
    )
    assert _stock(db, 12) == pytest.approx(stock_inicial + 20, abs=0.01)

    SalesService.create_sale(
        1, 3, [{"producto_id": 12, "cantidad": 5, "precio_unitario": 4.20}],
        forma_pago="EFECTIVO", fecha="2026-04-11", db_path=db
    )
    assert _stock(db, 12) == pytest.approx(stock_inicial + 15, abs=0.01)


def test_costo_promedio_ponderado_se_recalcula(db):
    producto_antes = InventoryService.get_product(2, db_path=db)
    costo_antes = producto_antes["costo_unitario"]
    stock_antes = producto_antes["stock_actual"]

    InventoryService.register_entry(2, 100, 2.10, fecha="2026-04-10", db_path=db)
    producto = InventoryService.get_product(2, db_path=db)
    esperado = round((stock_antes * costo_antes + 100 * 2.10) / (stock_antes + 100), 4)
    assert producto["costo_unitario"] == pytest.approx(esperado, abs=0.01)


def test_kardex_coincide_con_existencias_y_valor_de_inventario(db):
    """El saldo del Kardex debe coincidir con el stock y con la cuenta contable de inventario."""
    for producto in InventoryService.get_products(db_path=db):
        kardex = InventoryService.get_kardex(producto["id"], db_path=db)
        assert kardex["stock_final"] == pytest.approx(producto["stock_actual"], abs=0.01)

    conn = get_db_connection(db)
    try:
        valor_productos = conn.execute(
            "SELECT COALESCE(SUM(stock_actual * costo_unitario), 0) AS valor FROM productos"
        ).fetchone()["valor"]
    finally:
        conn.close()

    saldo_contable = AccountingService.get_account_balance(8, db_path=db)
    assert saldo_contable == pytest.approx(round(valor_productos, 2), abs=1.0)


def test_metodo_fifo_y_promedio_determinan_costo_de_venta(db):
    # Se ingresan dos lotes adicionales con costos distintos para el producto 19
    InventoryService.register_entry(19, 50, 1.00, fecha="2026-04-10", db_path=db)
    InventoryService.register_entry(19, 50, 2.00, fecha="2026-04-11", db_path=db)

    # Cálculo independiente del FIFO a partir de los lotes reales del Kardex
    conn = get_db_connection(db)
    try:
        lotes = conn.execute("""
            SELECT cantidad_restante, costo_unitario FROM kardex_lotes
            WHERE producto_id = 19 AND agotado = 0 AND cantidad_restante > 0
            ORDER BY fecha ASC, id ASC
        """).fetchall()
    finally:
        conn.close()

    pendiente, esperado_fifo = 60.0, 0.0
    for lote in lotes:
        consumir = min(pendiente, float(lote["cantidad_restante"]))
        esperado_fifo += consumir * float(lote["costo_unitario"])
        pendiente -= consumir
        if pendiente <= 0:
            break
    assert pendiente <= 0, "Los lotes deben cubrir las 60 unidades solicitadas"

    costo_fifo, _cu, _lotes = InventoryService.calculate_fifo_cost(19, 60, db_path=db)
    assert costo_fifo == pytest.approx(round(esperado_fifo, 2), abs=0.01)

    # Una venta bajo FIFO valoriza el costo con el lote más antiguo disponible
    costo_lote_antiguo = float(lotes[0]["costo_unitario"])
    sale_fifo = SalesService.create_sale(
        1, 3, [{"producto_id": 19, "cantidad": 10, "precio_unitario": 2.50}],
        forma_pago="EFECTIVO", metodo_kardex="FIFO", fecha="2026-04-12", db_path=db
    )
    venta = SalesService.get_sale_by_id(sale_fifo[0], db_path=db)
    assert venta["costo_ventas_total"] == pytest.approx(10 * costo_lote_antiguo, abs=0.01)

    # Bajo promedio ponderado el costo unitario es el costo promedio del producto
    producto = InventoryService.get_product(19, db_path=db)
    sale_prom = SalesService.create_sale(
        1, 3, [{"producto_id": 19, "cantidad": 10, "precio_unitario": 2.50}],
        forma_pago="EFECTIVO", metodo_kardex="PROMEDIO", fecha="2026-04-13", db_path=db
    )
    venta_prom = SalesService.get_sale_by_id(sale_prom[0], db_path=db)
    assert venta_prom["costo_ventas_total"] == pytest.approx(
        round(10 * producto["costo_unitario"], 2), abs=0.01)


def test_stock_insuficiente_impide_la_venta(db):
    producto = InventoryService.get_product(1, db_path=db)
    with pytest.raises(ValueError, match="Stock insuficiente"):
        SalesService.create_sale(
            1, 3, [{"producto_id": 1, "cantidad": producto["stock_actual"] + 1, "precio_unitario": 5.20}],
            forma_pago="EFECTIVO", fecha="2026-04-14", db_path=db
        )


def test_cantidad_invalida_impide_el_registro(db):
    with pytest.raises(ValueError):
        InventoryService.register_entry(1, 0, 3.80, db_path=db)
    with pytest.raises(ValueError):
        InventoryService.register_exit(1, -5, db_path=db)


# ---------------------------------------------------------------- Ventas
def test_venta_de_contado_integra_caja_documento_y_asientos(db):
    saldo_caja_antes = AccountingService.get_account_balance(3, db_path=db)

    venta_id, numero, total = SalesService.create_sale(
        1, 3, [{"producto_id": 20, "cantidad": 10, "precio_unitario": 1.50}],
        forma_pago="EFECTIVO", fecha="2026-04-15", db_path=db
    )
    venta = SalesService.get_sale_by_id(venta_id, db_path=db)

    # La venta tiene asiento de ingreso y asiento de costo
    assert venta["asiento_id"] and venta["asiento_costo_id"]
    assert venta["total"] == pytest.approx(10 * 1.50 * 1.15, abs=0.02)
    assert venta["iva_valor"] == pytest.approx(10 * 1.50 * 0.15, abs=0.02)

    # Caja aumenta por el total facturado
    assert AccountingService.get_account_balance(3, db_path=db) == pytest.approx(
        saldo_caja_antes + venta["total"], abs=0.02)

    conn = get_db_connection(db)
    try:
        movimientos = conn.execute("""
            SELECT COUNT(*) as cnt FROM movimientos_caja
            WHERE asiento_id = ? AND tipo_movimiento = 'INGRESO_VENTA'
        """, (venta["asiento_id"],)).fetchone()["cnt"]
        documento = conn.execute("""
            SELECT COUNT(*) as cnt FROM documentos_fuente
            WHERE tipo = 'FACTURA_VENTA' AND numero = ? AND asiento_id = ?
        """, (numero, venta["asiento_id"])).fetchone()["cnt"]
        costo_mov = conn.execute("""
            SELECT COUNT(*) as cnt FROM movimientos_inventario
            WHERE numero_documento = ? AND tipo_movimiento = 'SALIDA_VENTA'
        """, (numero,)).fetchone()["cnt"]
    finally:
        conn.close()

    assert movimientos == 1, "La venta de contado debe generar un movimiento de caja"
    assert documento == 1, "La venta debe generar su documento fuente (factura)"
    assert costo_mov == 1, "La venta debe generar la salida de inventario (Kardex)"


def test_venta_a_credito_genera_cuenta_por_cobrar(db):
    conn = get_db_connection(db)
    try:
        cxc_antes = conn.execute("SELECT COUNT(*) as cnt FROM cuentas_cobrar").fetchone()["cnt"]
        saldo_cliente_antes = conn.execute(
            "SELECT saldo_pendiente FROM clientes WHERE id = 6").fetchone()["saldo_pendiente"]
    finally:
        conn.close()

    venta_id, numero, total = SalesService.create_sale(
        1, 6, [{"producto_id": 13, "cantidad": 20, "precio_unitario": 1.65}],
        forma_pago="CREDITO", dias_credito=30, fecha="2026-04-16", db_path=db
    )

    conn = get_db_connection(db)
    try:
        cxc = conn.execute("""
            SELECT * FROM cuentas_cobrar WHERE numero_documento = ? ORDER BY id DESC LIMIT 1
        """, (numero,)).fetchone()
        cxc_despues = conn.execute("SELECT COUNT(*) as cnt FROM cuentas_cobrar").fetchone()["cnt"]
        saldo_cliente = conn.execute(
            "SELECT saldo_pendiente FROM clientes WHERE id = 6").fetchone()["saldo_pendiente"]
    finally:
        conn.close()

    assert cxc_despues == cxc_antes + 1
    assert cxc["monto_original"] == pytest.approx(total, abs=0.01)
    assert cxc["saldo_actual"] == pytest.approx(total, abs=0.01)
    assert cxc["estado"] == "PENDIENTE"
    assert cxc["fecha_vencimiento"] > cxc["fecha_emision"]
    assert saldo_cliente == pytest.approx(saldo_cliente_antes + total, abs=0.01)


def test_cobro_reduce_cartera_y_aumenta_el_banco(db):
    _venta_id, numero, total = SalesService.create_sale(
        1, 6, [{"producto_id": 13, "cantidad": 100, "precio_unitario": 1.65}],
        forma_pago="CREDITO", dias_credito=30, fecha="2026-04-17", db_path=db
    )
    conn = get_db_connection(db)
    try:
        cxc = conn.execute("SELECT * FROM cuentas_cobrar WHERE numero_documento = ?", (numero,)).fetchone()
    finally:
        conn.close()

    monto_cobro = 100.00
    banco_antes = AccountingService.get_account_balance(4, db_path=db)
    cobro_id, nuevo_saldo, estado = SalesService.register_collection(
        cxc["id"], monto_cobro, medio_pago="TRANSFERENCIA", banco_id=1,
        numero_comprobante="CI-TEST-001", fecha="2026-04-18", db_path=db
    )

    assert nuevo_saldo == pytest.approx(cxc["saldo_actual"] - monto_cobro, abs=0.01)
    assert estado == "PARCIAL"
    assert AccountingService.get_account_balance(4, db_path=db) == pytest.approx(banco_antes + monto_cobro, abs=0.02)


def test_no_se_puede_cobrar_mas_que_el_saldo(db):
    conn = get_db_connection(db)
    try:
        cxc = conn.execute(
            "SELECT * FROM cuentas_cobrar WHERE estado IN ('PENDIENTE','PARCIAL') ORDER BY id LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    with pytest.raises(ValueError, match="no puede ser mayor al saldo"):
        SalesService.register_collection(cxc["id"], cxc["saldo_actual"] + 500, db_path=db)


def test_servicio_registra_ingreso_en_cuenta_de_servicios(db):
    ingreso_servicios_antes = AccountingService.get_account_balance(32, db_path=db)
    srv_id, numero, total = SalesService.create_service_transaction(
        1, 3, 1, cantidad=2, tarifa=45.0, forma_pago="TRANSFERENCIA", banco_id=1,
        descripcion="Servicio de prueba", fecha="2026-04-19", db_path=db
    )
    assert AccountingService.get_account_balance(32, db_path=db) == pytest.approx(
        ingreso_servicios_antes + 90.00, abs=0.02)

    conn = get_db_connection(db)
    try:
        tx = conn.execute("SELECT * FROM transacciones_servicios WHERE id = ?", (srv_id,)).fetchone()
    finally:
        conn.close()
    assert tx["total"] == pytest.approx(103.50, abs=0.02)
    assert tx["asiento_id"] is not None


def test_venta_con_cliente_invalido_es_rechazada(db):
    with pytest.raises(ValueError, match="Cliente no encontrado"):
        SalesService.create_sale(
            1, 9999, [{"producto_id": 1, "cantidad": 1, "precio_unitario": 5.20}],
            forma_pago="EFECTIVO", fecha="2026-04-20", db_path=db
        )


# ---------------------------------------------------------------- Compras
def test_compra_a_credito_genera_cuenta_por_pagar_y_stock(db):
    stock_antes = _stock(db, 9)
    conn = get_db_connection(db)
    try:
        cxp_antes = conn.execute("SELECT COUNT(*) as cnt FROM cuentas_pagar").fetchone()["cnt"]
    finally:
        conn.close()

    compra_id, factura, total = PurchaseService.create_purchase(
        1, 3, "FAC-TEST-0099", [{"producto_id": 9, "cantidad": 50, "costo_unitario": 1.10}],
        forma_pago="CREDITO", dias_credito=30, fecha="2026-04-20", db_path=db
    )

    assert _stock(db, 9) == pytest.approx(stock_antes + 50, abs=0.01)

    conn = get_db_connection(db)
    try:
        cxp = conn.execute("SELECT * FROM cuentas_pagar WHERE numero_factura = ?", (factura,)).fetchone()
        cxp_despues = conn.execute("SELECT COUNT(*) as cnt FROM cuentas_pagar").fetchone()["cnt"]
        documento = conn.execute("""
            SELECT COUNT(*) as cnt FROM documentos_fuente WHERE tipo = 'FACTURA_COMPRA' AND numero = ?
        """, (factura,)).fetchone()["cnt"]
    finally:
        conn.close()

    assert cxp_despues == cxp_antes + 1
    assert cxp["saldo_actual"] == pytest.approx(total, abs=0.01)
    assert documento == 1


def test_pago_a_proveedor_reduce_la_obligacion(db):
    _compra_id, factura, total = PurchaseService.create_purchase(
        1, 3, "FAC-TEST-0100", [{"producto_id": 9, "cantidad": 10, "costo_unitario": 1.10}],
        forma_pago="CREDITO", dias_credito=30, fecha="2026-04-21", db_path=db
    )
    conn = get_db_connection(db)
    try:
        cxp = conn.execute("SELECT * FROM cuentas_pagar WHERE numero_factura = ?", (factura,)).fetchone()
    finally:
        conn.close()

    banco_antes = AccountingService.get_account_balance(4, db_path=db)
    pago_id, nuevo_saldo, estado = PurchaseService.register_payment(
        cxp["id"], total, medio_pago="TRANSFERENCIA", banco_id=1,
        numero_comprobante="CE-TEST-001", fecha="2026-04-22", db_path=db
    )
    assert nuevo_saldo == pytest.approx(0.0, abs=0.01)
    assert estado == "PAGADA"
    assert AccountingService.get_account_balance(4, db_path=db) == pytest.approx(banco_antes - total, abs=0.02)


def test_compra_a_proveedor_invalido_es_rechazada(db):
    with pytest.raises(ValueError, match="Proveedor no encontrado"):
        PurchaseService.create_purchase(
            1, 999, "FAC-X", [{"producto_id": 1, "cantidad": 1, "costo_unitario": 3.80}], db_path=db
        )


def test_herramientas_estructuradas_de_cartera(db):
    """create_receivable / create_payable (herramientas de agentes) mantienen la coherencia."""
    conn = get_db_connection(db)
    try:
        saldo_cliente_antes = conn.execute("SELECT saldo_pendiente FROM clientes WHERE id = 9").fetchone()["saldo_pendiente"]
    finally:
        conn.close()

    res = create_receivable(9, 250.00, "DOC-TEST-001", "2026-04-20", "2026-05-20", db_path=db)
    assert res["saldo"] == 250.00

    conn = get_db_connection(db)
    try:
        saldo_cliente = conn.execute("SELECT saldo_pendiente FROM clientes WHERE id = 9").fetchone()["saldo_pendiente"]
    finally:
        conn.close()
    assert saldo_cliente == pytest.approx(saldo_cliente_antes + 250.00, abs=0.01)

    with pytest.raises(ValueError):
        create_payable(999, 100.0, "X", "2026-04-20", "2026-05-20", db_path=db)
    with pytest.raises(ValueError):
        create_receivable(9, -10.0, "DOC-TEST-002", "2026-04-20", "2026-05-20", db_path=db)


# ---------------------------------------------------------------- Tesorería
def test_arqueo_de_caja_detecta_faltante_o_sobrante(db):
    saldo_contable = AccountingService.get_account_balance(3, db_path=db)
    resultado = TreasuryService.perform_cash_count(
        1, round(saldo_contable - 12.50, 2), observaciones="Prueba de arqueo", fecha="2026-04-25", db_path=db
    )
    assert resultado["diferencia"] == pytest.approx(-12.50, abs=0.01)
    assert resultado["estado"] == "FALTANTE"

    resultado2 = TreasuryService.perform_cash_count(
        1, round(saldo_contable + 3.00, 2), observaciones="Prueba de sobrante", fecha="2026-04-25", db_path=db
    )
    assert resultado2["diferencia"] == pytest.approx(3.00, abs=0.01)
    assert resultado2["estado"] == "SOBRANTE"


def test_saldos_de_tesoreria_se_sincronizan_con_el_libro_mayor(db):
    TreasuryService.sync_cash_balance(1, db_path=db)
    TreasuryService.sync_bank_balance(1, db_path=db)
    TreasuryService.sync_bank_balance(2, db_path=db)

    cajas = {c["id"]: c for c in TreasuryService.get_cash_boxes(db_path=db)}
    bancos = {b["id"]: b for b in TreasuryService.get_banks(db_path=db)}

    assert cajas[1]["saldo_actual"] == pytest.approx(AccountingService.get_account_balance(3, db_path=db), abs=0.01)
    assert bancos[1]["saldo_actual"] == pytest.approx(AccountingService.get_account_balance(4, db_path=db), abs=0.01)
    assert bancos[2]["saldo_actual"] == pytest.approx(AccountingService.get_account_balance(5, db_path=db), abs=0.01)


def test_conciliacion_bancaria_detecta_diferencias(db):
    banco = TreasuryService.get_banks(db_path=db)[0]
    saldo_libros = banco["saldo_contable_real"]

    conciliado = TreasuryService.perform_bank_reconciliation(
        1, 1, "2026-04-30", saldo_libros, observaciones="Conciliación exacta", db_path=db)

    assert conciliado["conciliado"] is True
    assert conciliado["diferencia"] == pytest.approx(0.0, abs=0.05)

    con_diferencia = TreasuryService.perform_bank_reconciliation(
        1, 1, "2026-04-30", saldo_libros - 500.00, observaciones="Diferencia de prueba", db_path=db)
    assert con_diferencia["conciliado"] is False
    assert con_diferencia["diferencia"] == pytest.approx(500.00, abs=0.05)


def test_movimientos_de_caja_y_banco_quedan_registrados(db):
    caja_id = TreasuryService.register_cash_movement(
        1, "INGRESO", 100.00, "Ingreso de prueba", numero_comprobante="CI-TEST-99", fecha="2026-04-26", db_path=db)
    banco_id = TreasuryService.register_bank_movement(
        1, "DEPOSITO", 200.00, "Depósito de prueba", numero_referencia="DEP-TEST-99", fecha="2026-04-26", db_path=db)
    assert caja_id > 0 and banco_id > 0

    with pytest.raises(ValueError):
        TreasuryService.register_cash_movement(1, "INGRESO", 0, "Monto inválido", db_path=db)
    with pytest.raises(ValueError):
        TreasuryService.register_bank_movement(1, "DEPOSITO", -5, "Monto inválido", db_path=db)


# ---------------------------------------------------------------- Impuestos
def test_calculo_de_iva_usa_la_configuracion_del_sistema(db):
    calculo = TaxService.calculate_tax(100.00, tipo="IVA_VENTAS", db_path=db)
    assert calculo["porcentaje"] == 15.0
    assert calculo["valor"] == pytest.approx(15.00, abs=0.01)
    assert calculo["total"] == pytest.approx(115.00, abs=0.01)


def test_no_se_inventan_tasas_inexistentes(db):
    with pytest.raises(ValueError):
        TaxService.calculate_tax(100.00, codigo_impuesto="NO-EXISTE", db_path=db)
    with pytest.raises(ValueError):
        TaxService.calculate_tax(100.0, tipo="TIPO_INEXISTENTE", db_path=db)


def test_retenciones_configuradas_disponibles(db):
    codigos = {i["codigo"] for i in TaxService.get_taxes(db_path=db)}
    for esperado in ["IVA-15-VTA", "IVA-15-COM", "RET-FTE-BIE", "RET-FTE-SRV"]:
        assert esperado in codigos
