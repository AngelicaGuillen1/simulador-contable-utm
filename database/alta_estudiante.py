"""Da de alta a un estudiante nuevo con todo lo que necesita, en un solo paso.

Hace lo que antes se hacía a mano: crea su cuenta en la base de control (con la clave que se le
entregará), le construye su propia aula a partir de la plantilla, le asigna las 6 actividades del
syllabus y le aplica sus datos propios (cifras del catálogo, identidad de su empresa, clientes,
proveedores, cuentas bancarias y cifras de los 19 casos). Al final muestra el resumen y deja la
clave registrada en la lista del paralelo.

En el servidor se usa con --servidor: crea la cuenta y el aula, sin tocar listas locales.

    python database/alta_estudiante.py --nombre "Perez Lopez Ana Maria" --cedula 1312345678 \
        --correo aperez5678@utm.edu.ec
    python database/alta_estudiante.py --borrar aperez5678
"""
import argparse
import csv
import glob
import os
import random
import secrets
import shutil
import sqlite3
import string
import subprocess
import sys
import tempfile
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

LETRAS = string.ascii_uppercase + string.digits
SIN_AMBIGUAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"      # sin O/0 ni I/1: se leen por teléfono


def generar_clave():
    """Clave con el mismo formato de la lista: ABCD-EFGH."""
    bloques = ["".join(secrets.choice(SIN_AMBIGUAS) for _ in range(4)) for _ in range(2)]
    return "-".join(bloques)


def usuario_desde_correo(correo):
    return (correo or "").split("@")[0].strip().lower()


def usuario_desde_nombre(nombre, cedula):
    """Mismo patrón que la nómina: inicial del nombre + primer apellido + 4 dígitos de la cédula.

    Las listas de la UTM vienen como «APELLIDO APELLIDO NOMBRE NOMBRE»: la inicial sale del
    primer nombre (tercer bloque) y el apellido del primer bloque, como en `ecarreno3182`.
    """
    limpio = unicodedata.normalize("NFKD", nombre or "")
    limpio = "".join(c for c in limpio if not unicodedata.combining(c)).lower()
    partes = [p for p in limpio.replace(",", " ").split() if p]
    if not partes:
        return (cedula or "")[-4:]
    if len(partes) >= 3:                 # apellido apellido nombre ...
        inicial, apellido = partes[2][0], partes[0]
    elif len(partes) == 2:               # apellido nombre
        inicial, apellido = partes[1][0], partes[0]
    else:
        inicial, apellido = partes[0][0], partes[0]
    return "%s%s%s" % (inicial, apellido, (cedula or "")[-4:])


def titulo(nombre):
    return " ".join(p.capitalize() for p in (nombre or "").split())


def nombre_presentable(nombre):
    partes = (nombre or "").split()
    if len(partes) >= 3:                  # "Apellido Apellido Nombre Nombre" -> "Nombre Apellido"
        return "%s %s" % (" ".join(partes[2:]), " ".join(partes[:2]))
    return titulo(nombre)


def rutas_de_listas():
    """Ubicación de las listas del paralelo (fuera del repositorio)."""
    return (os.path.join(os.path.expanduser("~"), "Desktop", "2026", "S2", "Clases", "Contabilidad 1",
                         "credenciales_paralelo_B.csv"),
            os.path.join(os.path.expanduser("~"), "Desktop", "2026", "S2", "Clases", "Contabilidad 1",
                         "claves_para_moodle.txt"))


def registrar_en_listas(correo, clave, nombre, usuario, cedula, paralelo="B",
                        ruta_csv=None, ruta_moodle=None):
    """Añade el estudiante a la lista del paralelo y al archivo para Moodle.

    Respeta el formato real de los archivos: la lista del paralelo lleva ocho columnas
    (paralelo, usuario, nombre, cédula, correo, clave, aula, estado) y el archivo de Moodle tres
    campos separados por tabulador (usuario, clave, nombre).
    """
    escritos = []
    ruta_csv_predeterminada, ruta_moodle_predeterminada = rutas_de_listas()
    ruta_csv = ruta_csv or ruta_csv_predeterminada
    ruta_moodle = ruta_moodle or ruta_moodle_predeterminada
    nombre_lista = titulo(nombre)          # mismo estilo de la lista: Apellido Apellido Nombre

    if os.path.exists(ruta_csv):
        with open(ruta_csv, encoding="utf-8") as archivo:
            cabecera = next(csv.reader(archivo), None)
        if not cabecera:
            cabecera = ["paralelo", "usuario", "nombre", "cedula", "correo", "password_inicial",
                        "aula", "estado"]
        valores = {
            "paralelo": paralelo, "usuario": usuario, "nombre": nombre_lista, "cedula": cedula,
            "correo": correo, "password_inicial": clave, "clave": clave,
            "aula": "%s.db" % usuario, "estado": "vigente",
        }
        with open(ruta_csv, "a", encoding="utf-8", newline="") as archivo:
            csv.writer(archivo).writerow([valores.get(c, "") for c in cabecera])
        escritos.append(os.path.basename(ruta_csv))

    if os.path.exists(ruta_moodle):
        with open(ruta_moodle, encoding="utf-8") as archivo:
            contenido = archivo.read().splitlines()
        cabecera = contenido[0] if contenido else "usuario\tclave\tnombre"
        with open(ruta_moodle, "a", encoding="utf-8") as archivo:
            archivo.write("%s\t%s\t%s\n" % (correo, clave, nombre_lista))
        escritos.append(os.path.basename(ruta_moodle))
    return escritos


