#!/usr/bin/env python
"""
Deja en CERO el trabajo de los estudiantes, conservando el material del curso.

Sirve para arrancar un período limpio (o para corregir un aula donde quedaron
pruebas). Por cada aula borra las OPERACIONES y el rastro del estudiante:

    asientos, ventas, compras, servicios, caja, bancos, inventario/Kardex,
    cuentas por cobrar/pagar, cobros, pagos, documentos emitidos, intentos,
    evidencias, sesiones/eventos y la auditoría de esa aula.

CONSERVA (no lo toca): el plan de cuentas, el catálogo (productos, clientes,
proveedores), las actividades del sílabo, el simulador de práctica (niveles y
casos), el catálogo del SRI y los parámetros tributarios, la empresa del
estudiante, su fila de usuario y la ejecución de la plantilla.

Uso:
    python database/limpiar_aulas.py --ver                  # solo informa (no escribe nada)
    python database/limpiar_aulas.py --todas-las-aulas --si # limpiar todas las aulas
    python database/limpiar_aulas.py --aula ealcivar4002 --paralelo B --si
    python database/limpiar_aulas.py --control --si         # además, borrar el historial
                                                            # de accesos/evidencias del panel docente
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

# Tablas que se vacían en el aula (mismo criterio que al preparar la plantilla).
TABLAS_OPERACIONES = [
    "detalle_asientos", "asientos", "detalle_ventas", "ventas", "detalle_compras", "compras",
    "transacciones_servicios", "movimientos_inventario", "kardex_lotes", "cuentas_cobrar",
    "cobros", "cuentas_pagar", "pagos", "movimientos_caja", "arqueos_caja",
    "movimientos_bancarios", "conciliaciones_bancarias", "documentos_fuente",
    "intentos_estudiante", "detalle_intentos",
    "sesiones_usuario", "eventos_estudiante", "versiones_evidencia", "evidencias",
    "asignaciones_actividad", "matriculas", "auditoria",
]

# Tablas del PANEL DOCENTE que viven en la base de control.
TABLAS_CONTROL = ["eventos_estudiante", "sesiones_usuario", "versiones_evidencia", "evidencias"]


def _conectar(ruta):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    return conexion


def contar(ruta):
    """Resumen de lo que tiene el aula (para ver el antes y el después)."""
    conexion = _conectar(ruta)
    resumen = {}
    try:
        for tabla in ("asientos", "ventas", "compras", "documentos_fuente",
                      "intentos_estudiante", "evidencias", "cuentas", "productos",
                      "actividades", "simulaciones", "casos_simulacion"):
            try:
                resumen[tabla] = conexion.execute("SELECT COUNT(*) FROM %s" % tabla).fetchone()[0]
            except sqlite3.Error:
                resumen[tabla] = "n/d"
    finally:
        conexion.close()
    return resumen


def restaurar_catalogo(ruta, plantilla=None, confirmar=False):
    """Devuelve los productos del aula a los valores de la plantilla (stock y costo).

    Las operaciones no solo crean asientos: también mueven el stock y el costo promedio de
    los productos. Al limpiar un aula hay que devolver el catálogo a su punto de partida,
    o el aula quedaría «en cero» contablemente pero con mercadería de más.
    """
    plantilla = plantilla or Config.RUTA_PLANTILLA
    if not os.path.exists(plantilla) or os.path.abspath(plantilla) == os.path.abspath(ruta):
        return 0
    origen = _conectar(plantilla)
    try:
        base = {f["codigo"]: dict(f) for f in origen.execute(
            "SELECT codigo, stock_actual, costo_unitario, precio_venta FROM productos")}
    finally:
        origen.close()

    destino = _conectar(ruta)
    cambiados = 0
    try:
        for fila in destino.execute("SELECT id, codigo, stock_actual, costo_unitario, precio_venta FROM productos"):
            esperado = base.get(fila["codigo"])
            if not esperado:
                continue
            if (fila["stock_actual"] != esperado["stock_actual"]
                    or fila["costo_unitario"] != esperado["costo_unitario"]
                    or fila["precio_venta"] != esperado["precio_venta"]):
                cambiados += 1
                if confirmar:
                    destino.execute("UPDATE productos SET stock_actual = ?, costo_unitario = ?, "
                                    "precio_venta = ? WHERE id = ?",
                                    (esperado["stock_actual"], esperado["costo_unitario"],
                                     esperado["precio_venta"], fila["id"]))
        if confirmar:
            destino.commit()
    finally:
        destino.close()
    return cambiados


def limpiar(ruta, confirmar=False):
    """Vacía las operaciones del aula. Devuelve el resumen después de limpiar."""
    conexion = _conectar(ruta)
    try:
        if confirmar:
            conexion.execute("PRAGMA foreign_keys = OFF")
            for tabla in TABLAS_OPERACIONES:
                try:
                    conexion.execute("DELETE FROM %s" % tabla)
                except sqlite3.Error:
                    pass
            conexion.commit()
            conexion.execute("PRAGMA foreign_keys = ON")
    finally:
        conexion.close()
    return contar(ruta)


def limpiar_control(confirmar=False):
    conexion = _conectar(Config.DATABASE_PATH)
    try:
        if confirmar:
            for tabla in TABLAS_CONTROL:
                try:
                    conexion.execute("DELETE FROM %s" % tabla)
                except sqlite3.Error:
                    pass
            conexion.commit()
        valores = {}
        for tabla in TABLAS_CONTROL:
            try:
                valores[tabla] = conexion.execute("SELECT COUNT(*) FROM %s" % tabla).fetchone()[0]
            except sqlite3.Error:
                valores[tabla] = "n/d"
        return valores
    finally:
        conexion.close()


def aulas(una=None, paralelo=None):
    if una:
        from models import ruta_aula
        return [ruta_aula(una, paralelo or "B")]
    return sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db")))


def main():
    parser = argparse.ArgumentParser(description="Deja en cero el trabajo de los estudiantes")
    parser.add_argument("--todas-las-aulas", action="store_true", help="limpiar todas las aulas")
    parser.add_argument("--aula", help="limpiar una sola aula (usuario)")
    parser.add_argument("--paralelo", default="B", help="paralelo de esa aula")
    parser.add_argument("--control", action="store_true",
                        help="limpiar además el historial de accesos/evidencias del panel docente")
    parser.add_argument("--si", action="store_true", help="confirmar (sin esto solo informa)")
    parser.add_argument("--ver", action="store_true", help="solo informar lo que hay")
    args = parser.parse_args()

    if not args.todas_las_aulas and not args.aula and not args.ver:
        print("Indique --todas-las-aulas o --aula USUARIO.  (--ver para solo informar de todas)")
        return
    if args.ver:
        args.todas_las_aulas = True

    confirmar = args.si and not args.ver
    rutas = [r for r in aulas(args.aula, args.paralelo) if os.path.exists(r)]
    con_datos = []

    print("Aulas encontradas: %d" % len(rutas))
    catalogo_movido = []
    for ruta in rutas:
        antes = contar(ruta)
        if antes["asientos"] or antes["ventas"] or antes["compras"]:
            con_datos.append((os.path.basename(ruta), antes["asientos"], antes["ventas"],
                              antes["compras"]))
        movidos = restaurar_catalogo(ruta, confirmar=confirmar)
        if movidos:
            catalogo_movido.append((os.path.basename(ruta), movidos))
        if confirmar:
            limpiar(ruta, confirmar=True)

    if catalogo_movido:
        print("\nCatálogo devuelto a su punto de partida (stock/costo) en %d aulas:"
              % len(catalogo_movido))
        for nombre, n in catalogo_movido[:10]:
            print("   %-28s %s producto(s) restaurado(s)" % (nombre, n))

    if con_datos:
        print("\nAulas que TENÍAN movimientos: %d" % len(con_datos))
        for nombre, a, v, c in con_datos[:10]:
            print("   %-28s asientos: %-4s ventas: %-4s compras: %s" % (nombre, a, v, c))
        if len(con_datos) > 10:
            print("   ... y %d más" % (len(con_datos) - 10))
    else:
        print("\nNinguna aula tenía movimientos.")

    if confirmar:
        print("\nLimpiadas. Comprobación final (deben quedar en cero):")
        muestra = rutas[:3]
        for ruta in muestra:
            r = contar(ruta)
            print("   %-28s asientos: %s ventas: %s compras: %s | cuentas: %s actividades: %s simulador: %s/%s"
                  % (os.path.basename(ruta), r["asientos"], r["ventas"], r["compras"],
                     r["cuentas"], r["actividades"], r["simulaciones"], r["casos_simulacion"]))
    else:
        print("\n(Simulación: no se escribió nada. Añada --si para limpiar de verdad.)")

    if args.control:
        estado = limpiar_control(confirmar=confirmar)
        print("\nPanel docente (base de control): %s" % estado)


if __name__ == "__main__":
    main()
