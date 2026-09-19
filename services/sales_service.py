# Sales (Commercial Goods & Services) Engine & Receivables Integration
import sqlite3
from datetime import datetime, date, timedelta
from models import get_db_contable
from database.esquema_retenciones_ventas import asegurar_retenciones_ventas
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from services.tax_service import TaxService
from services.audit_service import AuditService
from services.period_service import PeriodService
from services.treasury_service import TreasuryService
from services.document_service import DocumentService
# Los CONCEPTOS de retención son los mismos del módulo de compras: una sola lista de conceptos
# para toda la normativa (BIENES, SERVICIOS_MANO_OBRA, SERVICIOS_PROFESIONALES, ...).
from services.purchase_service import CONCEPTOS_RETENCION, CONCEPTOS_POR_CLAVE

# -------------------------------------------------------------------------------------------
# RETENCIÓN QUE EL CLIENTE LE PRACTICA AL VENDEDOR (Ecuador)
#
# Cuando el cliente es AGENTE DE RETENCIÓN (contribuyente especial) no paga el total de la
# factura: le retiene al vendedor un % de Impuesto a la Renta sobre el VALOR DE LA VENTA
# (subtotal − descuento) y un % del IVA sobre el VALOR DEL IVA de la factura, y le paga el NETO.
# Lo retenido es, para el vendedor, un anticipo del Impuesto a la Renta y un crédito tributario
# de IVA a su favor (cuentas por cobrar).
#
# El CONCEPTO elegido (`tipo_venta`) determina QUÉ retenciones se aplican; los PORCENTAJES y las
# CUENTAS CONTABLES no se escriben aquí: se leen del catálogo tributario (tabla `impuestos`,
# columnas `porcentaje` y `cuenta_venta_id` / `cuenta_contable_id`).
TIPO_VENTA_SIN_RETENCION = "SIN_RETENCION"
CONCEPTOS_RETENCION_VENTA = CONCEPTOS_RETENCION
CONCEPTOS_VENTA_POR_CLAVE = CONCEPTOS_POR_CLAVE

# Cuentas del lado venta que la empresa usa siempre (se resuelven por código en el plan de
# cuentas; si el aula no las tuviera, se conserva el id histórico del plan pedagógico).
CUENTA_IVA_VENTAS = "2.1.02"
CUENTA_INGRESO_BIENES = "4.1.01"
CUENTA_INGRESO_SERVICIOS = "4.1.02"


