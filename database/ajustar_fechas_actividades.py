"""Ajusta cuándo se abren y cierran las actividades del sílabo.

En el cronograma oficial cada actividad tiene su ventana (por ejemplo, la tarea de la Unidad 1
va del 5 al 10 de octubre). Esas fechas son las del **plan**, pero en la plataforma conviene
que el estudiante pueda trabajar desde el inicio de la unidad: si la tarea del sílabo abre el
5 de octubre y cierra el 10, solo tiene seis días y aparece «No disponible» durante las
primeras semanas de clase.

    # Ver cómo están las fechas en todas las bases
    python database/ajustar_fechas_actividades.py

    # Abrir cada actividad al inicio de su unidad (el cierre no se toca)
    python database/ajustar_fechas_actividades.py --unidades --aplicar

    # Cambiar una actividad concreta
    python database/ajustar_fechas_actividades.py --codigo U1-A1 --apertura 2026-09-21 --aplicar

El inicio de cada unidad se toma del inicio del período (Config) en semanas de 7 días:
unidad 1 = semana 1, unidad 2 = semana 5, unidad 3 = semana 9, unidad 4 = semana 13.
Las fechas de CIERRE (las del cronograma) nunca se modifican.
"""
import argparse
import glob
import os
import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

SEMANA_DE_INICIO_DE_UNIDAD = {1: 1, 2: 5, 3: 9, 4: 13}


def _conexion(ruta):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    return conexion


def _inicio_periodo():
    """Primer día del período, tomado de la empresa (o del 21/09/2026 por defecto)."""
    conexion = _conexion(Config.DATABASE_PATH)
    try:
        columnas = {f[1] for f in conexion.execute("PRAGMA table_info(empresas)")}
        for columna in ("periodo_inicio", "fecha_inicio_periodo", "inicio_periodo"):
            if columna in columnas:
                valor = conexion.execute("SELECT %s FROM empresas WHERE id = 1" % columna).fetchone()
                if valor and valor[0]:
                    return str(valor[0])[:10]
    finally:
        conexion.close()
    return "2026-09-21"


def apertura_de_unidad(unidad, inicio_periodo):
    semana = SEMANA_DE_INICIO_DE_UNIDAD.get(int(unidad or 1), 1)
    fecha = datetime.strptime(inicio_periodo, "%Y-%m-%d") + timedelta(days=7 * (semana - 1))
    return fecha.strftime("%Y-%m-%d 00:00")


def bases():
    """Base de control, plantilla de aulas y todas las aulas del curso."""
    rutas = [Config.DATABASE_PATH, Config.RUTA_PLANTILLA]
    for ruta in sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db"))):
        rutas.append(ruta)
    return [r for r in rutas if os.path.exists(r)]


def actividades_de(ruta):
    conexion = _conexion(ruta)
    try:
        tablas = {f[0] for f in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "actividades" not in tablas:
            return []
        return [dict(f) for f in conexion.execute(
            "SELECT id, codigo, titulo, unidad, fecha_apertura, fecha_cierre FROM actividades ORDER BY id")]
    finally:
        conexion.close()


def ajustar(ruta, cambios, aplicar=False):
    """cambios: {codigo: nueva apertura}. Devuelve cuántas filas cambió (o cambiaría)."""
    conexion = _conexion(ruta)
    try:
        if not aplicar:
            # Modo informe: NO se toca la base. Se cuenta lo que cambiaría y se sale.
            return sum(
                1 for fila in conexion.execute(
                    "SELECT codigo, fecha_apertura FROM actividades")
                if cambios.get(fila["codigo"])
                and cambios[fila["codigo"]] != (fila["fecha_apertura"] or ""))
        cambiadas = 0
        with conexion:
            for codigo, apertura in cambios.items():
                cursor = conexion.execute(
                    "UPDATE actividades SET fecha_apertura = ? WHERE codigo = ? AND "
                    "COALESCE(fecha_apertura, '') <> ?", (apertura, codigo, apertura))
                cambiadas += cursor.rowcount
        return cambiadas
    finally:
        conexion.close()


def main():
    analizador = argparse.ArgumentParser(description="Ajusta la apertura y el cierre de las actividades.")
    analizador.add_argument("--unidades", action="store_true",
                            help="abre cada actividad al inicio de su unidad (cierre intacto)")
    analizador.add_argument("--codigo", help="solo esta actividad (por ejemplo U1-A1)")
    analizador.add_argument("--apertura", help="nueva fecha de apertura (AAAA-MM-DD)")
    analizador.add_argument("--aplicar", action="store_true", help="escribe los cambios")
    argumentos = analizador.parse_args()

    inicio = _inicio_periodo()
    print("Inicio del período: %s" % inicio)
    print("Modo: %s\n" % ("APLICAR" if argumentos.aplicar else "solo informe (agregue --aplicar)"))

    print("%-8s %-9s %17s %17s" % ("CODIGO", "UNIDAD", "APERTURA ACTUAL", "APERTURA NUEVA"))
    print("-" * 58)
    cambios = {}
    # El objetivo se calcula con la REGLA, no comparando contra la primera base: si esa base
    # ya tuviera la fecha correcta y otra (la plantilla, por ejemplo) no, comparar contra la
    # primera dejaría el cambio sin detectar.
    for ruta in bases()[:1]:  # la lista de actividades es la misma en todas las bases
        for fila in actividades_de(ruta):
            if argumentos.codigo and fila["codigo"] != argumentos.codigo:
                continue
            if argumentos.apertura:
                nueva = argumentos.apertura[:10] + " 00:00"
            elif argumentos.unidades:
                nueva = apertura_de_unidad(fila["unidad"], inicio)
            else:
                nueva = fila["fecha_apertura"]
            print("%-8s %-9s %17s %17s" % (fila["codigo"], fila["unidad"],
                                           (fila["fecha_apertura"] or "-")[:16], nueva[:16]))
            if nueva:
                cambios[fila["codigo"]] = nueva

    if not cambios:
        print("\nNada que definir.")
        return 0

    total = 0
    for ruta in bases():
        total += ajustar(ruta, cambios, aplicar=argumentos.aplicar)
    if argumentos.aplicar:
        print("\nFilas actualizadas: %d" % total)
        print("Cierres: sin cambios (siguen los del cronograma).")
    else:
        print("\nSe cambiarían %d filas en %d bases. Ejecute con --aplicar." % (len(cambios), len(bases())))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