def existe_usuario(usuario):
    conexion = sqlite3.connect(Config.DATABASE_PATH)
    conexion.row_factory = sqlite3.Row
    try:
        return conexion.execute("SELECT id FROM usuarios WHERE username = ?", (usuario,)).fetchone()
    finally:
        conexion.close()


def ruta_aula(usuario, paralelo="B"):
    return os.path.join(Config.RUTA_AULAS, paralelo, "%s.db" % usuario)


def resumen(usuario, paralelo="B"):
    ruta = ruta_aula(usuario, paralelo)
    if not os.path.exists(ruta):
        return None
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    try:
        empresa = conexion.execute("SELECT razon_social, ruc FROM empresas LIMIT 1").fetchone()
        return {
            "empresa": empresa["razon_social"] if empresa else "?",
            "ruc": empresa["ruc"] if empresa else "?",
            "cuentas": conexion.execute("SELECT COUNT(*) FROM cuentas").fetchone()[0],
            "productos": conexion.execute("SELECT COUNT(*) FROM productos").fetchone()[0],
            "clientes": conexion.execute("SELECT COUNT(*) FROM clientes").fetchone()[0],
            "actividades": conexion.execute("SELECT COUNT(*) FROM actividades").fetchone()[0],
            "casos": conexion.execute("SELECT COUNT(*) FROM casos_simulacion").fetchone()[0],
            "inventario": conexion.execute(
                "SELECT COALESCE(SUM(stock_actual * costo_unitario), 0) FROM productos").fetchone()[0],
        }
    finally:
        conexion.close()


