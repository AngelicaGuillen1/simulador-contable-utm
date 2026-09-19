# -*- coding: utf-8 -*-
"""Pruebas del módulo de ACTIVIDADES del syllabus y del módulo de EVIDENCIAS verificables.

Cubre los requisitos de verificación del proyecto:
    1. El código de evidencia tiene el formato CONT1-<PARALELO>-2026-XXXXXXXX y es único.
    2. Finalizar deja la huella SHA-256 y `detectar_modificacion` detecta un cambio posterior.
    3. Un estudiante no puede ver ni modificar la evidencia de otro (acceso cruzado -> 403/404).
    4. Asignar la misma actividad dos veces no duplica filas en asignaciones_actividad.
    5. Iniciar una actividad cerrada por fecha se rechaza.

Se usan las fixtures de tests/conftest.py (base de datos demostrativa copiada por prueba).
Las rutas nuevas se registran sobre la aplicación en la propia prueba si el proyecto todavía no
las registra en routes/__init__.py, de modo que estas pruebas no dependen de ese archivo.
"""

import hashlib
import json
import re
from datetime import datetime, timedelta

import pytest

from models import get_db_connection
from services.activity_service import (
    ActivityService, ActividadNoAsignada, ActividadNoDisponible, ErrorActividad,
)
from services.evidence_service import (
    EvidenceService, EvidenciaAjena, EvidenciaNoEncontrada,
)

PATRON_CODIGO = re.compile(r"^CONT1-([A-Z0-9]{1,3})-(2026)-([0-9A-F]{8})$")


# --------------------------------------------------------------------------- Fixtures
@pytest.fixture()
def app_edu(db):
    """Aplicación Flask con los blueprints de actividades y evidencias registrados."""
    import app as app_module
    from routes.activities import activities_bp
    from routes.evidence import evidence_bp

    aplicacion = app_module.create_app()
    aplicacion.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    for blueprint in (activities_bp, evidence_bp):
        if blueprint.name not in aplicacion.blueprints:
            aplicacion.register_blueprint(blueprint)
    return aplicacion


def _autenticar(aplicacion, usuario, clave):
    cliente = aplicacion.test_client()
    respuesta = cliente.post("/login", data={"username": usuario, "password": clave},
                             follow_redirects=True)
    assert respuesta.status_code == 200
    return cliente


@pytest.fixture()
def cliente_estudiante(app_edu):
    return _autenticar(app_edu, "estudiante", "estudiante123")


@pytest.fixture()
def cliente_docente(app_edu):
    return _autenticar(app_edu, "docente", "docente123")


@pytest.fixture()
def estudiante_id(db):
    conn = get_db_connection(db)
    try:
        fila = conn.execute("SELECT id FROM usuarios WHERE username = 'estudiante'").fetchone()
    finally:
        conn.close()
    assert fila is not None, "La base de pruebas debe tener el usuario 'estudiante'"
    return fila["id"]


@pytest.fixture()
def otro_estudiante_id(db):
    """Segundo estudiante (paralelo B) para las pruebas de aislamiento."""
    conn = get_db_connection(db)
    try:
        cursor = conn.execute("""
            INSERT INTO usuarios (username, password_hash, nombre_completo, email, rol_id, activo, paralelo)
            VALUES ('estudiante_b', 'no-usado-en-pruebas', 'Beatriz Ortiz - Estudiante',
                    'bortiz@estudiantes.edu.ec', 3, 1, 'B')
        """)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _crear_actividad(db, codigo="U1-T1", estado="ABIERTA", dias_apertura=-3, dias_cierre=7,
                     tipo_evidencia="INTEGRAL", unidad=1, puntaje=10, estudiante_ids=None):
    """Crea una actividad con una ventana de fechas relativa al momento de la prueba."""
    ahora = datetime.now()
    datos = {
        "codigo": codigo,
        "titulo": "Actividad de prueba %s" % codigo,
        "unidad": unidad,
        "componente": "DOCENCIA",
        "puntaje": puntaje,
        "tipo_evidencia": tipo_evidencia,
        "estado": estado,
        "intentos_maximos": 1,
        "creada_por": 2,
    }
    if dias_apertura is not None:
        datos["fecha_apertura"] = (ahora + timedelta(days=dias_apertura)).strftime("%Y-%m-%d %H:%M")
    if dias_cierre is not None:
        datos["fecha_cierre"] = (ahora + timedelta(days=dias_cierre)).strftime("%Y-%m-%d %H:%M")

    actividad = ActivityService.crear_actividad(datos, db_path=db)
    if estudiante_ids:
        ActivityService.asignar_a_estudiantes(actividad["id"], estudiante_ids, db_path=db)
    return actividad


