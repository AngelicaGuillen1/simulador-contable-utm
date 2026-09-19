# -*- coding: utf-8 -*-
"""Servicio del módulo de EVIDENCIAS verificables (Contabilidad I).

Cada evidencia es una fotografía firmada del trabajo contable del estudiante:

    * `contenido_json`  -> datos reales tomados de las tablas contables (cuentas, asientos,
                           detalle_asientos) en el momento de generar la evidencia.
    * `huella`          -> SHA-256 del contenido almacenado, que permite comprobar después si
                           alguien modificó la evidencia o los datos que la respaldan.
    * `codigo`          -> CONT1-<PARALELO>-2026-XXXXXXXX (8 hexadecimales en mayúsculas), el
                           código que el docente digita para verificar la evidencia.
    * `versiones_evidencia` -> historial de versiones (la versión 1 se crea al finalizar).

Reglas de honestidad académica: si el estudiante no tiene datos contables, la evidencia se
genera VACÍA y lo indica expresamente; nunca se inventan cifras.
"""

import hashlib
import json
import os
import random
from datetime import datetime

from models import get_db_connection, dict_from_row, dicts_from_rows, ruta_aula
from services.activity_service import ErrorActividad
from services.libros_docente_service import ErrorLibros, abrir_aula_lectura

# --------------------------------------------------------------------------- Constantes
ANIO_CODIGO = 2026
PREFIJO_CODIGO = "CONT1"
TIPOS_EVIDENCIA = ("PLAN_CUENTAS", "DIARIO", "MAYOR", "BALANCE", "INTEGRAL")
ESTADOS_EVIDENCIA = ("BORRADOR", "FINAL", "INVALIDADA")
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"

AVISO_SIN_DATOS = ("La evidencia no contiene datos contables: el estudiante aún no ha registrado "
                   "cuentas ni asientos en el simulador. No se inventan cifras.")


class ErrorEvidencia(ErrorActividad):
    """Error de negocio del módulo de evidencias (mismo contrato que ErrorActividad)."""

    def __init__(self, mensaje, estado_http=400, codigo="VALIDACION"):
        super().__init__(mensaje, estado_http=estado_http, codigo=codigo)


class EvidenciaNoEncontrada(ErrorEvidencia):
    def __init__(self, mensaje="No existe la evidencia solicitada."):
        super().__init__(mensaje, estado_http=404, codigo="EVIDENCIA_INEXISTENTE")


class EvidenciaAjena(ErrorEvidencia):
    """Un estudiante intentó acceder a una evidencia que no le pertenece."""

    def __init__(self, mensaje="La evidencia no pertenece al estudiante autenticado."):
        super().__init__(mensaje, estado_http=403, codigo="EVIDENCIA_AJENA")


class AulaNoLegible(ErrorEvidencia):
    """El aula del estudiante existe pero no se pudo leer en modo lectura."""

    def __init__(self, mensaje="No fue posible leer el aula contable del estudiante.",
                 estado_http=503):
        super().__init__(mensaje, estado_http=estado_http, codigo="AULA_NO_LEGIBLE")


# --------------------------------------------------------------------------- Utilidades
def _ahora():
    return datetime.now()


def _sello_tiempo():
    return _ahora().strftime(FORMATO_FECHA)


def _texto_legible(valor):
    if not valor:
        return None
    return str(valor)[:16]


def _json_determinista(contenido):
    """Serializa el contenido de forma estable (misma entrada -> misma huella)."""
    return json.dumps(contenido, ensure_ascii=False, sort_keys=True, default=str)


def _calcular_huella(texto_json):
    return hashlib.sha256(texto_json.encode("utf-8")).hexdigest()


def _dinero(valor):
    try:
        return "{:,.2f}".format(float(valor or 0))
    except (TypeError, ValueError):
        return "0.00"


def _saldo_texto(cuenta):
    """Saldo en formato legible: monto deudor o con la marca A (acreedor)."""
    deudor = cuenta.get("saldo_deudor") or 0
    acreedor = cuenta.get("saldo_acreedor") or 0
    if deudor:
        return _dinero(deudor)
    if acreedor:
        return "A " + _dinero(acreedor)
    return _dinero(0)


def _tabla_texto(columnas, filas):
    """Renders a fixed-width table for the printable/captured version of the evidence."""
    columnas = [str(c) for c in columnas]
    filas = [[("" if v is None else str(v)) for v in fila] for fila in filas]
    if not filas:
        return ["(sin registros)"]
    anchos = [len(c) for c in columnas]
    for fila in filas:
        for i, valor in enumerate(fila):
            if i < len(anchos):
                anchos[i] = max(anchos[i], len(valor))
    cabecera = " | ".join(c.ljust(anchos[i]) for i, c in enumerate(columnas))
    separador = "-+-".join("-" * a for a in anchos)
    cuerpo = [" | ".join(v.ljust(anchos[i]) if i < len(anchos) else v
                         for i, v in enumerate(fila)) for fila in filas]
    return [cabecera, separador] + cuerpo


def _empresa_de_estudiante(conn, estudiante_id):
    """Empresa simulada del estudiante (con respaldo en la empresa de demostración del curso)."""
    fila = conn.execute(
        "SELECT id FROM empresas WHERE estudiante_id = ? ORDER BY id LIMIT 1",
        (estudiante_id,)).fetchone()
    if fila:
        return fila["id"]
    fila = conn.execute("SELECT id FROM empresas ORDER BY IFNULL(es_demo, 0) DESC, id ASC LIMIT 1").fetchone()
    return fila["id"] if fila else None


