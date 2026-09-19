# Structured Agent Tools - Operations, Treasury, Taxes & Financial Statements
from services.sales_service import SalesService
from services.purchase_service import PurchaseService
from services.treasury_service import TreasuryService
from services.tax_service import TaxService
from services.accounting_service import AccountingService
from models import get_db_contable

def create_sale(empresa_id, cliente_id, items, forma_pago="EFECTIVO", banco_id=None, dias_credito=0, usuario_id=1, fecha=None, db_path=None):
    """Executes atomic sale with inventory deduction, COGS and auto-journaling."""
    venta_id, num_fac, total = SalesService.create_sale(
        empresa_id, int(cliente_id), items, forma_pago=forma_pago,
        banco_id=banco_id, dias_credito=dias_credito, usuario_id=usuario_id, fecha=fecha, db_path=db_path
    )
    return {"venta_id": venta_id, "numero_factura": num_fac, "total": total}

def create_purchase(empresa_id, proveedor_id, numero_factura, items, forma_pago="EFECTIVO", banco_id=None, dias_credito=0, usuario_id=1, fecha=None, db_path=None):
    """Executes atomic purchase with stock intake and auto-journaling."""
    compra_id, num_fac, total = PurchaseService.create_purchase(
        empresa_id, int(proveedor_id), numero_factura, items, forma_pago=forma_pago,
        banco_id=banco_id, dias_credito=dias_credito, usuario_id=usuario_id, fecha=fecha, db_path=db_path
    )
    return {"compra_id": compra_id, "numero_factura": num_fac, "total": total}

def create_service_transaction(empresa_id, cliente_id, servicio_id, cantidad=1.0, tarifa=None, descripcion="", forma_pago="EFECTIVO", banco_id=None, dias_credito=0, usuario_id=1, fecha=None, db_path=None):
    """Executes atomic service transaction with service revenue auto-journaling."""
    srv_id, num_fac, total = SalesService.create_service_transaction(
        empresa_id, int(cliente_id), int(servicio_id), cantidad=float(cantidad),
        tarifa=tarifa, descripcion=descripcion, forma_pago=forma_pago,
        banco_id=banco_id, dias_credito=dias_credito, usuario_id=usuario_id, fecha=fecha, db_path=db_path
    )
    return {"servicio_tx_id": srv_id, "numero_factura": num_fac, "total": total}

def register_collection(cuenta_cobrar_id, monto, medio_pago="EFECTIVO", caja_id=1, banco_id=1, numero_comprobante="", usuario_id=1, fecha=None, db_path=None):
    """Registers customer debt collection and deposits funds."""
    cobro_id, nuevo_saldo, estado = SalesService.register_collection(
        int(cuenta_cobrar_id), float(monto), medio_pago=medio_pago,
        caja_id=caja_id, banco_id=banco_id, numero_comprobante=numero_comprobante,
        usuario_id=usuario_id, fecha=fecha, db_path=db_path
    )
    return {"cobro_id": cobro_id, "saldo_restante": nuevo_saldo, "estado": estado}

def register_payment(cuenta_pagar_id, monto, medio_pago="TRANSFERENCIA", caja_id=1, banco_id=1, numero_comprobante="", usuario_id=1, fecha=None, db_path=None):
    """Registers supplier debt payment and disburses funds."""
    pago_id, nuevo_saldo, estado = PurchaseService.register_payment(
        int(cuenta_pagar_id), float(monto), medio_pago=medio_pago,
        caja_id=caja_id, banco_id=banco_id, numero_comprobante=numero_comprobante,
        usuario_id=usuario_id, fecha=fecha, db_path=db_path
    )
    return {"pago_id": pago_id, "saldo_restante": nuevo_saldo, "estado": estado}

