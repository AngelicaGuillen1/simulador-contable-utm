# Documentos Fuente Simulados
# Sección que expone los documentos que respaldan cada operación contable del simulador:
# facturas, comprobantes de ingreso/egreso, notas de crédito/débito, papeletas, arqueos, roles y órdenes.
from flask import Blueprint, render_template, request, jsonify
from routes.auth import login_required
from services.document_service import DocumentService, TIPOS_DOCUMENTO

documents_bp = Blueprint("documents", __name__, url_prefix="/documentos")


@documents_bp.route("/")
@login_required
def index():
    tipo = request.args.get("tipo") or None
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin = request.args.get("fecha_fin") or None

    documentos = DocumentService.get_documents(
        tipo=tipo, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, limit=300
    )
    resumen = DocumentService.get_tipos_resumen()
    total_monto = round(sum(d["monto_total"] for d in documentos), 2)

    return render_template(
        "documents/index.html",
        documentos=documentos,
        resumen=resumen,
        tipos=TIPOS_DOCUMENTO,
        etiqueta=DocumentService.get_etiqueta,
        selected_tipo=tipo,
        fecha_inicio=fecha_inicio or "",
        fecha_fin=fecha_fin or "",
        total_monto=total_monto,
    )


@documents_bp.route("/<int:doc_id>")
@login_required
def detail(doc_id):
    doc = DocumentService.get_document(doc_id)
    if not doc:
        return jsonify({"success": False, "error": "Documento fuente no encontrado."}), 404
    return jsonify({"success": True, "documento": doc})
