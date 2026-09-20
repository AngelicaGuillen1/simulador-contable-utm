"""Fija la contraseña de un usuario del simulador (docente, admin, auditor...).

La clave se genera al azar o se lee de un archivo, **nunca se escribe en la línea de
comandos**, así no queda en el historial del shell ni en los registros del servidor.

Uso:
    # Genera una clave nueva, la guarda en un archivo y la aplica
    python deploy/fijar_clave.py --usuario docente --generar --archivo C:/ruta/clave_docente.txt

    # Aplica la clave que está en un archivo (por ejemplo en el servidor)
    python deploy/fijar_clave.py --usuario docente --archivo /ruta/clave_docente.txt

    # Comprueba qué clave del archivo abre la cuenta (sin mostrarla)
    python deploy/fijar_clave.py --usuario docente --comprobar --archivo C:/ruta/clave_docente.txt
"""
import argparse
import os
import secrets
import sqlite3
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from werkzeug.security import check_password_hash, generate_password_hash  # noqa: E402
from config import Config  # noqa: E402

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ123456789"  # sin O, I, 0, L (se confunden al dictar)


def generar_clave():
    """Clave del tipo XXXX-XXXX, fácil de dictar por teléfono."""
    partes = ["".join(secrets.choice(ALFABETO) for _ in range(4)) for _ in (0, 1)]
    return "%s-%s" % tuple(partes)


def conexion():
    con = sqlite3.connect(Config.DATABASE_PATH)
    con.row_factory = sqlite3.Row
    return con


def buscar(con, usuario):
    return con.execute(
        "SELECT id, username, email, nombre_completo, password_hash FROM usuarios "
        "WHERE username = ? OR email = ?", (usuario, usuario)).fetchone()


def main():
    analizador = argparse.ArgumentParser(description="Fija la contraseña de un usuario del simulador.")
    analizador.add_argument("--usuario", required=True, help="usuario o correo")
    analizador.add_argument("--generar", action="store_true", help="genera una clave nueva")
    analizador.add_argument("--archivo", required=True, help="archivo donde guardar/leer la clave")
    analizador.add_argument("--comprobar", action="store_true", help="solo comprueba si la clave del archivo abre la cuenta")
    argumentos = analizador.parse_args()

    con = conexion()
    try:
        fila = buscar(con, argumentos.usuario)
        if not fila:
            raise SystemExit("No existe el usuario %s en %s" % (argumentos.usuario, Config.DATABASE_PATH))
        print("Usuario: %s (%s) | %s" % (fila["username"], fila["email"], fila["nombre_completo"]))

        if argumentos.generar:
            clave = generar_clave()
            with open(argumentos.archivo, "w", encoding="utf-8") as salida:
                salida.write(clave + "\n")
            try:
                os.chmod(argumentos.archivo, 0o600)
            except OSError:
                pass
            con.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?",
                        (generate_password_hash(clave), fila["id"]))
            con.commit()
            print("Clave nueva aplicada y guardada en: %s" % argumentos.archivo)
        else:
            if not os.path.exists(argumentos.archivo):
                raise SystemExit("No está el archivo de la clave: %s" % argumentos.archivo)
            with open(argumentos.archivo, encoding="utf-8") as entrada:
                clave = entrada.read().strip().splitlines()[0].strip()

            if check_password_hash(fila["password_hash"], clave):
                print("La clave del archivo SÍ abre esta cuenta en %s" % Config.DATABASE_PATH)
                return 0
            if argumentos.comprobar:
                print("La clave del archivo NO abre esta cuenta en %s" % Config.DATABASE_PATH)
                return 3
            con.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?",
                        (generate_password_hash(clave), fila["id"]))
            con.commit()
            print("Clave del archivo aplicada en %s" % Config.DATABASE_PATH)
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
