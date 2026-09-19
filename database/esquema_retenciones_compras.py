# -*- coding: utf-8 -*-
"""esquema_retenciones_compras.py — columnas de retenciones del módulo de compras.

En Ecuador, toda compra a un proveedor sujeto a retención genera un comprobante de retención:
se retiene Impuesto a la Renta sobre el valor del bien o servicio y se retiene IVA sobre el IVA
de la factura. Para contabilizar y mostrar ese desglose, la tabla `compras` necesita columnas
nuevas; este script las agrega con ALTER TABLE de forma IDEMPOTENTE (no se edita db_init.py).

Columnas agregadas a `compras`:
    tipo_compra                        concepto de la retención (BIENES, SERVICIOS_MANO_OBRA, ...)
    proveedor_contribuyente_especial   1 si el proveedor es contribuyente especial
    retencion_renta_codigo             código SRI aplicado (ej. RET-RENTA-02-BIE)
    retencion_renta_porcentaje         % retenido (leído del catálogo)
    retencion_renta_valor              valor retenido sobre el subtotal (bien o servicio)
    retencion_iva_codigo               código SRI aplicado (ej. RET-IVA-30-BIE)
    retencion_iva_porcentaje           % retenido (leído del catálogo)
    retencion_iva_valor                valor retenido sobre el IVA de la factura
    total_retenciones                  suma de las retenciones de Renta y de IVA
    neto_pagar                         total de la factura − retenciones (lo que se paga)

Uso:
    python database/esquema_retenciones_compras.py                    # base de control
    python database/esquema_retenciones_compras.py --todas-las-aulas
    python database/esquema_retenciones_compras.py --db ruta.db
    python database/esquema_retenciones_compras.py --listar
"""
import argparse
import glob
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config  # noqa: E402

# (columna, definición) — se agregan una sola vez
COLUMNAS = [
    ("tipo_compra", "TEXT"),
    ("proveedor_contribuyente_especial", "INTEGER DEFAULT 0"),
    ("retencion_renta_codigo", "TEXT"),
    ("retencion_renta_porcentaje", "REAL DEFAULT 0"),
    ("retencion_renta_valor", "REAL DEFAULT 0"),
    ("retencion_iva_codigo", "TEXT"),
    ("retencion_iva_porcentaje", "REAL DEFAULT 0"),
    ("retencion_iva_valor", "REAL DEFAULT 0"),
    ("total_retenciones", "REAL DEFAULT 0"),
    ("neto_pagar", "REAL DEFAULT 0"),
]

# Compras anteriores a esta mejora no tenían retenciones: se dejan como compras sin retención
# y se completa el neto con el total de la factura.
BACKFILL = [
    "UPDATE compras SET tipo_compra = 'SIN_RETENCION' WHERE tipo_compra IS NULL",
    "UPDATE compras SET proveedor_contribuyente_especial = 0 WHERE proveedor_contribuyente_especial IS NULL",
    "UPDATE compras SET retencion_renta_porcentaje = 0 WHERE retencion_renta_porcentaje IS NULL",
    "UPDATE compras SET retencion_renta_valor = 0 WHERE retencion_renta_valor IS NULL",
    "UPDATE compras SET retencion_iva_porcentaje = 0 WHERE retencion_iva_porcentaje IS NULL",
    "UPDATE compras SET retencion_iva_valor = 0 WHERE retencion_iva_valor IS NULL",
    "UPDATE compras SET total_retenciones = 0 WHERE total_retenciones IS NULL",
    "UPDATE compras SET neto_pagar = total WHERE neto_pagar IS NULL OR neto_pagar = 0",
]


def asegurar_columnas(conn):
    """Agrega las columnas de retenciones a `compras`. Devuelve cuántas columnas creó.

    Es idempotente y barato: sólo ejecuta ALTER TABLE para las columnas que falten, por lo que
    puede invocarse desde los servicios cada vez que se registra una compra (así las aulas y la
    plantilla se actualizan solas) o desde la línea de comandos.
    """
    existentes = [fila[1] for fila in conn.execute("PRAGMA table_info(compras)")]
    if not existentes:
        return 0

    nuevas = 0
    for columna, definicion in COLUMNAS:
        if columna not in existentes:
            conn.execute("ALTER TABLE compras ADD COLUMN %s %s" % (columna, definicion))
            nuevas += 1

    if nuevas:
        for sentencia in BACKFILL:
            conn.execute(sentencia)
        conn.commit()
    return nuevas


def _conectar(ruta):
    conn = sqlite3.connect(ruta, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def aplicar(ruta, verboso=True):
    conn = _conectar(ruta)
    try:
        nuevas = asegurar_columnas(conn)
        if verboso:
            print("  %s" % ruta)
            print("     columnas de retenciones nuevas: %d (total %d)" % (nuevas, len(COLUMNAS)))
        return nuevas
    finally:
        conn.close()


def aplicar_a_todas_las_aulas(verboso=True):
    aulas = sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db")))
    if not aulas:
        print("No hay aulas creadas.")
        return 0
    if verboso:
        print("Agregando columnas de retenciones a %d aulas..." % len(aulas))
    total = 0
    for aula in aulas:
        try:
            total += aplicar(aula, verboso=False)
        except sqlite3.Error as error:
            print("   aviso: %s -> %s" % (os.path.basename(aula), error))
    if verboso:
        print("Aulas actualizadas: %d (columnas nuevas: %d)" % (len(aulas), total))
    return total


def listar(ruta=None):
    conn = _conectar(ruta or Config.DATABASE_PATH)
    try:
        columnas = [fila[1] for fila in conn.execute("PRAGMA table_info(compras)")]
        print("Tabla compras -> %s" % (ruta or Config.DATABASE_PATH))
        for columna, definicion in COLUMNAS:
            print("  %-36s %-10s %s" % (columna, definicion, "OK" if columna in columnas else "FALTA"))
        fila = conn.execute("""SELECT COUNT(*) AS n,
                                      COALESCE(SUM(total_retenciones), 0) AS ret,
                                      COALESCE(SUM(neto_pagar), 0) AS neto FROM compras""").fetchone()
        print("Compras registradas: %d | retenciones acumuladas: $%.2f | neto pagado/pagable: $%.2f"
              % (fila["n"], fila["ret"], fila["neto"]))
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description="Columnas de retenciones del módulo de compras")
    p.add_argument("--db", default=None)
    p.add_argument("--todas-las-aulas", action="store_true")
    p.add_argument("--listar", action="store_true")
    args = p.parse_args()
    if args.listar:
        listar(args.db)
        return 0
    aplicar(args.db or Config.DATABASE_PATH)
    if args.todas_las_aulas:
        aplicar_a_todas_las_aulas()
    return 0


if __name__ == "__main__":
    sys.exit(main())
