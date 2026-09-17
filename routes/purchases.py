# Purchases Routes: Supplier Orders, Invoices and Payments
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from routes.auth import login_required
from services.purchase_service import PurchaseService
from services.inventory_service import InventoryService
from services.tax_service import TaxService
from models import get_db_connection

purchases_bp = Blueprint("purchases", __name__, url_prefix="/compras")

@purchases_bp.route("/")
@login_required
def list_purchases():
    compras = PurchaseService.get_purchases()
    return render_template("purchases/list.html", compras=compras)

@purchases_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def create_purchase():
    conn = get_db_connection()
    try:
        if request.method == "POST":
            proveedor_id = int(request.form.get("proveedor_id"))
            numero_factura = request.form.get("numero_factura", "").strip()
            forma_pago = request.form.get("forma_pago", "EFECTIVO")
            banco_id = request.form.get("banco_id")
            dias_credito = int(request.form.get("dias_credito", 0))

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
                        "descuento": float(descuentos[i] or 0)
                    })

            try:
                compra_id, num_fac, total = PurchaseService.create_purchase(
                    1, proveedor_id, numero_factura, items, forma_pago=forma_pago,
                    banco_id=int(banco_id) if banco_id else None,
                    dias_credito=dias_credito, usuario_id=g.user["id"] if g.user else 1
                )
                flash(f"Compra Factura {num_fac} por ${total:,.2f} registrada, ingresada a stock e imputada al diario.", "success")
                return redirect(url_for("purchases.list_purchases"))
            except ValueError as ve:
                flash(f"Validación de compra: {str(ve)}", "danger")
            except Exception as e:
                flash(f"Error al registrar compra: {str(e)}", "danger")

        proveedores = conn.execute("SELECT * FROM proveedores WHERE activo = 1 ORDER BY razon_social ASC").fetchall()
        productos = InventoryService.get_products()
        bancos = conn.execute("SELECT * FROM bancos WHERE activo = 1").fetchall()
        impuestos = TaxService.get_taxes()

        return render_template("purchases/create.html", proveedores=proveedores, productos=productos, bancos=bancos, impuestos=impuestos)
    finally:
        conn.close()
