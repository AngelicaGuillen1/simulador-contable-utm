# Agente Auditor - Detección de Descuadres, Inconsistencias y Control Interno
from tools.financial_tools import generate_trial_balance, generate_balance_sheet
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from models import get_db_connection

class AuditAgent:
    def __init__(self):
        self.name = "AgenteAuditor"

    def audit_system(self, db_path=None):
        anomalias = []
        conn = get_db_connection(db_path)
        try:
            # 1. Audit Journal balance for all entries
            asientos = conn.execute("SELECT id, numero_asiento, fecha, glosa FROM asientos WHERE estado = 'CONTABILIZADO'").fetchall()
            for a in asientos:
                row = conn.execute("""
                    SELECT SUM(debe) as total_debe, SUM(haber) as total_haber
                    FROM detalle_asientos WHERE asiento_id = ?
                """, (a["id"],)).fetchone()
                debe = round(float(row["total_debe"] or 0.0), 2)
                haber = round(float(row["total_haber"] or 0.0), 2)
                if abs(debe - haber) > 0.01:
                    anomalias.append(f"Asiento #{a['numero_asiento']} ({a['glosa']}) descuadrado: Debe ${debe:,.2f} != Haber ${haber:,.2f}.")

            # 2. Audit Balance Sheet equation
            bs = generate_balance_sheet(db_path=db_path)
            if not bs["balanceado"]:
                anomalias.append(f"Desbalance en Estado de Situación Financiera: Activo (${bs['total_activo']:,.2f}) != Pasivo + Patrimonio (${bs['total_pasivo_y_patrimonio']:,.2f}).")

            # 3. Audit Negative Stocks
            neg_prods = conn.execute("SELECT codigo, descripcion, stock_actual FROM productos WHERE stock_actual < 0").fetchall()
            for p in neg_prods:
                anomalias.append(f"Stock negativo en producto '{p['descripcion']}' ({p['codigo']}): {p['stock_actual']} unidades.")

            # 4. Audit Cash Balances
            cajas = conn.execute("SELECT id, nombre, cuenta_contable_id FROM cajas").fetchall()
            for c in cajas:
                sal = AccountingService.get_account_balance(c["cuenta_contable_id"], db_path=db_path)
                if sal < 0:
                    anomalias.append(f"Saldo acreedor anómalo en Caja '{c['nombre']}': ${sal:,.2f}.")

            estado_general = "INTEGRIDAD_VERIFICADA" if len(anomalias) == 0 else "ANOMALIAS_DETECTADAS"

            return {
                "agente": self.name,
                "estado_auditoria": estado_general,
                "total_asientos_auditados": len(asientos),
                "total_anomalias": len(anomalias),
                "anomalias_detectadas": anomalias,
                "mensaje": "La auditoría no detectó inconsistencias contables ni descuadres." if len(anomalias) == 0 else f"Se detectaron {len(anomalias)} hallazgos que requieren revisión."
            }
        finally:
            conn.close()