def aplicar_datos_propios(usuario):
    """Catálogo, identidad de la empresa, terceros, textos y casos: todo propio del estudiante."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python = sys.executable
    for guion in ("variar_catalogos.py", "variar_terceros.py", "actualizar_texto_actividades.py",
                  "variar_casos.py"):
        ruta = os.path.join(raiz, "database", guion)
        proceso = subprocess.run([python, ruta, "--aplicar", "--aula", usuario],
                                 capture_output=True, text=True, cwd=raiz)
        estado = "ok" if proceso.returncode == 0 else "falló"
        print("      %-32s %s" % (guion, estado))
        if proceso.returncode != 0:
            print("      %s" % (proceso.stdout or proceso.stderr or "")[-400:])


def alta(nombre, cedula, correo, clave, paralelo, curso, servidor):
    from database.importar_nomina import importar
    from database.crear_aula import crear_aula

    usuario = usuario_desde_correo(correo) or usuario_desde_nombre(nombre, cedula)
    correo = correo or "%s@utm.edu.ec" % usuario
    clave = clave or generar_clave()

    print("   Estudiante: %s" % nombre_presentable(nombre))
    print("   Usuario   : %s   (correo institucional)" % usuario)
    print("   Correo    : %s" % correo)
    print("   Paralelo  : %s | curso: %s" % (paralelo, curso or "(el del proyecto)"))
    print()

    with tempfile.TemporaryDirectory(prefix="alta_") as temporal:
        nomina = os.path.join(temporal, "nomina.csv")
        with open(nomina, "w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["usuario", "correo", "nombre", "cedula", "paralelo",
                               "password_inicial"])
            escritor.writerow([usuario, correo, nombre, cedula, paralelo, clave])
        credenciales = os.path.join(temporal, "credenciales.csv")
        print("   1/4 cuenta en la base de control")
        codigo = importar(nomina, credenciales, paralelo=paralelo, curso=curso)
        if codigo:
            print("   [ERROR] no se pudo crear la cuenta")
            return 1

    fila = existe_usuario(usuario)
    estudiante_id = fila["id"] if fila else None

    print("   2/4 aula propia del estudiante")
    crear_aula(usuario, paralelo=paralelo, estudiante_id=estudiante_id)
    if not os.path.exists(ruta_aula(usuario, paralelo)):
        print("   [ERROR] no se pudo crear el aula en %s" % ruta_aula(usuario, paralelo))
        return 1

    print("   3/4 datos propios (valores, empresa, terceros, textos y casos)")
    aplicar_datos_propios(usuario)

    print("   4/4 resumen")
    datos = resumen(usuario, paralelo)
    if not datos:
        print("   [ERROR] no encontré el aula recién creada")
        return 1
    print("      empresa    : %s (%s)" % (datos["empresa"], datos["ruc"]))
    print("      estructura : %d cuentas, %d productos, %d clientes, %d actividades, %d casos"
          % (datos["cuentas"], datos["productos"], datos["clientes"], datos["actividades"],
             datos["casos"]))
    print("      inventario : $%.2f" % datos["inventario"])

    if not servidor:
        escritos = registrar_en_listas(correo, clave, nombre, usuario, cedula, paralelo)
        print()
        print("   Clave entregada al estudiante: guardada en %s"
              % (", ".join(escritos) if escritos else "(no encontré las listas locales)"))
        print("   La clave no se muestra aquí a propósito: está en su lista.")
    else:
        print()
        print("   Cuenta creada en el servidor con la clave indicada.")
    return 0


def borrar(usuario, paralelo="B"):
    """Elimina la cuenta y el aula (para una baja o una prueba)."""
    borrados = []
    ruta = ruta_aula(usuario, paralelo)
    if os.path.exists(ruta):
        os.remove(ruta)
        borrados.append(os.path.basename(ruta))
    conexion = sqlite3.connect(Config.DATABASE_PATH)
    try:
        conexion.execute("DELETE FROM usuarios WHERE username = ?", (usuario,))
        conexion.commit()
        borrados.append("cuenta de control")
    finally:
        conexion.close()
    # En el servidor las aulas también viven en /var/datos/aulas
    for patron in (os.path.join(Config.RUTA_AULAS, "*", "%s.db" % usuario),):
        for ruta_extra in glob.glob(patron):
            if os.path.exists(ruta_extra):
                shutil.copy(ruta_extra, ruta_extra + ".borrado")
                os.remove(ruta_extra)
    print("   Eliminado: %s" % ", ".join(borrados))
    return 0


def main():
    analizador = argparse.ArgumentParser(description="Alta (o baja) de un estudiante nuevo.")
    analizador.add_argument("--nombre", help="nombre completo tal como viene en la lista")
    analizador.add_argument("--cedula", help="cédula (10 dígitos)")
    analizador.add_argument("--correo", help="correo institucional (define el usuario)")
    analizador.add_argument("--usuario", help="usuario, si se conoce sin el correo")
    analizador.add_argument("--clave", help="clave a usar (si se omite, se genera)")
    analizador.add_argument("--paralelo", default="B")
    analizador.add_argument("--curso", default="CONT-AUD-2026-P2",
                            help="código del curso en la base de control")
    analizador.add_argument("--servidor", action="store_true",
                            help="alta en el servidor: no toca las listas locales")
    analizador.add_argument("--borrar", metavar="USUARIO", help="elimina la cuenta y el aula")
    argumentos = analizador.parse_args()

    if argumentos.borrar:
        return borrar(argumentos.borrar.split("@")[0], argumentos.paralelo)
    if not argumentos.nombre and not argumentos.usuario:
        raise SystemExit("Indique --nombre y --cedula (y --correo si ya lo tiene).")

    usuario = (argumentos.usuario or "").split("@")[0].strip().lower()
    if not usuario:
        usuario = usuario_desde_correo(argumentos.correo) or usuario_desde_nombre(
            argumentos.nombre, argumentos.cedula)
    if existe_usuario(usuario):
        print("   [AVISO] %s ya existe: se actualizarán sus datos y su aula, sin perder su trabajo."
              % usuario)
    if not argumentos.cedula and not argumentos.usuario:
        raise SystemExit("Falta la cédula: define el usuario (inicial + apellido + 4 dígitos).")
    return alta(argumentos.nombre or usuario, argumentos.cedula or "", argumentos.correo or "",
                argumentos.clave, argumentos.paralelo.upper(), argumentos.curso,
                argumentos.servidor)


if __name__ == "__main__":
    sys.exit(main() or 0)
