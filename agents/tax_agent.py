# Agente Tributario - Consulta y Cálculo sin inventar tasas
from tools.financial_tools import get_tax_configuration, calculate_tax

class TaxAgent:
    def __init__(self):
        self.name = "AgenteTributario"

    def handle_tax_query(self, query):
        taxes = get_tax_configuration()
        taxes_summary = ", ".join([f"{t['nombre']} ({t['porcentaje']}%)" for t in taxes])
        
        return {
            "agente": self.name,
            "tema": "CONFIGURACION_TRIBUTARIA",
            "respuesta": f"Configuración tributaria activa (Normativa SRI Ecuador):\nActualmente se encuentran configurados los siguientes tributos: {taxes_summary}. Las tasas nunca se asumen arbitrariamente y siempre son consultadas desde la tabla de parámetros.",
            "impuestos_disponibles": taxes
        }
