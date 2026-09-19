# -*- coding: utf-8 -*-
"""crear_aula.py — crea el aula (base de datos propia) de un estudiante.

Cada estudiante trabaja en su propio archivo SQLite, clonado de una plantilla, de modo que
su plan de cuentas, sus asientos, sus libros y sus estados financieros no se mezclan con los
de sus compañeros (ver docs/DISENO_MULTIESTUDIANTE.md).

Uso:
    python database/crear_aula.py --plantilla                     # (re)construye la plantilla
    python database/crear_aula.py ealcivar4002 --paralelo B       # crea el aula de una estudiante
    python database/crear_aula.py ealcivar4002 --plan incompleto  # plan de cuentas a completar
    python database/crear_aula.py --todas                         # crea aulas de toda la nómina
"""
import argparse
import csv
import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config  # noqa: E402
from models import ruta_aula  # noqa: E402

# Tablas con movimientos: se vacían en cada aula (la empresa queda lista para operar,
# pero sin las operaciones del período demostrativo).
TABLAS_TRANSACCIONALES = [
    "detalle_asientos", "asientos", "detalle_ventas", "ventas", "detalle_compras", "compras",
    "transacciones_servicios", "movimientos_inventario", "kardex_lotes", "cuentas_cobrar",
    "cobros", "cuentas_pagar", "pagos", "movimientos_caja", "arqueos_caja",
    "movimientos_bancarios", "conciliaciones_bancarias", "documentos_fuente",
    "intentos_estudiante", "detalle_intentos", "casos_simulacion", "simulaciones",
    "sesiones_usuario", "eventos_estudiante", "versiones_evidencia", "evidencias",
    "asignaciones_actividad", "matriculas", "auditoria",
]

# Actividades del syllabus que recibe cada estudiante al crearse su aula.
ACTIVIDADES_SYLLABUS = [
    ("U1-A1", "Taller asistido: objeto, objetivos y usuarios de la información contable", 1, "DOCENCIA", 10.0),
    ("U2-A2", "Práctica de laboratorio: clasificación, naturaleza y dinámica de las cuentas contables", 2, "PRACTICA", 12.0),
    ("U2-A3", "Fichero autónomo de cuentas: codificación, naturaleza y dinámica", 2, "AUTONOMO", 10.0),
    ("U3-A4", "Jornalización integral de transacciones comerciales con IVA y documentos soporte", 3, "DOCENCIA", 10.0),
    ("U3-A5", "Portafolio autónomo de jornalización y mayorización", 3, "AUTONOMO", 10.0),
    ("U4-A6", "Trabajo autónomo integral: balance de comprobación de sumas y saldos y corrección de errores contables", 4, "AUTONOMO", 10.0),
]

PERIODO_P2 = ("2026-09-21", "2027-01-16")