def _contar_asignaciones(db, actividad_id, estudiante_id):
    conn = get_db_connection(db)
    try:
        return conn.execute("""
            SELECT COUNT(*) AS n FROM asignaciones_actividad
            WHERE actividad_id = ? AND estudiante_id = ?
        """, (actividad_id, estudiante_id)).fetchone()["n"]
    finally:
        conn.close()


def _eventos(db, estudiante_id, evento):
    conn = get_db_connection(db)
    try:
        return [dict(f) for f in conn.execute("""
            SELECT * FROM eventos_estudiante WHERE usuario_id = ? AND evento = ?
        """, (estudiante_id, evento)).fetchall()]
    finally:
        conn.close()


# =========================================================================== 1. Código
def test_codigo_de_evidencia_tiene_formato_exacto_y_es_unico(db, estudiante_id):
    # El generador respeta el paralelo solicitado y 8 hexadecimales en mayúsculas.
    for paralelo in ("A", "B", "C"):
        codigo = EvidenceService.generar_codigo(paralelo, db_path=db)
        coincidencia = PATRON_CODIGO.match(codigo)
        assert coincidencia, "Código con formato inválido: %s" % codigo
        assert coincidencia.group(1) == paralelo
        assert len(coincidencia.group(3)) == 8

    # Los códigos realmente emitidos al crear evidencias son únicos.
    codigos = []
    for indice in range(20):
        creada = EvidenceService.crear_evidencia(
            estudiante_id, None, "INTEGRAL", "Evidencia de prueba %d" % indice,
            contenido_dict={"indice": indice}, db_path=db)
        codigos.append(creada["codigo"])

    assert all(PATRON_CODIGO.match(c) for c in codigos), "Algún código no cumple el formato"
    assert len(set(codigos)) == len(codigos), "Se repitió un código de evidencia"

    conn = get_db_connection(db)
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM evidencias").fetchone()["n"]
        distintos = conn.execute("SELECT COUNT(DISTINCT codigo) AS n FROM evidencias").fetchone()["n"]
    finally:
        conn.close()
    assert total == distintos == 20


# =========================================================================== 2. Huella
def test_finalizar_guarda_huella_y_detectar_modificacion_detecta_cambios(db, estudiante_id):
    actividad = _crear_actividad(db, codigo="U1-H1", estudiante_ids=[estudiante_id])
    evidencia = EvidenceService.crear_evidencia(
        estudiante_id, actividad["id"], "INTEGRAL", "Evidencia integral de la actividad",
        db_path=db)

    assert evidencia["estado"] == "BORRADOR"
    assert evidencia["huella"] == hashlib.sha256(evidencia["contenido_json"].encode("utf-8")).hexdigest()
    assert EvidenceService.detectar_modificacion(evidencia["id"], db_path=db) is False

    finalizada = EvidenceService.finalizar_evidencia(evidencia["id"], db_path=db)
    assert finalizada["estado"] == "FINAL"
    assert finalizada["huella"] == hashlib.sha256(finalizada["contenido_json"].encode("utf-8")).hexdigest()
    assert len(finalizada["huella"]) == 64

    versiones = EvidenceService.versiones(evidencia["id"], db_path=db)
    assert [v["version"] for v in versiones] == [1]
    assert versiones[0]["huella"] == finalizada["huella"]
    assert EvidenceService.detectar_modificacion(evidencia["id"], db_path=db) is False

    # Alguien modifica el contenido guardado después de generar la evidencia.
    conn = get_db_connection(db)
    try:
        conn.execute("UPDATE evidencias SET contenido_json = ? WHERE id = ?",
                     (evidencia["contenido_json"].replace("{", "{ \"alterado\": true,", 1),
                      evidencia["id"]))
        conn.commit()
        assert conn.execute("SELECT modificada_despues FROM evidencias WHERE id = ?",
                            (evidencia["id"],)).fetchone()["modificada_despues"] == 0
    finally:
        conn.close()

    assert EvidenceService.detectar_modificacion(evidencia["id"], db_path=db) is True

    conn = get_db_connection(db)
    try:
        assert conn.execute("SELECT modificada_despues FROM evidencias WHERE id = ?",
                            (evidencia["id"],)).fetchone()["modificada_despues"] == 1
    finally:
        conn.close()

    # Y el docente lo ve al verificar el código: la evidencia deja de ser válida.
    verificacion = EvidenceService.verificar_codigo(evidencia["codigo"], db_path=db)
    assert verificacion["modificada_despues"] is True
    assert verificacion["valida"] is False
    assert verificacion["estado"] == "FINAL"

    # Una nueva versión vuelve a dejar la evidencia verificable.
    nueva = EvidenceService.nueva_version(evidencia["id"], "Corrección del trabajo contable",
                                          db_path=db)
    assert nueva["version"] == 2
    assert len(EvidenceService.versiones(evidencia["id"], db_path=db)) == 2
    assert EvidenceService.detectar_modificacion(evidencia["id"], db_path=db) is False
    assert EvidenceService.verificar_codigo(evidencia["codigo"], db_path=db)["valida"] is True


