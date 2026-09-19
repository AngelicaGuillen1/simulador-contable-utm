# -*- coding: utf-8 -*-
"""Panel docente de ACCESOS y seguimiento de estudiantes (Contabilidad I - UTM).

Solo DOCENTE y ADMINISTRADOR. Ofrece el resumen de accesos con filtros, la
exportación a CSV, el listado de estudiantes, la ficha individual con su línea de
tiempo y el listado de quienes nunca ingresaron.

Todos los endpoints aceptan ``?formato=json`` (o cabecera ``Accept: application/json``)
y devuelven el mismo contenido en JSON, para integrarse con el resto del panel.
"""
from datetime import datetime

from flask import Blueprint, Response, jsonify, render_template, request

from routes.auth import login_required, roles_required
from services.access_service import (
    actividades_disponibles,
    exportar_csv,
    ficha_estudiante,
    linea_tiempo,
    listado_docente_estudiantes,
    listado_estudiantes_sin_ingreso,
    paralelos_disponibles,
    resumen_accesos,
)
from services.libros_docente_service import (
    AVISO_AULA_VACIA,
    AVISO_SIN_AULA,
    balance_comprobacion,
    datos_estudiante,
    estados_financieros,
    libro_diario,
    libro_mayor,
    plan_cuentas,
    resumen_aula,
)

teacher_bp = Blueprint("teacher", __name__, url_prefix="/docente")

ROLES_DOCENTE = ("Docente", "Administrador")

ESTADOS_FILTRO = (
    ("", "Todos los estados"),
    ("ACTIVO", "Cuenta activa"),
    ("INACTIVO", "Cuenta inactiva"),
    ("CON_INGRESO", "Ya ingresó al simulador"),
    ("SIN_INGRESO", "Nunca ingresó"),
)

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _quiere_json():
    """True si el cliente pidió la respuesta en JSON."""
    formato = (request.args.get("formato") or "").strip().lower()
    if formato in ("json", "application/json"):
        return True
    if (request.args.get("json") or "").strip().lower() in ("1", "true", "si", "sí"):
        return True
    acepta = request.accept_mimetypes
    return acepta.accept_json and not acepta.accept_html


def _filtros():
    """Extrae los filtros del query string (se reutilizan en el formulario)."""
    return {
        "estudiante_id": request.args.get("estudiante_id", ""),
        "desde": request.args.get("desde", ""),
        "hasta": request.args.get("hasta", ""),
        "actividad_id": request.args.get("actividad_id", ""),
        "estado": request.args.get("estado", ""),
        "paralelo": request.args.get("paralelo", ""),
        "buscar": request.args.get("buscar", ""),
    }


def _contexto_panel():
    """Datos de apoyo para poblar los filtros del panel."""
    return {
        "estudiantes_filtro": listado_docente_estudiantes(),
        "paralelos": paralelos_disponibles(),
        "actividades_filtro": actividades_disponibles(),
        "estados_filtro": ESTADOS_FILTRO,
    }


# ---------------------------------------------------------------------------
# Libros del estudiante (solo lectura)
# ---------------------------------------------------------------------------
def _estudiante_no_encontrado():
    """Respuesta 404 uniforme (JSON o HTML) cuando el id no corresponde a un estudiante."""
    if _quiere_json():
        return jsonify({"ok": False, "error": "Estudiante no encontrado"}), 404
    return render_template("404.html", mensaje=(
        "El estudiante solicitado no existe en el Simulador Integral de Sistema Contable.")), 404


def _avance_actividades(actividades):
    """Avance del estudiante en sus actividades del syllabus (asignadas/entregadas)."""
    total = len(actividades)
    completadas = len([a for a in actividades
                       if str(a.get("estado_asignacion") or "").upper() in ("ENTREGADA", "REVISADA")])
    en_curso = len([a for a in actividades
                    if str(a.get("estado_asignacion") or "").upper() == "EN_CURSO"])
    return {
        "asignadas": total,
        "completadas": completadas,
        "en_curso": en_curso,
        "pendientes": max(0, total - completadas - en_curso),
        "porcentaje": round(completadas * 100.0 / total, 1) if total else 0.0,
    }


