# Tax Service - Configurable Taxes & Withholdings (SRI Ecuador Standards)
import sqlite3
from models import get_db_connection

class TaxService:
    @staticmethod
    def get_taxes(db_path=None):
        conn = get_db_connection(db_path)
        try:
            rows = conn.execute("SELECT * FROM impuestos WHERE activo = 1 ORDER BY id ASC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_tax_by_code(codigo, db_path=None):
        conn = get_db_connection(db_path)
        try:
            row = conn.execute("SELECT * FROM impuestos WHERE codigo = ? AND activo = 1", (codigo,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def calculate_tax(base_imponible, codigo_impuesto=None, tipo="IVA_VENTAS", db_path=None):
        conn = get_db_connection(db_path)
        try:
            if codigo_impuesto:
                row = conn.execute("SELECT * FROM impuestos WHERE codigo = ? AND activo = 1", (codigo_impuesto,)).fetchone()
            else:
                row = conn.execute("SELECT * FROM impuestos WHERE tipo = ? AND activo = 1 ORDER BY id DESC LIMIT 1", (tipo,)).fetchone()
            
            if not row:
                raise ValueError(f"No existe configuración tributaria activa para el tipo o código: {codigo_impuesto or tipo}")
            
            impuesto = dict(row)
            porcentaje = float(impuesto["porcentaje"])
            base = float(base_imponible)
            valor_calculado = round((base * porcentaje) / 100.0, 2)

            return {
                "codigo": impuesto["codigo"],
                "nombre": impuesto["nombre"],
                "porcentaje": porcentaje,
                "base": base,
                "base_imponible": base,
                "valor": valor_calculado,
                "total": round(base + valor_calculado, 2),
                "cuenta_contable_id": impuesto["cuenta_contable_id"]
            }
        finally:
            conn.close()

    @staticmethod
    def update_tax(impuesto_id, nombre, porcentaje, tipo, cuenta_contable_id, activo=1, db_path=None):
        conn = get_db_connection(db_path)
        try:
            conn.execute("""
                UPDATE impuestos
                SET nombre = ?, porcentaje = ?, tipo = ?, cuenta_contable_id = ?, activo = ?
                WHERE id = ?
            """, (nombre, float(porcentaje), tipo, cuenta_contable_id, int(activo), impuesto_id))
            conn.commit()
            return True
        finally:
            conn.close()
