# AI Accounting Tutor Blueprint & Interactive Chat UI
from flask import Blueprint, render_template, request, jsonify, g
from routes.auth import login_required
from agents.tutor_agent import TutorAgent
from agents.orchestrator import OrchestratorAgent
from models import get_db_contable

tutor_bp = Blueprint("tutor", __name__, url_prefix="/tutor")


def _en_modo_examen(context):
    """
    Determina si la consulta se realiza dentro de una evaluación en Modo Examen.
    Cuando el caso pertenece a una simulación con modo_examen = 1, el Tutor IA restringe
    la entrega de solución para preservar la validez académica de la evaluación.
    """
    caso_id = (context or {}).get("caso_id")
    if not caso_id:
        return False
    conn = get_db_contable()
    try:
        row = conn.execute("""
            SELECT s.modo_examen
            FROM casos_simulacion c JOIN simulaciones s ON c.simulacion_id = s.id
            WHERE c.id = ?
        """, (caso_id,)).fetchone()
        return bool(row and row["modo_examen"])
    finally:
        conn.close()


@tutor_bp.route("/")
@login_required
def chat():
    return render_template("tutor/chat.html")


@tutor_bp.route("/preguntar", methods=["POST"])
@login_required
def ask():
    data = request.get_json() or {}
    pregunta = data.get("pregunta", "").strip()
    nivel_ayuda = data.get("nivel_ayuda", "PISTA")
    context = data.get("context", {}) or {}
    modo_examen = bool(data.get("modo_examen", False)) or _en_modo_examen(context)

    if not pregunta:
        return jsonify({"error": "La pregunta no puede estar vacía."}), 400

    if modo_examen:
        tutor = TutorAgent()
        respuesta = tutor.answer_question(pregunta, nivel_ayuda=nivel_ayuda,
                                          context=context, modo_examen=True)
        respuesta["modo_examen"] = True
        return jsonify(respuesta)

    orchestrator = OrchestratorAgent()
    resp = orchestrator.process_request(pregunta, context=context)
    return jsonify(resp)