def create_receivable(cliente_id, monto, numero_documento, fecha_emision, fecha_vencimiento,
                      tipo_origen="VENTA_PRODUCTOS", origen_id=0, crear_asiento=False, usuario_id=1, db_path=None):
    """
    Registra un documento por cobrar (control de cartera) para un cliente.
    Por defecto NO contabiliza (crear_asiento=False) para evitar duplicar un ingreso ya registrado
    por create_sale o create_service_transaction. Si crear_asiento=True genera el asiento
    Debe 1.1.04 Cuentas por Cobrar / Haber 4.1.01 Ingresos por Ventas.
    """
    AccountingService_instance = AccountingService
    conn = get_db_contable(db_path)
    try:
        cliente = conn.execute("SELECT * FROM clientes WHERE id = ?", (int(cliente_id),)).fetchone()
        if not cliente:
            raise ValueError("Cliente no encontrado.")
        if float(monto) <= 0:
            raise ValueError("El monto del documento por cobrar debe ser mayor a 0.")

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cuentas_cobrar (cliente_id, tipo_origen, origen_id, numero_documento,
                                        fecha_emision, fecha_vencimiento, monto_original, saldo_actual, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
        """, (int(cliente_id), tipo_origen, int(origen_id or 0), numero_documento,
              fecha_emision, fecha_vencimiento, float(monto), float(monto)))
        cxc_id = cursor.lastrowid
        cursor.execute("UPDATE clientes SET saldo_pendiente = saldo_pendiente + ? WHERE id = ?",
                       (float(monto), int(cliente_id)))
        conn.commit()

        asiento_id = None
        if crear_asiento:
            asiento_id, _num = AccountingService_instance.create_journal_entry(
                1, fecha_emision, f"Documento por cobrar {numero_documento} a {cliente['nombre_razon_social']}",
                [
                    {"cuenta_id": 6, "debe": float(monto), "haber": 0.0, "referencia": numero_documento},
                    {"cuenta_id": 31, "debe": 0.0, "haber": float(monto), "referencia": numero_documento},
                ],
                tipo_documento="DOCUMENTO_POR_COBRAR", numero_documento=numero_documento,
                origen_modulo="CARTERA", usuario_id=usuario_id, db_path=db_path
            )
        return {"cuenta_cobrar_id": cxc_id, "saldo": float(monto), "estado": "PENDIENTE", "asiento_id": asiento_id}
    finally:
        conn.close()

def create_payable(proveedor_id, monto, numero_factura, fecha_emision, fecha_vencimiento,
                   compra_id=None, crear_asiento=False, usuario_id=1, db_path=None):
    """
    Registra una obligación por pagar (control de proveedores).
    Por defecto NO contabiliza (crear_asiento=False) para evitar duplicar una compra ya registrada
    por create_purchase. Si crear_asiento=True genera el asiento
    Debe 1.1.06 Inventario / Haber 2.1.01 Cuentas por Pagar Proveedores.
    """
    conn = get_db_contable(db_path)
    try:
        prov = conn.execute("SELECT * FROM proveedores WHERE id = ?", (int(proveedor_id),)).fetchone()
        if not prov:
            raise ValueError("Proveedor no encontrado.")
        if float(monto) <= 0:
            raise ValueError("El monto de la obligación por pagar debe ser mayor a 0.")

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cuentas_pagar (proveedor_id, compra_id, numero_factura, fecha_emision, fecha_vencimiento,
                                       monto_original, saldo_actual, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
        """, (int(proveedor_id), int(compra_id) if compra_id else None, numero_factura, fecha_emision, fecha_vencimiento,
              float(monto), float(monto)))
        cxp_id = cursor.lastrowid
        cursor.execute("UPDATE proveedores SET saldo_pendiente = saldo_pendiente + ? WHERE id = ?",
                       (float(monto), int(proveedor_id)))
        conn.commit()

        asiento_id = None
        if crear_asiento:
            asiento_id, _num = AccountingService.create_journal_entry(
                1, fecha_emision, f"Obligación por pagar factura {numero_factura} de {prov['razon_social']}",
                [
                    {"cuenta_id": 8, "debe": float(monto), "haber": 0.0, "referencia": numero_factura},
                    {"cuenta_id": 20, "debe": 0.0, "haber": float(monto), "referencia": numero_factura},
                ],
                tipo_documento="DOCUMENTO_POR_PAGAR", numero_documento=numero_factura,
                origen_modulo="PROVEEDORES", usuario_id=usuario_id, db_path=db_path
            )
        return {"cuenta_pagar_id": cxp_id, "saldo": float(monto), "estado": "PENDIENTE", "asiento_id": asiento_id}
    finally:
        conn.close()

