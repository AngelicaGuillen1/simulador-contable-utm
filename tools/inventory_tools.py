# Structured Agent Tools - Inventory & Kardex
from services.inventory_service import InventoryService

def get_product(producto_id, db_path=None):
    """Retrieves product by ID."""
    return InventoryService.get_product(int(producto_id), db_path=db_path)

def get_inventory(categoria=None, db_path=None):
    """Retrieves complete list of products and current stock levels."""
    return InventoryService.get_products(categoria=categoria, db_path=db_path)

def register_inventory_entry(producto_id, cantidad, costo_unitario, tipo_documento="FACTURA_COMPRA", numero_documento="", observaciones="", fecha=None, db_path=None):
    """Registers physical stock entry and lot creation."""
    nuevo_stock, nuevo_cu = InventoryService.register_entry(
        int(producto_id), float(cantidad), float(costo_unitario),
        tipo_documento=tipo_documento, numero_documento=numero_documento,
        observaciones=observaciones, fecha=fecha, db_path=db_path
    )
    return {"nuevo_stock": nuevo_stock, "nuevo_costo_promedio": nuevo_cu}

def register_inventory_exit(producto_id, cantidad, metodo="PROMEDIO", tipo_documento="FACTURA_VENTA", numero_documento="", observaciones="", fecha=None, db_path=None):
    """Registers stock exit and calculates Cost of Goods Sold."""
    costo_total, costo_u, nuevo_stock = InventoryService.register_exit(
        int(producto_id), float(cantidad), metodo=metodo,
        tipo_documento=tipo_documento, numero_documento=numero_documento,
        observaciones=observaciones, fecha=fecha, db_path=db_path
    )
    return {"costo_total": costo_total, "costo_unitario": costo_u, "nuevo_stock": nuevo_stock}

def calculate_weighted_average(producto_id, db_path=None):
    """Calculates weighted average cost for a product."""
    p = InventoryService.get_product(int(producto_id), db_path=db_path)
    if not p:
        return None
    return {"producto_id": p["id"], "costo_promedio": p["costo_unitario"], "stock_actual": p["stock_actual"], "valor_total": round(p["stock_actual"] * p["costo_unitario"], 2)}

def calculate_fifo(producto_id, cantidad, db_path=None):
    """Calculates FIFO valuation and lot consumption for requested quantity."""
    costo_total, cu, lotes = InventoryService.calculate_fifo_cost(int(producto_id), float(cantidad), db_path=db_path)
    return {"costo_total_fifo": costo_total, "costo_unitario_promedio": cu, "lotes_consumidos": lotes}

def calculate_cost_of_goods_sold(items, metodo="PROMEDIO", db_path=None):
    """Calculates total COGS for an array of items."""
    total_cogs = 0.0
    items_breakdown = []
    for it in items:
        p_id = int(it["producto_id"])
        cant = float(it["cantidad"])
        if metodo == "FIFO":
            costo_item, cu, _ = InventoryService.calculate_fifo_cost(p_id, cant, db_path=db_path)
        else:
            p = InventoryService.get_product(p_id, db_path=db_path)
            cu = float(p["costo_unitario"]) if p else 0.0
            costo_item = round(cant * cu, 2)
        total_cogs += costo_item
        items_breakdown.append({"producto_id": p_id, "cantidad": cant, "costo_unitario": cu, "costo_total": costo_item})
    return {"total_costo_ventas": round(total_cogs, 2), "metodo": metodo, "detalle": items_breakdown}
