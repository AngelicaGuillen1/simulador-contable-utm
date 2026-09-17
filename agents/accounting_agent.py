# Agente Contable - Especialista en Cuentas, Partida Doble y Estados Financieros
from tools.accounting_tools import get_chart_of_accounts, get_account_balance, validate_journal_entry
from tools.financial_tools import generate_trial_balance, generate_income_statement, generate_balance_sheet, generate_cash_flow

class AccountingAgent:
    def __init__(self):
        self.name = "AgenteContable"

    def handle_query(self, query):
        q = query.lower()
        if "balance general" in q or "situacion financiera" in q or "situación" in q:
            bs = generate_balance_sheet()
            estado_str = "CUADRADO (Activo = Pasivo + Patrimonio)" if bs["balanceado"] else f"DESCUADRADO (Diferencia: ${bs['diferencia']:,.2f})"
            return {
                "agente": self.name,
                "tema": "ESTADO_SITUACION_FINANCIERA",
                "respuesta": f"Estado de Situación Financiera de Comercial y Servicios Nueva Esperanza:\n- Total Activos: ${bs['total_activo']:,.2f}\n- Total Pasivos: ${bs['total_pasivo']:,.2f}\n- Total Patrimonio: ${bs['total_patrimonio']:,.2f}\n- Ecuación Contable: {estado_str}.",
                "datos": bs
            }
        elif "resultado" in q or "utilidad" in q or "ganancia" in q or "perdida" in q:
            inc = generate_income_statement()
            return {
                "agente": self.name,
                "tema": "ESTADO_RESULTADOS",
                "respuesta": f"Estado de Resultados del Período:\n- Ingresos por Ventas de Bienes: ${inc['ventas_bienes']:,.2f}\n- Ingresos por Servicios: ${inc['ingresos_servicios']:,.2f}\n- Costo de Mercaderías Vendidas: ${inc['costo_ventas']:,.2f}\n- Utilidad Bruta: ${inc['utilidad_bruta']:,.2f}\n- Gastos Operacionales: ${inc['total_gastos_operacionales']:,.2f}\n- Utilidad Neta del Ejercicio: ${inc['utilidad_neta']:,.2f}.",
                "datos": inc
            }
        elif "comprobacion" in q or "comprobación" in q or "sumas" in q:
            trial = generate_trial_balance()
            return {
                "agente": self.name,
                "tema": "BALANCE_COMPROBACION",
                "respuesta": f"Balance de Comprobación:\n- Total Débitos: ${trial['total_debitos']:,.2f} | Total Créditos: ${trial['total_creditos']:,.2f}\n- Total Saldo Deudor: ${trial['total_saldo_deudor']:,.2f} | Total Saldo Acreedor: ${trial['total_saldo_acreedor']:,.2f}\n- Estado: {'Balanceado correctamente' if trial['cuadrado_saldos'] else 'Descuadrado'}.",
                "datos": trial
            }
        else:
            cuentas = get_chart_of_accounts()
            return {
                "agente": self.name,
                "tema": "PLAN_DE_CUENTAS",
                "respuesta": f"El Plan de Cuentas estructurado cuenta con {len(cuentas)} cuentas codificadas bajo normas NIIF y clasificación jerárquica (Activo, Pasivo, Patrimonio, Ingresos, Costos y Gastos).",
                "datos": cuentas[:10]
            }
