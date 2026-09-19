# -*- coding: utf-8 -*-
"""esquema_retenciones_ventas.py — retenciones que el CLIENTE le practica al VENDEDOR.

En Ecuador, cuando el cliente es agente de retención (contribuyente especial) le practica al
vendedor una retención de Impuesto a la Renta —sobre el valor de la venta— y una retención de IVA
—sobre el IVA de la factura—, y le paga el NETO. Para guardar y contabilizar ese desglose, las
tablas `ventas` y `transacciones_servicios` necesitan columnas nuevas; este script las agrega con
ALTER TABLE de forma IDEMPOTENTE (no se edita db_init.py).

También completa —sólo cuando están vacíos— los `impuestos.cuenta_venta_id` de las retenciones que
el catálogo del SRI todavía no tuviera configurados. La cuenta del lado venta (la 1.1.xx
«...por Cobrar») se resuelve del PLAN DE CUENTAS por el NOMBRE de la cuenta; los códigos de cuenta
no se escriben en el programa, y la cuenta se crea sólo si el plan no la tuviera.

Columnas agregadas a `ventas` y a `transacciones_servicios`:
    tipo_venta                    concepto de la retención (BIENES, SERVICIOS_MANO_OBRA, ...)
    cliente_agente_retencion      1 si el cliente es agente de retención
    retencion_renta_codigo        código SRI de la retención de Renta que aplica el cliente
    retencion_renta_porcentaje    % retenido (leído del catálogo)
    retencion_renta_valor         valor retenido sobre el valor de la venta (subtotal − descuento)
    retencion_iva_codigo          código SRI de la retención de IVA
    retencion_iva_porcentaje      % retenido (leído del catálogo)
    retencion_iva_valor           valor retenido sobre el IVA de la factura
    total_retenciones             suma de las retenciones de Renta y de IVA
    neto_cobrar                   total de la factura − retenciones (lo que paga el cliente)

Uso:
    python database/esquema_retenciones_ventas.py                      # base de control
    python database/esquema_retenciones_ventas.py --todas-las-aulas
    python database/esquema_retenciones_ventas.py --db ruta.db
    python database/esquema_retenciones_ventas.py --listar
"""
import argparse
import glob
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config  # noqa: E402

# (columna, definición) — se agregan una sola vez, a cada tabla de ventas
COLUMNAS = [
    ("tipo_venta", "TEXT"),
    ("cliente_agente_retencion", "INTEGER DEFAULT 0"),
    ("retencion_renta_codigo", "TEXT"),
    ("retencion_renta_porcentaje", "REAL DEFAULT 0"),
    ("retencion_renta_valor", "REAL DEFAULT 0"),
    ("retencion_iva_codigo", "TEXT"),
    ("retencion_iva_porcentaje", "REAL DEFAULT 0"),
    ("retencion_iva_valor", "REAL DEFAULT 0"),
    ("total_retenciones", "REAL DEFAULT 0"),
    ("neto_cobrar", "REAL DEFAULT 0"),
]

# Tablas que registran ventas: la de bienes y la de servicios.
TABLAS = ("ventas", "transacciones_servicios")

# Ventas anteriores a esta mejora no tuvieron retenciones: se dejan sin retención y se completa
# el neto por cobrar con el total de la factura.
BACKFILL = (
    "UPDATE {tabla} SET tipo_venta = 'SIN_RETENCION' WHERE tipo_venta IS NULL",
    "UPDATE {tabla} SET cliente_agente_retencion = 0 WHERE cliente_agente_retencion IS NULL",
    "UPDATE {tabla} SET retencion_renta_porcentaje = 0 WHERE retencion_renta_porcentaje IS NULL",
    "UPDATE {tabla} SET retencion_renta_valor = 0 WHERE retencion_renta_valor IS NULL",
    "UPDATE {tabla} SET retencion_iva_porcentaje = 0 WHERE retencion_iva_porcentaje IS NULL",
    "UPDATE {tabla} SET retencion_iva_valor = 0 WHERE retencion_iva_valor IS NULL",
    "UPDATE {tabla} SET total_retenciones = 0 WHERE total_retenciones IS NULL",
    "UPDATE {tabla} SET neto_cobrar = total WHERE neto_cobrar IS NULL OR neto_cobrar = 0",
)

