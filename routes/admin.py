# Administration Blueprint: Users, Taxes, Settings & Immutable Audit Log
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash
from routes.auth import login_required, roles_required
from services.audit_service import AuditService
from services.tax_service import TaxService
from services.period_service import PeriodService
from models import get_db_connection

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/", methods=["GET", "POST"])
@login_required
@roles_required("Administrador")
def index():
    conn = get_db_connection()
    try:
        if request.method == "POST":
            try:
                fecha_trabajo = (request.form.get("fecha_trabajo") or "").strip()
                if fecha_trabajo:
                    PeriodService.set_fecha_trabajo(fecha_trabajo)
                    AuditService.log(g.user["id"] if g.user else 1, g.user["username"] if g.user else "admin",
                                     "CAMBIAR_FECHA_TRABAJO", "ADMIN", "parametros", None,
                                     {"fecha_trabajo": fecha_trabajo})

                razon_social = (request.form.get("razon_social") or "").strip()
                nombre_comercial = (request.form.get("nombre_comercial") or "").strip()
                ruc = (request.form.get("ruc") or "").strip()
                direccion = (request.form.get("direccion") or "").strip()
                telefono = (request.form.get("telefono") or "").strip()
                email = (request.form.get("email") or "").strip()
                actividad_comercial = (request.form.get("actividad_comercial") or "").strip()
                actividad_servicios = (request.form.get("actividad_servicios") or "").strip()
                metodo = (request.form.get("metodo_kardex_defecto") or "PROMEDIO").strip().upper()
                if metodo not in ("PROMEDIO", "FIFO"):
                    raise ValueError("El método de valoración debe ser PROMEDIO o FIFO.")

                if razon_social and ruc:
                    conn.execute("""
                        UPDATE empresas SET razon_social = ?, nombre_comercial = ?, ruc = ?, direccion = ?,
                               telefono = ?, email = ?, actividad_comercial = ?, actividad_servicios = ?,
                               metodo_kardex_defecto = ?
                        WHERE id = 1
                    """, (razon_social, nombre_comercial or razon_social, ruc, direccion, telefono, email,
                          actividad_comercial, actividad_servicios, metodo))
                    conn.commit()
                flash("Parámetros del sistema y datos de la empresa simulada actualizados correctamente.", "success")
            except Exception as e:
                flash(f"No se pudieron actualizar los parámetros: {str(e)}", "danger")
            return redirect(url_for("admin.index"))

        total_users = conn.execute("SELECT COUNT(*) as cnt FROM usuarios").fetchone()["cnt"]
        total_audit = conn.execute("SELECT COUNT(*) as cnt FROM auditoria").fetchone()["cnt"]
        total_empresas = conn.execute("SELECT COUNT(*) as cnt FROM empresas").fetchone()["cnt"]

        empresa = conn.execute("SELECT * FROM empresas WHERE id = 1").fetchone()
        recent_audit = AuditService.get_logs(limit=10)
        periodos = PeriodService.get_periods()
        parametros = PeriodService.get_parameters()

        return render_template(
            "admin/settings.html",
            total_users=total_users,
            total_audit=total_audit,
            total_empresas=total_empresas,
            empresa=dict(empresa) if empresa else {},
            recent_audit=recent_audit,
            periodos=periodos,
            parametros=parametros,
            fecha_trabajo=PeriodService.get_fecha_trabajo()
        )
    finally:
        conn.close()

@admin_bp.route("/usuarios", methods=["GET", "POST"])
@login_required
@roles_required("Administrador")
def users():
    conn = get_db_connection()
    try:
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            nombre = request.form.get("nombre_completo", "").strip()
            email = request.form.get("email", "").strip()
            rol_id = int(request.form.get("rol_id", 3))

            if not username or not password:
                flash("El usuario y la contraseña son obligatorios.", "warning")
            else:
                try:
                    hash_pw = generate_password_hash(password)
                    conn.execute("""
                        INSERT INTO usuarios (username, password_hash, nombre_completo, email, rol_id, activo)
                        VALUES (?, ?, ?, ?, ?, 1)
                    """, (username, hash_pw, nombre, email, rol_id))
                    conn.commit()
                    AuditService.log(g.user["id"] if g.user else 1, g.user["username"] if g.user else "admin", "CREAR_USUARIO", "ADMIN", username, None, {"username": username, "rol_id": rol_id})
                    flash(f"Usuario '{username}' creado exitosamente con contraseña segura.", "success")
                except Exception as e:
                    flash(f"Error al crear usuario: {str(e)}", "danger")
            return redirect(url_for("admin.users"))

        users_list = conn.execute("""
            SELECT u.*, r.nombre as rol_nombre
            FROM usuarios u
            JOIN roles r ON u.rol_id = r.id
            ORDER BY u.id ASC
        """).fetchall()
        roles = conn.execute("SELECT * FROM roles ORDER BY id ASC").fetchall()

        return render_template("admin/users.html", usuarios=[dict(u) for u in users_list], roles=[dict(r) for r in roles])
    finally:
        conn.close()

@admin_bp.route("/impuestos", methods=["GET", "POST"])
@login_required
@roles_required("Administrador")
def taxes():
    if request.method == "POST":
        impuesto_id = int(request.form.get("impuesto_id"))
        nombre = request.form.get("nombre", "").strip()
        porcentaje = float(request.form.get("porcentaje", 0.0))
        tipo = request.form.get("tipo", "IVA_VENTAS")
        cuenta_id = int(request.form.get("cuenta_contable_id", 21))
        activo = int(request.form.get("activo", 1))

        try:
            TaxService.update_tax(impuesto_id, nombre, porcentaje, tipo, cuenta_id, activo=activo)
            flash("Parámetro tributario actualizado correctamente.", "success")
        except Exception as e:
            flash(f"Error al actualizar impuesto: {str(e)}", "danger")
        return redirect(url_for("admin.taxes"))

    taxes_list = TaxService.get_taxes()
    conn = get_db_connection()
    try:
        cuentas = conn.execute("SELECT id, codigo, nombre FROM cuentas WHERE acepta_movimiento = 1 ORDER BY codigo ASC").fetchall()
        return render_template("admin/taxes.html", impuestos=taxes_list, cuentas=[dict(c) for c in cuentas])
    finally:
        conn.close()

@admin_bp.route("/auditoria")
@login_required
@roles_required("Administrador", "Auditor")
def audit():
    modulo = request.args.get("modulo")
    logs = AuditService.get_logs(modulo=modulo, limit=200)
    return render_template("admin/audit.html", logs=logs, selected_modulo=modulo)
