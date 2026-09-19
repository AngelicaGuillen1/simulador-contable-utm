# -*- coding: utf-8 -*-
"""La empresa del aula es la EMPRESA PROPIA del estudiante.

Cada estudiante trabaja en su propio archivo SQLite (su aula) y la empresa de ese
archivo es «su» empresa. Si `empresas.estudiante_id` queda en NULL, las actividades,
las evidencias y el panel docente caen a la empresa compartida por defecto
(`services/activity_service._empresa_de_estudiante`), y la empresa del estudiante no
aparece como suya en el seguimiento de accesos (`services/access_service.py`).

Cubre:
  1. Al crear el aula con `estudiante_id`, su empresa queda marcada como del estudiante.
  2. La plantilla (el molde) conserva `estudiante_id` en NULL.
  3. `_empresa_de_estudiante` devuelve la empresa del aula, sin usar el respaldo.
  4. Un aula creada sin `estudiante_id` no marca empresa (se mantiene el respaldo).
"""
import os
import sqlite3

import pytest

from config import Config
from models import get_db_connection


# --------------------------------------------------------------------------- utilidades
def _crear_estudiante(db, username, paralelo="B", nombre="Estudiante de Prueba"):
    conn = get_db_connection(db)
    try:
        cursor = conn.execute("""
            INSERT INTO usuarios (username, password_hash, nombre_completo, email, rol_id,
                                  activo, paralelo, matricula)
            VALUES (?, 'no-usado-en-pruebas', ?, ?, 3, 1, ?, '1700000009')
        """, (username, nombre, "%s@estudiantes.edu.ec" % username, paralelo))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _empresa_de(ruta):
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    try:
        return dict(conn.execute("SELECT id, estudiante_id, es_demo FROM empresas").fetchone())
    finally:
        conn.close()


# --------------------------------------------------------------------------- fixtures
@pytest.fixture()
def entorno_aulas(tmp_path, monkeypatch):
    """Aísla las aulas y la plantilla en tmp_path (no toca los archivos del repositorio)."""
    monkeypatch.setattr(Config, "RUTA_AULAS", str(tmp_path / "aulas"))
    monkeypatch.setattr(Config, "RUTA_PLANTILLA", str(tmp_path / "plantilla" / "aula_base.db"))
    return tmp_path


@pytest.fixture()
def aula_de_estudiante(db, entorno_aulas):
    from database.crear_aula import crear_aula

    estudiante_id = _crear_estudiante(db, "estudiante_marca")
    ruta = crear_aula("estudiante_marca", "B", plan="completo", estudiante_id=estudiante_id,
                      verboso=False)
    return {"id": estudiante_id, "ruta": ruta}


# --------------------------------------------------------------------------- pruebas
def test_la_empresa_del_aula_es_la_del_estudiante(aula_de_estudiante):
    empresa = _empresa_de(aula_de_estudiante["ruta"])
    assert empresa["estudiante_id"] == aula_de_estudiante["id"], \
        "La empresa del aula debe quedar marcada como del estudiante que la usa"
    assert empresa["es_demo"] == 0, "La empresa propia del estudiante no es demostrativa"


def test_la_plantilla_no_tiene_dueno(aula_de_estudiante, entorno_aulas):
    empresa = _empresa_de(Config.RUTA_PLANTILLA)
    assert empresa["estudiante_id"] is None, \
        "La plantilla es el molde de las aulas: no puede pertenecer a ningún estudiante"


def test_el_servicio_resuelve_la_empresa_del_aula_sin_usar_el_respaldo(aula_de_estudiante):
    """Si la empresa del aula está marcada, no se cae a la empresa compartida."""
    from services.activity_service import _empresa_de_estudiante

    conn = sqlite3.connect(aula_de_estudiante["ruta"])
    conn.row_factory = sqlite3.Row
    try:
        resuelta = _empresa_de_estudiante(conn, aula_de_estudiante["id"])
        esperada = conn.execute("SELECT id FROM empresas WHERE estudiante_id = ?",
                                (aula_de_estudiante["id"],)).fetchone()["id"]
        assert resuelta == esperada
        assert resuelta == _empresa_de(aula_de_estudiante["ruta"])["id"]

        # Y sin marca, el servicio sigue funcionando con el respaldo (no rompe).
        conn.execute("UPDATE empresas SET estudiante_id = NULL")
        conn.commit()
        assert _empresa_de_estudiante(conn, aula_de_estudiante["id"]) is not None
    finally:
        conn.close()


def test_aula_sin_estudiante_no_marca_empresa(db, entorno_aulas):
    """La creación manual (sin estudiante_id) no inventa dueño para la empresa."""
    from database.crear_aula import crear_aula

    ruta = crear_aula("aula_sin_dueno", "B", plan="completo", verboso=False)
    assert os.path.exists(ruta)
    assert _empresa_de(ruta)["estudiante_id"] is None
