# -*- coding: utf-8 -*-
"""Servicio de seguimiento de ACCESOS del estudiante (Contabilidad I - UTM).

Registra dos cosas, siempre con fines pedagógicos (nunca vigilancia invasiva):

* ``sesiones_usuario``  -> cada inicio/cierre de sesión con su duración real.
* ``eventos_estudiante`` -> acciones relevantes hechas dentro del simulador.

Sobre estas dos tablas se construye el Panel Docente de Accesos: quién entró,
cuándo, por cuánto tiempo, qué actividad abrió y qué evidencia generó.

Todas las funciones aceptan ``db_path`` opcional para poder probarlas sobre una
base de prueba; si se omite se usa ``Config.DATABASE_PATH`` (vía models.get_db_connection).
"""
import csv
import io
import sqlite3
from datetime import datetime

from models import get_db_connection

# ---------------------------------------------------------------------------
# Catálogo de eventos permitidos (etiquetas exactas acordadas con el Prompt Maestro)
# ---------------------------------------------------------------------------
EVENTO_LOGIN = "LOGIN"
EVENTO_LOGOUT = "LOGOUT"
EVENTO_INICIO_ACTIVIDAD = "INICIO_ACTIVIDAD"
EVENTO_CREAR_CUENTA = "CREAR_CUENTA"
EVENTO_MODIFICAR_CUENTA = "MODIFICAR_CUENTA"
EVENTO_CREAR_ASIENTO = "CREAR_ASIENTO"
EVENTO_INTENTO_FALLIDO_ASIENTO = "INTENTO_FALLIDO_ASIENTO"
EVENTO_INTENTO_FALLIDO_DOCUMENTO = "INTENTO_FALLIDO_DOCUMENTO"
EVENTO_CONSULTA_DIARIO = "CONSULTA_DIARIO"
EVENTO_CONSULTA_MAYOR = "CONSULTA_MAYOR"
EVENTO_GENERACION_BALANCE = "GENERACION_BALANCE"
EVENTO_CORRECCION_ASIENTO = "CORRECCION_ASIENTO"
EVENTO_GENERACION_ESTADO_FINANCIERO = "GENERACION_ESTADO_FINANCIERO"
EVENTO_CREACION_EVIDENCIA = "CREACION_EVIDENCIA"
EVENTO_CONSULTA_ACTIVIDAD = "CONSULTA_ACTIVIDAD"

EVENTOS_PERMITIDOS = (
    EVENTO_LOGIN,
    EVENTO_LOGOUT,
    EVENTO_INICIO_ACTIVIDAD,
    EVENTO_CREAR_CUENTA,
    EVENTO_MODIFICAR_CUENTA,
    EVENTO_CREAR_ASIENTO,
    EVENTO_INTENTO_FALLIDO_ASIENTO,
    EVENTO_INTENTO_FALLIDO_DOCUMENTO,
    EVENTO_CONSULTA_DIARIO,
    EVENTO_CONSULTA_MAYOR,
    EVENTO_GENERACION_BALANCE,
    EVENTO_CORRECCION_ASIENTO,
    EVENTO_GENERACION_ESTADO_FINANCIERO,
    EVENTO_CREACION_EVIDENCIA,
    EVENTO_CONSULTA_ACTIVIDAD,
)

# ---------------------------------------------------------------------------
# Mapa endpoint -> (evento por método HTTP, módulo).  Solo se registran los
# endpoints que aportan trazabilidad pedagógica; el resto se ignora.
# ---------------------------------------------------------------------------
MAPA_ENDPOINTS = {
    "accounting.accounts": (
        {"GET": EVENTO_CONSULTA_ACTIVIDAD, "POST": EVENTO_CREAR_CUENTA}, "CUENTAS"),
    "accounting.edit_account": (
        {"POST": EVENTO_MODIFICAR_CUENTA}, "CUENTAS"),
    "accounting.journal": (
        {"GET": EVENTO_CONSULTA_DIARIO, "POST": EVENTO_CREAR_ASIENTO}, "DIARIO"),
    "accounting.reverse_journal": (
        {"POST": EVENTO_CORRECCION_ASIENTO}, "DIARIO"),
    "accounting.ledger": (
        {"GET": EVENTO_CONSULTA_MAYOR}, "MAYOR"),
    "accounting.trial_balance": (
        {"GET": EVENTO_GENERACION_BALANCE}, "BALANCE"),
    "accounting.adjustments": (
        {"GET": EVENTO_CONSULTA_ACTIVIDAD, "POST": EVENTO_CORRECCION_ASIENTO}, "AJUSTES"),
    "accounting.closing": (
        {"GET": EVENTO_CONSULTA_ACTIVIDAD, "POST": EVENTO_GENERACION_ESTADO_FINANCIERO}, "CIERRE"),
    "financial_statements.balance_sheet": (
        {"GET": EVENTO_GENERACION_ESTADO_FINANCIERO}, "ESTADOS"),
    "financial_statements.income_statement": (
        {"GET": EVENTO_GENERACION_ESTADO_FINANCIERO}, "ESTADOS"),
    "financial_statements.cash_flow": (
        {"GET": EVENTO_GENERACION_ESTADO_FINANCIERO}, "ESTADOS"),
    "reports.index": (
        {"GET": EVENTO_GENERACION_ESTADO_FINANCIERO}, "REPORTES"),
    "documents.index": (
        {"GET": EVENTO_CONSULTA_ACTIVIDAD}, "DOCUMENTOS"),
    "documents.detail": (
        {"GET": EVENTO_CREACION_EVIDENCIA}, "DOCUMENTOS"),
    "simulations.start_simulation": (
        {"GET": EVENTO_INICIO_ACTIVIDAD}, "SIMULADOR"),
    "simulations.play_simulation": (
        {"GET": EVENTO_INICIO_ACTIVIDAD}, "SIMULADOR"),
    "simulations.submit_attempt": (
        {"POST": EVENTO_CREACION_EVIDENCIA}, "SIMULADOR"),
}

