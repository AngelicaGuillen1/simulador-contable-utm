# Partners & Receivables / Payables Routes
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from routes.auth import login_required
from services.sales_service import SalesService
from services.purchase_service import PurchaseService
from services.period_service import PeriodService
from models import get_db_contable

partners_bp = Blueprint("partners", __name__)

@partners_bp.route("/clientes", methods=["GET", "POST"])
@login_required
def customers():
    conn = get_db_contable()
    try:
        if request.method == "POST":
            ident = request.form.get("identificacion", "").strip()
            nombre = request.form.get("nombre_razon_social", "").strip()
            email = request.form.get("email", "").strip()
            tel = request.form.get("telefono", "").strip()
            dir_cl = request.form.get("direccion", "").strip()
            limite = float(request.form.get("limite_credito", 5000.0))
            dias = int(request.form.get("dias_credito", 30))

            try:
                conn.execute("""
                    INSERT INTO clientes (identificacion, nombre_razon_social, email, telefono, direccion, limite_credito, dias_credito, saldo_pendiente)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0.0)
                """, (ident, nombre, email, tel, dir_cl, limite, dias))
                conn.commit()
                flash(f"Cliente '{nombre}' registrado exitosamente.", "success")
            except Exception as e:
                flash(f"Error al registrar cliente: {str(e)}", "danger")
            return redirect(url_for("partners.customers"))

        clientes = conn.execute("SELECT * FROM clientes ORDER BY nombre_razon_social ASC").fetchall()
        return render_template("partners/customers.html", clientes=[dict(c) for c in clientes],
                               hoy=PeriodService.get_fecha_trabajo())
    finally:
        conn.close()

@partners_bp.route("/proveedores", methods=["GET", "POST"])
@login_required
def suppliers():
    conn = get_db_contable()
    try:
        if request.method == "POST":
            ident = request.form.get("identificacion", "").strip()
            razon = request.form.get("razon_social", "").strip()
            email = request.form.get("email", "").strip()
            tel = request.form.get("telefono", "").strip()
            dir_pr = request.form.get("direccion", "").strip()
            dias = int(request.form.get("dias_credito", 30))

            try:
                conn.execute("""
                    INSERT INTO proveedores (identificacion, razon_social, email, telefono, direccion, dias_credito, saldo_pendiente)
                    VALUES (?, ?, ?, ?, ?, ?, 0.0)
                """, (ident, razon, email, tel, dir_pr, dias))
                conn.commit()
                flash(f"Proveedor '{razon}' registrado exitosamente.", "success")
            except Exception as e:
                flash(f"Error al registrar proveedor: {str(e)}", "danger")
            return redirect(url_for("partners.suppliers"))

        proveedores = conn.execute("SELECT * FROM proveedores ORDER BY razon_social ASC").fetchall()
        return render_template("partners/suppliers.html", proveedores=[dict(p) for p in proveedores],
                               hoy=PeriodService.get_fecha_trabajo())
    finally:
        conn.close()

@partners_bp.route("/cuentas-cobrar", methods=["GET", "POST"])
@login_required
def receivables():
    conn = get_db_contable()
    try:
        if request.method == "POST":
            cxc_id = int(request.form.get("cuenta_cobrar_id"))
            monto = float(request.form.get("monto", 0.0))
            medio = request.form.get("medio_pago", "EFECTIVO")
            banco_id = request.form.get("banco_id")
            num_comp = request.form.get("numero_comprobante", "")

            try:
                cobro_id, nuevo_saldo, estado = SalesService.register_collection(
                    cxc_id, monto, medio_pago=medio,
                    banco_id=int(banco_id) if banco_id else 1,
                    numero_comprobante=num_comp, usuario_id=g.user["id"] if g.user else 1
                )
                flash(f"Cobro de ${monto:,.2f} registrado exitosamente. Nuevo saldo pendiente: ${nuevo_saldo:,.2f} ({estado}).", "success")
            except Exception as e:
                flash(f"Error al procesar cobro: {str(e)}", "danger")
            return redirect(url_for("partners.receivables"))

        cxc_list = conn.execute("""
            SELECT c.*, cl.nombre_razon_social as cliente_nombre, cl.identificacion as cliente_ruc
            FROM cuentas_cobrar c
            JOIN clientes cl ON c.cliente_id = cl.id
            ORDER BY c.fecha_vencimiento ASC
        """).fetchall()

        bancos = conn.execute("SELECT * FROM bancos WHERE activo = 1").fetchall()
        total_cartera = sum(c["saldo_actual"] for c in cxc_list if c["estado"] != "PAGADA")

        return render_template("partners/receivables.html", cxc_list=[dict(c) for c in cxc_list], bancos=bancos, total_cartera=round(total_cartera, 2), hoy=PeriodService.get_fecha_trabajo())
    finally:
        conn.close()

@partners_bp.route("/cuentas-pagar", methods=["GET", "POST"])
@login_required
def payables():
    conn = get_db_contable()
    try:
        if request.method == "POST":
            cxp_id = int(request.form.get("cuenta_pagar_id"))
            monto = float(request.form.get("monto", 0.0))
            medio = request.form.get("medio_pago", "TRANSFERENCIA")
            banco_id = request.form.get("banco_id")
            num_comp = request.form.get("numero_comprobante", "")

            try:
                pago_id, nuevo_saldo, estado = PurchaseService.register_payment(
                    cxp_id, monto, medio_pago=medio,
                    banco_id=int(banco_id) if banco_id else 1,
                    numero_comprobante=num_comp, usuario_id=g.user["id"] if g.user else 1
                )
                flash(f"Pago a proveedor de ${monto:,.2f} procesado. Saldo restante: ${nuevo_saldo:,.2f} ({estado}).", "success")
            except Exception as e:
                flash(f"Error al procesar pago: {str(e)}", "danger")
            return redirect(url_for("partners.payables"))

        cxp_list = conn.execute("""
            SELECT c.*, p.razon_social as proveedor_nombre, p.identificacion as proveedor_ruc
            FROM cuentas_pagar c
            JOIN proveedores p ON c.proveedor_id = p.id
            ORDER BY c.fecha_vencimiento ASC
        """).fetchall()

        bancos = conn.execute("SELECT * FROM bancos WHERE activo = 1").fetchall()
        total_cxp = sum(c["saldo_actual"] for c in cxp_list if c["estado"] != "PAGADA")

        return render_template("partners/payables.html", cxp_list=[dict(c) for c in cxp_list], bancos=bancos, total_cxp=round(total_cxp, 2), hoy=PeriodService.get_fecha_trabajo())
    finally:
        conn.close()
