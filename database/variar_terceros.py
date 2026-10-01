"""Da identidad propia a la empresa de cada estudiante: clientes, proveedores y bancos.

Todos mantienen la MISMA estructura (mismo plan de cuentas, mismos 20 productos, 10 clientes,
8 proveedores y 2 cuentas bancarias), pero con datos propios: nombre, RUC/cédula, contacto,
cupo de crédito, plazos y número de cuenta. Así el trabajo es individual y verificable: nadie
puede copiar a un compañero porque las facturas, retenciones y estados no coinciden.

De paso deja en cero los saldos derivados (clientes, proveedores y bancos), que venían con las
cifras de la empresa de demostración.

    python database/variar_terceros.py               # informe (no escribe)
    python database/variar_terceros.py --aplicar     # aplica a todas las aulas
    python database/variar_terceros.py --aplicar --aula ealcivar4002

Los valores se derivan del nombre de usuario (SHA-256), así que son estables: repetirlo no los
mueve ni los acumula. La plantilla de aulas no se modifica.
"""
import argparse
import glob
import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

# --------------------------------------------------------------------- repertorio de nombres
GIROS_JURIDICOS = [
    ("Distribuidora", "Cía. Ltda."), ("Comercial", "S.A."), ("Supermercado", "S.A."),
    ("Almacén", "Cía. Ltda."), ("Importadora", "S.A."), ("Ferretería", "Cía. Ltda."),
    ("Farmacia", "Cía. Ltda."), ("Panificadora", "S.A."), ("Tienda de Barrio", "Cía. Ltda."),
    ("Bodega Mayorista", "S.A."), ("Autoservicio", "Cía. Ltda."), ("Minimarket", "S.A."),
    ("Comisariato", "Cía. Ltda."), ("Despensa Familiar", "S.A."), ("Depósito", "Cía. Ltda."),
]
NOMBRES_COMERCIALES = [
    "El Ahorro", "La Victoria", "San José", "Santa María", "El Rosado", "La Moderna",
    "El Portal", "Los Andes", "El Sol", "La Palmera", "San Francisco", "El Triunfo",
    "La Estrella", "Nueva Aurora", "El Mirador", "Los Álamos", "La Esperanza", "El Rocío",
    "San Pedro", "La Cumbre", "El Prado", "Los Cedros", "Villa Nueva", "La Floresta",
]
CIUDADES = ["Quito", "Guayaquil", "Cuenca", "Manta", "Portoviejo", "Ambato", "Machala",
            "Loja", "Santo Domingo", "Quevedo", "Latacunga", "Riobamba", "Esmeralda",
            "Ibarra", "Chone", "Jipijapa"]
NOMBRES_PILA = ["Carlos Alberto", "María Fernanda", "José Luis", "Ana Cristina",
                "Luis Eduardo", "Gabriela", "Miguel Ángel", "Rosa Elena", "Jorge Andrés",
                "Patricia", "Wilmer", "Andrea", "Freddy", "Ximena", "Byron", "Nathaly"]
APELLIDOS = ["Paredes Peña", "Zambrano Vélez", "Cedeño Bravo", "Moreira Macías",
             "Vera Intriago", "Loor Palacio", "Chávez Delgado", "Mendoza Pinargote",
             "García Arambulo", "Rivas Cárdenas", "Suárez Zambrano", "Ávila Mero",
             "Cantos Bermúdez", "Saltos Vera", "Ponce Quijije", "Macías Bravo"]
PROVEEDORES_BASE = [
    ("Agroindustrias del Litoral Cía. Ltda.", "ventas", "empresa"),
    ("Importadora Andina de Alimentos S.A.", "pedidos", "empresa"),
    ("Lácteos del Valle Cía. Ltda.", "comercial", "empresa"),
    ("Distribuidora Pacífico Sur S.A.", "distribucion", "empresa"),
    ("Aceites y Grasas del Ecuador Cía. Ltda.", "ventas", "empresa"),
    ("Servicios Contables Integrales Cía. Ltda.", "contacto", "servicios"),
    ("Transportes Rápidos del Ecuador S.A.", "operaciones", "servicios"),
    ("Consultoría Tributaria Austro Cía. Ltda.", "asesoria", "servicios"),
    ("Suministros Industriales Guayas S.A.", "ventas", "empresa"),
    ("Bebidas y Alimentos Nacionales Cía. Ltda.", "pedidos", "empresa"),
    ("Aseguradora Andina del Ecuador S.A.", "contacto", "servicios"),
    ("Tecnología y Servicios Quito Cía. Ltda.", "info", "servicios"),
]
DOMINIOS = ["com.ec", "ec", "mail.ec", "negocio.ec"]


def _azar(usuario, clave, minimo=0, maximo=999):
    dato = hashlib.sha256(("%s|%s" % (usuario, clave)).encode()).hexdigest()
    return minimo + int(dato[:8], 16) % (maximo - minimo + 1)


