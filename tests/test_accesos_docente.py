# -*- coding: utf-8 -*-
"""Pruebas del seguimiento de ACCESOS de estudiantes y del Panel Docente.

Cubren:
  * el enganche con /login y /logout (sesiones_usuario y eventos_estudiante);
  * los indicadores de la tabla de resumen;
  * los filtros y la exportación CSV del panel docente;
  * el control de acceso por rol (el estudiante no entra al panel);
  * el hook after_request que deduce eventos a partir del endpoint visitado.
"""
import pytest

from models import get_db_connection
from services.access_service import (
    AccessService,
    abrir_sesion,
    cerrar_sesion,
    cerrar_sesiones_huerfanas,
    exportar_csv,
    ficha_estudiante,
    linea_tiempo,
    listado_docente_estudiantes,
    listado_estudiantes_sin_ingreso,
    registrar_evento,
    resumen_accesos,
)

CREDENCIALES_ESTUDIANTE = {"username": "estudiante", "password": "estudiante123"}
CREDENCIALES_DOCENTE = {"username": "docente", "password": "docente123"}
ID_ESTUDIANTE = 3  # usuario 'estudiante' de la base demostrativa


# ---------------------------------------------------------------------------
# Utilidades de las pruebas
# ---------------------------------------------------------------------------
def _conexion(db):
    return get_db_connection(db)


def _sesiones(db, usuario_id=ID_ESTUDIANTE):
    conn = _conexion(db)
    try:
        filas = conn.execute(
            "SELECT * FROM sesiones_usuario WHERE usuario_id = ? ORDER BY id ASC",
            (usuario_id,)).fetchall()
        return [dict(f) for f in filas]
    finally:
        conn.close()


