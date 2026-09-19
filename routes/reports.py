# Reports Blueprint: informes consolidados y exportación a CSV, Excel (XLSX) y versión imprimible (PDF)
import csv
import io
from flask import Blueprint, render_template, request, Response, g
from routes.auth import login_required
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from services.simulation_service import SimulationService
from services.period_service import PeriodService
from models import get_db_contable

reports_bp = Blueprint("reports", __name__, url_prefix="/reportes")

# Definición de los reportes disponibles: tipo -> (título, grupo, constructor de filas)
REPORTES = {
    "diario": ("Libro Diario", "Contabilidad"),
    "mayor": ("Libro Mayor", "Contabilidad"),
    "balance": ("Balance de Comprobación", "Contabilidad"),
    "ventas": ("Registro de Ventas", "Operaciones"),
    "compras": ("Registro de Compras", "Operaciones"),
    "servicios": ("Registro de Servicios Prestados", "Operaciones"),
    "inventario": ("Inventario y Existencias", "Inventarios"),
    "kardex": ("Kardex Consolidado", "Inventarios"),
    "caja": ("Movimientos de Caja", "Tesorería y Cartera"),
    "bancos": ("Movimientos Bancarios", "Tesorería y Cartera"),
    "cartera": ("Cartera de Cuentas por Cobrar", "Tesorería y Cartera"),
    "cuentas-pagar": ("Cuentas por Pagar a Proveedores", "Tesorería y Cartera"),
    "resultados": ("Estado de Resultados", "Estados Financieros"),
    "situacion-financiera": ("Estado de Situación Financiera", "Estados Financieros"),
    "flujo-efectivo": ("Estado de Flujo de Efectivo", "Estados Financieros"),
    "academico": ("Resultados Académicos de Simulaciones", "Académico"),
}