def test_exportar_pdf_no_rompe_la_aplicacion(db, estudiante_id, tmp_path):
    """reportlab es opcional: si está, genera el PDF; si no, devuelve None (vista HTML)."""
    evidencia = EvidenceService.crear_evidencia(estudiante_id, None, "PLAN_CUENTAS",
                                                "Plan de cuentas", db_path=db)
    ruta = str(tmp_path / "evidencia.pdf")
    resultado = EvidenceService.exportar_pdf(evidencia["id"], ruta, db_path=db)

    try:
        import reportlab  # noqa: F401
        tiene_reportlab = True
    except ImportError:
        tiene_reportlab = False

    if tiene_reportlab:
        assert resultado == ruta
        with open(ruta, "rb") as archivo:
            assert archivo.read(4) == b"%PDF"
    else:
        assert resultado is None


# =========================================================================== 3. Aislamiento
def test_estudiante_no_puede_acceder_a_la_evidencia_de_otro(db, estudiante_id,
                                                            otro_estudiante_id,
                                                            cliente_estudiante):
    actividad = _crear_actividad(db, codigo="U2-X1",
                                 estudiante_ids=[estudiante_id, otro_estudiante_id])
    ajena = EvidenceService.crear_evidencia(otro_estudiante_id, actividad["id"], "PLAN_CUENTAS",
                                            "Evidencia del otro estudiante", db_path=db)
    EvidenceService.finalizar_evidencia(ajena["id"], db_path=db)

    propia = EvidenceService.crear_evidencia(estudiante_id, actividad["id"], "PLAN_CUENTAS",
                                             "Evidencia propia", db_path=db)

    # Servicio: el candado de aislamiento lanza EvidenciaAjena.
    with pytest.raises(EvidenciaAjena):
        EvidenceService.obtener_evidencia_de_estudiante(ajena["id"], estudiante_id, db_path=db)
    with pytest.raises(EvidenciaNoEncontrada):
        EvidenceService.obtener_evidencia_de_estudiante(999999, estudiante_id, db_path=db)
    assert EvidenceService.obtener_evidencia_de_estudiante(propia["id"], estudiante_id,
                                                           db_path=db)["id"] == propia["id"]

    # Rutas: lectura de la evidencia ajena -> 404 (no se revela su existencia).
    assert cliente_estudiante.get("/mis-evidencias/%d" % ajena["id"]).status_code == 404
    assert cliente_estudiante.get("/mis-evidencias/%d/captura" % ajena["id"]).status_code == 404
    assert cliente_estudiante.get("/mis-evidencias/%d/imprimible" % ajena["id"]).status_code == 404

    # Escritura sobre la evidencia ajena -> 403/404.
    respuesta = cliente_estudiante.post("/mis-evidencias/%d/finalizar" % ajena["id"])
    assert respuesta.status_code in (403, 404)

    # La evidencia ajena no aparece en el listado propio y sigue sin modificarse.
    listado = cliente_estudiante.get("/mis-evidencias?formato=json").get_json()
    codigos = [e["codigo"] for e in listado["evidencias"]]
    assert propia["codigo"] in codigos
    assert ajena["codigo"] not in codigos

    conn = get_db_connection(db)
    try:
        estado = conn.execute("SELECT estado FROM evidencias WHERE id = ?",
                              (ajena["id"],)).fetchone()["estado"]
    finally:
        conn.close()
    assert estado == "FINAL"

    # Tampoco puede iniciar una actividad que no le fue asignada.
    otra_actividad = _crear_actividad(db, codigo="U2-X2", estudiante_ids=[otro_estudiante_id])
    with pytest.raises(ActividadNoAsignada):
        ActivityService.iniciar_actividad(otra_actividad["id"], estudiante_id, db_path=db)
    assert cliente_estudiante.post(
        "/mis-actividades/%d/iniciar?formato=json" % otra_actividad["id"]).status_code == 404