def _elige(lista, usuario, clave):
    return lista[_azar(usuario, clave, 0, len(lista) - 1)]


def _digitos_semilla(usuario, clave, cuantos):
    """Serie de dígitos determinista a partir del estudiante y la clave."""
    dato = hashlib.sha256(("%s|%s" % (usuario, clave)).encode()).hexdigest()
    numeros = "".join(str(int(c, 16) % 10) for c in dato)
    return numeros[:cuantos]


def _cedula_valida(usuario, clave):
    """Cédula de 10 dígitos con el dígito verificador del SRI (módulo 10)."""
    provincia = "%02d" % (1 + int(_digitos_semilla(usuario, clave + "-prov", 2)) % 24)
    cuerpo = provincia + _digitos_semilla(usuario, clave + "-cuerpo", 7)
    suma = 0
    for posicion, digito in enumerate(cuerpo):
        valor = int(digito) * (2 if posicion % 2 == 0 else 1)
        if valor > 9:
            valor -= 9
        suma += valor
    verificador = (10 - suma % 10) % 10
    return cuerpo + str(verificador)


def _ruc_juridica(usuario, clave):
    """RUC de 13 dígitos de una empresa, con el dígito verificador del SRI (módulo 11).

    Estructura: [provincia 2][9][6 dígitos][verificador][001] — el verificador es el dígito 10 y
    se calcula con los coeficientes 4,3,2,7,6,5,4,3,2 sobre los nueve primeros dígitos.
    """
    provincia = "%02d" % (1 + int(_digitos_semilla(usuario, clave + "-prov", 2)) % 24)
    base = provincia + "9" + _digitos_semilla(usuario, clave + "-cuerpo", 6)   # 9 dígitos
    pesos = [4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(d) * p for d, p in zip(base, pesos))
    verificador = 11 - suma % 11
    if verificador >= 10:          # 11 -> 0 y 10 -> 0, como en el RUC de sociedades
        verificador = 0
    return base + str(verificador) + "001"


def identificacion(usuario, clave, juridica):
    """RUC de empresa, RUC de persona natural o cédula, según corresponda."""
    if juridica:
        return _ruc_juridica(usuario, clave)
    return _cedula_valida(usuario, clave)


def _orden_determinista(usuario, cantidad, sal):
    """Orden estable y único de los índices 0..cantidad-1 para ese estudiante."""
    return sorted(range(cantidad), key=lambda indice: hashlib.sha256(
        ("%s|%s|%d" % (usuario, sal, indice)).encode()).hexdigest())