# --------------------------------------------------------------------------- Código único
def generar_codigo(paralelo=None, db_path=None, anio=None):
    """Genera un código único de evidencia: CONT1-<PARALELO>-<AÑO>-XXXXXXXX.

    El bloque final son 8 caracteres hexadecimales EN MAYÚSCULAS. Se reintenta hasta
    garantizar que el código no exista ya en la tabla `evidencias`.
    """
    limpio = "".join(ch for ch in str(paralelo or "A").strip().upper() if ch.isalnum())[:3]
    paralelo_txt = limpio or "A"
    anio_txt = str(anio or ANIO_CODIGO)

    conn = get_db_connection(db_path)
    try:
        for _ in range(50):
            sufijo = "%08X" % random.getrandbits(32)
            codigo = "%s-%s-%s-%s" % (PREFIJO_CODIGO, paralelo_txt, anio_txt, sufijo)
            existe = conn.execute("SELECT 1 FROM evidencias WHERE codigo = ?", (codigo,)).fetchone()
            if not existe:
                return codigo
        raise ErrorEvidencia("No fue posible generar un código de evidencia único.",
                             estado_http=500, codigo="CODIGO_NO_DISPONIBLE")
    finally:
        conn.close()


def paralelo_de_estudiante(estudiante_id, db_path=None):
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("SELECT paralelo FROM usuarios WHERE id = ?", (estudiante_id,)).fetchone()
        return (fila["paralelo"] if fila and fila["paralelo"] else None) or "A"
    finally:
        conn.close()


# --------------------------------------------------------------------------- Aula del estudiante
def resolver_libros(estudiante_id, db_path=None, aula_path=None):
    """Resuelve DÓNDE están los libros del estudiante (su aula) y de dónde se leerán.

    Devuelve::

        {'aula': ruta o None, 'usa_aula': bool,
         'fuente': 'AULA_ESTUDIANTE' | 'BASE_CONTROL',
         'archivo': nombre del archivo o None, 'aviso': texto o None}

    Reglas (ver docs/DISENO_MULTIESTUDIANTE.md):

    1. ``aula_path`` explícito manda: el docente puede pedir la evidencia de un estudiante
       concreto indicando su archivo (se verifica que exista; si no existe se avisa con un
       error claro en lugar de mostrar cifras de otra empresa).
    2. Si no, el aula se resuelve con ``models.ruta_aula(username, paralelo)``, tomando el
       usuario y el paralelo de la tabla ``usuarios`` de la base de control.
    3. Si el estudiante no tiene aula (cuentas de demostración), los libros se leen de la
       base de control, como antes.
    """
    if aula_path:
        if os.path.exists(aula_path):
            return {"aula": aula_path, "usa_aula": True, "fuente": "AULA_ESTUDIANTE",
                    "archivo": os.path.basename(aula_path), "aviso": None}
        raise AulaNoLegible("No existe el aula indicada: %s" % aula_path, estado_http=404)

    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("SELECT username, paralelo FROM usuarios WHERE id = ?",
                            (estudiante_id,)).fetchone()
    finally:
        conn.close()

    if fila and fila["username"]:
        for paralelo in (fila["paralelo"], None):
            ruta = ruta_aula(fila["username"], paralelo)
            if ruta and os.path.exists(ruta):
                return {"aula": ruta, "usa_aula": True, "fuente": "AULA_ESTUDIANTE",
                        "archivo": os.path.basename(ruta), "aviso": None}

    return {"aula": None, "usa_aula": False, "fuente": "BASE_CONTROL", "archivo": None,
            "aviso": ("El estudiante no tiene aula contable propia: los libros se leen de la "
                      "base de control (empresa de demostración).")}


def conexion_libros(resolucion, db_path=None):
    """Conexión de lectura a los libros: el aula en modo lectura o, si no hay, la de control.

    El aula SIEMPRE se abre en modo lectura (``file:...?mode=ro``): generar una evidencia
    nunca puede modificar el trabajo del estudiante.
    """
    if resolucion.get("usa_aula") and resolucion.get("aula"):
        try:
            return abrir_aula_lectura(resolucion["aula"])
        except ErrorLibros as error:
            raise AulaNoLegible("No fue posible abrir el aula del estudiante en modo lectura: %s"
                                % error)
    return get_db_connection(db_path)


# --------------------------------------------------------------------------- Datos reales
def _datos_cuentas(conn):
    filas = conn.execute("""
        SELECT codigo, nombre, clasificacion, naturaleza, nivel, acepta_movimiento
        FROM cuentas
        WHERE activo = 1
        ORDER BY codigo
    """).fetchall()
    return [dict(f) for f in filas]


def _datos_movimientos(conn, empresa_id):
    """Asientos contabilizados del estudiante con el detalle de sus líneas."""
    if empresa_id is None:
        return [], []
    asientos = conn.execute("""
        SELECT id, numero_asiento, fecha, glosa, tipo_documento, numero_documento, estado
        FROM asientos
        WHERE empresa_id = ? AND UPPER(IFNULL(estado, '')) NOT IN ('ANULADO', 'REVERTIDO')
        ORDER BY fecha ASC, id ASC
    """, (empresa_id,)).fetchall()
    if not asientos:
        return [], []

    ids = [a["id"] for a in asientos]
    marcadores = ",".join("?" for _ in ids)
    lineas = [dict(l) for l in conn.execute("""
        SELECT d.asiento_id, d.cuenta_id, c.codigo, c.nombre, c.clasificacion, c.naturaleza,
               d.debe, d.haber, d.referencia
        FROM detalle_asientos d
        JOIN cuentas c ON c.id = d.cuenta_id
        WHERE d.asiento_id IN (%s)
        ORDER BY d.asiento_id, d.id
    """ % marcadores, ids).fetchall()]

    por_asiento = {}
    for linea in lineas:
        por_asiento.setdefault(linea["asiento_id"], []).append(linea)

    diario = []
    for asiento in asientos:
        registro = dict(asiento)
        lineas_asiento = por_asiento.get(asiento["id"], [])
        debe = round(sum(l["debe"] or 0 for l in lineas_asiento), 2)
        haber = round(sum(l["haber"] or 0 for l in lineas_asiento), 2)
        registro.update({"lineas": lineas_asiento, "total_debe": debe, "total_haber": haber,
                         "cuadrado": abs(debe - haber) < 0.01})
        diario.append(registro)
    return diario, lineas


