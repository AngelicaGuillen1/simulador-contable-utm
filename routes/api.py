# RESTful JSON API Blueprint for Specialized AI Agents & Asynchronous Frontends
from flask import Blueprint, request, jsonify, g
from tools import (
    get_chart_of_accounts, get_account, get_account_balance, validate_journal_entry,
    create_journal_entry, get_product, get_inventory, create_sale, create_purchase,
    create_service_transaction, register_collection, register_payment,
    get_customer_balance, get_supplier_balance, get_tax_configuration, calculate_tax,
    generate_trial_balance, generate_income_statement, generate_balance_sheet, generate_cash_flow,
    get_student_progress, audit_transaction, evaluate_student_attempt
)
from models import get_db_connection

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/accounts", methods=["GET"])
def api_accounts():
    accounts = get_chart_of_accounts()
    return jsonify({"success": True, "accounts": accounts})

@api_bp.route("/accounts/<int:account_id>/balance", methods=["GET"])
def api_account_balance(account_id):
    bal = get_account_balance(account_id)
    return jsonify({"success": True, "account_id": account_id, "balance": bal})

@api_bp.route("/journal/validate", methods=["POST"])
def api_validate_journal():
    data = request.get_json() or {}
    lines = data.get("lineas", [])
    res = validate_journal_entry(lines)
    return jsonify(res)