# Cuentas del lado VENTA: son DEUDORAS (lo retenido es un anticipo de Renta y un crédito
# tributario de IVA a favor del vendedor). Se ubican por las palabras de su nombre, nunca por un
# código escrito aquí: el plan de cuentas pedagógico puede tener ocupados los códigos previstos.
CUENTAS_VENTA = (
    ("RET_RENTA", ("retencion", "renta", "cobrar"),
     "Retención en la Fuente de Renta por Cobrar (Anticipo IR)"),
    ("RET_IVA", ("retencion", "iva", "cobrar"),
     "Retención en la Fuente de IVA por Cobrar (Crédito Tributario)"),
)


def _columnas(conn, tabla):
    return [r[1] for r in conn.execute("PRAGMA table_info(%s)" % tabla)]


def _normalizar(texto):
    """Minúsculas y sin acentos, para comparar nombres de cuentas."""
    limpio = (texto or "").lower()
    for con_acento, sin_acento in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        limpio = limpio.replace(con_acento, sin_acento)
    return limpio


def _asegurar_cuenta(conn, palabras, nombre_nuevo):
    """Id de la cuenta del plan que coincide con las palabras; si no existe, se crea 1.1.xx."""
    for fila in conn.execute("SELECT id, nombre FROM cuentas ORDER BY id"):
        if all(p in _normalizar(fila["nombre"]) for p in palabras):
            return fila["id"]

    columnas = _columnas(conn, "cuentas")
    ocupados = {r[0] for r in conn.execute("SELECT codigo FROM cuentas")}
    codigo = None
    for sufijo in range(8, 40):
        candidato = "1.1.%02d" % sufijo
        if candidato not in ocupados:
            codigo = candidato
            break
    if codigo is None:
        return None

    datos = {"codigo": codigo, "nombre": nombre_nuevo, "naturaleza": "DEUDORA",
             "clasificacion": "ACTIVO_CORRIENTE", "acepta_movimiento": 1}
    if "activo" in columnas:
        datos["activo"] = 1
    if "nivel" in columnas:
        datos["nivel"] = 2
    if "cuenta_padre_id" in columnas:
        padre = conn.execute("SELECT id FROM cuentas WHERE codigo = '1.1'").fetchone()
        datos["cuenta_padre_id"] = padre["id"] if padre else None
    campos = [c for c in datos if c in columnas]
    conn.execute("INSERT INTO cuentas (%s) VALUES (%s)" % (",".join(campos),
                ",".join("?" for _ in campos)), [datos[c] for c in campos])
    return conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (codigo,)).fetchone()["id"]


def asegurar_columnas(conn):
    """Agrega las columnas de retenciones a las tablas de ventas. Devuelve cuántas creó.

    Es idempotente y barato: sólo ejecuta ALTER TABLE para las columnas que falten, por lo que
    puede invocarse desde el servicio cada vez que se registra una venta (así las aulas y la
    plantilla se actualizan solas) o desde la línea de comandos.
    """
    nuevas = 0
    for tabla in TABLAS:
        existentes = _columnas(conn, tabla)
        if not existentes:
            continue
        creadas_aqui = 0
        for columna, definicion in COLUMNAS:
            if columna not in existentes:
                conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (tabla, columna, definicion))
                creadas_aqui += 1
        if creadas_aqui:
            for sentencia in BACKFILL:
                conn.execute(sentencia.format(tabla=tabla))
        nuevas += creadas_aqui
    if nuevas:
        conn.commit()
    return nuevas


