# Agente Tutor Contable IA - Andamiaje Pedagógico Progresivo
import json
from models import get_db_connection

class TutorAgent:
    """
    Agente Pedagógico que orienta al estudiante en el razonamiento contable.
    Nunca entrega la respuesta directa en modo examen; usa andamiaje progresivo:
    1. Orientación -> 2. Pista -> 3. Explicación conceptual -> 4. Verificación.
    """
    def __init__(self):
        self.name = "TutorContableIA"

    def answer_question(self, user_question, nivel_ayuda="PISTA", context=None, modo_examen=False):
        import unicodedata
        normalizado = unicodedata.normalize("NFKD", user_question or "")
        q = "".join(c for c in normalizado if not unicodedata.combining(c)).lower()
        context = context or {}
        caso_id = context.get("caso_id")

        if modo_examen:
            return {
                "agente": self.name,
                "modo": "EXAMEN_ACTIVO",
                "respuesta": "En Modo Examen el Tutor IA tiene restringida la entrega de pistas detalladas para garantizar la validez académica de la evaluación. Revisa cuidadosamente el documento fuente y los principios de la partida doble."
            }

        # Context-specific hint if case_id is provided
        if caso_id:
            conn = get_db_connection()
            try:
                caso = conn.execute("SELECT * FROM casos_simulacion WHERE id = ?", (caso_id,)).fetchone()
                if caso:
                    pistas = json.loads(caso["pistas_json"]) if caso["pistas_json"] else []
                    if "por que" in q or "porque" in q or "explic" in q or "significa" in q:
                        return {
                            "agente": self.name,
                            "tipo_ayuda": "EXPLICACION_CONCEPTUAL",
                            "respuesta": f"Explicación para '{caso['titulo']}':\n{caso['explicacion_pedagogica']}"
                        }
                    elif pistas:
                        idx = min(len(pistas) - 1, 0 if nivel_ayuda == "ORIENTACION" else (1 if nivel_ayuda == "PISTA" else len(pistas) - 1))
                        return {
                            "agente": self.name,
                            "tipo_ayuda": f"PISTA_NIVEL_{idx+1}",
                            "respuesta": f"Pista: {pistas[idx]}"
                        }
            finally:
                conn.close()

        # General Accounting Knowledge Base Rules
        if "debe" in q and "haber" in q:
            return {
                "agente": self.name,
                "tipo_ayuda": "CONCEPTO_PARTIDA_DOBLE",
                "respuesta": "Regla de Oro de la Partida Doble:\n- Se DEBITAN (Debe): Aumentos de Activo, Aumentos de Gastos y Costos, Disminuciones de Pasivo y Patrimonio.\n- Se ACREDITAN (Haber): Aumentos de Pasivo, Aumentos de Patrimonio, Aumentos de Ingresos, Disminuciones de Activo.\nSiempre debe cumplirse: Total Debe = Total Haber."
            }
        elif "costo de ventas" in q:
            return {
                "agente": self.name,
                "tipo_ayuda": "CONCEPTO_COSTO_VENTAS",
                "respuesta": "El Costo de Ventas refleja el valor de adquisición de las mercaderías que efectivamente salieron del almacén para ser vendidas. Bajo el sistema de inventario perpetuo, en cada venta se debita 'Costo de Mercaderías Vendidas' (cuenta de Costos 5.1.01) y se acredita 'Inventario de Mercaderías' (cuenta de Activo 1.1.06)."
            }
        elif "iva" in q or "retencion" in q or "retención" in q:
            return {
                "agente": self.name,
                "tipo_ayuda": "CONCEPTO_TRIBUTARIO",
                "respuesta": "Tratamiento contable del IVA:\n- En Ventas: El IVA cobrado al cliente es un Pasivo (Débito Fiscal, cuenta 2.1.02) porque es dinero recaudado que debe entregarse al SRI.\n- En Compras: El IVA pagado al proveedor es un Activo (Crédito Tributario, cuenta 1.1.07) compensable al final del mes contra el IVA cobrado."
            }
        elif "arqueo" in q:
            return {
                "agente": self.name,
                "tipo_ayuda": "CONCEPTO_TESORERIA",
                "respuesta": "El Arqueo de Caja compara el dinero físico real (conteo de billetes y monedas) con el saldo contable del Libro Mayor. Si Dinero Físico > Saldo Contable existe un Sobrante de Caja. Si Dinero Físico < Saldo Contable existe un Faltante de Caja."
            }
        elif "depreciacion" in q or "depreciación" in q:
            return {
                "agente": self.name,
                "tipo_ayuda": "CONCEPTO_AJUSTES",
                "respuesta": "La depreciación reconoce el desgaste y obsolescencia de los activos fijos durante su vida útil. Se debita la cuenta de resultados 'Gasto Depreciación de Activos Fijos' (6.1.04) y se acredita la cuenta correctora de activo 'Depreciación Acumulada' (1.2.02, 1.2.04 o 1.2.06)."
            }

        return {
            "agente": self.name,
            "tipo_ayuda": "ORIENTACION_GENERAL",
            "respuesta": "Recuerda analizar la transacción identificando:\n1. ¿Qué hecho económico ocurrió? (Compra, venta, cobro, pago, ajuste).\n2. ¿Qué cuentas intervienen y cuál es su naturaleza (Activo, Pasivo, Patrimonio, Ingreso, Gasto)?\n3. ¿Aumentan o disminuyen?\n4. ¿Qué cuenta debe ir al Debe y cuál al Haber por el mismo valor total?"
        }
