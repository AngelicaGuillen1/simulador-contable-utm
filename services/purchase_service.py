# Purchases Engine & Payables Integration
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

class PurchaseService:
    @staticmethod
    def get_purchases(empresa_id=1, limit=100, db_path=None):
        conn = get_db_connection(db_path)
        try:
            rows = conn.execute("""
                SELECT c.*, p.razon_social as proveedor_nombre, p.identificacion as proveedor_ruc
                FROM compras c
                JOIN proveedores p ON c.proveedor_id = p.id
                WHERE c.empresa_id = ?
                ORDER BY c.id DESC LIMIT ?
            """, (empresa_id, limit)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_purchase_by_id(compra_id, db_path=None):
        conn = get_db_connection(db_path)
        try:
            c = conn.execute("""
                SELECT c.*, p.razon_social as proveedor_nombre, p.identificacion as proveedor_ruc, p.direccion as proveedor_direccion
                FROM compras c
                JOIN proveedores p ON c.proveedor_id = p.id
                WHERE c.id = ?
            """, (compra_id,)).fetchone()
            if not c:
                return None
            c_dict = dict(c)
            det = conn.execute("""
                SELECT d.*, pr.codigo as producto_codigo, pr.descripcion as producto_nombre
                FROM detalle_compras d
                JOIN productos pr ON d.producto_id = pr.id
                WHERE d.compra_id = ?
            """, (compra_id,)).fetchall()
            c_dict["detalles"] = [dict(d) for d in det]
            return c_dict
        finally:
            conn.close()

    @staticmethod
    def create_purchase(empresa_id, proveedor_id, numero_factura, items, forma_pago="EFECTIVO", banco_id=None, dias_credito=0, usuario_id=1, fecha=None, db_path=None):
        """
        Executes atomic purchase:
        1. Validates items and prices
        2. Calculates subtotals, configurable IVA compras, and total
        3. Inserts purchase and details
        4. Registers stock intake in Inventory & Kardex
        5. Generates Accounts Payable if forma_pago == 'CREDITO'
        6. Generates balanced journal entry (Debit Inventory 1.1.06 + IVA Compras 1.1.07 -> Credit Cash/Bank/Payables)
        """
        if not items:
            raise ValueError("La compra debe incluir al menos un producto o ítem.")

        conn = get_db_connection(db_path)
        try:
            cursor = conn.cursor()
            prov = cursor.execute("SELECT * FROM proveedores WHERE id = ?", (proveedor_id,)).fetchone()
            if not prov:
                raise ValueError("Proveedor no encontrado.")

            subtotal_total = 0.0
            items_procesados = []

            for it in items:
                p_id = it["producto_id"]
                cant = float(it["cantidad"])
                costo_u = float(it["costo_unitario"])
                desc = float(it.get("descuento", 0.0))

                if cant <= 0 or costo_u < 0:
                    raise ValueError("Cantidad y costo unitario deben ser válidos.")

                p = cursor.execute("SELECT * FROM productos WHERE id = ?", (p_id,)).fetchone()
                if not p:
                    raise ValueError(f"Producto ID {p_id} no existe.")

                sub_item = round((cant * costo_u) - desc, 2)
                subtotal_total += sub_item

                items_procesados.append({
                    "producto_id": p_id,
                    "cantidad": cant,
                    "costo_unitario": costo_u,
                    "descuento": desc,
                    "subtotal": sub_item
                })

            # Taxes
            tax_calc = TaxService.calculate_tax(subtotal_total, tipo="IVA_COMPRAS", db_path=db_path)
            iva_valor = tax_calc["valor"]
            iva_porcentaje = tax_calc["porcentaje"]
            total_factura = round(subtotal_total + iva_valor, 2)

            fecha_hoy = fecha or PeriodService.get_fecha_trabajo(db_path=db_path)
            valido, msg_fecha = PeriodService.is_fecha_valida(fecha_hoy, db_path=db_path)
            if not valido:
                raise ValueError(msg_fecha)
            fecha_venc = (datetime.strptime(fecha_hoy, "%Y-%m-%d").date() + timedelta(days=int(dias_credito))).isoformat() if forma_pago == "CREDITO" else fecha_hoy

            cursor.execute("""
                INSERT INTO compras (
                    empresa_id, proveedor_id, numero_factura, fecha, forma_pago, dias_credito, fecha_vencimiento,
                    subtotal, descuento, iva_porcentaje, iva_valor, total, estado, usuario_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, 'REGISTRADA', ?)
            """, (empresa_id, proveedor_id, numero_factura, fecha_hoy, forma_pago, dias_credito, fecha_venc,
                  subtotal_total, iva_porcentaje, iva_valor, total_factura, usuario_id))
            compra_id = cursor.lastrowid

            for ip in items_procesados:
                cursor.execute("""
                    INSERT INTO detalle_compras (compra_id, producto_id, cantidad, costo_unitario, descuento, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (compra_id, ip["producto_id"], ip["cantidad"], ip["costo_unitario"], ip["descuento"], ip["subtotal"]))

            conn.commit()

            # Stock intake
            for ip in items_procesados:
                InventoryService.register_entry(
                    ip["producto_id"], ip["cantidad"], ip["costo_unitario"],
                    tipo_movimiento="ENTRADA_COMPRA", tipo_documento="FACTURA_COMPRA",
                    numero_documento=numero_factura, observaciones=f"Compra Factura {numero_factura} de {prov['razon_social']}",
                    fecha=fecha_hoy, db_path=db_path
                )

            # Accounts Payable if Credit
            if forma_pago == "CREDITO":
                conn_cxp = get_db_connection(db_path)
                try:
                    conn_cxp.execute("""
                        INSERT INTO cuentas_pagar (
                            proveedor_id, compra_id, numero_factura, fecha_emision, fecha_vencimiento,
                            monto_original, saldo_actual, estado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
                    """, (proveedor_id, compra_id, numero_factura, fecha_hoy, fecha_venc, total_factura, total_factura))
                    conn_cxp.execute("UPDATE proveedores SET saldo_pendiente = saldo_pendiente + ? WHERE id = ?", (total_factura, proveedor_id))
                    conn_cxp.commit()
                finally:
                    conn_cxp.close()

            # Accounting Journal Entry
            # Debit: Inventory (1.1.06) + IVA Compras (1.1.07)
            # Credit: Cash (1.1.01) / Bank (1.1.02/1.1.03) / Payables (2.1.01)
            if forma_pago == "EFECTIVO":
                cta_credit = 3 # Caja General
            elif forma_pago == "TRANSFERENCIA":
                cta_credit = 4 if not banco_id or banco_id == 1 else 5 # Pichincha / Guayaquil
            else:
                cta_credit = 20 # Cuentas por Pagar Proveedores

            lineas = [
                {"cuenta_id": 8, "debe": subtotal_total, "haber": 0.0, "referencia": f"Ingreso mercaderías Factura {numero_factura}"},
                {"cuenta_id": 9, "debe": iva_valor, "haber": 0.0, "referencia": f"IVA 15% Crédito Tributario {numero_factura}"},
                {"cuenta_id": cta_credit, "debe": 0.0, "haber": total_factura, "referencia": f"Pago/CxP Factura {numero_factura}"}
            ]

            asiento_id, _ = AccountingService.create_journal_entry(
                empresa_id, fecha_hoy, f"Contabilización Compra Factura {numero_factura} de {prov['razon_social']}",
                lineas, tipo_documento="FACTURA_COMPRA", numero_documento=numero_factura,
                origen_modulo="COMPRAS", usuario_id=usuario_id, db_path=db_path
            )

            conn_upd = get_db_connection(db_path)
            try:
                conn_upd.execute("UPDATE compras SET asiento_id = ? WHERE id = ?", (asiento_id, compra_id))
                conn_upd.commit()
            finally:
                conn_upd.close()

            # Integración con tesorería y documento fuente de compra
            if forma_pago == "EFECTIVO":
                TreasuryService.register_cash_movement(
                    1, "EGRESO_COMPRA", total_factura,
                    f"Pago en efectivo Factura de compra {numero_factura}",
                    numero_comprobante=numero_factura, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )
            elif forma_pago == "TRANSFERENCIA":
                TreasuryService.register_bank_movement(
                    banco_id or 1, "TRANSFERENCIA_EMITIDA", total_factura,
                    f"Pago por transferencia Factura de compra {numero_factura}",
                    numero_referencia=numero_factura, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )

            DocumentService.register(
                "FACTURA_COMPRA", numero_factura, fecha_hoy,
                prov["razon_social"], "Comercial y Servicios Nueva Esperanza S.A.",
                total_factura,
                f"Compra de mercaderías según Factura {numero_factura}",
                datos={
                    "ruc_proveedor": prov["identificacion"],
                    "forma_pago": forma_pago,
                    "dias_credito": int(dias_credito),
                    "subtotal": round(subtotal_total, 2),
                    "iva_porcentaje": iva_porcentaje,
                    "iva_valor": round(iva_valor, 2),
                    "total": total_factura,
                    "items": [
                        {"producto_id": ip["producto_id"], "cantidad": ip["cantidad"],
                         "costo_unitario": ip["costo_unitario"], "subtotal": ip["subtotal"]}
                        for ip in items_procesados
                    ]
                },
                asiento_id=asiento_id, db_path=db_path
            )

            AuditService.log(usuario_id, "sistema", "CREAR_COMPRA", "COMPRAS", compra_id, None, {
                "factura": numero_factura, "total": total_factura, "proveedor": prov["razon_social"]
            }, db_path=db_path)

            return compra_id, numero_factura, total_factura
        finally:
            conn.close()

    @staticmethod
    def register_payment(cuenta_pagar_id, monto, medio_pago="TRANSFERENCIA", caja_id=1, banco_id=1, numero_comprobante="", usuario_id=1, fecha=None, db_path=None):
        """
        Registers vendor payment against outstanding payable:
        1. Deducts payable balance and updates supplier debt
        2. Records payment transaction
        3. Creates balanced accounting entry (Debit Cuentas por Pagar Proveedores 2.1.01, Credit Cash/Bank)
        """
        if float(monto) <= 0:
            raise ValueError("El monto del pago debe ser mayor a 0.")

        conn = get_db_connection(db_path)
        try:
            cursor = conn.cursor()
            cxp = cursor.execute("SELECT * FROM cuentas_pagar WHERE id = ?", (cuenta_pagar_id,)).fetchone()
            if not cxp:
                raise ValueError("Cuenta por pagar no encontrada.")

            saldo_act = float(cxp["saldo_actual"])
            monto_pago = float(monto)
            if monto_pago > (saldo_act + 0.01):
                raise ValueError(f"El monto a pagar (${monto_pago:,.2f}) no puede ser mayor a la deuda pendiente (${saldo_act:,.2f}).")

            nuevo_saldo = round(max(0.0, saldo_act - monto_pago), 2)
            nuevo_estado = "PAGADA" if nuevo_saldo <= 0.01 else "PARCIAL"

            cursor.execute("UPDATE cuentas_pagar SET saldo_actual = ?, estado = ? WHERE id = ?", (nuevo_saldo, nuevo_estado, cuenta_pagar_id))
            cursor.execute("UPDATE proveedores SET saldo_pendiente = MAX(0.0, saldo_pendiente - ?) WHERE id = ?", (monto_pago, cxp["proveedor_id"]))

            fecha_hoy = fecha or PeriodService.get_fecha_trabajo(db_path=db_path)
            if not numero_comprobante:
                numero_comprobante = f"CE-{cxp['id']:04d}-{int(datetime.now().timestamp())}"

            cursor.execute("""
                INSERT INTO pagos (
                    cuenta_pagar_id, fecha, monto, medio_pago, caja_id, banco_id, numero_comprobante, observacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pago de obligación comercial con proveedor')
            """, (cuenta_pagar_id, fecha_hoy, monto_pago, medio_pago, caja_id if medio_pago == "EFECTIVO" else None, banco_id if medio_pago != "EFECTIVO" else None, numero_comprobante))
            pago_id = cursor.lastrowid
            conn.commit()

            # Accounting entry: Debit 2.1.01 Cuentas por Pagar Proveedores, Credit Cash/Bank
            cta_credit = 3 if medio_pago == "EFECTIVO" else (4 if banco_id == 1 else 5)
            lineas = [
                {"cuenta_id": 20, "debe": monto_pago, "haber": 0.0, "referencia": f"Cancelación Factura {cxp['numero_factura']}"},
                {"cuenta_id": cta_credit, "debe": 0.0, "haber": monto_pago, "referencia": f"Egreso de fondos {numero_comprobante}"}
            ]

            asiento_id, _ = AccountingService.create_journal_entry(
                1, fecha_hoy, f"Pago Factura {cxp['numero_factura']} con Comprobante {numero_comprobante}",
                lineas, tipo_documento="COMPROBANTE_EGRESO", numero_documento=numero_comprobante,
                origen_modulo="BANCOS", usuario_id=usuario_id, db_path=db_path
            )

            conn_upd = get_db_connection(db_path)
            try:
                conn_upd.execute("UPDATE pagos SET asiento_id = ? WHERE id = ?", (asiento_id, pago_id))
                conn_upd.commit()
            finally:
                conn_upd.close()

            # Integración con tesorería y documento fuente del pago
            if medio_pago == "EFECTIVO":
                TreasuryService.register_cash_movement(
                    caja_id, "EGRESO_PAGO", monto_pago,
                    f"Pago a proveedor Factura {cxp['numero_factura']}",
                    numero_comprobante=numero_comprobante, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )
            else:
                TreasuryService.register_bank_movement(
                    banco_id, "TRANSFERENCIA_EMITIDA", monto_pago,
                    f"Pago a proveedor Factura {cxp['numero_factura']}",
                    numero_referencia=numero_comprobante, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )

            DocumentService.register(
                "COMPROBANTE_EGRESO", numero_comprobante, fecha_hoy,
                "Comercial y Servicios Nueva Esperanza S.A.", f"Proveedor ID {cxp['proveedor_id']}",
                monto_pago,
                f"Pago de obligación con proveedor factura {cxp['numero_factura']}",
                datos={
                    "cuenta_pagar_id": cuenta_pagar_id,
                    "factura_pagada": cxp["numero_factura"],
                    "medio_pago": medio_pago,
                    "saldo_anterior": saldo_act,
                    "saldo_nuevo": nuevo_saldo
                },
                asiento_id=asiento_id, db_path=db_path
            )

            # Integración con tesorería y documento fuente del pago
            if medio_pago == "EFECTIVO":
                TreasuryService.register_cash_movement(
                    caja_id, "EGRESO_PAGO", monto_pago,
                    f"Pago a proveedor Factura {cxp['numero_factura']}",
                    numero_comprobante=numero_comprobante, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )
            else:
                TreasuryService.register_bank_movement(
                    banco_id, "TRANSFERENCIA_EMITIDA", monto_pago,
                    f"Pago a proveedor Factura {cxp['numero_factura']}",
                    numero_referencia=numero_comprobante, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )

            DocumentService.register(
                "COMPROBANTE_EGRESO", numero_comprobante, fecha_hoy,
                "Comercial y Servicios Nueva Esperanza S.A.", f"Proveedor ID {cxp['proveedor_id']}",
                monto_pago,
                f"Pago de obligacion con proveedor factura {cxp['numero_factura']}",
                datos={
                    "cuenta_pagar_id": cuenta_pagar_id,
                    "factura_pagada": cxp["numero_factura"],
                    "medio_pago": medio_pago,
                    "saldo_anterior": saldo_act,
                    "saldo_nuevo": nuevo_saldo
                },
                asiento_id=asiento_id, db_path=db_path
            )

            AuditService.log(usuario_id, "sistema", "REGISTRAR_PAGO", "PROVEEDORES", pago_id, {"saldo_anterior": saldo_act}, {"saldo_nuevo": nuevo_saldo, "monto_pagado": monto_pago}, db_path=db_path)
            return pago_id, nuevo_saldo, nuevo_estado
        finally:
            conn.close()
