#!/usr/bin/env python
"""
Exportador de evidencias del Simulador Contable para aulas aisladas.

Recorre las bases de datos de las aulas (una por estudiante), calcula los indicadores
contables y académicos de cada una y genera:

    evidencias_simulador.xlsx   -> hojas "Resumen" (una fila por estudiante),
                                   "Simulador" (intentos y puntuaciones) y
                                   "Revision" (avisos que requieren su atención)
    evidencias_simulador.csv    -> el resumen, para subir o procesar aparte

Es el insumo para calificar y para subir la evidencia a Moodle: no hay que depender de
capturas de pantalla del estudiante, los números salen del propio sistema.

Uso:
    python deploy/multiaula/exportar_evidencias.py
    python deploy/multiaula/exportar_evidencias.py --datos /var/datos/aulas --salida /root/evidencias
    python deploy/multiaula/exportar_evidencias.py --min-asientos 20 --permitir-descuadres 0
    python deploy/multiaula/exportar_evidencias.py --aulas aula01,aula02 --salida ./prueba

Los umbrales de cumplimiento son parámetros: no hay criterios "inventados" por el sistema.
"""

import argparse
import csv
import json
import os
import sqlite3
import sys
from datetime import datetime

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from config import Config                      # noqa: E402
from services.accounting_service import AccountingService  # noqa: E402
from services.inventory_service import InventoryService    # noqa: E402

COLUMNAS_RESUMEN = [
    ("aula", "Aula"),
    ("estudiante", "Estudiante"),
    ("asientos", "Asientos registrados"),
    ("lineas", "Líneas de asiento"),
    ("descuadres", "Asientos descuadrados"),
    ("cuentas_con_movimiento", "Cuentas con movimiento"),
    ("sumas_cuadran", "Sumas cuadran"),
    ("saldos_cuadran", "Saldos cuadran"),
    ("total_debitos", "Total débitos"),
    ("total_creditos", "Total créditos"),
    ("activo", "Activo"),
    ("pasivo", "Pasivo"),
    ("patrimonio", "Patrimonio"),
    ("pasivo_patrimonio", "Pasivo + Patrimonio"),
    ("diferencia_patrimonial", "Diferencia patrimonial"),
    ("balanceado", "Ecuación cuadra"),
    ("ingresos", "Ingresos del período"),
    ("costo_ventas", "Costo de ventas"),
    ("gastos", "Gastos del período"),
    ("utilidad_neta", "Utilidad neta"),
    ("caja", "Saldo de caja"),
    ("bancos", "Saldo bancario"),
    ("inventario", "Inventario valorizado"),
    ("cuentas_por_cobrar", "Cuentas por cobrar"),
    ("cuentas_por_pagar", "Cuentas por pagar"),
    ("productos_bajo_minimo", "Productos bajo mínimo"),
    ("intentos", "Intentos del simulador"),
    ("intentos_completados", "Intentos completados"),
    ("puntuacion_promedio", "Puntuación promedio"),
    ("mejor_puntuacion", "Mejor puntuación"),
    ("pistas_utilizadas", "Pistas utilizadas"),
    ("casos_incorrectos", "Casos incorrectos"),
    ("cumple_asientos", "Cumple mínimo de asientos"),
    ("cumple_sin_descuadres", "Sin asientos descuadrados"),
    ("cumple_ecuacion", "Ecuación patrimonial correcta"),
    ("cumplimiento", "Cumplimiento (0-3)"),
]


def _conexion(ruta):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    return conexion


