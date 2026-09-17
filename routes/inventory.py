# Inventory and Kardex Routes
from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required
from services.inventory_service import InventoryService
from models import get_db_connection

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventarios")

@inventory_bp.route("/")
@inventory_bp.route("/productos")
@login_required
def products():
    categoria = request.args.get("categoria")
    productos = InventoryService.get_products(categoria=categoria, activo_only=False)
    conn = get_db_connection()
    try:
        categorias = conn.execute("SELECT DISTINCT categoria FROM productos ORDER BY categoria ASC").fetchall()
        total_valor = sum(p["stock_actual"] * p["costo_unitario"] for p in productos)
        alertas = [p for p in productos if p["stock_actual"] <= p["stock_minimo"]]

        return render_template(
            "inventory/products.html",
            productos=productos,
            categorias=[c["categoria"] for c in categorias],
            selected_cat=categoria,
            total_valor=round(total_valor, 2),
            alertas_count=len(alertas)
        )
    finally:
        conn.close()

@inventory_bp.route("/kardex")
@inventory_bp.route("/kardex/<int:producto_id>")
@login_required
def kardex(producto_id=1):
    metodo = request.args.get("metodo", "PROMEDIO")
    kardex_data = InventoryService.get_kardex(producto_id, metodo=metodo)
    productos = InventoryService.get_products()

    return render_template(
        "inventory/kardex.html",
        kardex=kardex_data,
        productos=productos,
        selected_prod_id=producto_id,
        metodo=metodo
    )

@inventory_bp.route("/stock")
@login_required
def stock_report():
    productos = InventoryService.get_products()
    total_unidades = sum(p["stock_actual"] for p in productos)
    total_costo = sum(p["stock_actual"] * p["costo_unitario"] for p in productos)
    total_pv = sum(p["stock_actual"] * p["precio_venta"] for p in productos)
    margen_potencial = round(total_pv - total_costo, 2)

    return render_template(
        "inventory/stock.html",
        productos=productos,
        total_unidades=round(total_unidades, 2),
        total_costo=round(total_costo, 2),
        total_pv=round(total_pv, 2),
        margen_potencial=margen_potencial
    )
