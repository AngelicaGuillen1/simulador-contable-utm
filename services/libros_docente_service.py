# -*- coding: utf-8 -*-
"""Lectura de SOLO LECTURA de los libros contables del aula de un estudiante.

El panel docente no puede trabajar contra la base de control para ver los libros de un
estudiante: sus cuentas, asientos, mayor, balance y estados viven en SU aula
(``database/aulas/<PARALELO>/<usuario>.db``, ver docs/DISENO_MULTIESTUDIANTE.md).

Este servicio resuelve el aula de un estudiante (a partir de su ``username`` y ``paralelo``
en la base de control), la abre en **modo lectura** (``file:...?mode=ro``: SQLite rechaza
cualquier escritura) y arma las vistas de consulta:

    * ``resumen_aula``            -> cuántas cuentas y asientos tiene, si el balance cuadra.
    * ``libro_diario``            -> asientos con fecha, concepto, cuentas, Debe y Haber.
    * ``libro_mayor``             -> cuentas con sus movimientos y saldo.
    * ``balance_comprobacion``    -> sumas y saldos, con la comprobación de que cuadra.
    * ``plan_cuentas``            -> plan de cuentas del estudiante.
    * ``estados_financieros``     -> situación financiera, resultados y flujo de efectivo.

Honestidad de los datos: si el estudiante no tiene aula creada, TODAS las funciones
devuelven ``existe = False`` con un aviso legible (nunca cifras inventadas ni un error 500).
"""
import os
import sqlite3

from models import get_db_connection, ruta_aula

# Estados de asiento que el sistema muestra como movimiento válido (los mismos que usan
# el Libro Diario, el Mayor y el Balance de Comprobación del simulador).
ESTADOS_VALIDOS = ("CONTABILIZADO", "REVERTIDO")

AVISO_SIN_AULA = ("El estudiante aún no tiene aula contable creada: todavía no ha trabajado "
                  "en el simulador, por lo que no hay libros que mostrar. No se inventan cifras.")

AVISO_AULA_VACIA = ("El aula del estudiante está creada pero no contiene movimientos: aún no "
                    "ha registrado asientos, por lo que los libros aparecen en cero.")

# Cuentas de efectivo (Caja y Bancos) para el flujo de efectivo simplificado.
PREFIJOS_EFECTIVO = ("1.1.01", "1.1.02", "1.1.03")


# --------------------------------------------------------------------------- Conexión
def _uri_lectura(ruta):
    """URI de SQLite en modo lectura (nunca se puede escribir en el aula del estudiante)."""
    ruta = os.path.abspath(ruta)
    seguro = ruta.replace("\\", "/").replace("?", "%3f").replace("#", "%23")
    if not seguro.startswith("/"):            # Windows: C:/...
        seguro = "/" + seguro
    return "file:%s?mode=ro" % seguro


class ErrorLibros(Exception):
    """No fue posible leer el aula del estudiante (archivo dañado, borrado a mitad...)."""


def abrir_aula_lectura(ruta):
    """Abre el aula en modo lectura. Lanza ErrorLibros si no se puede abrir de ninguna forma."""
    if not ruta or not os.path.exists(ruta):
        raise ErrorLibros("No existe el archivo del aula solicitada.")

    intentos = (_uri_lectura(ruta), _uri_lectura(ruta) + "&immutable=1")
    ultimo = None
    for uri in intentos:
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=15.0)
            conn.row_factory = sqlite3.Row
            conn.execute("SELECT 1 FROM cuentas LIMIT 1")
            return conn
        except sqlite3.Error as error:        # pragma: no cover - defensivo
            ultimo = error
    raise ErrorLibros("No fue posible abrir el aula en modo lectura: %s" % ultimo)


