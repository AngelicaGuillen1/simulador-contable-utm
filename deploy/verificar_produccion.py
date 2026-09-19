#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verificador FUNCIONAL de produccion del Simulador Integral de Sistema Contable (UTM).

Comprueba, contra el servidor EN MARCHA (por defecto http://127.0.0.1:8080), 11 puntos
funcionales del aula virtual, cada uno con EVIDENCIA numerica real (HTTP y archivos .db):

   1. Acceso individual .......... dos estudiantes reales del CSV entran a SU propia aula
   2. Aislamiento entre estudiantes  lo de A no aparece en el aula de B (HTTP y .db)
   3. Panel docente .............. el docente ve los libros en SOLO LECTURA y no puede escribir
   4. Registro de ingresos ....... cada inicio de sesion queda en sesiones_usuario/eventos_estudiante
   5. Actividades ................ el estudiante ve sus actividades asignadas y su avance
   6. Evidencias ................. se crea una evidencia y se recupera con su codigo
   7. Trazabilidad ............... un intento rechazado queda registrado como intento fallido
   8. Libro Diario ............... 200 y asientos con Debe = Haber
   9. Libro Mayor ................ 200 con movimientos y saldos
  10. Balance de comprobacion .... 200 y sumas de Debe = sumas de Haber
  11. Estados financieros ........ estado de resultados y situacion financiera 200 y
                                   Activo = Pasivo + Patrimonio

Uso:
    .venv/Scripts/python.exe deploy/verificar_produccion.py
    .venv/Scripts/python.exe deploy/verificar_produccion.py --base http://127.0.0.1:8080
    .venv/Scripts/python.exe deploy/verificar_produccion.py --csv "C:\\ruta\\credenciales.csv"
    .venv/Scripts/python.exe deploy/verificar_produccion.py --forzar-asiento-prueba
    .venv/Scripts/python.exe deploy/verificar_produccion.py --sin-limpieza

Salida: codigo 0 si los 11 puntos pasan; 1 si alguno falla (o si el servidor no responde).

Notas de diseno:
  * Solo usa la libreria estandar (urllib + http.cookiejar + sqlite3): no requiere requests.
  * Las claves de los estudiantes NUNCA se imprimen: solo se muestra el usuario (clave oculta).
  * Elige los dos estudiantes leyendo sus aulas por archivo: el de MAS asientos para la evidencia
    contable (puntos 8 a 11) y el de MENOS para el aislamiento, de modo que ninguna comprobacion
    dependa de datos ajenos. Si el aula elegida no tuviera ningun asiento, registra UN asiento
    marcado VERIFICACION-PROD con la propia fecha de trabajo, lo verifica y lo borra al terminar.
  * Los datos de prueba llevan el marcador VERIFICACION-PROD y se BORRAN al terminar
    (salvo --sin-limpieza), para poder ejecutarlo muchas veces sin dejar basura. Lo unico que
    permanece es el rastro real de accesos (sesiones_usuario/eventos_estudiante) que el propio
    punto 4 comprueba.
  * Los endpoints de /contabilidad y /estados-financieros son de solo HTML (no aceptan
    ?formato=json); por eso los numeros se leen de /reportes/exportar/csv/<tipo>, que sirve el
    mismo contenido autenticado del aula del estudiante, y se contrastan con el archivo .db.
"""

import argparse
import csv
import http.cookiejar
import io
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

try:  # consola de Windows con acentos
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

MARCADOR = "VERIFICACION-PROD"
CODIGO_CUENTA_PRUEBA = "9.9.99"
NOMBRE_CUENTA_PRUEBA = "Cuenta de prueba VERIFICACION-PROD"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_POR_DEFECTO = os.path.join(
    os.path.expanduser("~"), "Desktop", "2026", "S2", "Clases", "Contabilidad 1",
    "credenciales_paralelo_B.csv")
MOMENTO = datetime.now().strftime("%Y%m%d-%H%M%S")
TITULO_EVIDENCIA = "%s evidencia funcional %s" % (MARCADOR, MOMENTO)
GLOSA_DESCUADRADA = "%s intento de asiento descuadrado %s" % (MARCADOR, MOMENTO)


# =========================================================================== utilidades
def _uri_ro(ruta):
    """URI SQLite en modo lectura (nunca escribe en las bases del sistema)."""
    ruta = os.path.abspath(ruta)
    seguro = ruta.replace("\\", "/").replace("?", "%3f").replace("#", "%23")
    if not seguro.startswith("/"):
        seguro = "/" + seguro
    return "file:%s?mode=ro" % seguro


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    """Evita seguir redirecciones: permite observar el 302/301 real de la aplicacion."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Cliente:
    """Sesion HTTP con cookies de la aplicacion (dos openers que comparten el mismo cookie jar)."""

    def __init__(self, base, seguir_redirecciones=True):
        self.base = base.rstrip("/")
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies))
        self.opener_sin = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies), _SinRedireccion())

    def pedir(self, ruta, datos=None, metodo=None, seguir=True):
        url = self.base + ruta
        cuerpo = urllib.parse.urlencode(datos, doseq=True).encode() if datos is not None else None
        cabeceras = {"User-Agent": "verificador-produccion/1.0", "Accept-Language": "es"}
        pet = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method=metodo)
        opener = self.opener if seguir else self.opener_sin
        try:
            with opener.open(pet, timeout=45) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)
        except urllib.error.URLError as e:
            return 0, ("ERROR DE RED: %s" % e).encode(), {}

    def get(self, ruta):
        return self.pedir(ruta)

    def post(self, ruta, datos):
        return self.pedir(ruta, datos)

    def texto(self, ruta):
        estado, cuerpo, _ = self.get(ruta)
        return estado, cuerpo.decode("utf-8", "ignore")

    def json(self, ruta):
        estado, cuerpo, _ = self.get(ruta)
        try:
            return estado, json.loads(cuerpo.decode("utf-8"))
        except Exception:
            return estado, None