def _indicadores_contables(ruta):
    """Indicadores del motor contable usando la base del aula indicada."""
    balance = AccountingService.get_trial_balance(db_path=ruta)
    situacion = AccountingService.get_balance_sheet(db_path=ruta)
    resultados = AccountingService.get_income_statement(db_path=ruta)

    conexion = _conexion(ruta)
    try:
        asientos = conexion.execute("SELECT COUNT(*) FROM asientos").fetchone()[0]
        lineas = conexion.execute("SELECT COUNT(*) FROM detalle_asientos").fetchone()[0]
        descuadres = conexion.execute(
            "SELECT COUNT(*) FROM (SELECT asiento_id FROM detalle_asientos "
            "GROUP BY asiento_id HAVING ABS(SUM(debe) - SUM(haber)) > 0.004)"
        ).fetchone()[0]
        cuentas_movimiento = len(balance.get("cuentas", []))

        def saldo(codigo):
            for cuenta in balance.get("cuentas", []):
                if cuenta["codigo"] == codigo:
                    return round(float(cuenta["saldo_deudor"]) - float(cuenta["saldo_acreedor"]), 2)
            return 0.0

        caja = saldo("1.1.01")
        bancos = round(saldo("1.1.02") + saldo("1.1.03"), 2)
        inventario = saldo("1.1.06")
        por_cobrar = saldo("1.1.04")
        por_pagar = round(-saldo("2.1.01"), 2)
    finally:
        conexion.close()

    try:
        bajo_minimo = len(InventoryService.get_low_stock_alerts(db_path=ruta))
    except TypeError:
        bajo_minimo = len(InventoryService.get_low_stock_alerts())

    return {
        "asientos": asientos,
        "lineas": lineas,
        "descuadres": descuadres,
        "cuentas_con_movimiento": cuentas_movimiento,
        "sumas_cuadran": bool(balance.get("cuadrado_sumas")),
        "saldos_cuadran": bool(balance.get("cuadrado_saldos")),
        "total_debitos": round(float(balance.get("total_debitos") or 0), 2),
        "total_creditos": round(float(balance.get("total_creditos") or 0), 2),
        "activo": round(float(situacion.get("total_activo") or 0), 2),
        "pasivo": round(float(situacion.get("total_pasivo") or 0), 2),
        "patrimonio": round(float(situacion.get("total_patrimonio") or 0), 2),
        "pasivo_patrimonio": round(float(situacion.get("total_pasivo_y_patrimonio") or 0), 2),
        "diferencia_patrimonial": round(float(situacion.get("diferencia") or 0), 2),
        "balanceado": bool(situacion.get("balanceado")),
        "ingresos": round(float(resultados.get("total_ingresos_operacionales") or 0), 2),
        "costo_ventas": round(float(resultados.get("costo_ventas") or 0), 2),
        "gastos": round(
            float(resultados.get("total_gastos_operacionales") or 0)
            + float(resultados.get("gastos_financieros") or 0),
            2,
        ),
        "utilidad_neta": round(float(resultados.get("utilidad_neta") or 0), 2),
        "caja": caja,
        "bancos": bancos,
        "inventario": inventario,
        "cuentas_por_cobrar": por_cobrar,
        "cuentas_por_pagar": por_pagar,
        "productos_bajo_minimo": bajo_minimo,
    }


def _indicadores_academicos(ruta):
    """Intentos de simulación registrados en la base del aula."""
    conexion = _conexion(ruta)
    try:
        intentos = conexion.execute(
            "SELECT i.id, i.puntuacion_total, i.estado, i.tiempo_segundos, s.titulo, s.nivel "
            "FROM intentos_estudiante i LEFT JOIN simulaciones s ON s.id = i.simulacion_id"
        ).fetchall()

        puntuaciones = [float(i["puntuacion_total"]) for i in intentos if i["puntuacion_total"] is not None]
        pistas = conexion.execute(
            "SELECT COALESCE(SUM(pistas_utilizadas), 0) FROM detalle_intentos"
        ).fetchone()[0]
        casos_incorrectos = conexion.execute(
            "SELECT COUNT(*) FROM detalle_intentos WHERE resultado = 'INCORRECTO'"
        ).fetchone()[0]
        completados = sum(1 for i in intentos if (i["estado"] or "").upper() == "COMPLETADO")
        nombre = conexion.execute(
            "SELECT nombre_completo FROM usuarios WHERE username = 'estudiante'"
        ).fetchone()
    finally:
        conexion.close()

    return {
        "intentos": len(intentos),
        "intentos_completados": completados,
        "puntuacion_promedio": round(sum(puntuaciones) / len(puntuaciones), 2) if puntuaciones else 0.0,
        "mejor_puntuacion": round(max(puntuaciones), 2) if puntuaciones else 0.0,
        "pistas_utilizadas": int(pistas or 0),
        "casos_incorrectos": int(casos_incorrectos or 0),
        "estudiante_db": (nombre["nombre_completo"] if nombre else ""),
    }


