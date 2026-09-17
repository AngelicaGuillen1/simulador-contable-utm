# Simulation & University Practice Routes
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g
from routes.auth import login_required, roles_required
from services.simulation_service import SimulationService
from services.evaluation_service import EvaluationService
from services.accounting_service import AccountingService
from models import get_db_connection
import json

simulations_bp = Blueprint("simulations", __name__)

@simulations_bp.route("/simulador")
@login_required
def list_simulations():
    sims = SimulationService.get_simulations()
    attempts = SimulationService.get_student_attempts(estudiante_id=g.user["id"] if g.user else 3)
    return render_template("simulations/list.html", simulaciones=sims, mis_intentos=attempts)

@simulations_bp.route("/simulador/<int:simulacion_id>/iniciar")
@login_required
def start_simulation(simulacion_id):
    intento_id = SimulationService.start_attempt(simulacion_id, g.user["id"] if g.user else 3)
    return redirect(url_for("simulations.play_simulation", simulacion_id=simulacion_id, intento_id=intento_id))

@simulations_bp.route("/simulador/<int:simulacion_id>/jugar")
@login_required
def play_simulation(simulacion_id):
    intento_id = request.args.get("intento_id", type=int)
    if not intento_id:
        intento_id = SimulationService.start_attempt(simulacion_id, g.user["id"] if g.user else 3)

    sim = SimulationService.get_simulation_by_id(simulacion_id)
    cuentas = AccountingService.get_accounts(active_only=True)

    caso_index = request.args.get("caso_index", 0, type=int)
    caso_actual = sim["casos"][caso_index] if sim and sim.get("casos") and caso_index < len(sim["casos"]) else None

    return render_template(
        "simulations/play.html",
        simulacion=sim,
        intento_id=intento_id,
        caso_actual=caso_actual,
        caso_index=caso_index,
        total_casos=len(sim["casos"]) if sim and sim.get("casos") else 0,
        cuentas=cuentas
    )

@simulations_bp.route("/simulador/evaluar", methods=["POST"])
@login_required
def submit_attempt():
    data = request.get_json() or {}
    intento_id = data.get("intento_id")
    caso_id = data.get("caso_id")
    lineas = data.get("lineas", [])
    pistas_usadas = data.get("pistas_usadas", 0)
    tiempo_segundos = data.get("tiempo_segundos", 0)

    try:
        resultado = EvaluationService.evaluate_attempt(
            intento_id, caso_id, lineas,
            pistas_usadas=pistas_usadas, tiempo_segundos=tiempo_segundos,
            usuario_id=g.user["id"] if g.user else 3
        )
        return jsonify({"success": True, "evaluacion": resultado})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@simulations_bp.route("/evaluaciones")
@login_required
def evaluations():
    estudiante_id = g.user["id"] if g.user and g.user["rol_nombre"] == "Estudiante" else None
    intentos = SimulationService.get_student_attempts(estudiante_id=estudiante_id)
    return render_template("simulations/evaluations.html", intentos=intentos)

@simulations_bp.route("/docente/panel")
@login_required
@roles_required("Docente", "Administrador")
def teacher_panel():
    analytics = SimulationService.get_teacher_analytics()
    conn = get_db_connection()
    try:
        estudiantes = conn.execute("""
            SELECT u.id, u.nombre_completo, u.email,
                   (SELECT COUNT(*) FROM intentos_estudiante WHERE estudiante_id = u.id) as total_intentos,
                   (SELECT AVG(puntuacion_total) FROM intentos_estudiante WHERE estudiante_id = u.id AND estado = 'COMPLETADO') as promedio_nota
            FROM usuarios u
            WHERE u.rol_id = 3 AND u.activo = 1
        """).fetchall()
        
        simulaciones = SimulationService.get_simulations()

        return render_template(
            "simulations/teacher_panel.html",
            analytics=analytics,
            estudiantes=[dict(e) for e in estudiantes],
            simulaciones=simulaciones
        )
    finally:
        conn.close()
