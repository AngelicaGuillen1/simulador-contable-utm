# Agente Evaluador - Análisis de Desempeño, Dificultad y Patrones de Error
from models import get_db_contable
from services.simulation_service import SimulationService

class EvaluatorAgent:
    def __init__(self):
        self.name = "AgenteEvaluador"

    def analyze_student_performance(self, estudiante_id=None):
        conn = get_db_contable()
        try:
            query = """
                SELECT d.*, c.titulo as caso_titulo, s.titulo as simulacion_titulo, s.nivel
                FROM detalle_intentos d
                JOIN casos_simulacion c ON d.caso_id = c.id
                JOIN intentos_estudiante i ON d.intento_id = i.id
                JOIN simulaciones s ON i.simulacion_id = s.id
            """
            params = []
            if estudiante_id:
                query += " WHERE i.estudiante_id = ?"
                params.append(estudiante_id)

            rows = conn.execute(query, params).fetchall()
            if not rows:
                return {"agente": self.name, "mensaje": "Aún no se registran intentos completados para analizar."}

            total_intentos = len(rows)
            correctos = sum(1 for r in rows if r["resultado"] == "CORRECTO")
            parciales = sum(1 for r in rows if r["resultado"] == "PARCIALMENTE_CORRECTO")
            incorrectos = sum(1 for r in rows if r["resultado"] == "INCORRECTO")
            promedio = sum(r["puntuacion"] for r in rows) / total_intentos

            # Diagnose error patterns
            diagnostico = []
            if incorrectos > correctos:
                diagnostico.append("Se detecta dificultad en la asignación correcta de la columna Debe vs Haber en cuentas de activo y pasivo.")
            if parciales > 0:
                diagnostico.append("Se observan errores menores en el cálculo de bases imponibles o importes con IVA.")
            else:
                diagnostico.append("Excelente asimilación de la partida doble y el ciclo contable integral.")

            return {
                "agente": self.name,
                "total_evaluaciones": total_intentos,
                "porcentaje_aciertos": round((correctos / total_intentos) * 100, 1),
                "promedio_general": round(promedio, 2),
                "distribucion": {"correctos": correctos, "parciales": parciales, "incorrectos": incorrectos},
                "diagnostico_pedagogico": diagnostico
            }
        finally:
            conn.close()