def _evaluar_cumplimiento(fila, minimo_asientos, descuadres_permitidos):
    cumple_asientos = fila["asientos"] >= minimo_asientos
    cumple_descuadres = fila["descuadres"] <= descuadres_permitidos
    cumple_ecuacion = bool(fila["balanceado"]) and fila["diferencia_patrimonial"] == 0
    fila["cumple_asientos"] = "SI" if cumple_asientos else "NO"
    fila["cumple_sin_descuadres"] = "SI" if cumple_descuadres else "NO"
    fila["cumple_ecuacion"] = "SI" if cumple_ecuacion else "NO"
    fila["cumplimiento"] = sum([cumple_asientos, cumple_descuadres, cumple_ecuacion])
    return fila


def recoger(datos_dir, aulas=None, nombres=None):
    """Recorre las aulas y devuelve (filas, revision)."""
    if not os.path.isdir(datos_dir):
        raise SystemExit(f"No existe el directorio de aulas: {datos_dir}")

    filas = []
    revision = []

    for entrada in sorted(os.listdir(datos_dir)):
        ruta_aula = os.path.join(datos_dir, entrada)
        ruta_db = os.path.join(ruta_aula, "simulator.db")
        if aulas and entrada not in aulas:
            continue
        if not os.path.isfile(ruta_db):
            revision.append({"aula": entrada, "aviso": "Sin base de datos (nunca se inició el aula)"})
            continue

        fila = {"aula": entrada}
        try:
            fila.update(_indicadores_contables(ruta_db))
            fila.update(_indicadores_academicos(ruta_db))
        except Exception as error:  # base corrupta o a medio sembrar
            revision.append({"aula": entrada, "aviso": f"No se pudo leer: {error}"})
            continue

        fila["estudiante"] = (nombres or {}).get(entrada) or fila.get("estudiante_db") or ""
        filas.append(fila)

        if fila["descuadres"] > 0:
            revision.append({"aula": entrada, "aviso": f"{fila['descuadres']} asiento(s) descuadrado(s)"})
        if not fila["balanceado"]:
            revision.append({"aula": entrada,
                             "aviso": f"Ecuación patrimonial con diferencia {fila['diferencia_patrimonial']}"})
        if fila["asientos"] == 0:
            revision.append({"aula": entrada, "aviso": "Sin asientos registrados"})

    return filas, revision


def cargar_nombres(ruta_csv, datos_dir):
    """Lee un CSV 'aula;nombre' (o coma) y un archivo nombres.txt por aula."""
    nombres = {}
    if ruta_csv and os.path.isfile(ruta_csv):
        with open(ruta_csv, encoding="utf-8-sig", newline="") as archivo:
            muestra = archivo.readline()
            archivo.seek(0)
            separador = ";" if ";" in muestra else ","
            for fila in csv.reader(archivo, delimiter=separador):
                if len(fila) >= 2 and fila[0].strip() and fila[0].strip().lower() != "aula":
                    nombres[fila[0].strip()] = fila[1].strip()
    for entrada in sorted(os.listdir(datos_dir)):
        ruta_txt = os.path.join(datos_dir, entrada, "estudiante.txt")
        if os.path.isfile(ruta_txt):
            with open(ruta_txt, encoding="utf-8") as archivo:
                nombres.setdefault(entrada, archivo.read().strip())
    return nombres


