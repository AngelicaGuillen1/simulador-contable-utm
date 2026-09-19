# -*- coding: utf-8 -*-
"""routes/documents.py — Documentos fuente simulados y comprobantes del SRI.

Sección que expone los documentos que respaldan cada operación contable del simulador
(facturas, comprobantes de ingreso/egreso, notas de crédito/débito, papeletas, arqueos, roles y
órdenes) y, además, el **módulo de Documentos del SRI**: catálogo de tipos de comprobante,
emisión con las validaciones del reglamento, detalle, anulación y ayuda didáctica.

Todos los endpoints aceptan `?formato=json` para devolver la misma información en JSON.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, g

from config import Config
from routes.auth import login_required
from services.document_service import (
    DocumentService,
    TIPOS_DOCUMENTO,
    ESTADOS_DOCUMENTO,
    CATEGORIA_ETIQUETAS,
    TABLA_SOPORTE,
    ALIAS_SOPORTE,
    fecha_trabajo,
)

documents_bp = Blueprint("documents", __name__, url_prefix="/documentos")

# Banderas de contexto que acepta la ayuda didáctica (GET /documentos/soporte).
BANDERAS_SOPORTE = ("es_consumidor_final", "requiere_traslado", "es_isd", "es_turistico", "es_rise",
                    "es_vehiculo_usado", "proveedor_tiene_ruc", "sin_identificacion")
VALORES_VERDAD = ("1", "true", "si", "sí", "on", "yes")
VALORES_FALSEDAD = ("0", "false", "no", "off")


def _quiere_json():
    """True si el cliente pidió la respuesta en JSON (?formato=json o ?json=1)."""
    formato = (request.args.get("formato") or "").strip().lower()
    if formato in ("json", "application/json"):
        return True
    return (request.args.get("json") or "").strip().lower() in VALORES_VERDAD


def _verdad(valor):
    """Convierte una bandera de la URL en booleano (None si no viene)."""
    if valor is None:
        return None
    texto = str(valor).strip().lower()
    if texto in VALORES_VERDAD:
        return True
    if texto in VALORES_FALSEDAD:
        return False
    return None


def _banderas_contexto():
    return {clave: _verdad(request.args.get(clave)) for clave in BANDERAS_SOPORTE
            if request.args.get(clave) is not None}


def _datos_formulario(formulario):
    """Toma los campos del formulario de emisión tal como los espera el servicio."""
    datos = {}
    for clave, valor in formulario.items():
        if isinstance(valor, str):
            valor = valor.strip()
        if valor in (None, ""):
            continue
        datos[clave] = valor
    return datos


def _tipos_para_filtro(usados=()):
    """Tipos de documento del listado: los del simulador y los del catálogo del SRI."""
    vistos, opciones = set(), []
    for codigo, nombre, _grupo in TIPOS_DOCUMENTO:
        if codigo not in vistos:
            vistos.add(codigo)
            opciones.append({"codigo": codigo, "nombre": nombre})
    for ficha in DocumentService.catalogo():
        if ficha["codigo"] not in vistos:
            vistos.add(ficha["codigo"])
            opciones.append({"codigo": ficha["codigo"], "nombre": ficha["nombre"]})
    for codigo in usados:
        if codigo and codigo not in vistos:
            vistos.add(codigo)
            opciones.append({"codigo": codigo, "nombre": DocumentService.get_etiqueta(codigo)})
    return sorted(opciones, key=lambda o: (o["nombre"] or "").lower())


# ---------------------------------------------------------------------------------------------
# Listado de documentos fuente
# ---------------------------------------------------------------------------------------------
@documents_bp.route("/")
@login_required
def index():
    tipo = request.args.get("tipo") or None
    numero = request.args.get("numero") or None
    tercero = request.args.get("tercero") or None
    estado = request.args.get("estado") or None
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin = request.args.get("fecha_fin") or None

    documentos = DocumentService.get_documents(
        tipo=tipo, numero=numero, tercero=tercero, estado=estado,
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, limit=300
    )
    resumen = DocumentService.get_tipos_resumen()
    total_monto = round(sum((d.get("monto_total") or 0) for d in documentos), 2)
    tipos = _tipos_para_filtro([r["tipo"] for r in resumen])
    estados = DocumentService.estados(sorted({(d.get("estado") or "EMITIDO") for d in documentos}))

    if _quiere_json():
        return jsonify({
            "success": True,
            "total": len(documentos),
            "monto_total": total_monto,
            "filtros": {"tipo": tipo, "numero": numero, "tercero": tercero, "estado": estado,
                        "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin},
            "resumen": resumen,
            "documentos": documentos,
        })

    return render_template(
        "documents/index.html",
        documentos=documentos,
        resumen=resumen,
        tipos=tipos,
        estados=estados,
        etiqueta=DocumentService.get_etiqueta,
        selected_tipo=tipo,
        numero=numero or "",
        tercero=tercero or "",
        selected_estado=estado or "",
        fecha_inicio=fecha_inicio or "",
        fecha_fin=fecha_fin or "",
        total_monto=total_monto,
        categorias=CATEGORIA_ETIQUETAS,
    )


# ---------------------------------------------------------------------------------------------
# Catálogo normativo del SRI
# ---------------------------------------------------------------------------------------------
@documents_bp.route("/catalogo")
@login_required
def catalogo():
    agrupado = DocumentService.catalogo(agrupado_por_categoria=True)
    reglas = DocumentService.reglas()
    parametros = DocumentService.parametros_efectivos()
    total_tipos = sum(len(t) for t in agrupado.values())

    if _quiere_json():
        return jsonify({
            "success": True,
            "total_tipos": total_tipos,
            "total_reglas": len(reglas),
            "categorias": CATEGORIA_ETIQUETAS,
            "catalogo": agrupado,
            "reglas": reglas,
            "parametros": {k: v for k, v in parametros.items() if not isinstance(v, (list, tuple))},
        })

    return render_template("documents/catalogo.html", agrupado=agrupado, reglas=reglas,
                           parametros=parametros, total_tipos=total_tipos,
                           categorias=CATEGORIA_ETIQUETAS)


# ---------------------------------------------------------------------------------------------
# Emisión de un comprobante
# ---------------------------------------------------------------------------------------------
@documents_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    tipos = DocumentService.catalogo()
    tipo_sel = (request.values.get("tipo") or (tipos[0]["codigo"] if tipos else "")).strip().upper()
    ficha = DocumentService.tipo_documento(tipo_sel) or (tipos[0] if tipos else None)
    if ficha:
        tipo_sel = ficha["codigo"]

    secciones = DocumentService.campos_formulario(tipo_sel) if ficha else []
    porcentajes = DocumentService.porcentajes_disponibles(tipo_sel)
    parametros = DocumentService.parametros_efectivos()
    leyenda = DocumentService.leyenda_educativa()
    datos = {}
    errores, advertencias = [], []
    valido = None

    if request.method == "POST":
        datos = _datos_formulario(request.form)
        valido, errores, advertencias = DocumentService.validar_documento(tipo_sel, datos)
        if valido:
            try:
                documento = DocumentService.emitir_documento(tipo_sel, datos)
            except ValueError as exc:  # DocumentoInvalido
                valido = False
                errores = [linea for linea in str(exc).split("\n") if linea.strip()]
            else:
                if _quiere_json():
                    return jsonify({"success": True, "documento": documento,
                                    "advertencias": advertencias}), 201
                flash("Comprobante %s emitido correctamente y guardado en los documentos fuente."
                      % (documento.get("numero_completo") or documento.get("numero")), "success")
                return redirect(url_for("documents.detail", doc_id=documento["id"]))
        if _quiere_json():
            return jsonify({"success": False, "tipo": tipo_sel, "errores": errores,
                            "advertencias": advertencias}), 400
        # El intento rechazado es evidencia pedagógica: se marca para que el hook
        # de trazabilidad lo registre como INTENTO_FALLIDO_DOCUMENTO (aquí la ruta
        # responde con redirect y flash, no con un código >= 400).
        g.intento_fallido = {
            "evento": "INTENTO_FALLIDO_DOCUMENTO",
            "mensaje": " | ".join(str(e) for e in (errores or [])[:3]) or "comprobante rechazado",
            "documento_elegido": tipo_sel,
        }
        flash("El comprobante no se emitió: revisa los puntos marcados en rojo.", "danger")

    # Valores sugeridos para no dejar el formulario en blanco.
    sugeridos = {
        "fecha": datos.get("fecha") or fecha_trabajo(),
        "emisor": datos.get("emisor") or Config.COMPANY_NAME,
        "ruc_emisor": datos.get("ruc_emisor") or Config.COMPANY_RUC,
        "establecimiento": datos.get("establecimiento") or "001",
        "punto_emision": datos.get("punto_emision") or "001",
        "tipo_emision": datos.get("tipo_emision") or "NORMAL",
        "adquirente_tipo_id": datos.get("adquirente_tipo_id") or "RUC",
        "forma_pago": datos.get("forma_pago") or "EFECTIVO",
    }
    valores = dict(sugeridos)
    valores.update({k: v for k, v in datos.items() if v not in (None, "")})

    return render_template("documents/nuevo.html", tipos=tipos, ficha=ficha, tipo_sel=tipo_sel,
                           secciones=secciones, porcentajes=porcentajes, parametros=parametros,
                           leyenda=leyenda, valores=valores, errores=errores,
                           advertencias=advertencias, valido=valido,
                           categorias=CATEGORIA_ETIQUETAS)


# ---------------------------------------------------------------------------------------------
# Ayuda didáctica: ¿qué documento corresponde a esta operación?
# ---------------------------------------------------------------------------------------------
@documents_bp.route("/soporte")
@login_required
def soporte():
    tipo_tx = (request.args.get("tipo") or "").strip()
    contexto = _banderas_contexto()
    sugerencia = DocumentService.soporte_sugerido(tipo_tx, contexto) if tipo_tx else None
    operaciones = [{"clave": clave, "tipo": datos["tipo"]} for clave, datos in TABLA_SOPORTE.items()]

    if _quiere_json():
        return jsonify({"success": True, "consulta": tipo_tx, "contexto": contexto,
                        "sugerencia": sugerencia, "operaciones": operaciones})

    return render_template("documents/soporte.html", consulta=tipo_tx, contexto=contexto,
                           sugerencia=sugerencia, operaciones=operaciones,
                           aliases=sorted(set(ALIAS_SOPORTE)))


# ---------------------------------------------------------------------------------------------
# Detalle de un documento
# ---------------------------------------------------------------------------------------------
@documents_bp.route("/<int:doc_id>")
@login_required
def detail(doc_id):
    doc = DocumentService.get_document(doc_id)
    if not doc:
        return jsonify({"success": False, "error": "Documento fuente no encontrado."}), 404

    datos = DocumentService.datos_desde_documento(doc)
    desglose = DocumentService.desglose_documento(doc)
    ficha = DocumentService.tipo_documento(doc.get("tipo"))
    revision = DocumentService.revisar_documento(doc.get("tipo"), datos) if ficha else None
    leyenda = DocumentService.leyenda_educativa()
    anulacion = datos.get("anulacion")

    if _quiere_json():
        return jsonify({
            "success": True,
            "documento": doc,
            "datos": datos,
            "desglose": desglose,
            "tipo_documento": ficha,
            "revision": revision,
            "leyenda_educativa": leyenda,
            "anulacion": anulacion,
        })

    return render_template("documents/detalle.html", documento=doc, datos=datos, desglose=desglose,
                           ficha=ficha, revision=revision, leyenda=leyenda, anulacion=anulacion,
                           categorias=CATEGORIA_ETIQUETAS)


@documents_bp.route("/<int:doc_id>/anular", methods=["POST"])
@login_required
def anular(doc_id):
    motivo = request.form.get("motivo")
    if motivo is None and request.is_json:
        motivo = (request.get_json(silent=True) or {}).get("motivo")

    try:
        documento = DocumentService.anular_documento(doc_id, motivo)
    except ValueError as exc:
        if _quiere_json() or request.is_json:
            return jsonify({"success": False, "error": str(exc)}), 400
        flash(str(exc), "danger")
        return redirect(url_for("documents.detail", doc_id=doc_id))

    if _quiere_json() or request.is_json:
        return jsonify({"success": True, "documento": documento,
                        "mensaje": "El comprobante quedó ANULADO con su motivo registrado."})
    flash("El comprobante quedó ANULADO con su motivo registrado; la fila se conserva en el archivo.",
          "warning")
    return redirect(url_for("documents.detail", doc_id=doc_id))
