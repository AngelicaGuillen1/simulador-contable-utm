"""Devuelve el catálogo de productos de las aulas a su punto de partida (el seed).

Las operaciones no solo crean asientos: mueven el stock y el costo promedio de los
productos. Si un aula se usó para pruebas (o el docente vendió/compró durante una
demostración), el catálogo queda con cifras que no son las iniciales y el estudiante
arranca con mercadería que no corresponde.

Uso:
    python database/normalizar_catalogo.py                 # solo informa (no escribe)
    python database/normalizar_catalogo.py --aplicar       # corrige plantilla + aulas
    python database/normalizar_catalogo.py --aplicar --aula ealcivar4002

La referencia se genera ejecutando database/seed_data.py en una carpeta temporal, así
que siempre es el catálogo inicial real del sistema (no una copia ya alterada).
"""
import argparse
import glob
import os
import sqlite3
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402


def catalogo_inicial():
    """Genera un seed limpio en una carpeta temporal y devuelve sus productos."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp = tempfile.mkdtemp(prefix="catalogo_")
    referencia = os.path.join(tmp, "simulator.db")
    entorno = dict(os.environ, DATABASE_PATH=referencia)
    proceso = subprocess.run([sys.executable, os.path.join(raiz, "database", "seed_data.py")],
                             env=entorno, capture_output=True, text=True)
    if not os.path.exists(referencia):
        raise SystemExit("No se pudo generar el catálogo de referencia:\n%s"
                         % ((proceso.stdout or "") + (proceso.stderr or ""))[-600:])
    conexion = sqlite3.connect(referencia)
    conexion.row_factory = sqlite3.Row
    try:
        return {f["codigo"]: {"stock_actual": f["stock_actual"],
                              "costo_unitario": f["costo_unitario"],
                              "precio_venta": f["precio_venta"]}
                for f in conexion.execute(
                    "SELECT codigo, stock_actual, costo_unitario, precio_venta FROM productos")}
    finally:
        conexion.close()


def valor_catalogo(ruta):
    conexion = sqlite3.connect(ruta)
    try:
        return round(conexion.execute(
            "SELECT COALESCE(SUM(stock_actual * costo_unitario), 0) FROM productos WHERE activo = 1"
        ).fetchone()[0] or 0, 2)
    finally:
        conexion.close()


def normalizar(ruta, canonico, aplicar=False):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    cambiados = 0
    try:
        filas = list(conexion.execute(
            "SELECT id, codigo, stock_actual, costo_unitario, precio_venta FROM productos"))
        for fila in filas:
            esperado = canonico.get(fila["codigo"])
            if not esperado:
                continue
            if (fila["stock_actual"] != esperado["stock_actual"]
                    or fila["costo_unitario"] != esperado["costo_unitario"]
                    or fila["precio_venta"] != esperado["precio_venta"]):
                cambiados += 1
                if aplicar:
                    conexion.execute(
                        "UPDATE productos SET stock_actual = ?, costo_unitario = ?, precio_venta = ? "
                        "WHERE id = ?",
                        (esperado["stock_actual"], esperado["costo_unitario"],
                         esperado["precio_venta"], fila["id"]))
        if aplicar and cambiados:
            conexion.commit()
    finally:
        conexion.close()
    return cambiados


def main():
    analizador = argparse.ArgumentParser(description="Normaliza el catálogo de productos de las aulas.")
    analizador.add_argument("--aplicar", action="store_true", help="escribe los cambios (sin esto solo informa)")
    analizador.add_argument("--aula", help="solo esta aula (usuario del estudiante)")
    argumentos = analizador.parse_args()

    canonico = catalogo_inicial()
    referencia = round(sum(p["stock_actual"] * p["costo_unitario"] for p in canonico.values()), 2)
    print("Catálogo inicial del sistema: %d productos | valor al costo $%s" % (len(canonico), referencia))
    print("Modo: %s\n" % ("APLICAR (escribe)" if argumentos.aplicar else "solo informe"))

    if argumentos.aula:
        destinos = [os.path.join(Config.RUTA_AULAS, "B", "%s.db" % argumentos.aula),
                    os.path.join(Config.RUTA_AULAS, "A", "%s.db" % argumentos.aula)]
        destinos = [d for d in destinos if os.path.exists(d)]
    else:
        destinos = [Config.RUTA_PLANTILLA] + sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db")))

    print("%-32s %12s %12s" % ("BASE", "VALOR ACTUAL", "PRODUCTOS"))
    print("-" * 60)
    total_cambios = 0
    for ruta in destinos:
        if not os.path.exists(ruta):
            continue
        cambios = normalizar(ruta, canonico, aplicar=argumentos.aplicar)
        total_cambios += cambios
        etiqueta = os.path.basename(ruta) if ruta != Config.RUTA_PLANTILLA else "PLANTILLA"
        print("%-32s %12s %12s" % (etiqueta, valor_catalogo(ruta), cambios or "igual"))

    print("-" * 60)
    if argumentos.aplicar:
        print("Bases revisadas: %d | productos corregidos: %d" % (len(destinos), total_cambios))
    else:
        print("Bases revisadas: %d | productos que cambiarían: %d" % (len(destinos), total_cambios))
        print("Ejecute con --aplicar para corregirlos.")


if __name__ == "__main__":
    main()