def escribir_salida(filas, revision, salida_base, metadatos):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("openpyxl no está instalado: instale requirements.txt para generar el Excel.")
        Workbook = None

    ruta_csv = salida_base + ".csv"
    with open(ruta_csv, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow([titulo for _, titulo in COLUMNAS_RESUMEN])
        for fila in filas:
            escritor.writerow([fila.get(clave, "") for clave, _ in COLUMNAS_RESUMEN])
    print(f"  CSV:   {ruta_csv}")

    if Workbook is None:
        return ruta_csv, None

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Resumen"
    encabezado = Font(bold=True, color="FFFFFF")
    fondo = PatternFill("solid", fgColor="1D4ED8")

    hoja.append([titulo for _, titulo in COLUMNAS_RESUMEN])
    for celda in hoja[1]:
        celda.font = encabezado
        celda.fill = fondo
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for fila in filas:
        hoja.append([fila.get(clave, "") for clave, _ in COLUMNAS_RESUMEN])

    for indice, (clave, titulo) in enumerate(COLUMNAS_RESUMEN, start=1):
        valores = [str(fila.get(clave, "")) for fila in filas] + [titulo]
        hoja.column_dimensions[get_column_letter(indice)].width = min(
            max(len(valor) for valor in valores) + 3, 34
        )
    hoja.freeze_panes = "C2"

    hoja_revision = libro.create_sheet("Revision")
    hoja_revision.append(["Aula", "Aviso a revisar"])
    for celda in hoja_revision[1]:
        celda.font = encabezado
        celda.fill = fondo
    for aviso in revision:
        hoja_revision.append([aviso["aula"], aviso["aviso"]])
    hoja_revision.column_dimensions["A"].width = 16
    hoja_revision.column_dimensions["B"].width = 70

    hoja_datos = libro.create_sheet("Datos")
    for clave, valor in metadatos.items():
        hoja_datos.append([clave, valor])
    hoja_datos.column_dimensions["A"].width = 34
    hoja_datos.column_dimensions["B"].width = 60

    ruta_xlsx = salida_base + ".xlsx"
    libro.save(ruta_xlsx)
    print(f"  Excel: {ruta_xlsx}")
    return ruta_csv, ruta_xlsx


def main():
    parser = argparse.ArgumentParser(description="Evidencias contables y académicas de las aulas")
    parser.add_argument("--datos", default=os.environ.get("AULAS_DIR", "/var/datos/aulas"),
                        help="carpeta con una subcarpeta por aula")
    parser.add_argument("--salida", default=".", help="carpeta o nombre base de los archivos generados")
    parser.add_argument("--aulas", help="lista separada por comas (por defecto todas)")
    parser.add_argument("--nombres", help="CSV 'aula;nombre del estudiante'")
    parser.add_argument("--min-asientos", type=int, default=0,
                        help="mínimo de asientos para considerar cumplida la práctica")
    parser.add_argument("--permitir-descuadres", type=int, default=0,
                        help="asientos descuadrados tolerados")
    args = parser.parse_args()

    aulas = [a.strip() for a in args.aulas.split(",")] if args.aulas else None
    nombres = cargar_nombres(args.nombres, args.datos) if os.path.isdir(args.datos) else {}
    filas, revision = recoger(args.datos, aulas, nombres)
    for fila in filas:
        _evaluar_cumplimiento(fila, args.min_asientos, args.permitir_descuadres)

    base = args.salida
    if os.path.isdir(base) or base.endswith(("/", "\\")):
        os.makedirs(base, exist_ok=True)
        base = os.path.join(base, "evidencias_simulador")

    metadatos = {
        "Generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Carpeta de aulas": args.datos,
        "Aulas con datos": len(filas),
        "Avisos de revisión": len(revision),
        "Mínimo de asientos exigido": args.min_asientos,
        "Asientos descuadrados tolerados": args.permitir_descuadres,
    }

    print("=" * 78)
    print(" EVIDENCIAS DEL SIMULADOR CONTABLE")
    print("=" * 78)
    print(f"  Aulas analizadas: {len(filas)}")
    if filas:
        print(f"  Asientos en total: {sum(f['asientos'] for f in filas)}")
        print(f"  Aulas con la ecuación patrimonial correcta: "
              f"{sum(1 for f in filas if f['balanceado'])}/{len(filas)}")
        print(f"  Aulas con asientos descuadrados: {sum(1 for f in filas if f['descuadres'] > 0)}")
    escribir_salida(filas, revision, base, metadatos)
    if revision:
        print(f"  Avisos de revisión: {len(revision)}")
        for aviso in revision[:15]:
            print(f"    - {aviso['aula']}: {aviso['aviso']}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
