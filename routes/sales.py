# Sales and Services Routes: goods, services, IVA and the retentions the customer applies
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from routes.auth import login_required
from services.sales_service import (SalesService, TIPO_VENTA_SIN_RETENCION,
                                    CONCEPTOS_VENTA_POR_CLAVE)
from services.inventory_service import InventoryService
from services.tax_service import TaxService
from models import get_db_contable

sales_bp = Blueprint("sales", __name__)


def _es_agente_retencion(formulario):
    """Casilla marcada = cliente agente de retención: le retiene Renta e IVA al vendedor."""
    return (formulario.get("cliente_agente_retencion") or "").strip().lower() in (
        "1", "on", "true", "si", "sí", "yes")


def _entero(valor, por_defecto=None):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return por_defecto


def _resumen_retenciones(venta, etiqueta_total="neto por cobrar"):
    """Texto didáctico con el desglose guardado, para el mensaje de confirmación."""
    partes = [f"subtotal ${venta['subtotal']:,.2f}",
              f"IVA {venta['iva_porcentaje']:g} % ${venta['iva_valor']:,.2f}"]
    if (venta.get("retencion_renta_valor") or 0) > 0:
        partes.append(f"ret. Renta {(venta.get('retencion_renta_porcentaje') or 0):g} % "
                      f"({venta['retencion_renta_codigo']}) ${venta['retencion_renta_valor']:,.2f}")
    if (venta.get("retencion_iva_valor") or 0) > 0:
        partes.append(f"ret. IVA {(venta.get('retencion_iva_porcentaje') or 0):g} % "
                      f"({venta['retencion_iva_codigo']}) ${venta['retencion_iva_valor']:,.2f}")
    partes.append(f"total factura ${venta['total']:,.2f}")
    partes.append(f"{etiqueta_total} ${(venta.get('neto_cobrar') or venta['total']):,.2f}")
    return " · ".join(partes) + "."


@sales_bp.route("/ventas", methods=["GET"])
@login_required
def list_sales():
    ventas = SalesService.get_sales()
    return render_template("sales/list.html", ventas=ventas,
                           conceptos=SalesService.listar_conceptos_retencion_venta())


@sales_bp.route("/ventas/nueva", methods=["GET", "POST"])
@login_required
def create_sale():
    conn = get_db_contable()
    try:
        if request.method == "POST":
            cliente_id = int(request.form.get("cliente_id"))
            forma_pago = request.form.get("forma_pago", "EFECTIVO")
            banco_id = request.form.get("banco_id")
            dias_credito = _entero(request.form.get("dias_credito"), 0)
            metodo_kardex = request.form.get("metodo_kardex", "PROMEDIO")

            # Concepto de la venta y situación del cliente ante la retención (datos del catálogo)
            tipo_venta = (request.form.get("tipo_venta")
                          or request.form.get("concepto_retencion")
                          or TIPO_VENTA_SIN_RETENCION)
            agente_retencion = _es_agente_retencion(request.form)

            prod_ids = request.form.getlist("producto_id[]")
            cantidades = request.form.getlist("cantidad[]")
            precios = request.form.getlist("precio[]")
            descuentos = request.form.getlist("descuento[]")

            items = []
            for i in range(len(prod_ids)):
                if prod_ids[i] and float(cantidades[i] or 0) > 0:
                    items.append({
                        "producto_id": int(prod_ids[i]),
                        "cantidad": float(cantidades[i]),
                        "precio_unitario": float(precios[i] or 0),
                        "descuento": float(descuentos[i] or 0) if i < len(descuentos) else 0.0
                    })

            try:
                venta_id, num_fac, total = SalesService.create_sale(
                    1, cliente_id, items, forma_pago=forma_pago,
                    banco_id=int(banco_id) if banco_id else None,
                    dias_credito=dias_credito, usuario_id=g.user["id"] if g.user else 1,
                    metodo_kardex=metodo_kardex,
                    tipo_venta=tipo_venta, cliente_agente_retencion=agente_retencion
                )
                venta = SalesService.get_sale_by_id(venta_id)
                resumen = _resumen_retenciones(venta) if venta else ""
                flash(f"Venta {num_fac} emitida y contabilizada correctamente: {resumen}", "success")
                return redirect(url_for("sales.list_sales"))
            except ValueError as ve:
                flash(f"Validación de venta: {str(ve)}", "danger")
            except Exception as e:
                flash(f"Error al procesar venta: {str(e)}", "danger")

        clientes = conn.execute("SELECT * FROM clientes WHERE activo = 1 ORDER BY nombre_razon_social ASC").fetchall()
        productos = InventoryService.get_products()
        bancos = conn.execute("SELECT * FROM bancos WHERE activo = 1").fetchall()
        impuestos = TaxService.get_taxes()

        return render_template("sales/create.html", clientes=clientes, productos=productos, bancos=bancos,
                               impuestos=impuestos,
                               conceptos=SalesService.listar_conceptos_retencion_venta(),
                               tipos_validos=list(CONCEPTOS_VENTA_POR_CLAVE))
    finally:
        conn.close()


