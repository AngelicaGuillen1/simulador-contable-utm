# -*- coding: utf-8 -*-
"""importar_nomina.py — carga la nómina oficial y crea el acceso de cada estudiante.

Para cada estudiante de la nómina:
  1. crea (o actualiza) su usuario en la base de control, con rol Estudiante, paralelo y matrícula;
  2. le genera una contraseña inicial aleatoria (nunca la cédula) guardada con hash;
  3. le crea su aula (base de datos propia) clonada de la plantilla;
  4. le asigna las seis actividades del syllabus;
  5. exporta sus credenciales a un CSV **fuera del repositorio**, para entregarlas por el aula virtual.

Uso:
    python database/importar_nomina.py --nomina datos/nomina_paralelo_B.csv
    python database/importar_nomina.py --plan incompleto --dry-run
"""
import argparse
import csv
import os
import secrets
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from werkzeug.security import generate_password_hash  # noqa: E402
from config import Config  # noqa: E402
from models import get_db_control, ruta_aula  # noqa: E402
from database.crear_aula import crear_aula  # noqa: E402

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # sin I, O, 0 ni 1 (se confunden al dictarlos)
NOMINA_POR_DEFECTO = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "2026", "S2", "Clases", "Contabilidad 1", "datos", "nomina_paralelo_B.csv"))
CREDENCIALES_POR_DEFECTO = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "2026", "S2", "Clases", "Contabilidad 1", "credenciales_paralelo_B.csv"))


def generar_password(largo=8):
    return "-".join("".join(secrets.choice(ALFABETO) for _ in range(4)) for _ in range(2))


def _rol_estudiante(conn):
    fila = conn.execute("SELECT id FROM roles WHERE LOWER(nombre) LIKE 'estudiante%'").fetchone()
    if fila:
        return fila["id"]
    conn.execute("INSERT INTO roles (nombre, descripcion) VALUES ('Estudiante', 'Estudiante del simulador')")
    conn.commit()
    return conn.execute("SELECT id FROM roles WHERE nombre='Estudiante'").fetchone()["id"]


def _nombre_presentable(nombre):
    return " ".join(p.capitalize() if p.isupper() else p for p in nombre.split())