def _contexto_libros(estudiante_id, libro, seccion):
    """Contexto común de las vistas de libros: estudiante, avisos y datos del aula."""
    return {
        "estudiante_id": estudiante_id,
        "estudiante": libro.get("estudiante") or {},
        "libro": libro,
        "seccion": seccion,
        "aviso_sin_aula": AVISO_SIN_AULA,
        "aviso_aula_vacia": AVISO_AULA_VACIA,
    }


# ---------------------------------------------------------------------------
# Panel de accesos
# ---------------------------------------------------------------------------
@teacher_bp.route("/accesos")
@login_required
@roles_required(*ROLES_DOCENTE)
def accesos():
    """Panel de seguimiento de accesos con filtros por estudiante, fecha,
    actividad, estado y paralelo."""
    filtros = _filtros()
    filas = resumen_accesos(filtros)

    if _quiere_json():
        return jsonify({
            "ok": True,
            "total": len(filas),
            "filtros": filtros,
            "estudiantes": filas,
        })

    totales = {
        "estudiantes": len(filas),
        "con_ingreso": sum(1 for f in filas if f.get("ha_ingresado")),
        "sesiones": sum((f.get("num_sesiones") or 0) for f in filas),
        "eventos": sum((f.get("num_eventos") or 0) for f in filas),
        "tiempo": sum((f.get("tiempo_actividad_segundos") or 0) for f in filas),
        "evidencias": sum((f.get("evidencias_generadas") or 0) for f in filas),
    }

    return render_template("teacher/accesos.html", filas=filas, filtros=filtros,
                           totales=totales, **_contexto_panel())


@teacher_bp.route("/accesos/exportar.csv")
@login_required
@roles_required(*ROLES_DOCENTE)
def accesos_exportar():
    """Descarga el resumen de accesos (con los filtros aplicados) en CSV."""
    filtros = _filtros()
    contenido = exportar_csv(filtros)
    nombre = "accesos_estudiantes_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M")
    return Response(
        contenido,
        mimetype="text/csv",
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": 'attachment; filename="%s"' % nombre,
        },
    )


# ---------------------------------------------------------------------------
# Estudiantes
# ---------------------------------------------------------------------------
@teacher_bp.route("/estudiantes")
@login_required
@roles_required(*ROLES_DOCENTE)
def estudiantes():
    """Listado completo de estudiantes con su estado y si alguna vez ingresaron."""
    lista = listado_docente_estudiantes()

    if _quiere_json():
        return jsonify({"ok": True, "total": len(lista), "estudiantes": lista})

    return render_template("teacher/estudiantes.html", estudiantes=lista)


@teacher_bp.route("/estudiantes/<int:estudiante_id>")
@login_required
@roles_required(*ROLES_DOCENTE)
def estudiante_detalle(estudiante_id):
    """Ficha individual: accesos, línea de tiempo, actividades, evidencias y sus libros."""
    ficha = ficha_estudiante(estudiante_id)
    if not ficha or ficha["datos"].get("rol_nombre") != "Estudiante":
        if _quiere_json():
            return jsonify({"ok": False, "error": "Estudiante no encontrado"}), 404
        return render_template("404.html", mensaje=(
            "El estudiante solicitado no existe en el Simulador Integral de Sistema Contable.")), 404

    # Resumen de sus libros (solo lectura del aula) y avance en las actividades del syllabus.
    ficha["libros"] = resumen_aula(estudiante_id)
    ficha["avance"] = _avance_actividades(ficha.get("actividades") or [])

    if _quiere_json():
        return jsonify({"ok": True, "ficha": ficha})

    return render_template("teacher/estudiante_detalle.html", ficha=ficha)


@teacher_bp.route("/estudiantes/<int:estudiante_id>/linea-tiempo")
@login_required
@roles_required(*ROLES_DOCENTE)
def estudiante_linea_tiempo(estudiante_id):
    """Línea de tiempo del estudiante (eventos más recientes primero)."""
    try:
        limite = int(request.args.get("limite", 200))
    except (TypeError, ValueError):
        limite = 200
    eventos = linea_tiempo(estudiante_id, limite=limite)

    if _quiere_json():
        return jsonify({"ok": True, "estudiante_id": estudiante_id,
                        "total": len(eventos), "eventos": eventos})

    ficha = ficha_estudiante(estudiante_id)
    if not ficha or ficha["datos"].get("rol_nombre") != "Estudiante":
        return render_template("404.html", mensaje=(
            "El estudiante solicitado no existe en el Simulador Integral de Sistema Contable.")), 404
    ficha["libros"] = resumen_aula(estudiante_id)
    ficha["avance"] = _avance_actividades(ficha.get("actividades") or [])
    ficha["linea_tiempo"] = eventos
    return render_template("teacher/estudiante_detalle.html", ficha=ficha)