# Prefijos de blueprint del módulo de actividades/evidencias del syllabus.
# Se resuelven por regla, no por nombre exacto de endpoint.
PREFIJOS_ACTIVIDADES = ("actividades.", "activities.")
PREFIJOS_EVIDENCIAS = ("evidencias.", "evidence.")

# Roles cuyos recorridos anota el hook global after_request. La tabla
# eventos_estudiante es de seguimiento PEDAGÓGICO, por eso por defecto solo se
# trazan los estudiantes (LOGIN/LOGOUT sí se registran para todos los roles
# desde routes/auth.py). El orquestador puede ampliarlo si lo necesita.
ROLES_SEGUIDOS = ("Estudiante",)


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------
def _conexion(db_path=None):
    return get_db_connection(db_path)


def _ahora():
    """Marca de tiempo en el mismo reloj que los DEFAULT de SQLite (UTC).

    Toda la base usa ``CURRENT_TIMESTAMP`` (UTC) en sus columnas de fecha, así que
    las escrituras de este servicio usan el mismo reloj para que las duraciones y
    los rangos de fechas sean coherentes.
    """
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _texto(valor):
    """Normaliza el valor de un filtro que llega de request.args."""
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor in ("", "None", "none", "null", "undefined"):
        return None
    return valor


def _a_entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _limite_fecha(valor, fin=False):
    """Convierte '2026-04-30' en '2026-04-30 23:59:59' (o 00:00:00 si es inicio)."""
    valor = _texto(valor)
    if not valor:
        return None
    if len(valor) <= 10:
        return valor + (" 23:59:59" if fin else " 00:00:00")
    return valor


def formatear_duracion(segundos):
    """Convierte 5400 en '1 h 30 min' (tiempo aproximado de actividad)."""
    try:
        total = int(segundos or 0)
    except (TypeError, ValueError):
        total = 0
    if total <= 0:
        return "0 min"
    horas, resto = divmod(total, 3600)
    minutos = resto // 60
    if horas and minutos:
        return "%d h %d min" % (horas, minutos)
    if horas:
        return "%d h" % horas
    if minutos:
        return "%d min" % minutos
    return "%d s" % total


def _partir_timestamp(valor):
    """Devuelve (fecha, hora, fecha_hora_legible) de un TIMESTAMP de SQLite."""
    if not valor:
        return (None, None, None)
    texto = str(valor)
    fecha, _, hora = texto.partition(" ")
    return (fecha, hora[:8], texto)


def _mapear_evento(endpoint, metodo):
    """Traduce el endpoint visitado a (evento, modulos) o (None, None)."""
    if not endpoint or endpoint == "static":
        return (None, None)

    regla = MAPA_ENDPOINTS.get(endpoint)
    if regla:
        evento = regla[0].get(metodo)
        if evento:
            return (evento, regla[1])
        # El endpoint es relevante pero no en este método (p. ej. GET /cuentas)
        return (None, None)

    if endpoint.startswith(PREFIJOS_ACTIVIDADES):
        # El servicio de actividades (services/activity_service.py) ya registra
        # INICIO_ACTIVIDAD y ENTREGA_ACTIVIDAD con el detalle de la asignación,
        # así que aquí solo se anotan las consultas para no duplicar la traza.
        if metodo == "GET":
            return (EVENTO_CONSULTA_ACTIVIDAD, "ACTIVIDADES")
        return (None, None)

    if endpoint.startswith(PREFIJOS_EVIDENCIAS):
        if metodo == "POST":
            return (EVENTO_CREACION_EVIDENCIA, "EVIDENCIAS")
        if metodo == "GET":
            return (EVENTO_CONSULTA_ACTIVIDAD, "EVIDENCIAS")

    return (None, None)