def _eventos(db, usuario_id=ID_ESTUDIANTE, tipo=None):
    conn = _conexion(db)
    try:
        sql = "SELECT * FROM eventos_estudiante WHERE usuario_id = ?"
        params = [usuario_id]
        if tipo:
            sql += " AND evento = ?"
            params.append(tipo)
        sql += " ORDER BY id ASC"
        return [dict(f) for f in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _retroceder_inicio(db, sesion_id, segundos):
    """Ubica el inicio de la sesión en el pasado para poder medir la duración."""
    conn = _conexion(db)
    try:
        conn.execute("UPDATE sesiones_usuario SET inicio = datetime('now', ?) WHERE id = ?",
                     ("-%d seconds" % int(segundos), sesion_id))
        conn.commit()
    finally:
        conn.close()


def _login(cliente, credenciales=CREDENCIALES_ESTUDIANTE):
    return cliente.post("/login", data=dict(credenciales), follow_redirects=True)


# ---------------------------------------------------------------------------
# Aplicación de prueba con el blueprint docente
# ---------------------------------------------------------------------------
@pytest.fixture()
def app_docente(db):
    """Aplicación Flask con el blueprint `teacher` registrado.

    El registro es idempotente: si el orquestador ya lo agregó en
    routes/__init__.py la prueba sigue funcionando sin cambios.
    """
    import app as app_module
    from routes.teacher import teacher_bp

    aplicacion = app_module.create_app()
    aplicacion.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    if "teacher" not in aplicacion.blueprints:
        aplicacion.register_blueprint(teacher_bp)
    return aplicacion


@pytest.fixture()
def app_docente_hook(app_docente):
    """Igual que `app_docente` pero con el hook global after_request activo."""
    from services.access_service import registrar_evento_desde_request

    app_docente.after_request(registrar_evento_desde_request)
    return app_docente


@pytest.fixture()
def cliente_estudiante(app_docente):
    cliente = app_docente.test_client()
    _login(cliente)
    return cliente


@pytest.fixture()
def cliente_docente(app_docente):
    cliente = app_docente.test_client()
    _login(cliente, CREDENCIALES_DOCENTE)
    return cliente


# ---------------------------------------------------------------------------
# 1) Login y logout: sesiones y eventos
# ---------------------------------------------------------------------------
def test_login_crea_sesion_y_evento_login(app_docente, db):
    cliente = app_docente.test_client()
    respuesta = _login(cliente)
    assert respuesta.status_code == 200

    sesiones = _sesiones(db)
    assert len(sesiones) == 1, "el login debe abrir exactamente una sesión"
    assert sesiones[0]["activa"] == 1
    assert sesiones[0]["fin"] is None
    assert sesiones[0]["duracion_seg"] == 0
    assert sesiones[0]["ip_origen"]

    eventos = _eventos(db, tipo="LOGIN")
    assert len(eventos) == 1, "el login debe registrar un único evento LOGIN"
    assert eventos[0]["sesion_id"] == sesiones[0]["id"]
    assert eventos[0]["modulo"] == "AUTH"


def test_logout_cierra_la_sesion_y_calcula_la_duracion(app_docente, db):
    cliente = app_docente.test_client()
    _login(cliente)

    sesiones = _sesiones(db)
    assert len(sesiones) == 1
    sesion_id = sesiones[0]["id"]
    _retroceder_inicio(db, sesion_id, 300)

    respuesta = cliente.get("/logout", follow_redirects=True)
    assert respuesta.status_code == 200

    cerrada = _sesiones(db)[0]
    assert cerrada["activa"] == 0
    assert cerrada["fin"] is not None
    assert cerrada["duracion_seg"] >= 295, "la duración debe reflejar los 300 s transcurridos"

    tipos = [e["evento"] for e in _eventos(db)]
    assert "LOGOUT" in tipos
    assert _eventos(db, tipo="LOGOUT")[0]["sesion_id"] == sesion_id


def test_dos_sesiones_seguidas_no_dejan_la_primera_activa(app_docente, db):
    """Un segundo ingreso del mismo usuario cierra la sesión anterior colgada."""
    primer_navegador = app_docente.test_client()
    assert _login(primer_navegador).status_code == 200

    segundo_navegador = app_docente.test_client()
    assert _login(segundo_navegador).status_code == 200

    sesiones = _sesiones(db)
    assert len(sesiones) == 2, "cada ingreso abre su propia sesión"
    assert sesiones[0]["activa"] == 0, "la primera sesión debe quedar cerrada"
    assert sesiones[0]["fin"] is not None
    assert sesiones[1]["activa"] == 1, "solo la última sesión puede quedar activa"
    assert sum(1 for s in sesiones if s["activa"]) == 1

    # El servicio expone la misma regla de forma directa.
    assert cerrar_sesiones_huerfanas(ID_ESTUDIANTE, db_path=db) == 1
    assert sum(1 for s in _sesiones(db) if s["activa"]) == 0


# ---------------------------------------------------------------------------
# 2) resumen_accesos
# ---------------------------------------------------------------------------
def test_resumen_accesos_cuenta_sesiones_eventos_y_tiempo(db):
    primera = abrir_sesion(ID_ESTUDIANTE, "10.0.0.5", "Navegador de prueba", db_path=db)
    registrar_evento(ID_ESTUDIANTE, "LOGIN", modulo="AUTH", sesion_id=primera, db_path=db)
    registrar_evento(ID_ESTUDIANTE, "CONSULTA_DIARIO", modulo="DIARIO", sesion_id=primera, db_path=db)
    _retroceder_inicio(db, primera, 3600)
    cerrada = cerrar_sesion(primera, db_path=db)
    assert cerrada["duracion_seg"] >= 3595

    segunda = abrir_sesion(ID_ESTUDIANTE, "10.0.0.9", "Navegador de prueba", db_path=db)
    registrar_evento(ID_ESTUDIANTE, "CREAR_ASIENTO", modulo="DIARIO", registro_id=99,
                     sesion_id=segunda, db_path=db)

    filas = resumen_accesos({"estudiante_id": ID_ESTUDIANTE}, db_path=db)
    assert len(filas) == 1
    fila = filas[0]

    assert fila["estudiante_id"] == ID_ESTUDIANTE
    assert fila["num_sesiones"] == 2
    assert fila["num_eventos"] == 3
    assert fila["ha_ingresado"] is True
    assert fila["estado_cuenta"] == "Activo"
    assert fila["primer_acceso"] and fila["ultimo_acceso"]
    assert fila["tiempo_actividad_segundos"] >= 3595
    assert fila["tiempo_actividad"].startswith("1 h")
    assert fila["ultima_accion"] == "CREAR_ASIENTO"
    assert fila["evidencias_generadas"] == 0
    assert fila["actividades_iniciadas"] == 0


def test_resumen_accesos_cuenta_actividades_y_evidencias(db):
    conn = _conexion(db)
    try:
        conn.execute("""
            INSERT INTO actividades (codigo, titulo, unidad, componente, puntaje, estado)
            VALUES ('U1-A1', 'Registro de operaciones básicas', 1, 'PRACTICA', 10, 'ABIERTA')
        """)
        actividad_id = conn.execute(
            "SELECT id FROM actividades WHERE codigo = 'U1-A1'").fetchone()["id"]
        conn.execute("""
            INSERT INTO asignaciones_actividad (actividad_id, estudiante_id, estado, intentos_usados)
            VALUES (?, ?, 'ENTREGADA', 1)
        """, (actividad_id, ID_ESTUDIANTE))
        conn.execute("""
            INSERT INTO evidencias (codigo, actividad_id, estudiante_id, titulo, tipo, estado)
            VALUES ('CONT1-B-2026-TEST0001', ?, ?, 'Evidencia de prueba', 'DIARIO', 'FINAL')
        """, (actividad_id, ID_ESTUDIANTE))
        conn.commit()
    finally:
        conn.close()

    sesion = abrir_sesion(ID_ESTUDIANTE, "10.0.0.1", "test", db_path=db)
    registrar_evento(ID_ESTUDIANTE, "INICIO_ACTIVIDAD", modulo="ACTIVIDADES",
                     actividad_id=actividad_id, sesion_id=sesion, db_path=db)
    registrar_evento(ID_ESTUDIANTE, "CREACION_EVIDENCIA", modulo="ACTIVIDADES",
                     actividad_id=actividad_id, sesion_id=sesion, db_path=db)

    fila = resumen_accesos({"estudiante_id": ID_ESTUDIANTE}, db_path=db)[0]
    assert fila["actividades_iniciadas"] == 1
    assert fila["actividades_asignadas"] == 1
    assert fila["actividades_completadas"] == 1
    assert fila["evidencias_generadas"] == 1
    assert fila["ultima_accion"] == "CREACION_EVIDENCIA"

    # El filtro por actividad solo devuelve a quien participó en ella.
    assert len(resumen_accesos({"actividad_id": actividad_id}, db_path=db)) == 1
    assert len(resumen_accesos({"actividad_id": 9999}, db_path=db)) == 0


def test_resumen_accesos_filtros_de_estado_fecha_y_paralelo(db):
    abrir_sesion(ID_ESTUDIANTE, "10.0.0.1", "test", db_path=db)
    conn = _conexion(db)
    try:
        conn.execute("UPDATE usuarios SET paralelo = 'B' WHERE id = ?", (ID_ESTUDIANTE,))
        conn.commit()
    finally:
        conn.close()

    assert len(resumen_accesos({"estado": "CON_INGRESO"}, db_path=db)) == 1
    assert len(resumen_accesos({"estado": "SIN_INGRESO"}, db_path=db)) == 0
    assert len(resumen_accesos({"paralelo": "B"}, db_path=db)) == 1
    assert len(resumen_accesos({"paralelo": "Z"}, db_path=db)) == 0
    assert len(resumen_accesos({"buscar": "morales"}, db_path=db)) == 1
    assert len(resumen_accesos({"desde": "2000-01-01", "hasta": "2099-12-31"}, db_path=db)) == 1
    assert len(resumen_accesos({"desde": "2099-01-01"}, db_path=db)) == 0


def test_linea_tiempo_en_orden_cronologico_descendente(db):
    sesion = abrir_sesion(ID_ESTUDIANTE, "10.0.0.1", "test", db_path=db)
    registrar_evento(ID_ESTUDIANTE, "LOGIN", modulo="AUTH", sesion_id=sesion, db_path=db)
    registrar_evento(ID_ESTUDIANTE, "CONSULTA_MAYOR", modulo="MAYOR", sesion_id=sesion, db_path=db)
    registrar_evento(ID_ESTUDIANTE, "GENERACION_BALANCE", modulo="BALANCE", sesion_id=sesion, db_path=db)

    eventos = linea_tiempo(ID_ESTUDIANTE, db_path=db)
    assert [e["evento"] for e in eventos] == ["GENERACION_BALANCE", "CONSULTA_MAYOR", "LOGIN"]
    for evento in eventos:
        assert evento["fecha"] and evento["hora"]
        assert evento["sesion_id"] == sesion
    assert len(linea_tiempo(ID_ESTUDIANTE, limite=1, db_path=db)) == 1


def test_registrar_evento_ignora_etiquetas_no_permitidas(db):
    assert registrar_evento(ID_ESTUDIANTE, "EVENTO_INVENTADO", db_path=db) is None
    assert registrar_evento(ID_ESTUDIANTE, "", db_path=db) is None
    assert _eventos(db) == []


def test_listado_de_estudiantes_y_sin_ingresar(db):
    listado = listado_docente_estudiantes(db_path=db)
    assert listado, "la base demostrativa debe tener estudiantes"
    assert all(e["ha_ingresado"] is False for e in listado)
    assert len(listado_estudiantes_sin_ingreso(db_path=db)) == len(listado)

    abrir_sesion(ID_ESTUDIANTE, "10.0.0.1", "test", db_path=db)
    listado = listado_docente_estudiantes(db_path=db)
    ingresaron = [e for e in listado if e["ha_ingresado"]]
    assert len(ingresaron) == 1
    assert ingresaron[0]["estudiante_id"] == ID_ESTUDIANTE
    assert len(listado_estudiantes_sin_ingreso(db_path=db)) == len(listado) - 1


# ---------------------------------------------------------------------------
# 3) Exportación CSV
# ---------------------------------------------------------------------------
def test_exportar_csv_contiene_el_resumen(db):
    sesion = abrir_sesion(ID_ESTUDIANTE, "10.0.0.1", "test", db_path=db)
    registrar_evento(ID_ESTUDIANTE, "LOGIN", modulo="AUTH", sesion_id=sesion, db_path=db)
    cerrar_sesion(sesion, db_path=db)

    contenido = exportar_csv(db_path=db)
    lineas = [l for l in contenido.replace("\ufeff", "").split("\r\n") if l.strip()]
    assert lineas[0].startswith("Estudiante;Usuario;Correo")
    assert len(lineas) == 2, "una cabecera más una fila por estudiante"
    assert "Ana Lucía Morales" in lineas[1]

    columnas = lineas[1].split(";")
    assert columnas[1] == "estudiante"
    assert columnas[5] == "Activo"
    assert columnas[8] == "1", "la columna Sesiones debe reflejar la sesión cerrada"
    assert columnas[10] == "0" and columnas[13] == "0"
    assert columnas[14] == "LOGIN", "la última acción registrada fue el inicio de sesión"


def test_endpoint_exportar_devuelve_text_csv(cliente_docente):
    respuesta = cliente_docente.get("/docente/accesos/exportar.csv")
    assert respuesta.status_code == 200
    assert respuesta.headers["Content-Type"].startswith("text/csv")
    assert "attachment" in respuesta.headers["Content-Disposition"]
    cuerpo = respuesta.get_data(as_text=True)
    assert "Estudiante;Usuario;Correo" in cuerpo
    assert "Ana Lucía Morales" in cuerpo


# ---------------------------------------------------------------------------
# 4) Control de acceso por rol
# ---------------------------------------------------------------------------
def test_estudiante_no_puede_entrar_al_panel_docente(cliente_estudiante):
    assert cliente_estudiante.get("/docente/accesos").status_code == 403
    assert cliente_estudiante.get("/docente/estudiantes").status_code == 403
    assert cliente_estudiante.get("/docente/sin-ingresar").status_code == 403
    assert cliente_estudiante.get("/docente/estudiantes/3").status_code == 403
    assert cliente_estudiante.get("/docente/estudiantes/3/linea-tiempo").status_code == 403
    assert cliente_estudiante.get("/docente/accesos/exportar.csv").status_code == 403


def test_anonimo_va_al_login(cliente_estudiante, app_docente):
    anonimo = app_docente.test_client()
    respuesta = anonimo.get("/docente/accesos")
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_docente_puede_ver_el_panel_y_los_filtros(cliente_docente):
    respuesta = cliente_docente.get("/docente/accesos?estado=CON_INGRESO&paralelo=B")
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "Panel de Accesos de Estudiantes" in cuerpo
    assert "Resumen de accesos por estudiante" in cuerpo
    assert "Nunca ingresó" in cuerpo or "Ana Lucía Morales" in cuerpo

    for ruta in ["/docente/estudiantes", "/docente/sin-ingresar", "/docente/estudiantes/3",
                 "/docente/estudiantes/3/linea-tiempo"]:
        assert cliente_docente.get(ruta).status_code == 200, ruta


def test_ficha_de_un_usuario_que_no_es_estudiante_devuelve_404(cliente_docente):
    # 1 = admin, 2 = docente: no son estudiantes
    assert cliente_docente.get("/docente/estudiantes/1").status_code == 404
    assert cliente_docente.get("/docente/estudiantes/9999").status_code == 404


def test_ficha_del_estudiante_reune_todos_los_apartados(db):
    sesion = abrir_sesion(ID_ESTUDIANTE, "10.0.0.1", "test", db_path=db)
    registrar_evento(ID_ESTUDIANTE, "LOGIN", modulo="AUTH", sesion_id=sesion, db_path=db)
    cerrar_sesion(sesion, db_path=db)

    ficha = ficha_estudiante(ID_ESTUDIANTE, db_path=db)
    assert ficha["datos"]["rol_nombre"] == "Estudiante"
    assert len(ficha["sesiones"]) == 1
    assert ficha["sesiones"][0]["estado"] == "Cerrada"
    assert len(ficha["linea_tiempo"]) == 1
    assert ficha["indicadores"]["num_sesiones"] == 1
    assert ficha["actividades"] == []
    assert ficha["evidencias"] == []
    assert ficha["intentos"] == []
    assert ficha_estudiante(9999, db_path=db) is None


# ---------------------------------------------------------------------------
# 5) Respuestas JSON
# ---------------------------------------------------------------------------
def test_panel_renderiza_con_datos_completos(app_docente, db):
    """El panel y la ficha renderizan correctamente con datos reales en todos los bloques."""
    conn = _conexion(db)
    try:
        conn.execute("UPDATE usuarios SET paralelo = 'A', matricula = 'UTM-2026-001' WHERE id = ?",
                     (ID_ESTUDIANTE,))
        conn.execute("""
            INSERT INTO actividades (codigo, titulo, unidad, componente, puntaje, estado, tipo_evidencia)
            VALUES ('U2-A3', 'Libro diario y mayor', 2, 'PRACTICA', 10, 'ABIERTA', 'DIARIO')
        """)
        actividad_id = conn.execute("SELECT id FROM actividades").fetchone()["id"]
        conn.execute("""
            INSERT INTO asignaciones_actividad (actividad_id, estudiante_id, estado, intentos_usados, nota)
            VALUES (?, ?, 'REVISADA', 2, 9.5)
        """, (actividad_id, ID_ESTUDIANTE))
        conn.execute("""
            INSERT INTO evidencias (codigo, actividad_id, estudiante_id, titulo, tipo, estado, modificada_despues)
            VALUES ('CONT1-B-2026-ABCD1234', ?, ?, 'Diario completo de abril', 'DIARIO', 'FINAL', 0)
        """, (actividad_id, ID_ESTUDIANTE))
        conn.commit()
    finally:
        conn.close()

    sesion = abrir_sesion(ID_ESTUDIANTE, "10.0.0.7", "Navegador", db_path=db)
    registrar_evento(ID_ESTUDIANTE, "LOGIN", modulo="AUTH", sesion_id=sesion, db_path=db)
    registrar_evento(ID_ESTUDIANTE, "INICIO_ACTIVIDAD", modulo="ACTIVIDADES",
                     actividad_id=actividad_id, sesion_id=sesion, db_path=db)
    registrar_evento(ID_ESTUDIANTE, "CREACION_EVIDENCIA", modulo="ACTIVIDADES",
                     actividad_id=actividad_id, sesion_id=sesion, db_path=db)
    cerrar_sesion(sesion, db_path=db)

    cliente = app_docente.test_client()
    _login(cliente, CREDENCIALES_DOCENTE)

    panel = cliente.get("/docente/accesos")
    assert panel.status_code == 200
    cuerpo = panel.get_data(as_text=True)
    for marcador in ["Panel de Accesos de Estudiantes", "Ana Lucía Morales",
                     "CREACION_EVIDENCIA", "U2-A3", "Tiempo de actividad"]:
        assert marcador in cuerpo, marcador
    # La fila del estudiante muestra su paralelo y sus evidencias
    assert ">A</span>" in cuerpo
    assert "Nunca ingresó" not in cuerpo.split("Resumen de accesos")[1]

    listado = cliente.get("/docente/estudiantes").get_data(as_text=True)
    assert "UTM-2026-001" in listado

    ficha = cliente.get("/docente/estudiantes/3").get_data(as_text=True)
    for marcador in ["Historial de accesos", "Línea de tiempo", "CONT1-B-2026-ABCD1234",
                     "Libro diario y mayor", "Revisada", "10.0.0.7"]:
        assert marcador in ficha, marcador

    # Con filtros combinados el panel sigue respondiendo y exportando.
    filtrado = cliente.get("/docente/accesos?paralelo=A&estado=CON_INGRESO&desde=2000-01-01")
    assert filtrado.status_code == 200
    csv = cliente.get("/docente/accesos/exportar.csv?paralelo=A&estado=CON_INGRESO")
    assert csv.status_code == 200
    assert "U2-A3" not in csv.get_data(as_text=True)  # el CSV es del resumen, no de actividades
    assert "Ana Lucía Morales" in csv.get_data(as_text=True)

    vacio = cliente.get("/docente/accesos?paralelo=Z")
    assert vacio.status_code == 200
    assert "No hay estudiantes que coincidan" in vacio.get_data(as_text=True)


def test_endpoints_en_formato_json(cliente_docente):
    datos = cliente_docente.get("/docente/accesos?formato=json").get_json()
    assert datos["ok"] is True
    assert datos["total"] == len(datos["estudiantes"]) >= 1
    assert "num_sesiones" in datos["estudiantes"][0]

    lista = cliente_docente.get("/docente/estudiantes?formato=json").get_json()
    assert lista["ok"] is True and lista["total"] >= 1

    sin_ingreso = cliente_docente.get("/docente/sin-ingresar?formato=json").get_json()
    assert sin_ingreso["ok"] is True

    ficha = cliente_docente.get("/docente/estudiantes/3?formato=json").get_json()
    assert ficha["ok"] is True and ficha["ficha"]["datos"]["estudiante_id"] == 3

    tiempo = cliente_docente.get("/docente/estudiantes/3/linea-tiempo?formato=json").get_json()
    assert tiempo["ok"] is True and tiempo["estudiante_id"] == 3


# ---------------------------------------------------------------------------
# 6) Hook after_request: eventos deducidos del endpoint
# ---------------------------------------------------------------------------
def test_after_request_registra_eventos_de_consulta(app_docente_hook, db):
    cliente = app_docente_hook.test_client()
    _login(cliente)

    assert cliente.get("/contabilidad/diario").status_code == 200
    assert cliente.get("/contabilidad/mayor").status_code == 200
    assert cliente.get("/contabilidad/balance").status_code == 200
    assert cliente.get("/contabilidad/diario").status_code == 200  # repetida: no duplica
    assert cliente.get("/dashboard").status_code == 200            # no relevante

    eventos = _eventos(db)
    tipos = [e["evento"] for e in eventos]
    assert "CONSULTA_DIARIO" in tipos
    assert "CONSULTA_MAYOR" in tipos
    assert "GENERACION_BALANCE" in tipos
    assert tipos.count("CONSULTA_DIARIO") == 1, "las consultas GET no deben duplicarse en la sesión"
    assert len(tipos) == len(set(tipos)), "sin duplicados por endpoint visitado"

    modulos = {e["evento"]: e["modulo"] for e in eventos}
    assert modulos["CONSULTA_DIARIO"] == "DIARIO"
    assert modulos["CONSULTA_MAYOR"] == "MAYOR"
    assert modulos["GENERACION_BALANCE"] == "BALANCE"
    assert all(e["sesion_id"] for e in eventos)


def test_after_request_nunca_rompe_la_respuesta(app_docente_hook):
    """El hook devuelve la respuesta intacta incluso para rutas no registradas."""
    cliente = app_docente_hook.test_client()
    respuesta = cliente.get("/ruta-que-no-existe")
    assert respuesta.status_code == 404


def test_hook_no_traza_a_docentes_y_evita_duplicar_actividades(app_docente_hook, db):
    # La navegación de un docente no contamina la traza de los estudiantes
    docente = app_docente_hook.test_client()
    _login(docente, CREDENCIALES_DOCENTE)
    assert docente.get("/contabilidad/diario").status_code == 200
    assert [e["evento"] for e in _eventos(db, usuario_id=2)] == ["LOGIN"]

    # El mapeo no duplica lo que ya registra services/activity_service.py
    from services.access_service import _mapear_evento
    assert _mapear_evento("activities.iniciar_actividad", "POST") == (None, None)
    assert _mapear_evento("activities.detalle_actividad", "GET") == ("CONSULTA_ACTIVIDAD", "ACTIVIDADES")
    assert _mapear_evento("evidence.nueva_evidencia", "POST") == ("CREACION_EVIDENCIA", "EVIDENCIAS")
    assert _mapear_evento("evidence.detalle_evidencia", "GET") == ("CONSULTA_ACTIVIDAD", "EVIDENCIAS")
    assert _mapear_evento("dashboard.index", "GET") == (None, None)
    assert _mapear_evento(None, "GET") == (None, None)


def test_servicio_expone_la_misma_api_en_la_fachada(db):
    sesion = AccessService.abrir_sesion(ID_ESTUDIANTE, "10.0.0.1", "test", db_path=db)
    assert AccessService.registrar_evento(ID_ESTUDIANTE, "LOGIN", sesion_id=sesion, db_path=db)
    assert AccessService.cerrar_sesion(sesion, db_path=db)["activa"] == 0
    assert AccessService.resumen_accesos(db_path=db)[0]["num_sesiones"] == 1
    assert AccessService.formatear_duracion(5400) == "1 h 30 min"
