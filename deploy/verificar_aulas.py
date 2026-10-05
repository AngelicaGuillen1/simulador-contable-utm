"""Comprueba, en el servidor, que las aulas de los estudiantes están como deben estar.

Se ejecuta al final del despliegue y deja la evidencia en el registro: cuántas aulas hay, si cada
empresa es distinta, si las identificaciones cumplen la estructura del SRI, si los valores del
catálogo son propios, si los textos ya no nombran la empresa compartida y si alguna aula tiene
movimientos cuando debería estar en cero. No inicia sesión como ningún estudiante, así que no deja
rastro en el panel de accesos de la docente.

    python deploy/verificar_aulas.py
    python deploy/verificar_aulas.py --detalle     # muestra las primeras aulas
"""
import argparse
import glob
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

tildes_buenas = tildes_malas = 0


def valida_cedula(identificacion):
    if len(identificacion) != 10 or not identificacion.isdigit():
        return False
    suma = 0
    for posicion, digito in enumerate(identificacion[:9]):
        valor = int(digito) * (2 if posicion % 2 == 0 else 1)
        suma += valor - 9 if valor > 9 else valor
    return (10 - suma % 10) % 10 == int(identificacion[9])


def valida_ruc(identificacion):
    if len(identificacion) != 13 or not identificacion.isdigit() or identificacion[2] != "9":
        return False
    if identificacion[10:] != "001":
        return False
    suma = sum(int(d) * p for d, p in zip(identificacion[:9], [4, 3, 2, 7, 6, 5, 4, 3, 2]))
    verificador = 11 - suma % 11
    verificador = 0 if verificador >= 10 else verificador
    return str(verificador) == identificacion[9]


def _asientos_cuadran(objeto):
    """True si todos los asientos del JSON (a cualquier profundidad) cuadran."""
    if isinstance(objeto, dict):
        if "debe" in objeto or "haber" in objeto:
            return True
        return all(_asientos_cuadran(v) for v in objeto.values())
    if isinstance(objeto, list):
        lineas = [l for l in objeto if isinstance(l, dict) and ("debe" in l or "haber" in l)]
        if lineas:
            debe = round(sum(float(l.get("debe") or 0) for l in lineas), 2)
            haber = round(sum(float(l.get("haber") or 0) for l in lineas), 2)
            if abs(debe - haber) >= 0.02:
                return False
        return all(_asientos_cuadran(v) for v in objeto)
    return True


def main():
    analizador = argparse.ArgumentParser(description="Verifica las aulas de los estudiantes.")
    analizador.add_argument("--detalle", action="store_true", help="muestra las primeras aulas")
    argumentos = analizador.parse_args()

    rutas = sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "B", "*.db")))
    if not rutas:
        print("   [AVISO] No encontré aulas en %s" % Config.RUTA_AULAS)
        return 1

    empresas, inventarios, problemas, huellas = {}, [], [], {}
    identificaciones_malas = textos_viejos = con_movimientos = 0
    casos_totales = asientos_descuadrados = 0
    estructura = None
    for ruta in rutas:
        usuario = os.path.basename(ruta)[:-3]
        conexion = sqlite3.connect(ruta)
        conexion.row_factory = sqlite3.Row
        try:
            empresa = conexion.execute("SELECT razon_social, ruc FROM empresas LIMIT 1").fetchone()
            if empresa:
                empresas.setdefault(empresa["razon_social"], []).append(usuario)
                if not valida_ruc(str(empresa["ruc"] or "")):
                    problemas.append("%s: RUC de empresa inválido (%s)" % (usuario, empresa["ruc"]))

            for tabla in ("clientes", "proveedores"):
                for fila in conexion.execute("SELECT identificacion FROM %s" % tabla):
                    identificacion = str(fila[0] or "")
                    correcta = (valida_cedula(identificacion) if len(identificacion) == 10
                                else valida_ruc(identificacion))
                    if not correcta:
                        identificaciones_malas += 1

            conteo = tuple(conexion.execute("SELECT COUNT(*) FROM %s" % tabla).fetchone()[0]
                           for tabla in ("cuentas", "productos", "clientes", "proveedores", "bancos"))
            estructura = estructura or conteo
            if conteo != estructura:
                problemas.append("%s: estructura distinta %s" % (usuario, conteo))

            inventario = conexion.execute(
                "SELECT COALESCE(SUM(stock_actual * costo_unitario), 0) FROM productos").fetchone()[0]
            inventarios.append(float(inventario or 0))

            for fila in conexion.execute("SELECT instrucciones FROM actividades"):
                if "Nueva Esperanza" in (fila[0] or ""):
                    textos_viejos += 1

            tabla_asientos = conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE '%asiento%' "
                "ORDER BY LENGTH(name) LIMIT 1").fetchone()
            if tabla_asientos:
                asientos = conexion.execute(
                    "SELECT COUNT(*) FROM %s" % tabla_asientos[0]).fetchone()[0]
                if asientos:
                    con_movimientos += 1

            # Los 19 casos del simulador: cifras propias y asientos cuadrados.
            casos = conexion.execute(
                "SELECT solucion_esperada_json FROM casos_simulacion").fetchall()
            casos_totales += len(casos)
            huella = []
            for fila_caso in casos:
                try:
                    datos_caso = json.loads(fila_caso["solucion_esperada_json"] or "{}")
                except ValueError:
                    continue
                if not _asientos_cuadran(datos_caso):
                    asientos_descuadrados += 1
                    problemas.append("%s: un asiento de los casos no cuadra" % usuario)
            for fila_caso in conexion.execute("SELECT datos_transaccion_json FROM casos_simulacion"):
                try:
                    huella.append(json.loads(fila_caso[0] or "{}").get("total"))
                except ValueError:
                    huella.append(None)
            huellas.setdefault(tuple(huella), []).append(usuario)
        finally:
            conexion.close()

    repetidas = {n: u for n, u in empresas.items() if len(u) > 1}
    repetidas_casos = {k: v for k, v in huellas.items() if len(v) > 1 and any(k)}
    print("   aulas: %d | empresas distintas: %d" % (len(rutas), len(empresas)))
    print("   estructura común (cuentas, productos, clientes, proveedores, bancos): %s"
          % (estructura,))
    print("   identificaciones fuera de la norma del SRI: %d" % identificaciones_malas)
    print("   actividades que aún nombran la empresa compartida: %d" % textos_viejos)
    print("   aulas con asientos registrados (deben estar en cero): %d" % con_movimientos)
    print("   casos del simulador revisados: %d | asientos de los casos descuadrados: %d"
          % (casos_totales, asientos_descuadrados))
    print("   aulas con las mismas cifras en los 19 casos: %d" % len(repetidas_casos))
    if inventarios:
        print("   inventario inicial por aula: de %.2f a %.2f" % (min(inventarios), max(inventarios)))
    if repetidas:
        problemas.append("empresas repetidas: %s" % ", ".join(sorted(repetidas)))
    for problema in problemas[:8]:
        print("   [PROBLEMA] %s" % problema)

    if argumentos.detalle:
        print()
        for ruta in rutas[:5]:
            conexion = sqlite3.connect(ruta)
            fila = conexion.execute("SELECT razon_social, ruc FROM empresas LIMIT 1").fetchone()
            cliente = conexion.execute(
                "SELECT nombre_razon_social FROM clientes ORDER BY RANDOM() LIMIT 1").fetchone()
            print("   %-16s %s (%s) · cliente: %s"
                  % (os.path.basename(ruta)[:-3], fila[0], fila[1], cliente[0]))
            conexion.close()

    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
