"""El alta de un estudiante nuevo: nombres de usuario, claves y borrado seguro.

Solo se prueban las funciones que no escriben nada: el alta completa se verificó a mano creando y
eliminando una estudiante temporal (cuenta, aula propia, 46 cuentas, 6 actividades y 19 casos).
"""
import os
import re
import sqlite3
import tempfile

import pytest

from config import Config
from database.alta_estudiante import (generar_clave, nombre_presentable, usuario_desde_correo,
                                      usuario_desde_nombre)


def test_usuario_desde_correo_y_nombre():
    assert usuario_desde_correo("aperez5678@utm.edu.ec") == "aperez5678"
    # Mismo patrón de la nómina: inicial del nombre + primer apellido + 4 dígitos de la cédula.
    # Las listas vienen como «APELLIDO APELLIDO NOMBRE NOMBRE», igual que ecarreno3182.
    assert usuario_desde_nombre("Perez Lopez Ana Maria", "1312345678") == "aperez5678"
    assert usuario_desde_nombre("MUÑOZ ZAMBRANO JOSÉ LUIS", "0912345678") == "jmunoz5678"
    assert usuario_desde_nombre("CARRENO BRAVO ERICK ALEXANDER", "1314293182") == "ecarreno3182"


def test_clave_con_el_formato_de_la_lista():
    for _ in range(20):
        clave = generar_clave()
        assert re.fullmatch(r"[A-Z0-9]{4}-[A-Z0-9]{4}", clave), clave
        assert not set(clave.replace("-", "")) & set("O0I1"), "confunde O/0 o I/1: %s" % clave


def test_nombre_presentable():
    assert nombre_presentable("Perez Lopez Ana Maria") == "Ana Maria Perez Lopez"
    assert nombre_presentable("Ana Perez") == "Ana Perez"


def test_borrar_no_falla_con_usuario_inexistente():
    """Dar de baja a alguien que no existe no debe romper nada."""
    from database.alta_estudiante import borrar

    original = Config.DATABASE_PATH
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = os.path.join(carpeta, "control.db")
        conexion = sqlite3.connect(ruta)
        conexion.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, username TEXT)")
        conexion.commit()
        conexion.close()
        Config.DATABASE_PATH = ruta
        try:
            assert borrar("nadie0000") == 0
            conexion = sqlite3.connect(ruta)
            assert conexion.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0
            conexion.close()
        finally:
            Config.DATABASE_PATH = original
