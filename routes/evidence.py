# -*- coding: utf-8 -*-
"""Rutas del módulo de EVIDENCIAS verificables (Contabilidad I).

Rutas de estudiante (todas filtran por session['user_id'] y devuelven 404/403 si la evidencia
pertenece a otro compañero):
    GET  /mis-evidencias
    POST /mis-evidencias/nueva
    GET  /mis-evidencias/<id>
    POST /mis-evidencias/<id>/finalizar
    GET  /mis-evidencias/<id>/captura       (vista limpia para capturar pantalla)
    GET  /mis-evidencias/<id>/imprimible    (vista imprimible; PDF si reportlab está instalado)

Rutas de docente / administrador (roles_required):
    GET /docente/evidencias
    GET /docente/evidencias/<id>
    GET /docente/evidencias/verificar?codigo=CONT1-B-2026-XXXXXXXX

Todos los endpoints devuelven JSON cuando la petición lo pide (`?formato=json` o cabecera
`Accept: application/json`).
"""

import os
import tempfile

from flask import (Blueprint, abort, flash, g, jsonify, redirect, render_template, request,
                   send_file, session, url_for)

from models import get_db_connection
from routes.auth import login_required, roles_required
from services.activity_service import ActivityService, ErrorActividad
from services.audit_service import AuditService
from services.evidence_service import (
    EvidenceService, ErrorEvidencia, EvidenciaAjena, EvidenciaNoEncontrada,
)

evidence_bp = Blueprint("evidence", __name__)


# --------------------------------------------------------------------------- Utilidades
def _quiere_json():
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
    if _quiere_json():
        return jsonify({"success": False, "error": error.mensaje,
                        "codigo": getattr(error, "codigo", "VALIDACION")}), error.estado_http
    if error.estado_http in (403, 404):
        abort(error.estado_http)
    flash(error.mensaje, "warning")
    return redirect(redireccion or url_for("evidence.mis_evidencias"))


def _evidencia_propia(evidencia_id, estado_http_ajeno=404):
    """Candado de aislamiento: devuelve la evidencia solo si es del estudiante autenticado."""
    estudiante_id = _usuario_actual()
    try:
        return EvidenceService.obtener_evidencia_de_estudiante(evidencia_id, estudiante_id)
    except EvidenciaAjena:
        abort(estado_http_ajeno if estado_http_ajeno else 403)
    except EvidenciaNoEncontrada:
        abort(404)


def _titulo_por_defecto(tipo, actividad):
    etiquetas = {
        "PLAN_CUENTAS": "Evidencia del plan de cuentas",
        "DIARIO": "Evidencia del libro diario",
        "MAYOR": "Evidencia del libro mayor",
        "BALANCE": "Evidencia del balance de comprobación",
        "INTEGRAL": "Evidencia integral del trabajo contable",
    }
    base = etiquetas.get((tipo or "INTEGRAL").upper(), "Evidencia contable")
    if actividad:
        return "%s · %s" % (base, actividad.get("codigo") or actividad.get("titulo"))
    return base


# --------------------------------------------------------------------------- Estudiante
@evidence_bp.route("/mis-evidencias")
@login_required
def mis_evidencias():
    estudiante_id = _usuario_actual()
    actividad_id = request.args.get("actividad_id", type=int)
    evidencias = EvidenceService.listar_evidencias_estudiante(estudiante_id,
                                                              actividad_id=actividad_id)
    actividades = ActivityService.listar_actividades_estudiante(estudiante_id)

    for evidencia in evidencias:
        evidencia["modificada"] = EvidenceService.detectar_modificacion(evidencia["id"])

    if _quiere_json():
        return jsonify({"success": True, "estudiante_id": estudiante_id,
                        "total": len(evidencias), "evidencias": evidencias,
                        "actividades": actividades})

    resumen = {
        "total": len(evidencias),
        "finales": sum(1 for e in evidencias if e.get("estado") == "FINAL"),
        "borradores": sum(1 for e in evidencias if e.get("estado") == "BORRADOR"),
        "modificadas": sum(1 for e in evidencias if e.get("modificada")),
    }
    return render_template("evidence/mis_evidencias.html", evidencias=evidencias,
                           actividades=actividades, resumen=resumen,
                           actividad_id=actividad_id)


