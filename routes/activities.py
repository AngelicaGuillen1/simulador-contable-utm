# -*- coding: utf-8 -*-
"""Rutas del módulo de ACTIVIDADES del syllabus (Contabilidad I).

Rutas de estudiante (aisladas por session['user_id']):
    GET  /mis-actividades
    GET  /mis-actividades/<id>
    POST /mis-actividades/<id>/iniciar

Rutas de docente / administrador (roles_required):
    GET  /docente/actividades
    GET  /docente/actividades/<id>
    POST /docente/actividades/nueva
    POST /docente/actividades/<id>/asignar

Todos los endpoints devuelven JSON cuando la petición lo pide (`?formato=json` o cabecera
`Accept: application/json`), además de la vista HTML.
"""

from flask import (Blueprint, abort, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)

from models import get_db_connection
from routes.auth import login_required, roles_required
from services.activity_service import (
    ActivityService, ActividadNoAsignada, ErrorActividad,
)
from services.audit_service import AuditService

activities_bp = Blueprint("activities", __name__)


# --------------------------------------------------------------------------- Utilidades
def _quiere_json():
    """True si el cliente pide la representación JSON del recurso."""
    if (request.args.get("formato") or "").lower() == "json":
        return True
    acepta = (request.headers.get("Accept") or "").lower()
    return "application/json" in acepta and "text/html" not in acepta


def _usuario_actual():
    return int(session.get("user_id"))


def _datos_peticion():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form


def _error(error, redireccion=None):
    """Responde el error en JSON o, en HTML, con aviso y redirección."""
    if _quiere_json():
        return jsonify({"success": False, "error": error.mensaje,
                        "codigo": getattr(error, "codigo", "VALIDACION")}), error.estado_http
    if error.estado_http in (403, 404):
        abort(error.estado_http)
    flash(error.mensaje, "warning")
    return redirect(redireccion or url_for("activities.mis_actividades"))


# --------------------------------------------------------------------------- Estudiante
@activities_bp.route("/mis-actividades")
@login_required
def mis_actividades():
    estudiante_id = _usuario_actual()
    actividades = ActivityService.listar_actividades_estudiante(estudiante_id)

    if _quiere_json():
        return jsonify({"success": True, "estudiante_id": estudiante_id,
                        "total": len(actividades), "actividades": actividades})

    resumen = {
        "total": len(actividades),
        "pendientes": sum(1 for a in actividades if a["estado_asignacion"] == "PENDIENTE"),
        "en_curso": sum(1 for a in actividades if a["estado_asignacion"] == "EN_CURSO"),
        "entregadas": sum(1 for a in actividades
                          if a["estado_asignacion"] in ("ENTREGADA", "REVISADA")),
        "puntaje_total": round(sum(a.get("puntaje") or 0 for a in actividades), 2),
    }
    return render_template("activities/mis_actividades.html", actividades=actividades,
                           resumen=resumen)


@activities_bp.route("/mis-actividades/<int:actividad_id>")
@login_required
def detalle_actividad(actividad_id):
    estudiante_id = _usuario_actual()
    try:
        asignacion = ActivityService.requiere_actividad_de_estudiante(actividad_id, estudiante_id)
    except ActividadNoAsignada as error:
        return _error(error)

    conn = get_db_connection()
    try:
        eventos = conn.execute("""
            SELECT evento, modulo, detalle, timestamp FROM eventos_estudiante
            WHERE usuario_id = ? AND actividad_id = ?
            ORDER BY timestamp DESC LIMIT 25
        """, (estudiante_id, actividad_id)).fetchall()
        eventos = [dict(f) for f in eventos]
        evidencias = conn.execute("""
            SELECT id, codigo, titulo, tipo, estado, generada_en, modificada_despues
            FROM evidencias WHERE estudiante_id = ? AND actividad_id = ?
            ORDER BY generada_en DESC, id DESC
        """, (estudiante_id, actividad_id)).fetchall()
        evidencias = [dict(f) for f in evidencias]
    finally:
        conn.close()

    if _quiere_json():
        return jsonify({"success": True, "actividad": asignacion, "eventos": eventos,
                        "evidencias": evidencias, "estudiante_id": estudiante_id})

    return render_template("activities/detalle.html", actividad=asignacion, eventos=eventos,
                           evidencias=evidencias)


@activities_bp.route("/mis-actividades/<int:actividad_id>/iniciar", methods=["POST"])
@login_required
def iniciar_actividad(actividad_id):
    estudiante_id = _usuario_actual()
    try:
        asignacion = ActivityService.iniciar_actividad(actividad_id, estudiante_id)
    except ErrorActividad as error:
        return _error(error, redireccion=url_for("activities.detalle_actividad",
                                                 actividad_id=actividad_id))

    if _quiere_json():
        return jsonify({"success": True, "mensaje": "Actividad iniciada.",
                        "asignacion": asignacion})

    flash("Actividad %s iniciada. ¡Éxito en tu trabajo!" % asignacion["codigo"], "success")
    return redirect(url_for("activities.detalle_actividad", actividad_id=actividad_id))


# --------------------------------------------------------------------------- Docente
@activities_bp.route("/docente/actividades")
@login_required
@roles_required("Docente", "Administrador")
def docente_actividades():
    filtros = {
        "unidad": request.args.get("unidad"),
        "componente": request.args.get("componente"),
        "estado": request.args.get("estado"),
        "q": request.args.get("q"),
        "estudiante_id": request.args.get("estudiante_id"),
    }
    actividades = ActivityService.listado_docente(filtros)
    estudiantes = ActivityService.estudiantes_activos()

    if _quiere_json():
        return jsonify({"success": True, "total": len(actividades), "filtros": filtros,
                        "actividades": actividades, "estudiantes": estudiantes})

    return render_template("activities/docente_actividades.html", actividades=actividades,
                           estudiantes=estudiantes, filtros=filtros, detalle=None,
                           asignaciones=[])


