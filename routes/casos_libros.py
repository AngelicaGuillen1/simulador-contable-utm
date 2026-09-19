# -*- coding: utf-8 -*-
"""Rutas del BANCO DE CASOS PRÁCTICOS DE LOS LIBROS (§61) y de las reglas de trazabilidad (§62).

Rutas de estudiante (aisladas por session['user_id']):
    GET  /casos-libros                       listado de casos activos con su ficha (§62.9)
    GET  /casos-libros/<codigo>              ficha y formulario de resolución
    POST /casos-libros/<codigo>/intentos     abre un intento (controla intentos máximos)
    POST /casos-libros/<codigo>/enviar       envía y verifica la respuesta del intento
    GET  /casos-libros/mis-intentos          historial de intentos del estudiante

Rutas de docente / administrador:
    GET  /docente/casos-libros               banco completo, fichas, trazabilidad, reglas y tasas
    POST /docente/casos-libros/<codigo>/activar
    POST /docente/casos-libros/tasas         tarifas demostrativas editables (§62.2)

Todas las rutas devuelven JSON cuando la petición lo pide (`?formato=json` o cabecera
`Accept: application/json`).
"""

from flask import (Blueprint, abort, flash, jsonify, redirect, render_template, request, session,
                   url_for)

from routes.auth import login_required, roles_required
from services.casos_libros_service import (
    CasoNoEncontrado, ErrorCasoLibro, advertencias_trazabilidad, ajustar_tasa_demostrativa,
    activar_caso, erratas_catalogo, fuentes, listar_casos, listar_intentos, modos_catalogo,
    obtener_caso, reglas, resumen_banco, resumen_intentos, tasas_demostrativas,
)

casos_bp = Blueprint("casos_libros", __name__)


# --------------------------------------------------------------------------- Utilidades
def _quiere_json():
    if request.is_json:
        return True
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
    return redirect(redireccion or url_for("casos_libros.listado"))


def _lineas_de_peticion(datos):
    """Acepta líneas en JSON (`lineas`) o en formulario HTML (`cuenta_1`, `debe_1`, `haber_1`)."""
    if isinstance(datos.get("lineas"), list):
        return [dict(l) for l in datos["lineas"]]
    lineas = []
    indices = set()
    for clave in datos.keys():
        if clave.startswith("cuenta_"):
            indices.add(clave.split("_", 1)[1])
    for indice in sorted(indices):
        cuenta = (datos.get("cuenta_%s" % indice) or "").strip()
        debe = (datos.get("debe_%s" % indice) or "0").strip() or "0"
        haber = (datos.get("haber_%s" % indice) or "0").strip() or "0"
        if not cuenta and float(debe.replace(",", ".") or 0) == 0 and float(haber.replace(",", ".") or 0) == 0:
            continue
        try:
            lineas.append({"cuenta": cuenta, "debe": float(debe.replace(",", ".")),
                           "haber": float(haber.replace(",", "."))})
        except ValueError:
            continue
    return lineas


# --------------------------------------------------------------------------- Estudiante
@casos_bp.route("/casos-libros")
@login_required
def listado():
    filtros = {"unidad": request.args.get("unidad"), "estado_validacion": request.args.get("estado"),
               "fuente": request.args.get("fuente"), "q": request.args.get("q")}
    docente = session.get("user_role") in ("Docente", "Administrador")
    casos = listar_casos(filtros, para_estudiante=not docente)
    resumen = resumen_banco()

    if _quiere_json():
        return jsonify({"success": True, "total": len(casos), "resumen": resumen,
                        "casos": casos, "advertencias": advertencias_trazabilidad()})

    return render_template("casos_libros/lista.html", casos=casos, resumen=resumen,
                           filtros=filtros, es_docente=docente,
                           advertencias=advertencias_trazabilidad(), fuentes=fuentes())


@casos_bp.route("/casos-libros/mis-intentos")
@login_required
def mis_intentos():
    intentos = listar_intentos(estudiante_id=_usuario_actual())
    if _quiere_json():
        return jsonify({"success": True, "total": len(intentos), "intentos": intentos})
    return render_template("casos_libros/intentos.html", intentos=intentos)


@casos_bp.route("/casos-libros/<codigo>")
@login_required
def ficha(codigo):
    docente = session.get("user_role") in ("Docente", "Administrador")
    try:
        caso = obtener_caso(codigo, para_estudiante=not docente)
    except CasoNoEncontrado as error:
        return _error(error)
    intentos = listar_intentos(codigo=caso["codigo"], estudiante_id=_usuario_actual())
    if _quiere_json():
        return jsonify({"success": True, "caso": caso, "intentos": intentos,
                        "advertencias": advertencias_trazabilidad()})
    return render_template("casos_libros/ficha.html", caso=caso, intentos=intentos,
                           es_docente=docente, advertencias=advertencias_trazabilidad())


@casos_bp.route("/casos-libros/<codigo>/intentos", methods=["POST"])
@login_required
def abrir_intento(codigo):
    try:
        resultado = _abrir_intento(codigo, _usuario_actual())
    except ErrorCasoLibro as error:
        return _error(error, redireccion=url_for("casos_libros.ficha", codigo=codigo))
    if _quiere_json():
        return jsonify({"success": True, "intento": resultado}), 201
    flash(resultado["mensaje"], "success")
    return redirect(url_for("casos_libros.ficha", codigo=codigo, intento=resultado["intento_id"]))