def _mayor_y_balance(cuentas, lineas):
    """Construye el Libro Mayor y el Balance de comprobación a partir de las líneas reales."""
    indice = {c["codigo"]: c for c in cuentas}
    acumulado = {}
    for linea in lineas:
        codigo = linea["codigo"]
        datos = acumulado.setdefault(codigo, {
            "codigo": codigo,
            "nombre": linea["nombre"],
            "clasificacion": linea.get("clasificacion"),
            "naturaleza": linea.get("naturaleza") or indice.get(codigo, {}).get("naturaleza"),
            "debitos": 0.0, "creditos": 0.0, "movimientos": [],
        })
        datos["debitos"] = round(datos["debitos"] + (linea["debe"] or 0), 2)
        datos["creditos"] = round(datos["creditos"] + (linea["haber"] or 0), 2)
        if (linea["debe"] or 0) or (linea["haber"] or 0):
            datos["movimientos"].append({
                "debe": round(linea["debe"] or 0, 2),
                "haber": round(linea["haber"] or 0, 2),
                "referencia": linea.get("referencia"),
            })

    mayor, balance = [], []
    for codigo in sorted(acumulado):
        datos = acumulado[codigo]
        # El saldo se presenta como en un balance de comprobación de sumas y saldos:
        # diferencia Debe - Haber con su signo; las columnas de saldo deudor/acreedor
        # reflejan el lado en que queda el saldo.
        saldo = round(datos["debitos"] - datos["creditos"], 2)
        entrada = {
            "codigo": codigo,
            "nombre": datos["nombre"],
            "clasificacion": datos.get("clasificacion"),
            "naturaleza": datos.get("naturaleza"),
            "debitos": datos["debitos"],
            "creditos": datos["creditos"],
            "saldo": saldo,
            "saldo_deudor": saldo if saldo > 0 else 0.0,
            "saldo_acreedor": round(-saldo, 2) if saldo < 0 else 0.0,
        }
        balance.append(entrada)
        mayor.append(dict(entrada, movimientos=datos["movimientos"]))
    return mayor, balance


def recolectar_datos_contables(empresa_id, db_path=None, tipos=None, conn=None):
    """Toma los datos REALES del estudiante desde las tablas contables.

    Devuelve un diccionario con las secciones disponibles (cuentas, asientos, lineas,
    mayor, balance). Si no hay datos, las secciones quedan vacías.

    `db_path` puede ser la ruta del aula del estudiante (lo habitual en modo
    multiestudiante) o la base de control (modo demostración). Con `conn` se reutiliza una
    conexión ya abierta (permite leer el aula en modo lectura).
    """
    tipos = set(tipos or TIPOS_EVIDENCIA)
    if conn is not None:
        return _recolectar(conn, empresa_id, tipos)
    conexion = get_db_connection(db_path)
    try:
        return _recolectar(conexion, empresa_id, tipos)
    finally:
        conexion.close()


def _recolectar(conn, empresa_id, tipos):
    cuentas = _datos_cuentas(conn) if tipos & {"PLAN_CUENTAS", "BALANCE", "MAYOR", "INTEGRAL"} else []
    diario, lineas = _datos_movimientos(conn, empresa_id) if tipos & {"DIARIO", "MAYOR", "BALANCE", "INTEGRAL"} else ([], [])
    mayor, balance = _mayor_y_balance(cuentas, lineas) if tipos & {"MAYOR", "BALANCE", "INTEGRAL"} else ([], [])
    return {"cuentas": cuentas, "asientos": diario, "lineas": lineas,
            "mayor": mayor, "balance": balance}


# --------------------------------------------------------------------------- Contenido
def construir_contenido_contable(estudiante_id, tipo, actividad_id=None, empresa_id=None,
                                 db_path=None, aula_path=None):
    """Arma el contenido (diccionario serializable) de una evidencia a partir de los datos reales.

    Las cifras se leen del **aula del estudiante** (``db_path`` apunta a la base de control
    donde vive la tabla `usuarios`; el aula se resuelve con `resolver_libros`). Si el
    estudiante no tiene aula (cuentas de demostración) se leen de la base de control, como
    antes. Con ``aula_path`` el docente puede pedir la evidencia de un estudiante concreto
    indicando el archivo de su aula.
    """
    tipo = str(tipo or "INTEGRAL").strip().upper()
    if tipo not in TIPOS_EVIDENCIA:
        raise ErrorEvidencia("Tipo de evidencia inválido: %s (use %s)."
                             % (tipo, ", ".join(TIPOS_EVIDENCIA)))

    # 1. Base de CONTROL: quién es el estudiante y a qué actividad corresponde la evidencia.
    conn = get_db_connection(db_path)
    try:
        estudiante = conn.execute(
            "SELECT id, username, nombre_completo, paralelo FROM usuarios WHERE id = ?",
            (estudiante_id,)).fetchone()
        actividad = None
        if actividad_id:
            actividad = conn.execute(
                "SELECT id, codigo, titulo, unidad, componente FROM actividades WHERE id = ?",
                (actividad_id,)).fetchone()
    finally:
        conn.close()

    # 2. Libros: el aula del estudiante (modo lectura) o, si no tiene, la base de control.
    resolucion = resolver_libros(estudiante_id, db_path=db_path, aula_path=aula_path)
    conn_libros = conexion_libros(resolucion, db_path=db_path)
    try:
        if empresa_id is None:
            empresa_id = _empresa_de_estudiante(conn_libros, estudiante_id)
        datos = recolectar_datos_contables(empresa_id, tipos={tipo}, conn=conn_libros)
    finally:
        conn_libros.close()

    contenido = {
        "tipo": tipo,
        "estudiante": dict(estudiante) if estudiante else None,
        "actividad": dict(actividad) if actividad else None,
        "empresa_id": empresa_id,
        "generado_en": _sello_tiempo(),
        "origen": "SIMULADOR_CONTABLE",
        "origen_datos": {
            "fuente": resolucion["fuente"],
            "archivo": resolucion["archivo"],
            "aviso": resolucion["aviso"],
        },
        "datos": datos,
    }
    contenido["resumen"] = resumen_desde_contenido(contenido)["texto"]
    return contenido