@teacher_bp.route("/sin-ingresar")
@login_required
@roles_required(*ROLES_DOCENTE)
def sin_ingresar():
    """Estudiantes matriculados que nunca iniciaron sesión."""
    lista = listado_estudiantes_sin_ingreso()

    if _quiere_json():
        return jsonify({"ok": True, "total": len(lista), "estudiantes": lista})

    return render_template("teacher/estudiantes.html", estudiantes=lista, solo_sin_ingreso=True)


# ---------------------------------------------------------------------------
# Libros del estudiante en SOLO LECTURA (Docente y Administrador)
# ---------------------------------------------------------------------------
@teacher_bp.route("/estudiantes/<int:estudiante_id>/diario")
@login_required
@roles_required(*ROLES_DOCENTE)
def estudiante_diario(estudiante_id):
    """Libro Diario del estudiante: asientos con fecha, concepto, cuentas, Debe y Haber."""
    datos = datos_estudiante(estudiante_id)
    if not datos:
        return _estudiante_no_encontrado()

    libro = libro_diario(estudiante_id, desde=request.args.get("desde"),
                         hasta=request.args.get("hasta"))
    if _quiere_json():
        return jsonify({"ok": True, "estudiante": datos, "libro_diario": libro})

    return render_template("teacher/libro_diario.html",
                           **_contexto_libros(estudiante_id, libro, "diario"))


@teacher_bp.route("/estudiantes/<int:estudiante_id>/mayor")
@login_required
@roles_required(*ROLES_DOCENTE)
def estudiante_mayor(estudiante_id):
    """Libro Mayor del estudiante: cuentas con sus movimientos y saldo."""
    datos = datos_estudiante(estudiante_id)
    if not datos:
        return _estudiante_no_encontrado()

    libro = libro_mayor(estudiante_id)
    if _quiere_json():
        return jsonify({"ok": True, "estudiante": datos, "libro_mayor": libro})

    return render_template("teacher/libro_mayor.html",
                           **_contexto_libros(estudiante_id, libro, "mayor"))


@teacher_bp.route("/estudiantes/<int:estudiante_id>/balance")
@login_required
@roles_required(*ROLES_DOCENTE)
def estudiante_balance(estudiante_id):
    """Balance de comprobación de sumas y saldos del estudiante."""
    datos = datos_estudiante(estudiante_id)
    if not datos:
        return _estudiante_no_encontrado()

    libro = balance_comprobacion(estudiante_id)
    if _quiere_json():
        return jsonify({"ok": True, "estudiante": datos, "balance": libro})

    return render_template("teacher/balance_comprobacion.html",
                           **_contexto_libros(estudiante_id, libro, "balance"))


@teacher_bp.route("/estudiantes/<int:estudiante_id>/cuentas")
@login_required
@roles_required(*ROLES_DOCENTE)
def estudiante_cuentas(estudiante_id):
    """Plan de cuentas del estudiante, agrupado por clasificación."""
    datos = datos_estudiante(estudiante_id)
    if not datos:
        return _estudiante_no_encontrado()

    libro = plan_cuentas(estudiante_id)
    if _quiere_json():
        return jsonify({"ok": True, "estudiante": datos, "plan_cuentas": libro})

    return render_template("teacher/plan_cuentas.html",
                           **_contexto_libros(estudiante_id, libro, "cuentas"))


@teacher_bp.route("/estudiantes/<int:estudiante_id>/estados")
@login_required
@roles_required(*ROLES_DOCENTE)
def estudiante_estados(estudiante_id):
    """Estados financieros básicos del estudiante: situación, resultados y efectivo."""
    datos = datos_estudiante(estudiante_id)
    if not datos:
        return _estudiante_no_encontrado()

    libro = estados_financieros(estudiante_id)
    if _quiere_json():
        return jsonify({"ok": True, "estudiante": datos, "estados": libro})

    return render_template("teacher/estados_financieros.html",
                           **_contexto_libros(estudiante_id, libro, "estados"))