# =========================================================================== 4. Idempotencia
def test_asignar_la_misma_actividad_dos_veces_no_duplica_filas(db, estudiante_id,
                                                              cliente_docente):
    actividad = _crear_actividad(db, codigo="U3-I1")

    primera = ActivityService.asignar_a_estudiantes(actividad["id"], [estudiante_id], db_path=db)
    segunda = ActivityService.asignar_a_estudiantes(actividad["id"], [estudiante_id], db_path=db)
    tercera = ActivityService.asignar_a_todos_los_estudiantes(actividad["id"], db_path=db)

    assert primera["asignadas"] == 1 and primera["ya_existentes"] == 0
    assert segunda["asignadas"] == 0 and segunda["ya_existentes"] == 1
    assert tercera["asignadas"] == 0
    assert _contar_asignaciones(db, actividad["id"], estudiante_id) == 1

    # Lo mismo a través de la ruta del docente (dos POST seguidos).
    for _ in range(2):
        respuesta = cliente_docente.post("/docente/actividades/%d/asignar" % actividad["id"],
                                         data={"estudiante_id": str(estudiante_id)},
                                         follow_redirects=True)
        assert respuesta.status_code == 200
    assert _contar_asignaciones(db, actividad["id"], estudiante_id) == 1

    # Y con la asignación masiva (checkbox "todos").
    cliente_docente.post("/docente/actividades/%d/asignar" % actividad["id"],
                         data={"todos": "1"}, follow_redirects=True)
    assert _contar_asignaciones(db, actividad["id"], estudiante_id) == 1

    # Crear de nuevo la actividad (mismo código) tampoco la duplica: es un upsert.
    repetida = ActivityService.crear_actividad({"codigo": "U3-I1", "titulo": "Otro título",
                                                "unidad": 3, "componente": "PRACTICA",
                                                "puntaje": 12, "estado": "ABIERTA"}, db_path=db)
    assert repetida["id"] == actividad["id"]
    conn = get_db_connection(db)
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM actividades WHERE codigo = 'U3-I1'").fetchone()["n"]
    finally:
        conn.close()
    assert total == 1
    assert _contar_asignaciones(db, actividad["id"], estudiante_id) == 1


# =========================================================================== 5. Fechas
def test_iniciar_actividad_cerrada_por_fecha_se_rechaza(db, estudiante_id, cliente_estudiante):
    cerrada = _crear_actividad(db, codigo="U4-C1", estado="ABIERTA",
                               dias_apertura=-20, dias_cierre=-5,
                               estudiante_ids=[estudiante_id])

    with pytest.raises(ActividadNoDisponible):
        ActivityService.iniciar_actividad(cerrada["id"], estudiante_id, db_path=db)

    # La asignación no se movió y no se consumió ningún intento ni se registró el evento.
    asignacion = ActivityService.obtener_asignacion(cerrada["id"], estudiante_id, db_path=db)
    assert asignacion["estado_asignacion"] == "PENDIENTE"
    assert asignacion["intentos_usados"] == 0
    assert asignacion["abierta_ahora"] is False
    assert "cerró" in asignacion["motivo_disponibilidad"]
    assert _eventos(db, estudiante_id, "INICIO_ACTIVIDAD") == []

    # Por la ruta del estudiante también se rechaza (JSON y HTML).
    respuesta = cliente_estudiante.post("/mis-actividades/%d/iniciar?formato=json" % cerrada["id"])
    assert respuesta.status_code in (400, 409)
    assert respuesta.get_json()["success"] is False

    html = cliente_estudiante.post("/mis-actividades/%d/iniciar" % cerrada["id"],
                                   follow_redirects=True)
    assert html.status_code == 200
    assert "cerró" in html.get_data(as_text=True)

    # Una actividad aún no publicada tampoco se puede iniciar.
    borrador = _crear_actividad(db, codigo="U4-C2", estado="BORRADOR",
                                dias_apertura=-1, dias_cierre=10, estudiante_ids=[estudiante_id])
    with pytest.raises(ErrorActividad):
        ActivityService.iniciar_actividad(borrador["id"], estudiante_id, db_path=db)


