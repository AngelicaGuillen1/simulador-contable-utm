"""Pone al día el texto de las actividades del aula con el cronograma vigente del proyecto.

Cuando cambia el texto de una actividad —por ejemplo, al dejar de nombrar la empresa compartida y
pasar a explicar que cada estudiante tiene la suya—, las aulas ya creadas conservan el texto viejo
porque el aula es una copia de la plantilla. Este script vuelve a construir las instrucciones con
la MISMA función que usa el sembrador (`construir_instrucciones`) y las reescribe solo si cambiaron.

No toca fechas, intentos, estado ni entregas; no duplica ni borra actividades; es idempotente.

    python database/actualizar_texto_actividades.py             # informe
    python database/actualizar_texto_actividades.py --aplicar   # escribe
    python database/actualizar_texto_actividades.py --aplicar --aula ealcivar4002
"""
import argparse
import glob
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402
from database.seed_actividades import (  # noqa: E402
    ACTIVIDADES, _unidad_del_cronograma, buscar_en_cronograma, cargar_cronograma,
    construir_instrucciones,
)

POR_CODIGO = {a["codigo"]: a for a in ACTIVIDADES}


def actualizar(ruta, cronograma, escribir=False):
    """Devuelve cuántos campos quedaron distintos (y los reescribe si escribir=True)."""
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    cambios = 0
    try:
        for fila in conexion.execute(
                "SELECT id, codigo, titulo, instrucciones, evidencia_requerida "
                "FROM actividades").fetchall():
            definicion = POR_CODIGO.get(fila["codigo"])
            if not definicion:
                continue
            item = buscar_en_cronograma(cronograma, definicion)
            unidad = _unidad_del_cronograma(cronograma, definicion["unidad"])
            nuevos = {
                "titulo": definicion["titulo"],
                "instrucciones": construir_instrucciones(definicion, item, unidad),
            }
            for campo, nuevo in nuevos.items():
                if nuevo is None:
                    continue
                if (fila[campo] or "").strip() != nuevo.strip():
                    cambios += 1
                    if escribir:
                        conexion.execute("UPDATE actividades SET %s = ? WHERE id = ?"
                                         % campo, (nuevo, fila["id"]))
        if escribir:
            conexion.commit()
    finally:
        conexion.close()
    return cambios


def main():
    analizador = argparse.ArgumentParser(
        description="Actualiza el texto de las actividades de cada aula con el cronograma vigente.")
    analizador.add_argument("--aplicar", action="store_true", help="escribe los cambios")
    analizador.add_argument("--aula", help="solo este estudiante")
    argumentos = analizador.parse_args()

    cronograma = cargar_cronograma()
    if not cronograma:
        raise SystemExit("No encontré el cronograma del proyecto.")
    print("Actividades del cronograma: %d" % len(cronograma.get("actividades") or []))
    print("Modo: %s\n" % ("APLICAR" if argumentos.aplicar else "solo informe (agregue --aplicar)"))

    rutas = sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "B", "*.db")))
    if argumentos.aula:
        usuario = argumentos.aula.split("@")[0]
        rutas = [r for r in rutas if os.path.basename(r) == "%s.db" % usuario]
        if not rutas:
            raise SystemExit("No encontré el aula de %s" % usuario)

    total = 0
    for ruta in rutas:
        total += actualizar(ruta, cronograma, escribir=argumentos.aplicar)
    print("Aulas revisadas: %d | campos con texto viejo: %d" % (len(rutas), total))
    if argumentos.aplicar:
        print("Las fechas, los intentos y las entregas no se tocan.")
    else:
        print("Ejecute con --aplicar para escribir.")


if __name__ == "__main__":
    sys.exit(main() or 0)
