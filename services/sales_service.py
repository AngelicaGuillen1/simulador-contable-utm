# Sales (Commercial Goods & Services) Engine & Receivables Integration
import sqlite3
from datetime import datetime, date, timedelta
from models import get_db_connection
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from services.tax_service import TaxService
from services.audit_service import AuditService
from services.period_service import PeriodService
from services.treasury_service import TreasuryService
from services.document_service import DocumentService

class SalesService:
    @staticmethod
    def get_sales(empresa_id=1, limit=100, db_path=None):
        conn = get_db_connection(db_path)
        try:
            rows = conn.execute("""
                SELECT v.*, c.nombre_razon_social as cliente_nombre, c.identificacion as cliente_ruc
                FROM ventas v
                JOIN clientes c ON v.cliente_id = c.id
                WHERE v.empresa_id = ?
                ORDER BY v.id DESC LIMIT ?
            """, (empresa_id, limit)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_sale_by_id(venta_id, db_path=None):
        conn = get_db_connection(db_path)
        try:
            v = conn.execute("""
                SELECT v.*, c.nombre_razon_social as cliente_nombre, c.identificacion as cliente_ruc, c.direccion as cliente_direccion
                FROM ventas v
                JOIN clientes c ON v.cliente_id = c.id
                WHERE v.id = ?
            """, (venta_id,)).fetchone()
            if not v:
                return None
            v_dict = dict(v)
            det = conn.execute("""
                SELECT d.*, p.codigo as producto_codigo, p.descripcion as producto_nombre
                FROM detalle_ventas d
                JOIN productos p ON d.producto_id = p.id
                WHERE d.venta_id = ?
            """, (venta_id,)).fetchall()
            v_dict["detalles"] = [dict(d) for d in det]
            return v_dict
        finally:
            conn.close()

    @staticmethod
    def create_sale(empresa_id, cliente_id, items, forma_pago="EFECTIVO", banco_id=None, caja_id=1, dias_credito=0, usuario_id=1, metodo_kardex="PROMEDIO", fecha=None, db_path=None):
        """
        Executes atomic sale:
        1. Validates stock for all items
        2. Calculates subtotals, configurable IVA, and Cost of Goods Sold
        3. Inserts sale & detail records
        4. Decrements inventory with Kardex entries
        5. Generates Accounts Receivable if forma_pago == 'CREDITO'
        6. Generates Sales Journal Entry (Cash/Bank/Receivable -> Sales Revenue + IVA Fiscal)
        7. Generates COGS Journal Entry (Cost of Goods Sold -> Inventory)
        8. Logs audit
        """
        if not items:
            raise ValueError("La venta debe contener al menos un producto.")

        conn = get_db_connection(db_path)
        try:
            cursor = conn.cursor()
            cliente = cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
            if not cliente:
                raise ValueError("Cliente no encontrado.")

            subtotal_total = 0.0
            costo_ventas_total = 0.0
            items_procesados = []

            # 1. Validate and calculate items
            for it in items:
                p_id = it["producto_id"]
                cant = float(it["cantidad"])
                p_unit = float(it.get("precio_unitario", 0.0))
                desc = float(it.get("descuento", 0.0))

                p = cursor.execute("SELECT * FROM productos WHERE id = ?", (p_id,)).fetchone()
                if not p:
                    raise ValueError(f"Producto ID {p_id} no existe.")
                if p["stock_actual"] < cant:
                    raise ValueError(f"Stock insuficiente para '{p['descripcion']}'. Existencias: {p['stock_actual']}, solicitadas: {cant}.")

                if p_unit <= 0:
                    p_unit = float(p["precio_venta"])

                sub_item = round((cant * p_unit) - desc, 2)
                subtotal_total += sub_item

                # Calculate item cost
                if metodo_kardex == "FIFO":
                    costo_item, cu_costo, _ = InventoryService.calculate_fifo_cost(p_id, cant, db_path=db_path)
                else:
                    cu_costo = float(p["costo_unitario"])
                    costo_item = round(cant * cu_costo, 2)

                costo_ventas_total += costo_item

                items_procesados.append({
                    "producto_id": p_id,
                    "cantidad": cant,
                    "precio_unitario": p_unit,
                    "descuento": desc,
                    "subtotal": sub_item,
                    "costo_unitario_venta": cu_costo,
                    "costo_total_venta": costo_item
                })

            # 2. Taxes
            tax_calc = TaxService.calculate_tax(subtotal_total, tipo="IVA_VENTAS", db_path=db_path)
            iva_valor = tax_calc["valor"]
            iva_porcentaje = tax_calc["porcentaje"]
            total_factura = round(subtotal_total + iva_valor, 2)

            # Invoice Number
            max_v = cursor.execute("SELECT MAX(id) as max_id FROM ventas").fetchone()
            next_seq = (max_v["max_id"] or 0) + 101
            num_factura = f"FAC-001-001-{next_seq:06d}"

            fecha_hoy = fecha or PeriodService.get_fecha_trabajo(db_path=db_path)
            valido, msg_fecha = PeriodService.is_fecha_valida(fecha_hoy, db_path=db_path)
            if not valido:
                raise ValueError(msg_fecha)
            fecha_venc = (datetime.strptime(fecha_hoy, "%Y-%m-%d").date() + timedelta(days=int(dias_credito))).isoformat() if forma_pago == "CREDITO" else fecha_hoy

            # 3. Insert Venta
            cursor.execute("""
                INSERT INTO ventas (
                    empresa_id, cliente_id, numero_factura, fecha, forma_pago, dias_credito, fecha_vencimiento,
                    subtotal, descuento, base_imponible, iva_porcentaje, iva_valor, total, costo_ventas_total,
                    estado, usuario_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, 'EMITIDA', ?)
            """, (empresa_id, cliente_id, num_factura, fecha_hoy, forma_pago, dias_credito, fecha_venc,
                  subtotal_total, subtotal_total, iva_porcentaje, iva_valor, total_factura, round(costo_ventas_total, 2), usuario_id))
            venta_id = cursor.lastrowid

            for ip in items_procesados:
                cursor.execute("""
                    INSERT INTO detalle_ventas (
                        venta_id, producto_id, cantidad, precio_unitario, descuento, subtotal, costo_unitario_venta, costo_total_venta
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (venta_id, ip["producto_id"], ip["cantidad"], ip["precio_unitario"], ip["descuento"], ip["subtotal"], ip["costo_unitario_venta"], ip["costo_total_venta"]))

            conn.commit()

            # 4. Inventory exits
            for ip in items_procesados:
                InventoryService.register_exit(
                    ip["producto_id"], ip["cantidad"], metodo=metodo_kardex,
                    tipo_movimiento="SALIDA_VENTA", tipo_documento="FACTURA_VENTA",
                    numero_documento=num_factura, observaciones=f"Venta ID {venta_id} a {cliente['nombre_razon_social']}",
                    fecha=fecha_hoy, db_path=db_path
                )

            # 5. Accounts Receivable if Credit
            if forma_pago == "CREDITO":
                conn_cxc = get_db_connection(db_path)
                try:
                    conn_cxc.execute("""
                        INSERT INTO cuentas_cobrar (
                            cliente_id, tipo_origen, origen_id, numero_documento,
                            fecha_emision, fecha_vencimiento, monto_original, saldo_actual, estado
                        ) VALUES (?, 'VENTA_PRODUCTOS', ?, ?, ?, ?, ?, ?, 'PENDIENTE')
                    """, (cliente_id, venta_id, num_factura, fecha_hoy, fecha_venc, total_factura, total_factura))
                    
                    conn_cxc.execute("UPDATE clientes SET saldo_pendiente = saldo_pendiente + ? WHERE id = ?", (total_factura, cliente_id))
                    conn_cxc.commit()
                finally:
                    conn_cxc.close()

            # 6. Accounting Journal Entry 1: Sale
            # Debit: Cash / Bank / Receivable
            # Credit: Sales Revenue (4.1.01) + IVA Ventas (2.1.02)
            if forma_pago == "EFECTIVO":
                cta_debit = 3 # Caja General
            elif forma_pago == "TRANSFERENCIA":
                cta_debit = 4 if not banco_id or banco_id == 1 else 5 # Banco Pichincha or Guayaquil
            else: # CREDITO
                cta_debit = 6 # Cuentas por Cobrar Clientes

            lineas_venta = [
                {"cuenta_id": cta_debit, "debe": total_factura, "haber": 0.0, "referencia": f"Cobro/CxC Venta {num_factura}"},
                {"cuenta_id": 31, "debe": 0.0, "haber": subtotal_total, "referencia": f"Ingreso ventas mercaderías {num_factura}"},
                {"cuenta_id": 21, "debe": 0.0, "haber": iva_valor, "referencia": f"IVA 15% Débito Fiscal {num_factura}"}
            ]

            asiento_vta_id, _ = AccountingService.create_journal_entry(
                empresa_id, fecha_hoy, f"Contabilización Factura de Venta {num_factura} a {cliente['nombre_razon_social']}",
                lineas_venta, tipo_documento="FACTURA_VENTA", numero_documento=num_factura,
                origen_modulo="VENTAS", usuario_id=usuario_id, db_path=db_path
            )

            # 7. Accounting Journal Entry 2: Cost of Goods Sold
            # Debit: Cost of Goods Sold (5.1.01)
            # Credit: Inventory (1.1.06)
            lineas_costo = [
                {"cuenta_id": 35, "debe": round(costo_ventas_total, 2), "haber": 0.0, "referencia": f"Costo de ventas {num_factura}"},
                {"cuenta_id": 8, "debe": 0.0, "haber": round(costo_ventas_total, 2), "referencia": f"Salida de inventario {num_factura}"}
            ]

            asiento_cst_id, _ = AccountingService.create_journal_entry(
                empresa_id, fecha_hoy, f"Contabilización Costo de Ventas e Inventario Factura {num_factura}",
                lineas_costo, tipo_documento="NOTA_EGRESO_INV", numero_documento=f"CST-{num_factura}",
                origen_modulo="VENTAS", usuario_id=usuario_id, db_path=db_path
            )

            # Update venta record with asiento ids
            conn_upd = get_db_connection(db_path)
            try:
                conn_upd.execute("UPDATE ventas SET asiento_id = ?, asiento_costo_id = ? WHERE id = ?", (asiento_vta_id, asiento_cst_id, venta_id))
                conn_upd.commit()
            finally:
                conn_upd.close()

            # 8. Integración con tesorería (caja o banco) y documento fuente
            if forma_pago == "EFECTIVO":
                TreasuryService.register_cash_movement(
                    caja_id, "INGRESO_VENTA", total_factura,
                    f"Cobro en efectivo Factura {num_factura}",
                    numero_comprobante=num_factura, asiento_id=asiento_vta_id,
                    fecha=fecha_hoy, db_path=db_path
                )
            elif forma_pago == "TRANSFERENCIA":
                TreasuryService.register_bank_movement(
                    banco_id or 1, "TRANSFERENCIA_RECIBIDA", total_factura,
                    f"Cobro por transferencia Factura {num_factura}",
                    numero_referencia=num_factura, asiento_id=asiento_vta_id,
                    fecha=fecha_hoy, db_path=db_path
                )

            DocumentService.register(
                "FACTURA_VENTA", num_factura, fecha_hoy,
                "Comercial y Servicios Nueva Esperanza S.A.", cliente["nombre_razon_social"],
                total_factura,
                f"Venta de mercaderías según Factura {num_factura}",
                datos={
                    "ruc_cliente": cliente["identificacion"],
                    "forma_pago": forma_pago,
                    "dias_credito": int(dias_credito),
                    "subtotal": round(subtotal_total, 2),
                    "iva_porcentaje": iva_porcentaje,
                    "iva_valor": round(iva_valor, 2),
                    "total": total_factura,
                    "costo_ventas": round(costo_ventas_total, 2),
                    "items": [
                        {"producto_id": ip["producto_id"], "cantidad": ip["cantidad"],
                         "precio_unitario": ip["precio_unitario"], "subtotal": ip["subtotal"]}
                        for ip in items_procesados
                    ]
                },
                asiento_id=asiento_vta_id, db_path=db_path
            )

            AuditService.log(usuario_id, "sistema", "CREAR_VENTA", "VENTAS", venta_id, None, {
                "factura": num_factura, "total": total_factura, "costo": round(costo_ventas_total, 2)
            }, db_path=db_path)

            return venta_id, num_factura, total_factura
        finally:
            conn.close()

    @staticmethod
    def create_service_transaction(empresa_id, cliente_id, servicio_id, cantidad=1.0, tarifa=None, descripcion="", forma_pago="EFECTIVO", banco_id=None, dias_credito=0, usuario_id=1, fecha=None, db_path=None):
        """
        Executes atomic Service Transaction:
        1. Calculates revenue, IVA, and total
        2. Differentiates revenue in account 4.1.02 (Ingresos por Prestación de Servicios)
        3. Creates transaction, accounts receivable (if credit), and balanced journal entry
        """
        conn = get_db_connection(db_path)
        try:
            cursor = conn.cursor()
            cliente = cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
            if not cliente:
                raise ValueError("Cliente no encontrado.")

            srv = cursor.execute("SELECT * FROM catalogo_servicios WHERE id = ?", (servicio_id,)).fetchone()
            if not srv:
                raise ValueError("Servicio no encontrado.")

            tarifa_real = float(tarifa) if tarifa is not None and float(tarifa) > 0 else float(srv["tarifa_sugerida"])
            subtotal = round(float(cantidad) * tarifa_real, 2)

            tax_calc = TaxService.calculate_tax(subtotal, tipo="IVA_VENTAS", db_path=db_path)
            iva_valor = tax_calc["valor"]
            iva_porcentaje = tax_calc["porcentaje"]
            total = round(subtotal + iva_valor, 2)

            max_s = cursor.execute("SELECT MAX(id) as max_id FROM transacciones_servicios").fetchone()
            next_seq = (max_s["max_id"] or 0) + 101
            num_factura = f"SRV-001-001-{next_seq:06d}"

            fecha_hoy = fecha or PeriodService.get_fecha_trabajo(db_path=db_path)
            valido, msg_fecha = PeriodService.is_fecha_valida(fecha_hoy, db_path=db_path)
            if not valido:
                raise ValueError(msg_fecha)
            fecha_venc = (datetime.strptime(fecha_hoy, "%Y-%m-%d").date() + timedelta(days=int(dias_credito))).isoformat() if forma_pago == "CREDITO" else fecha_hoy

            cursor.execute("""
                INSERT INTO transacciones_servicios (
                    empresa_id, cliente_id, servicio_id, numero_factura, fecha, descripcion,
                    cantidad, tarifa, descuento, subtotal, iva_porcentaje, iva_valor, total, forma_pago, dias_credito,
                    estado, usuario_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, ?, 'EMITIDA', ?)
            """, (empresa_id, cliente_id, servicio_id, num_factura, fecha_hoy, descripcion or srv["nombre"],
                  float(cantidad), tarifa_real, subtotal, iva_porcentaje, iva_valor, total, forma_pago, dias_credito, usuario_id))
            servicio_tx_id = cursor.lastrowid
            conn.commit()

            # Accounts Receivable if Credit
            if forma_pago == "CREDITO":
                conn_cxc = get_db_connection(db_path)
                try:
                    conn_cxc.execute("""
                        INSERT INTO cuentas_cobrar (
                            cliente_id, tipo_origen, origen_id, numero_documento,
                            fecha_emision, fecha_vencimiento, monto_original, saldo_actual, estado
                        ) VALUES (?, 'SERVICIO', ?, ?, ?, ?, ?, ?, 'PENDIENTE')
                    """, (cliente_id, servicio_tx_id, num_factura, fecha_hoy, fecha_venc, total, total))
                    conn_cxc.execute("UPDATE clientes SET saldo_pendiente = saldo_pendiente + ? WHERE id = ?", (total, cliente_id))
                    conn_cxc.commit()
                finally:
                    conn_cxc.close()

            # Accounting Journal Entry
            # Debit: Cash / Bank / Receivable
            # Credit: Service Revenue (4.1.02) + IVA Ventas (2.1.02)
            if forma_pago == "EFECTIVO":
                cta_debit = 3 # Caja General
            elif forma_pago == "TRANSFERENCIA":
                cta_debit = 4 if not banco_id or banco_id == 1 else 5 # Pichincha / Guayaquil
            else:
                cta_debit = 6 # Cuentas por Cobrar Clientes

            lineas = [
                {"cuenta_id": cta_debit, "debe": total, "haber": 0.0, "referencia": f"Cobro/CxC Servicio {num_factura}"},
                {"cuenta_id": 32, "debe": 0.0, "haber": subtotal, "referencia": f"Ingreso prestación servicios {num_factura}"},
                {"cuenta_id": 21, "debe": 0.0, "haber": iva_valor, "referencia": f"IVA 15% Débito Fiscal {num_factura}"}
            ]

            asiento_id, _ = AccountingService.create_journal_entry(
                empresa_id, fecha_hoy, f"Factura Servicio {num_factura} ({srv['nombre']}) a {cliente['nombre_razon_social']}",
                lineas, tipo_documento="FACTURA_VENTA", numero_documento=num_factura,
                origen_modulo="SERVICIOS", usuario_id=usuario_id, db_path=db_path
            )

            conn_upd = get_db_connection(db_path)
            try:
                conn_upd.execute("UPDATE transacciones_servicios SET asiento_id = ? WHERE id = ?", (asiento_id, servicio_tx_id))
                conn_upd.commit()
            finally:
                conn_upd.close()

            # Integración con tesorería y documento fuente del servicio prestado
            if forma_pago == "EFECTIVO":
                TreasuryService.register_cash_movement(
                    1, "INGRESO_SERVICIO", total,
                    f"Cobro en efectivo Factura de servicio {num_factura}",
                    numero_comprobante=num_factura, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )
            elif forma_pago == "TRANSFERENCIA":
                TreasuryService.register_bank_movement(
                    banco_id or 1, "TRANSFERENCIA_RECIBIDA", total,
                    f"Cobro por transferencia servicio {num_factura}",
                    numero_referencia=num_factura, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )

            DocumentService.register(
                "FACTURA_SERVICIO", num_factura, fecha_hoy,
                "Comercial y Servicios Nueva Esperanza S.A.", cliente["nombre_razon_social"],
                total,
                f"Prestación de servicios según Factura {num_factura}",
                datos={
                    "ruc_cliente": cliente["identificacion"],
                    "servicio": srv["nombre"],
                    "cantidad": float(cantidad),
                    "tarifa": tarifa_real,
                    "forma_pago": forma_pago,
                    "subtotal": subtotal,
                    "iva_porcentaje": iva_porcentaje,
                    "iva_valor": round(iva_valor, 2),
                    "total": total
                },
                asiento_id=asiento_id, db_path=db_path
            )

            AuditService.log(usuario_id, "sistema", "CREAR_SERVICIO", "SERVICIOS", servicio_tx_id, None, {
                "factura": num_factura, "total": total, "servicio": srv["nombre"]
            }, db_path=db_path)

            return servicio_tx_id, num_factura, total
        finally:
            conn.close()

    @staticmethod
    def register_collection(cuenta_cobrar_id, monto, medio_pago="EFECTIVO", caja_id=1, banco_id=1, numero_comprobante="", usuario_id=1, fecha=None, db_path=None):
        """
        Registers customer payment/collection against outstanding receivable:
        1. Validates payment amount <= remaining balance
        2. Deducts receivable balance and updates customer debt
        3. Generates collection record
        4. Generates balanced accounting entry (Debit Cash/Bank, Credit Cuentas por Cobrar Clientes)
        """
        if float(monto) <= 0:
            raise ValueError("El monto del cobro debe ser mayor a 0.")

        conn = get_db_connection(db_path)
        try:
            cursor = conn.cursor()
            cxc = cursor.execute("SELECT * FROM cuentas_cobrar WHERE id = ?", (cuenta_cobrar_id,)).fetchone()
            if not cxc:
                raise ValueError("Cuenta por cobrar no encontrada.")

            saldo_act = float(cxc["saldo_actual"])
            monto_cobro = float(monto)
            if monto_cobro > (saldo_act + 0.01):
                raise ValueError(f"El monto a cobrar (${monto_cobro:,.2f}) no puede ser mayor al saldo pendiente (${saldo_act:,.2f}).")

            nuevo_saldo = round(max(0.0, saldo_act - monto_cobro), 2)
            nuevo_estado = "PAGADA" if nuevo_saldo <= 0.01 else "PARCIAL"

            cursor.execute("UPDATE cuentas_cobrar SET saldo_actual = ?, estado = ? WHERE id = ?", (nuevo_saldo, nuevo_estado, cuenta_cobrar_id))
            cursor.execute("UPDATE clientes SET saldo_pendiente = MAX(0.0, saldo_pendiente - ?) WHERE id = ?", (monto_cobro, cxc["cliente_id"]))

            fecha_hoy = fecha or PeriodService.get_fecha_trabajo(db_path=db_path)
            if not numero_comprobante:
                numero_comprobante = f"CI-{cxc['id']:04d}-{int(datetime.now().timestamp())}"

            cursor.execute("""
                INSERT INTO cobros (
                    cuenta_cobrar_id, fecha, monto, medio_pago, caja_id, banco_id, numero_comprobante, observacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Recaudación de cartera cliente')
            """, (cuenta_cobrar_id, fecha_hoy, monto_cobro, medio_pago, caja_id if medio_pago == "EFECTIVO" else None, banco_id if medio_pago != "EFECTIVO" else None, numero_comprobante))
            cobro_id = cursor.lastrowid
            conn.commit()

            # Accounting entry: Debit Cash/Bank, Credit 1.1.04 Cuentas por Cobrar Clientes
            cta_debit = 3 if medio_pago == "EFECTIVO" else (4 if banco_id == 1 else 5)
            lineas = [
                {"cuenta_id": cta_debit, "debe": monto_cobro, "haber": 0.0, "referencia": f"Recaudación {numero_comprobante}"},
                {"cuenta_id": 6, "debe": 0.0, "haber": monto_cobro, "referencia": f"Abono doc {cxc['numero_documento']}"}
            ]

            asiento_id, _ = AccountingService.create_journal_entry(
                1, fecha_hoy, f"Recaudación Cobro {numero_comprobante} de factura {cxc['numero_documento']}",
                lineas, tipo_documento="COMPROBANTE_INGRESO", numero_documento=numero_comprobante,
                origen_modulo="CAJA", usuario_id=usuario_id, db_path=db_path
            )

            conn_upd = get_db_connection(db_path)
            try:
                conn_upd.execute("UPDATE cobros SET asiento_id = ? WHERE id = ?", (asiento_id, cobro_id))
                conn_upd.commit()
            finally:
                conn_upd.close()

            # Integración con tesorería y documento fuente del cobro
            if medio_pago == "EFECTIVO":
                TreasuryService.register_cash_movement(
                    caja_id, "INGRESO_COBRO", monto_cobro,
                    f"Recaudación cartera cliente doc. {cxc['numero_documento']}",
                    numero_comprobante=numero_comprobante, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )
            else:
                TreasuryService.register_bank_movement(
                    banco_id, "TRANSFERENCIA_RECIBIDA", monto_cobro,
                    f"Recaudación cartera cliente doc. {cxc['numero_documento']}",
                    numero_referencia=numero_comprobante, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )

            DocumentService.register(
                "COMPROBANTE_INGRESO", numero_comprobante, fecha_hoy,
                "Comercial y Servicios Nueva Esperanza S.A.", f"Cartera cliente ID {cxc['cliente_id']}",
                monto_cobro,
                f"Recaudación de cuenta por cobrar doc. {cxc['numero_documento']}",
                datos={
                    "cuenta_cobrar_id": cuenta_cobrar_id,
                    "documento_cobrado": cxc["numero_documento"],
                    "medio_pago": medio_pago,
                    "saldo_anterior": saldo_act,
                    "saldo_nuevo": nuevo_saldo
                },
                asiento_id=asiento_id, db_path=db_path
            )

            AuditService.log(usuario_id, "sistema", "REGISTRAR_COBRO", "CARTERA", cobro_id, {"saldo_anterior": saldo_act}, {"saldo_nuevo": nuevo_saldo, "monto_cobrado": monto_cobro}, db_path=db_path)
            return cobro_id, nuevo_saldo, nuevo_estado
        finally:
            conn.close()
