# Agente Orquestador - Coordinador Central y Enrutador de Intenciones
import re
import json
import unicodedata
from tools import (
    get_chart_of_accounts, get_account, get_account_balance, validate_journal_entry,
    create_journal_entry, get_product, get_inventory, create_sale, create_purchase,
    create_service_transaction, calculate_tax, get_tax_configuration,
    generate_trial_balance, generate_income_statement, generate_balance_sheet, generate_cash_flow
)


def normalizar(texto):
    """Normaliza el texto (minúsculas y sin tildes) para reconocer intenciones escritas sin acentos."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


class OrchestratorAgent:
    """
    Analiza la solicitud del usuario o estudiante, identifica la intención operativa o pedagógica,
    y delega a los agentes y herramientas estructuradas correspondientes.
    """
    def __init__(self):
        self.name = "AgenteOrquestador"

    def process_request(self, user_query, context=None):
        query = normalizar(user_query)
        context = context or {}

        # 1. Intención: Pregunta Conceptual / Tutor Contable
        if any(w in query for w in ["por que", "porque", "como afecta", "que significa", "pista",
                                    "ayuda", "explicar", "explica", "naturaleza", "debe o haber",
                                    "debito", "acredita"]):
            from agents.tutor_agent import TutorAgent
            tutor = TutorAgent()
            return tutor.answer_question(user_query, context=context)

        # 2. Intención: Auditoría / Detección de Anomalías
        if any(w in query for w in ["auditar", "auditoria", "descuadre", "descuadr", "inconsistencia",
                                    "anomalia", "revisar balance", "verificar", "integridad"]):
            from agents.audit_agent import AuditAgent
            auditor = AuditAgent()
            return auditor.audit_system()

        # 3. Intención: Consulta Tributaria
        if any(w in query for w in ["iva", "retencion", "impuesto", "tasa", "tributari", "sri"]):
            from agents.tax_agent import TaxAgent
            tax_agent = TaxAgent()
            return tax_agent.handle_tax_query(user_query)

        # 4. Intención: Consulta de Inventario / Kardex
        if any(w in query for w in ["inventario", "stock", "kardex", "existencia", "fifo", "promedio"]):
            from agents.inventory_agent import InventoryAgent
            inv_agent = InventoryAgent()
            return inv_agent.handle_query(user_query)

        # 5. Intención: Consulta Contable y Estados Financieros
        if any(w in query for w in ["balance", "resultado", "diario", "mayor", "patrimonio", "activo",
                                    "pasivo", "utilidad", "estado financiero", "cuenta"]):
            from agents.accounting_agent import AccountingAgent
            acc_agent = AccountingAgent()
            return acc_agent.handle_query(user_query)

        # Default: Respuesta de orientación general
        return {
            "agente": self.name,
            "intencion": "ORIENTACION_GENERAL",
            "respuesta": "Hola, soy el Agente Orquestador del Simulador Contable. Puedo asistirte en la consulta de cuentas contables, cálculo de impuestos, revisión de Kardex, auditoría de balances o resolver dudas conceptuales con el Tutor IA.",
            "herramientas_disponibles": [
                "get_chart_of_accounts", "get_account_balance", "validate_journal_entry",
                "get_inventory", "calculate_tax", "generate_balance_sheet"
            ]
        }
