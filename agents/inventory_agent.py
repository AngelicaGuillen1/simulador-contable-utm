# Agente de Inventarios - Especialista en Stock, Kardex, Costos y Valuación
from tools.inventory_tools import get_inventory, calculate_weighted_average, calculate_fifo

class InventoryAgent:
    def __init__(self):
        self.name = "AgenteInventarios"

    def handle_query(self, query):
        q = query.lower()
        inv = get_inventory()
        total_items = len(inv)
        stock_bajo = [p for p in inv if p["stock_actual"] <= p["stock_minimo"]]
        valor_total = sum(p["stock_actual"] * p["costo_unitario"] for p in inv)

        if "stock bajo" in q or "alerta" in q:
            return {
                "agente": self.name,
                "tema": "ALERTAS_STOCK",
                "respuesta": f"Existen {len(stock_bajo)} productos con existencias por debajo del stock mínimo recomendado.",
                "productos_alerta": stock_bajo
            }
        
        return {
            "agente": self.name,
            "tema": "RESUMEN_INVENTARIO",
            "respuesta": f"El catálogo de inventarios contiene {total_items} productos de primera necesidad valorados en ${valor_total:,.2f}. El sistema soporta control de Kardex por Promedio Ponderado y FIFO (PEPS).",
            "total_items": total_items,
            "valor_total_inventario": round(valor_total, 2),
            "alertas_stock_bajo": len(stock_bajo)
        }
