# -*- coding: utf-8 -*-
"""Pruebas del panel docente de LIBROS por estudiante (aula propia, solo lectura).

Modelo de referencia: docs/DISENO_MULTIESTUDIANTE.md — cada estudiante tiene su propia base
SQLite contable (su *aula*) y la base de control conserva usuarios, actividades y evidencias.

Cubre:
    1. El docente autenticado ve el asiento del aula del estudiante en /docente/estudiantes/<id>/diario
       y las cifras correctas en /docente/estudiantes/<id>/balance.
    2. El resumen de la evidencia de ese estudiante trae las cifras de SU aula (y no las de la
       empresa demostrativa), y la evidencia se guarda en la base de CONTROL.
    3. Un estudiante (rol Estudiante) recibe 403 en las rutas /docente/estudiantes/<id>/*.
    4. Un estudiante sin aula: las rutas del docente muestran el aviso, nunca un error 500.
    5. Leer los libros del estudiante NUNCA escribe en su aula (se abre en modo lectura).
"""
import os
import sqlite3

import pytest

from config import Config
from models import get_db_connection, ruta_aula
from services.evidence_service import EvidenceService

CONCEPTO_APORTE = "Aporte inicial de los socios en efectivo (prueba)"
MONTO_APORTE = 1500.00
DESDE = "2026-09-25"
USUARIO_CON_AULA = "jvargas9001"
USUARIO_SIN_AULA = "sinaula9002"

SUFIJOS_LIBROS = ("diario", "mayor", "balance", "cuentas", "estados")


# --------------------------------------------------------------------------- Utilidades
def _sqlite(ruta):
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    return conn


def _crear_estudiante(db, username, paralelo="B", nombre="Jordano Vargas - Estudiante"):
    """Inserta un estudiante en la base de CONTROL y devuelve su id."""
    conn = get_db_connection(db)
    try:
        cursor = conn.execute("""
            INSERT INTO usuarios (username, password_hash, nombre_completo, email, rol_id,
                                  activo, paralelo, matricula)
            VALUES (?, 'no-usado-en-pruebas', ?, ?, 3, 1, ?, '1700000001')
        """, (username, nombre, "%s@estudiantes.edu.ec" % username, paralelo))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _insertar_asiento(aula, monto=MONTO_APORTE):
    """Inserta un asiento real en el aula del estudiante (Debe Caja / Haber Capital)."""
    conn = _sqlite(aula)
    try:
        caja = conn.execute("SELECT id FROM cuentas WHERE codigo = '1.1.01'").fetchone()["id"]
        capital = conn.execute("SELECT id FROM cuentas WHERE codigo = '3.1.01'").fetchone()["id"]
        cursor = conn.execute("""
            INSERT INTO asientos (empresa_id, periodo_id, numero_asiento, fecha, glosa,
                                  tipo_documento, numero_documento, origen_modulo, estado)
            VALUES (1, 1, 1, ?, ?, 'COMPROBANTE', 'AP-001', 'MANUAL', 'CONTABILIZADO')
        """, (DESDE, CONCEPTO_APORTE))
        asiento_id = cursor.lastrowid
        conn.execute("""
            INSERT INTO detalle_asientos (asiento_id, cuenta_id, debe, haber, referencia)
            VALUES (?, ?, ?, 0, 'Aporte en efectivo de los socios')
        """, (asiento_id, caja, monto))
        conn.execute("""
            INSERT INTO detalle_asientos (asiento_id, cuenta_id, debe, haber, referencia)
            VALUES (?, ?, 0, ?, 'Aporte de capital')
        """, (asiento_id, capital, monto))
        conn.commit()
        return asiento_id
    finally:
        conn.close()


def _asignar_actividad_en_control(db, estudiante_id, codigo="U1-A1", estado="ENTREGADA"):
    """Crea una actividad del syllabus en la base de CONTROL y la asigna al estudiante.

    Es el registro académico que revisa el docente (la parte contable vive en el aula).
    """
    conn = get_db_connection(db)
    try:
        fila = conn.execute("SELECT id FROM actividades WHERE codigo = ?", (codigo,)).fetchone()
        if fila:
            actividad_id = fila["id"]
        else:
            cursor = conn.execute("""
                INSERT INTO actividades (codigo, titulo, unidad, componente, puntaje, estado,
                                         tipo_evidencia, creada_por)
                VALUES (?, ?, 1, 'DOCENCIA', 10, 'ABIERTA', 'INTEGRAL', 2)
            """, (codigo, "Actividad %s de prueba" % codigo))
            actividad_id = cursor.lastrowid
        conn.execute("""
            INSERT INTO asignaciones_actividad
                (actividad_id, estudiante_id, empresa_id, estado, cerrada_en)
            VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(actividad_id, estudiante_id) DO UPDATE
               SET estado = excluded.estado, cerrada_en = CURRENT_TIMESTAMP
        """, (actividad_id, estudiante_id, estado))
        conn.commit()
        return actividad_id
    finally:
        conn.close()


