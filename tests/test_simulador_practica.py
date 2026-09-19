# -*- coding: utf-8 -*-
"""El aula nueva trae el simulador de PRÁCTICA y ninguna operación del estudiante.

El módulo Simulador lee las simulaciones de la base contable de quien las usa, así que
cada aula necesita su copia del catálogo de niveles y casos. Ese catálogo es material
didáctico y NO debe vaciarse al preparar el aula (si se vacía, el módulo le queda vacío
al estudiante); lo que sí debe quedar en cero son las operaciones y los intentos.

Cubre:
  1. La plantilla conserva los niveles y casos, y no conserva operaciones.
  2. El aula nueva del estudiante trae el catálogo de práctica completo.
  3. El aula nueva no trae asientos, ventas, compras ni intentos (empieza de cero).
  4. Sembrar el catálogo otra vez no borra el trabajo del estudiante (idempotente).
"""
import sqlite3

import pytest

from config import Config
from models import get_db_connection


# --------------------------------------------------------------------------- utilidades
def _crear_estudiante(db, username, paralelo="B"):
    conn = get_db_connection(db)
    try:
        cursor = conn.execute("""
            INSERT INTO usuarios (username, password_hash, nombre_completo, email, rol_id,
                                  activo, paralelo, matricula)
            VALUES (?, 'no-usado-en-pruebas', 'Estudiante de Práctica', ?, 3, 1, ?, '1700000008')
        """, (username, "%s@estudiantes.edu.ec" % username, paralelo))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _contar(ruta, tabla, condicion=None):
    conn = sqlite3.connect(ruta)
    try:
        sql = "SELECT COUNT(*) FROM %s" % tabla
        if condicion:
            sql += " WHERE " + condicion
        return conn.execute(sql).fetchone()[0]
    finally:
        conn.close()


def _escribir(ruta, sql, params=()):
    conn = sqlite3.connect(ruta)
    try:
        with conn:
            conn.execute(sql, params)
    finally:
        conn.close()


def _escalar(ruta, sql, params=()):
    conn = sqlite3.connect(ruta)
    try:
        fila = conn.execute(sql, params).fetchone()
        return fila[0] if fila else None
    finally:
        conn.close()


# --------------------------------------------------------------------------- fixtures
@pytest.fixture()
def entorno_aulas(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "RUTA_AULAS", str(tmp_path / "aulas"))
    monkeypatch.setattr(Config, "RUTA_PLANTILLA", str(tmp_path / "plantilla" / "aula_base.db"))
    return tmp_path


@pytest.fixture()
def aula_nueva(db, entorno_aulas):
    from database.crear_aula import crear_aula

    estudiante_id = _crear_estudiante(db, "estudiante_practica")
    ruta = crear_aula("estudiante_practica", "B", plan="completo", estudiante_id=estudiante_id,
                      verboso=False)
    return {"id": estudiante_id, "ruta": ruta, "plantilla": Config.RUTA_PLANTILLA}


# --------------------------------------------------------------------------- pruebas
def test_la_plantilla_conserva_el_simulador_y_vacia_las_operaciones(aula_nueva):
    plantilla = aula_nueva["plantilla"]
    assert _contar(plantilla, "simulaciones") == 4, \
        "La plantilla debe conservar los 4 niveles del simulador de práctica"
    assert _contar(plantilla, "casos_simulacion") == 19, \
        "La plantilla debe conservar los 19 casos de práctica"
    assert _contar(plantilla, "asientos") == 0, "La plantilla no lleva operaciones"
    assert _contar(plantilla, "intentos_estudiante") == 0, "La plantilla no lleva intentos"


def test_el_aula_nueva_trae_el_simulador_de_practica(aula_nueva):
    ruta = aula_nueva["ruta"]
    assert _contar(ruta, "simulaciones") == 4
    assert _contar(ruta, "casos_simulacion") == 19


def test_el_aula_nueva_empieza_de_cero(aula_nueva):
    ruta = aula_nueva["ruta"]
    for tabla in ("asientos", "detalle_asientos", "ventas", "compras",
                  "intentos_estudiante", "detalle_intentos"):
        assert _contar(ruta, tabla) == 0, "El aula debe empezar sin %s" % tabla
    assert _contar(ruta, "cuentas") > 40, "El aula sí trae el plan de cuentas"


def test_sembrar_otra_vez_no_borra_el_trabajo_del_estudiante(aula_nueva):
    """Resembrar el catálogo de práctica no debe tocar nada del estudiante."""
    from database.sembrar_simulaciones import _leer_catalogo, sembrar

    ruta = aula_nueva["ruta"]
    antes = {
        "cuentas": _contar(ruta, "cuentas"),
        "actividades": _contar(ruta, "actividades"),
        "empresa_del_estudiante": _escalar(ruta, "SELECT estudiante_id FROM empresas LIMIT 1"),
    }
    assert antes["empresa_del_estudiante"] == aula_nueva["id"], \
        "El aula nace marcada como la empresa del estudiante"

    simulaciones, casos = _leer_catalogo(Config.DATABASE_PATH)
    sembrar(ruta, simulaciones, casos, verboso=False)

    assert _contar(ruta, "cuentas") == antes["cuentas"], "El plan de cuentas no se toca"
    assert _contar(ruta, "actividades") == antes["actividades"], "Las actividades no se tocan"
    assert _escalar(ruta, "SELECT estudiante_id FROM empresas LIMIT 1") == antes["empresa_del_estudiante"], \
        "La empresa propia del estudiante no se toca"
    assert _contar(ruta, "simulaciones") == 4
    assert _contar(ruta, "casos_simulacion") == 19
    assert _contar(ruta, "intentos_estudiante") == 0, "El estudiante sigue sin intentos"
