# Agente Generador de Casos - Generador Paramétrico de Escenarios Contables Coherentes
import random
import json
from datetime import date, timedelta
from tools.simulation_tools import create_simulation_case
from services.inventory_service import InventoryService
from services.tax_service import TaxService

class CaseGeneratorAgent:
    def __init__(self):
        self.name = "AgenteGeneradorCasos"

    def generate_case(self, simulacion_id, orden=1, tipo_operacion="VENTA_CONTADO", nivel=1):
        """
        Generates a parameterized, coherent accounting case with source document and solution.
        """
        fecha = (date.today() + timedelta(days=orden)).isoformat()
        
        if tipo_operacion == "VENTA_CONTADO":
            cant_arroz = random.randint(5, 20)
            pv_arroz = 5.20
            subtotal = round(cant_arroz * pv_arroz, 2)
            iva = round(subtotal * 0.15, 2)
            total = round(subtotal + iva, 2)
            costo = round(cant_arroz * 3.80, 2)
            num_fac = f"FAC-GEN-{random.randint(100, 999)}"

            enunciado = f"Se realiza una venta de contado de {cant_arroz} sacos de Arroz Flor Especial 5kg a $5.20 c/u + IVA 15%. Se cobra íntegramente en efectivo. Factura {num_fac}."
            
            solucion = {
                "asiento_venta": [
                    {"cuenta": "1.1.01", "nombre": "Caja General", "debe": total, "haber": 0.0},
                    {"cuenta": "4.1.01", "nombre": "Ingresos por Ventas de Bienes", "debe": 0.0, "haber": subtotal},
                    {"cuenta": "2.1.02", "nombre": "IVA Ventas (Débito Fiscal)", "debe": 0.0, "haber": iva}
                ],
                "asiento_costo": [
                    {"cuenta": "5.1.01", "nombre": "Costo de Mercaderías Vendidas", "debe": costo, "haber": 0.0},
                    {"cuenta": "1.1.06", "nombre": "Inventario de Mercaderías", "debe": 0.0, "haber": costo}
                ]
            }

            pistas = [
                "Ingresa el dinero en efectivo a Caja General por el valor total de la factura.",
                "Registra el ingreso en la cuenta de ventas por el subtotal y el IVA en el pasivo tributario.",
                "Recuerda registrar la salida física y contable del inventario valorado al costo."
            ]
            explicacion = "Las ventas de inventario perpetuo requieren contabilizar el ingreso comercial y la baja de existencias al costo de adquisición."

            return create_simulation_case(
                simulacion_id, orden, f"Venta de Contado Paramétrica #{orden}", fecha,
                enunciado, "FACTURA_VENTA", num_fac,
                {"subtotal": subtotal, "iva": iva, "total": total, "costo": costo},
                solucion, pistas, explicacion
            )

        return {"status": "TIPO_NO_SOPORTADO"}