def _conectar(ruta):
    conn = sqlite3.connect(ruta, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _limpiar_operaciones(ruta):
    """Vacía las tablas de movimientos. Las claves foráneas se desactivan durante la limpieza
    para no chocar con el orden de borrado entre padres e hijos."""
    conn = _conectar(ruta)
    fallos = []
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        for tabla in TABLAS_TRANSACCIONALES:
            try:
                conn.execute("DELETE FROM %s" % tabla)
            except sqlite3.Error as error:
                fallos.append("%s (%s)" % (tabla, error))
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
    finally:
        conn.close()
    return fallos


def construir_plantilla(destino=None, con_operaciones=False):
    """Copia la base actual y la limpia para usarla como plantilla de las aulas."""
    destino = destino or Config.RUTA_PLANTILLA
    origen = Config.DATABASE_PATH
    if not os.path.exists(origen):
        raise SystemExit("No existe la base de origen: %s" % origen)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if os.path.exists(destino):
        os.remove(destino)
    shutil.copy2(origen, destino)
    fallos = []
    if not con_operaciones:
        fallos = _limpiar_operaciones(destino)
    print("Plantilla creada: %s%s" % (destino, "" if con_operaciones else " (sin operaciones)"))
    if fallos:
        print("   Aviso: no se pudieron vaciar: %s" % "; ".join(fallos))
    return destino


def _aplicar_plan_cuentas(ruta, plan):
    """plan: completo | incompleto | vacio  (grado de avance que recibe el estudiante)."""
    if plan == "completo":
        return 0
    conn = _conectar(ruta)
    try:
        if plan == "vacio":
            borradas = conn.execute("DELETE FROM cuentas").rowcount
        else:  # incompleto: se conservan solo los dos primeros niveles
            borradas = conn.execute(
                "DELETE FROM cuentas WHERE LENGTH(REPLACE(codigo, '.', '')) > 2").rowcount
        conn.commit()
        return borradas
    finally:
        conn.close()


def _asignar_actividades(estudiante_id, paralelo, db_path=None):
    """Asigna al estudiante las seis actividades del syllabus.

    Las actividades y sus asignaciones viven en la base de CONTROL (el docente las ve todas
    juntas); el aula del estudiante guarda solo su trabajo contable.
    """
    conn = _conectar(db_path or Config.DATABASE_PATH)
    nuevas = 0
    try:
        for codigo, titulo, unidad, componente, puntaje in ACTIVIDADES_SYLLABUS:
            fila = conn.execute("SELECT id FROM actividades WHERE codigo = ?", (codigo,)).fetchone()
            if fila:
                actividad_id = fila["id"]
            else:
                cur = conn.execute(
                    """INSERT INTO actividades (codigo, titulo, unidad, componente, resultado_aprendizaje,
                           instrucciones, evidencia_requerida, puntaje, estado, modo_practica, tutor_ia,
                           modulos_habilitados, tipo_evidencia)
                       VALUES (?,?,?,?,?,?,?,?, 'ABIERTA', 0, 0, 'CUENTAS,DIARIO,MAYOR,BALANCE', 'INTEGRAL')""",
                    (codigo, titulo, unidad, componente, "", "", "", puntaje))
                actividad_id = cur.lastrowid
            cur = conn.execute(
                """INSERT OR IGNORE INTO asignaciones_actividad (actividad_id, estudiante_id, empresa_id, estado)
                   VALUES (?,?,1,'PENDIENTE')""", (actividad_id, estudiante_id))
            nuevas += cur.rowcount
        conn.commit()
        return nuevas
    finally:
        conn.close()


def _ajustar_periodo(ruta, inicio, fin, nombre=None):
    conn = _conectar(ruta)
    try:
        nombre = nombre or ("Período académico %s a %s" % (inicio, fin))
        if conn.execute("SELECT COUNT(*) FROM periodos").fetchone()[0]:
            conn.execute("UPDATE periodos SET nombre=?, fecha_inicio=?, fecha_fin=?, estado='ABIERTO'",
                         (nombre, inicio, fin))
        else:
            conn.execute("""INSERT INTO periodos (empresa_id, nombre, fecha_inicio, fecha_fin, estado)
                            VALUES (1, ?, ?, ?, 'ABIERTO')""", (nombre, inicio, fin))
        conn.execute("UPDATE parametros SET valor=? WHERE clave='fecha_trabajo'", (inicio,))
        conn.commit()
    finally:
        conn.close()


def _registrar_usuario_en_aula(ruta, estudiante_id, db_control=None):
    """Copia la fila del estudiante a la tabla `usuarios` de su aula.

    Las consultas contables hacen LEFT JOIN con `usuarios` para mostrar el nombre de quien
    registró cada asiento; sin esta fila el nombre saldría vacío. Solo se copia la fila del
    propio estudiante: no se replican los demás usuarios del sistema.
    """
    origen = _conectar(db_control or Config.DATABASE_PATH)
    try:
        columnas = [c[1] for c in origen.execute("PRAGMA table_info(usuarios)")]
        fila = origen.execute("SELECT * FROM usuarios WHERE id = ?", (estudiante_id,)).fetchone()
    finally:
        origen.close()
    if not fila:
        return 0
    datos = {c: fila[c] for c in columnas if c in fila.keys()}
    destino = _conectar(ruta)
    try:
        destino.execute("PRAGMA foreign_keys = OFF")
        destino.execute("DELETE FROM usuarios WHERE id <> ?", (estudiante_id,))
        campos = list(datos.keys())
        marcas = ",".join("?" for _ in campos)
        destino.execute("INSERT OR REPLACE INTO usuarios (%s) VALUES (%s)"
                        % (",".join(campos), marcas), [datos[c] for c in campos])
        destino.commit()
        return 1
    finally:
        destino.close()


def crear_aula(usuario, paralelo=None, plan="completo", estudiante_id=None,
               con_operaciones=False, periodo=PERIODO_P2, plantilla=None, verboso=True,
               forzar=False):
    """Crea el aula de un estudiante a partir de la plantilla. Devuelve la ruta del archivo.

    Si el aula ya existe y contiene trabajo del estudiante, no se sobreescribe salvo `forzar=True`.
    """
    plantilla = plantilla or Config.RUTA_PLANTILLA
    if not os.path.exists(plantilla):
        construir_plantilla(plantilla, con_operaciones=con_operaciones)
    destino = ruta_aula(usuario, paralelo)
    os.makedirs(os.path.dirname(destino), exist_ok=True)

    if os.path.exists(destino) and not forzar:
        try:
            conn = _conectar(destino)
            movimientos = sum(conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                              for t in ("asientos", "ventas", "compras"))
            conn.close()
        except sqlite3.Error:
            movimientos = 0
        if movimientos:
            print("  AVISO: %s ya tiene %d movimientos; no se sobreescribe (use --forzar)."
                  % (destino, movimientos))
            return destino

    shutil.copy2(plantilla, destino)

    borradas = _aplicar_plan_cuentas(destino, plan)
    if periodo:
        _ajustar_periodo(destino, periodo[0], periodo[1])
    asignadas = 0
    if estudiante_id:
        _registrar_usuario_en_aula(destino, estudiante_id)
        asignadas = _asignar_actividades(estudiante_id, paralelo)
    elif verboso:
        print("     (sin estudiante_id: no se asignaron actividades; indíquelo con --estudiante-id)")

    if verboso:
        print("  aula: %s | plan: %s%s%s"
              % (destino, plan,
                 " | cuentas retiradas: %d" % borradas if borradas else " | plan completo",
                 " | actividades asignadas: %d" % asignadas if asignadas else ""))
    return destino


def _leer_nomina(ruta_csv):
    with open(ruta_csv, encoding="utf-8") as fh:
        return [f for f in csv.DictReader(fh)]


def main():
    p = argparse.ArgumentParser(description="Crea o reconstruye las aulas de los estudiantes")
    p.add_argument("usuario", nargs="?", help="usuario del estudiante (parte local del correo)")
    p.add_argument("--paralelo", default="B")
    p.add_argument("--plan", default="completo", choices=["completo", "incompleto", "vacio"])
    p.add_argument("--estudiante-id", type=int, default=None)
    p.add_argument("--plantilla", action="store_true", help="solo (re)construye la plantilla")
    p.add_argument("--con-operaciones", action="store_true",
                   help="la plantilla conserva las operaciones demostrativas")
    p.add_argument("--todas", action="store_true", help="crea aulas para toda la nómina")
    p.add_argument("--nomina", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "Contabilidad 1",
        "datos", "nomina_paralelo_B.csv"))
    args = p.parse_args()

    if args.plantilla:
        construir_plantilla(con_operaciones=args.con_operaciones)
        return 0

    if args.todas:
        if not os.path.exists(args.nomina):
            print("No se encontró la nómina:", args.nomina)
            print("Genere primero el CSV desde el listado oficial.")
            return 1
        filas = _leer_nomina(args.nomina)
        print("Creando aulas para %d estudiantes del paralelo %s"
              % (len(filas), filas[0].get("paralelo", args.paralelo)))
        for f in filas:
            crear_aula(f["usuario"], f.get("paralelo") or args.paralelo, plan=args.plan,
                       con_operaciones=args.con_operaciones)
        return 0

    if not args.usuario:
        p.print_help()
        return 1
    crear_aula(args.usuario, args.paralelo, plan=args.plan, estudiante_id=args.estudiante_id,
               con_operaciones=args.con_operaciones)
    return 0


if __name__ == "__main__":
    sys.exit(main())