def _totales_de(ruta, estados=("CONTABILIZADO", "REVERTIDO")):
    """(total Debe, total Haber, número de asientos) leídos directamente del archivo."""
    marcadores = ",".join("?" for _ in estados)
    conn = _sqlite(ruta)
    try:
        fila = conn.execute("""
            SELECT COALESCE(SUM(d.debe), 0) AS debe, COALESCE(SUM(d.haber), 0) AS haber,
                   COUNT(DISTINCT a.id) AS asientos
              FROM detalle_asientos d
              JOIN asientos a ON a.id = d.asiento_id
             WHERE UPPER(IFNULL(a.estado, '')) IN (%s)
        """ % marcadores, list(estados)).fetchone()
        return round(fila["debe"], 2), round(fila["haber"], 2), fila["asientos"]
    finally:
        conn.close()


# --------------------------------------------------------------------------- Fixtures
@pytest.fixture()
def entorno_aulas(tmp_path, monkeypatch):
    """Aísla las aulas y la plantilla en tmp_path (no toca los archivos del repositorio)."""
    monkeypatch.setattr(Config, "RUTA_AULAS", str(tmp_path / "aulas"))
    monkeypatch.setattr(Config, "RUTA_PLANTILLA", str(tmp_path / "plantilla" / "aula_base.db"))
    return tmp_path


@pytest.fixture()
def estudiante_con_aula(db, entorno_aulas):
    """Estudiante nuevo con su aula clonada de la plantilla y un asiento dentro de ella."""
    from database.crear_aula import crear_aula

    estudiante_id = _crear_estudiante(db, USUARIO_CON_AULA, paralelo="B")
    aula = crear_aula(USUARIO_CON_AULA, "B", plan="completo", estudiante_id=estudiante_id,
                      verboso=False)
    asiento_id = _insertar_asiento(aula)
    _asignar_actividad_en_control(db, estudiante_id)
    assert os.path.exists(aula), "El aula del estudiante debe existir para las pruebas"
    assert aula == ruta_aula(USUARIO_CON_AULA, "B")
    return {"id": estudiante_id, "username": USUARIO_CON_AULA, "aula": aula,
            "asiento_id": asiento_id, "monto": MONTO_APORTE}


@pytest.fixture()
def estudiante_sin_aula(db, entorno_aulas):
    """Estudiante de la base de control que todavía no tiene aula contable creada."""
    estudiante_id = _crear_estudiante(db, USUARIO_SIN_AULA, paralelo="C",
                                      nombre="Sin Aula Toledo - Estudiante")
    assert not os.path.exists(ruta_aula(USUARIO_SIN_AULA, "C"))
    return {"id": estudiante_id, "username": USUARIO_SIN_AULA}


@pytest.fixture()
def cliente_docente(app_client):
    respuesta = app_client.post("/login", data={"username": "docente", "password": "docente123"},
                                follow_redirects=True)
    assert respuesta.status_code == 200
    return app_client


@pytest.fixture()
def cliente_estudiante_rol(app_client):
    respuesta = app_client.post("/login", data={"username": "estudiante",
                                                "password": "estudiante123"},
                                follow_redirects=True)
    assert respuesta.status_code == 200
    return app_client