@evidence_bp.route("/mis-evidencias/nueva", methods=["POST"])
@login_required
def nueva_evidencia():
    estudiante_id = _usuario_actual()
    datos = dict(_datos_peticion())

    tipo = str(datos.get("tipo") or "INTEGRAL").strip().upper()
    actividad_id = datos.get("actividad_id")
    try:
        actividad_id = int(actividad_id) if actividad_id else None
    except (TypeError, ValueError):
        actividad_id = None

    actividad = None
    if actividad_id:
        try:
            asignacion = ActivityService.requiere_actividad_de_estudiante(actividad_id, estudiante_id)
            actividad = asignacion
        except ErrorActividad as error:
            return _error(error, redireccion=url_for("evidence.mis_evidencias"))

    titulo = (datos.get("titulo") or "").strip() or _titulo_por_defecto(tipo, actividad)

    try:
        evidencia = EvidenceService.crear_evidencia(estudiante_id, actividad_id, tipo, titulo,
                                                    db_path=None)
        if str(datos.get("finalizar") or "").lower() in ("1", "true", "on", "si", "sí"):
            evidencia = EvidenceService.finalizar_evidencia(evidencia["id"])
            accion = "FINALIZAR_EVIDENCIA"
        else:
            accion = "GENERAR_EVIDENCIA"
    except ErrorEvidencia as error:
        return _error(error, redireccion=url_for("evidence.mis_evidencias"))

    AuditService.log(estudiante_id, session.get("username", "estudiante"), accion, "EVIDENCIAS",
                     evidencia["id"], None,
                     {"codigo": evidencia["codigo"], "tipo": evidencia["tipo"],
                      "actividad_id": actividad_id, "titulo": evidencia["titulo"]},
                     ip_origen=request.remote_addr or "127.0.0.1")

    if _quiere_json():
        return jsonify({"success": True, "evidencia": evidencia}), 201

    flash("Evidencia %s generada. Código verificable: %s"
          % (evidencia["titulo"], evidencia["codigo"]), "success")
    return redirect(url_for("evidence.detalle_evidencia", evidencia_id=evidencia["id"]))


@evidence_bp.route("/mis-evidencias/<int:evidencia_id>")
@login_required
def detalle_evidencia(evidencia_id):
    evidencia = _evidencia_propia(evidencia_id)
    modificada = EvidenceService.detectar_modificacion(evidencia_id)
    resumen = EvidenceService.resumen_evidencia(evidencia_id)
    versiones = EvidenceService.versiones(evidencia_id)

    if _quiere_json():
        datos = dict(evidencia)
        datos["modificada_despues"] = bool(modificada)
        datos["versiones"] = versiones
        return jsonify({"success": True, "evidencia": datos, "resumen": resumen})

    return render_template("evidence/detalle.html", evidencia=evidencia, resumen=resumen,
                           versiones=versiones, modificada=modificada)


@evidence_bp.route("/mis-evidencias/<int:evidencia_id>/finalizar", methods=["POST"])
@login_required
def finalizar_evidencia(evidencia_id):
    evidencia = _evidencia_propia(evidencia_id, estado_http_ajeno=403)
    try:
        actualizada = EvidenceService.finalizar_evidencia(evidencia_id)
    except ErrorEvidencia as error:
        return _error(error, redireccion=url_for("evidence.detalle_evidencia",
                                                 evidencia_id=evidencia_id))

    AuditService.log(_usuario_actual(), session.get("username", "estudiante"),
                     "FINALIZAR_EVIDENCIA", "EVIDENCIAS", evidencia_id,
                     {"estado": evidencia.get("estado")},
                     {"estado": actualizada.get("estado"), "huella": actualizada.get("huella")},
                     ip_origen=request.remote_addr or "127.0.0.1")

    if _quiere_json():
        return jsonify({"success": True, "evidencia": actualizada})

    flash("Evidencia %s finalizada y firmada con su huella de verificación."
          % actualizada["codigo"], "success")
    return redirect(url_for("evidence.detalle_evidencia", evidencia_id=evidencia_id))


@evidence_bp.route("/mis-evidencias/<int:evidencia_id>/version", methods=["POST"])
@login_required
def nueva_version_evidencia(evidencia_id):
    evidencia = _evidencia_propia(evidencia_id, estado_http_ajeno=403)
    datos = _datos_peticion()
    motivo = (datos.get("motivo") or "").strip() or "Corrección posterior del trabajo contable"
    try:
        actualizada = EvidenceService.nueva_version(evidencia_id, motivo)
    except ErrorEvidencia as error:
        return _error(error, redireccion=url_for("evidence.detalle_evidencia",
                                                 evidencia_id=evidencia_id))

    AuditService.log(_usuario_actual(), session.get("username", "estudiante"),
                     "NUEVA_VERSION_EVIDENCIA", "EVIDENCIAS", evidencia_id,
                     {"huella": evidencia.get("huella"), "version": 1},
                     {"huella": actualizada.get("huella"), "version": actualizada.get("version"),
                      "motivo": motivo},
                     ip_origen=request.remote_addr or "127.0.0.1")

    if _quiere_json():
        return jsonify({"success": True, "evidencia": actualizada})

    flash("Se registró la versión %s de la evidencia %s."
          % (actualizada.get("version"), actualizada["codigo"]), "success")
    return redirect(url_for("evidence.detalle_evidencia", evidencia_id=evidencia_id))


