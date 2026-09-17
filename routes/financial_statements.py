# Financial Statements Routes: Income Statement, Balance Sheet, Cash Flow
from flask import Blueprint, render_template, request
from routes.auth import login_required
from services.accounting_service import AccountingService

financial_bp = Blueprint("financial_statements", __name__, url_prefix="/estados-financieros")

@financial_bp.route("/")
@financial_bp.route("/situacion-financiera")
@login_required
def balance_sheet():
    fecha_corte = request.args.get("fecha_corte")
    bs = AccountingService.get_balance_sheet(fecha_corte=fecha_corte)
    return render_template("financial_statements/balance_sheet.html", bs=bs, fecha_corte=fecha_corte)

@financial_bp.route("/resultados")
@login_required
def income_statement():
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    income = AccountingService.get_income_statement(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    return render_template("financial_statements/income_statement.html", income=income, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

@financial_bp.route("/flujo-efectivo")
@login_required
def cash_flow():
    cf = AccountingService.get_cash_flow_statement()
    return render_template("financial_statements/cash_flow.html", cf=cf)