# --------------------------------------------------------------------------- Contexto
def datos_estudiante(estudiante_id, db_path=None):
    """Datos del estudiante tomados de la base de CONTROL (usuarios)."""
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("""
            SELECT u.id, u.username, u.nombre_completo, u.email, u.paralelo, u.matricula,
                   r.nombre AS rol_nombre
              FROM usuarios u
              LEFT JOIN roles r ON u.rol_id = r.id
             WHERE u.id = ?
        """, (estudiante_id,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def ruta_aula_estudiante(estudiante_id, db_path=None):
    """Ruta del aula del estudiante (o None si aún no tiene)."""
    datos = datos_estudiante(estudiante_id, db_path=db_path)
    if not datos or not datos.get("username"):
        return None
    # Con el paralelo declarado y, si no existe, sin paralelo (aulas antiguas).
    for paralelo in (datos.get("paralelo"), None):
        ruta = ruta_aula(datos["username"], paralelo)
        if ruta and os.path.exists(ruta):
            return ruta
    return None


def _contexto(estudiante_id, db_path=None):
    """(datos del estudiante, ruta del aula o None, conexión en lectura o None)."""
    datos = datos_estudiante(estudiante_id, db_path=db_path)
    if not datos:
        return None, None, None, "No existe el estudiante solicitado."
    ruta = ruta_aula_estudiante(estudiante_id, db_path=db_path)
    if not ruta:
        return datos, None, None, AVISO_SIN_AULA
    try:
        return datos, ruta, abrir_aula_lectura(ruta), None
    except ErrorLibros as error:              # pragma: no cover - defensivo
        return datos, ruta, None, "No fue posible abrir el aula del estudiante: %s" % error


def _base(estudiante_id, datos, ruta, aviso):
    """Estructura común de las vistas cuando no hay libros que mostrar."""
    return {
        "estudiante_id": estudiante_id,
        "estudiante": datos,
        "aula": ruta,
        "nombre_archivo": os.path.basename(ruta) if ruta else None,
        "existe": False,
        "aviso": aviso,
    }


# --------------------------------------------------------------------------- Consultas
def _cuentas(conn, solo_movimiento=False):
    sql = "SELECT * FROM cuentas"
    if solo_movimiento:
        sql += " WHERE acepta_movimiento = 1"
    return [dict(f) for f in conn.execute(sql + " ORDER BY codigo ASC").fetchall()]


def _asientos(conn):
    """Asientos con sus líneas (fecha, concepto, cuentas, Debe y Haber)."""
    filas = conn.execute("""
        SELECT id, numero_asiento, fecha, glosa, tipo_documento, numero_documento,
               origen_modulo, estado, observacion
          FROM asientos
         WHERE UPPER(IFNULL(estado, '')) IN ('CONTABILIZADO', 'REVERTIDO')
         ORDER BY fecha ASC, numero_asiento ASC, id ASC
    """).fetchall()
    asientos = []
    for fila in filas:
        lineas = [dict(l) for l in conn.execute("""
            SELECT d.id, d.cuenta_id, c.codigo, c.nombre, c.naturaleza, c.clasificacion,
                   d.debe, d.haber, d.referencia
              FROM detalle_asientos d
              JOIN cuentas c ON c.id = d.cuenta_id
             WHERE d.asiento_id = ?
             ORDER BY d.id ASC
        """, (fila["id"],)).fetchall()]
        registro = dict(fila)
        debe = round(sum(l["debe"] or 0 for l in lineas), 2)
        haber = round(sum(l["haber"] or 0 for l in lineas), 2)
        registro.update({"lineas": lineas, "total_debe": debe, "total_haber": haber,
                         "cuadrado": abs(debe - haber) < 0.01})
        asientos.append(registro)
    return asientos


def _lineas_movimiento(conn):
    """Todas las líneas de movimiento, ordenadas por cuenta y fecha (para el Mayor)."""
    return [dict(f) for f in conn.execute("""
        SELECT d.id, d.cuenta_id, c.codigo, c.nombre, c.naturaleza, c.clasificacion,
               d.debe, d.haber, d.referencia,
               a.id AS asiento_id, a.numero_asiento, a.fecha, a.glosa, a.tipo_documento,
               a.numero_documento
          FROM detalle_asientos d
          JOIN asientos a ON a.id = d.asiento_id
          JOIN cuentas c ON c.id = d.cuenta_id
         WHERE UPPER(IFNULL(a.estado, '')) IN ('CONTABILIZADO', 'REVERTIDO')
         ORDER BY c.codigo ASC, a.fecha ASC, a.numero_asiento ASC, d.id ASC
    """).fetchall()]


def _acumulados(cuentas, lineas):
    """Sumas por cuenta: débitos, créditos y saldo según la naturaleza."""
    indice = {c["codigo"]: c for c in cuentas}
    acumulado = {}
    for linea in lineas:
        datos = acumulado.setdefault(linea["codigo"], {
            "codigo": linea["codigo"],
            "nombre": linea["nombre"],
            "naturaleza": linea.get("naturaleza") or "",
            "clasificacion": linea.get("clasificacion") or "",
            "debitos": 0.0, "creditos": 0.0, "movimientos": [],
        })
        datos["debitos"] = round(datos["debitos"] + (linea["debe"] or 0), 2)
        datos["creditos"] = round(datos["creditos"] + (linea["haber"] or 0), 2)
        datos["movimientos"].append(linea)

    for codigo, datos in acumulado.items():
        cuenta = indice.get(codigo) or {}
        datos["naturaleza"] = datos["naturaleza"] or cuenta.get("naturaleza") or "DEUDORA"
        datos["clasificacion"] = datos["clasificacion"] or cuenta.get("clasificacion") or ""
    return acumulado


def _saldo(datos):
    """(saldo_deudor, saldo_acreedor, diferencia) de una cuenta acumulada.

    La diferencia se calcula en la dirección natural de la cuenta (Deudora: Debe-Haber;
    Acreedora: Haber-Debe), así que un saldo positivo queda siempre en su lado natural.
    """
    if datos["naturaleza"] == "ACREEDORA":
        diferencia = round(datos["creditos"] - datos["debitos"], 2)
    else:
        diferencia = round(datos["debitos"] - datos["creditos"], 2)

    if diferencia >= 0:
        deudor, acreedor = (0.0, diferencia) if datos["naturaleza"] == "ACREEDORA" \
            else (diferencia, 0.0)
    else:
        deudor, acreedor = (-diferencia, 0.0) if datos["naturaleza"] == "ACREEDORA" \
            else (0.0, -diferencia)
    return round(deudor, 2), round(acreedor, 2), diferencia


# --------------------------------------------------------------------------- Vistas
def resumen_aula(estudiante_id, db_path=None):
    """Resumen del aula: cuentas creadas, asientos, si el balance cuadra y totales."""
    datos, ruta, conn, aviso = _contexto(estudiante_id, db_path=db_path)
    if conn is None:
        base = _base(estudiante_id, datos, ruta, aviso)
        base.update({"num_cuentas": 0, "num_cuentas_movimiento": 0, "num_asientos": 0,
                     "num_lineas": 0, "total_debe": 0.0, "total_haber": 0.0,
                     "diferencia": 0.0, "cuadrado": False, "hay_movimientos": False,
                     "empresa": None, "periodo": None,
                     "primera_fecha": None, "ultima_fecha": None})
        return base
    try:
        cuentas = _cuentas(conn)
        lineas = _lineas_movimiento(conn)
        total_debe = round(sum(l["debe"] or 0 for l in lineas), 2)
        total_haber = round(sum(l["haber"] or 0 for l in lineas), 2)
        empresa = conn.execute("SELECT razon_social FROM empresas ORDER BY id ASC LIMIT 1").fetchone()
        periodo = conn.execute(
            "SELECT nombre, fecha_inicio, fecha_fin, estado FROM periodos ORDER BY id ASC LIMIT 1"
        ).fetchone()
        fechas = conn.execute(
            "SELECT MIN(fecha) AS primera, MAX(fecha) AS ultima FROM asientos "
            "WHERE UPPER(IFNULL(estado, '')) IN ('CONTABILIZADO', 'REVERTIDO')").fetchone()

        resultado = _base(estudiante_id, datos, ruta, None)
        resultado.update({
            "existe": True,
            "num_cuentas": len(cuentas),
            "num_cuentas_movimiento": len([c for c in cuentas if c.get("acepta_movimiento")]),
            "num_asientos": len({l["asiento_id"] for l in lineas}),
            "num_lineas": len(lineas),
            "total_debe": total_debe,
            "total_haber": total_haber,
            "diferencia": round(abs(total_debe - total_haber), 2),
            # Sin movimientos no hay nada que cuadrar: no se declara «cuadrado» en falso.
            "hay_movimientos": bool(lineas),
            "cuadrado": bool(lineas) and abs(total_debe - total_haber) < 0.02,
            "empresa": dict(empresa)["razon_social"] if empresa else None,
            "periodo": dict(periodo) if periodo else None,
            "primera_fecha": dict(fechas)["primera"] if fechas else None,
            "ultima_fecha": dict(fechas)["ultima"] if fechas else None,
        })
        if not lineas:
            resultado["aviso"] = AVISO_AULA_VACIA
        return resultado
    finally:
        conn.close()


def libro_diario(estudiante_id, db_path=None, desde=None, hasta=None):
    """Libro Diario del estudiante: asientos con fecha, concepto, cuentas, Debe y Haber."""
    datos, ruta, conn, aviso = _contexto(estudiante_id, db_path=db_path)
    if conn is None:
        base = _base(estudiante_id, datos, ruta, aviso)
        base.update({"asientos": [], "total_debe": 0.0, "total_haber": 0.0})
        return base
    try:
        asientos = _asientos(conn)
        if desde:
            asientos = [a for a in asientos if str(a.get("fecha") or "") >= str(desde)]
        if hasta:
            asientos = [a for a in asientos if str(a.get("fecha") or "") <= str(hasta)]
        resultado = _base(estudiante_id, datos, ruta, None)
        resultado.update({
            "existe": True,
            "asientos": asientos,
            "total_debe": round(sum(a["total_debe"] for a in asientos), 2),
            "total_haber": round(sum(a["total_haber"] for a in asientos), 2),
            "desde": desde, "hasta": hasta,
        })
        if not asientos:
            resultado["aviso"] = AVISO_AULA_VACIA
        return resultado
    finally:
        conn.close()


def libro_mayor(estudiante_id, db_path=None):
    """Libro Mayor: cuentas con sus movimientos y el saldo acumulado."""
    datos, ruta, conn, aviso = _contexto(estudiante_id, db_path=db_path)
    if conn is None:
        base = _base(estudiante_id, datos, ruta, aviso)
        base.update({"cuentas": [], "total_debe": 0.0, "total_haber": 0.0})
        return base
    try:
        cuentas = _cuentas(conn)
        acumulado = _acumulados(cuentas, _lineas_movimiento(conn))

        mayor = []
        for codigo in sorted(acumulado):
            item = acumulado[codigo]
            saldo = 0.0
            movimientos = []
            for movimiento in item["movimientos"]:
                debe = round(movimiento["debe"] or 0, 2)
                haber = round(movimiento["haber"] or 0, 2)
                saldo = round(saldo + (haber - debe if item["naturaleza"] == "ACREEDORA"
                                       else debe - haber), 2)
                movimientos.append({
                    "fecha": movimiento["fecha"],
                    "numero_asiento": movimiento["numero_asiento"],
                    "glosa": movimiento["glosa"],
                    "tipo_documento": movimiento["tipo_documento"],
                    "numero_documento": movimiento["numero_documento"],
                    "referencia": movimiento.get("referencia"),
                    "debe": debe, "haber": haber, "saldo": saldo,
                })
            deudor, acreedor, _ = _saldo(item)
            mayor.append({
                "codigo": item["codigo"], "nombre": item["nombre"],
                "naturaleza": item["naturaleza"], "clasificacion": item["clasificacion"],
                "movimientos": movimientos,
                "num_movimientos": len(movimientos),
                "total_debe": item["debitos"], "total_haber": item["creditos"],
                "saldo_final": saldo, "saldo_deudor": deudor, "saldo_acreedor": acreedor,
            })

        resultado = _base(estudiante_id, datos, ruta, None)
        resultado.update({
            "existe": True,
            "cuentas": mayor,
            "total_debe": round(sum(c["total_debe"] for c in mayor), 2),
            "total_haber": round(sum(c["total_haber"] for c in mayor), 2),
        })
        if not mayor:
            resultado["aviso"] = AVISO_AULA_VACIA
        return resultado
    finally:
        conn.close()


def balance_comprobacion(estudiante_id, db_path=None):
    """Balance de comprobación de sumas y saldos, con la comprobación de que cuadra."""
    datos, ruta, conn, aviso = _contexto(estudiante_id, db_path=db_path)
    if conn is None:
        base = _base(estudiante_id, datos, ruta, aviso)
        base.update({"cuentas": [], "total_debitos": 0.0, "total_creditos": 0.0,
                     "total_saldo_deudor": 0.0, "total_saldo_acreedor": 0.0,
                     "cuadrado_sumas": False, "cuadrado_saldos": False,
                     "diferencia_sumas": 0.0, "diferencia_saldos": 0.0,
                     "cuadrado": False, "hay_movimientos": False})
        return base
    try:
        cuentas = _cuentas(conn, solo_movimiento=True)
        acumulado = _acumulados(cuentas, _lineas_movimiento(conn))

        filas = []
        for codigo in sorted(acumulado):
            item = acumulado[codigo]
            deudor, acreedor, _ = _saldo(item)
            filas.append({
                "codigo": item["codigo"], "nombre": item["nombre"],
                "clasificacion": item["clasificacion"], "naturaleza": item["naturaleza"],
                "debitos": item["debitos"], "creditos": item["creditos"],
                "saldo_deudor": deudor, "saldo_acreedor": acreedor,
            })

        total_debitos = round(sum(f["debitos"] for f in filas), 2)
        total_creditos = round(sum(f["creditos"] for f in filas), 2)
        total_deudor = round(sum(f["saldo_deudor"] for f in filas), 2)
        total_acreedor = round(sum(f["saldo_acreedor"] for f in filas), 2)

        resultado = _base(estudiante_id, datos, ruta, None)
        resultado.update({
            "existe": True,
            "cuentas": filas,
            "total_debitos": total_debitos,
            "total_creditos": total_creditos,
            "total_saldo_deudor": total_deudor,
            "total_saldo_acreedor": total_acreedor,
            "diferencia_sumas": round(abs(total_debitos - total_creditos), 2),
            "diferencia_saldos": round(abs(total_deudor - total_acreedor), 2),
            "cuadrado_sumas": abs(total_debitos - total_creditos) < 0.02,
            "cuadrado_saldos": abs(total_deudor - total_acreedor) < 0.02,
            "hay_movimientos": bool(filas),
        })
        resultado["cuadrado"] = bool(filas) and resultado["cuadrado_sumas"] \
            and resultado["cuadrado_saldos"]
        if not filas:
            resultado["aviso"] = AVISO_AULA_VACIA
        return resultado
    finally:
        conn.close()


def plan_cuentas(estudiante_id, db_path=None):
    """Plan de cuentas del estudiante, agrupado por clasificación."""
    datos, ruta, conn, aviso = _contexto(estudiante_id, db_path=db_path)
    if conn is None:
        base = _base(estudiante_id, datos, ruta, aviso)
        base.update({"cuentas": [], "grupos": [], "num_cuentas": 0, "num_movimiento": 0})
        return base
    try:
        cuentas = _cuentas(conn)
        grupos, orden = {}, []
        for cuenta in cuentas:
            clave = cuenta.get("clasificacion") or "SIN CLASIFICACIÓN"
            if clave not in grupos:
                grupos[clave] = []
                orden.append(clave)
            grupos[clave].append(cuenta)

        resultado = _base(estudiante_id, datos, ruta, None)
        resultado.update({
            "existe": True,
            "cuentas": cuentas,
            "grupos": [{"clasificacion": g, "cuentas": grupos[g],
                        "num_cuentas": len(grupos[g])} for g in orden],
            "num_cuentas": len(cuentas),
            "num_movimiento": len([c for c in cuentas if c.get("acepta_movimiento")]),
        })
        if not cuentas:
            resultado["aviso"] = AVISO_AULA_VACIA
        return resultado
    finally:
        conn.close()


def estados_financieros(estudiante_id, db_path=None):
    """Estados financieros básicos del aula: situación financiera, resultados y efectivo."""
    datos, ruta, conn, aviso = _contexto(estudiante_id, db_path=db_path)
    if conn is None:
        base = _base(estudiante_id, datos, ruta, aviso)
        base.update({"situacion": None, "resultados": None, "efectivo": None})
        return base
    try:
        cuentas = _cuentas(conn, solo_movimiento=True)
        lineas = _lineas_movimiento(conn)
        acumulado = _acumulados(cuentas, lineas)

        por_clasificacion = {}
        for item in acumulado.values():
            por_clasificacion.setdefault(item["clasificacion"], []).append(item)

        def saldos(clasificacion, signo="acreedor"):
            """Cuentas de una clasificación con su valor neto en el lado pedido."""
            resultado = []
            for item in sorted(por_clasificacion.get(clasificacion, []),
                               key=lambda i: i["codigo"]):
                deudor, acreedor, _ = _saldo(item)
                valor = round(acreedor - deudor, 2) if signo == "acreedor" \
                    else round(deudor - acreedor, 2)
                resultado.append({"codigo": item["codigo"], "nombre": item["nombre"],
                                  "valor": valor})
            return resultado

        ingresos_op = saldos("INGRESOS_OPERACIONALES")
        otros_ingresos = saldos("INGRESOS_NO_OPERACIONALES")
        costos = saldos("COSTOS", signo="deudor")
        gastos_admin = saldos("GASTOS_ADMIN", signo="deudor")
        gastos_ventas = saldos("GASTOS_VENTAS", signo="deudor")
        gastos_fin = saldos("GASTOS_FINANCIEROS", signo="deudor")

        total_ingresos = round(sum(i["valor"] for i in ingresos_op), 2)
        total_otros = round(sum(i["valor"] for i in otros_ingresos), 2)
        total_costos = round(sum(i["valor"] for i in costos), 2)
        total_gastos_admin = round(sum(i["valor"] for i in gastos_admin), 2)
        total_gastos_ventas = round(sum(i["valor"] for i in gastos_ventas), 2)
        total_gastos_fin = round(sum(i["valor"] for i in gastos_fin), 2)

        utilidad_bruta = round(total_ingresos - total_costos, 2)
        utilidad_operacional = round(utilidad_bruta - total_gastos_admin - total_gastos_ventas, 2)
        utilidad_neta = round(utilidad_operacional + total_otros - total_gastos_fin, 2)

        resultados = {
            "ingresos_operacionales": ingresos_op,
            "total_ingresos_operacionales": total_ingresos,
            "costos": costos,
            "total_costos": total_costos,
            "utilidad_bruta": utilidad_bruta,
            "gastos_administrativos": gastos_admin,
            "total_gastos_administrativos": total_gastos_admin,
            "gastos_ventas": gastos_ventas,
            "total_gastos_ventas": total_gastos_ventas,
            "utilidad_operacional": utilidad_operacional,
            "otros_ingresos": otros_ingresos,
            "total_otros_ingresos": total_otros,
            "gastos_financieros": gastos_fin,
            "total_gastos_financieros": total_gastos_fin,
            "utilidad_neta": utilidad_neta,
        }

        activos_corrientes = saldos("ACTIVO_CORRIENTE", signo="deudor")
        activos_no_corrientes = saldos("ACTIVO_NO_CORRIENTE", signo="deudor")
        pasivos_corrientes = saldos("PASIVO_CORRIENTE")
        pasivos_no_corrientes = saldos("PASIVO_NO_CORRIENTE")
        patrimonio = saldos("PATRIMONIO")
        # El resultado del ejercicio se incorpora al patrimonio mientras el período siga abierto.
        patrimonio.append({"codigo": "3.3.02", "nombre": "Resultado del Ejercicio (calculado)",
                           "valor": utilidad_neta})

        total_activo_corr = round(sum(i["valor"] for i in activos_corrientes), 2)
        total_activo_nocorr = round(sum(i["valor"] for i in activos_no_corrientes), 2)
        total_activo = round(total_activo_corr + total_activo_nocorr, 2)
        total_pasivo_corr = round(sum(i["valor"] for i in pasivos_corrientes), 2)
        total_pasivo_nocorr = round(sum(i["valor"] for i in pasivos_no_corrientes), 2)
        total_pasivo = round(total_pasivo_corr + total_pasivo_nocorr, 2)
        total_patrimonio = round(sum(i["valor"] for i in patrimonio), 2)
        total_pasivo_patrimonio = round(total_pasivo + total_patrimonio, 2)

        situacion = {
            "activos_corrientes": activos_corrientes,
            "total_activo_corriente": total_activo_corr,
            "activos_no_corrientes": activos_no_corrientes,
            "total_activo_no_corriente": total_activo_nocorr,
            "total_activo": total_activo,
            "pasivos_corrientes": pasivos_corrientes,
            "total_pasivo_corriente": total_pasivo_corr,
            "pasivos_no_corrientes": pasivos_no_corrientes,
            "total_pasivo_no_corriente": total_pasivo_nocorr,
            "total_pasivo": total_pasivo,
            "patrimonio": patrimonio,
            "total_patrimonio": total_patrimonio,
            "total_pasivo_y_patrimonio": total_pasivo_patrimonio,
            "diferencia": round(abs(total_activo - total_pasivo_patrimonio), 2),
            "cuadra": abs(total_activo - total_pasivo_patrimonio) < 0.05,
        }

        # Flujo de efectivo simplificado: movimientos de Caja y Bancos por origen del módulo.
        operacion, inversion, financiamiento = [], [], []
        for linea in lineas:
            codigo = str(linea["codigo"] or "")
            if not codigo.startswith(PREFIJOS_EFECTIVO):
                continue
            item = {
                "fecha": linea["fecha"],
                "numero_asiento": linea["numero_asiento"],
                "concepto": linea["glosa"],
                "monto": round((linea["debe"] or 0) - (linea["haber"] or 0), 2),
            }
            origen = (linea.get("tipo_documento") or "").upper()
            if origen in ("CIERRE", "CIERRE_INGRESOS", "CIERRE_GASTOS"):
                continue
            if (linea.get("origen_modulo") or "").upper() == "INVERSION":
                inversion.append(item)
            elif (linea.get("origen_modulo") or "").upper() == "FINANCIAMIENTO":
                financiamiento.append(item)
            else:
                operacion.append(item)

        efectivo = {
            "operacion": operacion, "total_operacion": round(sum(i["monto"] for i in operacion), 2),
            "inversion": inversion, "total_inversion": round(sum(i["monto"] for i in inversion), 2),
            "financiamiento": financiamiento,
            "total_financiamiento": round(sum(i["monto"] for i in financiamiento), 2),
            "variacion_neta": round(sum(i["monto"] for i in operacion + inversion + financiamiento), 2),
        }

        resultado = _base(estudiante_id, datos, ruta, None)
        resultado.update({"existe": True, "situacion": situacion, "resultados": resultados,
                          "efectivo": efectivo})
        fila_empresa = conn.execute(
            "SELECT razon_social FROM empresas ORDER BY id ASC LIMIT 1").fetchone()
        resultado["empresa"] = fila_empresa["razon_social"] if fila_empresa else None
        if not lineas:
            resultado["aviso"] = AVISO_AULA_VACIA
        return resultado
    finally:
        conn.close()


class LibrosDocenteService:
    """Fachada con la misma API, al estilo de los demás servicios del proyecto."""

    AVISO_SIN_AULA = AVISO_SIN_AULA
    AVISO_AULA_VACIA = AVISO_AULA_VACIA
    ErrorLibros = ErrorLibros

    datos_estudiante = staticmethod(datos_estudiante)
    ruta_aula_estudiante = staticmethod(ruta_aula_estudiante)
    abrir_aula_lectura = staticmethod(abrir_aula_lectura)
    resumen_aula = staticmethod(resumen_aula)
    libro_diario = staticmethod(libro_diario)
    libro_mayor = staticmethod(libro_mayor)
    balance_comprobacion = staticmethod(balance_comprobacion)
    plan_cuentas = staticmethod(plan_cuentas)
    estados_financieros = staticmethod(estados_financieros)