def importar(nomina, credenciales, plan="completo", paralelo=None, dry_run=False,
             reset_passwords=False, curso=None):
    if not os.path.exists(nomina):
        print("No se encontró la nómina:", nomina)
        return 1
    with open(nomina, encoding="utf-8") as fh:
        filas = [f for f in csv.DictReader(fh) if (f.get("usuario") or "").strip()]
    if not filas:
        print("La nómina está vacía:", nomina)
        return 1

    conn = get_db_control()
    rol_id = _rol_estudiante(conn) if not dry_run else None
    curso_id = None
    if curso and not dry_run:
        fila = conn.execute("SELECT id FROM cursos WHERE codigo = ?", (curso,)).fetchone()
        if fila:
            curso_id = fila["id"]
        else:
            docente = conn.execute(
                """SELECT u.id FROM usuarios u JOIN roles r ON u.rol_id = r.id
                   WHERE LOWER(r.nombre) LIKE 'docente%' ORDER BY u.id LIMIT 1""").fetchone()
            docente_id = docente["id"] if docente else 1
            cur = conn.execute(
                """INSERT INTO cursos (nombre, codigo, docente_id, periodo_academico, activo)
                   VALUES (?,?,?,?,1)""",
                ("Contabilidad I (AUD ONLINE)", curso, docente_id,
                 "SEPTIEMBRE 2026 - ENERO 2027"))
            curso_id = cur.lastrowid
            conn.commit()

    creados = actualizados = 0
    salida = []
    try:
        for f in filas:
            usuario = f["usuario"].strip().lower()
            correo = (f.get("correo") or "").strip().lower()
            nombre = _nombre_presentable((f.get("nombre") or usuario).strip())
            cedula = (f.get("cedula") or "").strip()
            paral = (f.get("paralelo") or paralelo or "B").strip().upper()

            existente = conn.execute(
                "SELECT id, password_hash FROM usuarios WHERE username = ? OR email = ?",
                (usuario, correo)).fetchone()
            # Si el CSV trae la clave (columna `password_inicial`), se respeta: así el
            # servidor queda con EXACTAMENTE las claves de la lista que se entrega.
            password_csv = (f.get("password_inicial") or "").strip()
            password = None
            if existente:
                estudiante_id = existente["id"]
                actualizados += 1
                if reset_passwords or password_csv:
                    password = password_csv or generar_password()
                    if not dry_run:
                        conn.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?",
                                     (generate_password_hash(password), estudiante_id))
            else:
                password = password_csv or generar_password()
                creados += 1
                if not dry_run:
                    cur = conn.execute(
                        """INSERT INTO usuarios (username, password_hash, nombre_completo, email,
                                                 rol_id, activo, paralelo, matricula)
                           VALUES (?,?,?,?,?,1,?,?)""",
                        (usuario, generate_password_hash(password), nombre, correo,
                         rol_id, paral, cedula))
                    estudiante_id = cur.lastrowid
            if not dry_run:
                conn.execute("""UPDATE usuarios SET nombre_completo=?, email=?, paralelo=?, matricula=?,
                                rol_id=? WHERE id=?""",
                             (nombre, correo, paral, cedula, rol_id, estudiante_id))
                if curso_id:
                    conn.execute("""INSERT OR IGNORE INTO matriculas (curso_id, estudiante_id)
                                    VALUES (?,?)""", (curso_id, estudiante_id))
                conn.commit()

            aula = "-"
            if not dry_run:
                aula = crear_aula(usuario, paral, plan=plan, estudiante_id=estudiante_id, verboso=False)
            salida.append({
                "paralelo": paral, "usuario": usuario, "nombre": nombre, "cedula": cedula,
                "correo": correo, "password_inicial": password or password_csv or "(la que ya tenía)",
                "aula": os.path.basename(aula), "estado": "actualizado" if existente else "creado",
            })
    finally:
        conn.close()

    if not dry_run and salida:
        os.makedirs(os.path.dirname(credenciales), exist_ok=True)
        with open(credenciales, "w", newline="", encoding="utf-8") as fh:
            campos = ["paralelo", "usuario", "nombre", "cedula", "correo", "password_inicial", "aula", "estado"]
            w = csv.DictWriter(fh, fieldnames=campos)
            w.writeheader()
            w.writerows(salida)

    print("=" * 78)
    print(" IMPORTACIÓN DE LA NÓMINA%s" % (" (SIMULACIÓN, sin escribir nada)" if dry_run else ""))
    print("=" * 78)
    print(" Estudiantes en la nómina : %d" % len(filas))
    print(" Usuarios creados        : %d" % creados)
    print(" Usuarios actualizados   : %d" % actualizados)
    print(" Aulas disponibles       : %d" % len([1 for s in salida if s["aula"] != "-"]))
    print(" Plan de cuentas del aula: %s" % plan)
    if not dry_run:
        print(" Credenciales            : %s" % credenciales)
        print(" (fuera del repositorio: no se publica en GitHub)")
    print("=" * 78)
    return 0


def main():
    p = argparse.ArgumentParser(description="Carga la nómina y crea el acceso de cada estudiante")
    p.add_argument("--nomina", default=NOMINA_POR_DEFECTO)
    p.add_argument("--credenciales", default=CREDENCIALES_POR_DEFECTO)
    p.add_argument("--plan", default="completo", choices=["completo", "incompleto", "vacio"])
    p.add_argument("--paralelo", default=None)
    p.add_argument("--curso", default="CONT1-AUD-ONLINE-P2-2026")
    p.add_argument("--reset-passwords", action="store_true",
                   help="vuelve a generar la contraseña inicial de todos")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    return importar(args.nomina, args.credenciales, plan=args.plan, paralelo=args.paralelo,
                    dry_run=args.dry_run, reset_passwords=args.reset_passwords, curso=args.curso)


if __name__ == "__main__":
    sys.exit(main())
