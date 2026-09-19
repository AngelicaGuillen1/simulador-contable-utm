# -*- coding: utf-8 -*-
"""revisar_cuentas_retencion.py — comprueba a qué cuenta apuntan las retenciones en cada base.

Uso: .venv/Scripts/python.exe database/revisar_cuentas_retencion.py
"""
import glob
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config  # noqa: E402

CODIGOS_CLAVE = ("1.1.06", "1.1.07", "2.1.01", "2.1.03", "2.1.04", "2.1.05", "2.1.06")


def plan(ruta):
    conn = sqlite3.connect(ruta)
    try:
        return {r[0]: r[1] for r in conn.execute("SELECT codigo, nombre FROM cuentas")}
    finally:
        conn.close()


def main():
    rutas = [Config.DATABASE_PATH, Config.RUTA_PLANTILLA]
    rutas += sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db")))
    print("Base de datos: %d archivos\n" % len(rutas))
    for ruta in rutas[:3] + rutas[-1:]:
        d = plan(ruta)
        print(os.path.basename(ruta))
        for cod in CODIGOS_CLAVE:
            print("   %-7s %s" % (cod, d.get(cod, "(no existe)")))

    print("\n=== Destino de las filas de retención (primera aula) ===")
    aula = sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db")))[0]
    conn = sqlite3.connect(aula)
    conn.row_factory = sqlite3.Row
    try:
        for r in conn.execute("""SELECT i.codigo, i.porcentaje, i.cuenta_contable_id,
                                        c.codigo AS cc, c.nombre AS cn
                                 FROM impuestos i LEFT JOIN cuentas c ON c.id = i.cuenta_contable_id
                                 WHERE i.codigo LIKE 'RET-%' ORDER BY i.codigo"""):
            print("   %-22s %-6s -> id %-4s %s %s"
                  % (r["codigo"], r["porcentaje"], r["cuenta_contable_id"], r["cc"],
                     (r["cn"] or "")[:44]))
    finally:
        conn.close()

    print("\n=== Códigos 2.1.0x ocupados por aula ===")
    conteo = {}
    for ruta in rutas:
        d = plan(ruta)
        for cod in CODIGOS_CLAVE:
            if cod in d:
                conteo.setdefault(cod, set()).add(d[cod])
    for cod in CODIGOS_CLAVE:
        if cod in conteo:
            print("   %-7s %s" % (cod, " | ".join(sorted(conteo[cod]))))


if __name__ == "__main__":
    main()