# --------------------------------------------------------------------------- Resumen
def resumen_desde_contenido(contenido, tipo=None):
    """Construye el texto de la evidencia según su tipo a partir del contenido dado.

    Devuelve {'tipo', 'texto', 'secciones', 'vacio', 'aviso'} donde `secciones` es una lista
    de {'titulo', 'columnas', 'filas'} lista para pintar en HTML o exportar a PDF.
    """
    contenido = contenido if isinstance(contenido, dict) else {}
    tipo = str(tipo or contenido.get("tipo") or "INTEGRAL").strip().upper()
    datos = contenido.get("datos") or {}
    cuentas = datos.get("cuentas") or []
    asientos = datos.get("asientos") or []
    mayor = datos.get("mayor") or []
    balance = datos.get("balance") or []

    quiere_cuentas = tipo in ("PLAN_CUENTAS", "INTEGRAL")
    quiere_diario = tipo in ("DIARIO", "INTEGRAL")
    quiere_mayor = tipo in ("MAYOR", "INTEGRAL")
    quiere_balance = tipo in ("BALANCE", "INTEGRAL")

    secciones = []

    if quiere_cuentas:
        filas = [[c.get("codigo"), c.get("nombre"), c.get("clasificacion") or "—",
                  c.get("naturaleza") or "—"] for c in cuentas]
        secciones.append({"titulo": "Plan de cuentas (código, nombre, clasificación y naturaleza)",
                          "columnas": ["Código", "Cuenta", "Clasificación", "Naturaleza"],
                          "filas": filas})

    if quiere_diario:
        filas = []
        for asiento in asientos:
            for linea in (asiento.get("lineas") or []):
                filas.append([
                    asiento.get("fecha"), asiento.get("glosa"),
                    "%s %s" % (linea.get("codigo"), linea.get("nombre")),
                    _dinero(linea.get("debe")), _dinero(linea.get("haber")),
                ])
        secciones.append({"titulo": "Libro Diario (fecha, concepto, cuentas, Debe y Haber)",
                          "columnas": ["Fecha", "Concepto", "Cuenta", "Debe", "Haber"],
                          "filas": filas})

    if quiere_mayor:
        filas = []
        for cuenta in mayor:
            filas.append([cuenta.get("codigo"), cuenta.get("nombre"),
                          _dinero(cuenta.get("debitos")), _dinero(cuenta.get("creditos")),
                          _saldo_texto(cuenta)])
            for movimiento in (cuenta.get("movimientos") or []):
                filas.append(["", "   movimiento: %s" % (movimiento.get("referencia") or "—"),
                              _dinero(movimiento.get("debe")), _dinero(movimiento.get("haber")), ""])
        secciones.append({"titulo": "Libro Mayor (cuenta, movimientos y saldo)",
                          "columnas": ["Código", "Cuenta / movimiento", "Debe", "Haber", "Saldo"],
                          "filas": filas})

    if quiere_balance:
        filas = [[cuenta.get("codigo"), cuenta.get("nombre"),
                  _dinero(cuenta.get("debitos")), _dinero(cuenta.get("creditos")),
                  _dinero(cuenta.get("saldo_deudor")), _dinero(cuenta.get("saldo_acreedor"))]
                 for cuenta in balance]
        total_debe = round(sum(c.get("debitos") or 0 for c in balance), 2)
        total_haber = round(sum(c.get("creditos") or 0 for c in balance), 2)
        total_deudor = round(sum(c.get("saldo_deudor") or 0 for c in balance), 2)
        total_acreedor = round(sum(c.get("saldo_acreedor") or 0 for c in balance), 2)
        filas.append(["", "TOTALES", _dinero(total_debe), _dinero(total_haber),
                      _dinero(total_deudor), _dinero(total_acreedor)])
        secciones.append({"titulo": "Balance de comprobación (cuentas, débitos, créditos y saldos)",
                          "columnas": ["Código", "Cuenta", "Débitos", "Créditos",
                                       "Saldo deudor", "Saldo acreedor"],
                          "filas": filas})

    hay_datos = any(seccion["filas"] for seccion in secciones)
    vacio = not hay_datos

    cabecera = []
    estudiante = contenido.get("estudiante") or {}
    actividad = contenido.get("actividad") or {}
    if estudiante:
        cabecera.append("Estudiante: %s (%s)" % (estudiante.get("nombre_completo"),
                                                 estudiante.get("username")))
    if actividad:
        cabecera.append("Actividad: %s · %s" % (actividad.get("codigo"), actividad.get("titulo")))
    cabecera.append("Tipo de evidencia: %s" % tipo)
    cabecera.append("Generada en: %s" % (contenido.get("generado_en") or "—"))
    origen_datos = contenido.get("origen_datos") or {}
    if origen_datos.get("fuente") == "AULA_ESTUDIANTE":
        cabecera.append("Cifras leídas del aula propia del estudiante (%s)."
                        % (origen_datos.get("archivo") or "archivo de su aula"))
    elif origen_datos.get("fuente") == "BASE_CONTROL":
        cabecera.append("Cifras leídas de la base de control (empresa de demostración).")

    bloques = list(cabecera)
    if vacio:
        bloques.append("")
        bloques.append(AVISO_SIN_DATOS)
    for seccion in secciones:
        bloques.append("")
        bloques.append("== %s ==" % seccion["titulo"])
        bloques.extend(_tabla_texto(seccion["columnas"], seccion["filas"]))

    return {"tipo": tipo, "texto": "\n".join(bloques), "secciones": secciones,
            "vacio": vacio, "aviso": AVISO_SIN_DATOS if vacio else None,
            "cabecera": cabecera}