def get_customer_balance(cliente_id, db_path=None):
    """Retrieves customer details, credit limit and outstanding balance."""
    conn = get_db_contable(db_path)
    try:
        c = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
        return dict(c) if c else None
    finally:
        conn.close()

def get_supplier_balance(proveedor_id, db_path=None):
    """Retrieves supplier details and outstanding payables."""
    conn = get_db_contable(db_path)
    try:
        p = conn.execute("SELECT * FROM proveedores WHERE id = ?", (proveedor_id,)).fetchone()
        return dict(p) if p else None
    finally:
        conn.close()

def get_cash_balance(caja_id=1, db_path=None):
    """Retrieves live balance for a cash box."""
    cajas = TreasuryService.get_cash_boxes(db_path=db_path)
    for c in cajas:
        if c["id"] == int(caja_id):
            return c
    return None

def get_bank_balance(banco_id=1, db_path=None):
    """Retrieves live ledger balance for a bank account."""
    bancos = TreasuryService.get_banks(db_path=db_path)
    for b in bancos:
        if b["id"] == int(banco_id):
            return b
    return None

def reconcile_bank(banco_id, periodo_id, fecha_corte, saldo_extracto, depositos_transito=0.0, cheques_transito=0.0, notas_debito=0.0, notas_credito=0.0, observaciones="", usuario_id=1, db_path=None):
    """Executes bank reconciliation matching bank statement with accounting records."""
    return TreasuryService.perform_bank_reconciliation(
        int(banco_id), int(periodo_id), fecha_corte, float(saldo_extracto),
        depositos_transito=float(depositos_transito), cheques_transito=float(cheques_transito),
        notas_debito=float(notas_debito), notas_credito=float(notas_credito),
        observaciones=observaciones, usuario_id=usuario_id, db_path=db_path
    )

def get_tax_configuration(db_path=None):
    """Retrieves active tax parameters (IVA and withholdings)."""
    return TaxService.get_taxes(db_path=db_path)

def calculate_tax(base_imponible, codigo_impuesto=None, tipo="IVA_VENTAS", db_path=None):
    """Calculates tax amount for a tax base using system configuration."""
    return TaxService.calculate_tax(float(base_imponible), codigo_impuesto=codigo_impuesto, tipo=tipo, db_path=db_path)

def generate_trial_balance(fecha_corte=None, db_path=None):
    """Generates 4-column Trial Balance with debits/credits and debtor/creditor balances."""
    return AccountingService.get_trial_balance(fecha_corte=fecha_corte, db_path=db_path)

def generate_income_statement(fecha_inicio=None, fecha_fin=None, db_path=None):
    """Generates Income Statement (Estado de Resultados) with Gross Margin and Net Income."""
    return AccountingService.get_income_statement(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, db_path=db_path)

def generate_balance_sheet(fecha_corte=None, db_path=None):
    """Generates Balance Sheet (Estado de Situación Financiera) and checks Assets = Liabilities + Equity."""
    return AccountingService.get_balance_sheet(fecha_corte=fecha_corte, db_path=db_path)

def generate_cash_flow(db_path=None):
    """Generates Cash Flow statement categorized by Operation, Investment, and Financing."""
    return AccountingService.get_cash_flow_statement(db_path=db_path)