@sales_bp.route("/ventas/desglose", methods=["POST"])
@login_required
def desglose_venta():
    """Devuelve el desglose (IVA, retención de Renta y de IVA, neto y asiento) antes de guardar.

    Lo calcula el MISMO servicio que contabiliza la venta, así lo que el estudiante ve en
    pantalla es exactamente lo que se registrará en el diario.
    """
    try:
        subtotal = float(request.form.get("subtotal") or 0)
    except ValueError:
        subtotal = -1.0

    tipo_venta = (request.form.get("tipo_venta")
                  or request.form.get("concepto_retencion")
                  or TIPO_VENTA_SIN_RETENCION)
    forma_pago = request.form.get("forma_pago") or "EFECTIVO"
    banco_id = _entero(request.form.get("banco_id"))
    cuenta_ingreso = request.form.get("cuenta_ingreso") or "4.1.01"

    try:
        desglose = SalesService.calcular_desglose_venta(
            subtotal, tipo_venta=tipo_venta,
            cliente_agente_retencion=_es_agente_retencion(request.form),
            cuenta_cobro_id=SalesService.cuenta_cobro_venta(forma_pago, banco_id),
            cuenta_ingreso_codigo=cuenta_ingreso)
    except ValueError as error:
        return jsonify({"ok": False, "mensaje": str(error)}), 400

    return jsonify({"ok": True, "desglose": desglose})


@sales_bp.route("/ventas/<int:venta_id>")
@login_required
def sale_detail(venta_id):
    """Detalle de una venta con su desglose de IVA, retenciones sufridas y asiento contable."""
    venta = SalesService.get_sale_by_id(venta_id)
    if not venta:
        flash("La venta solicitada no existe.", "warning")
        return redirect(url_for("sales.list_sales"))

    lineas = []
    total_debe = total_haber = 0.0
    conn = get_db_contable()
    try:
        if venta.get("asiento_id"):
            filas = conn.execute("""
                SELECT d.debe, d.haber, d.referencia, c.codigo AS cuenta_codigo, c.nombre AS cuenta_nombre
                FROM detalle_asientos d
                JOIN cuentas c ON c.id = d.cuenta_id
                WHERE d.asiento_id = ?
                ORDER BY d.id ASC
            """, (venta["asiento_id"],)).fetchall()
            lineas = [dict(f) for f in filas]
            total_debe = round(sum(f["debe"] for f in lineas), 2)
            total_haber = round(sum(f["haber"] for f in lineas), 2)
    finally:
        conn.close()

    return render_template("sales/detail.html", venta=venta, lineas=lineas,
                           total_debe=total_debe, total_haber=total_haber,
                           concepto=next((c for c in SalesService.listar_conceptos_retencion_venta()
                                          if c["clave"] == (venta.get("tipo_venta") or TIPO_VENTA_SIN_RETENCION)), None))


@sales_bp.route("/servicios", methods=["GET", "POST"])
@login_required
def services():
    conn = get_db_contable()
    try:
        if request.method == "POST":
            cliente_id = int(request.form.get("cliente_id"))
            servicio_id = int(request.form.get("servicio_id"))
            cantidad = float(request.form.get("cantidad", 1.0))
            tarifa = float(request.form.get("tarifa", 0.0))
            descripcion = request.form.get("descripcion", "")
            forma_pago = request.form.get("forma_pago", "EFECTIVO")
            banco_id = request.form.get("banco_id")
            dias_credito = _entero(request.form.get("dias_credito"), 0)
            tipo_venta = (request.form.get("tipo_venta")
                          or request.form.get("concepto_retencion")
                          or TIPO_VENTA_SIN_RETENCION)
            agente_retencion = _es_agente_retencion(request.form)

            try:
                srv_id, num_fac, total = SalesService.create_service_transaction(
                    1, cliente_id, servicio_id, cantidad=cantidad, tarifa=tarifa,
                    descripcion=descripcion, forma_pago=forma_pago,
                    banco_id=int(banco_id) if banco_id else None,
                    dias_credito=dias_credito, usuario_id=g.user["id"] if g.user else 1,
                    tipo_venta=tipo_venta, cliente_agente_retencion=agente_retencion
                )
                flash(f"Factura de servicio {num_fac} por ${total:,.2f} registrada y contabilizada "
                      f"en cuenta de ingresos por servicios.", "success")
                return redirect(url_for("sales.services"))
            except Exception as e:
                flash(f"Error al facturar servicio: {str(e)}", "danger")

        tx_servicios = conn.execute("""
            SELECT t.*, c.nombre_razon_social as cliente_nombre, s.nombre as servicio_nombre
            FROM transacciones_servicios t
            JOIN clientes c ON t.cliente_id = c.id
            JOIN catalogo_servicios s ON t.servicio_id = s.id
            ORDER BY t.id DESC
        """).fetchall()

        clientes = conn.execute("SELECT * FROM clientes WHERE activo = 1 ORDER BY nombre_razon_social ASC").fetchall()
        catalogo = conn.execute("SELECT * FROM catalogo_servicios WHERE activo = 1 ORDER BY nombre ASC").fetchall()
        bancos = conn.execute("SELECT * FROM bancos WHERE activo = 1").fetchall()

        return render_template("sales/services.html", tx_servicios=tx_servicios, clientes=clientes,
                               catalogo=catalogo, bancos=bancos,
                               conceptos=SalesService.listar_conceptos_retencion_venta())
    finally:
        conn.close()