def asegurar_cuentas_venta(conn):
    """Completa `impuestos.cuenta_venta_id` de las retenciones que aún no la tuvieran.

    Sólo escribe donde está vacío y resuelve la cuenta por su nombre en el plan de cuentas, de
    modo que el porcentaje y la cuenta siguen siendo DATOS del catálogo, no constantes del
    programa. Devuelve cuántas filas del catálogo quedaron enlazadas.
    """
    columnas = _columnas(conn, "impuestos")
    if "cuenta_venta_id" not in columnas:
        return 0

    completadas = 0
    for prefijo, palabras, nombre in CUENTAS_VENTA:
        cuenta_id = _asegurar_cuenta(conn, palabras, nombre)
        if not cuenta_id:
            continue
        cursor = conn.execute(
            "UPDATE impuestos SET cuenta_venta_id = ? "
            "WHERE tipo LIKE ? AND (cuenta_venta_id IS NULL OR cuenta_venta_id = 0)",
            (cuenta_id, prefijo + "%"))
        completadas += cursor.rowcount or 0
    # Se confirma SIEMPRE: aunque no haya filas nuevas, el UPDATE abrió una transacción de
    # escritura y SQLite no la libera hasta el commit (dejaría bloqueada la base para el resto
    # de la venta, que trabaja con otras conexiones).
    conn.commit()
    return completadas


def asegurar_retenciones_ventas(conn):
    """Deja la base lista para registrar retenciones sufridas por el vendedor.

    Devuelve (columnas_nuevas, cuentas_del_catalogo_enlazadas).
    """
    nuevas = asegurar_columnas(conn)
    cuentas = asegurar_cuentas_venta(conn)
    return nuevas, cuentas


def _conectar(ruta):
    conn = sqlite3.connect(ruta, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def aplicar(ruta, verboso=True):
    conn = _conectar(ruta)
    try:
        nuevas, cuentas = asegurar_retenciones_ventas(conn)
        if verboso:
            print("  %s" % ruta)
            print("     columnas de retenciones de ventas nuevas: %d (total %d por tabla)"
                  % (nuevas, len(COLUMNAS)))
            print("     cuentas del lado venta enlazadas en el catálogo: %d" % cuentas)
        return nuevas, cuentas
    finally:
        conn.close()


def aplicar_a_todas_las_aulas(verboso=True):
    aulas = sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db")))
    aulas += sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*.db")))
    if not aulas:
        print("No hay aulas creadas.")
        return 0
    if verboso:
        print("Agregando columnas de retenciones de ventas a %d aulas..." % len(aulas))
    total = 0
    for aula in aulas:
        try:
            total += aplicar(aula, verboso=False)[0]
        except sqlite3.Error as error:
            print("   aviso: %s -> %s" % (os.path.basename(aula), error))
    if verboso:
        print("Aulas actualizadas: %d (columnas nuevas: %d)" % (len(aulas), total))
    return total


def listar(ruta=None):
    conn = _conectar(ruta or Config.DATABASE_PATH)
    try:
        print("Retenciones del lado venta -> %s" % (ruta or Config.DATABASE_PATH))
        for tabla in TABLAS:
            columnas = _columnas(conn, tabla)
            print("  Tabla %s" % tabla)
            for columna, definicion in COLUMNAS:
                print("    %-32s %-10s %s" % (columna, definicion,
                                              "OK" if columna in columnas else "FALTA"))
            if columnas:
                fila = conn.execute(
                    "SELECT COUNT(*) AS n, COALESCE(SUM(total_retenciones), 0) AS ret, "
                    "COALESCE(SUM(neto_cobrar), 0) AS neto FROM %s" % tabla).fetchone()
                print("    Registros: %d | retenciones sufridas: $%.2f | neto por cobrar: $%.2f"
                      % (fila["n"], fila["ret"], fila["neto"]))
        print("  Catálogo (impuestos.cuenta_venta_id):")
        if "cuenta_venta_id" in _columnas(conn, "impuestos"):
            consulta = """SELECT i.codigo, i.porcentaje, i.tipo, c.codigo AS cuenta
                          FROM impuestos i LEFT JOIN cuentas c ON c.id = i.cuenta_venta_id
                          WHERE i.tipo LIKE 'RET%' ORDER BY i.codigo"""
            for fila in conn.execute(consulta):
                print("    %-24s %6.2f %%  %-22s" % (fila["codigo"], fila["porcentaje"],
                                                     fila["cuenta"] or "(sin cuenta del lado venta)"))
        else:
            print("    El catálogo no tiene la columna cuenta_venta_id: ejecute "
                  "database/parametros_tributarios_sri.py")
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description="Retenciones sufridas por el vendedor (lado venta)")
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