def _filas_reporte(tipo, db_path=None):
    """Devuelve (encabezados, filas) con los datos reales de cada reporte."""
    conn = get_db_contable(db_path)
    try:
        if tipo == "diario":
            filas = []
            for a in AccountingService.get_journal_entries(db_path=db_path):
                for d in a["detalles"]:
                    filas.append([a["numero_asiento"], a["fecha"], a["glosa"], a["tipo_documento"],
                                  d["cuenta_codigo"], d["cuenta_nombre"], d["debe"], d["haber"], d["referencia"]])
            return ["N° Asiento", "Fecha", "Glosa", "Documento", "Código Cuenta", "Cuenta",
                    "Debe", "Haber", "Referencia"], filas

        if tipo == "mayor":
            filas = []
            for cta in AccountingService.get_ledger(db_path=db_path):
                for m in cta["movimientos"]:
                    filas.append([cta["codigo"], cta["nombre"], m["fecha"], m["numero_asiento"],
                                  m["glosa"], m["debe"], m["haber"], m["saldo"]])
            return ["Código", "Cuenta", "Fecha", "N° Asiento", "Concepto", "Debe", "Haber", "Saldo"], filas

        if tipo == "balance":
            trial = AccountingService.get_trial_balance(db_path=db_path)
            filas = [[c["codigo"], c["nombre"], c["naturaleza"], c["debitos"], c["creditos"],
                      c["saldo_deudor"], c["saldo_acreedor"]] for c in trial["cuentas"]]
            filas.append(["TOTALES", "", "", trial["total_debitos"], trial["total_creditos"],
                          trial["total_saldo_deudor"], trial["total_saldo_acreedor"]])
            return ["Código", "Cuenta", "Naturaleza", "Débitos", "Créditos",
                    "Saldo Deudor", "Saldo Acreedor"], filas

        if tipo == "ventas":
            filas = [list(r) for r in conn.execute("""
                SELECT v.numero_factura, v.fecha, c.nombre_razon_social, v.forma_pago, v.subtotal,
                       v.iva_valor, v.total, v.costo_ventas_total, v.estado
                FROM ventas v JOIN clientes c ON v.cliente_id = c.id
                ORDER BY v.fecha ASC, v.id ASC
            """).fetchall()]
            return ["Factura", "Fecha", "Cliente", "Forma Pago", "Subtotal", "IVA", "Total",
                    "Costo de Ventas", "Estado"], filas

        if tipo == "compras":
            filas = [list(r) for r in conn.execute("""
                SELECT co.numero_factura, co.fecha, p.razon_social, co.forma_pago, co.subtotal,
                       co.iva_valor, co.total, co.estado
                FROM compras co JOIN proveedores p ON co.proveedor_id = p.id
                ORDER BY co.fecha ASC, co.id ASC
            """).fetchall()]
            return ["Factura", "Fecha", "Proveedor", "Forma Pago", "Subtotal", "IVA", "Total", "Estado"], filas

        if tipo == "servicios":
            filas = [list(r) for r in conn.execute("""
                SELECT t.numero_factura, t.fecha, c.nombre_razon_social, s.nombre, t.cantidad,
                       t.tarifa, t.subtotal, t.iva_valor, t.total, t.forma_pago
                FROM transacciones_servicios t
                JOIN clientes c ON t.cliente_id = c.id
                JOIN catalogo_servicios s ON t.servicio_id = s.id
                ORDER BY t.fecha ASC, t.id ASC
            """).fetchall()]
            return ["Factura", "Fecha", "Cliente", "Servicio", "Cantidad", "Tarifa", "Subtotal",
                    "IVA", "Total", "Forma Pago"], filas

        if tipo == "inventario":
            filas = [[p["codigo"], p["categoria"], p["descripcion"], p["unidad_medida"], p["costo_unitario"],
                      p["precio_venta"], p["stock_actual"], p["stock_minimo"], p["stock_maximo"],
                      round(p["stock_actual"] * p["costo_unitario"], 2)] for p in InventoryService.get_products(activo_only=False, db_path=db_path)]
            return ["Código", "Categoría", "Descripción", "Unidad", "Costo Unitario", "Precio Venta",
                    "Stock Actual", "Stock Mínimo", "Stock Máximo", "Valor Stock"], filas

        if tipo == "kardex":
            filas = [list(r) for r in conn.execute("""
                SELECT p.codigo, p.descripcion, m.fecha, m.tipo_movimiento, m.tipo_documento,
                       m.numero_documento, m.cantidad, m.costo_unitario, m.costo_total,
                       m.saldo_cantidad, m.saldo_costo_total
                FROM movimientos_inventario m JOIN productos p ON m.producto_id = p.id
                ORDER BY p.codigo ASC, m.fecha ASC, m.id ASC
            """).fetchall()]
            return ["Código", "Producto", "Fecha", "Movimiento", "Documento", "Número", "Cantidad",
                    "Costo Unitario", "Costo Total", "Saldo Cantidad", "Saldo Valor"], filas

        if tipo == "caja":
            filas = [list(r) for r in conn.execute("""
                SELECT c.nombre, m.fecha, m.tipo_movimiento, m.monto, m.concepto, m.numero_comprobante,
                       m.asiento_id
                FROM movimientos_caja m JOIN cajas c ON m.caja_id = c.id
                ORDER BY m.fecha ASC, m.id ASC
            """).fetchall()]
            return ["Caja", "Fecha", "Tipo Movimiento", "Monto", "Concepto", "Comprobante", "Asiento"], filas

        if tipo == "bancos":
            filas = [list(r) for r in conn.execute("""
                SELECT b.nombre_banco, b.numero_cuenta, m.fecha, m.tipo_movimiento, m.monto,
                       m.concepto, m.numero_referencia, CASE m.conciliado WHEN 1 THEN 'Sí' ELSE 'No' END
                FROM movimientos_bancarios m JOIN bancos b ON m.banco_id = b.id
                ORDER BY m.fecha ASC, m.id ASC
            """).fetchall()]
            return ["Banco", "N° Cuenta", "Fecha", "Tipo Movimiento", "Monto", "Concepto",
                    "Referencia", "Conciliado"], filas

        if tipo == "cartera":
            filas = [list(r) for r in conn.execute("""
                SELECT c.numero_documento, cl.nombre_razon_social, c.tipo_origen, c.fecha_emision,
                       c.fecha_vencimiento, c.monto_original, c.saldo_actual, c.estado
                FROM cuentas_cobrar c JOIN clientes cl ON c.cliente_id = cl.id
                ORDER BY c.fecha_vencimiento ASC
            """).fetchall()]
            return ["Documento", "Cliente", "Origen", "Emisión", "Vencimiento", "Monto Original",
                    "Saldo", "Estado"], filas

        if tipo == "cuentas-pagar":
            filas = [list(r) for r in conn.execute("""
                SELECT c.numero_factura, p.razon_social, c.fecha_emision, c.fecha_vencimiento,
                       c.monto_original, c.saldo_actual, c.estado
                FROM cuentas_pagar c JOIN proveedores p ON c.proveedor_id = p.id
                ORDER BY c.fecha_vencimiento ASC
            """).fetchall()]
            return ["Factura", "Proveedor", "Emisión", "Vencimiento", "Monto Original", "Saldo", "Estado"], filas

        if tipo == "resultados":
            i = AccountingService.get_income_statement(db_path=db_path)
            filas = [
                ["Ingresos por ventas de bienes", i["ventas_bienes"]],
                ["Ingresos por prestación de servicios", i["ingresos_servicios"]],
                ["Total ingresos operacionales", i["total_ingresos_operacionales"]],
                ["(-) Costo de ventas", i["costo_ventas"]],
                ["Utilidad bruta en ventas", i["utilidad_bruta"]],
                ["(-) Gastos administrativos", i["gastos_administrativos"]["total"]],
                ["(-) Gastos de ventas", i["gastos_ventas"]["total"]],
                ["Utilidad operacional", i["utilidad_operacional"]],
                ["(+) Otros ingresos", i["otros_ingresos"]],
                ["(-) Gastos financieros", i["gastos_financieros"]],
                ["Utilidad / (Pérdida) neta del período", i["utilidad_neta"]],
            ]
            return ["Concepto", "Valor USD"], filas

        if tipo == "situacion-financiera":
            bs = AccountingService.get_balance_sheet(db_path=db_path)
            filas = []
            for grupo, total in [("ACTIVO CORRIENTE", bs["total_activo_corriente"]),
                                 ("ACTIVO NO CORRIENTE", bs["total_activo_no_corriente"])]:
                filas.append([grupo, ""])
                for it in bs["activos_corrientes"] if grupo == "ACTIVO CORRIENTE" else bs["activos_no_corrientes"]:
                    filas.append([f"  {it['codigo']} {it['nombre']}", round(it["valor"] * it["signo"], 2)])
                filas.append([f"Total {grupo.title()}", total])
            filas.append(["TOTAL ACTIVO", bs["total_activo"]])
            for grupo in ("pasivos_corrientes", "pasivos_no_corrientes"):
                nombres = {"pasivos_corrientes": "PASIVO CORRIENTE", "pasivos_no_corrientes": "PASIVO NO CORRIENTE"}
                filas.append([nombres[grupo], ""])
                for it in bs[grupo]:
                    filas.append([f"  {it['codigo']} {it['nombre']}", round(it["valor"] * it["signo"], 2)])
            filas.append(["TOTAL PASIVO", bs["total_pasivo"]])
            for it in bs["patrimonio"]:
                filas.append([f"  {it['codigo']} {it['nombre']}", round(it["valor"] * it["signo"], 2)])
            filas.append(["TOTAL PATRIMONIO", bs["total_patrimonio"]])
            filas.append(["TOTAL PASIVO Y PATRIMONIO", bs["total_pasivo_y_patrimonio"]])
            filas.append(["Ecuación Activo = Pasivo + Patrimonio", "CUMPLE" if bs["balanceado"] else f"DIFERENCIA {bs['diferencia']}"])
            return ["Concepto", "Valor USD"], filas

        if tipo == "flujo-efectivo":
            cf = AccountingService.get_cash_flow_statement(db_path=db_path)
            filas = [["ACTIVIDADES DE OPERACIÓN", ""]]
            filas += [[f"  {x['fecha']} {x['concepto']}", x["monto"]] for x in cf["flujo_operacion"]]
            filas.append(["Total actividades de operación", cf["total_operacion"]])
            filas.append(["ACTIVIDADES DE INVERSIÓN", ""])
            filas += [[f"  {x['fecha']} {x['concepto']}", x["monto"]] for x in cf["flujo_inversion"]]
            filas.append(["Total actividades de inversión", cf["total_inversion"]])
            filas.append(["ACTIVIDADES DE FINANCIAMIENTO", ""])
            filas += [[f"  {x['fecha']} {x['concepto']}", x["monto"]] for x in cf["flujo_financiamiento"]]
            filas.append(["Total actividades de financiamiento", cf["total_financiamiento"]])
            filas.append(["Variación neta del efectivo", cf["variacion_neta_efectivo"]])
            return ["Concepto", "Monto USD"], filas

        if tipo == "academico":
            filas = [list(r) for r in conn.execute("""
                SELECT u.nombre_completo, s.titulo, s.nivel, i.fecha_inicio, i.fecha_fin,
                       i.estado, i.puntuacion_total, i.tiempo_segundos,
                       (SELECT COUNT(*) FROM detalle_intentos di WHERE di.intento_id = i.id) as casos_resueltos
                FROM intentos_estudiante i
                JOIN usuarios u ON i.estudiante_id = u.id
                JOIN simulaciones s ON i.simulacion_id = s.id
                ORDER BY i.fecha_inicio DESC
            """).fetchall()]
            return ["Estudiante", "Simulación", "Nivel", "Inicio", "Fin", "Estado", "Puntuación",
                    "Tiempo (s)", "Casos resueltos"], filas

        raise ValueError(f"Reporte no reconocido: '{tipo}'.")
    finally:
        conn.close()


