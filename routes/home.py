# Página de Inicio Pública del Simulador
# Muestra el encabezado profesional, el mensaje institucional, los accesos principales
# y los indicadores rápidos obtenidos dinámicamente desde SQLite.
from flask import Blueprint, render_template, redirect, url_for, session, send_from_directory
import os

from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from services.period_service import PeriodService
from config import Config

home_bp = Blueprint("home", __name__)

# Directorio de documentación del proyecto (docs/)
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")


@home_bp.route("/")
def index():
    # Si ya existe una sesión activa, el usuario pasa directamente a su dashboard.
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    caja = AccountingService.get_account_balance(3)      # 1.1.01 Caja General
    pichincha = AccountingService.get_account_balance(4)  # 1.1.02 Banco Pichincha
    guayaquil = AccountingService.get_account_balance(5)  # 1.1.03 Banco Guayaquil
    cxc = AccountingService.get_account_balance(6)        # 1.1.04 Cuentas por Cobrar
    cxp = AccountingService.get_account_balance(20)       # 2.1.01 Cuentas por Pagar
    inventario = AccountingService.get_account_balance(8)  # 1.1.06 Inventario de Mercaderías
    income = AccountingService.get_income_statement()

    indicadores = {
        "caja": caja,
        "bancos": round(pichincha + guayaquil, 2),
        "inventario": inventario,
        "cuentas_por_cobrar": cxc,
        "cuentas_por_pagar": cxp,
        "ingresos": income["total_ingresos_operacionales"],
        "gastos": round(income["total_gastos_operacionales"] + income["gastos_financieros"], 2),
        "resultado": income["utilidad_neta"],
        "productos": len(InventoryService.get_products()),
        "periodo": PeriodService.get_active_period(),
        "fecha_trabajo": PeriodService.get_fecha_trabajo(),
    }

    return render_template(
        "index.html",
        app_name=Config.APP_NAME,
        app_subtitle=Config.APP_SUBTITLE,
        empresa=Config.COMPANY_NAME,
        empresa_ruc=Config.COMPANY_RUC,
        indicadores=indicadores,
    )


@home_bp.route("/manual")
def manual():
    """Manual de Usuario del sistema (página imprimible generada desde docs/MANUAL_DE_USUARIO.md)."""
    return send_from_directory(DOCS_DIR, "MANUAL_DE_USUARIO.html")


@home_bp.route("/manual/fuente")
def manual_fuente():
    """Fuente Markdown del manual, para descarga y edición."""
    return send_from_directory(
        DOCS_DIR, "MANUAL_DE_USUARIO.md", as_attachment=True, download_name="MANUAL_DE_USUARIO.md"
    )