def resumen_texto_plano(evidencia_id, db_path=None):
    """Texto plano del resumen de una evidencia almacenada."""
    return resumen_evidencia(evidencia_id, db_path=db_path)["texto"]


def resumen_evidencia(evidencia_id, db_path=None):
    """Resumen de la evidencia guardada, con los datos reales tomados de las tablas contables.

    Si la evidencia no guardó contenido, el resumen se construye con los datos actuales del
    estudiante (que pueden estar vacíos: en ese caso se indica expresamente).
    """
    evidencia = obtener_evidencia(evidencia_id, db_path=db_path)
    if not evidencia:
        raise EvidenciaNoEncontrada("No existe la evidencia %s." % evidencia_id)

    contenido = {}
    if evidencia.get("contenido_json"):
        try:
            contenido = json.loads(evidencia["contenido_json"])
        except (TypeError, ValueError):
            contenido = {}

    if not (contenido.get("datos") and (contenido["datos"].get("cuentas")
                                        or contenido["datos"].get("asientos"))):
        contenido = construir_contenido_contable(
            evidencia["estudiante_id"], evidencia.get("tipo") or "INTEGRAL",
            actividad_id=evidencia.get("actividad_id"),
            empresa_id=evidencia.get("empresa_id"), db_path=db_path)

    resumen = resumen_desde_contenido(contenido, tipo=evidencia.get("tipo"))
    resumen.update({
        "evidencia_id": evidencia["id"],
        "codigo": evidencia["codigo"],
        "titulo": evidencia.get("titulo"),
        "estado": evidencia.get("estado"),
        "estudiante_id": evidencia.get("estudiante_id"),
        "actividad_id": evidencia.get("actividad_id"),
        "generada_en": evidencia.get("generada_en"),
        "huella": evidencia.get("huella"),
        "modificada_despues": bool(evidencia.get("modificada_despues")),
    })
    return resumen


# --------------------------------------------------------------------------- CRUD
def obtener_evidencia(evidencia_id, db_path=None):
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("""
            SELECT e.*, a.codigo AS actividad_codigo, a.titulo AS actividad_titulo,
                   a.unidad AS actividad_unidad, a.componente AS actividad_componente,
                   u.username, u.nombre_completo AS estudiante_nombre, u.paralelo
            FROM evidencias e
            LEFT JOIN actividades a ON a.id = e.actividad_id
            LEFT JOIN usuarios u ON u.id = e.estudiante_id
            WHERE e.id = ?
        """, (evidencia_id,)).fetchone()
        return dict_from_row(fila)
    finally:
        conn.close()


def obtener_evidencia_de_estudiante(evidencia_id, estudiante_id, db_path=None):
    """Evidencia propia del estudiante; lanza EvidenciaAjena/NoEncontrada si no corresponde.

    Es el candado de aislamiento: ninguna ruta de estudiante puede leer ni modificar la
    evidencia de otro compañero.
    """
    evidencia = obtener_evidencia(evidencia_id, db_path=db_path)
    if not evidencia:
        raise EvidenciaNoEncontrada("No existe la evidencia %s." % evidencia_id)
    if int(evidencia["estudiante_id"]) != int(estudiante_id):
        raise EvidenciaAjena("La evidencia %s pertenece a otro estudiante." % evidencia_id)
    return evidencia


