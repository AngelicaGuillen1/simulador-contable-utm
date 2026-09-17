#!/usr/bin/env python
"""
Respaldo del archivo SQLite del Simulador Contable.

Usa la API de respaldo en caliente de sqlite3, por lo que puede ejecutarse con el
servidor en marcha sin riesgo de copiar un archivo a medio escribir.

Uso:
    python deploy/backup_db.py                    # respalda en deploy/respaldos/
    python deploy/backup_db.py --destino D:/copias --conservar 20
    python deploy/backup_db.py --origen /datos/simulator.db

Programación sugerida (Windows, diario a las 22:00):
    schtasks /Create /SC DAILY /ST 22:00 /TN "RespaldoSimuladorContable" ^
             /TR "cmd /c cd /d \"C:\\ruta\\proyecto\" && .venv\\Scripts\\python.exe deploy\\backup_db.py"
Programación sugerida (Linux, cron):
    0 22 * * * cd /opt/simulador && .venv/bin/python deploy/backup_db.py >> logs/respaldo.log 2>&1
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from config import Config  # noqa: E402


def respaldar(origen, destino_dir, conservar, etiqueta="simulator"):
    if not os.path.exists(origen):
        raise SystemExit(f"No existe la base de datos: {origen}")

    os.makedirs(destino_dir, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(destino_dir, f"{etiqueta}_{marca}.db")

    conexion_origen = sqlite3.connect(origen)
    conexion_destino = sqlite3.connect(destino)
    try:
        with conexion_destino:
            conexion_origen.backup(conexion_destino)
    finally:
        conexion_destino.close()
        conexion_origen.close()

    tamano = os.path.getsize(destino)
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


def main():
    parser = argparse.ArgumentParser(description="Respaldo del archivo SQLite del simulador")
    parser.add_argument("--origen", default=Config.DATABASE_PATH, help="archivo SQLite a respaldar")
    parser.add_argument("--destino", default=os.path.join(RAIZ, "deploy", "respaldos"),
                        help="carpeta donde guardar los respaldos")
    parser.add_argument("--conservar", type=int, default=10, help="cuántos respaldos mantener")
    args = parser.parse_args()

    respaldar(args.origen, args.destino, args.conservar)


if __name__ == "__main__":
    main()
