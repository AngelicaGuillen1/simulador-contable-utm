# Purchases Engine & Payables Integration
import sqlite3
from datetime import datetime, date, timedelta
from models import get_db_contable
from database.esquema_retenciones_compras import asegurar_columnas
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from services.tax_service import TaxService
from services.audit_service import AuditService
from services.period_service import PeriodService
from services.treasury_service import TreasuryService
from services.document_service import DocumentService

# -------------------------------------------------------------------------------------------
# RETENCIONES DE LA COMPRA (Ecuador)
#
# El CONCEPTO que elige el usuario (`tipo_compra`) determina QUÉ retenciones se aplican; los
# PORCENTAJES y las CUENTAS CONTABLES no se escriben aquí: se leen del catálogo tributario
# (tabla `impuestos`, ver database/parametros_tributarios_sri.py).
#
#   Retención de Renta -> se calcula sobre el VALOR DEL BIEN O SERVICIO (subtotal − descuento).
#   Retención de IVA   -> se calcula sobre el VALOR DEL IVA de la factura (nunca sobre la base).
TIPO_COMPRA_SIN_RETENCION = "SIN_RETENCION"

CONCEPTOS_RETENCION = [
    {
        "clave": "BIENES",
        "etiqueta": "BIENES — mercadería y bienes muebles",
        "familia": "BIENES",
        "codigo_renta": "RET-RENTA-02-BIE", "tipo_renta": "RET_RENTA_BIENES",
        "codigo_iva": "RET-IVA-30-BIE", "tipo_iva": "RET_IVA_BIENES",
        "explicacion": "Adquisición de bienes muebles de naturaleza corporal (mercadería). "
                       "Renta 2 % del valor del bien; IVA 30 % del IVA facturado.",
    },
    {
        "clave": "SERVICIOS_MANO_OBRA",
        "etiqueta": "SERVICIOS_MANO_OBRA — servicios con predominio de mano de obra",
        "familia": "SERVICIOS",
        "codigo_renta": "RET-RENTA-03-SRV", "tipo_renta": "RET_RENTA_SERVICIOS",
        "codigo_iva": "RET-IVA-70-SRV", "tipo_iva": "RET_IVA_SERVICIOS",
        "explicacion": "Servicios de personas naturales donde predomina la mano de obra (limpieza, "
                       "mantenimiento, instalación). Renta 3 % del servicio; IVA 70 % del IVA.",
    },
    {
        "clave": "SERVICIOS_PROFESIONALES",
        "etiqueta": "SERVICIOS_PROFESIONALES — honorarios y arrendamiento de personas naturales",
        "familia": "SERVICIOS",
        "codigo_renta": "RET-RENTA-10-HON", "tipo_renta": "RET_RENTA_HONORARIOS",
        "codigo_iva": "RET-IVA-100-PRO", "tipo_iva": "RET_IVA_PROFESIONALES",
        "explicacion": "Honorarios profesionales y arrendamiento de inmuebles de personas naturales. "
                       "Renta 10 % del servicio; IVA 100 % del IVA facturado.",
    },
    {
        "clave": "SERVICIOS_SOCIEDADES",
        "etiqueta": "SERVICIOS_SOCIEDADES — servicios profesionales prestados por sociedades",
        "familia": "SERVICIOS",
        "codigo_renta": "RET-RENTA-05-SOC", "tipo_renta": "RET_RENTA_SERVICIOS_SOCIEDADES",
        "codigo_iva": "RET-IVA-70-SRV", "tipo_iva": "RET_IVA_SERVICIOS",
        "explicacion": "Servicios profesionales y comisiones pagados a sociedades residentes. "
                       "Renta 5 % del servicio; IVA 70 % del IVA facturado.",
    },
    {
        "clave": "BIENES_AGRICOLAS_PRODUCTOR",
        "etiqueta": "BIENES_AGRICOLAS_PRODUCTOR — compra directa al productor",
        "familia": "BIENES",
        "codigo_renta": "RET-RENTA-01-AGR", "tipo_renta": "RET_RENTA_AGRICOLA_PRODUCTOR",
        "codigo_iva": "RET-IVA-30-BIE", "tipo_iva": "RET_IVA_BIENES",
        "explicacion": "Bienes de origen agrícola, avícola, pecuario o forestal comprados "
                       "directamente al productor. Renta 1 % del bien; IVA 30 % del IVA.",
    },
    {
        "clave": "RIMPE_EMPRENDEDOR",
        "etiqueta": "RIMPE_EMPRENDEDOR — proveedor acogido a RIMPE Emprendedor",
        "familia": "BIENES",
        "codigo_renta": "RET-RENTA-01-RIMPE", "tipo_renta": "RET_RENTA_RIMPE_EMPRENDEDOR",
        "codigo_iva": "RET-IVA-30-BIE", "tipo_iva": "RET_IVA_BIENES",
        "explicacion": "Compras a contribuyentes RIMPE Emprendedor. Renta 1 % del valor; "
                       "IVA 30 % del IVA (bienes).",
    },
    {
        "clave": "RIMPE_NEGOCIO_POPULAR",
        "etiqueta": "RIMPE_NEGOCIO_POPULAR — proveedor RIMPE Negocio Popular",
        "familia": "NINGUNA",
        "codigo_renta": "RET-RENTA-00-RIMPE", "tipo_renta": "RET_RENTA_RIMPE_POPULAR",
        "codigo_iva": None, "tipo_iva": None,
        "explicacion": "Compras a RIMPE Negocio Popular con comprobante preimpreso: "
                       "Renta 0 % y sin retención de IVA.",
    },
    {
        "clave": "LIQUIDACION_COMPRA",
        "etiqueta": "LIQUIDACION_COMPRA — liquidación de compra de bienes y servicios",
        "familia": "LIQUIDACION",
        "codigo_renta": "RET-RENTA-03-LIQ", "tipo_renta": "RET_RENTA_LIQUIDACION",
        "codigo_iva": "RET-IVA-100-LIQ", "tipo_iva": "RET_IVA_LIQUIDACION",
        "explicacion": "Liquidaciones de compra a personas sin RUC o con RUC suspendido. "
                       "Renta 3 % del valor; IVA 100 % del IVA.",
    },
    {
        "clave": "SIN_RETENCION",
        "etiqueta": "SIN_RETENCION — no se practica retención",
        "familia": "NINGUNA",
        "codigo_renta": None, "tipo_renta": None,
        "codigo_iva": None, "tipo_iva": None,
        "explicacion": "Compras a otros contribuyentes especiales, al sector público o a "
                       "proveedores no sujetos a retención: no se retiene Renta ni IVA.",
    },
]