# =========================================================================== 1. Vistas del docente
def test_docente_ve_el_asiento_del_aula_en_el_diario_y_las_cifras_en_el_balance(
        estudiante_con_aula, cliente_docente):
    estudiante_id = estudiante_con_aula["id"]

    # --- Libro Diario: el asiento insertado en el aula aparece tal cual ---
    diario = cliente_docente.get("/docente/estudiantes/%d/diario" % estudiante_id)
    assert diario.status_code == 200
    cuerpo = diario.get_data(as_text=True)
    assert CONCEPTO_APORTE in cuerpo
    assert "1.1.01" in cuerpo and "Caja General" in cuerpo
    assert "3.1.01" in cuerpo and "Capital Social Suscrito y Pagado" in cuerpo
    assert "AP-001" in cuerpo
    assert "1500.00" in cuerpo
    assert "Solo lectura" in cuerpo

    # --- Libro Mayor: la cuenta con su movimiento y su saldo ---
    mayor = cliente_docente.get("/docente/estudiantes/%d/mayor" % estudiante_id)
    assert mayor.status_code == 200
    assert "1.1.01" in mayor.get_data(as_text=True)
    assert "1500.00" in mayor.get_data(as_text=True)

    # --- Balance de comprobación: sumas y saldos del aula ---
    balance = cliente_docente.get("/docente/estudiantes/%d/balance" % estudiante_id)
    assert balance.status_code == 200
    assert "El balance cuadra" in balance.get_data(as_text=True)

    datos = cliente_docente.get(
        "/docente/estudiantes/%d/balance?formato=json" % estudiante_id).get_json()
    libro = datos["balance"]
    assert libro["existe"] is True
    assert libro["aula"] == estudiante_con_aula["aula"]
    assert libro["nombre_archivo"] == os.path.basename(estudiante_con_aula["aula"])
    assert libro["total_debitos"] == MONTO_APORTE
    assert libro["total_creditos"] == MONTO_APORTE
    assert libro["total_saldo_deudor"] == MONTO_APORTE
    assert libro["total_saldo_acreedor"] == MONTO_APORTE
    assert libro["cuadrado_sumas"] is True and libro["cuadrado_saldos"] is True
    assert libro["cuadrado"] is True

    cuentas = {c["codigo"]: c for c in libro["cuentas"]}
    assert cuentas["1.1.01"]["debitos"] == MONTO_APORTE
    assert cuentas["1.1.01"]["saldo_deudor"] == MONTO_APORTE
    assert cuentas["3.1.01"]["creditos"] == MONTO_APORTE
    assert cuentas["3.1.01"]["saldo_acreedor"] == MONTO_APORTE

    # --- Plan de cuentas y estados financieros ---
    cuentas_json = cliente_docente.get(
        "/docente/estudiantes/%d/cuentas?formato=json" % estudiante_id).get_json()["plan_cuentas"]
    assert cuentas_json["existe"] is True
    assert cuentas_json["num_cuentas"] >= 1
    codigos = {c["codigo"] for c in cuentas_json["cuentas"]}
    assert {"1.1.01", "3.1.01"} <= codigos

    estados = cliente_docente.get(
        "/docente/estudiantes/%d/estados?formato=json" % estudiante_id).get_json()["estados"]
    assert estados["existe"] is True
    situacion = estados["situacion"]
    assert situacion["total_activo"] == MONTO_APORTE          # Caja General
    assert situacion["total_pasivo_y_patrimonio"] == MONTO_APORTE   # Capital social
    assert situacion["cuadra"] is True

    # --- La ficha del estudiante resume sus libros y su avance ---
    ficha = cliente_docente.get("/docente/estudiantes/%d?formato=json" % estudiante_id).get_json()
    assert ficha["ok"] is True
    assert ficha["ficha"]["libros"]["existe"] is True
    assert ficha["ficha"]["libros"]["num_asientos"] == 1
    assert ficha["ficha"]["libros"]["cuadrado"] is True
    avance = ficha["ficha"]["avance"]
    assert avance["asignadas"] >= 1
    assert avance["completadas"] == 1                      # la actividad se entregó
    assert 0 < avance["porcentaje"] <= 100
    assert avance["porcentaje"] == round(avance["completadas"] * 100.0 / avance["asignadas"], 1)

    # --- El docente lee el aula pero NUNCA la modifica: sigue con su único asiento ---
    debe, haber, asientos = _totales_de(estudiante_con_aula["aula"])
    assert (debe, haber, asientos) == (MONTO_APORTE, MONTO_APORTE, 1)
    conn = _sqlite(estudiante_con_aula["aula"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM evidencias").fetchone()[0] == 0
        # El aula nace con el plan de cuentas de la plantilla, sin cuentas de más ni de menos.
        # (Se compara contra la plantilla y no contra un número fijo, que cambia cuando el plan
        #  de cuentas crece: p. ej. al añadir las cuentas de retención por cobrar.)
        with sqlite3.connect(Config.RUTA_PLANTILLA) as conn_plantilla:
            esperadas = conn_plantilla.execute("SELECT COUNT(*) FROM cuentas").fetchone()[0]
        assert esperadas >= 43
        assert conn.execute("SELECT COUNT(*) FROM cuentas").fetchone()[0] == esperadas
    finally:
        conn.close()


def test_rutas_de_libros_responden_en_html_y_json_para_admin_y_docente(
        estudiante_con_aula, app_client, cliente_docente):
    estudiante_id = estudiante_con_aula["id"]
    for sufijo in SUFIJOS_LIBROS:
        respuesta = cliente_docente.get("/docente/estudiantes/%d/%s" % (estudiante_id, sufijo))
        assert respuesta.status_code == 200
        assert "Solo lectura" in respuesta.get_data(as_text=True)

    # Un estudiante inexistente devuelve 404 (no 500).
    assert cliente_docente.get("/docente/estudiantes/999999/diario").status_code == 404
    assert cliente_docente.get(
        "/docente/estudiantes/999999/balance?formato=json").status_code == 404


# =========================================================================== 2. Evidencia
def test_el_resumen_de_la_evidencia_trae_las_cifras_del_aula_del_estudiante(
        estudiante_con_aula, db):
    estudiante_id = estudiante_con_aula["id"]
    aula = estudiante_con_aula["aula"]

    evidencia = EvidenceService.crear_evidencia(
        estudiante_id, None, "INTEGRAL", "Evidencia integral del aula propia", db_path=db)

    # La evidencia se GUARDA en la base de control, no en el aula del estudiante.
    conn = get_db_connection(db)
    try:
        guardada = conn.execute("SELECT id FROM evidencias WHERE id = ?",
                                (evidencia["id"],)).fetchone()
    finally:
        conn.close()
    assert guardada is not None
    conn = _sqlite(aula)
    try:
        assert conn.execute("SELECT COUNT(*) FROM evidencias").fetchone()[0] == 0
    finally:
        conn.close()

    # Y sus cifras se leen del aula (el asiento insertado), no de la empresa demostrativa.
    resumen = EvidenceService.resumen_evidencia(evidencia["id"], db_path=db)
    assert resumen["vacio"] is False
    balance = [s for s in resumen["secciones"] if "Balance" in s["titulo"]][0]
    totales = balance["filas"][-1]
    assert "TOTALES" in totales
    assert float(totales[2].replace(",", "")) == MONTO_APORTE
    assert float(totales[3].replace(",", "")) == MONTO_APORTE
    assert float(totales[4].replace(",", "")) == MONTO_APORTE
    assert float(totales[5].replace(",", "")) == MONTO_APORTE

    diario = [s for s in resumen["secciones"] if "Diario" in s["titulo"]][0]
    assert CONCEPTO_APORTE in " ".join(str(v) for fila in diario["filas"] for v in fila)
    assert len(diario["filas"]) == 2                     # dos líneas: Caja y Capital

    # Las cifras coinciden con el archivo del aula y NO con la empresa de demostración.
    debe_aula, haber_aula, _ = _totales_de(aula)
    assert (debe_aula, haber_aula) == (MONTO_APORTE, MONTO_APORTE)
    debe_demo, haber_demo, asientos_demo = _totales_de(db)
    assert asientos_demo > 0
    assert (debe_demo, haber_demo) != (MONTO_APORTE, MONTO_APORTE)

    # El contenido deja constancia de que las cifras vienen del aula del estudiante.
    import json
    contenido = json.loads(evidencia["contenido_json"])
    assert contenido["origen_datos"]["fuente"] == "AULA_ESTUDIANTE"
    assert contenido["origen_datos"]["archivo"] == os.path.basename(aula)
    assert "Cifras leídas del aula propia del estudiante" in resumen["texto"]

    # La evidencia sigue siendo verificable desde el panel docente (se finaliza para ello).
    EvidenceService.finalizar_evidencia(evidencia["id"], db_path=db)
    verificacion = EvidenceService.verificar_codigo(evidencia["codigo"], db_path=db)
    assert verificacion["estado"] == "FINAL"
    assert verificacion["modificada_despues"] is False
    assert verificacion["valida"] is True
    assert "1,500.00" in verificacion["resumen"]

    # Y el docente puede pedir la evidencia de ese estudiante indicando su aula explícitamente.
    contenido_explicito = EvidenceService.construir_contenido_contable(
        estudiante_id, "BALANCE", db_path=db, aula_path=aula)
    assert contenido_explicito["origen_datos"]["fuente"] == "AULA_ESTUDIANTE"
    totales_explicito = contenido_explicito["datos"]["balance"]
    assert round(sum(c["debitos"] for c in totales_explicito), 2) == MONTO_APORTE

    # Un aula indicada que no existe se rechaza con un error claro (nunca con cifras ajenas).
    from services.evidence_service import AulaNoLegible
    with pytest.raises(AulaNoLegible):
        EvidenceService.construir_contenido_contable(
            estudiante_id, "BALANCE", db_path=db,
            aula_path=str(estudiante_con_aula["aula"]) + ".no-existe.db")


# =========================================================================== 3. Roles
def test_estudiante_recibe_403_en_las_rutas_de_libros_del_docente(
        estudiante_con_aula, cliente_estudiante_rol):
    estudiante_id = estudiante_con_aula["id"]

    assert cliente_estudiante_rol.get("/docente/estudiantes").status_code == 403
    assert cliente_estudiante_rol.get("/docente/estudiantes/%d" % estudiante_id).status_code == 403
    for sufijo in SUFIJOS_LIBROS:
        respuesta = cliente_estudiante_rol.get(
            "/docente/estudiantes/%d/%s" % (estudiante_id, sufijo))
        assert respuesta.status_code == 403, "Rol Estudiante no debe entrar a /%s" % sufijo
        assert respuesta.status_code != 500


def test_sin_sesion_las_rutas_de_libros_redirigen_al_login(estudiante_con_aula, app_client):
    estudiante_id = estudiante_con_aula["id"]
    for sufijo in SUFIJOS_LIBROS:
        assert app_client.get(
            "/docente/estudiantes/%d/%s" % (estudiante_id, sufijo)).status_code == 302


# =========================================================================== 4. Estudiante sin aula
def test_estudiante_sin_aula_muestra_aviso_y_no_error_500(
        estudiante_sin_aula, cliente_docente):
    estudiante_id = estudiante_sin_aula["id"]

    for sufijo in SUFIJOS_LIBROS:
        respuesta = cliente_docente.get("/docente/estudiantes/%d/%s" % (estudiante_id, sufijo))
        assert respuesta.status_code == 200, "La vista /%s no debe fallar" % sufijo
        cuerpo = respuesta.get_data(as_text=True)
        assert "no tiene aula contable" in cuerpo
        assert "No se inventan cifras" in cuerpo
        assert "Sin aula contable" in cuerpo

    # En JSON el resultado es explícito: no existe aula y las cifras quedan en cero.
    balance = cliente_docente.get(
        "/docente/estudiantes/%d/balance?formato=json" % estudiante_id).get_json()["balance"]
    assert balance["existe"] is False
    assert balance["aula"] is None
    assert balance["total_debitos"] == 0.0 and balance["total_creditos"] == 0.0
    assert balance["cuadrado"] is False
    assert "aula" in balance["aviso"].lower()

    # La ficha del estudiante también lo avisa y muestra el avance de sus actividades.
    ficha = cliente_docente.get(
        "/docente/estudiantes/%d?formato=json" % estudiante_id).get_json()["ficha"]
    assert ficha["libros"]["existe"] is False
    assert ficha["libros"]["num_cuentas"] == 0
    assert ficha["avance"]["asignadas"] == 0
    pagina = cliente_docente.get("/docente/estudiantes/%d" % estudiante_id)
    assert pagina.status_code == 200
    assert "no tiene aula contable" in pagina.get_data(as_text=True)


def test_aula_creada_sin_asientos_avisa_que_esta_vacia(db, entorno_aulas, cliente_docente):
    """Aula clonada pero sin movimientos: se dice expresamente, nunca se inventan cifras."""
    from database.crear_aula import crear_aula

    estudiante_id = _crear_estudiante(db, "kzambrano7777", paralelo="B",
                                      nombre="Karla Zambrano - Estudiante")
    aula = crear_aula("kzambrano7777", "B", plan="completo", estudiante_id=estudiante_id,
                      verboso=False)
    assert os.path.exists(aula)

    diario = cliente_docente.get(
        "/docente/estudiantes/%d/diario?formato=json" % estudiante_id).get_json()["libro_diario"]
    assert diario["existe"] is True
    assert diario["asientos"] == []
    assert "no contiene movimientos" in diario["aviso"]

    balance = cliente_docente.get(
        "/docente/estudiantes/%d/balance?formato=json" % estudiante_id).get_json()["balance"]
    assert balance["existe"] is True
    assert balance["cuentas"] == []
    assert balance["cuadrado"] is False
    assert "no contiene movimientos" in balance["aviso"]

    # El plan de cuentas sí existe (el aula se clona con el plan completo).
    cuentas = cliente_docente.get(
        "/docente/estudiantes/%d/cuentas?formato=json" % estudiante_id).get_json()["plan_cuentas"]
    assert cuentas["existe"] is True
    assert cuentas["num_cuentas"] > 0

    # Y una evidencia de un estudiante sin movimientos se genera vacía y lo dice.
    evidencia = EvidenceService.crear_evidencia(estudiante_id, None, "DIARIO",
                                                "Evidencia sin movimientos", db_path=db)
    resumen = EvidenceService.resumen_evidencia(evidencia["id"], db_path=db)
    assert resumen["vacio"] is True
    assert "no contiene datos contables" in resumen["texto"]
