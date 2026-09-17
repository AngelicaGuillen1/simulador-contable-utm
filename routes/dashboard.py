# Dashboard Blueprint - Indicadores financieros dinámicos, gráficos reales y alertas operativas
from flask import Blueprint, render_template, g
from routes.auth import login_required
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from services.simulation_service import SimulationService
from services.period_service import PeriodService
from services.document_service import DocumentService
from models import get_db_connection
from datetime import datetime, timedelta

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    fecha_trabajo = PeriodService.get_fecha_trabajo()
    periodo = PeriodService.get_active_period()
    fecha_inicio = periodo["fecha_inicio"] if periodo else None
    fecha_fin = periodo["fecha_fin"] if periodo else None

    conn = get_db_connection()
    try:
        # ---------------- Indicadores financieros (Libro Mayor) ----------------
        caja_balance = AccountingService.get_account_balance(3)      # 1.1.01 Caja General
        pichincha_balance = AccountingService.get_account_balance(4)  # 1.1.02 Banco Pichincha
        guayaquil_balance = AccountingService.get_account_balance(5)  # 1.1.03 Banco Guayaquil
        bancos_total = round(pichincha_balance + guayaquil_balance, 2)

        cxc_total = AccountingService.get_account_balance(6)     # 1.1.04 Cuentas por Cobrar
        cxp_total = AccountingService.get_account_balance(20)    # 2.1.01 Cuentas por Pagar
        inventario_total = AccountingService.get_account_balance(8)  # 1.1.06 Inventario
        iva_ventas = AccountingService.get_account_balance(21)   # 2.1.02 IVA Ventas
        iva_compras = AccountingService.get_account_balance(9)   # 1.1.07 IVA Compras

        income_stmt = AccountingService.get_income_statement(
            fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
        )
        ingresos_total = income_stmt["total_ingresos_operacionales"]
        gastos_total = round(
            income_stmt["total_gastos_operacionales"] + income_stmt["gastos_financieros"], 2
        )
        utilidad_periodo = income_stmt["utilidad_neta"]

        ventas_total = income_stmt["ventas_bienes"]
        servicios_total = income_stmt["ingresos_servicios"]
        costo_ventas_total = income_stmt["costo_ventas"]

        # ---------------- Alertas operativas ----------------
        alertas_stock = InventoryService.get_low_stock_alerts()
        cxc_vencidas = conn.execute("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(saldo_actual), 0) as monto
            FROM cuentas_cobrar
            WHERE estado IN ('PENDIENTE', 'PARCIAL') AND fecha_vencimiento < ?
        """, (fecha_trabajo,)).fetchone()
        cxp_proximas = conn.execute("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(saldo_actual), 0) as monto
            FROM cuentas_pagar
            WHERE estado IN ('PENDIENTE', 'PARCIAL')
        """).fetchone()

        # Asientos descuadrados (control de integridad contable)
        descuadres = conn.execute("""
            SELECT COUNT(*) as cnt FROM (
                SELECT a.id, SUM(d.debe) as debe, SUM(d.haber) as haber
                FROM asientos a JOIN detalle_asientos d ON d.asiento_id = a.id
                WHERE a.estado IN ('CONTABILIZADO', 'REVERTIDO')
                GROUP BY a.id
                HAVING ABS(SUM(d.debe) - SUM(d.haber)) > 0.01
            )
        """).fetchone()["cnt"]

        # ---------------- Actividad reciente ----------------
        recent_journal = conn.execute("""
            SELECT a.id, a.numero_asiento, a.fecha, a.glosa, a.tipo_documento, a.numero_documento,
                   a.origen_modulo,
                   (SELECT COALESCE(SUM(debe), 0) FROM detalle_asientos WHERE asiento_id = a.id) as total_debe
            FROM asientos a
            WHERE a.estado IN ('CONTABILIZADO', 'REVERTIDO')
            ORDER BY a.fecha DESC, a.numero_asiento DESC
            LIMIT 6
        """).fetchall()
        recent_journal = [dict(r) for r in recent_journal]

        ultimos_documentos = DocumentService.get_documents(limit=5)

        # Ventas y servicios recientes
        ultimas_ventas = [dict(r) for r in conn.execute("""
            SELECT v.numero_factura, v.fecha, v.total, v.forma_pago, c.nombre_razon_social as cliente
            FROM ventas v JOIN clientes c ON v.cliente_id = c.id
            ORDER BY v.fecha DESC, v.id DESC LIMIT 5
        """).fetchall()]

        # ---------------- Datos de gráficos (agregaciones reales por semana) ----------------
        def agrupar_por_semana(tabla, columna_fecha, columna_monto, filtro_extra=""):
            """Suma real de una tabla operativa agrupada en 4 semanas del período."""
            if not fecha_inicio:
                return [0.0, 0.0, 0.0, 0.0]
            totales = [0.0, 0.0, 0.0, 0.0]
            filas = conn.execute(f"""
                SELECT {columna_fecha} as fecha, COALESCE(SUM({columna_monto}), 0) as monto
                FROM {tabla}
                WHERE {columna_fecha} >= ? AND {columna_fecha} <= ? {filtro_extra}
                GROUP BY {columna_fecha}
            """, (fecha_inicio, fecha_fin or fecha_trabajo)).fetchall()
            base = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            for f in filas:
                try:
                    df = datetime.strptime(str(f["fecha"])[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    continue
                idx = min(3, max(0, (df - base).days // 7))
                totales[idx] += float(f["monto"] or 0.0)
            return [round(t, 2) for t in totales]

        chart_labels = ["Semana 1", "Semana 2", "Semana 3", "Semana 4"]
        ventas_data = agrupar_por_semana("ventas", "fecha", "subtotal")
        servicios_data = agrupar_por_semana("transacciones_servicios", "fecha", "subtotal")
        compras_data = agrupar_por_semana("compras", "fecha", "subtotal")

        gastos_rows = conn.execute("""
            SELECT a.fecha as fecha, COALESCE(SUM(d.debe - d.haber), 0) as monto
            FROM detalle_asientos d
            JOIN asientos a ON d.asiento_id = a.id
            JOIN cuentas c ON d.cuenta_id = c.id
            WHERE c.codigo IN ('6.1.01','6.1.02','6.1.03','6.1.04','6.1.05','6.1.06','6.2.01')
              AND a.estado IN ('CONTABILIZADO', 'REVERTIDO')
            GROUP BY a.fecha
        """).fetchall()
        gastos_data = [0.0, 0.0, 0.0, 0.0]
        if fecha_inicio:
            base = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            for r in gastos_rows:
                try:
                    df = datetime.strptime(str(r["fecha"])[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    continue
                idx = min(3, max(0, (df - base).days // 7))
                gastos_data[idx] += float(r["monto"] or 0.0)
        gastos_data = [round(g, 2) for g in gastos_data]

        cartera_por_estado = [dict(r) for r in conn.execute("""
            SELECT estado, COUNT(*) as cantidad, COALESCE(SUM(saldo_actual), 0) as monto
            FROM cuentas_cobrar GROUP BY estado
        """).fetchall()]

        inventario_por_categoria = [dict(r) for r in conn.execute("""
            SELECT categoria,
                   COALESCE(SUM(stock_actual * costo_unitario), 0) as valor,
                   COUNT(*) as productos
            FROM productos WHERE activo = 1 GROUP BY categoria ORDER BY valor DESC
        """).fetchall()]

        total_productos = conn.execute("SELECT COUNT(*) as cnt FROM productos WHERE activo = 1").fetchone()["cnt"]
        total_clientes = conn.execute("SELECT COUNT(*) as cnt FROM clientes WHERE activo = 1").fetchone()["cnt"]
        total_proveedores = conn.execute("SELECT COUNT(*) as cnt FROM proveedores WHERE activo = 1").fetchone()["cnt"]
        total_asientos = conn.execute("SELECT COUNT(*) as cnt FROM asientos WHERE estado IN ('CONTABILIZADO', 'REVERTIDO')").fetchone()["cnt"]
        total_documentos = conn.execute("SELECT COUNT(*) as cnt FROM documentos_fuente").fetchone()["cnt"]

        sim_stats = SimulationService.get_teacher_analytics()

        return render_template(
            "dashboard.html",
            fecha_trabajo=fecha_trabajo,
            periodo=periodo,
            caja_balance=caja_balance,
            bancos_total=bancos_total,
            pichincha_balance=pichincha_balance,
            guayaquil_balance=guayaquil_balance,
            cxc_total=cxc_total,
            cxp_total=cxp_total,
            inventario_total=inventario_total,
            iva_ventas=iva_ventas,
            iva_compras=iva_compras,
            ingresos_total=ingresos_total,
            gastos_total=gastos_total,
            utilidad_periodo=utilidad_periodo,
            ventas_total=ventas_total,
            servicios_total=servicios_total,
            costo_ventas_total=costo_ventas_total,
            alertas_stock=alertas_stock,
            cxc_vencidas=cxc_vencidas["cnt"],
            cxc_vencidas_monto=round(float(cxc_vencidas["monto"] or 0), 2),
            cxp_proximas=cxp_proximas["cnt"],
            cxp_proximas_monto=round(float(cxp_proximas["monto"] or 0), 2),
            descuadres=descuadres,
            recent_journal=recent_journal,
            ultimos_documentos=ultimos_documentos,
            ultimas_ventas=ultimas_ventas,
            chart_labels=chart_labels,
            ventas_data=ventas_data,
            servicios_data=servicios_data,
            compras_data=compras_data,
            gastos_data=gastos_data,
            cartera_por_estado=cartera_por_estado,
            inventario_por_categoria=inventario_por_categoria,
            total_productos=total_productos,
            total_clientes=total_clientes,
            total_proveedores=total_proveedores,
            total_asientos=total_asientos,
            total_documentos=total_documentos,
            sim_stats=sim_stats
        )
    finally:
        conn.close()