def crear_evidencia(estudiante_id, actividad_id, tipo, titulo, resumen_texto=None,
                    contenido_dict=None, empresa_id=None, estado="BORRADOR", db_path=None,
                    aula_path=None):
    """Crea una evidencia (BORRADOR o FINAL) y calcula su huella SHA-256.

    `contenido_dict` puede venir como diccionario (se serializa con ensure_ascii=False) o
    directamente como texto JSON. Si no se entrega contenido, se toma una fotografía de los
    datos contables reales del estudiante: sus libros se leen de **su aula** (resuelta con
    `resolver_libros`, o del archivo indicado en `aula_path`) y la evidencia se guarda en la
    **base de control** (`db_path`).
    """
    tipo = str(tipo or "INTEGRAL").strip().upper()
    if tipo not in TIPOS_EVIDENCIA:
        raise ErrorEvidencia("Tipo de evidencia inválido: %s (use %s)."
                             % (tipo, ", ".join(TIPOS_EVIDENCIA)))
    estado = str(estado or "BORRADOR").strip().upper()
    if estado not in ESTADOS_EVIDENCIA:
        raise ErrorEvidencia("Estado de evidencia inválido: %s (use %s)."
                             % (estado, ", ".join(ESTADOS_EVIDENCIA)))
    if not titulo:
        raise ErrorEvidencia("El título de la evidencia es obligatorio.")

    if contenido_dict is None:
        contenido_dict = construir_contenido_contable(
            estudiante_id, tipo, actividad_id=actividad_id, empresa_id=empresa_id,
            db_path=db_path, aula_path=aula_path)

    if isinstance(contenido_dict, str):
        contenido_json = contenido_dict
    else:
        contenido_json = _json_determinista(contenido_dict)

    huella = _calcular_huella(contenido_json)

    if resumen_texto is None:
        try:
            resumen_texto = resumen_desde_contenido(json.loads(contenido_json), tipo=tipo)["texto"]
        except (TypeError, ValueError):
            resumen_texto = ""

    codigo = generar_codigo(paralelo_de_estudiante(estudiante_id, db_path=db_path), db_path=db_path)

    conn = get_db_connection(db_path)
    try:
        if not empresa_id:
            empresa_id = _empresa_de_estudiante(conn, estudiante_id)
        if actividad_id:
            existe = conn.execute("SELECT 1 FROM actividades WHERE id = ?", (actividad_id,)).fetchone()
            if not existe:
                raise ErrorEvidencia("No existe la actividad %s." % actividad_id,
                                     estado_http=404, codigo="ACTIVIDAD_INEXISTENTE")
        cursor = conn.execute("""
            INSERT INTO evidencias (codigo, actividad_id, estudiante_id, empresa_id, titulo, tipo,
                                    resumen_texto, contenido_json, huella, estado, modificada_despues,
                                    generada_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (codigo, actividad_id, estudiante_id, empresa_id, titulo, tipo, resumen_texto,
              contenido_json, huella, estado, _sello_tiempo()))
        evidencia_id = cursor.lastrowid
        conn.commit()
        fila = conn.execute("""
            SELECT e.*, u.username, u.nombre_completo AS estudiante_nombre, u.paralelo
            FROM evidencias e LEFT JOIN usuarios u ON u.id = e.estudiante_id
            WHERE e.id = ?
        """, (evidencia_id,)).fetchone()
        creada = dict_from_row(fila)
    finally:
        conn.close()

    if estado == "FINAL":
        finalizar_evidencia(evidencia_id, db_path=db_path)
        creada = obtener_evidencia(evidencia_id, db_path=db_path)
    return creada


def finalizar_evidencia(evidencia_id, db_path=None):
    """Marca la evidencia como FINAL, guarda su huella y fecha, y crea la versión 1."""
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("SELECT * FROM evidencias WHERE id = ?", (evidencia_id,)).fetchone()
        if not fila:
            raise EvidenciaNoEncontrada("No existe la evidencia %s." % evidencia_id)

        evidencia = dict(fila)
        contenido_json = evidencia.get("contenido_json") or ""
        huella = _calcular_huella(contenido_json)
        sello = _sello_tiempo()

        conn.execute("""
            UPDATE evidencias
               SET estado = 'FINAL', huella = ?, generada_en = ?, modificada_despues = 0
             WHERE id = ?
        """, (huella, sello, evidencia_id))

        existe_version = conn.execute(
            "SELECT 1 FROM versiones_evidencia WHERE evidencia_id = ? AND version = 1",
            (evidencia_id,)).fetchone()
        if not existe_version:
            conn.execute("""
                INSERT INTO versiones_evidencia (evidencia_id, version, contenido_json, huella, motivo,
                                                 generada_en)
                VALUES (?, 1, ?, ?, ?, ?)
            """, (evidencia_id, contenido_json, huella,
                  "Generación inicial de la evidencia verificable", sello))
        conn.commit()
    finally:
        conn.close()

    return obtener_evidencia(evidencia_id, db_path=db_path)


def detectar_modificacion(evidencia_id, contenido_actual=None, db_path=None):
    """Comprueba si la evidencia cambió después de ser finalizada.

    Recalcula la huella del contenido actual y la compara con la huella base guardada.
    Si difieren, marca `modificada_despues = 1` y devuelve True.

    `contenido_actual` permite comparar contra un contenido externo (por ejemplo, el que se
    recalcula desde las tablas contables); si no se entrega, se usa el contenido almacenado.
    """
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("SELECT * FROM evidencias WHERE id = ?", (evidencia_id,)).fetchone()
        if not fila:
            raise EvidenciaNoEncontrada("No existe la evidencia %s." % evidencia_id)

        evidencia = dict(fila)
        if contenido_actual is None:
            texto = evidencia.get("contenido_json") or ""
        elif isinstance(contenido_actual, str):
            texto = contenido_actual
        else:
            texto = _json_determinista(contenido_actual)

        huella_actual = _calcular_huella(texto)
        huella_base = evidencia.get("huella")

        if not huella_base:
            # Una evidencia sin huella base todavía no es verificable: no se marca como alterada.
            return False

        modificada = huella_actual != huella_base
        if modificada and not evidencia.get("modificada_despues"):
            conn.execute("UPDATE evidencias SET modificada_despues = 1 WHERE id = ?", (evidencia_id,))
            conn.commit()
        return modificada
    finally:
        conn.close()


def nueva_version(evidencia_id, motivo=None, contenido_dict=None, db_path=None):
    """Crea la siguiente versión de la evidencia y actualiza la huella base.

    Se usa cuando el estudiante corrige su trabajo después de haber generado la evidencia:
    el historial conserva lo anterior y la evidencia vuelve a quedar verificable.
    """
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("SELECT * FROM evidencias WHERE id = ?", (evidencia_id,)).fetchone()
        if not fila:
            raise EvidenciaNoEncontrada("No existe la evidencia %s." % evidencia_id)

        evidencia = dict(fila)
        if contenido_dict is None:
            contenido_json = evidencia.get("contenido_json") or ""
        elif isinstance(contenido_dict, str):
            contenido_json = contenido_dict
        else:
            contenido_json = _json_determinista(contenido_dict)

        ultima = conn.execute(
            "SELECT MAX(version) AS v FROM versiones_evidencia WHERE evidencia_id = ?",
            (evidencia_id,)).fetchone()
        version = int((ultima["v"] if ultima and ultima["v"] else 0)) + 1
        huella = _calcular_huella(contenido_json)
        sello = _sello_tiempo()

        conn.execute("""
            INSERT INTO versiones_evidencia (evidencia_id, version, contenido_json, huella, motivo,
                                             generada_en)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (evidencia_id, version, contenido_json, huella,
              motivo or "Nueva versión de la evidencia", sello))

        conn.execute("""
            UPDATE evidencias
               SET contenido_json = ?, huella = ?, generada_en = ?, modificada_despues = 0
             WHERE id = ?
        """, (contenido_json, huella, sello, evidencia_id))
        conn.commit()

        resultado = dict_from_row(conn.execute(
            "SELECT * FROM evidencias WHERE id = ?", (evidencia_id,)).fetchone())
        resultado["version"] = version
        resultado["motivo"] = motivo or "Nueva versión de la evidencia"
        return resultado
    finally:
        conn.close()