class SalesService:
    @staticmethod
    def get_sales(empresa_id=1, limit=100, db_path=None):
        conn = get_db_contable(db_path)
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
        conn = get_db_contable(db_path)
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

    # ---------------------------------------------------------------------------------------
    # Retención que el cliente le practica al vendedor: cálculo y desglose
    # ---------------------------------------------------------------------------------------
    @staticmethod
    def cuenta_cobro_venta(forma_pago="EFECTIVO", banco_id=None):
        """Cuenta que se debita al registrar la venta (caja, banco o cuentas por cobrar clientes)."""
        if forma_pago == "EFECTIVO":
            return 3      # 1.1.01 Caja General
        if forma_pago == "TRANSFERENCIA":
            return 4 if not banco_id or banco_id == 1 else 5   # Banco Pichincha / Guayaquil
        return 6          # 1.1.04 Cuentas por Cobrar Clientes

    @staticmethod
    def _cuenta(cursor, codigo, respaldo_id):
        """Cuenta del plan de cuentas por su código; si el aula no la tiene, el id histórico."""
        fila = cursor.execute("SELECT id, codigo, nombre FROM cuentas WHERE codigo = ?",
                              (codigo,)).fetchone()
        if fila:
            return {"cuenta_id": fila["id"], "cuenta_codigo": fila["codigo"],
                    "cuenta_nombre": fila["nombre"]}
        return {"cuenta_id": respaldo_id, "cuenta_codigo": codigo,
                "cuenta_nombre": "(cuenta del plan de cuentas)"}

    @staticmethod
    def _leer_impuesto_venta(cursor, codigo, tipo):
        """Retención del catálogo con la CUENTA DEL LADO VENTA que le corresponde.

        El porcentaje y la cuenta se leen de la tabla `impuestos` (columnas `porcentaje` y
        `cuenta_venta_id`), de modo que el docente puede actualizar la normativa sin tocar el
        programa. Esa cuenta es donde el VENDEDOR registra lo que el cliente le retiene.
        """
        fila = None
        if codigo:
            fila = cursor.execute("SELECT * FROM impuestos WHERE codigo = ? AND activo = 1",
                                  (codigo,)).fetchone()
        if fila is None and tipo:
            fila = cursor.execute("SELECT * FROM impuestos WHERE tipo = ? AND activo = 1 "
                                  "ORDER BY id DESC LIMIT 1", (tipo,)).fetchone()
        if fila is None:
            raise ValueError(
                "No existe configuración tributaria activa para %s. Actualice el catálogo con "
                "database/parametros_tributarios_sri.py." % (codigo or tipo))

        cuenta_id = fila["cuenta_venta_id"] if "cuenta_venta_id" in fila.keys() else None
        cta = cursor.execute("SELECT id, codigo, nombre FROM cuentas WHERE id = ?",
                             (cuenta_id,)).fetchone() if cuenta_id else None
        if cta is None:
            raise ValueError(
                "El catálogo del aula no tiene la cuenta del lado venta de la retención %s "
                "(columna impuestos.cuenta_venta_id). Actualice el catálogo con "
                "database/parametros_tributarios_sri.py o database/esquema_retenciones_ventas.py."
                % (codigo or tipo))

        return {
            "codigo": fila["codigo"],
            "nombre": fila["nombre"],
            "porcentaje": float(fila["porcentaje"]),
            "codigo_sri": fila["codigo_sri"] if "codigo_sri" in fila.keys() else None,
            "cuenta_id": cta["id"],
            "cuenta_codigo": cta["codigo"],
            "cuenta_nombre": cta["nombre"],
        }

    @staticmethod
    def _retencion_venta(cursor, codigo, tipo, base):
        """Retención del catálogo aplicada sobre su base (redondeo a 2 decimales)."""
        impuesto = SalesService._leer_impuesto_venta(cursor, codigo, tipo)
        porcentaje = impuesto["porcentaje"]
        impuesto["base"] = round(float(base), 2)
        impuesto["valor"] = round(float(base) * porcentaje / 100.0, 2)
        return impuesto

    @staticmethod
    def listar_conceptos_retencion_venta(db_path=None):
        """Conceptos de venta con los porcentajes vigentes, para el formulario y el detalle.

        Si el catálogo del aula no tuviera configurado un concepto, se devuelve marcado como no
        disponible (el formulario lo deshabilita) en lugar de romper la pantalla.
        """
        conn = get_db_contable(db_path)
        try:
            asegurar_retenciones_ventas(conn)
            cursor = conn.cursor()
            opciones = []
            for concepto in CONCEPTOS_RETENCION_VENTA:
                renta = iva = None
                disponible, motivo = True, None
                try:
                    if concepto["codigo_renta"]:
                        renta = SalesService._leer_impuesto_venta(
                            cursor, concepto["codigo_renta"], concepto["tipo_renta"])
                    if concepto["codigo_iva"]:
                        iva = SalesService._leer_impuesto_venta(
                            cursor, concepto["codigo_iva"], concepto["tipo_iva"])
                except ValueError as error:
                    disponible, motivo = False, str(error)
                opciones.append({
                    "clave": concepto["clave"],
                    "etiqueta": concepto["etiqueta"],
                    "explicacion": concepto["explicacion"],
                    "familia": concepto["familia"],
                    "renta": renta,
                    "iva": iva,
                    "disponible": disponible,
                    "motivo_no_disponible": motivo,
                })
            return opciones
        finally:
            conn.close()

    @staticmethod
    def calcular_desglose_venta(subtotal, tipo_venta=TIPO_VENTA_SIN_RETENCION, descuento=0.0,
                                cliente_agente_retencion=False, cuenta_cobro_id=6,
                                cuenta_ingreso_codigo=CUENTA_INGRESO_BIENES, db_path=None):
        """Desglose completo de una venta con las retenciones que le practica el cliente.

        Reglas (normativa ecuatoriana):
          * Retención de Renta: sobre el VALOR DE LA VENTA (subtotal − descuento, sin IVA).
          * Retención de IVA:   sobre el VALOR DEL IVA de la factura (nunca sobre la base).
          * Sólo retiene un cliente AGENTE DE RETENCIÓN (contribuyente especial); con cualquier
            otro cliente la venta se registra como siempre.

        Devuelve subtotal, IVA, retenciones, total de la factura, neto por cobrar y las líneas
        del asiento (partida doble) listas para revisar en pantalla o registrar.
        """
        concepto = CONCEPTOS_VENTA_POR_CLAVE.get(tipo_venta)
        if concepto is None:
            raise ValueError(
                "Concepto de retención desconocido: %s. Valores válidos: %s."
                % (tipo_venta, ", ".join(CONCEPTOS_VENTA_POR_CLAVE)))

        subtotal = round(float(subtotal), 2)
        if subtotal < 0:
            raise ValueError("El subtotal de la venta no puede ser negativo.")
        descuento = round(float(descuento or 0.0), 2)
        # Base de la retención de Renta: valor de la venta, sin IVA y neto de descuentos.
        base_venta = round(subtotal - descuento, 2)
        aplica_retencion = (bool(cliente_agente_retencion)
                            and concepto["clave"] != TIPO_VENTA_SIN_RETENCION)

        conn = get_db_contable(db_path)
        try:
            asegurar_retenciones_ventas(conn)
            cursor = conn.cursor()

            # IVA de la venta: se lee la tarifa vigente en el catálogo (IVA_VENTAS)
            iva = TaxService.calculate_tax(base_venta, tipo="IVA_VENTAS", db_path=db_path)
            iva_porcentaje = float(iva["porcentaje"])
            iva_valor = round(float(iva["valor"]), 2)
            cuenta_iva = SalesService._cuenta(cursor, CUENTA_IVA_VENTAS, 21)
            cuenta_ingreso = SalesService._cuenta(cursor, cuenta_ingreso_codigo, 31)

            # Retención de Renta sobre el valor de la venta
            renta = None
            if aplica_retencion and concepto["codigo_renta"]:
                renta = SalesService._retencion_venta(cursor, concepto["codigo_renta"],
                                                      concepto["tipo_renta"], base_venta)

            # Retención de IVA sobre el valor del IVA de la factura
            ret_iva = None
            if aplica_retencion and concepto["codigo_iva"]:
                ret_iva = SalesService._retencion_venta(cursor, concepto["codigo_iva"],
                                                        concepto["tipo_iva"], iva_valor)

            cta_cobro = cursor.execute("SELECT id, codigo, nombre FROM cuentas WHERE id = ?",
                                       (cuenta_cobro_id,)).fetchone()
            cuenta_cobro = {"cuenta_id": cuenta_cobro_id,
                            "cuenta_codigo": cta_cobro["codigo"] if cta_cobro else None,
                            "cuenta_nombre": cta_cobro["nombre"] if cta_cobro else None}
        finally:
            conn.close()

        total_retenciones = round((renta["valor"] if renta else 0.0)
                                  + (ret_iva["valor"] if ret_iva else 0.0), 2)
        total_factura = round(base_venta + iva_valor, 2)
        neto_cobrar = round(total_factura - total_retenciones, 2)

        # Asiento contable (misma lógica que se guarda en el diario):
        #   Debe:  Caja/Banco/CxC por el NETO + retención de Renta por cobrar + retención de IVA
        #   Haber: Ingresos por el valor de la venta + IVA Ventas (débito fiscal)
        lineas = [{
            "cuenta_id": cuenta_cobro["cuenta_id"], "cuenta_codigo": cuenta_cobro["cuenta_codigo"],
            "cuenta_nombre": cuenta_cobro["cuenta_nombre"],
            "debe": neto_cobrar, "haber": 0.0,
            "referencia": "Neto por cobrar al cliente (total de la factura − retenciones)",
        }]
        if renta and renta["valor"] > 0:
            lineas.append({
                "cuenta_id": renta["cuenta_id"], "cuenta_codigo": renta["cuenta_codigo"],
                "cuenta_nombre": renta["cuenta_nombre"],
                "debe": renta["valor"], "haber": 0.0,
                "referencia": f"Retención Renta {renta['porcentaje']:g} % que el cliente retiene "
                              f"sobre el valor de la venta ({renta['codigo']})",
            })
        if ret_iva and ret_iva["valor"] > 0:
            lineas.append({
                "cuenta_id": ret_iva["cuenta_id"], "cuenta_codigo": ret_iva["cuenta_codigo"],
                "cuenta_nombre": ret_iva["cuenta_nombre"],
                "debe": ret_iva["valor"], "haber": 0.0,
                "referencia": f"Retención IVA {ret_iva['porcentaje']:g} % que el cliente retiene "
                              f"sobre el IVA de la factura ({ret_iva['codigo']})",
            })
        lineas.append({
            "cuenta_id": cuenta_ingreso["cuenta_id"], "cuenta_codigo": cuenta_ingreso["cuenta_codigo"],
            "cuenta_nombre": cuenta_ingreso["cuenta_nombre"],
            "debe": 0.0, "haber": base_venta,
            "referencia": "Ingreso por la venta (valor del bien o servicio)",
        })
        lineas.append({
            "cuenta_id": cuenta_iva["cuenta_id"], "cuenta_codigo": cuenta_iva["cuenta_codigo"],
            "cuenta_nombre": cuenta_iva["cuenta_nombre"],
            "debe": 0.0, "haber": iva_valor,
            "referencia": f"IVA {iva_porcentaje:g} % Débito Fiscal (IVA en ventas)",
        })

        return {
            "subtotal": subtotal,
            "descuento": descuento,
            "base_venta": base_venta,
            "iva_codigo": iva["codigo"],
            "iva_porcentaje": iva_porcentaje,
            "iva_valor": iva_valor,
            "iva_cuenta": cuenta_iva,
            "ingreso_cuenta": cuenta_ingreso,
            "total_factura": total_factura,
            "tipo_venta": tipo_venta,
            "concepto_retencion": concepto["clave"],
            "concepto_etiqueta": concepto["etiqueta"],
            "concepto_explicacion": concepto["explicacion"],
            "cliente_agente_retencion": bool(cliente_agente_retencion),
            "aplica_retencion": aplica_retencion,
            "retencion_renta": renta,
            "retencion_iva": ret_iva,
            "total_retenciones": total_retenciones,
            "neto_cobrar": neto_cobrar,
            "cuenta_cobro": cuenta_cobro,
            "lineas": lineas,
        }

    @staticmethod
    def create_sale(empresa_id, cliente_id, items, forma_pago="EFECTIVO", banco_id=None, caja_id=1, dias_credito=0, usuario_id=1, metodo_kardex="PROMEDIO", fecha=None, db_path=None, tipo_venta=TIPO_VENTA_SIN_RETENCION, cliente_agente_retencion=False, concepto_retencion=None):
        """
        Executes atomic sale:
        1. Validates stock for all items
        2. Calculates subtotals, configurable IVA, Cost of Goods Sold y las retenciones que el
           cliente (si es agente de retención) le practica al vendedor: Renta sobre el valor de
           la venta e IVA sobre el IVA de la factura
        3. Inserts sale & detail records (con el desglose de retenciones y el neto por cobrar)
        4. Decrements inventory with Kardex entries
        5. Generates Accounts Receivable if forma_pago == 'CREDITO' por el NETO por cobrar
        6. Generates Sales Journal Entry (Cash/Bank/Receivable por el neto + Retención de Renta
           por cobrar + Retención de IVA por cobrar -> Sales Revenue + IVA Fiscal)
        7. Generates COGS Journal Entry (Cost of Goods Sold -> Inventory)
        8. Logs audit

        `concepto_retencion` es un alias del concepto (`tipo_venta`) para quien llame al servicio
        con el nombre del lado venta.
        """
        if not items:
            raise ValueError("La venta debe contener al menos un producto.")

        concepto_retencion = concepto_retencion or tipo_venta

        conn = get_db_contable(db_path)
        try:
            # Las columnas y cuentas del lado venta se preparan solas la primera vez
            # (idempotente), así las aulas y la plantilla quedan listas sin editar db_init.py.
            asegurar_retenciones_ventas(conn)
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

            # 2. Taxes y retenciones que el cliente le practica al vendedor.
            #    Renta -> sobre el valor de la venta (subtotal − descuento)
            #    IVA   -> sobre el valor del IVA de la factura
            subtotal_total = round(subtotal_total, 2)
            desglose = SalesService.calcular_desglose_venta(
                subtotal_total, tipo_venta=concepto_retencion,
                cliente_agente_retencion=cliente_agente_retencion,
                cuenta_cobro_id=SalesService.cuenta_cobro_venta(forma_pago, banco_id),
                cuenta_ingreso_codigo=CUENTA_INGRESO_BIENES, db_path=db_path
            )
            iva_valor = desglose["iva_valor"]
            iva_porcentaje = desglose["iva_porcentaje"]
            retencion_renta = desglose["retencion_renta"]
            retencion_iva = desglose["retencion_iva"]
            total_retenciones = desglose["total_retenciones"]
            total_factura = desglose["total_factura"]
            neto_cobrar = desglose["neto_cobrar"]

            # Invoice Number
            max_v = cursor.execute("SELECT MAX(id) as max_id FROM ventas").fetchone()
            next_seq = (max_v["max_id"] or 0) + 101
            num_factura = f"FAC-001-001-{next_seq:06d}"

            fecha_hoy = fecha or PeriodService.get_fecha_trabajo(db_path=db_path)
            valido, msg_fecha = PeriodService.is_fecha_valida(fecha_hoy, db_path=db_path)
            if not valido:
                raise ValueError(msg_fecha)
            fecha_venc = (datetime.strptime(fecha_hoy, "%Y-%m-%d").date() + timedelta(days=int(dias_credito))).isoformat() if forma_pago == "CREDITO" else fecha_hoy

            # 3. Insert Venta (con el desglose de las retenciones sufridas y el neto por cobrar)
            cursor.execute("""
                INSERT INTO ventas (
                    empresa_id, cliente_id, numero_factura, fecha, forma_pago, dias_credito, fecha_vencimiento,
                    subtotal, descuento, base_imponible, iva_porcentaje, iva_valor, total, costo_ventas_total,
                    estado, usuario_id,
                    tipo_venta, cliente_agente_retencion,
                    retencion_renta_codigo, retencion_renta_porcentaje, retencion_renta_valor,
                    retencion_iva_codigo, retencion_iva_porcentaje, retencion_iva_valor,
                    total_retenciones, neto_cobrar
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, 'EMITIDA', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (empresa_id, cliente_id, num_factura, fecha_hoy, forma_pago, dias_credito, fecha_venc,
                  subtotal_total, subtotal_total, iva_porcentaje, iva_valor, total_factura, round(costo_ventas_total, 2), usuario_id,
                  concepto_retencion, 1 if cliente_agente_retencion else 0,
                  retencion_renta["codigo"] if retencion_renta else None,
                  retencion_renta["porcentaje"] if retencion_renta else 0.0,
                  retencion_renta["valor"] if retencion_renta else 0.0,
                  retencion_iva["codigo"] if retencion_iva else None,
                  retencion_iva["porcentaje"] if retencion_iva else 0.0,
                  retencion_iva["valor"] if retencion_iva else 0.0,
                  total_retenciones, neto_cobrar))
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

            # 5. Accounts Receivable if Credit: el cliente debe el NETO (factura − retenciones),
            #    porque lo retenido lo declara y lo paga al SRI el propio cliente.
            if forma_pago == "CREDITO":
                conn_cxc = get_db_contable(db_path)
                try:
                    conn_cxc.execute("""
                        INSERT INTO cuentas_cobrar (
                            cliente_id, tipo_origen, origen_id, numero_documento,
                            fecha_emision, fecha_vencimiento, monto_original, saldo_actual, estado
                        ) VALUES (?, 'VENTA_PRODUCTOS', ?, ?, ?, ?, ?, ?, 'PENDIENTE')
                    """, (cliente_id, venta_id, num_factura, fecha_hoy, fecha_venc, neto_cobrar, neto_cobrar))
                    
                    conn_cxc.execute("UPDATE clientes SET saldo_pendiente = saldo_pendiente + ? WHERE id = ?", (neto_cobrar, cliente_id))
                    conn_cxc.commit()
                finally:
                    conn_cxc.close()

            # 6. Accounting Journal Entry 1: Sale (líneas construidas por el desglose)
            # Debe:  Caja / Banco / Cuentas por Cobrar por el NETO
            #        + Retención de Renta por Cobrar + Retención de IVA por Cobrar
            # Haber: Ventas (4.1.01) por el valor de la venta + IVA Ventas (2.1.02)
            glosa_venta = f"Contabilización Factura de Venta {num_factura} a {cliente['nombre_razon_social']}"
            if total_retenciones > 0:
                detalle = []
                if retencion_renta and retencion_renta["valor"] > 0:
                    detalle.append(f"Renta {retencion_renta['porcentaje']:g} %")
                if retencion_iva and retencion_iva["valor"] > 0:
                    detalle.append(f"IVA {retencion_iva['porcentaje']:g} %")
                glosa_venta += (" — el cliente retuvo " + " e ".join(detalle)
                                + f" por ${total_retenciones:,.2f}; neto por cobrar ${neto_cobrar:,.2f}")

            asiento_vta_id, _ = AccountingService.create_journal_entry(
                empresa_id, fecha_hoy, glosa_venta,
                desglose["lineas"], tipo_documento="FACTURA_VENTA", numero_documento=num_factura,
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
            conn_upd = get_db_contable(db_path)
            try:
                conn_upd.execute("UPDATE ventas SET asiento_id = ?, asiento_costo_id = ? WHERE id = ?", (asiento_vta_id, asiento_cst_id, venta_id))
                conn_upd.commit()
            finally:
                conn_upd.close()

            # 8. Integración con tesorería (caja o banco) y documento fuente.
            #    Se cobra el NETO: lo retenido no entra a caja, queda por cobrar al cliente.
            if forma_pago == "EFECTIVO":
                TreasuryService.register_cash_movement(
                    caja_id, "INGRESO_VENTA", neto_cobrar,
                    f"Cobro en efectivo Factura {num_factura} (neto de retenciones)",
                    numero_comprobante=num_factura, asiento_id=asiento_vta_id,
                    fecha=fecha_hoy, db_path=db_path
                )
            elif forma_pago == "TRANSFERENCIA":
                TreasuryService.register_bank_movement(
                    banco_id or 1, "TRANSFERENCIA_RECIBIDA", neto_cobrar,
                    f"Cobro por transferencia Factura {num_factura} (neto de retenciones)",
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
                    "tipo_venta": concepto_retencion,
                    "concepto_retencion": desglose["concepto_etiqueta"],
                    "cliente_agente_retencion": bool(cliente_agente_retencion),
                    "retencion_renta": ({
                        "codigo": retencion_renta["codigo"],
                        "porcentaje": retencion_renta["porcentaje"],
                        "base": retencion_renta["base"],
                        "valor": retencion_renta["valor"],
                    } if retencion_renta else None),
                    "retencion_iva": ({
                        "codigo": retencion_iva["codigo"],
                        "porcentaje": retencion_iva["porcentaje"],
                        "base": retencion_iva["base"],
                        "valor": retencion_iva["valor"],
                    } if retencion_iva else None),
                    "total_retenciones": total_retenciones,
                    "neto_cobrar": neto_cobrar,
                    "items": [
                        {"producto_id": ip["producto_id"], "cantidad": ip["cantidad"],
                         "precio_unitario": ip["precio_unitario"], "subtotal": ip["subtotal"]}
                        for ip in items_procesados
                    ]
                },
                asiento_id=asiento_vta_id, db_path=db_path
            )

            AuditService.log(usuario_id, "sistema", "CREAR_VENTA", "VENTAS", venta_id, None, {
                "factura": num_factura, "total": total_factura, "costo": round(costo_ventas_total, 2),
                "tipo_venta": concepto_retencion,
                "cliente_agente_retencion": bool(cliente_agente_retencion),
                "retencion_renta": retencion_renta["valor"] if retencion_renta else 0.0,
                "retencion_iva": retencion_iva["valor"] if retencion_iva else 0.0,
                "total_retenciones": total_retenciones, "neto_cobrar": neto_cobrar
            }, db_path=db_path)

            return venta_id, num_factura, total_factura
        finally:
            conn.close()

    @staticmethod
    def create_service_transaction(empresa_id, cliente_id, servicio_id, cantidad=1.0, tarifa=None, descripcion="", forma_pago="EFECTIVO", banco_id=None, dias_credito=0, usuario_id=1, fecha=None, db_path=None, tipo_venta=TIPO_VENTA_SIN_RETENCION, cliente_agente_retencion=False, concepto_retencion=None):
        """
        Executes atomic Service Transaction:
        1. Calculates revenue, IVA, total y las retenciones que el cliente (si es agente de
           retención) le practica al vendedor
        2. Differentiates revenue in account 4.1.02 (Ingresos por Prestación de Servicios)
        3. Creates transaction, accounts receivable (if credit, por el neto), treasury y asiento
           balanceado (retenciones por cobrar incluidas)
        """
        concepto_retencion = concepto_retencion or tipo_venta

        conn = get_db_contable(db_path)
        try:
            asegurar_retenciones_ventas(conn)
            cursor = conn.cursor()
            cliente = cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
            if not cliente:
                raise ValueError("Cliente no encontrado.")

            srv = cursor.execute("SELECT * FROM catalogo_servicios WHERE id = ?", (servicio_id,)).fetchone()
            if not srv:
                raise ValueError("Servicio no encontrado.")

            tarifa_real = float(tarifa) if tarifa is not None and float(tarifa) > 0 else float(srv["tarifa_sugerida"])
            subtotal = round(float(cantidad) * tarifa_real, 2)

            # Retenciones que el cliente le practica al vendedor (Renta sobre el servicio,
            # IVA sobre el IVA de la factura). Porcentajes y cuentas: catálogo tributario.
            desglose = SalesService.calcular_desglose_venta(
                subtotal, tipo_venta=concepto_retencion,
                cliente_agente_retencion=cliente_agente_retencion,
                cuenta_cobro_id=SalesService.cuenta_cobro_venta(forma_pago, banco_id),
                cuenta_ingreso_codigo=CUENTA_INGRESO_SERVICIOS, db_path=db_path
            )
            iva_valor = desglose["iva_valor"]
            iva_porcentaje = desglose["iva_porcentaje"]
            retencion_renta = desglose["retencion_renta"]
            retencion_iva = desglose["retencion_iva"]
            total_retenciones = desglose["total_retenciones"]
            total = desglose["total_factura"]
            neto_cobrar = desglose["neto_cobrar"]

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
                    estado, usuario_id,
                    tipo_venta, cliente_agente_retencion,
                    retencion_renta_codigo, retencion_renta_porcentaje, retencion_renta_valor,
                    retencion_iva_codigo, retencion_iva_porcentaje, retencion_iva_valor,
                    total_retenciones, neto_cobrar
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, ?, 'EMITIDA', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (empresa_id, cliente_id, servicio_id, num_factura, fecha_hoy, descripcion or srv["nombre"],
                  float(cantidad), tarifa_real, subtotal, iva_porcentaje, iva_valor, total, forma_pago, dias_credito, usuario_id,
                  concepto_retencion, 1 if cliente_agente_retencion else 0,
                  retencion_renta["codigo"] if retencion_renta else None,
                  retencion_renta["porcentaje"] if retencion_renta else 0.0,
                  retencion_renta["valor"] if retencion_renta else 0.0,
                  retencion_iva["codigo"] if retencion_iva else None,
                  retencion_iva["porcentaje"] if retencion_iva else 0.0,
                  retencion_iva["valor"] if retencion_iva else 0.0,
                  total_retenciones, neto_cobrar))
            servicio_tx_id = cursor.lastrowid
            conn.commit()

            # Accounts Receivable if Credit: el cliente debe el NETO (factura − retenciones)
            if forma_pago == "CREDITO":
                conn_cxc = get_db_contable(db_path)
                try:
                    conn_cxc.execute("""
                        INSERT INTO cuentas_cobrar (
                            cliente_id, tipo_origen, origen_id, numero_documento,
                            fecha_emision, fecha_vencimiento, monto_original, saldo_actual, estado
                        ) VALUES (?, 'SERVICIO', ?, ?, ?, ?, ?, ?, 'PENDIENTE')
                    """, (cliente_id, servicio_tx_id, num_factura, fecha_hoy, fecha_venc, neto_cobrar, neto_cobrar))
                    conn_cxc.execute("UPDATE clientes SET saldo_pendiente = saldo_pendiente + ? WHERE id = ?", (neto_cobrar, cliente_id))
                    conn_cxc.commit()
                finally:
                    conn_cxc.close()

            # Accounting Journal Entry
            # Debe:  Caja / Banco / Cuentas por Cobrar por el NETO + retenciones por cobrar
            # Haber: Servicio Revenue (4.1.02) + IVA Ventas (2.1.02)
            glosa = f"Factura Servicio {num_factura} ({srv['nombre']}) a {cliente['nombre_razon_social']}"
            if total_retenciones > 0:
                glosa += (f" — el cliente retuvo ${total_retenciones:,.2f}; "
                          f"neto por cobrar ${neto_cobrar:,.2f}")

            asiento_id, _ = AccountingService.create_journal_entry(
                empresa_id, fecha_hoy, glosa,
                desglose["lineas"], tipo_documento="FACTURA_VENTA", numero_documento=num_factura,
                origen_modulo="SERVICIOS", usuario_id=usuario_id, db_path=db_path
            )

            conn_upd = get_db_contable(db_path)
            try:
                conn_upd.execute("UPDATE transacciones_servicios SET asiento_id = ? WHERE id = ?", (asiento_id, servicio_tx_id))
                conn_upd.commit()
            finally:
                conn_upd.close()

            # Integración con tesorería y documento fuente del servicio prestado (se cobra el
            # neto: lo retenido queda por cobrar al cliente como crédito tributario/anticipo).
            if forma_pago == "EFECTIVO":
                TreasuryService.register_cash_movement(
                    1, "INGRESO_SERVICIO", neto_cobrar,
                    f"Cobro en efectivo Factura de servicio {num_factura} (neto de retenciones)",
                    numero_comprobante=num_factura, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )
            elif forma_pago == "TRANSFERENCIA":
                TreasuryService.register_bank_movement(
                    banco_id or 1, "TRANSFERENCIA_RECIBIDA", neto_cobrar,
                    f"Cobro por transferencia servicio {num_factura} (neto de retenciones)",
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
                    "total": total,
                    "tipo_venta": concepto_retencion,
                    "cliente_agente_retencion": bool(cliente_agente_retencion),
                    "retencion_renta": ({
                        "codigo": retencion_renta["codigo"],
                        "porcentaje": retencion_renta["porcentaje"],
                        "base": retencion_renta["base"],
                        "valor": retencion_renta["valor"],
                    } if retencion_renta else None),
                    "retencion_iva": ({
                        "codigo": retencion_iva["codigo"],
                        "porcentaje": retencion_iva["porcentaje"],
                        "base": retencion_iva["base"],
                        "valor": retencion_iva["valor"],
                    } if retencion_iva else None),
                    "total_retenciones": total_retenciones,
                    "neto_cobrar": neto_cobrar
                },
                asiento_id=asiento_id, db_path=db_path
            )

            AuditService.log(usuario_id, "sistema", "CREAR_SERVICIO", "SERVICIOS", servicio_tx_id, None, {
                "factura": num_factura, "total": total, "servicio": srv["nombre"],
                "tipo_venta": concepto_retencion,
                "cliente_agente_retencion": bool(cliente_agente_retencion),
                "retencion_renta": retencion_renta["valor"] if retencion_renta else 0.0,
                "retencion_iva": retencion_iva["valor"] if retencion_iva else 0.0,
                "total_retenciones": total_retenciones, "neto_cobrar": neto_cobrar
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

        conn = get_db_contable(db_path)
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

            conn_upd = get_db_contable(db_path)
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
