"""
Configuración común de las pruebas automáticas del
Simulador Integral de Sistema Contable.

Estrategia: se genera UNA base de datos demostrativa completa (con las 30 operaciones reales
del período Abril 2026) y cada prueba trabaja sobre una COPIA independiente, de modo que las
pruebas no se afectan entre sí y pueden registrar operaciones sin contaminar el resto.
"""
import os
import shutil
import sqlite3
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from config import Config                     # noqa: E402
from database.seed_data import seed_all       # noqa: E402


@pytest.fixture(scope="session")
def plantilla_demo(tmp_path_factory):
    """Base de datos demostrativa completa generada una sola vez por sesión."""
    ruta = str(tmp_path_factory.mktemp("plantilla") / "simulator_demo.db")
    seed_all(db_path=ruta, reset=True, verbose=False)

    # Consolidar el archivo WAL dentro del archivo principal antes de copiarlo
    conn = sqlite3.connect(ruta)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
    finally:
        conn.close()
    return ruta


@pytest.fixture()
def db(plantilla_demo, tmp_path, monkeypatch):
    """Copia limpia de la base demostrativa para cada prueba (ruta devuelta)."""
    origen = plantilla_demo
    destino = str(tmp_path / "simulator.db")
    shutil.copyfile(origen, destino)

    if os.path.exists(origen + "-wal"):
        shutil.copyfile(origen + "-wal", destino + "-wal")

    monkeypatch.setattr(Config, "DATABASE_PATH", destino)
    return destino


@pytest.fixture()
def app_client(db):
    """Cliente de pruebas de Flask con autenticación disponible."""
    import app as app_module

    aplicacion = app_module.create_app()
    aplicacion.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return aplicacion.test_client()


@pytest.fixture()
def admin_client(app_client):
    """Cliente autenticado como Administrador."""
    respuesta = app_client.post("/login", data={"username": "admin", "password": "admin123"},
                                follow_redirects=True)
    assert respuesta.status_code == 200
    return app_client


@pytest.fixture()
def estudiante_client(app_client):
    """Cliente autenticado como Estudiante."""
    respuesta = app_client.post("/login", data={"username": "estudiante", "password": "estudiante123"},
                                follow_redirects=True)
    assert respuesta.status_code == 200
    return app_client
