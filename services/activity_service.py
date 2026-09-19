# -*- coding: utf-8 -*-
"""Servicio del módulo de ACTIVIDADES del syllabus (Contabilidad I).

Administra las actividades del syllabus, su asignación individual a cada estudiante y el
ciclo de vida de la asignación:

    PENDIENTE  ->  EN_CURSO  ->  ENTREGADA  ->  REVISADA

Estados de la actividad (tabla `actividades.estado`): BORRADOR | ABIERTA | CERRADA.
Una asignación solo se puede iniciar si la actividad está ABIERTA **y** la fecha actual
cae dentro de la ventana de apertura/cierre.

Convenciones del proyecto:
    * Se usa `models.get_db_connection()`, `dict_from_row()` y `dicts_from_rows()`.
    * Todas las funciones aceptan `db_path` para las pruebas (por defecto Config.DATABASE_PATH).
    * Los errores de negocio se lanzan como `ErrorActividad` (subclase de ValueError) con un
      atributo `estado_http` para que las rutas respondan con el código correcto.
"""

import json
from datetime import datetime

from models import get_db_connection, dict_from_row, dicts_from_rows

# --------------------------------------------------------------------------- Constantes
COMPONENTES_VALIDOS = ("DOCENCIA", "PRACTICA", "AUTONOMO")
ESTADOS_VALIDOS = ("BORRADOR", "ABIERTA", "CERRADA")
TIPOS_EVIDENCIA_VALIDOS = ("PLAN_CUENTAS", "DIARIO", "MAYOR", "BALANCE", "INTEGRAL")
MODULOS_VALIDOS = ("CUENTAS", "DIARIO", "MAYOR", "BALANCE", "ESTADOS")

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