@api_bp.route("/journal/create", methods=["POST"])
def api_create_journal():
    data = request.get_json() or {}
    try:
        res = create_journal_entry(
            data.get("empresa_id", 1),
            data.get("fecha"),
            data.get("glosa"),
            data.get("lineas", []),
            tipo_documento=data.get("tipo_documento", "MANUAL"),
            numero_documento=data.get("numero_documento"),
            origen_modulo=data.get("origen_modulo", "API"),
            usuario_id=data.get("usuario_id", 1)
        )
        return jsonify({"success": True, "data": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@api_bp.route("/products", methods=["GET"])
def api_products():
    cat = request.args.get("categoria")
    prods = get_inventory(categoria=cat)
    return jsonify({"success": True, "products": prods})

@api_bp.route("/inventory/<int:product_id>", methods=["GET"])
def api_inventory_product(product_id):
    p = get_product(product_id)
    return jsonify({"success": True, "product": p})

@api_bp.route("/sales", methods=["POST"])
def api_create_sale():
    data = request.get_json() or {}
    try:
        res = create_sale(
            data.get("empresa_id", 1),
            data.get("cliente_id"),
            data.get("items", []),
            forma_pago=data.get("forma_pago", "EFECTIVO"),
            banco_id=data.get("banco_id"),
            dias_credito=data.get("dias_credito", 0),
            usuario_id=data.get("usuario_id", 1)
        )
        return jsonify({"success": True, "data": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@api_bp.route("/purchases", methods=["POST"])
def api_create_purchase():
    data = request.get_json() or {}
    try:
        res = create_purchase(
            data.get("empresa_id", 1),
            data.get("proveedor_id"),
            data.get("numero_factura"),
            data.get("items", []),
            forma_pago=data.get("forma_pago", "EFECTIVO"),
            banco_id=data.get("banco_id"),
            dias_credito=data.get("dias_credito", 0),
            usuario_id=data.get("usuario_id", 1)
        )
        return jsonify({"success": True, "data": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@api_bp.route("/taxes", methods=["GET"])
def api_taxes():
    taxes = get_tax_configuration()
    return jsonify({"success": True, "taxes": taxes})

@api_bp.route("/statements", methods=["GET"])
def api_statements():
    tipo = request.args.get("tipo", "balance_sheet")
    if tipo == "income_statement":
        data = generate_income_statement()
    elif tipo == "cash_flow":
        data = generate_cash_flow()
    else:
        data = generate_balance_sheet()
    return jsonify({"success": True, "statement": data})

@api_bp.route("/audit", methods=["GET"])
def api_audit():
    modulo = request.args.get("modulo")
    logs = audit_transaction(None, modulo=modulo)
    return jsonify({"success": True, "logs": logs})

@api_bp.route("/search", methods=["GET"])
def global_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": {}})

    q_pattern = f"%{query}%"
    conn = get_db_connection()
    try:
        cuentas = conn.execute("SELECT id, codigo, nombre FROM cuentas WHERE codigo LIKE ? OR nombre LIKE ? LIMIT 5", (q_pattern, q_pattern)).fetchall()
        clientes = conn.execute("SELECT id, identificacion, nombre_razon_social FROM clientes WHERE identificacion LIKE ? OR nombre_razon_social LIKE ? LIMIT 5", (q_pattern, q_pattern)).fetchall()
        proveedores = conn.execute("SELECT id, identificacion, razon_social FROM proveedores WHERE identificacion LIKE ? OR razon_social LIKE ? LIMIT 5", (q_pattern, q_pattern)).fetchall()
        productos = conn.execute("SELECT id, codigo, descripcion FROM productos WHERE codigo LIKE ? OR descripcion LIKE ? LIMIT 5", (q_pattern, q_pattern)).fetchall()
        asientos = conn.execute("SELECT id, numero_asiento, fecha, glosa FROM asientos WHERE numero_asiento LIKE ? OR glosa LIKE ? LIMIT 5", (q_pattern, q_pattern)).fetchall()
        simulaciones = conn.execute("SELECT id, titulo, nivel FROM simulaciones WHERE titulo LIKE ? LIMIT 5", (q_pattern,)).fetchall()

        return jsonify({
            "results": {
                "cuentas": [dict(c) for c in cuentas],
                "clientes": [dict(c) for c in clientes],
                "proveedores": [dict(p) for p in proveedores],
                "productos": [dict(pr) for pr in productos],
                "asientos": [dict(a) for a in asientos],
                "simulaciones": [dict(s) for s in simulaciones]
            }
        })
    finally:
        conn.close()


# ============================================================================
# API ampliada para los agentes especializados del simulador
# Todas las respuestas son JSON y todos los cambios pasan por los servicios
# estructurados (ningún agente escribe directamente en SQLite).
# ============================================================================
from services.accounting_service import AccountingService          # noqa: E402
from services.inventory_service import InventoryService            # noqa: E402
from services.sales_service import SalesService                    # noqa: E402
from services.purchase_service import PurchaseService              # noqa: E402
from services.simulation_service import SimulationService          # noqa: E402
from services.evaluation_service import EvaluationService          # noqa: E402
from services.document_service import DocumentService              # noqa: E402
from services.tax_service import TaxService                        # noqa: E402
from services.treasury_service import TreasuryService              # noqa: E402
from services.period_service import PeriodService                  # noqa: E402
import tools as agent_tools                                        # noqa: E402


@api_bp.route("/health", methods=["GET"])
def api_health():
    try:
        conn = get_db_connection()
        try:
            tablas = conn.execute("SELECT COUNT(*) as cnt FROM sqlite_master WHERE type = 'table'").fetchone()["cnt"]
        finally:
            conn.close()
        return jsonify({
            "success": True,
            "sistema": "Simulador Integral de Sistema Contable",
            "estado": "OPERATIVO",
            "tablas": tablas,
            "fecha_trabajo": PeriodService.get_fecha_trabajo(),
            "periodo_activo": PeriodService.get_active_period(),
        })
    except Exception as e:
        return jsonify({"success": False, "estado": "ERROR", "error": str(e)}), 500


@api_bp.route("/dashboard", methods=["GET"])
def api_dashboard():
    """Indicadores financieros consolidados para agentes y frontends."""
    income = AccountingService.get_income_statement()
    return jsonify({
        "success": True,
        "indicadores": {
            "caja": AccountingService.get_account_balance(3),
            "banco_pichincha": AccountingService.get_account_balance(4),
            "banco_guayaquil": AccountingService.get_account_balance(5),
            "cuentas_por_cobrar": AccountingService.get_account_balance(6),
            "inventario": AccountingService.get_account_balance(8),
            "iva_compras": AccountingService.get_account_balance(9),
            "cuentas_por_pagar": AccountingService.get_account_balance(20),
            "iva_ventas": AccountingService.get_account_balance(21),
        },
        "estado_resultados": income,
        "fecha_trabajo": PeriodService.get_fecha_trabajo(),
        "periodo": PeriodService.get_active_period(),
    })


@api_bp.route("/inventory", methods=["GET"])
def api_inventory():
    categoria = request.args.get("categoria")
    productos = InventoryService.get_products(categoria=categoria, activo_only=False)
    return jsonify({
        "success": True,
        "total": len(productos),
        "valor_total_inventario": round(sum(p["stock_actual"] * p["costo_unitario"] for p in productos), 2),
        "productos": productos,
    })


@api_bp.route("/inventory/alerts", methods=["GET"])
def api_inventory_alerts():
    return jsonify({"success": True, "alertas": InventoryService.get_low_stock_alerts()})


@api_bp.route("/services", methods=["GET", "POST"])
def api_services():
    if request.method == "GET":
        conn = get_db_connection()
        try:
            rows = conn.execute("SELECT * FROM catalogo_servicios WHERE activo = 1 ORDER BY nombre ASC").fetchall()
            return jsonify({"success": True, "servicios": [dict(r) for r in rows]})
        finally:
            conn.close()

    data = request.get_json() or {}
    try:
        res = create_service_transaction(
            data.get("empresa_id", 1),
            data.get("cliente_id"),
            data.get("servicio_id"),
            cantidad=data.get("cantidad", 1.0),
            tarifa=data.get("tarifa"),
            descripcion=data.get("descripcion", ""),
            forma_pago=data.get("forma_pago", "EFECTIVO"),
            banco_id=data.get("banco_id"),
            dias_credito=data.get("dias_credito", 0),
            usuario_id=data.get("usuario_id", 1),
            fecha=data.get("fecha"),
        )
        return jsonify({"success": True, "data": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/customers", methods=["GET"])
def api_customers():
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM clientes ORDER BY nombre_razon_social ASC").fetchall()
        return jsonify({"success": True, "clientes": [dict(r) for r in rows]})
    finally:
        conn.close()


@api_bp.route("/customers/<int:cliente_id>/history", methods=["GET"])
def api_customer_history(cliente_id):
    conn = get_db_connection()
    try:
        cliente = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
        if not cliente:
            return jsonify({"success": False, "error": "Cliente no encontrado."}), 404

        ventas = [dict(r) for r in conn.execute("""
            SELECT numero_factura, fecha, forma_pago, subtotal, iva_valor, total, estado
            FROM ventas WHERE cliente_id = ? ORDER BY fecha DESC, id DESC
        """, (cliente_id,)).fetchall()]

        servicios = [dict(r) for r in conn.execute("""
            SELECT t.numero_factura, t.fecha, s.nombre as servicio, t.cantidad, t.tarifa, t.total,
                   t.forma_pago, t.estado
            FROM transacciones_servicios t
            JOIN catalogo_servicios s ON t.servicio_id = s.id
            WHERE t.cliente_id = ? ORDER BY t.fecha DESC, t.id DESC
        """, (cliente_id,)).fetchall()]

        cobros = [dict(r) for r in conn.execute("""
            SELECT c.fecha, c.monto, c.medio_pago, c.numero_comprobante, cc.numero_documento
            FROM cobros c JOIN cuentas_cobrar cc ON c.cuenta_cobrar_id = cc.id
            WHERE cc.cliente_id = ? ORDER BY c.fecha DESC, c.id DESC
        """, (cliente_id,)).fetchall()]

        cartera = [dict(r) for r in conn.execute("""
            SELECT numero_documento, tipo_origen, fecha_emision, fecha_vencimiento,
                   monto_original, saldo_actual, estado
            FROM cuentas_cobrar WHERE cliente_id = ? ORDER BY fecha_vencimiento ASC
        """, (cliente_id,)).fetchall()]

        return jsonify({
            "success": True,
            "cliente": dict(cliente),
            "ventas": ventas,
            "servicios": servicios,
            "cobros": cobros,
            "cuentas_cobrar": cartera,
        })
    finally:
        conn.close()


@api_bp.route("/suppliers", methods=["GET"])
def api_suppliers():
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM proveedores ORDER BY razon_social ASC").fetchall()
        return jsonify({"success": True, "proveedores": [dict(r) for r in rows]})
    finally:
        conn.close()


@api_bp.route("/suppliers/<int:proveedor_id>/history", methods=["GET"])
def api_supplier_history(proveedor_id):
    conn = get_db_connection()
    try:
        proveedor = conn.execute("SELECT * FROM proveedores WHERE id = ?", (proveedor_id,)).fetchone()
        if not proveedor:
            return jsonify({"success": False, "error": "Proveedor no encontrado."}), 404

        compras = [dict(r) for r in conn.execute("""
            SELECT numero_factura, fecha, forma_pago, subtotal, iva_valor, total, estado
            FROM compras WHERE proveedor_id = ? ORDER BY fecha DESC, id DESC
        """, (proveedor_id,)).fetchall()]

        pagos = [dict(r) for r in conn.execute("""
            SELECT p.fecha, p.monto, p.medio_pago, p.numero_comprobante, cp.numero_factura
            FROM pagos p JOIN cuentas_pagar cp ON p.cuenta_pagar_id = cp.id
            WHERE cp.proveedor_id = ? ORDER BY p.fecha DESC, p.id DESC
        """, (proveedor_id,)).fetchall()]

        obligaciones = [dict(r) for r in conn.execute("""
            SELECT numero_factura, fecha_emision, fecha_vencimiento, monto_original, saldo_actual, estado
            FROM cuentas_pagar WHERE proveedor_id = ? ORDER BY fecha_vencimiento ASC
        """, (proveedor_id,)).fetchall()]

        return jsonify({
            "success": True,
            "proveedor": dict(proveedor),
            "compras": compras,
            "pagos": pagos,
            "cuentas_pagar": obligaciones,
        })
    finally:
        conn.close()


@api_bp.route("/receivables", methods=["GET"])
def api_receivables():
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT c.*, cl.nombre_razon_social as cliente_nombre
            FROM cuentas_cobrar c JOIN clientes cl ON c.cliente_id = cl.id
            ORDER BY c.fecha_vencimiento ASC
        """).fetchall()
        return jsonify({"success": True, "cuentas_por_cobrar": [dict(r) for r in rows]})
    finally:
        conn.close()


@api_bp.route("/payables", methods=["GET"])
def api_payables():
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT c.*, p.razon_social as proveedor_nombre
            FROM cuentas_pagar c JOIN proveedores p ON c.proveedor_id = p.id
            ORDER BY c.fecha_vencimiento ASC
        """).fetchall()
        return jsonify({"success": True, "cuentas_por_pagar": [dict(r) for r in rows]})
    finally:
        conn.close()


@api_bp.route("/collections", methods=["POST"])
def api_collections():
    data = request.get_json() or {}
    try:
        res = register_collection(
            data.get("cuenta_cobrar_id"), data.get("monto"),
            medio_pago=data.get("medio_pago", "EFECTIVO"),
            banco_id=data.get("banco_id", 1),
            numero_comprobante=data.get("numero_comprobante", ""),
            usuario_id=data.get("usuario_id", 1),
            fecha=data.get("fecha"),
        )
        return jsonify({"success": True, "cobro_id": res[0], "nuevo_saldo": res[1], "estado": res[2]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/payments", methods=["POST"])
def api_payments():
    data = request.get_json() or {}
    try:
        res = register_payment(
            data.get("cuenta_pagar_id"), data.get("monto"),
            medio_pago=data.get("medio_pago", "TRANSFERENCIA"),
            banco_id=data.get("banco_id", 1),
            numero_comprobante=data.get("numero_comprobante", ""),
            usuario_id=data.get("usuario_id", 1),
            fecha=data.get("fecha"),
        )
        return jsonify({"success": True, "pago_id": res[0], "nuevo_saldo": res[1], "estado": res[2]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/treasury", methods=["GET"])
def api_treasury():
    return jsonify({
        "success": True,
        "cajas": TreasuryService.get_cash_boxes(),
        "bancos": TreasuryService.get_banks(),
    })


@api_bp.route("/taxes/calculate", methods=["POST"])
def api_calculate_tax():
    data = request.get_json() or {}
    try:
        base = float(data.get("base", 0.0))
        if base < 0:
            raise ValueError("La base imponible no puede ser negativa.")
        res = TaxService.calculate_tax(base, codigo_impuesto=data.get("codigo"), tipo=data.get("tipo", "IVA_VENTAS"))
        return jsonify({"success": True, **res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/periods", methods=["GET"])
def api_periods():
    return jsonify({
        "success": True,
        "periodos": PeriodService.get_periods(),
        "periodo_activo": PeriodService.get_active_period(),
        "fecha_trabajo": PeriodService.get_fecha_trabajo(),
    })


@api_bp.route("/documents", methods=["GET"])
def api_documents():
    tipo = request.args.get("tipo")
    docs = DocumentService.get_documents(tipo=tipo, limit=200)
    return jsonify({"success": True, "total": len(docs), "documentos": docs})


@api_bp.route("/documents/<int:doc_id>", methods=["GET"])
def api_document_detail(doc_id):
    doc = DocumentService.get_document(doc_id)
    if not doc:
        return jsonify({"success": False, "error": "Documento fuente no encontrado."}), 404
    return jsonify({"success": True, "documento": doc})


@api_bp.route("/simulations", methods=["GET"])
def api_simulations():
    sims = SimulationService.get_simulations()
    return jsonify({"success": True, "simulaciones": sims})


@api_bp.route("/simulations/<int:simulacion_id>", methods=["GET"])
def api_simulation_detail(simulacion_id):
    sim = SimulationService.get_simulation_by_id(simulacion_id)
    if not sim:
        return jsonify({"success": False, "error": "Simulación no encontrada."}), 404
    for caso in sim.get("casos", []):
        caso.pop("solucion_esperada_json", None)
    return jsonify({"success": True, "simulacion": sim})


@api_bp.route("/evaluate", methods=["POST"])
def api_evaluate():
    data = request.get_json() or {}
    try:
        res = evaluate_student_attempt(
            data.get("intento_id"), data.get("caso_id"), data.get("lineas", []),
            pistas_usadas=data.get("pistas_usadas", 0),
            tiempo_segundos=data.get("tiempo_segundos", 0),
            usuario_id=data.get("usuario_id", 3),
        )
        return jsonify({"success": True, "evaluacion": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/progress/<int:estudiante_id>", methods=["GET"])
def api_student_progress(estudiante_id):
    return jsonify({"success": True, "progreso": get_student_progress(estudiante_id)})


@api_bp.route("/tools", methods=["GET"])
def api_tools():
    """Catálogo de herramientas estructuradas disponibles para los agentes."""
    nombres = [
        "get_chart_of_accounts", "get_account", "get_account_balance", "validate_journal_entry",
        "create_journal_entry", "reverse_journal_entry", "close_accounting_period",
        "get_product", "get_inventory", "register_inventory_entry", "register_inventory_exit",
        "calculate_weighted_average", "calculate_fifo", "calculate_cost_of_goods_sold",
        "create_sale", "create_purchase", "create_service_transaction", "create_receivable",
        "create_payable", "register_collection", "register_payment", "get_customer_balance",
        "get_supplier_balance", "get_cash_balance", "get_bank_balance", "reconcile_bank",
        "get_tax_configuration", "calculate_tax", "generate_trial_balance", "generate_income_statement",
        "generate_balance_sheet", "generate_cash_flow", "create_simulation_case",
        "evaluate_student_attempt", "generate_feedback", "get_student_progress", "audit_transaction",
    ]
    return jsonify({
        "success": True,
        "total": len(nombres),
        "disponibles": [n for n in nombres if hasattr(agent_tools, n)],
        "faltantes": [n for n in nombres if not hasattr(agent_tools, n)],
    })