def leer(ruta_db, sql, params=()):
    """Ejecuta un SELECT en modo lectura sobre un archivo SQLite. Devuelve lista de dicts."""
    con = sqlite3.connect(_uri_ro(ruta_db), uri=True, timeout=20)
    con.row_factory = sqlite3.Row
    try:
        return [dict(f) for f in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def escalar(ruta_db, sql, params=(), por_defecto=None):
    filas = leer(ruta_db, sql, params)
    if not filas:
        return por_defecto
    valor = list(filas[0].values())[0]
    return por_defecto if valor is None else valor


def escribir(ruta_db, sql, params=()):
    """Escritura usada SOLO para limpiar los datos de prueba del propio verificador."""
    con = sqlite3.connect(ruta_db, timeout=20)
    try:
        cur = con.execute(sql, params)
        con.commit()
        return cur.rowcount
    finally:
        con.close()


def filas_csv(texto):
    """Parseo tolerante de un CSV servido por la aplicacion (BOM incluido)."""
    return list(csv.reader(io.StringIO(texto.lstrip("\ufeff"))))


def num(valor):
    try:
        return float(str(valor).replace(",", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def solo_usuario(fila_csv):
    return (fila_csv.get("usuario") or "").strip()


def clave_de(fila_csv):
    """Clave del CSV (columna 'clave' o 'password_inicial'). Nunca se imprime."""
    for columna in ("clave", "password_inicial", "password", "clave_inicial"):
        valor = (fila_csv.get(columna) or "").strip()
        if valor:
            return valor
    return ""


class Informe:
    """Acumula el resultado de los 11 puntos."""

    def __init__(self):
        self.puntos = []
        self.fallos_reales = []

    def anota(self, numero, titulo, ok, evidencias, cifra=""):
        self.puntos.append({"n": numero, "titulo": titulo, "ok": bool(ok),
                            "evidencias": list(evidencias), "cifra": cifra})
        print(" [%s] %-2d) %s" % ("OK" if ok else "FALLO", numero, titulo))
        for linea in evidencias:
            print("        - %s" % linea)
        print()

    def fallo_real(self, descripcion, evidencia):
        self.fallos_reales.append((descripcion, evidencia))

    @property
    def total_ok(self):
        return sum(1 for p in self.puntos if p["ok"])


# =========================================================================== verificador
class Verificador:
    def __init__(self, args):
        self.args = args
        self.base = args.base.rstrip("/")
        self.informe = Informe()
        self.control_db = args.db_control or os.path.join(BASE_DIR, "database", "simulator.db")
        self.aulas_dir = os.path.join(BASE_DIR, "database", "aulas")
        self.inicio = datetime.utcnow()
        self.fecha_trabajo = datetime.now().strftime("%Y-%m-%d")
        self.creados = {"cuenta": None, "evidencia": None, "aula_evidencia": None}
        self.estudiantes = {}          # usuario -> dict(fila, id, aula, cliente)
        self.principal = None          # usuario con mas asientos (evidencia contable)
        self.otro = None               # segundo estudiante (aislamiento)
        self.docente = None            # usuario docente autenticado
        self.cliente_docente = None

    # ------------------------------------------------------------------ infraestructura
    def aula_de(self, usuario, paralelo=None):
        candidatas = []
        if paralelo:
            candidatas.append(os.path.join(self.aulas_dir, str(paralelo).upper(),
                                           "%s.db" % usuario.lower()))
        candidatas.append(os.path.join(self.aulas_dir, "%s.db" % usuario.lower()))
        for ruta in candidatas:
            if os.path.exists(ruta):
                return ruta
        if os.path.isdir(self.aulas_dir):
            for raiz, _dirs, archivos in os.walk(self.aulas_dir):
                for archivo in archivos:
                    if archivo.lower() == "%s.db" % usuario.lower():
                        return os.path.join(raiz, archivo)
        return candidatas[0]

    def id_usuario_control(self, usuario):
        return escalar(self.control_db,
                       "SELECT id FROM usuarios WHERE username = ?", (usuario,))

    def metricas_aula(self, aula):
        """(cuentas, asientos, lineas, debe, haber) del aula, leidos del archivo .db."""
        if not aula or not os.path.exists(aula):
            return (0, 0, 0, 0.0, 0.0)
        cuentas = escalar(aula, "SELECT COUNT(*) FROM cuentas", por_defecto=0)
        filas = leer(aula, """
            SELECT COUNT(DISTINCT a.id) AS asientos, COUNT(d.id) AS lineas,
                   COALESCE(SUM(d.debe), 0) AS debe, COALESCE(SUM(d.haber), 0) AS haber
              FROM detalle_asientos d
              JOIN asientos a ON a.id = d.asiento_id
             WHERE UPPER(IFNULL(a.estado, '')) IN ('CONTABILIZADO', 'REVERTIDO')
        """)
        f = filas[0] if filas else {}
        return (int(cuentas or 0), int(f.get("asientos") or 0), int(f.get("lineas") or 0),
                round(float(f.get("debe") or 0), 2), round(float(f.get("haber") or 0), 2))

    def asientos_csv(self, cliente):
        """Asientos del Libro Diario servidos por la aplicacion, agrupados por N°."""
        estado, texto = cliente.texto("/reportes/exportar/csv/diario")
        if estado != 200:
            return None
        filas = filas_csv(texto)
        if not filas:
            return []
        agrupados = {}
        for fila in filas[1:]:
            if len(fila) < 8:
                continue
            numero = fila[0]
            datos = agrupados.setdefault(numero, {"numero": numero, "fecha": fila[1],
                                                  "glosa": fila[2], "debe": 0.0, "haber": 0.0,
                                                  "lineas": 0})
            datos["debe"] += num(fila[6])
            datos["haber"] += num(fila[7])
            datos["lineas"] += 1
        for datos in agrupados.values():
            datos["debe"] = round(datos["debe"], 2)
            datos["haber"] = round(datos["haber"], 2)
        return [agrupados[clave] for clave in sorted(agrupados, key=lambda x: (len(x), x))]

    def totales_csv_balance(self, cliente):
        """Totales del balance de comprobacion (TOTALES,,,Debitos,Creditos,SaldoD,SaldoA)."""
        estado, texto = cliente.texto("/reportes/exportar/csv/balance")
        if estado != 200:
            return None
        for fila in filas_csv(texto):
            if fila and fila[0].strip().upper() == "TOTALES":
                return {"debitos": num(fila[3]), "creditos": num(fila[4]),
                        "saldo_deudor": num(fila[5]), "saldo_acreedor": num(fila[6])}
        return None

    # ------------------------------------------------------------------ pasos previos
    def comprobar_servidor(self):
        estado, datos = Cliente(self.base).json("/api/health")
        if estado != 200 or not datos:
            print(" [FALLO] El servidor no responde en %s/api/health (estado %s)." % (self.base, estado))
            print("         Arranquelo con:")
            print("         powershell -NoProfile -Command \"Start-Process -FilePath "
                  "'%s' -WindowStyle Hidden\"" % os.path.join(BASE_DIR, "deploy", "windows",
                                                              "iniciar_servidor.cmd"))
            return False
        print(" Servidor operativo: %s | tablas=%s | periodo='%s' | fecha de trabajo=%s"
              % (datos.get("estado"), datos.get("tablas"),
                 (datos.get("periodo_activo") or {}).get("nombre"), datos.get("fecha_trabajo")))
        print()
        if datos.get("fecha_trabajo"):
            self.fecha_trabajo = str(datos["fecha_trabajo"])
        return True

    def cargar_estudiantes(self):
        ruta = self.args.csv
        if not os.path.exists(ruta):
            print(" [FALLO] No existe el CSV de credenciales: %s" % ruta)
            return False
        with open(ruta, encoding="utf-8-sig", newline="") as archivo:
            filas = [f for f in csv.DictReader(archivo) if solo_usuario(f)]
        if len(filas) < 2:
            print(" [FALLO] El CSV no trae al menos dos estudiantes.")
            return False
        print(" Credenciales de estudiantes: %s (%d filas; claves OCULTAS)"
              % (os.path.basename(ruta), len(filas)))
        for fila in filas:
            usuario = solo_usuario(fila)
            self.estudiantes[usuario] = {
                "fila": fila, "usuario": usuario,
                "nombre": (fila.get("nombre") or "").strip(),
                "paralelo": (fila.get("paralelo") or "").strip(),
                "id": self.id_usuario_control(usuario),
                "aula": self.aula_de(usuario, (fila.get("paralelo") or "").strip()),
                "cliente": None, "sesiones_antes": None,
            }
        return True

    def elegir_estudiantes(self):
        """Elige los dos estudiantes de trabajo leyendo sus aulas (sin iniciar sesion).

        El de mas asientos sirve para la evidencia contable (Libro Diario/Mayor/Balance/
        Estados) y el de menos para demostrar el aislamiento: asi ninguna de las dos
        comprobaciones depende de datos de otro estudiante.
        """
        candidatos = []
        for datos in list(self.estudiantes.values())[:max(2, self.args.muestra)] \
                if self.args.muestra else list(self.estudiantes.values()):
            if not os.path.exists(datos["aula"]):
                continue
            _c, asientos, lineas, debe, haber = self.metricas_aula(datos["aula"])
            datos.update({"asientos_iniciales": asientos, "lineas_iniciales": lineas,
                          "debe_inicial": debe, "haber_inicial": haber})
            candidatos.append(datos)
        if len(candidatos) < 2:
            return False
        ordenados = sorted(candidatos, key=lambda d: (-d["asientos_iniciales"], d["usuario"]))
        self.principal = ordenados[0]["usuario"]
        self.otro = ordenados[-1]["usuario"]
        for usuario in (self.principal, self.otro):
            datos = self.estudiantes[usuario]
            antes = escalar(self.control_db,
                            "SELECT COUNT(*) FROM sesiones_usuario WHERE usuario_id = ?",
                            (datos["id"],), por_defecto=0)
            cliente = Cliente(self.base)
            estado, cuerpo, cabeceras = cliente.pedir(
                "/login", {"username": usuario, "password": clave_de(datos["fila"])}, seguir=False)
            datos.update({"cliente": cliente, "login": estado,
                          "destino": cabeceras.get("Location", ""),
                          "sesiones_antes": int(antes or 0)})
        return True

    def preparar_evidencia_contable(self):
        """Garantiza movimientos reales en el aula de trabajo para los puntos 8 a 11.

        Si el aula elegida no tiene asientos se registra UN asiento marcado VERIFICACION-PROD
        (partida doble, 1000.00) que luego se borra. Con --forzar-asiento-prueba se crea
        siempre, para probar este camino.
        """
        datos = self.estudiantes[self.principal]
        _c, asientos, _l, _d, _h = self.metricas_aula(datos["aula"])
        if asientos and not self.args.forzar_asiento_prueba:
            return [" Evidencia contable: el aula de %s ya tiene %s asientos propios; "
                    "no se crean datos de prueba." % (self.principal, asientos)]
        cuentas = leer(datos["aula"], """
            SELECT id, codigo, nombre, naturaleza, clasificacion FROM cuentas
             WHERE acepta_movimiento = 1 ORDER BY codigo ASC
        """)
        deudora = next((c for c in cuentas if str(c["naturaleza"]).upper() == "DEUDORA"), None)
        # Se prefiere una cuenta de PATRIMONIO (aporte de capital) para que el asiento de prueba
        # sea contablemente natural: Caja (activo) contra Capital.
        acreedora = next((c for c in cuentas if str(c["naturaleza"]).upper() == "ACREEDORA"
                          and str(c["clasificacion"]).upper() == "PATRIMONIO"), None) \
            or next((c for c in cuentas if str(c["naturaleza"]).upper() == "ACREEDORA"), None)
        if not deudora or not acreedora:
            return [" [FALLO] El aula de %s no tiene cuentas DEUDORA/ACREEDORA con movimiento: "
                    "no se puede preparar evidencia contable." % self.principal]
        glosa = "%s asiento de prueba %s" % (MARCADOR, MOMENTO)
        numero_doc = "VERIFICACION-PROD-%s" % MOMENTO
        estado, _cuerpo, cabeceras = datos["cliente"].pedir(
            "/contabilidad/diario",
            {"fecha": self.fecha_trabajo, "glosa": glosa, "tipo_documento": "DOCUMENTO_INTERNO",
             "numero_documento": numero_doc,
             "cuenta_id[]": [str(deudora["id"]), str(acreedora["id"])],
             "debe[]": ["1000", "0"], "haber[]": ["0", "1000"],
             "referencia[]": ["VERIFICACION-PROD Debe", "VERIFICACION-PROD Haber"]}, seguir=True)
        creado = leer(datos["aula"], "SELECT id FROM asientos WHERE glosa = ?", (glosa,))
        if not creado:
            return [" [FALLO] No se pudo registrar el asiento de prueba VERIFICACION-PROD "
                    "(POST /contabilidad/diario -> %s -> %s)" % (estado, cabeceras.get("Location"))]
        self.creados["asiento"] = (datos["aula"], glosa)
        return [" Datos de prueba (se borran al terminar): asiento «%s» id=%s 1000.00 "
                "(%s %s / %s %s)" % (glosa, creado[0]["id"], deudora["codigo"], deudora["nombre"],
                                     acreedora["codigo"], acreedora["nombre"])]

    def autenticar_docente(self):
        for usuario, password in ((self.args.docente_usuario, self.args.docente_password),
                                  ("admin", "admin123")):
            if not usuario or not password:
                continue
            cliente = Cliente(self.base)
            estado, _cuerpo, cabeceras = cliente.pedir(
                "/login", {"username": usuario, "password": password}, seguir=False)
            if estado in (301, 302, 303) and "dashboard" in cabeceras.get("Location", ""):
                self.cliente_docente = cliente
                self.docente = usuario
                return True
        return False

    # ------------------------------------------------------------------ 1. acceso individual
    def punto1_acceso_individual(self):
        evidencias, ok = [], True
        for usuario in (self.principal, self.otro):
            datos = self.estudiantes[usuario]
            estado, html = datos["cliente"].texto("/dashboard")
            nombre_visible = bool(datos["nombre"]) and datos["nombre"] in html
            cuentas, asientos, lineas, debe, haber = self.metricas_aula(datos["aula"])
            existe_aula = os.path.exists(datos["aula"])
            ok = ok and estado == 200 and datos["login"] in (301, 302, 303) and nombre_visible \
                and existe_aula
            evidencias.append(
                "usuario=%s (clave oculta): POST /login -> %s -> %s | /dashboard %s y %s"
                % (usuario, datos["login"], datos["destino"] or "-", estado,
                   ("muestra «%s»" % datos["nombre"]) if nombre_visible else "NO muestra su nombre"))
            evidencias.append(
                "  aula propia: %s | %s cuentas, %s asientos, %s lineas | Debe %.2f / Haber %.2f"
                % (os.path.relpath(datos["aula"], BASE_DIR).replace("\\", "/"), cuentas, asientos,
                   lineas, debe, haber))
        if self.principal == self.otro:
            ok = False
            evidencias.append("  no se pudieron separar dos estudiantes distintos")
        return ok, evidencias, "2 estudiantes en sus propias aulas (%s, %s)" % (self.principal, self.otro)

    # ------------------------------------------------------------------ 2. aislamiento
    def punto2_aislamiento(self):
        evidencias = []
        a = self.estudiantes[self.principal]
        b = self.estudiantes[self.otro]

        # (a) Cuenta privada creada por A en su aula.
        escribir(a["aula"], "DELETE FROM cuentas WHERE codigo = ?", (CODIGO_CUENTA_PRUEBA,))
        estado_post, _cuerpo, cabeceras = a["cliente"].pedir(
            "/contabilidad/cuentas",
            {"codigo": CODIGO_CUENTA_PRUEBA, "nombre": NOMBRE_CUENTA_PRUEBA,
             "naturaleza": "DEUDORA", "clasificacion": "ACTIVO_CORRIENTE", "nivel": "1",
             "acepta_movimiento": "1"}, seguir=False)
        self.creados["cuenta"] = (a["aula"], CODIGO_CUENTA_PRUEBA)

        estado_http_a, html_a = a["cliente"].texto("/contabilidad/cuentas")
        estado_http_b, html_b = b["cliente"].texto("/contabilidad/cuentas")
        en_a = CODIGO_CUENTA_PRUEBA in html_a
        en_b = CODIGO_CUENTA_PRUEBA in html_b

        fila_a = escalar(a["aula"], "SELECT COUNT(*) FROM cuentas WHERE codigo = ?",
                         (CODIGO_CUENTA_PRUEBA,), por_defecto=0)
        fila_b = escalar(b["aula"], "SELECT COUNT(*) FROM cuentas WHERE codigo = ?",
                         (CODIGO_CUENTA_PRUEBA,), por_defecto=0)

        # (b) Asientos de A no aparecen en el aula de B (HTTP + archivo).
        asientos_a = self.asientos_csv(a["cliente"]) or []
        asientos_b = self.asientos_csv(b["cliente"]) or []
        glosas_a = {x["glosa"] for x in asientos_a}
        glosas_b = {x["glosa"] for x in asientos_b}
        compartidas = {g for g in glosas_a if g in glosas_b and g}
        _c, asient_a, lin_a, debe_a, haber_a = self.metricas_aula(a["aula"])
        _c, asient_b, lin_b, debe_b, haber_b = self.metricas_aula(b["aula"])

        ok = (estado_post in (301, 302, 303) and en_a and not en_b
              and int(fila_a) == 1 and int(fila_b) == 0 and not compartidas)

        evidencias.append(
            "cuenta privada «%s» creada por %s (POST /contabilidad/cuentas -> %s):"
            % (CODIGO_CUENTA_PRUEBA, self.principal, estado_post))
        evidencias.append(
            "  HTTP: GET /contabilidad/cuentas -> %s (200) la muestra=%s | %s (200) la muestra=%s"
            % (self.principal, en_a, self.otro, en_b))
        evidencias.append(
            "  archivos .db: %s.cuentas con codigo %s = %s | %s.cuentas = %s"
            % (os.path.basename(a["aula"]), CODIGO_CUENTA_PRUEBA, fila_a,
               os.path.basename(b["aula"]), fila_b))
        evidencias.append(
            "  Libro Diario: %s -> %s asientos (Debe %.2f / Haber %.2f); %s -> %s asientos "
            "(Debe %.2f / Haber %.2f); glosas compartidas=%s"
            % (self.principal, asient_a, debe_a, haber_a, self.otro, asient_b, debe_b, haber_b,
               len(compartidas) or "ninguna"))
        return ok, evidencias, "aislamiento total (0 filas cruzadas)"

    # ------------------------------------------------------------------ 3. panel docente
    def punto3_panel_docente(self):
        evidencias = []
        if not self.cliente_docente:
            self.informe.fallo_real(
                "No fue posible autenticar al perfil docente",
                "POST /login con usuario='%s' y con admin no llegaron a /dashboard"
                % self.args.docente_usuario)
            return False, ["login del docente fallido"], "sin panel docente"
        datos = self.estudiantes[self.principal]
        id_est = datos["id"]
        antes = self.metricas_aula(datos["aula"])

        lecturas, ok_lectura = [], True
        for sufijo, campo in (("diario", "libro_diario"), ("mayor", "libro_mayor"),
                              ("balance", "balance"), ("estados", "estados"),
                              ("cuentas", "plan_cuentas")):
            estado, cuerpo = self.cliente_docente.json(
                "/docente/estudiantes/%s/%s?formato=json" % (id_est, sufijo))
            datos_libro = (cuerpo or {}).get(campo) or {}
            existe = datos_libro.get("existe")
            ok_lectura = ok_lectura and estado == 200 and bool(existe)
            if campo == "libro_diario":
                detalle = ("asientos=%s Debe=%.2f Haber=%.2f"
                           % (len(datos_libro.get("asientos") or []),
                              num(datos_libro.get("total_debe")), num(datos_libro.get("total_haber"))))
            elif campo == "balance":
                detalle = ("cuentas=%s Debitos=%.2f Creditos=%.2f cuadrado=%s"
                           % (len(datos_libro.get("cuentas") or []),
                              num(datos_libro.get("total_debitos")),
                              num(datos_libro.get("total_creditos")),
                              datos_libro.get("cuadrado")))
            elif campo == "libro_mayor":
                detalle = ("cuentas=%s movimientos=%s Debe=%.2f Haber=%.2f"
                           % (len(datos_libro.get("cuentas") or []),
                              sum(int(c.get("num_movimientos") or 0)
                                  for c in (datos_libro.get("cuentas") or [])),
                              num(datos_libro.get("total_debe")),
                              num(datos_libro.get("total_haber"))))
            elif campo == "plan_cuentas":
                detalle = "cuentas=%s" % datos_libro.get("num_cuentas")
            elif campo == "estados":
                situacion = datos_libro.get("situacion") or {}
                resultado = datos_libro.get("resultados") or {}
                detalle = ("situacion: Activo=%.2f Pasivo=%.2f Patrimonio=%.2f diferencia=%.2f "
                           "cuadra=%s | resultados: utilidad_neta=%.2f"
                           % (num(situacion.get("total_activo")), num(situacion.get("total_pasivo")),
                              num(situacion.get("total_patrimonio")),
                              num(situacion.get("diferencia")), situacion.get("cuadra"),
                              num(resultado.get("utilidad_neta"))))
            else:
                detalle = "claves=%s" % ",".join(sorted(datos_libro.keys())[:6])
            lecturas.append("GET /docente/estudiantes/%s/%s?formato=json -> %s (%s) %s"
                            % (id_est, sufijo, estado, os.path.basename(datos_libro.get("aula") or ""),
                               detalle))

        # Escritura: ninguna ruta del panel docente admite POST (solo lectura).
        no_escribibles, ok_escritura = [], True
        for sufijo in ("diario", "mayor", "balance", "estados", "cuentas"):
            estado, _c, _h = self.cliente_docente.pedir(
                "/docente/estudiantes/%s/%s" % (id_est, sufijo), {"glosa": MARCADOR},
                metodo="POST")
            no_escribibles.append("%s:%s" % (sufijo, estado))
            ok_escritura = ok_escritura and estado == 405
        despues = self.metricas_aula(datos["aula"])
        sin_cambios = antes == despues

        evidencias.append("docente '%s' autenticado; libros del estudiante %s (id %s) en SOLO LECTURA:"
                          % (self.docente, self.principal, id_est))
        evidencias.extend("  " + x for x in lecturas)
        evidencias.append("  POST a las 5 vistas de libros -> %s (405 = Method Not Allowed)"
                          % ", ".join(no_escribibles))
        evidencias.append("  aula del estudiante sin cambios tras la lectura: %s (cuentas=%s, "
                          "asientos=%s)" % ("identica" if sin_cambios else "CAMBIADA",
                                            despues[0], despues[1]))
        ok = ok_lectura and ok_escritura and sin_cambios
        return ok, evidencias, "%s libros leidos; POST -> 405" % len(lecturas)

    # ------------------------------------------------------------------ 4. registro de ingresos
    def punto4_registro_ingresos(self):
        evidencias, ok = [], True
        sesiones = leer(self.control_db, """
            SELECT s.id, s.usuario_id, u.username, s.inicio, s.ip_origen, s.navegador,
                   COALESCE(s.activa, 0) AS activa
              FROM sesiones_usuario s LEFT JOIN usuarios u ON u.id = s.usuario_id
             ORDER BY s.id DESC LIMIT 3
        """)
        for usuario in (self.principal, self.otro):
            datos = self.estudiantes[usuario]
            ahora = escalar(self.control_db,
                            "SELECT COUNT(*) FROM sesiones_usuario WHERE usuario_id = ?",
                            (datos["id"],), por_defecto=0)
            nueva = leer(self.control_db, """
                SELECT id, inicio, ip_origen, navegador FROM sesiones_usuario
                 WHERE usuario_id = ? ORDER BY id DESC LIMIT 1
            """, (datos["id"],))
            evento = leer(self.control_db, """
                SELECT id, evento, modulo, detalle, timestamp FROM eventos_estudiante
                 WHERE usuario_id = ? AND evento = 'LOGIN' ORDER BY id DESC LIMIT 1
            """, (datos["id"],))
            ok = ok and ahora == datos["sesiones_antes"] + 1 and bool(nueva) and bool(evento)
            evidencias.append(
                "usuario=%s: sesiones_usuario %s -> %s (+1); ultima sesion id=%s inicio=%s ip=%s"
                % (usuario, datos["sesiones_antes"], ahora,
                   (nueva[0]["id"] if nueva else "-"),
                   (nueva[0]["inicio"] if nueva else "-"),
                   (nueva[0]["ip_origen"] if nueva else "-")))
            evidencias.append(
                "  eventos_estudiante LOGIN: id=%s evento=%s modulo=%s detalle='%s' timestamp=%s"
                % (evento[0]["id"], evento[0]["evento"], evento[0]["modulo"],
                   evento[0]["detalle"], evento[0]["timestamp"]) if evento
                else "  eventos_estudiante LOGIN: NO ENCONTRADO")
        evidencias.append("ultimos ingresos registrados en el sistema (sesiones_usuario):")
        for s in sesiones:
            evidencias.append("  id=%s usuario=%s inicio=%s ip=%s activa=%s"
                              % (s["id"], s["username"], s["inicio"], s["ip_origen"], s["activa"]))
        return ok, evidencias, "sesiones y eventos LOGIN con usuario y fecha"

    # ------------------------------------------------------------------ 5. actividades
    def punto5_actividades(self):
        evidencias = []
        datos = self.estudiantes[self.principal]
        estado, cuerpo = datos["cliente"].json("/mis-actividades?formato=json")
        actividades = (cuerpo or {}).get("actividades") or []
        estados = {}
        puntaje = 0.0
        for actividad in actividades:
            clave = str(actividad.get("estado_asignacion") or "?")
            estados[clave] = estados.get(clave, 0) + 1
            puntaje += num(actividad.get("puntaje"))
        avance = {}
        if actividades:
            primera = actividades[0]
            estado_det, detalle = datos["cliente"].json(
                "/mis-actividades/%s?formato=json" % primera["id"])
            avance = {"estado": estado_det,
                      "asignacion": bool((detalle or {}).get("actividad")),
                      "eventos": len((detalle or {}).get("eventos") or []),
                      "evidencias": len((detalle or {}).get("evidencias") or [])}
        estado_doc, cuerpo_doc = self.cliente_docente.json("/docente/actividades?formato=json") \
            if self.cliente_docente else (0, None)
        total_doc = (cuerpo_doc or {}).get("total")
        estado_est_doc, cuerpo_est_doc = self.cliente_docente.json(
            "/docente/estudiantes/%s?formato=json" % datos["id"]) if self.cliente_docente else (0, None)
        avance_doc = ((cuerpo_est_doc or {}).get("ficha") or {}).get("avance") or {}

        ok = (estado == 200 and len(actividades) >= 1 and all(
            a.get("estado_asignacion") for a in actividades))
        evidencias.append(
            "GET /mis-actividades?formato=json -> %s: %s actividades asignadas a %s | por estado: %s | puntaje total %.2f"
            % (estado, len(actividades), self.principal,
               ", ".join("%s=%s" % (k, v) for k, v in sorted(estados.items())), puntaje))
        if actividades:
            p = actividades[0]
            evidencias.append(
                "  primera: codigo=%s unidad=%s estado=%s intentos_usados=%s puntaje=%s"
                % (p.get("codigo"), p.get("unidad"), p.get("estado_asignacion"),
                   p.get("intentos_usados"), p.get("puntaje")))
        if avance:
            evidencias.append(
                "  GET /mis-actividades/%s?formato=json -> %s (asignacion=%s, %s eventos, %s evidencias)"
                % (actividades[0]["id"], avance["estado"], avance["asignacion"],
                   avance["eventos"], avance["evidencias"]))
        evidencias.append(
            "  docente: /docente/actividades?formato=json -> %s (%s actividades); ficha del estudiante: "
            "avance=%s" % (estado_doc, total_doc, json.dumps(avance_doc, ensure_ascii=False)))
        return ok, evidencias, "%s actividades asignadas, %s" % (
            len(actividades), ", ".join("%s=%s" % (k, v) for k, v in sorted(estados.items())) or "-")

    # ------------------------------------------------------------------ 6. evidencias
    def punto6_evidencias(self):
        evidencias = []
        datos = self.estudiantes[self.principal]
        estado, cuerpo, _h = datos["cliente"].pedir(
            "/mis-evidencias/nueva?formato=json", {"tipo": "INTEGRAL", "titulo": TITULO_EVIDENCIA})
        evidencia = (cuerpo and json.loads(cuerpo.decode("utf-8")).get("evidencia")) or {}
        codigo = evidencia.get("codigo")
        ok = estado == 201 and bool(codigo)
        if not ok:
            evidencias.append("POST /mis-evidencias/nueva?formato=json -> %s (respuesta: %s)"
                              % (estado, cuerpo[:180]))
            return False, evidencias, "no se pudo crear la evidencia"
        self.creados["evidencia"] = (codigo, evidencia.get("id"), TITULO_EVIDENCIA)

        estado_get, cuerpo_get = datos["cliente"].json("/mis-evidencias/%s?formato=json"
                                                      % evidencia["id"])
        recuperada = ((cuerpo_get or {}).get("evidencia") or {})
        estado_lista, cuerpo_lista = datos["cliente"].json("/mis-evidencias?formato=json")
        lista_codigos = [e.get("codigo") for e in ((cuerpo_lista or {}).get("evidencias") or [])]

        estado_doc, cuerpo_doc = (self.cliente_docente.json(
            "/docente/evidencias/verificar?codigo=%s&formato=json" % codigo)
            if self.cliente_docente else (0, None))
        verificacion = (cuerpo_doc or {}).get("verificacion") or {}

        # Aislamiento adicional: el otro estudiante no puede abrir la evidencia ajena.
        estado_ajeno, _c = self.estudiantes[self.otro]["cliente"].json(
            "/mis-evidencias/%s?formato=json" % evidencia["id"])

        ok = (estado_get == 200 and recuperada.get("codigo") == codigo
              and codigo in lista_codigos and estado_doc == 200
              and bool((cuerpo_doc or {}).get("success")) and estado_ajeno in (403, 404))
        evidencias.append("POST /mis-evidencias/nueva?formato=json -> %s, codigo=%s id=%s estado=%s titulo='%s'"
                          % (estado, codigo, evidencia.get("id"), evidencia.get("estado"),
                             evidencia.get("titulo")))
        evidencias.append("GET /mis-evidencias/%s?formato=json -> %s, codigo recuperado=%s huella=%s"
                          % (evidencia.get("id"), estado_get, recuperada.get("codigo"),
                             (recuperada.get("huella") or "sin huella (borrador)")))
        evidencias.append("GET /mis-evidencias?formato=json -> %s, %s evidencias del estudiante; "
                          "el codigo nuevo esta en la lista=%s"
                          % (estado_lista, len(lista_codigos), codigo in lista_codigos))
        evidencias.append("docente GET /docente/evidencias/verificar?codigo=%s -> %s success=%s "
                          "estudiante=%s estado=%s"
                          % (codigo, estado_doc, (cuerpo_doc or {}).get("success"),
                             verificacion.get("estudiante_username") or verificacion.get("estudiante"),
                             verificacion.get("estado")))
        evidencias.append("aislamiento: el estudiante %s pide esa evidencia -> %s (no puede verla)"
                          % (self.otro, estado_ajeno))
        return ok, evidencias, "codigo %s verificado por el docente" % codigo

    # ------------------------------------------------------------------ 7. trazabilidad
    def punto7_trazabilidad(self):
        evidencias = []
        datos = self.estudiantes[self.principal]
        _c, asientos_antes, _l, _d, _h = self.metricas_aula(datos["aula"])

        # El rechazo viaja como aviso flash: se lee el estado real (sin seguir el redirect) y el
        # mensaje que ve el estudiante (siguiendo el redirect, que es la pagina con el aviso).
        intento = {"fecha": "2026-04-30", "glosa": GLOSA_DESCUADRADA, "tipo_documento": "MANUAL",
                   "cuenta_id[]": ["3", "31"], "debe[]": ["500", "0"], "haber[]": ["0", "450"]}
        estado_post, _cuerpo, cabeceras = datos["cliente"].pedir(
            "/contabilidad/diario", intento, seguir=False)
        destino_post = cabeceras.get("Location", "")
        _e, cuerpo_flash, _h = datos["cliente"].pedir("/contabilidad/diario", intento)
        texto = ""
        for fragmento in re.findall(r"(El asiento no cuadra[^<\"]{0,180})",
                                    cuerpo_flash.decode("utf-8", "ignore")):
            texto = re.sub(r"\s+", " ", fragmento).strip()
            break
        _c, asientos_despues, _l, _d, _h = self.metricas_aula(datos["aula"])
        persistido = escalar(datos["aula"],
                             "SELECT COUNT(*) FROM asientos WHERE glosa LIKE ?",
                             ("%s%%" % GLOSA_DESCUADRADA,), por_defecto=0)

        # Documento invalido (segundo ejemplo de intento rechazado).
        docs_antes = escalar(self.control_db, "SELECT COUNT(*) FROM documentos_fuente",
                             por_defecto=0)
        estado_doc, cuerpo_doc, _h2 = datos["cliente"].pedir(
            "/documentos/nuevo?formato=json", {"tipo": "FACTURA", "emisor": MARCADOR})
        docs_despues = escalar(self.control_db, "SELECT COUNT(*) FROM documentos_fuente",
                               por_defecto=0)
        errores_doc = []
        try:
            errores_doc = (json.loads(cuerpo_doc.decode("utf-8")) or {}).get("errores") or []
        except Exception:
            pass

        # ¿Quedo registrado el intento fallido con su mensaje?
        fallidos = leer(self.control_db, """
            SELECT id, evento, timestamp, detalle FROM eventos_estudiante
             WHERE usuario_id = ? AND evento = 'INTENTO_FALLIDO_ASIENTO'
             ORDER BY id DESC LIMIT 3
        """, (datos["id"],))
        ventana = leer(self.control_db, """
            SELECT id, evento, modulo, detalle, timestamp FROM eventos_estudiante
             WHERE usuario_id = ? AND timestamp >= ? ORDER BY id ASC
        """, (datos["id"], self.inicio.strftime("%Y-%m-%d %H:%M:%S")))
        rechazos_auditoria = leer(self.control_db, """
            SELECT id, accion, modulo FROM auditoria
             WHERE usuario_id = ? AND (UPPER(accion) LIKE '%RECHAZ%' OR UPPER(accion) LIKE '%FALLID%'
                                       OR UPPER(accion) LIKE '%ERROR%')
             ORDER BY id DESC LIMIT 3
        """, (datos["id"],))
        total_fallidos = escalar(self.control_db,
                                 "SELECT COUNT(*) FROM eventos_estudiante WHERE evento = "
                                 "'INTENTO_FALLIDO_ASIENTO'", por_defecto=0)

        rechazado = (estado_post == 302 and "no cuadra" in texto) and int(persistido) == 0 \
            and asientos_antes == asientos_despues and estado_doc == 400 and bool(errores_doc)
        registrado = bool(fallidos) or bool(rechazos_auditoria)

        evidencias.append("intento de asiento descuadrado (glosa='%s'): POST /contabilidad/diario -> %s "
                          "Location=%s (nunca 4xx: el rechazo viaja como aviso flash)"
                          % (GLOSA_DESCUADRADA, estado_post, destino_post or "-"))
        evidencias.append("  mensaje literal del sistema: «%s»" % (texto or "NO SE ENCONTRO EL MENSAJE"))
        evidencias.append("  no se persistio nada: asientos en el aula %s -> %s; filas con esa glosa=%s"
                          % (asientos_antes, asientos_despues, persistido))
        evidencias.append("documento invalido: POST /documentos/nuevo?formato=json -> %s con %s error(es); "
                          "documentos_fuente %s -> %s (no se emitio nada); ejemplo: «%s»"
                          % (estado_doc, len(errores_doc), docs_antes, docs_despues,
                             (errores_doc[0][:120] if errores_doc else "-")))
        if registrado:
            for fila in fallidos:
                evidencias.append("  REGISTRO: eventos_estudiante id=%s evento=%s timestamp=%s detalle=%s"
                                  % (fila["id"], fila["evento"], fila["timestamp"], fila["detalle"]))
        else:
            eventos_ventana = ["%s(id=%s)" % (x["evento"], x["id"]) for x in ventana]
            evidencias.append("  SIN REGISTRO DE INTENTO FALLIDO: eventos_estudiante "
                              "'INTENTO_FALLIDO_ASIENTO' de este usuario = %s (en todo el sistema = %s); "
                              "auditoria con accion de rechazo = %s"
                              % (len(fallidos), total_fallidos, len(rechazos_auditoria)))
            evidencias.append("  eventos de la corrida para el usuario: %s"
                              % (", ".join(eventos_ventana) or "ninguno"))
        ok = rechazado and registrado
        if not (rechazado and registrado):
            if rechazado:
                self.informe.fallo_real(
                    "TRAZABILIDAD: el intento rechazado NO queda registrado como intento fallido. "
                    "El sistema rechaza el asiento descuadrado con su mensaje y no persiste el "
                    "asiento, pero no hay ninguna fila de intento fallido: la conversion a "
                    "INTENTO_FALLIDO_ASIENTO (services/access_service.py:373-375) exige una "
                    "respuesta HTTP >= 400, y routes/accounting.py:99-102 siempre responde 302 "
                    "(flash + redirect); el intento acaba anotado como CREAR_ASIENTO.",
                    "POST /contabilidad/diario (Debe 500.00 / Haber 450.00) -> mensaje «%s»; "
                    "asientos del aula %s -> %s; eventos_estudiante INTENTO_FALLIDO_ASIENTO = %s; "
                    "eventos de la corrida: %s"
                    % (texto or "sin mensaje", asientos_antes, asientos_despues, total_fallidos,
                       ", ".join("%s(id=%s)" % (x["evento"], x["id"]) for x in ventana) or "ninguno"))
            else:
                self.informe.fallo_real(
                    "TRAZABILIDAD: el intento de asiento descuadrado no fue rechazado como se espera",
                    "POST /contabilidad/diario -> %s; mensaje «%s»; asientos %s -> %s; filas con la "
                    "glosa de prueba = %s; documento invalido -> %s con %s error(es)"
                    % (estado_post, texto or "sin mensaje", asientos_antes, asientos_despues,
                       persistido, estado_doc, len(errores_doc)))
        return ok, evidencias, ("rechazo con mensaje y registro de intento fallido" if ok
                                else "rechazo con mensaje, SIN registro del intento fallido")

    # ------------------------------------------------------------------ 8. libro diario
    def punto8_libro_diario(self):
        datos = self.estudiantes[self.principal]
        estado, html = datos["cliente"].texto("/contabilidad/diario")
        asientos = self.asientos_csv(datos["cliente"])
        if asientos is None:
            return False, ["GET /reportes/exportar/csv/diario no respondio 200"], "sin datos"
        descuadrados = [a for a in asientos if abs(a["debe"] - a["haber"]) >= 0.01]
        debe = round(sum(a["debe"] for a in asientos), 2)
        haber = round(sum(a["haber"] for a in asientos), 2)
        cuentas, asientos_db, lineas_db, debe_db, haber_db = self.metricas_aula(datos["aula"])
        ok = (estado == 200 and len(asientos) >= 1 and not descuadrados
              and abs(debe - debe_db) < 0.02 and abs(haber - haber_db) < 0.02)
        evidencias = [
            "GET /contabilidad/diario -> %s (%s, %s caracteres)" % (estado, "HTML del libro", len(html)),
            "Libro Diario de %s: %s asientos, %s lineas | TOTAL Debe=%.2f = TOTAL Haber=%.2f | "
            "asientos descuadrados=%s" % (self.principal, len(asientos),
                                          sum(a["lineas"] for a in asientos), debe, haber,
                                          len(descuadrados)),
            "  archivo %s: %s asientos, %s lineas de detalle, Debe=%.2f, Haber=%.2f (coincide con el HTTP: %s)"
            % (os.path.basename(datos["aula"]), asientos_db, lineas_db, debe_db, haber_db,
               abs(debe - debe_db) < 0.02 and abs(haber - haber_db) < 0.02),
        ]
        for a in asientos[:3]:
            evidencias.append("  asiento N°%s %s '%s' Debe=%.2f Haber=%.2f lineas=%s"
                              % (a["numero"], a["fecha"], a["glosa"][:45], a["debe"], a["haber"],
                                 a["lineas"]))
        return ok, evidencias, "%s asientos, Debe %.2f = Haber %.2f" % (len(asientos), debe, haber)

    # ------------------------------------------------------------------ 9. libro mayor
    def punto9_libro_mayor(self):
        datos = self.estudiantes[self.principal]
        estado, html = datos["cliente"].texto("/contabilidad/mayor")
        estado_csv, texto = datos["cliente"].texto("/reportes/exportar/csv/mayor")
        filas = filas_csv(texto) if estado_csv == 200 else []
        movimientos = [f for f in filas[1:] if len(f) >= 8]
        cuentas_con_mov = {f[0] for f in movimientos}
        con_saldo = [f for f in movimientos if abs(num(f[7])) > 0]
        _c, asientos_db, lineas_db, _d, _h = self.metricas_aula(datos["aula"])
        ok = (estado == 200 and len(movimientos) >= 1 and len(cuentas_con_mov) >= 1
              and len(movimientos) == lineas_db)
        evidencias = [
            "GET /contabilidad/mayor -> %s (%s caracteres)" % (estado, len(html)),
            "Libro Mayor de %s: %s cuentas con movimiento, %s movimientos, %s con saldo != 0"
            % (self.principal, len(cuentas_con_mov), len(movimientos), len(con_saldo)),
            "  archivo %s: %s lineas de movimiento en asientos validos (coincide con el HTTP: %s)"
            % (os.path.basename(datos["aula"]), lineas_db, len(movimientos) == lineas_db),
        ]
        for f in movimientos[:3]:
            evidencias.append("  %s %s | asiento N°%s %s | Debe=%s Haber=%s Saldo=%s"
                              % (f[0], f[1][:32], f[3], f[4][:28], f[5], f[6], f[7]))
        return ok, evidencias, "%s cuentas, %s movimientos con saldo" % (len(cuentas_con_mov), len(movimientos))

    # ------------------------------------------------------------------ 10. balance de comprobacion
    def punto10_balance_comprobacion(self):
        datos = self.estudiantes[self.principal]
        estado, html = datos["cliente"].texto("/contabilidad/balance")
        totales = self.totales_csv_balance(datos["cliente"])
        _c, asientos_db, lineas_db, debe_db, haber_db = self.metricas_aula(datos["aula"])
        if totales is None:
            return False, ["GET /reportes/exportar/csv/balance no devolvio la fila TOTALES"], "sin datos"
        diferencia = round(abs(totales["debitos"] - totales["creditos"]), 2)
        dif_saldos = round(abs(totales["saldo_deudor"] - totales["saldo_acreedor"]), 2)
        ok = (estado == 200 and diferencia < 0.01 and dif_saldos < 0.01
              and abs(totales["debitos"] - debe_db) < 0.02)
        evidencias = [
            "GET /contabilidad/balance -> %s (%s caracteres)" % (estado, len(html)),
            "Balance de comprobacion de %s: SUMA DEBE=%.2f | SUMA HABER=%.2f | diferencia=%.2f"
            % (self.principal, totales["debitos"], totales["creditos"], diferencia),
            "  saldos: deudor=%.2f | acreedor=%.2f | diferencia=%.2f"
            % (totales["saldo_deudor"], totales["saldo_acreedor"], dif_saldos),
            "  archivo %s: %s asientos, %s lineas, Debe=%.2f, Haber=%.2f"
            % (os.path.basename(datos["aula"]), asientos_db, lineas_db, debe_db, haber_db),
        ]
        return ok, evidencias, "Debe %.2f = Haber %.2f" % (totales["debitos"], totales["creditos"])

    # ------------------------------------------------------------------ 11. estados financieros
    def punto11_estados_financieros(self):
        datos = self.estudiantes[self.principal]
        estado_res, html_res = datos["cliente"].texto("/estados-financieros/resultados")
        estado_sit, html_sit = datos["cliente"].texto("/estados-financieros/situacion-financiera")
        estado_json_res, cuerpo_res = datos["cliente"].json("/api/statements?tipo=income_statement")
        estado_json_sit, cuerpo_sit = datos["cliente"].json("/api/statements?tipo=balance_sheet")
        res = (cuerpo_res or {}).get("statement") or {}
        sit = (cuerpo_sit or {}).get("statement") or {}
        estado_csv, texto_csv = datos["cliente"].texto("/reportes/exportar/csv/situacion-financiera")
        ecuacion_csv = ""
        for fila in filas_csv(texto_csv) if estado_csv == 200 else []:
            if fila and "cuaci" in fila[0]:
                ecuacion_csv = fila[-1]
        activo = num(sit.get("total_activo"))
        pasivo_patrimonio = num(sit.get("total_pasivo_y_patrimonio"))
        diferencia = round(activo - pasivo_patrimonio, 2)
        ok = (estado_res == 200 and estado_sit == 200 and estado_json_res == 200
              and estado_json_sit == 200 and abs(diferencia) < 0.01
              and bool(res.get("utilidad_neta") is not None))
        evidencias = [
            "GET /estados-financieros/resultados -> %s (%s caracteres); "
            "GET /estados-financieros/situacion-financiera -> %s (%s caracteres)"
            % (estado_res, len(html_res), estado_sit, len(html_sit)),
            "Estado de resultados (%s, /api/statements?tipo=income_statement): "
            "ingresos=%.2f, costo de ventas=%.2f, gastos=%.2f, UTILIDAD NETA=%.2f"
            % (estado_json_res, num(res.get("total_ingresos_operacionales")), num(res.get("costo_ventas")),
               num(res.get("total_gastos_operacionales")), num(res.get("utilidad_neta"))),
            "Estado de situacion financiera (%s): ACTIVO=%.2f | PASIVO=%.2f | PATRIMONIO=%.2f | "
            "PASIVO+PATRIMONIO=%.2f" % (estado_json_sit, activo, num(sit.get("total_pasivo")),
                                        num(sit.get("total_patrimonio")), pasivo_patrimonio),
            "  ECUACION: Activo - (Pasivo + Patrimonio) = %.2f (diferencia declarada por el sistema=%s, "
            "balanceado=%s)" % (diferencia, sit.get("diferencia"), sit.get("balanceado")),
            "  vista imprimible del estado: «Ecuacion Activo = Pasivo + Patrimonio» -> %s"
            % (ecuacion_csv or "-"),
        ]
        return ok, evidencias, "Activo %.2f = Pasivo+Patrimonio %.2f (diferencia %.2f)" % (
            activo, pasivo_patrimonio, diferencia)

    # ------------------------------------------------------------------ limpieza
    def limpiar(self):
        acciones = []
        if self.args.sin_limpieza:
            return ["--sin-limpieza: se conservaron los datos de prueba con marcador %s" % MARCADOR]
        asiento = self.creados.get("asiento")
        if asiento:
            ruta, glosa = asiento
            detalles = escribir(ruta, "DELETE FROM detalle_asientos WHERE asiento_id IN "
                                      "(SELECT id FROM asientos WHERE glosa = ?)", (glosa,))
            borrados = escribir(ruta, "DELETE FROM asientos WHERE glosa = ?", (glosa,))
            documentos = escribir(ruta, "DELETE FROM documentos_fuente WHERE numero LIKE ? "
                                        "OR descripcion LIKE ?",
                                  ("%s%%" % MARCADOR, "%s%%" % MARCADOR))
            acciones.append("asiento de prueba borrado de %s (%s asiento(s), %s linea(s), "
                            "%s documento(s) fuente)" % (os.path.basename(ruta), borrados, detalles,
                                                         documentos))
        cuenta = self.creados.get("cuenta")
        if cuenta:
            ruta, codigo = cuenta
            borradas = escribir(ruta, "DELETE FROM cuentas WHERE codigo = ?", (codigo,))
            acciones.append("cuenta %s borrada del aula %s (%s fila(s))"
                            % (codigo, os.path.basename(ruta), borradas))
        evidencia = self.creados.get("evidencia")
        restos = leer(self.control_db,
                      "SELECT id, codigo, titulo FROM evidencias WHERE titulo LIKE ?",
                      ("%s%%" % MARCADOR,))
        if evidencia and not any(r["id"] == evidencia[1] for r in restos):
            restos.append({"id": evidencia[1], "codigo": evidencia[0], "titulo": evidencia[2]})
        for resto in restos:
            versiones = escribir(self.control_db,
                                 "DELETE FROM versiones_evidencia WHERE evidencia_id = ?",
                                 (resto["id"],))
            indice = escribir(self.control_db,
                              "DELETE FROM evidencias_indice WHERE codigo = ?", (resto["codigo"],))
            principal = escribir(self.control_db, "DELETE FROM evidencias WHERE id = ?",
                                 (resto["id"],))
            acciones.append("evidencia %s borrada (evidencias=%s, versiones=%s, evidencias_indice=%s)"
                            % (resto["codigo"], principal, versiones, indice))
        if not acciones:
            acciones.append("no hubo datos de prueba que borrar")
        return acciones

    def cerrar_sesiones(self):
        cerradas = []
        for usuario, datos in self.estudiantes.items():
            if datos.get("cliente"):
                estado, _c, _h = datos["cliente"].get("/logout")
                cerradas.append("%s:%s" % (usuario, estado))
        if self.cliente_docente:
            self.cliente_docente.get("/logout")
        return cerradas

    # ------------------------------------------------------------------ orquestacion
    def ejecutar(self):
        print("=" * 92)
        print(" VERIFICACION FUNCIONAL DE PRODUCCION - %s" % self.base)
        print(" Proyecto: %s" % BASE_DIR)
        print(" Inicio (UTC): %s | marcador de pruebas: %s" % (self.inicio, MARCADOR))
        print("=" * 92)
        print()

        if not self.comprobar_servidor():
            return 1
        if not self.cargar_estudiantes():
            return 1
        if not self.elegir_estudiantes():
            print(" [FALLO] No se pudo iniciar sesion con dos estudiantes del CSV.")
            return 1
        print(" Estudiantes en verificacion: principal=%s (%s asientos en su aula), segundo=%s "
              "(para el aislamiento)" % (self.principal,
                                         self.estudiantes[self.principal]["asientos_iniciales"],
                                         self.otro))
        autenticado = self.autenticar_docente()
        print(" Perfil docente: %s" % (("%s (autenticado)" % self.docente) if autenticado
                                       else "NO se pudo autenticar"))
        print()

        pasos = [
            (1, "ACCESO INDIVIDUAL (cada estudiante entra a su propia empresa/aula)",
             self.punto1_acceso_individual),
            (2, "AISLAMIENTO ENTRE ESTUDIANTES (HTTP y archivos .db)", self.punto2_aislamiento),
            (3, "PANEL DOCENTE (libros en SOLO LECTURA, sin escritura)", self.punto3_panel_docente),
            (4, "REGISTRO DE INGRESOS (sesiones_usuario / eventos_estudiante)",
             self.punto4_registro_ingresos),
            (5, "ACTIVIDADES ASIGNADAS Y AVANCE", self.punto5_actividades),
            (6, "EVIDENCIAS (crear y recuperar por codigo)", self.punto6_evidencias),
            (7, "TRAZABILIDAD (intento rechazado registrado como fallido)", self.punto7_trazabilidad),
            (8, "LIBRO DIARIO (200 y Debe = Haber)", self.punto8_libro_diario),
            (9, "LIBRO MAYOR (200 con movimientos y saldos)", self.punto9_libro_mayor),
            (10, "BALANCE DE COMPROBACION (200 y sumas Debe = sumas Haber)",
             self.punto10_balance_comprobacion),
            (11, "ESTADOS FINANCIEROS (Activo = Pasivo + Patrimonio)",
             self.punto11_estados_financieros),
        ]
        for numero, titulo, funcion in pasos:
            if numero == 8:
                for linea in self.preparar_evidencia_contable():
                    print(linea)
                print()
            try:
                ok, evidencias, cifra = funcion()
            except Exception as error:  # un fallo del propio verificador no debe ocultar el resto
                ok, evidencias, cifra = False, ["EXCEPCION del verificador: %r" % (error,)], "excepcion"
            self.informe.anota(numero, titulo, ok, evidencias, cifra)

        print("-" * 92)
        print(" LIMPIEZA DE DATOS DE PRUEBA")
        for accion in self.limpiar():
            print("   - %s" % accion)
        print("   - rastro de accesos conservado a proposito: sesiones y eventos LOGIN/LOGOUT del "
              "verificador son el registro real que comprueba el punto 4.")
        print("   - sesiones cerradas (GET /logout): %s" % ", ".join(self.cerrar_sesiones()))
        print("-" * 92)
        print(" RESUMEN DE LOS 11 PUNTOS")
        print("-" * 92)
        print("  %-4s %-66s %-5s %s" % ("Nº", "Punto verificado", "Estado", "Cifra clave"))
        for punto in self.informe.puntos:
            print("  %-4s %-66s %-5s %s" % (punto["n"], punto["titulo"][:66],
                                            "OK" if punto["ok"] else "FALLO", punto["cifra"]))
        print("-" * 92)
        print(" RESULTADO: %s de %s puntos OK" % (self.informe.total_ok, len(self.informe.puntos)))
        if self.informe.fallos_reales:
            print(" FALLOS REALES DEL SISTEMA (documentados, NO corregidos por este verificador):")
            for descripcion, evidencia in self.informe.fallos_reales:
                print("   * %s" % descripcion)
                print("     evidencia: %s" % evidencia)
        return 0 if self.informe.total_ok == len(self.informe.puntos) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Verificador funcional de 11 puntos del Simulador Integral de Sistema Contable")
    parser.add_argument("--base", default="http://127.0.0.1:8080",
                        help="URL base del servidor en marcha (por defecto http://127.0.0.1:8080)")
    parser.add_argument("--csv", default=CSV_POR_DEFECTO,
                        help="CSV de credenciales de los estudiantes (usuario/clave)")
    parser.add_argument("--db-control", default=None,
                        help="Ruta de la base de control (por defecto database/simulator.db)")
    parser.add_argument("--docente-usuario", default="docente")
    parser.add_argument("--docente-password", default="docente123")
    parser.add_argument("--muestra", type=int, default=0,
                        help="Cuantos estudiantes del CSV se consideran candidatos "
                             "(0 = todos; se elige el de mas asientos y el de menos)")
    parser.add_argument("--forzar-asiento-prueba", action="store_true",
                        help="Registra siempre un asiento marcado VERIFICACION-PROD (1000.00) "
                             "para comprobar este camino aunque el aula ya tenga movimientos")
    parser.add_argument("--sin-limpieza", action="store_true",
                        help="Conserva los datos de prueba con marcador VERIFICACION-PROD")
    args = parser.parse_args()
    verificador = Verificador(args)
    return verificador.ejecutar()


if __name__ == "__main__":
    sys.exit(main())
