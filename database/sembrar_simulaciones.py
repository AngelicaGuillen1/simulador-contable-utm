#!/usr/bin/env python
"""
Siembra el SIMULADOR DE PRÁCTICA (niveles y casos) en el aula de cada estudiante.

Por qué existe este script
--------------------------
El módulo Simulador lee las simulaciones de la base CONTABLE de quien las usa; como cada
estudiante tiene su propia base (su aula), cada aula necesita su copia del catálogo de
niveles y casos. El catálogo vive en la base de demostración/control (la que crea
`database/seed_data.py`) y se copia desde ahí.

Es idempotente (INSERT OR REPLACE por id) y NO toca los intentos del estudiante: las
tablas `intentos_estudiante` y `detalle_intentos` se dejan intactas, así que el
estudiante sigue empezando de cero.

Uso:
    python database/sembrar_simulaciones.py                    # plantilla + todas las aulas
    python database/sembrar_simulaciones.py --solo-plantilla
    python database/sembrar_simulaciones.py --aula ealcivar4002 --paralelo B
    python database/sembrar_simulaciones.py --origen /var/datos/simulator.db
"""

import argparse
import glob
import os
import sqlite3
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from config import Config  # noqa: E402

TABLAS = ("simulaciones", "casos_simulacion")


def _conectar(ruta):
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    return conn


def _leer_catalogo(origen):
    """Lee el catálogo de simulaciones y casos de la base de origen."""
    conn = _conectar(origen)
    try:
        simulaciones = [dict(f) for f in conn.execute("SELECT * FROM simulaciones")]
        casos = [dict(f) for f in conn.execute("SELECT * FROM casos_simulacion")]
    finally:
        conn.close()
    return simulaciones, casos


def _existe(conn, tabla, valor):
    if valor is None:
        return False
    fila = conn.execute("SELECT 1 FROM %s WHERE id = ?" % tabla, (valor,)).fetchone()
    return bool(fila)


def sembrar(destino, simulaciones, casos, verboso=True):
    """Copia el catálogo al aula indicada. Devuelve (niveles, casos, intentos)."""
    conn = _conectar(destino)
    try:
        # Las claves foráneas de una aula son distintas de las de la base de control:
        # el aula solo tiene la fila del estudiante en `usuarios`. Si el docente o el
        # curso del catálogo no existen en el aula, se guardan como NULL (la simulación
        # es material del estudiante, no propiedad de un docente concreto).
        for tabla in TABLAS:
            conn.execute("DELETE FROM %s" % tabla)
        for fila in simulaciones:
            datos = dict(fila)
            if not _existe(conn, "usuarios", datos.get("docente_id")):
                datos["docente_id"] = None
            if not _existe(conn, "cursos", datos.get("curso_id")):
                datos["curso_id"] = None
            columnas = ", ".join(datos.keys())
            marcas = ", ".join(["?"] * len(datos))
            conn.execute("INSERT INTO simulaciones (%s) VALUES (%s)" % (columnas, marcas),
                         list(datos.values()))
        for fila in casos:
            datos = dict(fila)
            columnas = ", ".join(datos.keys())
            marcas = ", ".join(["?"] * len(datos))
            conn.execute("INSERT INTO casos_simulacion (%s) VALUES (%s)" % (columnas, marcas),
                         list(datos.values()))
        conn.commit()
        intentos = conn.execute("SELECT COUNT(*) FROM intentos_estudiante").fetchone()[0]
        niveles = conn.execute("SELECT COUNT(*) FROM simulaciones").fetchone()[0]
        total_casos = conn.execute("SELECT COUNT(*) FROM casos_simulacion").fetchone()[0]
        if verboso:
            print("   %-46s niveles: %d | casos: %d | intentos: %d"
                  % (os.path.relpath(destino, RAIZ), niveles, total_casos, intentos))
        return niveles, total_casos, intentos
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Siembra el simulador de práctica en las aulas")
    parser.add_argument("--origen", default=Config.DATABASE_PATH,
                        help="base que contiene el catálogo (por defecto la de control/demostración)")
    parser.add_argument("--solo-plantilla", action="store_true", help="sembrar solo la plantilla")
    parser.add_argument("--aula", help="sembrar una sola aula (usuario)")
    parser.add_argument("--paralelo", default="B", help="paralelo de esa aula")
    args = parser.parse_args()

    simulaciones, casos = _leer_catalogo(args.origen)
    if not simulaciones:
        raise SystemExit("La base de origen no tiene simulaciones: %s" % args.origen)
    print("Catálogo de origen: %d niveles, %d casos (%s)"
          % (len(simulaciones), len(casos), args.origen))

    if args.aula:
        from models import ruta_aula
        sembrar(ruta_aula(args.aula, args.paralelo), simulaciones, casos)
        return

    destinos = []
    if os.path.exists(Config.RUTA_PLANTILLA):
        destinos.append(Config.RUTA_PLANTILLA)
    if not args.solo_plantilla:
        destinos += sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db")))

    print("Sembrando en %d base(s)..." % len(destinos))
    for destino in destinos:
        try:
            sembrar(destino, simulaciones, casos, verboso=False)
        except sqlite3.Error as error:
            print("   AVISO: %s -> %s" % (destino, error))
    print("Listo: %d base(s) con el simulador de práctica disponible." % len(destinos))


if __name__ == "__main__":
    main()
