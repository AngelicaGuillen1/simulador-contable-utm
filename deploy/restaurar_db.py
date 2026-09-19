#!/usr/bin/env python
"""
Restauración de las bases de datos del Simulador Contable.

Trabaja con los respaldos que genera deploy/backup_db.py:

    · Respaldo COMPLETO (carpeta con marca de tiempo):
        deploy/respaldos/20260919_2200/
            simulator.db
            plantilla/aula_base.db
            aulas/B/ealcivar4002.db
            aulas/B/javiles8757.db  ...

    · Respaldo simple (un solo archivo .db de la base de control):
        deploy/respaldos/simulator_20260919_2200.db

Uso:
    python deploy/restaurar_db.py --listar                      # ver respaldos disponibles
    python deploy/restaurar_db.py --desde <carpeta o archivo>   # simula (no escribe nada)
    python deploy/restaurar_db.py --desde <carpeta> --si        # restaura de verdad

Seguridad: antes de sobrescribir NADA, el script copia el estado actual a
deploy/respaldos/antes_de_restaurar_<marca>/ para poder deshacer. Nunca borra
las aulas que no estén en el respaldo.
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

RESPALDOS = os.path.join(RAIZ, "deploy", "respaldos")


def _marca():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _copiar_sqlite(origen, destino):
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


def listar(destino_dir=RESPALDOS):
    """Muestra los respaldos disponibles: carpetas completas y archivos sueltos."""
    if not os.path.isdir(destino_dir):
        print(f"No hay respaldos en {destino_dir}")
        return
    carpetas = sorted((d for d in os.listdir(destino_dir)
                       if os.path.isdir(os.path.join(destino_dir, d)) and d[:8].isdigit()), reverse=True)
    archivos = sorted((a for a in os.listdir(destino_dir)
                       if a.endswith(".db") and not os.path.isdir(os.path.join(destino_dir, a))), reverse=True)

    print(f"Respaldos en {destino_dir}")
    if carpetas:
        print("\n  COMPLETOS (control + plantilla + aulas)")
        for d in carpetas:
            ruta = os.path.join(destino_dir, d)
            n_aulas = len(glob.glob(os.path.join(ruta, "aulas", "*", "*.db")))
            mb = sum(os.path.getsize(os.path.join(dp, f))
                     for dp, _, fs in os.walk(ruta) for f in fs) / 1024.0 / 1024.0
            print(f"    {d}   aulas: {n_aulas:>3}   {mb:6.2f} MB   {ruta}")
    if archivos:
        print("\n  SIMPLES (solo base de control)")
        for a in archivos:
            ruta = os.path.join(destino_dir, a)
            print(f"    {a}   {os.path.getsize(ruta) / 1024.0:.0f} KB   {ruta}")
    if not carpetas and not archivos:
        print("  (vacío)")


def _plan_desde_carpeta(origen):
    """(origen, destino) de cada base que se restauraría desde un respaldo completo."""
    plan = []
    control = os.path.join(origen, "simulator.db")
    if os.path.exists(control):
        plan.append((control, Config.DATABASE_PATH))
    plantilla = os.path.join(origen, "plantilla", "aula_base.db")
    if os.path.exists(plantilla):
        plan.append((plantilla, Config.RUTA_PLANTILLA))
    for ruta in sorted(glob.glob(os.path.join(origen, "aulas", "*", "*.db"))):
        relativa = os.path.relpath(ruta, os.path.join(origen, "aulas"))
        plan.append((ruta, os.path.join(Config.RUTA_AULAS, relativa)))
    return plan


def _plan_desde_archivo(origen):
    """Un archivo .db suelto se interpreta como la base de control."""
    return [(origen, Config.DATABASE_PATH)]


def _resumen(ruta):
    """Datos útiles de un archivo SQLite para saber qué se está restaurando."""
    try:
        conexion = sqlite3.connect(ruta)
        try:
            tablas = conexion.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            info = f"{tablas} tablas"
            for tabla in ("usuarios", "asientos", "ventas", "compras", "documentos_fuente"):
                try:
                    n = conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
                    info += f", {tabla}: {n}"
                except sqlite3.Error:
                    pass
            return info
        finally:
            conexion.close()
    except sqlite3.Error as error:
        return f"(no se pudo leer: {error})"


def restaurar(origen, confirmar=False, destino_dir=RESPALDOS):
    if not os.path.exists(origen):
        raise SystemExit(f"No existe el respaldo: {origen}")

    plan = _plan_desde_carpeta(origen) if os.path.isdir(origen) else _plan_desde_archivo(origen)
    if not plan:
        raise SystemExit(f"El respaldo {origen} no contiene bases que se puedan restaurar.")

    print(f"Restauración desde: {origen}")
    print(f"  bases a restaurar: {len(plan)}")
    for ruta_origen, ruta_destino in plan[:6]:
        existe = "sobrescribe" if os.path.exists(ruta_destino) else "crea"
        print(f"    [{existe}] {ruta_destino}")
    if len(plan) > 6:
        print(f"    ... y {len(plan) - 6} más")

    if not confirmar:
        print("\n SIMULACIÓN: no se escribió nada. Añada --si para restaurar de verdad.")
        return False

    # Copia de seguridad del estado actual ANTES de sobrescribir
    respaldo_previo = os.path.join(destino_dir, f"antes_de_restaurar_{_marca()}")
    respaldadas = 0
    for _, ruta_destino in plan:
        if os.path.exists(ruta_destino):
            relativa = os.path.relpath(ruta_destino, RAIZ).replace("..", "externo")
            _copiar_sqlite(ruta_destino, os.path.join(respaldo_previo, relativa.lstrip("/\\")))
            respaldadas += 1
    if respaldadas:
        print(f"\n Estado actual guardado en: {respaldo_previo} ({respaldadas} bases)")

    for ruta_origen, ruta_destino in plan:
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        shutil.copy2(ruta_origen, ruta_destino)

    print(f"\n Restauración terminada: {len(plan)} bases.")
    print(" Detalles de la base de control restaurada:")
    print(f"   {_resumen(Config.DATABASE_PATH)}")
    print("\n Reinicie el servicio para que tome los datos restaurados:")
    print("   Windows:  detener y volver a ejecutar deploy/windows/iniciar_servidor.cmd")
    print("   Linux:    sudo systemctl restart simulador-contable")
    return True


def main():
    parser = argparse.ArgumentParser(description="Restauración de las bases del simulador")
    parser.add_argument("--listar", action="store_true", help="mostrar los respaldos disponibles")
    parser.add_argument("--desde", help="carpeta de respaldo completo, o archivo .db de la base de control")
    parser.add_argument("--destino", default=RESPALDOS, help="carpeta de respaldos")
    parser.add_argument("--si", action="store_true", help="confirmar la restauración (sin esto solo simula)")
    args = parser.parse_args()

    if args.listar or not args.desde:
        listar(args.destino)
        if not args.desde:
            print("\nIndique qué restaurar con  --desde <carpeta o archivo>  (añada --si para confirmar).")
        return

    restaurar(args.desde, confirmar=args.si, destino_dir=args.destino)


if __name__ == "__main__":
    main()