def _filtros_normalizados(filtros):
    """Unifica los nombres de filtros aceptados (panel docente y JSON)."""
    f = dict(filtros or {})

    def _pick(*nombres):
        for nombre in nombres:
            valor = _texto(f.get(nombre))
            if valor is not None:
                return valor
        return None

    return {
        "estudiante_id": _a_entero(_pick("estudiante_id", "estudiante", "id_estudiante")),
        "desde": _limite_fecha(_pick("desde", "fecha_desde", "inicio")),
        "hasta": _limite_fecha(_pick("hasta", "fecha_hasta", "fin"), fin=True),
        "actividad_id": _a_entero(_pick("actividad_id", "actividad")),
        "estado": (_pick("estado") or "").upper(),
        "paralelo": _pick("paralelo"),
        "buscar": _pick("q", "buscar", "texto", "nombre"),
    }


# ---------------------------------------------------------------------------
# Sesiones
# ---------------------------------------------------------------------------
def abrir_sesion(usuario_id, ip=None, navegador=None, db_path=None):
    """Abre una sesión de trabajo y devuelve su id (o None si no se pudo)."""
    if not usuario_id:
        return None
    conn = _conexion(db_path)
    try:
        cursor = conn.execute("""
            INSERT INTO sesiones_usuario (usuario_id, inicio, ip_origen, navegador, activa)
            VALUES (?, ?, ?, ?, 1)
        """, (usuario_id, _ahora(), (ip or None), (navegador or None)[:255] if navegador else None))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print("Error al abrir sesión: %s" % e)
        return None
    finally:
        conn.close()


def cerrar_sesion(sesion_id, db_path=None):
    """Marca la sesión como finalizada y calcula su duración en segundos."""
    sesion_id = _a_entero(sesion_id)
    if not sesion_id:
        return None
    conn = _conexion(db_path)
    try:
        conn.execute("""
            UPDATE sesiones_usuario
               SET fin = CURRENT_TIMESTAMP,
                   activa = 0,
                   duracion_seg = MAX(0, CAST(ROUND(
                       (julianday(CURRENT_TIMESTAMP) - julianday(inicio)) * 86400) AS INTEGER))
             WHERE id = ?
        """, (sesion_id,))
        conn.commit()
        fila = conn.execute(
            "SELECT id, usuario_id, inicio, fin, duracion_seg, activa FROM sesiones_usuario WHERE id = ?",
            (sesion_id,)).fetchone()
        return dict(fila) if fila else None
    except sqlite3.Error as e:
        print("Error al cerrar sesión: %s" % e)
        return None
    finally:
        conn.close()