@activities_bp.route("/docente/actividades/<int:actividad_id>")
@login_required
@roles_required("Docente", "Administrador")
def docente_detalle_actividad(actividad_id):
    actividad = ActivityService.obtener_actividad(actividad_id)
    if not actividad:
        abort(404)

    asignaciones = ActivityService.resumen_asignaciones(actividad_id)

    if _quiere_json():
        return jsonify({"success": True, "actividad": actividad, "asignaciones": asignaciones})

    actividades = ActivityService.listado_docente({"unidad": actividad.get("unidad")})
    return render_template("activities/docente_actividades.html", actividades=actividades,
                           estudiantes=ActivityService.estudiantes_activos(),
                           filtros={"unidad": actividad.get("unidad")},
                           detalle=actividad, asignaciones=asignaciones)


@activities_bp.route("/docente/actividades/nueva", methods=["POST"])
@login_required
@roles_required("Docente", "Administrador")
def nueva_actividad():
    datos = _datos_peticion()
    datos = dict(datos)
    datos["creada_por"] = _usuario_actual()
    datos["modo_practica"] = bool(datos.get("modo_practica"))
    datos["tutor_ia"] = bool(datos.get("tutor_ia"))
    datos.setdefault("estado", "ABIERTA")

    try:
        actividad = ActivityService.crear_actividad(datos)
    except ErrorActividad as error:
        return _error(error, redireccion=url_for("activities.docente_actividades"))

    AuditService.log(_usuario_actual(), session.get("username", "docente"),
                     "CREAR_ACTIVIDAD", "ACTIVIDADES", actividad["id"], None,
                     {"codigo": actividad["codigo"], "titulo": actividad["titulo"],
                      "unidad": actividad["unidad"], "puntaje": actividad["puntaje"]},
                     ip_origen=request.remote_addr or "127.0.0.1")

    if _quiere_json():
        return jsonify({"success": True, "actividad": actividad}), 201

    flash("Actividad %s registrada correctamente." % actividad["codigo"], "success")
    return redirect(url_for("activities.docente_detalle_actividad", actividad_id=actividad["id"]))


@activities_bp.route("/docente/actividades/<int:actividad_id>/asignar", methods=["POST"])
@login_required
@roles_required("Docente", "Administrador")
def asignar_actividad(actividad_id):
    if request.is_json:
        datos = request.get_json(silent=True) or {}
        estudiantes = datos.get("estudiante_ids") or datos.get("estudiante_id") or []
        if isinstance(estudiantes, str):
            estudiantes = [estudiantes]
    else:
        datos = request.form
        estudiantes = (request.form.getlist("estudiante_id")
                       or request.form.getlist("estudiante_id[]"))
        if not estudiantes and request.form.get("estudiante_ids"):
            estudiantes = request.form.get("estudiante_ids").replace(",", " ").split()
    if isinstance(estudiantes, str):
        estudiantes = [e for e in estudiantes.replace(",", " ").split() if e]
    if datos.get("todos") in ("1", "true", "on", True) or not estudiantes:
        resultado = ActivityService.asignar_a_todos_los_estudiantes(actividad_id)
    else:
        try:
            resultado = ActivityService.asignar_a_estudiantes(actividad_id, estudiantes)
        except ErrorActividad as error:
            return _error(error, redireccion=url_for("activities.docente_actividades"))

    AuditService.log(_usuario_actual(), session.get("username", "docente"),
                     "ASIGNAR_ACTIVIDAD", "ACTIVIDADES", actividad_id, None, resultado,
                     ip_origen=request.remote_addr or "127.0.0.1")

    if _quiere_json():
        return jsonify({"success": True, "asignacion": resultado})

    flash("Actividad %s: %d asignación(es) nueva(s), %d ya existente(s)."
          % (resultado.get("codigo") or actividad_id, resultado["asignadas"],
             resultado["ya_existentes"]), "success")
    return redirect(url_for("activities.docente_detalle_actividad", actividad_id=actividad_id))


@activities_bp.route("/docente/actividades/<int:actividad_id>/estado", methods=["POST"])
@login_required
@roles_required("Docente", "Administrador")
def cambiar_estado_actividad(actividad_id):
    """Abre o cierra una actividad del syllabus (control de la ventana de disponibilidad)."""
    datos = _datos_peticion()
    nuevo_estado = str(datos.get("estado") or "").strip().upper()
    if nuevo_estado not in ("ABIERTA", "CERRADA", "BORRADOR"):
        e = ErrorActividad("Estado inválido. Use ABIERTA, CERRADA o BORRADOR.")
        return _error(e, redireccion=url_for("activities.docente_actividades"))

    actividad = ActivityService.obtener_actividad(actividad_id)
    if not actividad:
        abort(404)

    conn = get_db_connection()
    try:
        conn.execute("UPDATE actividades SET estado = ? WHERE id = ?", (nuevo_estado, actividad_id))
        conn.commit()
    finally:
        conn.close()

    AuditService.log(_usuario_actual(), session.get("username", "docente"),
                     "CAMBIAR_ESTADO_ACTIVIDAD", "ACTIVIDADES", actividad_id,
                     {"estado": actividad.get("estado")}, {"estado": nuevo_estado},
                     ip_origen=request.remote_addr or "127.0.0.1")

    if _quiere_json():
        return jsonify({"success": True, "actividad_id": actividad_id, "estado": nuevo_estado})

    flash("Actividad %s marcada como %s." % (actividad["codigo"], nuevo_estado), "success")
    return redirect(url_for("activities.docente_detalle_actividad", actividad_id=actividad_id))