def nombre_empresa(usuario):
    """Razón social y nombre comercial propios; la ciudad garantiza que no se repitan."""
    combos = _orden_determinista(usuario, len(GIROS_JURIDICOS) * len(NOMBRES_COMERCIALES), "emp")
    giro, tipo = GIROS_JURIDICOS[combos[0] % len(GIROS_JURIDICOS)]
    marca = NOMBRES_COMERCIALES[(combos[0] // len(GIROS_JURIDICOS)) % len(NOMBRES_COMERCIALES)]
    ciudad = _elige(CIUDADES, usuario, "emp-ciudad")
    return ("%s %s de %s %s" % (giro, marca, ciudad, tipo), "%s %s de %s" % (giro, marca, ciudad))


def catalogo_base():
    """Empresa, clientes, proveedores, bancos y cuentas de un seed limpio."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temporal = tempfile.mkdtemp(prefix="base_terceros_")
    referencia = os.path.join(temporal, "simulator.db")
    proceso = subprocess.run([sys.executable, os.path.join(raiz, "database", "seed_data.py")],
                             env=dict(os.environ, DATABASE_PATH=referencia),
                             capture_output=True, text=True)
    if not os.path.exists(referencia):
        raise SystemExit("No se pudo generar la base de referencia:\n%s"
                         % ((proceso.stdout or "") + (proceso.stderr or ""))[-400:])
    conexion = sqlite3.connect(referencia)
    conexion.row_factory = sqlite3.Row
    try:
        datos = {}
        for tabla in ("clientes", "proveedores", "bancos", "cuentas"):
            datos[tabla] = [dict(f) for f in conexion.execute("SELECT * FROM %s" % tabla)]
        datos["empresa"] = dict(conexion.execute("SELECT * FROM empresas WHERE id = 1").fetchone())
        return datos
    finally:
        conexion.close()


def _cliente(usuario, indice, plantilla=None):
    """Cliente propio del estudiante; dentro de un aula los nombres no se repiten."""
    orden = _orden_determinista(usuario, len(GIROS_JURIDICOS) * len(NOMBRES_COMERCIALES), "cli")
    posicion = orden[(indice - 1) % len(orden)]
    juridica = indice % 3 != 2          # dos de cada tres son empresas, como en la base
    clave = "cliente-%d" % indice
    if juridica:
        giro, tipo = GIROS_JURIDICOS[posicion % len(GIROS_JURIDICOS)]
        nombre = "%s %s %s" % (giro, NOMBRES_COMERCIALES[(posicion // len(GIROS_JURIDICOS)) % len(NOMBRES_COMERCIALES)], tipo)
    else:
        personas = _orden_determinista(usuario, len(NOMBRES_PILA) * len(APELLIDOS), "per")
        p = personas[(indice - 1) % len(personas)]
        nombre = "%s %s" % (NOMBRES_PILA[p % len(NOMBRES_PILA)],
                            APELLIDOS[(p // len(NOMBRES_PILA)) % len(APELLIDOS)])
    ciudad = _elige(CIUDADES, usuario, clave + "-ciudad")
    dominio = _elige(DOMINIOS, usuario, clave + "-dom")
    return {
        "identificacion": identificacion(usuario, clave, juridica),
        "nombre_razon_social": nombre,
        "email": "%s%d@%s" % ("contacto" if juridica else "cliente",
                              _azar(usuario, clave + "-num", 10, 999), dominio),
        "telefono": "0%d-%04d-%03d" % (_azar(usuario, clave + "-prov", 2, 9),
                                       _azar(usuario, clave + "-t1", 2000, 3999),
                                       _azar(usuario, clave + "-t2", 100, 999)),
        "direccion": "%s, %s" % (_elige(["Av. Principal", "Calle 10 de Agosto", "Av. Amazonas",
                                         "Calle Sucre", "Av. Los Shyris", "Calle Bolívar",
                                         "Av. Malecón", "Calle Olmedo"],
                                        usuario, clave + "-via"),
                                 ciudad),
        "limite_credito": float(_azar(usuario, clave + "-lim", 15, 150)) * 100,
        "dias_credito": _elige([15, 30, 45, 60], usuario, clave + "-dias"),
        "saldo_pendiente": 0.0,
        "activo": 1,
    }


def _proveedor(usuario, indice, plantilla=None):
    """Proveedor propio del estudiante; los 8 son distintos entre sí."""
    orden = _orden_determinista(usuario, len(PROVEEDORES_BASE), "prov")
    nombre, correo, giro = PROVEEDORES_BASE[orden[(indice - 1) % len(orden)]]
    ciudades = _orden_determinista(usuario, len(CIUDADES), "ciud")
    ciudad = CIUDADES[ciudades[(indice - 1) % len(ciudades)]]
    clave = "proveedor-%d" % indice
    return {
        "identificacion": identificacion(usuario, clave, True),
        "razon_social": nombre.replace(" del Litoral", " del %s" % ciudad)
                             .replace(" del Austro", " del %s" % ciudad)
                             .replace(" Quito", " %s" % ciudad)
                             .replace(" Guayas", " %s" % ciudad),
        "email": "%s@%s" % (correo, _elige(DOMINIOS, usuario, clave + "-dom")),
        "telefono": "0%d-%04d-%03d" % (_azar(usuario, clave + "-prov", 2, 9),
                                       _azar(usuario, clave + "-t1", 2000, 3999),
                                       _azar(usuario, clave + "-t2", 100, 999)),
        "direccion": "%s, %s" % (_elige(["Km 5 vía a Daule", "Parque Industrial", "Av. Industrial",
                                         "Calle Los Cerezos", "Zona Franca"],
                                        usuario, clave + "-via"),
                                 ciudad),
        "dias_credito": _elige([15, 30, 45], usuario, clave + "-dias"),
        "saldo_pendiente": 0.0,
        "activo": 1,
    }


def aplicar_en(ruta, base, usuario, escribir=False):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    cambios = 0
    try:
        # --- la empresa del estudiante ---
        razon, comercial = nombre_empresa(usuario)
        empresa = {
            "ruc": identificacion(usuario, "empresa", True),
            "razon_social": "%s S.A." % razon.replace(" S.A.", "").replace(" Cía. Ltda.", ""),
            "nombre_comercial": comercial,
            "direccion": "%s, %s" % (_elige(["Av. 9 de Octubre", "Av. Naciones Unidas",
                                             "Calle 5 de Junio", "Av. Circunvalación"],
                                            usuario, "emp-dir"),
                                     _elige(CIUDADES, usuario, "emp-ciudad")),
            "telefono": "0%d-%04d-%03d" % (_azar(usuario, "emp-prov", 2, 9),
                                           _azar(usuario, "emp-t1", 2000, 3999),
                                           _azar(usuario, "emp-t2", 100, 999)),
            "email": "info@%s" % _elige(DOMINIOS, usuario, "emp-dom"),
        }
        actual = conexion.execute("SELECT * FROM empresas WHERE id = 1").fetchone()
        for campo, valor in empresa.items():
            if actual and (actual[campo] or "") != valor:
                cambios += 1
                if escribir:
                    conexion.execute("UPDATE empresas SET %s = ? WHERE id = 1" % campo, (valor,))

        # --- clientes ---
        for indice, fila in enumerate(conexion.execute("SELECT id FROM clientes ORDER BY id"), start=1):
            nuevo = _cliente(usuario, indice, False)
            actual = conexion.execute("SELECT * FROM clientes WHERE id = ?", (fila["id"],)).fetchone()
            for campo, valor in nuevo.items():
                if actual and (actual[campo] or "") != valor:
                    cambios += 1
                    if escribir:
                        conexion.execute("UPDATE clientes SET %s = ? WHERE id = ?" % campo,
                                         (valor, fila["id"]))

        # --- proveedores ---
        for indice, fila in enumerate(conexion.execute("SELECT id FROM proveedores ORDER BY id"), start=1):
            nuevo = _proveedor(usuario, indice, False)
            actual = conexion.execute("SELECT * FROM proveedores WHERE id = ?", (fila["id"],)).fetchone()
            for campo, valor in nuevo.items():
                if actual and (actual[campo] or "") != valor:
                    cambios += 1
                    if escribir:
                        conexion.execute("UPDATE proveedores SET %s = ? WHERE id = ?" % campo,
                                         (valor, fila["id"]))

        # --- bancos: cuentas propias y saldo en cero ---
        cuentas = {}
        for indice, fila in enumerate(conexion.execute("SELECT * FROM bancos ORDER BY id"), start=1):
            numero = "%010d" % _azar(usuario, "banco-%d" % indice, 1000000000, 9999999999)
            cuentas[fila["id"]] = numero
            if fila["numero_cuenta"] != numero or float(fila["saldo_actual"] or 0) != 0.0:
                cambios += 1
                if escribir:
                    conexion.execute("UPDATE bancos SET numero_cuenta = ?, saldo_actual = 0 "
                                     "WHERE id = ?", (numero, fila["id"]))
                    if fila["cuenta_contable_id"]:
                        actual = conexion.execute("SELECT nombre FROM cuentas WHERE id = ?",
                                                  (fila["cuenta_contable_id"],)).fetchone()
                        if actual:
                            import re
                            nombre = re.sub(r"\d{6,}", numero, actual["nombre"])
                            conexion.execute("UPDATE cuentas SET nombre = ? WHERE id = ?",
                                             (nombre, fila["cuenta_contable_id"]))

        if escribir:
            conexion.commit()
    finally:
        conexion.close()
    return cambios


def main():
    analizador = argparse.ArgumentParser(
        description="Da identidad propia a la empresa, clientes, proveedores y bancos de cada estudiante.")
    analizador.add_argument("--aplicar", action="store_true", help="escribe los cambios")
    analizador.add_argument("--aula", help="solo este estudiante")
    argumentos = analizador.parse_args()

    base = catalogo_base()
    print("Base de referencia: %d clientes, %d proveedores, %d bancos"
          % (len(base["clientes"]), len(base["proveedores"]), len(base["bancos"])))
    print("Modo: %s\n" % ("APLICAR" if argumentos.aplicar else "solo informe (agregue --aplicar)"))

    rutas = sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "B", "*.db")))
    if argumentos.aula:
        usuario = argumentos.aula.split("@")[0]
        rutas = [r for r in rutas if os.path.basename(r) == "%s.db" % usuario]
        if not rutas:
            raise SystemExit("No encontré el aula de %s" % usuario)

    print("%-22s %8s   %-42s %s" % ("ESTUDIANTE", "CAMBIOS", "SU EMPRESA", "RUC"))
    print("-" * 92)
    total = 0
    for ruta in rutas[:8]:
        usuario = os.path.basename(ruta)[:-3]
        cambios = aplicar_en(ruta, base, usuario, escribir=argumentos.aplicar)
        razon, comercial = nombre_empresa(usuario)
        print("%-22s %8d   %-42s %s" % (usuario, cambios, comercial[:42],
                                        identificacion(usuario, "empresa", True)))
    for ruta in rutas[8:]:
        usuario = os.path.basename(ruta)[:-3]
        cambios = aplicar_en(ruta, base, usuario, escribir=argumentos.aplicar)
        total += cambios
    if rutas:
        print("-" * 92)
        print("Aulas revisadas: %d %s" % (len(rutas), "(los conteos de arriba son los 8 primeros)"))
    if argumentos.aplicar:
        print("\nAplicado. Los datos son estables: repetirlo no los mueve.")
    else:
        print("\nEjecute con --aplicar para escribir los datos.")


if __name__ == "__main__":
    sys.exit(main() or 0)
