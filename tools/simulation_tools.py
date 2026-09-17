# Structured Agent Tools - Simulation, Evaluation, Audit & Diagnostics
from services.simulation_service import SimulationService
from services.evaluation_service import EvaluationService
from services.audit_service import AuditService
from models import get_db_connection
import json

def create_simulation_case(simulacion_id, orden, titulo, fecha, enunciado, doc_tipo, doc_numero, datos_transaccion, solucion_esperada, pistas, explicacion, db_path=None):
    """Creates a new simulation case with expected journal entry and progressive hints."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO casos_simulacion (
                simulacion_id, orden, titulo, fecha_transaccion, enunciado,
                documento_fuente_tipo, documento_fuente_numero, datos_transaccion_json,
                solucion_esperada_json, pistas_json, explicacion_pedagogica
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (int(simulacion_id), int(orden), titulo, fecha, enunciado, doc_tipo, doc_numero,
              json.dumps(datos_transaccion) if isinstance(datos_transaccion, (dict, list)) else datos_transaccion,
              json.dumps(solucion_esperada) if isinstance(solucion_esperada, (dict, list)) else solucion_esperada,
              json.dumps(pistas) if isinstance(pistas, (dict, list)) else pistas,
              explicacion))
        caso_id = cursor.lastrowid
        conn.commit()
        return {"caso_id": caso_id, "status": "CREADO"}
    finally:
        conn.close()

def evaluate_student_attempt(intento_id, caso_id, user_lines, pistas_usadas=0, tiempo_segundos=0, usuario_id=3, db_path=None):
    """Evaluates a student attempt (0-100 score) with full rubric and pedagogical feedback."""
    return EvaluationService.evaluate_attempt(
        int(intento_id), int(caso_id), user_lines,
        pistas_usadas=int(pistas_usadas), tiempo_segundos=int(tiempo_segundos),
        usuario_id=usuario_id, db_path=db_path
    )

def generate_feedback(caso_id, student_lines, db_path=None):
    """Generates pedagogical explanation and hints for a case without saving attempt."""
    conn = get_db_connection(db_path)
    try:
        caso = conn.execute("SELECT * FROM casos_simulacion WHERE id = ?", (int(caso_id),)).fetchone()
        if not caso:
            return "Caso no encontrado."
        return {
            "titulo": caso["titulo"],
            "explicacion": caso["explicacion_pedagogica"],
            "pistas": json.loads(caso["pistas_json"]) if caso["pistas_json"] else []
        }
    finally:
        conn.close()

def get_student_progress(estudiante_id, db_path=None):
    """Retrieves all student attempts and completed simulations."""
    return SimulationService.get_student_attempts(estudiante_id=int(estudiante_id), db_path=db_path)

def audit_transaction(registro_id, modulo=None, db_path=None):
    """Retrieves immutable audit history for a specific transaction or module."""
    return AuditService.get_logs(modulo=modulo, limit=50, db_path=db_path)
