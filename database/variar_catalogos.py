"""Da a cada estudiante valores propios en su empresa, sin cambiar la estructura.

Todos los estudiantes tienen el MISMO plan de cuentas y los MISMOS 20 productos, pero con
cifras distintas: cantidad en bodega, costo unitario y precio de venta. Así, aunque hagan
las mismas operaciones, sus estados de resultados salen diferentes (no se pueden copiar) y
el inventario con el que arranca cada empresa también es suyo.

Los valores se derivan del nombre de usuario, así que son **estables**: el mismo estudiante
siempre obtiene los mismos números y volver a ejecutarlo no los mueve (no se acumula).

    python database/variar_catalogos.py                  # informe (no escribe)
    python database/variar_catalogos.py --aplicar        # aplica a todas las aulas
    python database/variar_catalogos.py --aplicar --aula ealcivar4002

La base de cálculo es el catálogo inicial del seed (no lo que hoy tenga el aula), de modo que
el resultado no depende de ejecuciones anteriores.
"""
import argparse
import glob
import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

# Amplitud de la variación de cada valor (±)
VARIACION_STOCK = 0.20        # ±20 % de unidades en bodega
VARIACION_COSTO = 0.10        # ±10 % del costo unitario
MARGEN_MINIMO = 1.25          # el precio de venta queda entre 25 % y 45 % sobre el costo
MARGEN_EXTRA = 0.20
STOCK_MINIMO = 5


def _numero(usuario, codigo, sal):
    """Valor determinista entre 0 y 1 a partir del estudiante, el producto y una sal."""
    dato = hashlib.sha256(("%s|%s|%s" % (usuario, codigo, sal)).encode()).hexdigest()
    return int(dato[:8], 16) / 0xFFFFFFFF


def catalogo_inicial():
    """Genera un seed limpio en una carpeta temporal y devuelve sus productos."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temporal = tempfile.mkdtemp(prefix="catalogo_base_")
    referencia = os.path.join(temporal, "simulator.db")
    entorno = dict(os.environ, DATABASE_PATH=referencia)
    proceso = subprocess.run([sys.executable, os.path.join(raiz, "database", "seed_data.py")],
                             env=entorno, capture_output=True, text=True)
    if not os.path.exists(referencia):
        raise SystemExit("No se pudo generar el catálogo base:\n%s"
                         % ((proceso.stdout or "") + (proceso.stderr or ""))[-500:])
    conexion = sqlite3.connect(referencia)
    conexion.row_factory = sqlite3.Row
    try:
        return {fila["codigo"]: dict(fila) for fila in conexion.execute(
            "SELECT codigo, descripcion, categoria, stock_actual, costo_unitario, precio_venta "
            "FROM productos")}
    finally:
        conexion.close()


def valores_para(usuario, producto):
    """Devuelve (stock, costo, precio) propios de ese estudiante para ese producto."""
    codigo = producto["codigo"]
    stock_base = float(producto["stock_actual"] or 0)
    costo_base = float(producto["costo_unitario"] or 0)

    f_stock = _numero(usuario, codigo, "stock")
    f_costo = _numero(usuario, codigo, "costo")
    f_margen = _numero(usuario, codigo, "margen")

    stock = max(STOCK_MINIMO, int(round(stock_base * (1 + VARIACION_STOCK * (2 * f_stock - 1)))))
    costo = round(costo_base * (1 + VARIACION_COSTO * (2 * f_costo - 1)), 2)
    if costo <= 0:
        costo = round(costo_base, 2)
    precio = round(costo * (MARGEN_MINIMO + MARGEN_EXTRA * f_margen), 2)
    if precio <= costo:
        precio = round(costo * 1.30, 2)
    return stock, costo, precio


def aplicar_en(ruta, base, usuario, escribir=False):
    """Ajusta los productos del aula. Devuelve (productos_tocados, valor_inventario)."""
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    tocados = 0
    valor = 0.0
    try:
        for fila in conexion.execute(
                "SELECT id, codigo, stock_actual, costo_unitario, precio_venta FROM productos"):
            producto = base.get(fila["codigo"])
            if not producto:
                continue
            stock, costo, precio = valores_para(usuario, producto)
            valor += stock * costo
            if (fila["stock_actual"], fila["costo_unitario"], fila["precio_venta"]) != (stock, costo, precio):
                tocados += 1
                if escribir:
                    conexion.execute(
                        "UPDATE productos SET stock_actual = ?, costo_unitario = ?, precio_venta = ? "
                        "WHERE id = ?", (stock, costo, precio, fila["id"]))
        if escribir and tocados:
            conexion.commit()
    finally:
        conexion.close()
    return tocados, round(valor, 2)


def aulas(paralelo="B"):
    return sorted(glob.glob(os.path.join(Config.RUTA_AULAS, paralelo, "*.db")))


def main():
    analizador = argparse.ArgumentParser(
        description="Da valores propios a la empresa de cada estudiante (misma estructura).")
    analizador.add_argument("--aplicar", action="store_true", help="escribe los cambios")
    analizador.add_argument("--aula", help="solo este estudiante (usuario o correo)")
    argumentos = analizador.parse_args()

    base = catalogo_inicial()
    print("Catálogo base: %d productos" % len(base))
    print("Modo: %s\n" % ("APLICAR" if argumentos.aplicar else "solo informe (agregue --aplicar)"))

    rutas = aulas()
    if argumentos.aula:
        usuario = argumentos.aula.split("@")[0]
        rutas = [r for r in rutas if os.path.basename(r) == "%s.db" % usuario]
        if not rutas:
            raise SystemExit("No encontré el aula de %s" % usuario)

    print("%-24s %6s %14s %14s" % ("ESTUDIANTE", "TOCO", "INVENTARIO", "MUESTRA (costo/precio)"))
    print("-" * 66)
    total_valor = 0.0
    minimo, maximo = None, None
    for ruta in rutas:
        usuario = os.path.basename(ruta)[:-3]
        tocados, valor = aplicar_en(ruta, base, usuario, escribir=argumentos.aplicar)
        total_valor += valor
        minimo = valor if minimo is None else min(minimo, valor)
        maximo = valor if maximo is None else max(maximo, valor)
        stock, costo, precio = valores_para(usuario, base.get("PROD-001", {"codigo": "PROD-001",
                                                                          "stock_actual": 100,
                                                                          "costo_unitario": 3.80}))
        print("%-24s %6d %14s %8s / %s" % (usuario, tocados, "{:,.2f}".format(valor), costo, precio))

    print("-" * 66)
    if rutas:
        print("Aulas: %d | inventario entre %s y %s | promedio %s"
              % (len(rutas), "{:,.2f}".format(minimo or 0), "{:,.2f}".format(maximo or 0),
                 "{:,.2f}".format(total_valor / len(rutas))))
    if argumentos.aplicar:
        print("\nAplicado. Los valores son estables: volver a ejecutarlo no los mueve.")
    else:
        print("\nEjecute con --aplicar para escribir los valores.")


if __name__ == "__main__":
    sys.exit(main() or 0)