@evidence_bp.route("/mis-evidencias/<int:evidencia_id>/captura")
@login_required
def captura_evidencia(evidencia_id):
    """Vista limpia (sin menú lateral) lista para capturar pantalla como evidencia."""
    evidencia = _evidencia_propia(evidencia_id)
    modificada = EvidenceService.detectar_modificacion(evidencia_id)
    resumen = EvidenceService.resumen_evidencia(evidencia_id)

    if _quiere_json():
        return jsonify({"success": True, "evidencia": evidencia, "resumen": resumen,
                        "modificada_despues": bool(modificada)})

    return render_template("evidence/resumen.html", evidencia=evidencia, resumen=resumen,
                           modificada=modificada, modo_imprimible=False)


@evidence_bp.route("/mis-evidencias/<int:evidencia_id>/imprimible")
@login_required
def imprimible_evidencia(evidencia_id):
    """Vista imprimible: PDF con reportlab si está instalado; si no, HTML listo para imprimir."""
    evidencia = _evidencia_propia(evidencia_id)
    modificada = EvidenceService.detectar_modificacion(evidencia_id)
    resumen = EvidenceService.resumen_evidencia(evidencia_id)

    if request.args.get("pdf") in ("1", "true", "si", "sí"):
        ruta = os.path.join(tempfile.gettempdir(), EvidenceService.nombre_archivo_evidencia(evidencia))
        generado = EvidenceService.exportar_pdf(evidencia_id, ruta)
        if generado and os.path.exists(generado):
            return send_file(generado, mimetype="application/pdf", as_attachment=False,
                             download_name=EvidenceService.nombre_archivo_evidencia(evidencia))

    if _quiere_json():
        return jsonify({"success": True, "evidencia": evidencia, "resumen": resumen,
                        "pdf_disponible": _pdf_disponible()})

    return render_template("evidence/resumen.html", evidencia=evidencia, resumen=resumen,
                           modificada=modificada, modo_imprimible=True)


def _pdf_disponible():
    try:
        import reportlab  # noqa: F401
        return True
    except ImportError:
        return False


# --------------------------------------------------------------------------- Docente
@evidence_bp.route("/docente/evidencias")
@login_required
@roles_required("Docente", "Administrador")
def docente_evidencias():
    filtros = {
        "estudiante_id": request.args.get("estudiante_id"),
        "actividad_id": request.args.get("actividad_id"),
        "estado": request.args.get("estado"),
        "q": request.args.get("q"),
        "modificadas": request.args.get("modificadas"),
    }
    evidencias = EvidenceService.listar_evidencias_docente(filtros)
    for evidencia in evidencias:
        evidencia["modificada"] = EvidenceService.detectar_modificacion(evidencia["id"])

    if _quiere_json():
        return jsonify({"success": True, "total": len(evidencias), "filtros": filtros,
                        "evidencias": evidencias})

    resumen = {
        "total": len(evidencias),
        "finales": sum(1 for e in evidencias if e.get("estado") == "FINAL"),
        "modificadas": sum(1 for e in evidencias if e.get("modificada")),
    }
    return render_template("evidence/docente_evidencias.html", evidencias=evidencias,
                           filtros=filtros, resumen=resumen,
                           actividades=ActivityService.listado_docente({}),
                           estudiantes=ActivityService.estudiantes_activos())


@evidence_bp.route("/docente/evidencias/verificar")
@login_required
@roles_required("Docente", "Administrador")
def verificar_evidencia():
    codigo = (request.args.get("codigo") or "").strip().upper()
    resultado = EvidenceService.verificar_codigo(codigo) if codigo else None

    if _quiere_json():
        if not resultado:
            return jsonify({"success": False, "codigo": codigo,
                            "error": "No existe una evidencia con ese código."}), 404
        return jsonify({"success": True, "verificacion": resultado})

    return render_template("evidence/verificar.html", codigo=codigo, verificacion=resultado)


@evidence_bp.route("/docente/evidencias/<int:evidencia_id>")
@login_required
@roles_required("Docente", "Administrador")
def docente_detalle_evidencia(evidencia_id):
    evidencia = EvidenceService.obtener_evidencia(evidencia_id)
    if not evidencia:
        abort(404)

    modificada = EvidenceService.detectar_modificacion(evidencia_id)
    resumen = EvidenceService.resumen_evidencia(evidencia_id)
    versiones = EvidenceService.versiones(evidencia_id)

    if _quiere_json():
        datos = dict(evidencia)
        datos["modificada_despues"] = bool(modificada)
        datos["versiones"] = versiones
        return jsonify({"success": True, "evidencia": datos, "resumen": resumen})

    return render_template("evidence/detalle.html", evidencia=evidencia, resumen=resumen,
                           versiones=versiones, modificada=modificada, vista_docente=True)
