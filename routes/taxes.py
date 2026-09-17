# Tributación: configuración tributaria vigente y determinación mensual de IVA
# IMPORTANTE: el sistema NUNCA inventa tasas. Si no existe configuración para un tipo de impuesto,
# las operaciones que lo requieran son rechazadas por TaxService.
from flask import Blueprint, render_template, request, jsonify, g
from routes.auth import login_required
from services.tax_service import TaxService
from services.accounting_service import AccountingService
from services.period_service import PeriodService
from models import get_db_connection
from datetime import date

taxes_bp = Blueprint("taxes", __name__, url_prefix="/impuestos")


@taxes_bp.route("/")
@login_required
def index():
    impuestos = TaxService.get_taxes()
    periodo = PeriodService.get_active_period()
    fecha_inicio = periodo["fecha_inicio"] if periodo else None
    fecha_fin = periodo["fecha_fin"] if periodo else None

    conn = get_db_connection()
    try:
        cuentas = [dict(r) for r in conn.execute(
            "SELECT id, codigo, nombre FROM cuentas WHERE acepta_movimiento = 1 ORDER BY codigo ASC"
        ).fetchall()]

        def saldo_cuenta(codigo):
            cta = conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (codigo,)).fetchone()
            if not cta:
                return 0.0
            return AccountingService.get_account_balance(cta["id"])

        iva_ventas = saldo_cuenta("2.1.02")   # Débito fiscal (IVA cobrado)
        iva_compras = saldo_cuenta("1.1.07")  # Crédito tributario (IVA pagado)
        retenciones = saldo_cuenta("2.1.03")  # Retenciones por pagar
        iva_por_pagar = round(max(0.0, iva_ventas - iva_compras), 2)
        credito_a_favor = round(max(0.0, iva_compras - iva_ventas), 2)
    finally:
        conn.close()

    determinacion = {
        "iva_ventas": iva_ventas,
        "iva_compras": iva_compras,
        "retenciones": retenciones,
        "iva_por_pagar": iva_por_pagar,
        "credito_a_favor": credito_a_favor,
    }

    return render_template(
        "taxes/index.html",
        impuestos=impuestos,
        cuentas=cuentas,
        determinacion=determinacion,
        periodo=periodo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
