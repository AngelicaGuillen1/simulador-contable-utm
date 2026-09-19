# Purchases Routes: Supplier Orders, Invoices, Retentions and Payments
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from routes.auth import login_required
from services.purchase_service import (PurchaseService, TIPO_COMPRA_SIN_RETENCION,
                                       CONCEPTOS_POR_CLAVE)
from services.inventory_service import InventoryService
from services.tax_service import TaxService
from models import get_db_contable

purchases_bp = Blueprint("purchases", __name__, url_prefix="/compras")


def _es_contribuyente_especial(formulario):
    """Casilla marcada = proveedor con el que se practica la retención de IVA reducida."""
    return (formulario.get("proveedor_contribuyente_especial") or "").strip().lower() in (
        "1", "on", "true", "si", "sí", "yes")


def _entero(valor, por_defecto=None):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return por_defecto


@purchases_bp.route("/")
@login_required
def list_purchases():
    compras = PurchaseService.get_purchases()
    return render_template("purchases/list.html", compras=compras)


@purchases_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def create_purchase():
    conn = get_db_contable()
    try:
        if request.method == "POST":
            proveedor_id = int(request.form.get("proveedor_id"))
            numero_factura = request.form.get("numero_factura", "").strip()
            forma_pago = request.form.get("forma_pago", "EFECTIVO")
            banco_id = request.form.get("banco_id")
            dias_credito = _entero(request.form.get("dias_credito"), 0)

            # Concepto de retención elegido por el estudiante (porcentajes del catálogo del SRI)
            tipo_compra = request.form.get("tipo_compra") or TIPO_COMPRA_SIN_RETENCION
            contribuyente_especial = _es_contribuyente_especial(request.form)

            prod_ids = request.form.getlist("producto_id[]")
            cantidades = request.form.getlist("cantidad[]")
            costos = request.form.getlist("costo[]")
            descuentos = request.form.getlist("descuento[]")

            items = []
            for i in range(len(prod_ids)):
                if prod_ids[i] and float(cantidades[i] or 0) > 0:
                    items.append({
                        "producto_id": int(prod_ids[i]),
                        "cantidad": float(cantidades[i]),
                        "costo_unitario": float(costos[i] or 0),
                        "descuento": float(descuentos[i] or 0) if i < len(descuentos) else 0.0
                    })

            try:
                compra_id, num_fac, total = PurchaseService.create_purchase(
                    1, proveedor_id, numero_factura, items, forma_pago=forma_pago,
                    banco_id=int(banco_id) if banco_id else None,
                    dias_credito=dias_credito, usuario_id=g.user["id"] if g.user else 1,
                    tipo_compra=tipo_compra,
                    proveedor_contribuyente_especial=contribuyente_especial
                )
                resumen = _resumen_retenciones(compra_id)
                flash(f"Compra Factura {num_fac} registrada: {resumen}", "success")
                return redirect(url_for("purchases.list_purchases"))
            except ValueError as ve:
                flash(f"Validación de compra: {str(ve)}", "danger")
            except Exception as e:
                flash(f"Error al registrar compra: {str(e)}", "danger")

        proveedores = conn.execute("SELECT * FROM proveedores WHERE activo = 1 ORDER BY razon_social ASC").fetchall()
        productos = InventoryService.get_products()
        bancos = conn.execute("SELECT * FROM bancos WHERE activo = 1").fetchall()
        impuestos = TaxService.get_taxes()
        conceptos = PurchaseService.listar_conceptos_retencion()

        return render_template("purchases/create.html", proveedores=proveedores, productos=productos,
                               bancos=bancos, impuestos=impuestos, conceptos=conceptos,
                               tipos_validos=list(CONCEPTOS_POR_CLAVE))
    finally:
        conn.close()


def _resumen_retenciones(compra_id):
    """Texto didáctico con el desglose guardado, para el mensaje de confirmación."""
    compra = PurchaseService.get_purchase_by_id(compra_id)
    if not compra:
        return "compra contabilizada."
    partes = [f"subtotal ${compra['subtotal']:,.2f}",
              f"IVA {compra['iva_porcentaje']:g} % ${compra['iva_valor']:,.2f}"]
    if (compra.get("retencion_renta_valor") or 0) > 0:
        partes.append(f"ret. Renta {(compra.get('retencion_renta_porcentaje') or 0):g} % "
                      f"({compra['retencion_renta_codigo']}) ${compra['retencion_renta_valor']:,.2f}")
    if (compra.get("retencion_iva_valor") or 0) > 0:
        partes.append(f"ret. IVA {(compra.get('retencion_iva_porcentaje') or 0):g} % "
                      f"({compra['retencion_iva_codigo']}) ${compra['retencion_iva_valor']:,.2f}")
    partes.append(f"total factura ${compra['total']:,.2f}")
    partes.append(f"neto al proveedor ${(compra.get('neto_pagar') or compra['total']):,.2f}")
    return " · ".join(partes) + "."


@purchases_bp.route("/desglose", methods=["POST"])
@login_required
def desglose_compra():
    """Devuelve el desglose (IVA, retención de Renta y de IVA, neto y asiento) antes de guardar.

    Lo calcula el MISMO servicio que contabiliza la compra, así lo que el estudiante ve en
    pantalla es exactamente lo que se registrará en el diario.
    """
    try:
        subtotal = float(request.form.get("subtotal") or 0)
    except ValueError:
        subtotal = -1.0

    tipo_compra = request.form.get("tipo_compra") or TIPO_COMPRA_SIN_RETENCION
    forma_pago = request.form.get("forma_pago") or "EFECTIVO"
    banco_id = _entero(request.form.get("banco_id"))

    try:
        desglose = PurchaseService.calcular_desglose_compra(
            subtotal, tipo_compra=tipo_compra,
            proveedor_contribuyente_especial=_es_contribuyente_especial(request.form),
            cuenta_pago_id=PurchaseService.cuenta_pago_compra(forma_pago, banco_id))
    except ValueError as error:
        return jsonify({"ok": False, "mensaje": str(error)}), 400

    return jsonify({"ok": True, "desglose": desglose})


@purchases_bp.route("/<int:compra_id>")
@login_required
def purchase_detail(compra_id):
    """Detalle de una compra con su desglose de IVA, retenciones y asiento contable."""
    compra = PurchaseService.get_purchase_by_id(compra_id)
    if not compra:
        flash("La compra solicitada no existe.", "warning")
        return redirect(url_for("purchases.list_purchases"))

    lineas = []
    total_debe = total_haber = 0.0
    if compra.get("asiento_id"):
        conn = get_db_contable()
        try:
            filas = conn.execute("""
                SELECT d.debe, d.haber, d.referencia, c.codigo AS cuenta_codigo, c.nombre AS cuenta_nombre
                FROM detalle_asientos d
                JOIN cuentas c ON c.id = d.cuenta_id
                WHERE d.asiento_id = ?
                ORDER BY d.id ASC
            """, (compra["asiento_id"],)).fetchall()
            lineas = [dict(f) for f in filas]
            total_debe = round(sum(f["debe"] for f in lineas), 2)
            total_haber = round(sum(f["haber"] for f in lineas), 2)
        finally:
            conn.close()

    return render_template("purchases/detail.html", compra=compra, lineas=lineas,
                          total_debe=total_debe, total_haber=total_haber,
                          conceptos=PurchaseService.listar_conceptos_retencion())
