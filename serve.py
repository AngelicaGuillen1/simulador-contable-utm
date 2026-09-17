"""
Servidor de producción del Simulador Integral de Sistema Contable.

Usa waitress (servidor WSGI puro Python, funciona en Windows y Linux) en lugar del
servidor de desarrollo de Flask. Arranca la base de datos de demostración si no existe,
de modo que un despliegue nuevo queda operativo sin pasos manuales.

Uso:
    python serve.py                    # usa HOST/PORT del entorno (127.0.0.1:5000 por defecto)
    HOST=0.0.0.0 PORT=8080 python serve.py
    THREADS=12 python serve.py
"""

import os
import sys

from waitress import serve

from config import Config


def _asegurar_base_de_datos():
    """Crea la base demostrativa si no existe (primer arranque en un hosting nuevo)."""
    ruta = Config.DATABASE_PATH
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        return
    Directorio = os.path.dirname(ruta)
    if Directorio:
        os.makedirs(Directorio, exist_ok=True)
    print(f" Base de datos no encontrada en {ruta}")
    print(" Generando datos de demostración (puede tardar un minuto)...")
    from database.seed_data import seed_all

    seed_all(db_path=ruta, reset=True, verbose=False)


def main():
    _asegurar_base_de_datos()

    aplicacion = None
    from wsgi import application as aplicacion  # noqa: F811  (import tardío: tras sembrar la BD)

    host = Config.HOST
    puerto = Config.PORT
    hilos = int(os.environ.get("THREADS", "8"))

    print("=" * 78)
    print(" SIMULADOR INTEGRAL DE SISTEMA CONTABLE")
    print(" Servicios y Comercialización de Productos - Comercial Nueva Esperanza")
    print("=" * 78)
    print(f" Servidor de producción (waitress) escuchando en http://{host}:{puerto}")
    print(f" Base de datos: {Config.DATABASE_PATH}")
    print(f" Hilos: {hilos} | Modo depuración: {'ACTIVADO' if Config.DEBUG else 'desactivado'}")

    if Config.SECRET_KEY == Config.SECRET_KEY_POR_DEFECTO:
        print("-" * 78)
        print(" AVISO DE SEGURIDAD: se está usando la SECRET_KEY por defecto.")
        print(" Antes de exponer el sistema en Internet defina la variable de entorno")
        print(" SECRET_KEY con una cadena aleatoria larga (ver docs/DESPLIEGUE.md).")
    print("=" * 78)
    sys.stdout.flush()

    serve(
        aplicacion,
        host=host,
        port=puerto,
        threads=hilos,
        ident="Simulador Contable UTM (waitress)",
        clear_untrusted_proxy_headers=False,
    )


if __name__ == "__main__":
    main()