class ErrorActividad(ValueError):
    """Error de negocio del módulo de actividades."""

    def __init__(self, mensaje, estado_http=400, codigo="VALIDACION"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.estado_http = estado_http
        self.codigo = codigo


class ActividadNoAsignada(ErrorActividad):
    """La actividad no está asignada al estudiante (o no existe la asignación)."""

    def __init__(self, mensaje="La actividad no está asignada a este estudiante."):
        super().__init__(mensaje, estado_http=404, codigo="NO_ASIGNADA")


class ActividadNoDisponible(ErrorActividad):
    """La actividad existe pero no está abierta o está fuera de la ventana de fechas."""

    def __init__(self, mensaje):
        super().__init__(mensaje, estado_http=409, codigo="NO_DISPONIBLE")


# --------------------------------------------------------------------------- Utilidades
def _ahora():
    return datetime.now()


def _parse_fecha(valor, fin_de_dia=False):
    """Convierte a datetime un valor TEXT de SQLite ('AAAA-MM-DD' o 'AAAA-MM-DD HH:MM:SS').

    Si el valor solo trae la fecha y `fin_de_dia` es True (caso de fecha_cierre), se
    interpreta como el final de ese día, de modo que la actividad sigue abierta el día límite.
    """
    if valor in (None, "", "None"):
        return None
    texto = str(valor).strip().replace("T", " ")
    if "." in texto:
        texto = texto.split(".")[0]
    intentos = [(texto[:19], FORMATO_FECHA), (texto[:16], "%Y-%m-%d %H:%M"), (texto[:10], "%Y-%m-%d")]
    for recorte, formato in intentos:
        try:
            fecha = datetime.strptime(recorte, formato)
        except ValueError:
            continue
        if formato == "%Y-%m-%d" and fin_de_dia:
            return fecha.replace(hour=23, minute=59, second=59)
        return fecha
    return None


def _texto_legible(valor):
    fecha = _parse_fecha(valor)
    return fecha.strftime("%Y-%m-%d %H:%M") if fecha else None


def _esta_abierta(actividad, ahora=None):
    """True si la actividad está ABIERTA y la fecha actual cae dentro de su ventana."""
    if str(actividad.get("estado") or "").upper() != "ABIERTA":
        return False
    ahora = ahora or _ahora()
    apertura = _parse_fecha(actividad.get("fecha_apertura"))
    cierre = _parse_fecha(actividad.get("fecha_cierre"), fin_de_dia=True)
    if apertura and ahora < apertura:
        return False
    if cierre and ahora > cierre:
        return False
    return True


def _motivo_no_disponible(actividad, ahora=None):
    """Explica en español por qué la actividad no se puede trabajar."""
    estado = str(actividad.get("estado") or "BORRADOR").upper()
    ahora = ahora or _ahora()
    apertura = _parse_fecha(actividad.get("fecha_apertura"))
    cierre = _parse_fecha(actividad.get("fecha_cierre"), fin_de_dia=True)
    if estado != "ABIERTA":
        return {"BORRADOR": "La actividad aún no ha sido publicada por el docente.",
                "CERRADA": "La actividad fue cerrada por el docente."}.get(
                    estado, f"La actividad está en estado {estado}.")
    if apertura and ahora < apertura:
        return "La actividad se habilita el %s." % apertura.strftime("%d/%m/%Y %H:%M")
    if cierre and ahora > cierre:
        return "La actividad cerró el %s." % cierre.strftime("%d/%m/%Y %H:%M")
    return "La actividad no está disponible en este momento."


def _empresa_de_estudiante(conn, estudiante_id):
    """Empresa simulada del estudiante.

    Si el estudiante aún no tiene empresa propia (empresas.estudiante_id), se usa la empresa
    de demostración del curso, que es sobre la que trabaja todo el grupo.
    """
    fila = conn.execute(
        "SELECT id FROM empresas WHERE estudiante_id = ? ORDER BY id LIMIT 1",
        (estudiante_id,)).fetchone()
    if fila:
        return fila["id"]
    fila = conn.execute("SELECT id FROM empresas ORDER BY IFNULL(es_demo, 0) DESC, id ASC LIMIT 1").fetchone()
    return fila["id"] if fila else None


def _registrar_evento(conn, estudiante_id, actividad_id, evento, detalle, registro_id=None):
    """Anota un evento del estudiante en eventos_estudiante (trazabilidad pedagógica)."""
    empresa_id = _empresa_de_estudiante(conn, estudiante_id)
    conn.execute("""
        INSERT INTO eventos_estudiante (usuario_id, empresa_id, actividad_id, evento, modulo,
                                        registro_id, detalle)
        VALUES (?, ?, ?, ?, 'ACTIVIDADES', ?, ?)
    """, (estudiante_id, empresa_id, actividad_id, evento,
          str(registro_id) if registro_id is not None else None,
          json.dumps(detalle, ensure_ascii=False, default=str)))


def _normalizar_fecha(valor, fin_de_dia=False):
    """Normaliza una fecha recibida del formulario a 'AAAA-MM-DD HH:MM:SS'."""
    fecha = _parse_fecha(valor, fin_de_dia=fin_de_dia)
    if fecha is None:
        return None
    if not fin_de_dia:
        return fecha.replace(hour=0, minute=0, second=0).strftime(FORMATO_FECHA)
    return fecha.strftime(FORMATO_FECHA)


def _enriquecer_asignacion(fila, ahora=None):
    """Agrega a la fila de asignación los campos calculados de disponibilidad."""
    actividad = dict(fila)
    ahora = ahora or _ahora()
    actividad["abierta_ahora"] = _esta_abierta(actividad, ahora=ahora)
    actividad["apertura_legible"] = _texto_legible(actividad.get("fecha_apertura"))
    actividad["cierre_legible"] = _texto_legible(actividad.get("fecha_cierre"))
    actividad["abierta_en_legible"] = _texto_legible(actividad.get("abierta_en"))
    actividad["cerrada_en_legible"] = _texto_legible(actividad.get("cerrada_en"))
    actividad["motivo_disponibilidad"] = None if actividad["abierta_ahora"] else _motivo_no_disponible(actividad, ahora=ahora)
    estado_asignacion = str(actividad.get("estado_asignacion") or "PENDIENTE").upper()
    if estado_asignacion == "EN_CURSO":
        actividad["puede_iniciar"] = bool(actividad["abierta_ahora"])
        actividad["accion_sugerida"] = "Continuar actividad"
    elif estado_asignacion in ("ENTREGADA", "REVISADA"):
        actividad["puede_iniciar"] = False
        actividad["accion_sugerida"] = "Actividad entregada"
    else:
        intentos_maximos = int(actividad.get("intentos_maximos") or 1)
        intentos_usados = int(actividad.get("intentos_usados") or 0)
        actividad["puede_iniciar"] = bool(actividad["abierta_ahora"] and intentos_usados < intentos_maximos)
        actividad["accion_sugerida"] = "Iniciar actividad" if actividad["puede_iniciar"] else "No disponible"
    return actividad


# --------------------------------------------------------------------------- API pública
def listar_actividades_estudiante(estudiante_id, db_path=None):
    """Devuelve las actividades asignadas a un estudiante con su estado y disponibilidad.

    Cada elemento incluye: estado de la asignación, fechas, puntaje, intentos usados,
    si la actividad está abierta en este momento y la acción sugerida para la interfaz.
    """
    conn = get_db_connection(db_path)
    try:
        filas = conn.execute("""
            SELECT a.*,
                   asg.id            AS asignacion_id,
                   asg.estado        AS estado_asignacion,
                   asg.intentos_usados,
                   asg.abierta_en,
                   asg.cerrada_en,
                   asg.nota,
                   asg.observacion_docente,
                   asg.asignada_en
            FROM asignaciones_actividad asg
            JOIN actividades a ON a.id = asg.actividad_id
            WHERE asg.estudiante_id = ?
            ORDER BY a.unidad ASC, a.codigo ASC
        """, (estudiante_id,)).fetchall()
        ahora = _ahora()
        return [_enriquecer_asignacion(dict(f), ahora=ahora) for f in filas]
    finally:
        conn.close()


def obtener_asignacion(actividad_id, estudiante_id, db_path=None):
    """Asignación concreta de una actividad a un estudiante (None si no está asignada)."""
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("""
            SELECT asg.*, a.codigo, a.titulo, a.unidad, a.componente, a.puntaje,
                   a.fecha_apertura, a.fecha_cierre, a.intentos_maximos, a.estado AS estado_actividad,
                   a.tipo_evidencia, a.instrucciones, a.evidencia_requerida, a.modulos_habilitados,
                   a.resultado_aprendizaje, a.modo_practica, a.tutor_ia
            FROM asignaciones_actividad asg
            JOIN actividades a ON a.id = asg.actividad_id
            WHERE asg.actividad_id = ? AND asg.estudiante_id = ?
        """, (actividad_id, estudiante_id)).fetchone()
        if not fila:
            return None
        datos = dict(fila)
        datos["estado_asignacion"] = datos.get("estado")
        datos["estado"] = datos.get("estado_actividad")
        return _enriquecer_asignacion(datos)
    finally:
        conn.close()


def obtener_actividad(actividad_id, db_path=None):
    """Actividad del syllabus por su id (None si no existe)."""
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("SELECT * FROM actividades WHERE id = ?", (actividad_id,)).fetchone()
        return dict_from_row(fila)
    finally:
        conn.close()


def requiere_actividad_de_estudiante(actividad_id, estudiante_id, db_path=None):
    """Devuelve la asignación o lanza ActividadNoAsignada (aislamiento por estudiante)."""
    asignacion = obtener_asignacion(actividad_id, estudiante_id, db_path=db_path)
    if not asignacion:
        raise ActividadNoAsignada(
            "La actividad %s no está asignada a tu usuario." % actividad_id)
    return asignacion


def iniciar_actividad(actividad_id, estudiante_id, db_path=None):
    """Inicia (o retoma) una actividad asignada.

    Valida que la actividad esté asignada, ABIERTA y dentro de las fechas; pasa la asignación
    a EN_CURSO, registra `abierta_en`, incrementa `intentos_usados` respetando
    `intentos_maximos` y anota el evento INICIO_ACTIVIDAD en eventos_estudiante.

    Devuelve un dict con la asignación actualizada y el detalle del intento.
    """
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("""
            SELECT asg.*, a.codigo, a.titulo, a.estado AS estado_actividad, a.fecha_apertura,
                   a.fecha_cierre, a.intentos_maximos
            FROM asignaciones_actividad asg
            JOIN actividades a ON a.id = asg.actividad_id
            WHERE asg.actividad_id = ? AND asg.estudiante_id = ?
        """, (actividad_id, estudiante_id)).fetchone()
        if not fila:
            raise ActividadNoAsignada(
                "La actividad %s no está asignada a tu usuario." % actividad_id)

        asignacion = dict(fila)
        estado_asignacion = str(asignacion.get("estado") or "PENDIENTE").upper()

        actividad_para_fechas = {
            "estado": asignacion.get("estado_actividad"),
            "fecha_apertura": asignacion.get("fecha_apertura"),
            "fecha_cierre": asignacion.get("fecha_cierre"),
        }
        if not _esta_abierta(actividad_para_fechas):
            raise ActividadNoDisponible(_motivo_no_disponible(actividad_para_fechas))

        if estado_asignacion in ("ENTREGADA", "REVISADA"):
            raise ErrorActividad(
                "La actividad %s ya fue entregada (estado %s)." % (asignacion["codigo"], estado_asignacion),
                estado_http=409, codigo="YA_ENTREGADA")

        intentos_maximos = int(asignacion.get("intentos_maximos") or 1)
        intentos_usados = int(asignacion.get("intentos_usados") or 0)
        ahora = _ahora().strftime(FORMATO_FECHA)

        if estado_asignacion == "EN_CURSO":
            # Retomar una actividad en curso no consume un intento adicional.
            conn.execute("""
                UPDATE asignaciones_actividad SET abierta_en = COALESCE(abierta_en, ?)
                WHERE id = ?
            """, (ahora, asignacion["id"]))
            intento_numero = max(intentos_usados, 1)
            nuevo_intento = False
        else:
            if intentos_usados >= intentos_maximos:
                raise ErrorActividad(
                    "Se agotaron los intentos permitidos (%d de %d) para la actividad %s."
                    % (intentos_usados, intentos_maximos, asignacion["codigo"]),
                    estado_http=409, codigo="SIN_INTENTOS")
            intentos_usados += 1
            conn.execute("""
                UPDATE asignaciones_actividad
                   SET estado = 'EN_CURSO', abierta_en = ?, intentos_usados = ?
                 WHERE id = ?
            """, (ahora, intentos_usados, asignacion["id"]))
            intento_numero = intentos_usados
            nuevo_intento = True

        _registrar_evento(
            conn, estudiante_id, actividad_id, "INICIO_ACTIVIDAD",
            {"codigo": asignacion["codigo"], "titulo": asignacion["titulo"],
             "intento": intento_numero, "intentos_maximos": intentos_maximos,
             "nuevo_intento": nuevo_intento, "fecha": ahora},
            registro_id=asignacion["id"])

        conn.commit()
        actualizada = conn.execute(
            "SELECT * FROM asignaciones_actividad WHERE id = ?", (asignacion["id"],)).fetchone()
        resultado = dict_from_row(actualizada)
        resultado["codigo"] = asignacion["codigo"]
        resultado["titulo"] = asignacion["titulo"]
        resultado["intento"] = intento_numero
        resultado["nuevo_intento"] = nuevo_intento
        resultado["abierta_en_legible"] = _texto_legible(resultado.get("abierta_en"))
        return resultado
    finally:
        conn.close()


def cerrar_actividad(actividad_id, estudiante_id, db_path=None):
    """Marca la asignación como ENTREGADA y registra `cerrada_en`."""
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("""
            SELECT asg.*, a.codigo, a.titulo
            FROM asignaciones_actividad asg
            JOIN actividades a ON a.id = asg.actividad_id
            WHERE asg.actividad_id = ? AND asg.estudiante_id = ?
        """, (actividad_id, estudiante_id)).fetchone()
        if not fila:
            raise ActividadNoAsignada(
                "La actividad %s no está asignada a tu usuario." % actividad_id)

        asignacion = dict(fila)
        if str(asignacion.get("estado") or "").upper() in ("ENTREGADA", "REVISADA"):
            return asignacion

        ahora = _ahora().strftime(FORMATO_FECHA)
        conn.execute("""
            UPDATE asignaciones_actividad SET estado = 'ENTREGADA', cerrada_en = ? WHERE id = ?
        """, (ahora, asignacion["id"]))
        _registrar_evento(
            conn, estudiante_id, actividad_id, "ENTREGA_ACTIVIDAD",
            {"codigo": asignacion["codigo"], "titulo": asignacion["titulo"], "fecha": ahora},
            registro_id=asignacion["id"])
        conn.commit()
        actualizada = conn.execute(
            "SELECT * FROM asignaciones_actividad WHERE id = ?", (asignacion["id"],)).fetchone()
        resultado = dict_from_row(actualizada)
        resultado["codigo"] = asignacion["codigo"]
        resultado["titulo"] = asignacion["titulo"]
        return resultado
    finally:
        conn.close()


def crear_actividad(datos, db_path=None):
    """Crea (o actualiza, si el código ya existe) una actividad del syllabus.

    Es idempotente por `codigo`: volver a ejecutar el seed actualiza los datos de la
    actividad sin duplicarla y sin perder las asignaciones existentes.
    """
    if not isinstance(datos, dict):
        raise ErrorActividad("Los datos de la actividad deben enviarse como diccionario.")

    codigo = str(datos.get("codigo") or "").strip().upper()
    titulo = str(datos.get("titulo") or "").strip()
    if not codigo:
        raise ErrorActividad("El código de la actividad es obligatorio (por ejemplo U1-A1).")
    if not titulo:
        raise ErrorActividad("El título de la actividad es obligatorio.")

    componente = str(datos.get("componente") or "AUTONOMO").strip().upper()
    if componente not in COMPONENTES_VALIDOS:
        raise ErrorActividad("Componente inválido: %s (use %s)."
                             % (componente, ", ".join(COMPONENTES_VALIDOS)))

    estado = str(datos.get("estado") or "BORRADOR").strip().upper()
    if estado not in ESTADOS_VALIDOS:
        raise ErrorActividad("Estado inválido: %s (use %s)."
                             % (estado, ", ".join(ESTADOS_VALIDOS)))

    tipo_evidencia = datos.get("tipo_evidencia")
    if tipo_evidencia:
        tipo_evidencia = str(tipo_evidencia).strip().upper()
        if tipo_evidencia not in TIPOS_EVIDENCIA_VALIDOS:
            raise ErrorActividad("Tipo de evidencia inválido: %s (use %s)."
                                 % (tipo_evidencia, ", ".join(TIPOS_EVIDENCIA_VALIDOS)))

    modulos = datos.get("modulos_habilitados")
    if isinstance(modulos, (list, tuple, set)):
        modulos = ",".join(str(m).strip().upper() for m in modulos if str(m).strip())
    elif modulos:
        modulos = str(modulos).strip().upper()

    try:
        unidad = int(datos.get("unidad") or 1)
    except (TypeError, ValueError):
        raise ErrorActividad("La unidad debe ser un número entero (1 a 4).")

    try:
        puntaje = float(datos.get("puntaje") or 0)
    except (TypeError, ValueError):
        raise ErrorActividad("El puntaje debe ser numérico.")

    try:
        intentos_maximos = int(datos.get("intentos_maximos") or 1)
    except (TypeError, ValueError):
        raise ErrorActividad("Los intentos máximos deben ser un número entero.")

    valores = (
        codigo, titulo, unidad, componente,
        datos.get("resultado_aprendizaje"), datos.get("instrucciones"),
        datos.get("evidencia_requerida"), puntaje,
        _normalizar_fecha(datos.get("fecha_apertura")),
        _normalizar_fecha(datos.get("fecha_cierre"), fin_de_dia=True),
        max(intentos_maximos, 1), 1 if datos.get("modo_practica") else 0,
        1 if datos.get("tutor_ia") else 0, modulos, tipo_evidencia, estado,
        datos.get("creada_por"),
    )

    conn = get_db_connection(db_path)
    try:
        conn.execute("""
            INSERT INTO actividades (codigo, titulo, unidad, componente, resultado_aprendizaje,
                instrucciones, evidencia_requerida, puntaje, fecha_apertura, fecha_cierre,
                intentos_maximos, modo_practica, tutor_ia, modulos_habilitados, tipo_evidencia,
                estado, creada_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(codigo) DO UPDATE SET
                titulo = excluded.titulo,
                unidad = excluded.unidad,
                componente = excluded.componente,
                resultado_aprendizaje = excluded.resultado_aprendizaje,
                instrucciones = excluded.instrucciones,
                evidencia_requerida = excluded.evidencia_requerida,
                puntaje = excluded.puntaje,
                fecha_apertura = excluded.fecha_apertura,
                fecha_cierre = excluded.fecha_cierre,
                intentos_maximos = excluded.intentos_maximos,
                modo_practica = excluded.modo_practica,
                tutor_ia = excluded.tutor_ia,
                modulos_habilitados = excluded.modulos_habilitados,
                tipo_evidencia = excluded.tipo_evidencia,
                estado = excluded.estado
        """, valores)
        conn.commit()
        fila = conn.execute("SELECT * FROM actividades WHERE codigo = ?", (codigo,)).fetchone()
        return dict_from_row(fila)
    finally:
        conn.close()


def asignar_a_estudiantes(actividad_id, estudiante_ids, db_path=None):
    """Asigna la actividad a los estudiantes indicados. Es idempotente (INSERT OR IGNORE).

    Devuelve {'asignadas': n, 'ya_existentes': n, 'actividad_id': id, 'estudiantes': [...]}.
    """
    actividad = obtener_actividad(actividad_id, db_path=db_path)
    if not actividad:
        raise ErrorActividad("No existe la actividad %s." % actividad_id, estado_http=404,
                             codigo="ACTIVIDAD_INEXISTENTE")

    if isinstance(estudiante_ids, (int, str)):
        estudiante_ids = [estudiante_ids]
    ids = []
    for valor in (estudiante_ids or []):
        try:
            ids.append(int(valor))
        except (TypeError, ValueError):
            continue
    ids = sorted(set(ids))

    conn = get_db_connection(db_path)
    try:
        asignadas, ya_existentes, validos = 0, 0, []
        for estudiante_id in ids:
            existe = conn.execute("SELECT 1 FROM usuarios WHERE id = ?", (estudiante_id,)).fetchone()
            if not existe:
                continue
            validos.append(estudiante_id)
            empresa_id = _empresa_de_estudiante(conn, estudiante_id)
            cursor = conn.execute("""
                INSERT OR IGNORE INTO asignaciones_actividad
                    (actividad_id, estudiante_id, empresa_id, estado, intentos_usados)
                VALUES (?, ?, ?, 'PENDIENTE', 0)
            """, (actividad_id, estudiante_id, empresa_id))
            if cursor.rowcount:
                asignadas += 1
            else:
                ya_existentes += 1
        conn.commit()
        return {"actividad_id": actividad_id, "codigo": actividad.get("codigo"),
                "asignadas": asignadas, "ya_existentes": ya_existentes,
                "estudiantes": validos}
    finally:
        conn.close()


def estudiantes_activos(db_path=None):
    """Estudiantes activos (rol Estudiante) para asignaciones masivas."""
    conn = get_db_connection(db_path)
    try:
        filas = conn.execute("""
            SELECT u.id, u.username, u.nombre_completo, u.paralelo
            FROM usuarios u JOIN roles r ON u.rol_id = r.id
            WHERE r.nombre = 'Estudiante' AND u.activo = 1
            ORDER BY u.id
        """).fetchall()
        return dicts_from_rows(filas)
    finally:
        conn.close()


def asignar_a_todos_los_estudiantes(actividad_id, db_path=None):
    """Asigna la actividad a todos los estudiantes activos (asignación masiva idempotente)."""
    return asignar_a_estudiantes(actividad_id,
                                 [e["id"] for e in estudiantes_activos(db_path=db_path)],
                                 db_path=db_path)


def listado_docente(filtros=None, db_path=None):
    """Listado de actividades para el docente con conteo de asignadas/entregadas.

    Filtros admitidos: `unidad`, `componente`, `estado`, `estudiante_id` y `q` (búsqueda
    libre en código, título o instrucciones).
    """
    filtros = filtros or {}
    condiciones, parametros = [], []

    if filtros.get("unidad"):
        condiciones.append("a.unidad = ?")
        parametros.append(int(filtros["unidad"]))
    if filtros.get("componente"):
        condiciones.append("UPPER(a.componente) = ?")
        parametros.append(str(filtros["componente"]).strip().upper())
    if filtros.get("estado"):
        condiciones.append("UPPER(a.estado) = ?")
        parametros.append(str(filtros["estado"]).strip().upper())
    if filtros.get("q"):
        condiciones.append("(a.codigo LIKE ? OR a.titulo LIKE ? OR IFNULL(a.instrucciones, '') LIKE ?)")
        patron = "%%%s%%" % str(filtros["q"]).strip()
        parametros.extend([patron, patron, patron])
    if filtros.get("estudiante_id"):
        condiciones.append("""EXISTS (SELECT 1 FROM asignaciones_actividad x
                              WHERE x.actividad_id = a.id AND x.estudiante_id = ?)""")
        parametros.append(int(filtros["estudiante_id"]))

    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    conn = get_db_connection(db_path)
    try:
        filas = conn.execute("""
            SELECT a.*,
                   COUNT(asg.id) AS asignadas,
                   SUM(CASE WHEN asg.estado IN ('ENTREGADA', 'REVISADA') THEN 1 ELSE 0 END) AS entregadas,
                   SUM(CASE WHEN asg.estado = 'EN_CURSO' THEN 1 ELSE 0 END) AS en_curso,
                   SUM(CASE WHEN asg.estado = 'PENDIENTE' THEN 1 ELSE 0 END) AS pendientes,
                   ROUND(AVG(asg.nota), 2) AS nota_promedio
            FROM actividades a
            LEFT JOIN asignaciones_actividad asg ON asg.actividad_id = a.id
            %s
            GROUP BY a.id
            ORDER BY a.unidad ASC, a.codigo ASC
        """ % where, parametros).fetchall()

        actividades = []
        for fila in filas:
            datos = dict(fila)
            for campo in ("asignadas", "entregadas", "en_curso", "pendientes"):
                datos[campo] = int(datos.get(campo) or 0)
            datos["abierta_ahora"] = _esta_abierta(datos)
            datos["apertura_legible"] = _texto_legible(datos.get("fecha_apertura"))
            datos["cierre_legible"] = _texto_legible(datos.get("fecha_cierre"))
            datos["porcentaje_entrega"] = (round(100.0 * datos["entregadas"] / datos["asignadas"], 1)
                                           if datos["asignadas"] else 0.0)
            actividades.append(datos)
        return actividades
    finally:
        conn.close()


def resumen_asignaciones(actividad_id, db_path=None):
    """Detalle de las asignaciones de una actividad (para la vista del docente)."""
    conn = get_db_connection(db_path)
    try:
        filas = conn.execute("""
            SELECT asg.*, u.username, u.nombre_completo, u.paralelo,
                   e.codigo AS evidencia_codigo, e.estado AS evidencia_estado,
                   e.modificada_despues AS evidencia_modificada
            FROM asignaciones_actividad asg
            JOIN usuarios u ON u.id = asg.estudiante_id
            LEFT JOIN evidencias e ON e.estudiante_id = asg.estudiante_id
                 AND e.actividad_id = asg.actividad_id
            WHERE asg.actividad_id = ?
            ORDER BY u.nombre_completo
        """, (actividad_id,)).fetchall()
        return dicts_from_rows(filas)
    finally:
        conn.close()


class ActivityService:
    """Fachada con la misma API, para el estilo de servicios del proyecto."""

    listar_actividades_estudiante = staticmethod(listar_actividades_estudiante)
    obtener_asignacion = staticmethod(obtener_asignacion)
    obtener_actividad = staticmethod(obtener_actividad)
    requiere_actividad_de_estudiante = staticmethod(requiere_actividad_de_estudiante)
    iniciar_actividad = staticmethod(iniciar_actividad)
    cerrar_actividad = staticmethod(cerrar_actividad)
    crear_actividad = staticmethod(crear_actividad)
    asignar_a_estudiantes = staticmethod(asignar_a_estudiantes)
    asignar_a_todos_los_estudiantes = staticmethod(asignar_a_todos_los_estudiantes)
    estudiantes_activos = staticmethod(estudiantes_activos)
    listado_docente = staticmethod(listado_docente)
    resumen_asignaciones = staticmethod(resumen_asignaciones)
    esta_abierta = staticmethod(_esta_abierta)
    ErrorActividad = ErrorActividad
    ActividadNoAsignada = ActividadNoAsignada
    ActividadNoDisponible = ActividadNoDisponible
