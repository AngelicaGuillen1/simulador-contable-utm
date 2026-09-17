# Documentos Fuente Simulados (facturas, comprobantes, notas, estados bancarios, órdenes)
# Cada operación contable del simulador queda respaldada por uno o varios documentos fuente,
# lo que garantiza la cadena verificable: Documento -> Transacción -> Asiento -> Diario -> Mayor -> Balance -> EEFF.
import json
from models import get_db_connection
from services.audit_service import AuditService

TIPOS_DOCUMENTO = [
    ("FACTURA_VENTA", "Factura de Venta", "factura"),
    ("FACTURA_COMPRA", "Factura de Compra", "factura"),
    ("FACTURA_SERVICIO", "Factura de Servicio", "factura"),
    ("COMPROBANTE_INGRESO", "Comprobante de Ingreso", "comprobante"),
    ("COMPROBANTE_EGRESO", "Comprobante de Egreso", "comprobante"),
    ("COMPROBANTE_CAJA", "Comprobante de Caja", "tesoreria"),
    ("COMPROBANTE_CIERRE", "Comprobante de Cierre Contable", "ajuste"),
    ("NOTA_CREDITO", "Nota de Crédito", "nota"),
    ("NOTA_DEBITO", "Nota de Débito", "nota"),
    ("PAPELETA_DEPOSITO", "Papeleta de Depósito", "banco"),
    ("NOTA_DEBITO_BCO", "Nota de Débito Bancaria", "banco"),
    ("NOTA_CREDITO_BCO", "Nota de Crédito Bancaria", "banco"),
    ("NOTA_BANCARIA", "Nota Bancaria", "banco"),
    ("ESTADO_CUENTA_BANCARIO", "Estado de Cuenta Bancario", "banco"),
    ("ARQUEO_CAJA", "Acta de Arqueo de Caja", "tesoreria"),
    ("ROL_PAGOS", "Rol de Pagos", "nomina"),
    ("ORDEN_COMPRA", "Orden de Compra", "compra"),
    ("COMPROBANTE_AJUSTE", "Comprobante de Ajuste", "ajuste"),
    ("DOCUMENTO_POR_COBRAR", "Documento por Cobrar", "cartera"),
    ("DOCUMENTO_POR_PAGAR", "Documento por Pagar", "cartera"),
    ("DOCUMENTO_INTERNO", "Documento Interno", "ajuste"),
]


class DocumentService:
    @staticmethod
    def register(tipo, numero, fecha, emisor, receptor, monto_total, descripcion="", datos=None,
                 asiento_id=None, simulacion_caso_id=None, db_path=None):
        """Registra un documento fuente. Evita duplicar el mismo tipo+numero+asiento."""
        conn = get_db_connection(db_path)
        try:
            if asiento_id:
                existente = conn.execute("""
                    SELECT id FROM documentos_fuente WHERE tipo = ? AND numero = ? AND asiento_id = ?
                """, (tipo, numero, asiento_id)).fetchone()
                if existente:
                    return existente["id"]

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documentos_fuente
                    (tipo, numero, fecha, emisor, receptor, monto_total, descripcion, datos_json, asiento_id, simulacion_caso_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (tipo, numero, fecha, emisor, receptor, round(float(monto_total), 2), descripcion,
                  json.dumps(datos, ensure_ascii=False) if datos is not None else None,
                  asiento_id, simulacion_caso_id))
            doc_id = cursor.lastrowid
            conn.commit()
            AuditService.log(1, "sistema", "CREAR_DOCUMENTO", "DOCUMENTOS", doc_id, None,
                             {"tipo": tipo, "numero": numero, "monto": round(float(monto_total), 2)},
                             db_path=db_path)
            return doc_id
        finally:
            conn.close()

    @staticmethod
    def get_documents(tipo=None, fecha_inicio=None, fecha_fin=None, limit=300, db_path=None):
        conn = get_db_connection(db_path)
        try:
            query = """
                SELECT d.*, a.numero_asiento, a.glosa as asiento_glosa, a.estado as asiento_estado
                FROM documentos_fuente d
                LEFT JOIN asientos a ON d.asiento_id = a.id
                WHERE 1 = 1
            """
            params = []
            if tipo:
                query += " AND d.tipo = ?"
                params.append(tipo)
            if fecha_inicio:
                query += " AND d.fecha >= ?"
                params.append(fecha_inicio)
            if fecha_fin:
                query += " AND d.fecha <= ?"
                params.append(fecha_fin)
            query += " ORDER BY d.fecha DESC, d.id DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(query, params).fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_document(doc_id, db_path=None):
        conn = get_db_connection(db_path)
        try:
            row = conn.execute("""
                SELECT d.*, a.numero_asiento, a.glosa as asiento_glosa, a.estado as asiento_estado
                FROM documentos_fuente d
                LEFT JOIN asientos a ON d.asiento_id = a.id
                WHERE d.id = ?
            """, (doc_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_tipos_resumen(db_path=None):
        """Resumen por tipo de documento con conteo y monto acumulado."""
        conn = get_db_connection(db_path)
        try:
            rows = conn.execute("""
                SELECT tipo, COUNT(*) as cantidad, COALESCE(SUM(monto_total), 0) as monto_total
                FROM documentos_fuente
                GROUP BY tipo
                ORDER BY tipo ASC
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_etiqueta(tipo):
        for codigo, etiqueta, _grupo in TIPOS_DOCUMENTO:
            if codigo == tipo:
                return etiqueta
        return tipo.replace("_", " ").title() if tipo else "Documento"
