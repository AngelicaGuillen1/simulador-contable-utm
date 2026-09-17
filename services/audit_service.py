# Audit and Traceability Service
import sqlite3
import json
from datetime import datetime
from models import get_db_connection

class AuditService:
    @staticmethod
    def log(usuario_id, username, accion, modulo, registro_id=None, valor_anterior=None, valor_nuevo=None, ip_origen="127.0.0.1", agente_utilizado=None, herramienta_ejecutada=None, db_path=None):
        conn = get_db_connection(db_path)
        try:
            val_ant_str = json.dumps(valor_anterior, ensure_ascii=False) if isinstance(valor_anterior, (dict, list)) else (str(valor_anterior) if valor_anterior is not None else None)
            val_nuev_str = json.dumps(valor_nuevo, ensure_ascii=False) if isinstance(valor_nuevo, (dict, list)) else (str(valor_nuevo) if valor_nuevo is not None else None)
            
            conn.execute("""
                INSERT INTO auditoria (
                    usuario_id, username, accion, modulo, registro_id,
                    valor_anterior, valor_nuevo, ip_origen, agente_utilizado, herramienta_ejecutada
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (usuario_id, username, accion, modulo, str(registro_id) if registro_id else None,
                  val_ant_str, val_nuev_str, ip_origen, agente_utilizado, herramienta_ejecutada))
            conn.commit()
        except Exception as e:
            print(f"Error logging audit: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_logs(modulo=None, usuario_id=None, limit=100, db_path=None):
        conn = get_db_connection(db_path)
        try:
            query = "SELECT * FROM auditoria WHERE 1=1"
            params = []
            if modulo:
                query += " AND modulo = ?"
                params.append(modulo)
            if usuario_id:
                query += " AND usuario_id = ?"
                params.append(usuario_id)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
