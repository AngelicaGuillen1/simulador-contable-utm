# Inventory & Multi-Method Kardex (Weighted Average & FIFO) Service
import sqlite3
from datetime import datetime, date
from models import get_db_contable
from services.audit_service import AuditService
from services.period_service import PeriodService

class InventoryService:
    @staticmethod
    def get_products(categoria=None, activo_only=True, db_path=None):
        conn = get_db_contable(db_path)
        try:
            query = "SELECT * FROM productos WHERE 1=1"
            params = []
            if activo_only:
                query += " AND activo = 1"
            if categoria:
                query += " AND categoria = ?"
                params.append(categoria)
            query += " ORDER BY codigo ASC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_product(producto_id, db_path=None):
        conn = get_db_contable(db_path)
        try:
            row = conn.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_low_stock_alerts(db_path=None):
        conn = get_db_contable(db_path)
        try:
            rows = conn.execute("""
                SELECT * FROM productos
                WHERE stock_actual <= stock_minimo AND activo = 1
                ORDER BY (stock_actual / stock_minimo) ASC
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def register_entry(producto_id, cantidad, costo_unitario, tipo_movimiento="ENTRADA_COMPRA", tipo_documento="FACTURA_COMPRA", numero_documento="", observaciones="", asiento_id=None, fecha=None, db_path=None):
        """
        Registers stock intake. Updates average cost and creates FIFO lot.
        """
        if cantidad <= 0:
            raise ValueError("La cantidad de entrada debe ser mayor a 0.")
        if costo_unitario < 0:
            raise ValueError("El costo unitario no puede ser negativo.")

        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            p = cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
            if not p:
                raise ValueError("Producto no encontrado.")

            stock_anterior = float(p["stock_actual"])
            costo_ant = float(p["costo_unitario"])
            costo_total_ant = stock_anterior * costo_ant

            costo_entrada_total = float(cantidad) * float(costo_unitario)
            nuevo_stock = stock_anterior + float(cantidad)
            
            # Weighted Average calculation
            nuevo_costo_promedio = (costo_total_ant + costo_entrada_total) / nuevo_stock if nuevo_stock > 0 else float(costo_unitario)
            nuevo_costo_total = nuevo_stock * nuevo_costo_promedio

            # Update product master record
            cursor.execute("""
                UPDATE productos
                SET stock_actual = ?, costo_unitario = ?
                WHERE id = ?
            """, (round(nuevo_stock, 2), round(nuevo_costo_promedio, 4), producto_id))

            # Record Inventory Movement
            cursor.execute("""
                INSERT INTO movimientos_inventario (
                    producto_id, fecha, tipo_movimiento, tipo_documento, numero_documento,
                    cantidad, costo_unitario, costo_total, saldo_cantidad, saldo_costo_unitario, saldo_costo_total,
                    asiento_id, observaciones
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (producto_id, fecha or PeriodService.get_fecha_trabajo(db_path=db_path), tipo_movimiento, tipo_documento, numero_documento,
                  float(cantidad), float(costo_unitario), round(costo_entrada_total, 2),
                  round(nuevo_stock, 2), round(nuevo_costo_promedio, 4), round(nuevo_costo_total, 2),
                  asiento_id, observaciones))

            # Create FIFO Lot entry
            cursor.execute("""
                INSERT INTO kardex_lotes (producto_id, fecha, documento_origen, cantidad_inicial, cantidad_restante, costo_unitario, agotado)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (producto_id, fecha or PeriodService.get_fecha_trabajo(db_path=db_path), numero_documento, float(cantidad), float(cantidad), float(costo_unitario)))

            conn.commit()
            return round(nuevo_stock, 2), round(nuevo_costo_promedio, 4)
        finally:
            conn.close()

    @staticmethod
    def calculate_fifo_cost(producto_id, cantidad_salida, db_path=None):
        """
        Calculates Cost of Goods Sold for a quantity using First-In-First-Out (FIFO) method.
        """
        conn = get_db_contable(db_path)
        try:
            lotes = conn.execute("""
                SELECT * FROM kardex_lotes
                WHERE producto_id = ? AND agotado = 0 AND cantidad_restante > 0
                ORDER BY fecha ASC, id ASC
            """, (producto_id,)).fetchall()

            cant_pendiente = float(cantidad_salida)
            costo_total_fifo = 0.0
            lotes_consumidos = []

            for l in lotes:
                disponible = float(l["cantidad_restante"])
                pu = float(l["costo_unitario"])

                if cant_pendiente <= disponible:
                    costo_total_fifo += cant_pendiente * pu
                    lotes_consumidos.append({"lote_id": l["id"], "cantidad": cant_pendiente, "costo_unitario": pu})
                    cant_pendiente = 0
                    break
                else:
                    costo_total_fifo += disponible * pu
                    lotes_consumidos.append({"lote_id": l["id"], "cantidad": disponible, "costo_unitario": pu})
                    cant_pendiente -= disponible

            if cant_pendiente > 0.001:
                raise ValueError(f"Stock insuficiente para FIFO en producto ID {producto_id}. Faltan {cant_pendiente} unidades.")

            costo_unitario_prom = costo_total_fifo / float(cantidad_salida)
            return round(costo_total_fifo, 2), round(costo_unitario_prom, 4), lotes_consumidos
        finally:
            conn.close()

    @staticmethod
    def register_exit(producto_id, cantidad, metodo="PROMEDIO", tipo_movimiento="SALIDA_VENTA", tipo_documento="FACTURA_VENTA", numero_documento="", observaciones="", asiento_id=None, fecha=None, db_path=None):
        """
        Registers stock exit and returns total Cost of Goods Sold.
        """
        if cantidad <= 0:
            raise ValueError("La cantidad de salida debe ser mayor a 0.")

        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            p = cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
            if not p:
                raise ValueError("Producto no encontrado.")

            stock_anterior = float(p["stock_actual"])
            if stock_anterior < float(cantidad):
                raise ValueError(f"Stock insuficiente para '{p['descripcion']}'. Existencias actuales: {stock_anterior}, solicitadas: {cantidad}.")

            if metodo == "FIFO":
                costo_total, costo_unitario, lotes_consumidos = InventoryService.calculate_fifo_cost(producto_id, cantidad, db_path=db_path)
                # Consume lots in DB
                for lc in lotes_consumidos:
                    cursor.execute("""
                        UPDATE kardex_lotes
                        SET cantidad_restante = cantidad_restante - ?,
                            agotado = CASE WHEN cantidad_restante - ? <= 0.001 THEN 1 ELSE 0 END
                        WHERE id = ?
                    """, (lc["cantidad"], lc["cantidad"], lc["lote_id"]))
            else: # PROMEDIO
                costo_unitario = float(p["costo_unitario"])
                costo_total = round(float(cantidad) * costo_unitario, 2)

            nuevo_stock = round(stock_anterior - float(cantidad), 2)
            nuevo_costo_total = round(nuevo_stock * float(p["costo_unitario"]), 2)

            cursor.execute("UPDATE productos SET stock_actual = ? WHERE id = ?", (nuevo_stock, producto_id))

            cursor.execute("""
                INSERT INTO movimientos_inventario (
                    producto_id, fecha, tipo_movimiento, tipo_documento, numero_documento,
                    cantidad, costo_unitario, costo_total, saldo_cantidad, saldo_costo_unitario, saldo_costo_total,
                    asiento_id, observaciones
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (producto_id, fecha or PeriodService.get_fecha_trabajo(db_path=db_path), tipo_movimiento, tipo_documento, numero_documento,
                  float(cantidad), round(costo_unitario, 4), round(costo_total, 2),
                  nuevo_stock, round(float(p["costo_unitario"]), 4), nuevo_costo_total,
                  asiento_id, observaciones))

            conn.commit()
            return round(costo_total, 2), round(costo_unitario, 4), nuevo_stock
        finally:
            conn.close()

    @staticmethod
    def get_kardex(producto_id, metodo="PROMEDIO", db_path=None):
        """
        Retrieves full Kardex statement with standard format: Entradas, Salidas, Saldos.
        """
        conn = get_db_contable(db_path)
        try:
            p = conn.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
            if not p:
                return None

            movs = conn.execute("""
                SELECT * FROM movimientos_inventario
                WHERE producto_id = ?
                ORDER BY fecha ASC, id ASC
            """, (producto_id,)).fetchall()

            kardex_rows = []
            for m in movs:
                tipo = m["tipo_movimiento"]
                is_entry = "ENTRADA" in tipo or "INICIAL" in tipo or "POSITIVO" in tipo
                
                row = {
                    "id": m["id"],
                    "fecha": m["fecha"],
                    "tipo_movimiento": m["tipo_movimiento"],
                    "documento": f"{m['tipo_documento']} {m['numero_documento']}",
                    "observaciones": m["observaciones"],
                    "entrada_cant": m["cantidad"] if is_entry else 0.0,
                    "entrada_cu": m["costo_unitario"] if is_entry else 0.0,
                    "entrada_total": m["costo_total"] if is_entry else 0.0,
                    "salida_cant": m["cantidad"] if not is_entry else 0.0,
                    "salida_cu": m["costo_unitario"] if not is_entry else 0.0,
                    "salida_total": m["costo_total"] if not is_entry else 0.0,
                    "saldo_cant": m["saldo_cantidad"],
                    "saldo_cu": m["saldo_costo_unitario"],
                    "saldo_total": m["saldo_costo_total"]
                }
                kardex_rows.append(row)

            return {
                "producto": dict(p),
                "metodo": metodo,
                "movimientos": kardex_rows,
                "total_entradas_cant": sum(r["entrada_cant"] for r in kardex_rows),
                "total_salidas_cant": sum(r["salida_cant"] for r in kardex_rows),
                "stock_final": p["stock_actual"],
                "costo_unitario_actual": p["costo_unitario"],
                "valor_total_inventario": round(p["stock_actual"] * p["costo_unitario"], 2)
            }
        finally:
            conn.close()