def test_iniciar_actividad_abierta_registra_evento_y_consume_un_solo_intento(
        db, estudiante_id, cliente_estudiante):
    abierta = _crear_actividad(db, codigo="U1-A1", estado="ABIERTA",
                               dias_apertura=-2, dias_cierre=5,
                               estudiante_ids=[estudiante_id])

    respuesta = cliente_estudiante.post("/mis-actividades/%d/iniciar?formato=json" % abierta["id"])
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["success"] is True
    assert cuerpo["asignacion"]["estado"] == "EN_CURSO"
    assert cuerpo["asignacion"]["intentos_usados"] == 1
    assert cuerpo["asignacion"]["abierta_en"] is not None

    eventos = _eventos(db, estudiante_id, "INICIO_ACTIVIDAD")
    assert len(eventos) == 1
    assert eventos[0]["actividad_id"] == abierta["id"]
    assert eventos[0]["modulo"] == "ACTIVIDADES"

    # Retomar la actividad en curso no consume otro intento.
    segunda = cliente_estudiante.post("/mis-actividades/%d/iniciar?formato=json" % abierta["id"])
    assert segunda.get_json()["asignacion"]["intentos_usados"] == 1

    # Al cerrarla queda ENTREGADA con su fecha de cierre.
    entregada = ActivityService.cerrar_actividad(abierta["id"], estudiante_id, db_path=db)
    assert entregada["estado"] == "ENTREGADA"
    assert entregada["cerrada_en"] is not None
    with pytest.raises(ErrorActividad):
        ActivityService.iniciar_actividad(abierta["id"], estudiante_id, db_path=db)

    # El listado del estudiante refleja estado, fechas, puntaje y disponibilidad.
    listado = ActivityService.listar_actividades_estudiante(estudiante_id, db_path=db)
    fila = [a for a in listado if a["id"] == abierta["id"]][0]
    assert fila["abierta_ahora"] is True
    assert fila["puntaje"] == 10
    assert fila["apertura_legible"] and fila["cierre_legible"]

    # El docente ve el conteo de asignadas/entregadas de la actividad.
    resumen = [a for a in ActivityService.listado_docente({}, db_path=db) if a["id"] == abierta["id"]][0]
    assert resumen["asignadas"] == 1
    assert resumen["entregadas"] == 1
    assert resumen["porcentaje_entrega"] == 100.0


# =========================================================================== 6. Resumen
def test_resumen_de_la_evidencia_usa_los_datos_reales_y_avisa_cuando_esta_vacio(
        db, estudiante_id):
    actividad = _crear_actividad(db, codigo="U1-R1", estudiante_ids=[estudiante_id])
    evidencia = EvidenceService.crear_evidencia(estudiante_id, actividad["id"], "INTEGRAL",
                                                "Evidencia integral", db_path=db)
    resumen = EvidenceService.resumen_evidencia(evidencia["id"], db_path=db)

    assert resumen["vacio"] is False
    titulos = " ".join(s["titulo"] for s in resumen["secciones"])
    for esperado in ("Plan de cuentas", "Libro Diario", "Libro Mayor", "Balance de comprobación"):
        assert esperado in titulos

    # Los importes provienen de las tablas contables reales (asiento de apertura incluido).
    balance = [s for s in resumen["secciones"] if "Balance" in s["titulo"]][0]
    totales = balance["filas"][-1]
    assert "TOTALES" in totales
    assert totales[2] == totales[3], "El balance de comprobación debe cuadrar sumas"
    assert totales[4] == totales[5], "El balance de comprobación debe cuadrar saldos"
    assert float(totales[2].replace(",", "")) > 0

    # Sin datos contables la evidencia se genera vacía y lo indica (no se inventan cifras).
    vacio = EvidenceService.resumen_desde_contenido({"tipo": "DIARIO", "datos": {}})
    assert vacio["vacio"] is True
    assert "no contiene datos contables" in vacio["texto"]
    assert "No se inventan cifras" in vacio["texto"]
    assert vacio["aviso"] and "datos contables" in vacio["aviso"]

    # Y con una empresa sin asientos (base recién instalada), el resumen también sale vacío.
    conn = get_db_connection(db)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM detalle_asientos")
        conn.execute("DELETE FROM asientos")
        conn.commit()
    finally:
        conn.close()
    sin_movimientos = EvidenceService.crear_evidencia(estudiante_id, None, "DIARIO",
                                                      "Diario sin movimientos", db_path=db)
    resumen_vacio = EvidenceService.resumen_evidencia(sin_movimientos["id"], db_path=db)
    assert resumen_vacio["vacio"] is True
    assert resumen_vacio["aviso"] and "datos contables" in resumen_vacio["aviso"]