def versiones(evidencia_id, db_path=None):
    conn = get_db_connection(db_path)
    try:
        filas = conn.execute("""
            SELECT version, huella, motivo, generada_en
            FROM versiones_evidencia WHERE evidencia_id = ? ORDER BY version DESC
        """, (evidencia_id,)).fetchall()
        return dicts_from_rows(filas)
    finally:
        conn.close()


def verificar_codigo(codigo, db_path=None):
    """Verificación docente: devuelve todo lo necesario para validar una evidencia impresa.

    Incluye estudiante, actividad, fecha de generación, estado, si fue modificada después y el
    resumen del contenido. Devuelve None si el código no existe.
    """
    codigo = str(codigo or "").strip().upper()
    if not codigo:
        return None

    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("""
            SELECT e.*, a.codigo AS actividad_codigo, a.titulo AS actividad_titulo,
                   a.unidad AS actividad_unidad, a.componente AS actividad_componente,
                   u.username, u.nombre_completo AS estudiante_nombre, u.paralelo,
                   u.email AS estudiante_email
            FROM evidencias e
            LEFT JOIN actividades a ON a.id = e.actividad_id
            LEFT JOIN usuarios u ON u.id = e.estudiante_id
            WHERE UPPER(e.codigo) = ?
        """, (codigo,)).fetchone()
        if not fila:
            return None
        evidencia = dict(fila)
        total_versiones = conn.execute(
            "SELECT COUNT(*) AS n FROM versiones_evidencia WHERE evidencia_id = ?",
            (evidencia["id"],)).fetchone()["n"]
    finally:
        conn.close()

    modificar = detectar_modificacion(evidencia["id"], db_path=db_path)

    resumen = ""
    try:
        resumen = resumen_evidencia(evidencia["id"], db_path=db_path)["texto"]
    except ErrorEvidencia:
        resumen = ""

    return {
        "codigo": evidencia["codigo"],
        "evidencia_id": evidencia["id"],
        "valida": bool(evidencia.get("estado") == "FINAL" and not modificar),
        "estado": evidencia.get("estado"),
        "modificada_despues": bool(modificar),
        "fecha_generacion": evidencia.get("generada_en"),
        "huella": evidencia.get("huella"),
        "tipo": evidencia.get("tipo"),
        "titulo": evidencia.get("titulo"),
        "resumen": resumen,
        "resumen_texto": evidencia.get("resumen_texto"),
        "total_versiones": int(total_versiones or 0),
        "estudiante": {
            "id": evidencia.get("estudiante_id"),
            "username": evidencia.get("username"),
            "nombre_completo": evidencia.get("estudiante_nombre"),
            "paralelo": evidencia.get("paralelo"),
            "email": evidencia.get("estudiante_email"),
        },
        "actividad": {
            "id": evidencia.get("actividad_id"),
            "codigo": evidencia.get("actividad_codigo"),
            "titulo": evidencia.get("actividad_titulo"),
            "unidad": evidencia.get("actividad_unidad"),
            "componente": evidencia.get("actividad_componente"),
        },
    }


def listar_evidencias_estudiante(estudiante_id, db_path=None, actividad_id=None):
    conn = get_db_connection(db_path)
    try:
        parametros = [estudiante_id]
        filtro = ""
        if actividad_id:
            filtro = " AND e.actividad_id = ?"
            parametros.append(int(actividad_id))
        filas = conn.execute("""
            SELECT e.*, a.codigo AS actividad_codigo, a.titulo AS actividad_titulo,
                   (SELECT COUNT(*) FROM versiones_evidencia v WHERE v.evidencia_id = e.id) AS versiones
            FROM evidencias e
            LEFT JOIN actividades a ON a.id = e.actividad_id
            WHERE e.estudiante_id = ? %s
            ORDER BY e.generada_en DESC, e.id DESC
        """ % filtro, parametros).fetchall()
        return dicts_from_rows(filas)
    finally:
        conn.close()


