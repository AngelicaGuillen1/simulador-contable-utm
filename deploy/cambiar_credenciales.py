#!/usr/bin/env python
"""
Cambia la contraseña de un usuario del Simulador Contable.

Obligatorio antes de publicar el sistema en Internet: las cuentas de demostración
(admin, docente, estudiante, auditor) traen contraseñas conocidas.

La contraseña se escribe de forma oculta, nunca se muestra, no se guarda en el historial
del shell y se almacena con hash Werkzeug (igual que el resto del sistema).

Uso:
    python deploy/cambiar_credenciales.py                 # menú interactivo
    python deploy/cambiar_credenciales.py --usuario admin # cambia solo ese usuario
    python deploy/cambiar_credenciales.py --listar        # muestra usuarios existentes
"""

import argparse
import getpass
import os
import sqlite3
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from werkzeug.security import generate_password_hash  # noqa: E402
from config import Config  # noqa: E402

LONGITUD_MINIMA = 10


def usuarios():
    conexion = sqlite3.connect(Config.DATABASE_PATH)
    conexion.row_factory = sqlite3.Row
    try:
        return conexion.execute(
            "SELECT u.id, u.username, u.nombre_completo, r.nombre AS rol "
            "FROM usuarios u LEFT JOIN roles r ON r.id = u.rol_id ORDER BY u.id"
        ).fetchall()
    finally:
        conexion.close()


def cambiar(username, nueva):
    conexion = sqlite3.connect(Config.DATABASE_PATH)
    try:
        fila = conexion.execute("SELECT id FROM usuarios WHERE username = ?", (username,)).fetchone()
        if not fila:
            raise SystemExit(f"No existe el usuario '{username}'.")
        conexion.execute(
            "UPDATE usuarios SET password_hash = ? WHERE username = ?",
            (generate_password_hash(nueva), username),
        )
        conexion.commit()
        print(f"Contraseña actualizada para '{username}'. Cierre las sesiones abiertas de ese usuario.")
    finally:
        conexion.close()


def pedir_contrasena():
    while True:
        primera = getpass.getpass("Nueva contraseña: ")
        if len(primera) < LONGITUD_MINIMA:
            print(f"Debe tener al menos {LONGITUD_MINIMA} caracteres. Intente de nuevo.")
            continue
        segunda = getpass.getpass("Repita la nueva contraseña: ")
        if primera != segunda:
            print("Las contraseñas no coinciden. Intente de nuevo.")
            continue
        return primera


def main():
    parser = argparse.ArgumentParser(description="Cambio de contraseñas del simulador")
    parser.add_argument("--usuario", help="usuario a modificar")
    parser.add_argument("--listar", action="store_true", help="mostrar los usuarios existentes")
    args = parser.parse_args()

    registros = usuarios()
    if not registros:
        raise SystemExit("No hay usuarios en la base de datos.")

    if args.listar:
        for fila in registros:
            print(f"  {fila['id']:>3}  {fila['username']:<12} {fila['rol'] or '(sin rol)':<16} {fila['nombre_completo']}")
        return

    if args.usuario:
        cambiar(args.usuario, pedir_contrasena())
        return

    print("Usuarios disponibles:")
    for fila in registros:
        print(f"  {fila['id']:>3}  {fila['username']:<12} {fila['rol'] or '(sin rol)':<16} {fila['nombre_completo']}")

    while True:
        usuario = input("\nUsuario a modificar (vacío para terminar): ").strip()
        if not usuario:
            break
        if not any(fila["username"] == usuario for fila in registros):
            print(f"  '{usuario}' no existe en la lista.")
            continue
        cambiar(usuario, pedir_contrasena())


if __name__ == "__main__":
    main()