# =========================================================================== 7. Verificación
def test_verificar_codigo_devuelve_estudiante_actividad_fecha_estado_y_resumen(
        db, estudiante_id):
    actividad = _crear_actividad(db, codigo="U3-V1", unidad=3, estudiante_ids=[estudiante_id])
    evidencia = EvidenceService.crear_evidencia(estudiante_id, actividad["id"], "BALANCE",
                                                "Balance de comprobación", db_path=db)
    EvidenceService.finalizar_evidencia(evidencia["id"], db_path=db)

    verificacion = EvidenceService.verificar_codigo(evidencia["codigo"].lower(), db_path=db)
    assert verificacion is not None
    assert verificacion["codigo"] == evidencia["codigo"]
    assert verificacion["estudiante"]["username"] == "estudiante"
    assert verificacion["actividad"]["codigo"] == "U3-V1"
    assert verificacion["estado"] == "FINAL"
    assert verificacion["modificada_despues"] is False
    assert verificacion["valida"] is True
    assert verificacion["fecha_generacion"]
    assert verificacion["total_versiones"] == 1
    assert "Balance de comprobación" in verificacion["resumen"]
    assert verificacion["huella"] == evidencia["huella"] or len(verificacion["huella"]) == 64

    assert EvidenceService.verificar_codigo("CONT1-Z-2026-00000000", db_path=db) is None
    assert EvidenceService.verificar_codigo("", db_path=db) is None


