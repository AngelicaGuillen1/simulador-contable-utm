#!/usr/bin/env python
"""
Respaldo de las bases de datos del Simulador Contable.

El sistema usa VARIAS bases SQLite:
    · 1 base de CONTROL      -> usuarios, actividades, evidencias, sesiones, eventos
    · 1 plantilla de aula    -> database/plantilla/aula_base.db (molde de las aulas)
    · N aulas de estudiantes -> database/aulas/<paralelo>/<usuario>.db

Usa la API de respaldo en caliente de sqlite3, por lo que puede ejecutarse con el
servidor en marcha sin riesgo de copiar un archivo a medio escribir.

Uso:
    python deploy/backup_db.py --todas                 # respaldo COMPLETO (control + plantilla + aulas)
    python deploy/backup_db.py --todas --destino D:/copias --conservar 20
    python deploy/backup_db.py                         # solo la base de control
    python deploy/backup_db.py --origen /datos/simulator.db

Programación sugerida (Windows, diario a las 22:00):
    schtasks /Create /SC DAILY /ST 22:00 /TN "RespaldoSimuladorContable" ^
             /TR "cmd /c cd /d \"C:\\ruta\\proyecto\" && .venv\\Scripts\\python.exe deploy\\backup_db.py --todas"
Programación sugerida (Linux, cron):
    0 22 * * * cd /opt/simulador && .venv/bin/python deploy/backup_db.py --todas >> logs/respaldo.log 2>&1

Restauración:  python deploy/restaurar_db.py --listar
               python deploy/restaurar_db.py --desde deploy/respaldos/AAAAmmdd_HHMMSS --si
"""

import argparse
import glob
import os
import shutil
import sqlite3
import sys
from datetime import datetime

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from config import Config  # noqa: E402


def _copiar_sqlite(origen, destino):
    """Copia en caliente un archivo SQLite (seguro con el servidor en marcha)."""
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    conexion_origen = sqlite3.connect(origen)
    conexion_destino = sqlite3.connect(destino)
    try:
        with conexion_destino:
            conexion_origen.backup(conexion_destino)
    finally:
        conexion_destino.close()
        conexion_origen.close()
    return os.path.getsize(destino)


def respaldar(origen, destino_dir, conservar, etiqueta="simulator"):
    """Respalda UN archivo SQLite, conservando las N copias más recientes."""
    if not os.path.exists(origen):
        raise SystemExit(f"No existe la base de datos: {origen}")

    os.makedirs(destino_dir, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(destino_dir, f"{etiqueta}_{marca}.db")

    tamano = _copiar_sqlite(origen, destino)
    print(f"Respaldo creado: {destino} ({tamano:,} bytes)")

    # Rotación: conservar solo los N más recientes
    archivos = sorted(
        (os.path.join(destino_dir, a) for a in os.listdir(destino_dir) if a.startswith(etiqueta + "_")),
        key=os.path.getmtime,
        reverse=True,
    )
    for viejo in archivos[conservar:]:
        os.remove(viejo)
        print(f"Respaldo antiguo eliminado: {viejo}")

    return destino


def aulas_existentes():
    """(ruta, ruta_relativa dentro del respaldo) de cada aula que exista hoy."""
    patron = os.path.join(Config.RUTA_AULAS, "*", "*.db")
    for ruta in sorted(glob.glob(patron)):
        relativa = os.path.relpath(ruta, Config.RUTA_AULAS)
        yield ruta, os.path.join("aulas", relativa)


def respaldar_completo(destino_dir, conservar, con_plantilla=True, con_aulas=True):
    """Respaldo COMPLETO en una carpeta con marca de tiempo (control + plantilla + aulas)."""
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta = os.path.join(destino_dir, marca)
    os.makedirs(carpeta, exist_ok=True)

    total = 0
    pesado = 0

    if os.path.exists(Config.DATABASE_PATH):
        pesado += _copiar_sqlite(Config.DATABASE_PATH, os.path.join(carpeta, "simulator.db"))
        total += 1
        print(f"  control    : {os.path.basename(Config.DATABASE_PATH)}")
    else:
        print(f"  AVISO: no existe la base de control en {Config.DATABASE_PATH}")

    if con_plantilla and os.path.exists(Config.RUTA_PLANTILLA):
        pesado += _copiar_sqlite(Config.RUTA_PLANTILLA, os.path.join(carpeta, "plantilla", "aula_base.db"))
        total += 1
        print("  plantilla  : aula_base.db")

    if con_aulas:
        n = 0
        for ruta, relativa in aulas_existentes():
            pesado += _copiar_sqlite(ruta, os.path.join(carpeta, relativa))
            n += 1
        total += n
        print(f"  aulas      : {n} archivos")

    print(f"Respaldo COMPLETO: {carpeta}")
    print(f"  bases: {total} | tamaño: {pesado / 1024.0 / 1024.0:.2f} MB")

    # Rotación de carpetas completas (solo las que llevan fecha AAAAmmdd)
    carpetas = sorted(
        (os.path.join(destino_dir, d) for d in os.listdir(destino_dir)
         if os.path.isdir(os.path.join(destino_dir, d)) and d[:8].isdigit()),
        key=os.path.getmtime, reverse=True,
    )
    for vieja in carpetas[conservar:]:
        shutil.rmtree(vieja, ignore_errors=True)
        print(f"Respaldo completo antiguo eliminado: {vieja}")

    return carpeta


def main():
    parser = argparse.ArgumentParser(description="Respaldo de las bases SQLite del simulador")
    parser.add_argument("--origen", default=Config.DATABASE_PATH, help="archivo SQLite a respaldar")
    parser.add_argument("--destino", default=os.path.join(RAIZ, "deploy", "respaldos"),
                        help="carpeta donde guardar los respaldos")
    parser.add_argument("--conservar", type=int, default=10, help="cuántos respaldos mantener")
    parser.add_argument("--todas", action="store_true",
                        help="respaldo COMPLETO: base de control + plantilla + todas las aulas")
    parser.add_argument("--sin-plantilla", action="store_true", help="con --todas: omitir la plantilla")
    parser.add_argument("--sin-aulas", action="store_true", help="con --todas: omitir las aulas")
    args = parser.parse_args()

    if args.todas:
        respaldar_completo(args.destino, args.conservar,
                           con_plantilla=not args.sin_plantilla,
                           con_aulas=not args.sin_aulas)
    else:
        respaldar(args.origen, args.destino, args.conservar)


if __name__ == "__main__":
    main()
