# -*- coding: utf-8 -*-
"""Carga el banco de casos prácticos de los libros (§61) y las reglas de trazabilidad (§62).

Aplica el esquema y siembra los datos en la base de CONTROL. Es idempotente.

Uso:
    .venv/Scripts/python.exe database/cargar_casos_libros.py                  # base configurada
    .venv/Scripts/python.exe database/cargar_casos_libros.py --db ruta.db
    .venv/Scripts/python.exe database/cargar_casos_libros.py --listar         # solo informa
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config                                              # noqa: E402
from database.esquema_casos_libros import aplicar, sembrar             # noqa: E402
from services.casos_libros_service import (                            # noqa: E402
    erratas_catalogo, fuentes, listar_casos, reglas, resumen_banco, tasas_demostrativas,
)


def informar(db_path, verboso=True):
    """Muestra el estado del banco cargado."""
    resumen = resumen_banco(db_path)
    print("-" * 78)
    print(" BANCO DE CASOS PRÁCTICOS DE LOS LIBROS (§61) — base: %s" % db_path)
    print("-" * 78)
    print(" Casos cargados            : %d" % resumen["total"])
    print(" Activos para estudiantes  : %d" % resumen["activos"])
    print(" Sin solución en la fuente : %d (práctica sin solución visible, §62.5)"
          % resumen["sin_solucion_en_fuente"])
    print(" Con erratas corregidas    : %d (§62.1)" % resumen["con_correccion_de_erratas"])
    print(" Con dato reconstruido     : %d (§62.4)" % resumen["con_dato_reconstruido"])
    print(" Por estado de validación  : %s" % ", ".join(
        "%s=%d" % (k, v) for k, v in sorted(resumen["por_estado"].items())))
    print("-" * 78)
    if not verboso:
        return resumen
    print(" Fuentes (§62.7 — doble numeración de páginas):")
    for fuente in fuentes(db_path):
        print("   · %-4s %s → %s" % (fuente["codigo"], fuente["nombre"][:52],
                                     fuente["correlacion_paginas"]))
    print(" Reglas §62 cargadas       : %d (%d de trazabilidad de fuentes)"
          % (len(reglas(db_path=db_path)), len(reglas(solo_trazabilidad=True, db_path=db_path))))
    print(" Erratas §59.10 registradas: %d" % len(erratas_catalogo(db_path)))
    print(" Tarifas demostrativas     : %d (§62.2, editables desde el panel docente)"
          % len(tasas_demostrativas(db_path)))
    print("-" * 78)
    for caso in listar_casos(db_path=db_path):
        print(" %s %-2s U%s %-22s %s" % (caso["codigo"], caso["estado_validacion"][:4],
                                         caso["unidad"], caso["tipo"][:22],
                                         caso["nombre"][:46]))
    print("-" * 78)
    return resumen


def main():
    parser = argparse.ArgumentParser(description="Carga el banco de casos §61 del simulador.")
    parser.add_argument("--db", dest="db", default=None, help="Ruta de la base de control.")
    parser.add_argument("--listar", action="store_true", help="Solo informa del estado del banco.")
    argumentos = parser.parse_args()
    db_path = argumentos.db or Config.DATABASE_PATH

    if not argumentos.listar:
        aplicar(db_path, verboso=True)
        resultado = sembrar(db_path, verboso=True)
        print(" Sembrado: %(casos)d casos, %(reglas)d reglas §62, %(fuentes)d fuentes." % resultado)

    informar(db_path, verboso=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
