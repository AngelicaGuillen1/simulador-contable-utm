# Authentication and Role-Based Access Control Blueprint
import functools
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import check_password_hash
from models import get_db_control
from services.audit_service import AuditService
from services.access_service import (
    abrir_sesion,
    cerrar_sesion,
    cerrar_sesiones_huerfanas,
    registrar_evento,
)

auth_bp = Blueprint("auth", __name__)

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_id") is None:
            flash("Por favor inicia sesión para acceder al sistema.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return view(**kwargs)
    return wrapped_view

def roles_required(*allowed_roles):
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if session.get("user_id") is None:
                return redirect(url_for("auth.login"))
            rol = session.get("user_role")
            if rol not in allowed_roles:
                flash(f"Acceso no autorizado. Tu rol ({rol}) no cuenta con permisos para este módulo.", "danger")
                return render_template("403.html", mensaje=f"Se requiere rol: {', '.join(allowed_roles)}"), 403
            return view(**kwargs)
        return wrapped_view
    return decorator

@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        conn = get_db_control()
        try:
            user = conn.execute("""
                SELECT u.*, r.nombre as rol_nombre
                FROM usuarios u
                JOIN roles r ON u.rol_id = r.id
                WHERE u.id = ? AND u.activo = 1
            """, (user_id,)).fetchone()
            g.user = dict(user) if user else None
        finally:
            conn.close()

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_control()
        try:
            user = conn.execute("""
                SELECT u.*, r.nombre as rol_nombre
                FROM usuarios u
                JOIN roles r ON u.rol_id = r.id
                WHERE (u.username = ? OR u.email = ?) AND u.activo = 1
            """, (username, username)).fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["user_fullname"] = user["nombre_completo"]
                session["user_role"] = user["rol_nombre"]
                session["empresa_id"] = 1
                # Aula propia del estudiante (base de datos aislada). Vacío para los
                # perfiles docente, administrador y auditor, que trabajan en la base de control.
                try:
                    session["paralelo"] = user["paralelo"]
                except (IndexError, KeyError):
                    session["paralelo"] = None

                # --- Seguimiento de accesos (Panel Docente) ----------------------
                # Se cierran las sesiones que quedaron colgadas de ingresos previos
                # y se abre la sesión de trabajo actual.
                try:
                    cerrar_sesiones_huerfanas(user["id"])
                    session["sesion_id"] = abrir_sesion(
                        user["id"],
                        request.remote_addr or "127.0.0.1",
                        request.headers.get("User-Agent"),
                    )
                    registrar_evento(
                        user["id"], "LOGIN", modulo="AUTH", registro_id=user["id"],
                        detalle="Inicio de sesión correcto",
                        empresa_id=session.get("empresa_id"),
                        sesion_id=session.get("sesion_id"),
                    )
                except Exception as e:  # el acceso nunca debe fallar por el seguimiento
                    print(f"Aviso: no se pudo registrar la sesión de acceso: {e}")

                AuditService.log(user["id"], user["username"], "LOGIN", "AUTH", user["id"], None, {"status": "SUCCESS"}, ip_origen=request.remote_addr or "127.0.0.1")
                flash(f"¡Bienvenido(a) al Simulador Contable, {user['nombre_completo']}!", "success")
                
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard.index"))
            else:
                flash("Credenciales incorrectas o usuario inactivo. Verifica tu usuario y contraseña.", "danger")
        finally:
            conn.close()

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    user_id = session.get("user_id")
    username = session.get("username", "anon")
    sesion_id = session.get("sesion_id")
    empresa_id = session.get("empresa_id")
    if user_id:
        # Cierre del seguimiento de accesos: primero se cierra la sesión de trabajo
        # (para que quede su duración) y después se registra el evento LOGOUT.
        try:
            if sesion_id:
                cerrar_sesion(sesion_id)
            registrar_evento(user_id, "LOGOUT", modulo="AUTH", registro_id=user_id,
                             detalle="Cierre de sesión", empresa_id=empresa_id,
                             sesion_id=sesion_id)
        except Exception as e:  # el logout nunca debe fallar por el seguimiento
            print(f"Aviso: no se pudo cerrar la sesión de acceso: {e}")

        AuditService.log(user_id, username, "LOGOUT", "AUTH", user_id, None, {"status": "LOGOUT"}, ip_origen=request.remote_addr or "127.0.0.1")
    session.clear()
    flash("Has cerrado sesión exitosamente.", "info")
    return redirect(url_for("auth.login"))