def listar_evidencias_docente(filtros=None, db_path=None):
    """Listado de evidencias para el docente (todos los estudiantes), con filtros."""
    filtros = filtros or {}
    condiciones, parametros = [], []
    if filtros.get("estudiante_id"):
        condiciones.append("e.estudiante_id = ?")
        parametros.append(int(filtros["estudiante_id"]))
    if filtros.get("actividad_id"):
        condiciones.append("e.actividad_id = ?")
        parametros.append(int(filtros["actividad_id"]))
    if filtros.get("estado"):
        condiciones.append("UPPER(e.estado) = ?")
        parametros.append(str(filtros["estado"]).strip().upper())
    if filtros.get("modificadas") in (True, "1", 1, "true"):
        condiciones.append("e.modificada_despues = 1")
    if filtros.get("q"):
        condiciones.append("(e.codigo LIKE ? OR e.titulo LIKE ? OR u.nombre_completo LIKE ?)")
        patron = "%%%s%%" % str(filtros["q"]).strip()
        parametros.extend([patron, patron, patron])
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    conn = get_db_connection(db_path)
    try:
        filas = conn.execute("""
            SELECT e.*, a.codigo AS actividad_codigo, a.titulo AS actividad_titulo,
                   u.username, u.nombre_completo AS estudiante_nombre, u.paralelo,
                   (SELECT COUNT(*) FROM versiones_evidencia v WHERE v.evidencia_id = e.id) AS versiones
            FROM evidencias e
            LEFT JOIN actividades a ON a.id = e.actividad_id
            LEFT JOIN usuarios u ON u.id = e.estudiante_id
            %s
            ORDER BY e.generada_en DESC, e.id DESC
        """ % where, parametros).fetchall()
        return dicts_from_rows(filas)
    finally:
        conn.close()


def nombre_archivo_evidencia(evidencia):
    return "evidencia_%s.pdf" % str(evidencia.get("codigo") or evidencia.get("id")).replace("/", "-")


def exportar_pdf(evidencia_id, ruta, db_path=None):
    """Genera un PDF sencillo con reportlab.

    Devuelve la ruta del archivo si reportlab está instalado y el PDF se generó; devuelve None
    si reportlab no está disponible, para que la interfaz use la vista imprimible HTML.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        return None

    evidencia = obtener_evidencia(evidencia_id, db_path=db_path)
    if not evidencia:
        raise EvidenciaNoEncontrada("No existe la evidencia %s." % evidencia_id)

    resumen = resumen_evidencia(evidencia_id, db_path=db_path)

    try:
        carpeta = os.path.dirname(os.path.abspath(ruta))
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        lienzo = canvas.Canvas(ruta, pagesize=A4)
        ancho, alto = A4
        x = 18 * mm
        y = alto - 22 * mm

        lienzo.setFont("Helvetica-Bold", 13)
        lienzo.drawString(x, y, "SIMULADOR INTEGRAL DE SISTEMA CONTABLE")
        y -= 6 * mm
        lienzo.setFont("Helvetica", 9)
        lienzo.drawString(x, y, "Comercial y Servicios Nueva Esperanza S.A. - Entorno academico")
        y -= 8 * mm
        lienzo.setFont("Helvetica-Bold", 11)
        lienzo.drawString(x, y, "Evidencia verificable %s" % resumen["codigo"])
        y -= 6 * mm
        lienzo.setFont("Helvetica", 9)

        encabezado = [
            "Titulo: %s" % (resumen.get("titulo") or ""),
            "Tipo: %s    Estado: %s    Fecha: %s" % (resumen.get("tipo"), resumen.get("estado"),
                                                     _texto_legible(resumen.get("generada_en"))),
            "Huella SHA-256: %s" % (resumen.get("huella") or "sin huella"),
            "-" * 96,
        ]
        for linea in encabezado:
            lienzo.drawString(x, y, linea[:118])
            y -= 5 * mm

        lienzo.setFont("Courier", 7.5)
        for seccion in resumen["secciones"]:
            for linea in _tabla_texto(seccion["columnas"], seccion["filas"]):
                if y < 18 * mm:
                    lienzo.showPage()
                    lienzo.setFont("Courier", 7.5)
                    y = alto - 20 * mm
                lienzo.drawString(x, y, linea[:150])
                y -= 3.6 * mm
            y -= 4 * mm

        if resumen["vacio"]:
            lienzo.setFont("Helvetica-Oblique", 9)
            lienzo.drawString(x, y, AVISO_SIN_DATOS[:110])

        lienzo.showPage()
        lienzo.save()
        return ruta
    except Exception as error:  # pragma: no cover - defensivo ante fallos de reportlab
        print("No fue posible generar el PDF de la evidencia: %s" % error)
        return None


class EvidenceService:
    """Fachada con la misma API, para el estilo de servicios del proyecto."""

    generar_codigo = staticmethod(generar_codigo)
    paralelo_de_estudiante = staticmethod(paralelo_de_estudiante)
    resolver_libros = staticmethod(resolver_libros)
    conexion_libros = staticmethod(conexion_libros)
    crear_evidencia = staticmethod(crear_evidencia)
    obtener_evidencia = staticmethod(obtener_evidencia)
    obtener_evidencia_de_estudiante = staticmethod(obtener_evidencia_de_estudiante)
    finalizar_evidencia = staticmethod(finalizar_evidencia)
    detectar_modificacion = staticmethod(detectar_modificacion)
    nueva_version = staticmethod(nueva_version)
    versiones = staticmethod(versiones)
    verificar_codigo = staticmethod(verificar_codigo)
    resumen_evidencia = staticmethod(resumen_evidencia)
    resumen_texto_plano = staticmethod(resumen_texto_plano)
    resumen_desde_contenido = staticmethod(resumen_desde_contenido)
    construir_contenido_contable = staticmethod(construir_contenido_contable)
    recolectar_datos_contables = staticmethod(recolectar_datos_contables)
    listar_evidencias_estudiante = staticmethod(listar_evidencias_estudiante)
    listar_evidencias_docente = staticmethod(listar_evidencias_docente)
    exportar_pdf = staticmethod(exportar_pdf)
    nombre_archivo_evidencia = staticmethod(nombre_archivo_evidencia)
    ErrorEvidencia = ErrorEvidencia
    EvidenciaNoEncontrada = EvidenciaNoEncontrada
    EvidenciaAjena = EvidenciaAjena
    AulaNoLegible = AulaNoLegible