# =========================================================================== 8. Rutas
def test_rutas_de_actividades_y_evidencias_del_estudiante(db, estudiante_id, cliente_estudiante):
    actividad = _crear_actividad(db, codigo="U1-W1", estudiante_ids=[estudiante_id])

    assert cliente_estudiante.get("/mis-actividades").status_code == 200
    listado = cliente_estudiante.get("/mis-actividades?formato=json").get_json()
    assert listado["success"] is True
    assert any(a["codigo"] == "U1-W1" for a in listado["actividades"])

    # Con cabecera Accept también responde JSON.
    acepta_json = cliente_estudiante.get("/mis-actividades", headers={"Accept": "application/json"})
    assert acepta_json.is_json and acepta_json.get_json()["total"] >= 1

    assert cliente_estudiante.get("/mis-actividades/%d" % actividad["id"]).status_code == 200
    assert cliente_estudiante.get("/mis-evidencias").status_code == 200

    # Generar una evidencia por formulario y finalizarla.
    respuesta = cliente_estudiante.post("/mis-evidencias/nueva", data={
        "actividad_id": str(actividad["id"]), "tipo": "INTEGRAL",
        "titulo": "Evidencia desde la interfaz",
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    assert "Código verificable" in respuesta.get_data(as_text=True)

    conn = get_db_connection(db)
    try:
        fila = conn.execute("""SELECT id, codigo FROM evidencias WHERE estudiante_id = ?
                               ORDER BY id DESC LIMIT 1""", (estudiante_id,)).fetchone()
    finally:
        conn.close()
    assert fila is not None
    evidencia_id, codigo = fila["id"], fila["codigo"]

    detalle = cliente_estudiante.get("/mis-evidencias/%d" % evidencia_id)
    assert detalle.status_code == 200
    assert codigo in detalle.get_data(as_text=True)

    captura = cliente_estudiante.get("/mis-evidencias/%d/captura" % evidencia_id)
    assert captura.status_code == 200
    cuerpo = captura.get_data(as_text=True)
    assert codigo in cuerpo
    assert "Ana Lucía Morales" in cuerpo          # estudiante
    assert "U1-W1" in cuerpo                      # actividad
    assert "Vista limpia para capturar pantalla" in cuerpo
    assert "Estudiante" in cuerpo and "Fecha y hora" in cuerpo

    imprimible = cliente_estudiante.get("/mis-evidencias/%d/imprimible" % evidencia_id)
    assert imprimible.status_code == 200
    assert codigo in imprimible.get_data(as_text=True)

    finalizar = cliente_estudiante.post("/mis-evidencias/%d/finalizar" % evidencia_id,
                                        follow_redirects=True)
    assert finalizar.status_code == 200
    assert "finalizada" in finalizar.get_data(as_text=True).lower()

    json_evidencia = cliente_estudiante.get(
        "/mis-evidencias/%d?formato=json" % evidencia_id).get_json()
    assert json_evidencia["evidencia"]["estado"] == "FINAL"
    assert json_evidencia["resumen"]["codigo"] == codigo

    # Un visitante anónimo no entra a los módulos.
    anonimo = app_edu_cliente_anonimo(db)
    assert anonimo.get("/mis-actividades").status_code == 302
    assert anonimo.get("/mis-evidencias").status_code == 302


def app_edu_cliente_anonimo(db):
    """Cliente sin sesión sobre la aplicación de pruebas (sin registrar blueprints dos veces)."""
    import app as app_module
    from routes.activities import activities_bp
    from routes.evidence import evidence_bp

    aplicacion = app_module.create_app()
    aplicacion.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    for blueprint in (activities_bp, evidence_bp):
        if blueprint.name not in aplicacion.blueprints:
            aplicacion.register_blueprint(blueprint)
    return aplicacion.test_client()


def test_rutas_docentes_requieren_rol_y_muestran_las_evidencias(db, estudiante_id,
                                                               cliente_estudiante,
                                                               cliente_docente):
    actividad = _crear_actividad(db, codigo="U4-W1", unidad=4, puntaje=10,
                                 estudiante_ids=[estudiante_id])
    evidencia = EvidenceService.crear_evidencia(estudiante_id, actividad["id"], "BALANCE",
                                                "Balance de comprobación", db_path=db)
    EvidenceService.finalizar_evidencia(evidencia["id"], db_path=db)

    pagina = cliente_docente.get("/docente/actividades")
    assert pagina.status_code == 200
    assert "Gestión de actividades del syllabus" in pagina.get_data(as_text=True)

    detalle = cliente_docente.get("/docente/actividades/%d" % actividad["id"])
    assert detalle.status_code == 200
    assert "Asignaciones por estudiante" in detalle.get_data(as_text=True)

    listado_json = cliente_docente.get("/docente/actividades?formato=json").get_json()
    assert listado_json["success"] is True
    assert any(a["codigo"] == "U4-W1" and a["asignadas"] == 1 for a in listado_json["actividades"])

    evidencias = cliente_docente.get("/docente/evidencias")
    assert evidencias.status_code == 200
    assert evidencia["codigo"] in evidencias.get_data(as_text=True)

    verificar = cliente_docente.get("/docente/evidencias/verificar?codigo=%s" % evidencia["codigo"])
    assert verificar.status_code == 200
    cuerpo = verificar.get_data(as_text=True)
    assert "Evidencia válida" in cuerpo
    assert "Ana Lucía Morales" in cuerpo
    assert "U4-W1" in cuerpo

    json_verificacion = cliente_docente.get(
        "/docente/evidencias/verificar?codigo=%s&formato=json" % evidencia["codigo"]).get_json()
    assert json_verificacion["verificacion"]["valida"] is True

    faltante = cliente_docente.get("/docente/evidencias/verificar?codigo=CONT1-Z-2026-00000000")
    assert faltante.status_code == 200
    assert "No existe ninguna evidencia" in faltante.get_data(as_text=True)
    assert cliente_docente.get(
        "/docente/evidencias/verificar?codigo=NOEXISTE&formato=json").status_code == 404

    docente_detalle = cliente_docente.get("/docente/evidencias/%d" % evidencia["id"])
    assert docente_detalle.status_code == 200
    assert evidencia["codigo"] in docente_detalle.get_data(as_text=True)

    # El rol Estudiante no entra al módulo docente; el docente no entra a las vistas de estudiante.
    assert cliente_estudiante.get("/docente/actividades").status_code == 403
    assert cliente_estudiante.get("/docente/evidencias").status_code == 403
    assert cliente_estudiante.get("/docente/evidencias/verificar").status_code == 403
    assert cliente_docente.get("/mis-evidencias/%d" % evidencia["id"]).status_code in (403, 404)


def test_crear_actividad_y_evidencia_desde_las_rutas_docentes(db, estudiante_id, cliente_docente):
    respuesta = cliente_docente.post("/docente/actividades/nueva", data={
        "codigo": "U2-N1", "titulo": "Práctica creada por el docente", "unidad": "2",
        "componente": "PRACTICA", "puntaje": "12", "tipo_evidencia": "PLAN_CUENTAS",
        "estado": "ABIERTA", "fecha_apertura": "2026-01-01 00:00", "fecha_cierre": "2026-12-31 23:59",
        "instrucciones": "Clasifique treinta cuentas por grupo y naturaleza.",
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    assert "registrada correctamente" in respuesta.get_data(as_text=True)

    creada = [a for a in ActivityService.listado_docente({}, db_path=db) if a["codigo"] == "U2-N1"]
    assert len(creada) == 1
    assert creada[0]["puntaje"] == 12
    assert creada[0]["estado"] == "ABIERTA"

    # Cerramos la actividad y comprobamos que el estudiante ya no puede iniciarla.
    cliente_docente.post("/docente/actividades/%d/estado" % creada[0]["id"],
                         data={"estado": "CERRADA"}, follow_redirects=True)
    ActivityService.asignar_a_estudiantes(creada[0]["id"], [estudiante_id], db_path=db)
    with pytest.raises(ActividadNoDisponible):
        ActivityService.iniciar_actividad(creada[0]["id"], estudiante_id, db_path=db)

    # Una actividad ABIERTA sin fechas queda disponible de forma permanente (no hay plazo que violar).
    sin_fechas = ActivityService.crear_actividad({"codigo": "U2-N2", "titulo": "Sin fechas",
                                                  "unidad": 2, "componente": "AUTONOMO",
                                                  "estado": "ABIERTA"}, db_path=db)
    assert sin_fechas["fecha_apertura"] is None and sin_fechas["fecha_cierre"] is None
    ActivityService.asignar_a_estudiantes(sin_fechas["id"], [estudiante_id], db_path=db)
    iniciada = ActivityService.iniciar_actividad(sin_fechas["id"], estudiante_id, db_path=db)
    assert iniciada["estado"] == "EN_CURSO"

    # Una evidencia asociada a una actividad inexistente se rechaza (no se contamina el histórico).
    with pytest.raises(ErrorActividad):
        EvidenceService.crear_evidencia(estudiante_id, 999999, "INTEGRAL", "Actividad fantasma",
                                        db_path=db)


def test_evidencias_se_guardan_con_json_determinista_y_utf8(db, estudiante_id):
    contenido = {"tipo": "PLAN_CUENTAS", "cuenta": "Caja General · señal",
                 "datos": {"saldo": 1234.5}}
    evidencia = EvidenceService.crear_evidencia(estudiante_id, None, "PLAN_CUENTAS",
                                                "Evidencia con acentos",
                                                contenido_dict=contenido, db_path=db)
    guardado = json.loads(evidencia["contenido_json"])
    assert guardado["cuenta"] == "Caja General · señal"
    assert "señal" in evidencia["contenido_json"]           # ensure_ascii=False
    assert evidencia["contenido_json"].index('"cuenta"') < evidencia["contenido_json"].index('"datos"')

    # Mismo contenido -> misma huella (JSON determinista).
    repetida = EvidenceService.crear_evidencia(estudiante_id, None, "PLAN_CUENTAS",
                                               "Evidencia con acentos",
                                               contenido_dict=contenido, db_path=db)
    assert repetida["huella"] == evidencia["huella"]
    assert repetida["codigo"] != evidencia["codigo"]
