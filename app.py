"""
Simulador Integral de Sistema Contable
Servicios y Comercialización de Productos
--------------------------------------------------------------
Punto de entrada de la aplicación Flask.
Ejecución local:  python app.py   ->  http://127.0.0.1:5000
"""
import os
from datetime import datetime

from flask import Flask, render_template, g, redirect, url_for, request
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from models import get_db_connection
from routes import register_blueprints
from routes.home import home_bp
from routes.documents import documents_bp
from routes.taxes import taxes_bp
from services.period_service import PeriodService
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["JSON_AS_ASCII"] = False

    # Detrás del proxy inverso (Nginx en el VPS): confía en UNA capa de proxy para
    # conocer el esquema real (https) y la IP del estudiante. Sin esto, el registro de
    # accesos guardaría 127.0.0.1 y los enlaces saldrían con http:// en vez de https://.
    # x_for=1 (una sola cabecera X-Forwarded-For) evita que un cliente falsifique su IP.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    @app.context_processor
    def _version_estatica():
        """Marca de tiempo del CSS: evita que el navegador sirva una versión vieja."""
        try:
            ruta = os.path.join(app.static_folder, "css", "custom.css")
            return {"static_version": int(os.path.getmtime(ruta))}
        except OSError:
            return {"static_version": 0}

    # ---------------- Filtros de plantilla ----------------
    @app.template_filter("money")
    def money_filter(value):
        try:
            return "${:,.2f}".format(float(value or 0))
        except (TypeError, ValueError):
            return "$0.00"

    @app.template_filter("num")
    def num_filter(value, decimales=2):
        try:
            formato = "{:,.%df}" % int(decimales)
            return formato.format(float(value or 0))
        except (TypeError, ValueError):
            return "0"

    # §62.6 — las cifras de las fuentes se muestran en formato es-EC (1.234,56) sin alterar
    # ningún valor: `num_ec` y `money_ec` son las versiones normalizadas de `num` y `money`.
    @app.template_filter("num_ec")
    def num_ec_filter(value, decimales=2):
        from database.banco_casos_libros import formato_es_ec
        return formato_es_ec(value, decimales)

    @app.template_filter("money_ec")
    def money_ec_filter(value, decimales=2):
        from database.banco_casos_libros import formato_es_ec
        return "$%s" % formato_es_ec(value, decimales)

    @app.template_filter("fecha_legible")
    def fecha_legible(value):
        """Convierte 2026-04-30 en 30 de Abril de 2026."""
        if not value:
            return ""
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                 "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        try:
            d = datetime.strptime(str(value)[:10], "%Y-%m-%d")
            return f"{d.day} de {meses[d.month - 1].capitalize()} de {d.year}"
        except ValueError:
            return str(value)

    # ---------------- Contexto global ----------------
    @app.context_processor
    def inject_globals():
        try:
            periodo = PeriodService.get_active_period()
            fecha_trabajo = PeriodService.get_fecha_trabajo()
        except Exception:
            periodo = None
            fecha_trabajo = None

        alertas = {"stock_bajo": 0, "cxc_vencidas": 0, "cxp_proximas": 0, "periodo": None}
        try:
            # Los indicadores dependen de los libros de quien está en sesión: se leen del aula
            # del estudiante y, para los perfiles administrativos, de la base de control.
            from models import get_db_contable
            conn = get_db_contable()
            try:
                alertas["stock_bajo"] = len(InventoryService.get_low_stock_alerts())
                alertas["cxc_vencidas"] = conn.execute("""
                    SELECT COUNT(*) as cnt FROM cuentas_cobrar
                    WHERE estado IN ('PENDIENTE', 'PARCIAL') AND fecha_vencimiento < ?
                """, (fecha_trabajo,)).fetchone()["cnt"]
                alertas["cxp_proximas"] = conn.execute("""
                    SELECT COUNT(*) as cnt FROM cuentas_pagar
                    WHERE estado IN ('PENDIENTE', 'PARCIAL')
                """).fetchone()["cnt"]
                alertas["periodo"] = conn.execute("""
                    SELECT COUNT(*) as cnt FROM periodos WHERE estado = 'ABIERTO'
                """).fetchone()["cnt"]
            finally:
                conn.close()
        except Exception:
            pass

        # ¿Este usuario trabaja en SU propio espacio (su aula, con su propia empresa)?
        # Sirve para que la interfaz no le diga «datos de demostración» a un estudiante
        # real, y para avisar cuando alguien entra a la empresa compartida de práctica.
        aula_propia = False
        empresa_propia = None
        try:
            from flask import session as _sesion
            from models import ruta_aula as _ruta_aula
            if _sesion.get("user_role") == "Estudiante" and _sesion.get("paralelo"):
                ruta = _ruta_aula(_sesion.get("username"), _sesion.get("paralelo"))
                aula_propia = os.path.exists(ruta)
                if aula_propia:
                    import sqlite3 as _sqlite3
                    conexion = _sqlite3.connect(ruta)
                    try:
                        fila = conexion.execute(
                            "SELECT razon_social FROM empresas LIMIT 1").fetchone()
                        empresa_propia = fila[0] if fila else None
                    finally:
                        conexion.close()
        except Exception:
            aula_propia = False

        return {
            "app_name": Config.APP_NAME,
            "app_subtitle": Config.APP_SUBTITLE,
            "empresa_nombre": Config.COMPANY_NAME,
            "empresa_ruc": Config.COMPANY_RUC,
            "periodo_activo": periodo,
            "fecha_trabajo": fecha_trabajo,
            "alertas_globales": alertas,
            "aula_propia": aula_propia,
            "empresa_propia": empresa_propia,
        }

    # ---------------- Blueprints ----------------
    register_blueprints(app)
    app.register_blueprint(home_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(taxes_bp)

    # ---------------- Seguimiento de accesos (Panel Docente) ----------------
    # Anota en eventos_estudiante la acción correspondiente a cada endpoint visitado
    # por un estudiante. Nunca altera ni rompe la respuesta original.
    from services.access_service import registrar_evento_desde_request
    app.after_request(registrar_evento_desde_request)

    # ---------------- Manejo de errores ----------------
    @app.errorhandler(403)
    def error_403(e):
        mensaje = "Acceso no autorizado: tu rol no cuenta con permisos para este módulo."
        return render_template("403.html", mensaje=mensaje), 403

    @app.errorhandler(404)
    def error_404(e):
        mensaje = (f"La dirección solicitada '{request.path}' no existe en el Simulador Integral de "
                   f"Sistema Contable. Verifica el enlace o retorna al Dashboard General.")
        return render_template("404.html", mensaje=mensaje), 404

    @app.errorhandler(500)
    def error_500(e):
        mensaje = ("Error interno del servidor. La operación no pudo completarse y NO se registró ningún "
                   "movimiento contable. Revisa los logs de Flask para conocer el detalle técnico.")
        return render_template("500.html", mensaje=mensaje), 500

    return app


app = create_app()


if __name__ == "__main__":
    print("=" * 78)
    print(" SIMULADOR INTEGRAL DE SISTEMA CONTABLE")
    print(" Servicios y Comercialización de Productos - Comercial Nueva Esperanza")
    print("=" * 78)
    print(f" Modo desarrollo en: http://{Config.HOST}:{Config.PORT}")
    if Config.DEBUG:
        print(" Usuarios demo: admin/admin123 - docente/docente123 - estudiante/estudiante123")
    else:
        print(" Modo producción: el modo depuración está desactivado.")
        print(" Para servir 24/7 use el servidor de producción:  python serve.py")
    if Config.SECRET_KEY == Config.SECRET_KEY_POR_DEFECTO:
        print(" AVISO: SECRET_KEY por defecto. Defínala en el entorno antes de publicar el sitio.")
    print("=" * 78)
    print(" Manual de usuario: http://{}:{}/manual".format(Config.HOST, Config.PORT))
    print("=" * 78)
    app.run(host=Config.HOST, port=Config.PORT, debug=bool(Config.DEBUG))
