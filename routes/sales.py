# Sales and Services Routes
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from routes.auth import login_required
from services.sales_service import SalesService
from services.inventory_service import InventoryService
from services.tax_service import TaxService
from models import get_db_connection

sales_bp = Blueprint("sales", __name__)

@sales_bp.route("/ventas", methods=["GET"])
@login_required
def list_sales():
    ventas = SalesService.get_sales()
    return render_template("sales/list.html", ventas=ventas)

@sales_bp.route("/ventas/nueva", methods=["GET", "POST"])
@login_required
def create_sale():
    conn = get_db_connection()
    try:
        if request.method == "POST":
            cliente_id = int(request.form.get("cliente_id"))
            forma_pago = request.form.get("forma_pago", "EFECTIVO")
            banco_id = request.form.get("banco_id")
            dias_credito = int(request.form.get("dias_credito", 0))
            metodo_kardex = request.form.get("metodo_kardex", "PROMEDIO")

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
                        "descuento": float(descuentos[i] or 0)
                    })

            try:
                venta_id, num_fac, total = SalesService.create_sale(
                    1, cliente_id, items, forma_pago=forma_pago,
                    banco_id=int(banco_id) if banco_id else None,
                    dias_credito=dias_credito, usuario_id=g.user["id"] if g.user else 1,
                    metodo_kardex=metodo_kardex
                )
                flash(f"Venta {num_fac} por un total de ${total:,.2f} emitida y contabilizada correctamente.", "success")
                return redirect(url_for("sales.list_sales"))
            except ValueError as ve:
                flash(f"Validación de venta: {str(ve)}", "danger")
            except Exception as e:
                flash(f"Error al procesar venta: {str(e)}", "danger")

        clientes = conn.execute("SELECT * FROM clientes WHERE activo = 1 ORDER BY nombre_razon_social ASC").fetchall()
        productos = InventoryService.get_products()
        bancos = conn.execute("SELECT * FROM bancos WHERE activo = 1").fetchall()
        impuestos = TaxService.get_taxes()

        return render_template("sales/create.html", clientes=clientes, productos=productos, bancos=bancos, impuestos=impuestos)
    finally:
        conn.close()

@sales_bp.route("/servicios", methods=["GET", "POST"])
@login_required
def services():
    conn = get_db_connection()
    try:
        if request.method == "POST":
            cliente_id = int(request.form.get("cliente_id"))
            servicio_id = int(request.form.get("servicio_id"))
            cantidad = float(request.form.get("cantidad", 1.0))
            tarifa = float(request.form.get("tarifa", 0.0))
            descripcion = request.form.get("descripcion", "")
            forma_pago = request.form.get("forma_pago", "EFECTIVO")
            banco_id = request.form.get("banco_id")
            dias_credito = int(request.form.get("dias_credito", 0))

            try:
                srv_id, num_fac, total = SalesService.create_service_transaction(
                    1, cliente_id, servicio_id, cantidad=cantidad, tarifa=tarifa,
                    descripcion=descripcion, forma_pago=forma_pago,
                    banco_id=int(banco_id) if banco_id else None,
                    dias_credito=dias_credito, usuario_id=g.user["id"] if g.user else 1
                )
                flash(f"Factura de servicio {num_fac} por ${total:,.2f} registrada y contabilizada en cuenta de ingresos por servicios.", "success")
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

        return render_template("sales/services.html", tx_servicios=tx_servicios, clientes=clientes, catalogo=catalogo, bancos=bancos)
    finally:
        conn.close()
