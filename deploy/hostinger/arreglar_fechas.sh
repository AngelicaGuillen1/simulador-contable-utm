#!/usr/bin/env bash
# ============================================================================
#  Arregla la ventana de disponibilidad de las actividades del sílabo.
#
#  Deja cada tarea abierta desde el inicio de su unidad (así el estudiante puede
#  trabajar durante toda la unidad) y mantiene la fecha de entrega del cronograma.
#
#  Uso (en el servidor, como root):
#      bash arreglar_fechas.sh
#
#  Rutas por defecto del VPS: código en /opt/simulador y datos en /var/datos.
#  Se pueden cambiar con las variables PROYECTO_DIR y DATOS_DIR.
# ============================================================================
set -u

PROYECTO="${PROYECTO_DIR:-/opt/simulador}"
DATOS="${DATOS_DIR:-/var/datos}"
# En Linux el intérprete está en .venv/bin/python; en Windows (para probar en local), en
# .venv/Scripts/python.exe. Se puede indicar con PYTHON=... si hace falta.
PY="${PYTHON:-$PROYECTO/.venv/bin/python}"

verde() { echo -e "\033[32m$*\033[0m"; }
rojo()  { echo -e "\033[31m$*\033[0m"; }

if [[ ! -x "$PY" ]]; then
  rojo "No encuentro el python del proyecto en $PY"
  echo "  Si el código está en otra carpeta, ejecute:  PROYECTO_DIR=/ruta bash $0"
  exit 1
fi

echo "Proyecto : $PROYECTO"
echo "Datos    : $DATOS"
echo

DATABASE_PATH="$DATOS/simulator.db" \
RUTA_AULAS="$DATOS/aulas" \
RUTA_PLANTILLA="$DATOS/plantilla/aula_base.db" \
"$PY" - <<'PY'
"""Abre cada actividad al inicio de su unidad y conserva su cierre."""
import glob
import os
import sqlite3

# Semana del período en la que empieza cada unidad (1, 5, 9 y 13).
SEMANA = {1: 1, 2: 5, 3: 9, 4: 13}
INICIO_PERIODO = "2026-09-21"          # primer día del período académico
from datetime import datetime, timedelta


def apertura(unidad):
    fecha = datetime.strptime(INICIO_PERIODO, "%Y-%m-%d") + timedelta(days=7 * (SEMANA.get(int(unidad or 1), 1) - 1))
    return fecha.strftime("%Y-%m-%d 00:00")


rutas = [os.environ["DATABASE_PATH"], os.environ["RUTA_PLANTILLA"]]
rutas += sorted(glob.glob(os.path.join(os.environ["RUTA_AULAS"], "*", "*.db")))

total = 0
detalle = []
for ruta in rutas:
    if not os.path.exists(ruta):
        continue
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    try:
        tablas = {f[0] for f in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "actividades" not in tablas:
            continue
        cambiadas = 0
        for fila in conexion.execute("SELECT id, codigo, unidad, fecha_apertura, fecha_cierre FROM actividades"):
            nueva = apertura(fila["unidad"])
            if (fila["fecha_apertura"] or "") != nueva:
                conexion.execute("UPDATE actividades SET fecha_apertura = ? WHERE id = ?", (nueva, fila["id"]))
                cambiadas += 1
                detalle.append((fila["codigo"], (fila["fecha_apertura"] or "-")[:16], nueva[:16],
                                (fila["fecha_cierre"] or "-")[:16]))
        conexion.commit()
        total += cambiadas
    finally:
        conexion.close()

print("Bases revisadas        : %d" % len(rutas))
print("Actividades corregidas : %d" % total)
print()
if detalle:
    print("%-8s %-17s %-17s %s" % ("CODIGO", "ANTES", "AHORA", "CIERRA (sin cambios)"))
    for codigo, antes, ahora, cierre in detalle[:8]:
        print("%-8s %-17s %-17s %s" % (codigo, antes, ahora, cierre))
    if len(detalle) > 8:
        print("... y %d más (una por cada aula y actividad)" % (len(detalle) - 8))
else:
    print("Todo estaba ya correcto.")

# Comprobación final sobre una actividad del aula de ejemplo
ejemplo = os.path.join(os.environ["RUTA_AULAS"], "B")
if os.path.isdir(ejemplo):
    archivos = sorted(glob.glob(os.path.join(ejemplo, "*.db")))
    if archivos:
        conexion = sqlite3.connect(archivos[0])
        fila = conexion.execute("SELECT codigo, fecha_apertura FROM actividades ORDER BY id LIMIT 1").fetchone()
        conexion.close()
        print()
        print("Comprobación en %s -> %s abre %s" % (os.path.basename(archivos[0]), fila[0], fila[1]))
PY

echo
verde "LISTO. Los estudiantes verán la tarea 1 disponible al recargar la página."