@reports_bp.route("/")
@login_required
def index():
    grupos = {}
    for tipo, (titulo, grupo) in REPORTES.items():
        grupos.setdefault(grupo, []).append({"tipo": tipo, "titulo": titulo})
    return render_template("reports/index.html", grupos=grupos, reportes=REPORTES)


@reports_bp.route("/exportar/csv/<tipo>")
@login_required
def export_csv(tipo):
    if tipo not in REPORTES:
        return Response(f"Reporte no reconocido: {tipo}", status=404, mimetype="text/plain")
    encabezados, filas = _filas_reporte(tipo)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(encabezados)
    writer.writerows(filas)
    output.seek(0)
    nombre = f"{tipo.replace('-', '_')}.csv"
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment;filename={nombre}"}
    )


@reports_bp.route("/exportar/excel/<tipo>")
@login_required
def export_excel(tipo):
    if tipo not in REPORTES:
        return Response(f"Reporte no reconocido: {tipo}", status=404, mimetype="text/plain")
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return Response(
            "La exportación a Excel requiere la librería openpyxl. "
            "Instale las dependencias con: pip install -r requirements.txt",
            status=500, mimetype="text/plain"
        )

    encabezados, filas = _filas_reporte(tipo)
    wb = Workbook()
    ws = wb.active
    ws.title = REPORTES[tipo][0][:31]

    ws.append([REPORTES[tipo][0]])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Empresa: Comercial y Servicios Nueva Esperanza S.A. | Fecha de trabajo: {PeriodService.get_fecha_trabajo()}"])
    ws.append([])
    ws.append(encabezados)
    fila_encabezado = ws.max_row
    for celda in ws[fila_encabezado]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1E3A8A")
        celda.alignment = Alignment(horizontal="center")

    for f in filas:
        ws.append(f)

    for i, _ in enumerate(encabezados, start=1):
        letra = ws.cell(row=fila_encabezado, column=i).column_letter
        ws.column_dimensions[letra].width = max(14, min(45, len(str(encabezados[i - 1])) + 8))

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    nombre = f"{tipo.replace('-', '_')}.xlsx"
    return Response(
        buffer.read(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename={nombre}"}
    )


@reports_bp.route("/imprimible/<tipo>")
@login_required
def printable(tipo):
    if tipo not in REPORTES:
        return render_template("404.html", mensaje=f"El reporte '{tipo}' no existe."), 404
    encabezados, filas = _filas_reporte(tipo)
    trial = AccountingService.get_trial_balance() if tipo == "balance" else None
    return render_template(
        "reports/print.html",
        titulo=REPORTES[tipo][0],
        grupo=REPORTES[tipo][1],
        encabezados=encabezados,
        filas=filas,
        tipo=tipo,
        trial=trial,
        empresa="Comercial y Servicios Nueva Esperanza S.A.",
        ruc="1792345678001",
        periodo=PeriodService.get_active_period(),
        fecha_trabajo=PeriodService.get_fecha_trabajo(),
    )


# ---------------- Rutas de exportación heredadas (compatibilidad) ----------------
@reports_bp.route("/exportar/diario-csv")
@login_required
def export_journal_csv():
    return export_csv("diario")


@reports_bp.route("/exportar/balance-csv")
@login_required
def export_trial_balance_csv():
    return export_csv("balance")


@reports_bp.route("/exportar/inventario-csv")
@login_required
def export_inventory_csv():
    return export_csv("inventario")
