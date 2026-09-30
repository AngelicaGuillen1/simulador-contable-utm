"""Borra el historial de ingresos de los estudiantes (panel docente).

Sirve para dejar el panel de accesos como recién entregado. Hace falta porque **cualquier
verificación por HTTP que entre como estudiante queda registrada como un ingreso real**: el
panel muestra «han ingresado N» y la docente lo lee como que sus estudiantes ya entraron
(cuando fueron las pruebas).

    python database/limpiar_accesos.py                 # solo informa (no borra nada)
    python database/limpiar_accesos.py --si            # borra sesiones y eventos de estudiantes
    python database/limpiar_accesos.py --si --aula ealcivar4002

No toca el plan de cuentas, el catálogo, las actividades, las evidencias ni el trabajo
contable: solo el rastro de accesos (sesiones_usuario y eventos_estudiante) de los
estudiantes. Las sesiones del docente y del administrador se conservan.
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

ESTUDIANTES = "JOIN roles r ON r.id = u.rol_id AND r.nombre = 'Estudiante'"


def _conexion(ruta=None):
    conexion = sqlite3.connect(ruta or Config.DATABASE_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def resumen(ruta=None, usuario=None):
    """Cuenta sesiones y eventos de estudiantes, y delata las sesiones de prueba."""
    conexion = _conexion(ruta)
    try:
        filtro = " AND u.username = ?" if usuario else ""
        parametros = (usuario,) if usuario else ()
        sesiones = conexion.execute(
            "SELECT COUNT(*) FROM sesiones_usuario s JOIN usuarios u ON u.id = s.usuario_id "
            + ESTUDIANTES + filtro, parametros).fetchone()[0]
        eventos = conexion.execute(
            "SELECT COUNT(*) FROM eventos_estudiante e JOIN usuarios u ON u.id = e.usuario_id "
            + ESTUDIANTES + filtro, parametros).fetchone()[0]
        prueba = conexion.execute(
            "SELECT COUNT(*) FROM sesiones_usuario s JOIN usuarios u ON u.id = s.usuario_id "
            + ESTUDIANTES + " AND (s.navegador IS NULL OR s.navegador LIKE '%urllib%' "
                              "OR s.navegador LIKE '%python%' OR s.navegador LIKE '%curl%' "
                              "OR s.navegador LIKE '%node%' OR s.navegador LIKE '%requests%')"
            + filtro, parametros).fetchone()[0]
        detalle = conexion.execute(
            "SELECT u.username, COUNT(s.id) AS n, MAX(s.inicio) AS ultimo, "
            "       MAX(s.navegador) AS navegador "
            "FROM usuarios u JOIN sesiones_usuario s ON s.usuario_id = u.id "
            + ESTUDIANTES + filtro +
            " GROUP BY u.id ORDER BY n DESC", parametros).fetchall()
        otra_parte = conexion.execute(
            "SELECT COUNT(*) FROM sesiones_usuario s JOIN usuarios u ON u.id = s.usuario_id "
            "LEFT JOIN roles r ON r.id = u.rol_id WHERE r.nombre IS NULL OR r.nombre <> 'Estudiante'"
        ).fetchone()[0]
        return {"sesiones": sesiones, "eventos": eventos, "de_prueba": prueba,
                "detalle": [dict(f) for f in detalle], "otras": otra_parte}
    finally:
        conexion.close()


def limpiar(ruta=None, usuario=None):
    """Borra el rastro de accesos de los estudiantes. Devuelve cuántas filas borró."""
    conexion = _conexion(ruta)
    borradas = 0
    try:
        condicion = "usuario_id IN (SELECT u.id FROM usuarios u %s%s)" % (
            ESTUDIANTES, " WHERE u.username = ?" if usuario else "")
        parametros = (usuario,) if usuario else ()
        with conexion:
            borradas += conexion.execute(
                "DELETE FROM eventos_estudiante WHERE " + condicion, parametros).rowcount
            borradas += conexion.execute(
                "DELETE FROM sesiones_usuario WHERE " + condicion, parametros).rowcount
        return borradas
    finally:
        conexion.close()


def main():
    analizador = argparse.ArgumentParser(description="Limpia el historial de ingresos de los estudiantes.")
    analizador.add_argument("--si", action="store_true", help="ejecuta el borrado (sin esto solo informa)")
    analizador.add_argument("--aula", help="solo este estudiante (usuario o correo)")
    argumentos = analizador.parse_args()

    usuario = argumentos.aula
    if usuario and '@' in usuario:
        usuario = usuario.split('@')[0]

    print("Base de control: %s" % Config.DATABASE_PATH)
    antes = resumen(usuario=usuario)
    print("  Registros de estudiantes: %d sesiones · %d eventos" % (antes["sesiones"], antes["eventos"]))
    print("  De esas sesiones, %d tienen navegador de prueba (urllib/python/curl/node/requests)"
          % antes["de_prueba"])
    print("  Sesiones de docente/administrador que se conservan: %d" % antes["otras"])
    for fila in antes["detalle"][:8]:
        print("     %-22s %-3s sesiones  último: %-19s %s"
              % (fila["username"], fila["n"], fila["ultimo"] or "-", fila["navegador"] or ""))

    if not argumentos.si:
        print("\n  (solo informe: agregue --si para borrar el historial)")
        return 0

    borradas = limpiar(usuario=usuario)
    despues = resumen(usuario=usuario)
    print("\n  Filas borradas: %d" % borradas)
    print("  Estado final: %d sesiones · %d eventos de estudiantes"
          % (despues["sesiones"], despues["eventos"]))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