def cerrar_sesiones_huerfanas(usuario_id, excepto_sesion_id=None, db_path=None):
    """Cierra las sesiones activas previas del mismo usuario.

    Evita sesiones colgadas cuando el estudiante cierra el navegador sin usar
    /logout (o cuando vuelve a entrar en otro dispositivo). Devuelve cuántas cerró.
    """
    usuario_id = _a_entero(usuario_id)
    if not usuario_id:
        return 0
    try:
        conn = _conexion(db_path)
        try:
            sql = "SELECT id FROM sesiones_usuario WHERE usuario_id = ? AND COALESCE(activa, 0) = 1"
            params = [usuario_id]
            if excepto_sesion_id:
                sql += " AND id <> ?"
                params.append(excepto_sesion_id)
            ids = [fila["id"] for fila in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    except sqlite3.Error as e:
        print("Error al buscar sesiones huérfanas: %s" % e)
        return 0

    cerradas = 0
    for sesion_id in ids:
        if cerrar_sesion(sesion_id, db_path=db_path):
            cerradas += 1
    return cerradas


# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------
def registrar_evento(usuario_id, evento, modulo=None, registro_id=None, detalle=None,
                     actividad_id=None, empresa_id=None, sesion_id=None, db_path=None):
    """Inserta un evento del estudiante. Devuelve el id o None.

    Ignora silenciosamente las etiquetas fuera del catálogo permitido (así una
    llamada mal escrita nunca rompe el flujo del estudiante).
    """
    usuario_id = _a_entero(usuario_id)
    evento = (evento or "").strip().upper()
    if not usuario_id or evento not in EVENTOS_PERMITIDOS:
        return None
    conn = _conexion(db_path)
    try:
        cursor = conn.execute("""
            INSERT INTO eventos_estudiante
                (usuario_id, empresa_id, sesion_id, actividad_id, evento, modulo, registro_id, detalle, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (usuario_id, _a_entero(empresa_id), _a_entero(sesion_id), _a_entero(actividad_id),
              evento, modulo, None if registro_id is None else str(registro_id), detalle, _ahora()))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print("Error al registrar evento: %s" % e)
        return None
    finally:
        conn.close()


def registrar_evento_desde_request(response, db_path=None, roles=ROLES_SEGUIDOS):
    """Registra el evento correspondiente al endpoint visitado (hook after_request).

    Deduce usuario, empresa y sesión de flask.session. Si el endpoint no aporta
    trazabilidad pedagógica no registra nada y NUNCA lanza excepción: la respuesta
    original siempre se devuelve intacta.

    ``roles`` limita el seguimiento a los roles indicados (por defecto Estudiante);
    pase ``roles=None`` para trazar también a docentes y administradores.
    """
    try:
        from flask import request, session, g

        if session.get("user_id") is None or request.method == "OPTIONS":
            return response

        if roles is not None and session.get("user_role") not in roles:
            return response

        codigo = getattr(response, "status_code", 200)
        if codigo >= 500:
            return response

        endpoint = request.endpoint or ""
        evento, modulo = _mapear_evento(endpoint, request.method)
        # Una ruta puede marcar el intento rechazado en flask.g (cuando responde con
        # redirect + flash y el código HTTP no lo delata: es un 302, no un >= 400).
        marca = getattr(g, "intento_fallido", None)
        if marca:
            evento = marca.get("evento") or EVENTO_INTENTO_FALLIDO_ASIENTO
        elif not evento:
            return response
        elif evento == EVENTO_CREAR_ASIENTO and codigo >= 400:
            # Un asiento que el sistema rechazó cuenta como intento fallido.
            evento = EVENTO_INTENTO_FALLIDO_ASIENTO

        usuario_id = session.get("user_id")
        sesion_id = session.get("sesion_id")
        empresa_id = session.get("empresa_id")
        actividad_id = session.get("actividad_id")
        registro_id = request.view_args.get("asiento_id") if request.view_args else None

        # Las consultas (GET) se registran una sola vez por sesión para no inflar
        # la traza con cada clic del menú.
        if request.method == "GET" and sesion_id:
            conn = _conexion(db_path)
            try:
                repetido = conn.execute("""
                    SELECT 1 FROM eventos_estudiante
                     WHERE sesion_id = ? AND evento = ? AND COALESCE(modulo, '') = COALESCE(?, '')
                     LIMIT 1
                """, (sesion_id, evento, modulo)).fetchone()
            finally:
                conn.close()
            if repetido:
                return response

        detalle = request.path
        if marca and marca.get("mensaje"):
            detalle = "%s | RECHAZADO: %s" % (request.path, marca["mensaje"])
            if marca.get("documento_elegido"):
                detalle += " | documento elegido: %s" % marca["documento_elegido"]

        registrar_evento(usuario_id, evento, modulo=modulo, registro_id=registro_id,
                         detalle=detalle, actividad_id=actividad_id,
                         empresa_id=empresa_id, sesion_id=sesion_id, db_path=db_path)
    except Exception as e:  # nunca debe romper la respuesta
        print("Aviso: no se pudo registrar el evento de acceso: %s" % e)
    return response


# ---------------------------------------------------------------------------
# Consultas del panel docente
# ---------------------------------------------------------------------------
def _condiciones_sesion(f, alias="s"):
    sql, params = "", []
    if f.get("desde"):
        sql += " AND %s.inicio >= ?" % alias
        params.append(f["desde"])
    if f.get("hasta"):
        sql += " AND %s.inicio <= ?" % alias
        params.append(f["hasta"])
    return sql, params


def _condiciones_evento(f, alias="e", con_actividad=True, columna="timestamp"):
    sql, params = "", []
    if f.get("desde"):
        sql += " AND %s.%s >= ?" % (alias, columna)
        params.append(f["desde"])
    if f.get("hasta"):
        sql += " AND %s.%s <= ?" % (alias, columna)
        params.append(f["hasta"])
    if con_actividad and f.get("actividad_id"):
        sql += " AND %s.actividad_id = ?" % alias
        params.append(f["actividad_id"])
    return sql, params


def resumen_accesos(filtros=None, db_path=None):
    """Una fila por estudiante con todos los indicadores del panel docente.

    Filtros aceptados (todos opcionales): estudiante_id, desde, hasta,
    actividad_id, estado (ACTIVO | INACTIVO | CON_INGRESO | SIN_INGRESO),
    paralelo y buscar (texto sobre nombre/correo).
    """
    f = _filtros_normalizados(filtros)

    cond_ses, params_ses = _condiciones_sesion(f)
    cond_ev, params_ev = _condiciones_evento(f)

    sql = """
    SELECT t.* FROM (
        SELECT u.id AS estudiante_id,
               u.username,
               u.nombre_completo AS nombre,
               u.email AS correo,
               u.paralelo,
               u.matricula,
               COALESCE(u.activo, 0) AS activo,
               {sesiones}      AS num_sesiones,
               {primer}        AS primer_acceso,
               {ultimo}        AS ultimo_acceso,
               {tiempo}        AS tiempo_seg,
               (SELECT COUNT(*) FROM eventos_estudiante e
                 WHERE e.usuario_id = u.id {cond_ev}) AS num_eventos,
               (SELECT e.evento FROM eventos_estudiante e
                 WHERE e.usuario_id = u.id {cond_ev}
                 ORDER BY e.timestamp DESC, e.id DESC LIMIT 1) AS ultima_accion,
               (SELECT e.timestamp FROM eventos_estudiante e
                 WHERE e.usuario_id = u.id {cond_ev}
                 ORDER BY e.timestamp DESC, e.id DESC LIMIT 1) AS ultima_accion_fecha,
               (SELECT e.detalle FROM eventos_estudiante e
                 WHERE e.usuario_id = u.id {cond_ev}
                 ORDER BY e.timestamp DESC, e.id DESC LIMIT 1) AS ultima_accion_detalle,
               (SELECT COUNT(DISTINCT e.actividad_id) FROM eventos_estudiante e
                 WHERE e.usuario_id = u.id AND e.actividad_id IS NOT NULL
                   AND e.evento IN ('INICIO_ACTIVIDAD', 'CONSULTA_ACTIVIDAD') {cond_ev}) AS actividades_iniciadas,
               (SELECT COUNT(*) FROM asignaciones_actividad a
                 WHERE a.estudiante_id = u.id {cond_asig}) AS actividades_asignadas,
               (SELECT COUNT(*) FROM asignaciones_actividad a
                 WHERE a.estudiante_id = u.id AND a.estado IN ('ENTREGADA', 'REVISADA') {cond_asig}) AS actividades_completadas,
               (SELECT COUNT(*) FROM evidencias v
                 WHERE v.estudiante_id = u.id {cond_evd}) AS evidencias_generadas
          FROM usuarios u
          JOIN roles r ON u.rol_id = r.id
         WHERE r.nombre = 'Estudiante'
    ) t
    WHERE 1 = 1
    """
    cond_asig, params_asig = _condiciones_evento(f, alias="a", columna="asignada_en")
    cond_evd, params_evd = _condiciones_evento(f, alias="v", columna="generada_en")

    reemplazos = {
        "{cond_ev}": cond_ev,
        "{cond_asig}": cond_asig,
        "{cond_evd}": cond_evd,
        "{sesiones}": "(SELECT COUNT(*) FROM sesiones_usuario s WHERE s.usuario_id = u.id %s)" % cond_ses,
        "{primer}": "(SELECT MIN(s.inicio) FROM sesiones_usuario s WHERE s.usuario_id = u.id %s)" % cond_ses,
        "{ultimo}": "(SELECT MAX(s.inicio) FROM sesiones_usuario s WHERE s.usuario_id = u.id %s)" % cond_ses,
        "{tiempo}": "(SELECT COALESCE(SUM(s.duracion_seg), 0) FROM sesiones_usuario s WHERE s.usuario_id = u.id %s)" % cond_ses,
    }
    for clave, valor in reemplazos.items():
        sql = sql.replace(clave, valor)

    # El orden de los marcadores ? sigue el orden de aparición en el SQL.
    params = (params_ses * 4) + params_ev + params_ev + params_ev + params_ev + params_ev \
        + params_asig + params_asig + params_evd

    condiciones, params_extra = [], []
    if f.get("estudiante_id"):
        condiciones.append("t.estudiante_id = ?")
        params_extra.append(f["estudiante_id"])
    if f.get("paralelo"):
        condiciones.append("COALESCE(t.paralelo, '') = ?")
        params_extra.append(f["paralelo"])
    if f.get("buscar"):
        condiciones.append("(t.nombre LIKE ? OR t.correo LIKE ? OR t.username LIKE ?)")
        patron = "%%%s%%" % f["buscar"]
        params_extra.extend([patron, patron, patron])
    if f.get("estado"):
        estados = {
            "ACTIVO": "t.activo = 1",
            "INACTIVO": "t.activo = 0",
            "CON_INGRESO": "t.num_sesiones > 0",
            "HA_INGRESADO": "t.num_sesiones > 0",
            "SIN_INGRESO": "t.num_sesiones = 0",
        }
        if f["estado"] in estados:
            condiciones.append(estados[f["estado"]])
    if f.get("actividad_id"):
        condiciones.append("(t.actividades_iniciadas > 0 OR t.actividades_asignadas > 0 "
                           "OR t.evidencias_generadas > 0)")
    if f.get("desde") or f.get("hasta"):
        condiciones.append("(t.num_sesiones > 0 OR t.num_eventos > 0)")

    if condiciones:
        sql += " AND " + " AND ".join(condiciones)
    sql += " ORDER BY (t.ultimo_acceso IS NULL), t.ultimo_acceso DESC, t.nombre COLLATE NOCASE ASC"

    conn = _conexion(db_path)
    try:
        filas = conn.execute(sql, params + params_extra).fetchall()
    finally:
        conn.close()

    resultado = []
    for fila in filas:
        item = dict(fila)
        item["estado_cuenta"] = "Activo" if item.get("activo") else "Inactivo"
        item["ha_ingresado"] = (item.get("num_sesiones") or 0) > 0
        item["tiempo_actividad_segundos"] = item.get("tiempo_seg") or 0
        item["tiempo_actividad"] = formatear_duracion(item.get("tiempo_seg"))
        fecha, hora, _ = _partir_timestamp(item.get("ultimo_acceso"))
        item["ultimo_acceso_fecha"] = fecha
        item["ultimo_acceso_hora"] = hora
        fecha_p, hora_p, _ = _partir_timestamp(item.get("primer_acceso"))
        item["primer_acceso_fecha"] = fecha_p
        item["primer_acceso_hora"] = hora_p
        resultado.append(item)
    return resultado


def linea_tiempo(estudiante_id, limite=200, db_path=None):
    """Línea de tiempo del estudiante, del evento más reciente al más antiguo."""
    estudiante_id = _a_entero(estudiante_id)
    if not estudiante_id:
        return []
    try:
        limite = max(1, min(int(limite), 2000))
    except (TypeError, ValueError):
        limite = 200

    conn = _conexion(db_path)
    try:
        filas = conn.execute("""
            SELECT e.id, e.evento, e.modulo, e.registro_id, e.detalle, e.timestamp,
                   e.actividad_id, e.sesion_id, e.empresa_id
              FROM eventos_estudiante e
             WHERE e.usuario_id = ?
             ORDER BY e.timestamp DESC, e.id DESC
             LIMIT ?
        """, (estudiante_id, limite)).fetchall()
    finally:
        conn.close()

    eventos = []
    for fila in filas:
        item = dict(fila)
        fecha, hora, legible = _partir_timestamp(item.get("timestamp"))
        item["fecha"] = fecha
        item["hora"] = hora
        item["fecha_legible"] = legible
        eventos.append(item)
    return eventos


def exportar_csv(filtros=None, db_path=None):
    """Devuelve el contenido CSV (texto) del resumen de accesos."""
    filas = resumen_accesos(filtros, db_path=db_path)

    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow([
        "Estudiante", "Usuario", "Correo", "Paralelo", "Matrícula", "Estado de la cuenta",
        "Primer acceso", "Último acceso", "Sesiones", "Tiempo de actividad",
        "Actividades iniciadas", "Actividades asignadas", "Actividades completadas",
        "Evidencias generadas", "Última acción",
    ])
    for fila in filas:
        escritor.writerow([
            fila.get("nombre") or "", fila.get("username") or "", fila.get("correo") or "",
            fila.get("paralelo") or "", fila.get("matricula") or "", fila.get("estado_cuenta") or "",
            fila.get("primer_acceso") or "", fila.get("ultimo_acceso") or "",
            fila.get("num_sesiones") or 0, fila.get("tiempo_actividad") or "0 min",
            fila.get("actividades_iniciadas") or 0, fila.get("actividades_asignadas") or 0,
            fila.get("actividades_completadas") or 0, fila.get("evidencias_generadas") or 0,
            fila.get("ultima_accion") or "",
        ])
    return "\ufeff" + salida.getvalue()


def listado_docente_estudiantes(db_path=None):
    """Todos los estudiantes con su estado y si alguna vez ingresaron."""
    conn = _conexion(db_path)
    try:
        filas = conn.execute("""
            SELECT u.id AS estudiante_id, u.username,
                   u.nombre_completo AS nombre, u.email AS correo,
                   u.paralelo, u.matricula, COALESCE(u.activo, 0) AS activo, u.creado_en,
                   (SELECT COUNT(*) FROM sesiones_usuario s WHERE s.usuario_id = u.id) AS num_sesiones,
                   (SELECT MAX(s.inicio) FROM sesiones_usuario s WHERE s.usuario_id = u.id) AS ultimo_acceso,
                   (SELECT COUNT(*) FROM eventos_estudiante e WHERE e.usuario_id = u.id) AS num_eventos,
                   (SELECT COUNT(*) FROM evidencias v WHERE v.estudiante_id = u.id) AS evidencias_generadas,
                   (SELECT COUNT(*) FROM asignaciones_actividad a WHERE a.estudiante_id = u.id) AS actividades_asignadas,
                   (SELECT COALESCE(SUM(s.duracion_seg), 0) FROM sesiones_usuario s WHERE s.usuario_id = u.id) AS tiempo_seg
              FROM usuarios u
              JOIN roles r ON u.rol_id = r.id
             WHERE r.nombre = 'Estudiante'
             ORDER BY u.nombre_completo COLLATE NOCASE ASC
        """).fetchall()
    finally:
        conn.close()

    estudiantes = []
    for fila in filas:
        item = dict(fila)
        item["estado_cuenta"] = "Activo" if item.get("activo") else "Inactivo"
        item["ha_ingresado"] = (item.get("num_sesiones") or 0) > 0
        item["tiempo_actividad"] = formatear_duracion(item.get("tiempo_seg"))
        fecha, hora, _ = _partir_timestamp(item.get("ultimo_acceso"))
        item["ultimo_acceso_fecha"] = fecha
        item["ultimo_acceso_hora"] = hora
        estudiantes.append(item)
    return estudiantes


def listado_estudiantes_sin_ingreso(db_path=None):
    """Estudiantes que nunca iniciaron sesión en el simulador."""
    return [e for e in listado_docente_estudiantes(db_path=db_path) if not e["ha_ingresado"]]


def sesiones_de_estudiante(estudiante_id, limite=100, db_path=None):
    """Historial de sesiones (del más reciente al más antiguo)."""
    estudiante_id = _a_entero(estudiante_id)
    if not estudiante_id:
        return []
    try:
        limite = max(1, min(int(limite), 1000))
    except (TypeError, ValueError):
        limite = 100

    conn = _conexion(db_path)
    try:
        filas = conn.execute("""
            SELECT id, inicio, fin, COALESCE(duracion_seg, 0) AS duracion_seg,
                   ip_origen, navegador, COALESCE(activa, 0) AS activa
              FROM sesiones_usuario
             WHERE usuario_id = ?
             ORDER BY inicio DESC, id DESC
             LIMIT ?
        """, (estudiante_id, limite)).fetchall()
    finally:
        conn.close()

    sesiones = []
    for fila in filas:
        item = dict(fila)
        item["duracion"] = formatear_duracion(item.get("duracion_seg"))
        item["estado"] = "En curso" if item.get("activa") else "Cerrada"
        fecha, hora, _ = _partir_timestamp(item.get("inicio"))
        item["inicio_fecha"] = fecha
        item["inicio_hora"] = hora
        fecha_f, hora_f, _ = _partir_timestamp(item.get("fin"))
        item["fin_fecha"] = fecha_f
        item["fin_hora"] = hora_f
        sesiones.append(item)
    return sesiones


def actividades_de_estudiante(estudiante_id, db_path=None):
    """Actividades asignadas al estudiante con su estado e intentos usados."""
    estudiante_id = _a_entero(estudiante_id)
    if not estudiante_id:
        return []
    conn = _conexion(db_path)
    try:
        filas = conn.execute("""
            SELECT a.id, a.codigo, a.titulo, a.unidad, a.componente, a.estado AS estado_actividad,
                   a.puntaje, a.fecha_cierre, a.tipo_evidencia,
                   ag.id AS asignacion_id, ag.estado AS estado_asignacion,
                   COALESCE(ag.intentos_usados, 0) AS intentos_usados,
                   ag.nota, ag.abierta_en, ag.cerrada_en
              FROM asignaciones_actividad ag
              JOIN actividades a ON ag.actividad_id = a.id
             WHERE ag.estudiante_id = ?
             ORDER BY a.unidad ASC, a.codigo ASC
        """, (estudiante_id,)).fetchall()
    finally:
        conn.close()
    return [dict(f) for f in filas]


def evidencias_de_estudiante(estudiante_id, db_path=None):
    """Evidencias generadas por el estudiante."""
    estudiante_id = _a_entero(estudiante_id)
    if not estudiante_id:
        return []
    conn = _conexion(db_path)
    try:
        filas = conn.execute("""
            SELECT v.id, v.codigo, v.titulo, v.tipo, v.estado, v.generada_en,
                   COALESCE(v.modificada_despues, 0) AS modificada_despues,
                   a.codigo AS actividad_codigo, a.titulo AS actividad_titulo
              FROM evidencias v
              LEFT JOIN actividades a ON v.actividad_id = a.id
             WHERE v.estudiante_id = ?
             ORDER BY v.generada_en DESC, v.id DESC
        """, (estudiante_id,)).fetchall()
    finally:
        conn.close()

    evidencias = []
    for fila in filas:
        item = dict(fila)
        fecha, hora, _ = _partir_timestamp(item.get("generada_en"))
        item["fecha"] = fecha
        item["hora"] = hora
        evidencias.append(item)
    return evidencias


def intentos_de_estudiante(estudiante_id, limite=50, db_path=None):
    """Intentos de simulación del estudiante (actividades evaluativas)."""
    estudiante_id = _a_entero(estudiante_id)
    if not estudiante_id:
        return []
    try:
        limite = max(1, min(int(limite), 500))
    except (TypeError, ValueError):
        limite = 50

    conn = _conexion(db_path)
    try:
        filas = conn.execute("""
            SELECT i.id, i.fecha_inicio, i.fecha_fin, COALESCE(i.puntuacion_total, 0) AS puntuacion_total,
                   i.estado, COALESCE(i.tiempo_segundos, 0) AS tiempo_segundos,
                   s.titulo AS simulacion_titulo
              FROM intentos_estudiante i
              LEFT JOIN simulaciones s ON i.simulacion_id = s.id
             WHERE i.estudiante_id = ?
             ORDER BY i.fecha_inicio DESC, i.id DESC
             LIMIT ?
        """, (estudiante_id, limite)).fetchall()
    finally:
        conn.close()

    intentos = []
    for fila in filas:
        item = dict(fila)
        fecha, hora, _ = _partir_timestamp(item.get("fecha_inicio"))
        item["fecha"] = fecha
        item["hora"] = hora
        intentos.append(item)
    return intentos


def ficha_estudiante(estudiante_id, db_path=None):
    """Ficha completa del estudiante para el panel docente."""
    estudiante_id = _a_entero(estudiante_id)
    if not estudiante_id:
        return None

    conn = _conexion(db_path)
    try:
        fila = conn.execute("""
            SELECT u.id AS estudiante_id, u.username, u.nombre_completo AS nombre,
                   u.email AS correo, u.paralelo, u.matricula, r.nombre AS rol_nombre,
                   COALESCE(u.activo, 0) AS activo, u.creado_en,
                   COALESCE(e.razon_social, e.nombre_comercial, '') AS empresa
              FROM usuarios u
              JOIN roles r ON u.rol_id = r.id
              LEFT JOIN empresas e ON e.estudiante_id = u.id
             WHERE u.id = ?
        """, (estudiante_id,)).fetchone()
    finally:
        conn.close()

    if not fila:
        return None

    ficha = dict(fila)
    ficha["estado_cuenta"] = "Activo" if ficha.get("activo") else "Inactivo"

    resumen = resumen_accesos({"estudiante_id": estudiante_id}, db_path=db_path)
    indicadores = resumen[0] if resumen else {}
    if not indicadores:
        indicadores = {
            "num_sesiones": 0, "tiempo_seg": 0, "tiempo_actividad": "0 min",
            "actividades_iniciadas": 0, "actividades_completadas": 0,
            "evidencias_generadas": 0, "ultima_accion": None, "num_eventos": 0,
        }

    return {
        "datos": ficha,
        "indicadores": indicadores,
        "sesiones": sesiones_de_estudiante(estudiante_id, db_path=db_path),
        "linea_tiempo": linea_tiempo(estudiante_id, limite=200, db_path=db_path),
        "actividades": actividades_de_estudiante(estudiante_id, db_path=db_path),
        "evidencias": evidencias_de_estudiante(estudiante_id, db_path=db_path),
        "intentos": intentos_de_estudiante(estudiante_id, db_path=db_path),
    }


def paralelos_disponibles(db_path=None):
    """Paralelos existentes en la base, para llenar el filtro del panel."""
    conn = _conexion(db_path)
    try:
        filas = conn.execute("""
            SELECT DISTINCT u.paralelo FROM usuarios u
              JOIN roles r ON u.rol_id = r.id
             WHERE r.nombre = 'Estudiante' AND u.paralelo IS NOT NULL AND TRIM(u.paralelo) <> ''
             ORDER BY u.paralelo
        """).fetchall()
    finally:
        conn.close()
    return [fila[0] for fila in filas]


def actividades_disponibles(db_path=None):
    """Actividades existentes (codigo/titulo) para el filtro del panel."""
    conn = _conexion(db_path)
    try:
        filas = conn.execute("""
            SELECT id, codigo, titulo, unidad FROM actividades ORDER BY unidad ASC, codigo ASC
        """).fetchall()
    finally:
        conn.close()
    return [dict(f) for f in filas]


# ---------------------------------------------------------------------------
# Fachada de clase (misma API en estilo AuditService)
# ---------------------------------------------------------------------------
class AccessService:
    """Fachada de conveniencia sobre las funciones del módulo."""

    EVENTOS_PERMITIDOS = EVENTOS_PERMITIDOS

    abrir_sesion = staticmethod(abrir_sesion)
    cerrar_sesion = staticmethod(cerrar_sesion)
    cerrar_sesiones_huerfanas = staticmethod(cerrar_sesiones_huerfanas)
    registrar_evento = staticmethod(registrar_evento)
    registrar_evento_desde_request = staticmethod(registrar_evento_desde_request)
    resumen_accesos = staticmethod(resumen_accesos)
    linea_tiempo = staticmethod(linea_tiempo)
    exportar_csv = staticmethod(exportar_csv)
    listado_docente_estudiantes = staticmethod(listado_docente_estudiantes)
    listado_estudiantes_sin_ingreso = staticmethod(listado_estudiantes_sin_ingreso)
    sesiones_de_estudiante = staticmethod(sesiones_de_estudiante)
    actividades_de_estudiante = staticmethod(actividades_de_estudiante)
    evidencias_de_estudiante = staticmethod(evidencias_de_estudiante)
    intentos_de_estudiante = staticmethod(intentos_de_estudiante)
    ficha_estudiante = staticmethod(ficha_estudiante)
    paralelos_disponibles = staticmethod(paralelos_disponibles)
    actividades_disponibles = staticmethod(actividades_disponibles)
    formatear_duracion = staticmethod(formatear_duracion)