def _abrir_intento(codigo, estudiante_id):
    from services.casos_libros_service import iniciar_intento
    return iniciar_intento(codigo, estudiante_id)


@casos_bp.route("/casos-libros/<codigo>/enviar", methods=["POST"])
@login_required
def enviar(codigo):
    datos = _datos_peticion()
    lineas = _lineas_de_peticion(datos)
    totales = dict(datos.get("totales")) if isinstance(datos.get("totales"), dict) else None
    if totales is None:
        # Formulario HTML: los totales llegan como «totales.<clave>».
        for clave, valor in datos.items():
            if not clave.startswith("totales."):
                continue
            totales = totales or {}
            try:
                totales[clave.split(".", 1)[1]] = float(str(valor).replace(",", "."))
            except (TypeError, ValueError):
                continue
    ecuacion = datos.get("ecuacion") if isinstance(datos.get("ecuacion"), dict) else None
    if not lineas and not totales and not ecuacion:
        for clave in ("activo", "pasivo", "capital", "ingresos", "gastos"):
            if datos.get(clave) not in (None, ""):
                ecuacion = ecuacion or {}
                try:
                    ecuacion[clave] = float(str(datos.get(clave)).replace(",", "."))
                except ValueError:
                    continue
        if not lineas and not ecuacion and not totales:
            error = ErrorCasoLibro("Debe enviar al menos una línea de asiento o los totales del caso.")
            return _error(error, redireccion=url_for("casos_libros.ficha", codigo=codigo))

    from services.casos_libros_service import enviar_intento
    intento_id = datos.get("intento_id") or request.args.get("intento_id")
    try:
        resultado = enviar_intento(codigo, _usuario_actual(), lineas=lineas, totales=totales,
                                   ecuacion=ecuacion,
                                   intento_id=int(intento_id) if intento_id else None,
                                   tiempo_segundos=int(datos.get("tiempo_segundos") or 0))
    except ErrorCasoLibro as error:
        return _error(error, redireccion=url_for("casos_libros.ficha", codigo=codigo))

    if _quiere_json():
        return jsonify({"success": True, "resultado": resultado})
    flash("Intento %d verificado: %s (%.2f puntos).%s"
          % (resultado["numero_intento"], resultado["resultado"], resultado["puntuacion"],
             " Requiere revisión del docente." if resultado["requiere_revision_docente"] else ""),
          "success" if resultado["resultado"] == "CORRECTO" else "warning")
    return redirect(url_for("casos_libros.ficha", codigo=codigo))


# --------------------------------------------------------------------------- Docente
@casos_bp.route("/docente/casos-libros")
@login_required
@roles_required("Docente", "Administrador")
def panel_docente():
    casos = listar_casos({}, para_estudiante=False)
    resumen = resumen_banco()
    intentos = listar_intentos(limite=100)
    datos = {
        "success": True, "resumen": resumen, "casos": casos, "intentos": intentos,
        "reglas": reglas(), "reglas_trazabilidad": reglas(solo_trazabilidad=True),
        "erratas_catalogo": erratas_catalogo(), "fuentes": fuentes(),
        "tasas": tasas_demostrativas(), "modos_catalogo": modos_catalogo(),
        "advertencias": advertencias_trazabilidad(),
    }
    if _quiere_json():
        return jsonify(datos)
    return render_template("casos_libros/docente.html", **datos)


@casos_bp.route("/docente/casos-libros/<codigo>")
@login_required
@roles_required("Docente", "Administrador")
def docente_ficha(codigo):
    try:
        caso = obtener_caso(codigo, para_estudiante=False)
    except CasoNoEncontrado as error:
        return _error(error)
    resumen = resumen_intentos(caso["codigo"])
    if _quiere_json():
        return jsonify({"success": True, "caso": caso, "intentos": resumen})
    return render_template("casos_libros/ficha.html", caso=caso, intentos=resumen["intentos"],
                           es_docente=True, resumen_intentos=resumen,
                           advertencias=advertencias_trazabilidad())


@casos_bp.route("/docente/casos-libros/<codigo>/activar", methods=["POST"])
@login_required
@roles_required("Docente", "Administrador")
def activar(codigo):
    datos = _datos_peticion()
    activo = str(datos.get("activo", "1")).lower() not in ("0", "false", "off", "no")
    try:
        caso = activar_caso(codigo, activo=activo)
    except ErrorCasoLibro as error:
        return _error(error, redireccion=url_for("casos_libros.panel_docente"))
    if _quiere_json():
        return jsonify({"success": True, "caso": caso["codigo"], "activo": caso["activo"]})
    flash("Caso %s %s." % (caso["codigo"], "activado" if caso["activo"] else "desactivado"), "success")
    return redirect(url_for("casos_libros.panel_docente"))


@casos_bp.route("/docente/casos-libros/tasas", methods=["POST"])
@login_required
@roles_required("Docente", "Administrador")
def editar_tasa():
    datos = _datos_peticion()
    clave = (datos.get("clave") or "").strip()
    try:
        ajustada = ajustar_tasa_demostrativa(clave, datos.get("valor"))
    except ErrorCasoLibro as error:
        return _error(error, redireccion=url_for("casos_libros.panel_docente"))
    if _quiere_json():
        return jsonify({"success": True, "tasa": ajustada})
    flash("Tarifa demostrativa «%s» fijada en %s (configuración académica)."
          % (ajustada["nombre"], ajustada["valor_vigente"]), "success")
    return redirect(url_for("casos_libros.panel_docente"))