CONCEPTOS_POR_CLAVE = {c["clave"]: c for c in CONCEPTOS_RETENCION}

# Cuando el proveedor es otro contribuyente especial la retención de IVA baja al 10 % (bienes)
# o al 20 % (servicios); la retención de Renta se mantiene igual.
RETENCION_IVA_CONTRIBUYENTE_ESPECIAL = {
    "BIENES": {"codigo": "RET-IVA-10-BIE-ESP", "tipo": "RET_IVA_BIENES_ESPECIALES"},
    "SERVICIOS": {"codigo": "RET-IVA-20-SRV-ESP", "tipo": "RET_IVA_SERVICIOS_ESPECIALES"},
}

# Cuenta contable de respaldo si el catálogo tributario no la tuviera configurada
CUENTA_RETENCION_RENTA = "2.1.03"
CUENTA_RETENCION_IVA = "2.1.04"

class PurchaseService:
    @staticmethod
    def get_purchases(empresa_id=1, limit=100, db_path=None):
        conn = get_db_contable(db_path)
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
        conn = get_db_contable(db_path)
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

    # ---------------------------------------------------------------------------------------
    # Retenciones de compras: cálculo y desglose
    # ---------------------------------------------------------------------------------------
    @staticmethod
    def cuenta_pago_compra(forma_pago="EFECTIVO", banco_id=None):
        """Cuenta que se acredita al registrar la compra (caja, banco o cuentas por pagar)."""
        if forma_pago == "EFECTIVO":
            return 3      # 1.1.01 Caja General
        if forma_pago == "TRANSFERENCIA":
            return 4 if not banco_id or banco_id == 1 else 5   # Banco Pichincha / Guayaquil
        return 20         # 2.1.01 Cuentas por Pagar Proveedores

    @staticmethod
    def _leer_impuesto(cursor, codigo, tipo, cuenta_respaldo=None):
        """Lee un impuesto del catálogo (por código SRI y, si no está, por su tipo).

        Los porcentajes NUNCA vienen del código: se toman de la tabla `impuestos`, de modo que
        el docente puede actualizarlos cuando la normativa cambie.
        """
        fila = None
        if codigo:
            fila = cursor.execute(
                "SELECT * FROM impuestos WHERE codigo = ? AND activo = 1", (codigo,)).fetchone()
        if fila is None and tipo:
            fila = cursor.execute(
                "SELECT * FROM impuestos WHERE tipo = ? AND activo = 1 ORDER BY id DESC LIMIT 1",
                (tipo,)).fetchone()
        if fila is None:
            raise ValueError(
                "No existe configuración tributaria activa para %s. Actualice el catálogo con "
                "database/parametros_tributarios_sri.py." % (codigo or tipo))

        cuenta_id = fila["cuenta_contable_id"]
        cuenta_codigo = cuenta_nombre = None
        if cuenta_id:
            cta = cursor.execute("SELECT id, codigo, nombre FROM cuentas WHERE id = ?", (cuenta_id,)).fetchone()
        else:
            cta = cursor.execute("SELECT id, codigo, nombre FROM cuentas WHERE codigo = ?",
                                 (cuenta_respaldo,)).fetchone() if cuenta_respaldo else None
        if cta:
            cuenta_id, cuenta_codigo, cuenta_nombre = cta["id"], cta["codigo"], cta["nombre"]

        return {
            "codigo": fila["codigo"],
            "nombre": fila["nombre"],
            "porcentaje": float(fila["porcentaje"]),
            "codigo_sri": fila["codigo_sri"] if "codigo_sri" in fila.keys() else None,
            "cuenta_id": cuenta_id,
            "cuenta_codigo": cuenta_codigo,
            "cuenta_nombre": cuenta_nombre,
        }

    @staticmethod
    def _retencion(cursor, codigo, tipo, base, cuenta_respaldo):
        """Retención de un impuesto del catálogo aplicada sobre su base (redondeo a 2 decimales)."""
        impuesto = PurchaseService._leer_impuesto(cursor, codigo, tipo, cuenta_respaldo)
        porcentaje = impuesto["porcentaje"]
        valor = round(float(base) * porcentaje / 100.0, 2)
        impuesto["base"] = round(float(base), 2)
        impuesto["valor"] = valor
        return impuesto

    @staticmethod
    def listar_conceptos_retencion(db_path=None):
        """Conceptos de compra con los porcentajes vigentes, para el formulario y el detalle.

        Si el catálogo del aula no tuviera configurado un concepto, se devuelve marcado como no
        disponible (el formulario lo deshabilita) en lugar de romper la pantalla.
        """
        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            opciones = []
            for concepto in CONCEPTOS_RETENCION:
                renta = iva = iva_especial = None
                disponible, motivo = True, None
                try:
                    if concepto["codigo_renta"]:
                        renta = PurchaseService._leer_impuesto(
                            cursor, concepto["codigo_renta"], concepto["tipo_renta"], CUENTA_RETENCION_RENTA)
                    if concepto["codigo_iva"]:
                        iva = PurchaseService._leer_impuesto(
                            cursor, concepto["codigo_iva"], concepto["tipo_iva"], CUENTA_RETENCION_IVA)
                        especial = RETENCION_IVA_CONTRIBUYENTE_ESPECIAL.get(concepto["familia"])
                        if especial:
                            iva_especial = PurchaseService._leer_impuesto(
                                cursor, especial["codigo"], especial["tipo"], CUENTA_RETENCION_IVA)
                except ValueError as error:
                    disponible, motivo = False, str(error)
                opciones.append({
                    "clave": concepto["clave"],
                    "etiqueta": concepto["etiqueta"],
                    "explicacion": concepto["explicacion"],
                    "familia": concepto["familia"],
                    "renta": renta,
                    "iva": iva,
                    "iva_contribuyente_especial": iva_especial,
                    "disponible": disponible,
                    "motivo_no_disponible": motivo,
                })
            return opciones
        finally:
            conn.close()

    @staticmethod
    def calcular_desglose_compra(subtotal, tipo_compra=TIPO_COMPRA_SIN_RETENCION,
                                 proveedor_contribuyente_especial=False, cuenta_pago_id=20,
                                 db_path=None):
        """Desglose completo de una compra con sus retenciones de Renta y de IVA.

        Reglas (normativa ecuatoriana):
          * Retención de Renta: sobre el valor del bien o servicio SIN IVA (subtotal − descuento).
          * Retención de IVA:   sobre el VALOR DEL IVA de la factura (nunca sobre la base).
          * Proveedor contribuyente especial: la retención de IVA baja al 10 % (bienes) o al
            20 % (servicios); la retención de Renta se mantiene.

        Devuelve subtotal, IVA, retenciones, total de la factura, neto a pagar al proveedor y las
        líneas del asiento (partida doble) listas para revisar en pantalla o registrar.
        """
        concepto = CONCEPTOS_POR_CLAVE.get(tipo_compra)
        if concepto is None:
            raise ValueError(
                "Concepto de retención desconocido: %s. Valores válidos: %s."
                % (tipo_compra, ", ".join(CONCEPTOS_POR_CLAVE)))

        subtotal = round(float(subtotal), 2)
        if subtotal < 0:
            raise ValueError("El subtotal de la compra no puede ser negativo.")

        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()

            # IVA de la factura: se lee la tarifa vigente en el catálogo (IVA_COMPRAS)
            iva = TaxService.calculate_tax(subtotal, tipo="IVA_COMPRAS", db_path=db_path)
            iva_porcentaje = float(iva["porcentaje"])
            iva_valor = round(float(iva["valor"]), 2)
            cta_iva = cursor.execute(
                "SELECT id, codigo, nombre FROM cuentas WHERE codigo = '1.1.07'").fetchone()
            iva_cuenta = {"cuenta_id": cta_iva["id"], "cuenta_codigo": cta_iva["codigo"],
                          "cuenta_nombre": cta_iva["nombre"]} if cta_iva else {
                "cuenta_id": 9, "cuenta_codigo": "1.1.07", "cuenta_nombre": "IVA Compras"}

            # Retención de Renta sobre la base (valor del bien o servicio)
            renta = None
            if concepto["codigo_renta"]:
                renta = PurchaseService._retencion(cursor, concepto["codigo_renta"],
                                                   concepto["tipo_renta"], subtotal, CUENTA_RETENCION_RENTA)

            # Retención de IVA sobre el valor del IVA de la factura
            ret_iva = None
            if concepto["codigo_iva"]:
                codigo_iva, tipo_iva = concepto["codigo_iva"], concepto["tipo_iva"]
                if proveedor_contribuyente_especial:
                    especial = RETENCION_IVA_CONTRIBUYENTE_ESPECIAL.get(concepto["familia"])
                    if especial:
                        codigo_iva, tipo_iva = especial["codigo"], especial["tipo"]
                ret_iva = PurchaseService._retencion(cursor, codigo_iva, tipo_iva, iva_valor,
                                                     CUENTA_RETENCION_IVA)

            cta_pago = cursor.execute("SELECT id, codigo, nombre FROM cuentas WHERE id = ?",
                                      (cuenta_pago_id,)).fetchone()
            cuenta_pago = {"cuenta_id": cuenta_pago_id,
                           "cuenta_codigo": cta_pago["codigo"] if cta_pago else None,
                           "cuenta_nombre": cta_pago["nombre"] if cta_pago else None}

            cta_inv = cursor.execute(
                "SELECT id, codigo, nombre FROM cuentas WHERE codigo = '1.1.06'").fetchone()
            cuenta_inventario = {"cuenta_id": cta_inv["id"] if cta_inv else 8,
                                 "cuenta_codigo": cta_inv["codigo"] if cta_inv else "1.1.06",
                                 "cuenta_nombre": cta_inv["nombre"] if cta_inv else "Inventario de Mercaderías"}
        finally:
            conn.close()

        total_retenciones = round((renta["valor"] if renta else 0.0) + (ret_iva["valor"] if ret_iva else 0.0), 2)
        total_factura = round(subtotal + iva_valor, 2)
        neto_pagar = round(total_factura - total_retenciones, 2)

        etiqueta = f"Retención Renta {renta['porcentaje']:g} %" if renta else "Sin retención de Renta"
        # Asiento contable (misma lógica que se guarda en el diario)
        lineas = [{
            "cuenta_id": cuenta_inventario["cuenta_id"], "cuenta_codigo": cuenta_inventario["cuenta_codigo"],
            "cuenta_nombre": cuenta_inventario["cuenta_nombre"],
            "debe": subtotal, "haber": 0.0,
            "referencia": "Ingreso de bienes/servicios al inventario",
        }, {
            "cuenta_id": iva_cuenta["cuenta_id"], "cuenta_codigo": iva_cuenta["cuenta_codigo"],
            "cuenta_nombre": iva_cuenta["cuenta_nombre"],
            "debe": iva_valor, "haber": 0.0,
            "referencia": f"IVA {iva_porcentaje:g} % Crédito Tributario",
        }]
        if renta and renta["valor"] > 0:
            lineas.append({
                "cuenta_id": renta["cuenta_id"], "cuenta_codigo": renta["cuenta_codigo"],
                "cuenta_nombre": renta["cuenta_nombre"],
                "debe": 0.0, "haber": renta["valor"],
                "referencia": f"{etiqueta} — retención sobre el valor del bien o servicio ({renta['codigo']})",
            })
        if ret_iva and ret_iva["valor"] > 0:
            lineas.append({
                "cuenta_id": ret_iva["cuenta_id"], "cuenta_codigo": ret_iva["cuenta_codigo"],
                "cuenta_nombre": ret_iva["cuenta_nombre"],
                "debe": 0.0, "haber": ret_iva["valor"],
                "referencia": f"Retención IVA {ret_iva['porcentaje']:g} % — retención sobre el IVA "
                              f"de la factura ({ret_iva['codigo']})",
            })
        lineas.append({
            "cuenta_id": cuenta_pago["cuenta_id"], "cuenta_codigo": cuenta_pago["cuenta_codigo"],
            "cuenta_nombre": cuenta_pago["cuenta_nombre"],
            "debe": 0.0, "haber": neto_pagar,
            "referencia": "Neto a pagar al proveedor (factura − retenciones)",
        })

        return {
            "subtotal": subtotal,
            "iva_codigo": iva["codigo"],
            "iva_porcentaje": iva_porcentaje,
            "iva_valor": iva_valor,
            "iva_cuenta": iva_cuenta,
            "total_factura": total_factura,
            "tipo_compra": tipo_compra,
            "concepto_retencion": concepto["clave"],
            "concepto_etiqueta": concepto["etiqueta"],
            "concepto_explicacion": concepto["explicacion"],
            "proveedor_contribuyente_especial": bool(proveedor_contribuyente_especial),
            "retencion_renta": renta,
            "retencion_iva": ret_iva,
            "total_retenciones": total_retenciones,
            "neto_pagar": neto_pagar,
            "cuenta_pago": cuenta_pago,
            "lineas": lineas,
        }

    @staticmethod
    def create_purchase(empresa_id, proveedor_id, numero_factura, items, forma_pago="EFECTIVO", banco_id=None, dias_credito=0, usuario_id=1, fecha=None, db_path=None, tipo_compra=TIPO_COMPRA_SIN_RETENCION, proveedor_contribuyente_especial=False):
        """
        Executes atomic purchase:
        1. Validates items and prices
        2. Calculates subtotals, IVA compras and the retentions of Renta and IVA of the invoice
        3. Inserts purchase and details
        4. Registers stock intake in Inventory & Kardex
        5. Generates Accounts Payable if forma_pago == 'CREDITO' (net of retentions)
        6. Generates balanced journal entry (Debit Inventory 1.1.06 + IVA Compras 1.1.07 ->
           Credit Retention Renta 2.1.03 + Retention IVA 2.1.04 + Cash/Bank/Payables por el neto)
        """
        if not items:
            raise ValueError("La compra debe incluir al menos un producto o ítem.")

        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            # Las columnas de retenciones se crean solas la primera vez (idempotente), así las
            # aulas y la plantilla del simulador quedan listas sin editar db_init.py.
            asegurar_columnas(conn)
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

            subtotal_total = round(subtotal_total, 2)

            # IVA y retenciones: porcentajes y cuentas se leen del catálogo tributario.
            #   Renta -> sobre el valor del bien o servicio (subtotal − descuento)
            #   IVA    -> sobre el valor del IVA de la factura
            desglose = PurchaseService.calcular_desglose_compra(
                subtotal_total, tipo_compra=tipo_compra,
                proveedor_contribuyente_especial=proveedor_contribuyente_especial,
                cuenta_pago_id=PurchaseService.cuenta_pago_compra(forma_pago, banco_id),
                db_path=db_path
            )
            iva_valor = desglose["iva_valor"]
            iva_porcentaje = desglose["iva_porcentaje"]
            retencion_renta = desglose["retencion_renta"]
            retencion_iva = desglose["retencion_iva"]
            total_retenciones = desglose["total_retenciones"]
            total_factura = desglose["total_factura"]
            neto_pagar = desglose["neto_pagar"]

            fecha_hoy = fecha or PeriodService.get_fecha_trabajo(db_path=db_path)
            valido, msg_fecha = PeriodService.is_fecha_valida(fecha_hoy, db_path=db_path)
            if not valido:
                raise ValueError(msg_fecha)
            fecha_venc = (datetime.strptime(fecha_hoy, "%Y-%m-%d").date() + timedelta(days=int(dias_credito))).isoformat() if forma_pago == "CREDITO" else fecha_hoy

            cursor.execute("""
                INSERT INTO compras (
                    empresa_id, proveedor_id, numero_factura, fecha, forma_pago, dias_credito, fecha_vencimiento,
                    subtotal, descuento, iva_porcentaje, iva_valor, total, estado, usuario_id,
                    tipo_compra, proveedor_contribuyente_especial,
                    retencion_renta_codigo, retencion_renta_porcentaje, retencion_renta_valor,
                    retencion_iva_codigo, retencion_iva_porcentaje, retencion_iva_valor,
                    total_retenciones, neto_pagar
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, 'REGISTRADA', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (empresa_id, proveedor_id, numero_factura, fecha_hoy, forma_pago, dias_credito, fecha_venc,
                  subtotal_total, iva_porcentaje, iva_valor, total_factura, usuario_id,
                  tipo_compra, 1 if proveedor_contribuyente_especial else 0,
                  retencion_renta["codigo"] if retencion_renta else None,
                  retencion_renta["porcentaje"] if retencion_renta else 0.0,
                  retencion_renta["valor"] if retencion_renta else 0.0,
                  retencion_iva["codigo"] if retencion_iva else None,
                  retencion_iva["porcentaje"] if retencion_iva else 0.0,
                  retencion_iva["valor"] if retencion_iva else 0.0,
                  total_retenciones, neto_pagar))
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

            # Accounts Payable if Credit: se debe al proveedor el NETO (factura − retenciones),
            # porque las retenciones se declaran y pagan al SRI, no al proveedor.
            if forma_pago == "CREDITO":
                conn_cxp = get_db_contable(db_path)
                try:
                    conn_cxp.execute("""
                        INSERT INTO cuentas_pagar (
                            proveedor_id, compra_id, numero_factura, fecha_emision, fecha_vencimiento,
                            monto_original, saldo_actual, estado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
                    """, (proveedor_id, compra_id, numero_factura, fecha_hoy, fecha_venc, neto_pagar, neto_pagar))
                    conn_cxp.execute("UPDATE proveedores SET saldo_pendiente = saldo_pendiente + ? WHERE id = ?", (neto_pagar, proveedor_id))
                    conn_cxp.commit()
                finally:
                    conn_cxp.close()

            # Accounting Journal Entry (líneas construidas por el desglose de retenciones)
            # Debit:  Inventory (1.1.06) + IVA Compras (1.1.07)
            # Credit: Retención Renta por Pagar (2.1.03) + Retención IVA por Pagar (2.1.04)
            #         + Caja (1.1.01) / Banco / Cuentas por Pagar (2.1.01) por el neto
            glosa = f"Contabilización Compra Factura {numero_factura} de {prov['razon_social']}"
            if total_retenciones > 0:
                glosa += (f" — retenciones Renta {retencion_renta['porcentaje']:g} % e IVA "
                          f"{retencion_iva['porcentaje']:g} % por ${total_retenciones:,.2f}"
                          if retencion_renta and retencion_iva else
                          f" — retenciones por ${total_retenciones:,.2f}")

            asiento_id, _ = AccountingService.create_journal_entry(
                empresa_id, fecha_hoy, glosa,
                desglose["lineas"], tipo_documento="FACTURA_COMPRA", numero_documento=numero_factura,
                origen_modulo="COMPRAS", usuario_id=usuario_id, db_path=db_path
            )

            conn_upd = get_db_contable(db_path)
            try:
                conn_upd.execute("UPDATE compras SET asiento_id = ? WHERE id = ?", (asiento_id, compra_id))
                conn_upd.commit()
            finally:
                conn_upd.close()

            # Integración con tesorería y documento fuente de compra (se paga el neto)
            if forma_pago == "EFECTIVO":
                TreasuryService.register_cash_movement(
                    1, "EGRESO_COMPRA", neto_pagar,
                    f"Pago en efectivo Factura de compra {numero_factura} (neto de retenciones)",
                    numero_comprobante=numero_factura, asiento_id=asiento_id,
                    fecha=fecha_hoy, db_path=db_path
                )
            elif forma_pago == "TRANSFERENCIA":
                TreasuryService.register_bank_movement(
                    banco_id or 1, "TRANSFERENCIA_EMITIDA", neto_pagar,
                    f"Pago por transferencia Factura de compra {numero_factura} (neto de retenciones)",
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
                    "tipo_compra": tipo_compra,
                    "concepto_retencion": desglose["concepto_etiqueta"],
                    "proveedor_contribuyente_especial": bool(proveedor_contribuyente_especial),
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
                    "neto_pagar": neto_pagar,
                    "items": [
                        {"producto_id": ip["producto_id"], "cantidad": ip["cantidad"],
                         "costo_unitario": ip["costo_unitario"], "subtotal": ip["subtotal"]}
                        for ip in items_procesados
                    ]
                },
                asiento_id=asiento_id, db_path=db_path
            )

            AuditService.log(usuario_id, "sistema", "CREAR_COMPRA", "COMPRAS", compra_id, None, {
                "factura": numero_factura, "total": total_factura, "proveedor": prov["razon_social"],
                "tipo_compra": tipo_compra,
                "proveedor_contribuyente_especial": bool(proveedor_contribuyente_especial),
                "retencion_renta": retencion_renta["valor"] if retencion_renta else 0.0,
                "retencion_iva": retencion_iva["valor"] if retencion_iva else 0.0,
                "total_retenciones": total_retenciones, "neto_pagar": neto_pagar
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

        conn = get_db_contable(db_path)
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

            conn_upd = get_db_contable(db_path)
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
