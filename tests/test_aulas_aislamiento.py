# -*- coding: utf-8 -*-
"""Pruebas de aislamiento entre aulas: un aula (base de datos) por estudiante.

Comprueba que todo el trabajo contable de un estudiante se resuelve contra SU propia base
de datos (`models.get_db_contable()`) y no contra la base de control:

    1. Una cuenta registrada por el estudiante A no aparece ni en el plan de cuentas ni en la
       API de cuentas del estudiante B.
    2. Los asientos de A no aparecen en el Libro Diario ni en el Balance de Comprobación de B.
    3. Un usuario Estudiante sin aula creada sigue trabajando en la base de control
       (modo demostración) sin errores.
    4. `get_db_contable()` resuelve el aula cuando hay sesión de estudiante con aula y la base
       de control en cualquier otro caso (prueba unitaria directa, sin petición HTTP).

Las dos aulas se crean con `database.crear_aula.crear_aula(...)` en una carpeta temporal y se
borran al terminar la prueba (no se toca `database/aulas/` del repositorio).
"""

import os
import sqlite3

import pytest
from flask import session as flask_session

from config import Config
from database.crear_aula import crear_aula
from models import existe_aula, get_db_contable, get_db_control

CODIGO_PRIVADO = "9.9.99"
NOMBRE_PRIVADO = "CUENTA PRIVADA DE A"
GLOSA_PRIVADA = "ASIENTO PRIVADO DE A"
MONTO_PRIVADO = 1234.56
MONTO_FORMATO = "1,234.56"

# Marcas para saber qué archivo se abrió en la prueba unitaria de get_db_contable()
CODIGO_AULA_A = "7.7.77"
CODIGO_CONTROL = "6.6.66"


# --------------------------------------------------------------------------- Utilidades
def _filas(ruta, sql, params=()):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    try:
        return [dict(f) for f in conexion.execute(sql, params).fetchall()]
    finally:
        conexion.close()


def _escalar(ruta, sql, params=()):
    filas = _filas(ruta, sql, params)
    if not filas:
        return None
    return list(filas[0].values())[0]


def _ejecutar(ruta, sql, params=()):
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute(sql, params)
        conexion.commit()
    finally:
        conexion.close()


def _marcar_cuenta(ruta, codigo):
    """Inserta una cuenta distintiva para identificar el archivo abierto."""
    _ejecutar(ruta, """
        INSERT INTO cuentas (codigo, nombre, naturaleza, clasificacion, nivel, acepta_movimiento, activo)
        VALUES (?, ?, 'DEUDORA', 'ACTIVO_CORRIENTE', 4, 1, 1)
    """, (codigo, codigo))


def _crear_usuario_control(ruta_control, username, nombre, rol_id=3, paralelo="B"):
    """Crea el usuario en la base de CONTROL (los usuarios no viven en las aulas)."""
    conexion = get_db_control(ruta_control)
    try:
        cursor = conexion.execute("""
            INSERT INTO usuarios (username, password_hash, nombre_completo, email, rol_id, activo, paralelo)
            VALUES (?, 'sin-clave', ?, ?, ?, 1, ?)
        """, (username, nombre, "%s@estudiantes.edu.ec" % username, rol_id, paralelo))
        conexion.commit()
        return cursor.lastrowid
    finally:
        conexion.close()


def _cliente(usuario, rol, paralelo, usuario_id):
    """Cliente de pruebas de Flask con la sesión ya iniciada como el usuario indicado."""
    import app as app_module

    aplicacion = app_module.create_app()
    aplicacion.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    cliente = aplicacion.test_client()
    with cliente.session_transaction() as sesion:
        sesion["user_id"] = usuario_id
        sesion["username"] = usuario
        sesion["user_role"] = rol
        sesion["paralelo"] = paralelo
        sesion["empresa_id"] = 1
    return cliente


def _borrar_archivo(ruta):
    for sufijo in ("", "-wal", "-shm"):
        if ruta and os.path.exists(ruta + sufijo):
            os.remove(ruta + sufijo)


def _codigos_visibles_para_el_usuario_en_sesion():
    """Códigos de cuenta que ve `get_db_contable()` con la sesión actual."""
    conexion = get_db_contable()
    try:
        return {f["codigo"] for f in conexion.execute("SELECT codigo FROM cuentas").fetchall()}
    finally:
        conexion.close()


# --------------------------------------------------------------------------- Fixtures
@pytest.fixture()
def aulas(db, tmp_path, monkeypatch):
    """Dos aulas reales (estudiante_a y estudiante_b) creadas en una carpeta temporal."""
    carpeta = tmp_path / "aulas"
    plantilla = tmp_path / "plantilla" / "aula_base.db"
    monkeypatch.setattr(Config, "RUTA_AULAS", str(carpeta))
    monkeypatch.setattr(Config, "RUTA_PLANTILLA", str(plantilla))
    monkeypatch.setattr(Config, "MULTIESTUDIANTE", True)

    # La plantilla se construye a partir de la base de la prueba (la demostrativa); se consolida
    # el WAL antes de copiarla para que el aula clonada tenga todos los datos.
    _ejecutar(db, "PRAGMA wal_checkpoint(TRUNCATE)")

    id_a = _crear_usuario_control(db, "estudiante_a", "Estudiante A")
    id_b = _crear_usuario_control(db, "estudiante_b", "Estudiante B")
    ruta_a = crear_aula("estudiante_a", "B", estudiante_id=id_a, verboso=False)
    ruta_b = crear_aula("estudiante_b", "B", estudiante_id=id_b, verboso=False)

    datos = {
        "a": ruta_a,
        "b": ruta_b,
        "control": db,
        "carpeta": str(carpeta),
        "id_a": id_a,
        "id_b": id_b,
    }
    yield datos

    # Limpieza: todo lo creado en la prueba es temporal y se elimina.
    _borrar_archivo(ruta_a)
    _borrar_archivo(ruta_b)
    _borrar_archivo(str(plantilla))
    if os.path.isdir(str(carpeta)):
        for raiz, _dirs, archivos in os.walk(str(carpeta)):
            for nombre in archivos:
                os.remove(os.path.join(raiz, nombre))


# --------------------------------------------------------------------------- 1. Cuentas
def test_cuenta_de_a_no_aparece_en_el_plan_de_cuentas_ni_en_la_api_de_b(aulas):
    cliente_a = _cliente("estudiante_a", "Estudiante", "B", aulas["id_a"])
    cliente_b = _cliente("estudiante_b", "Estudiante", "B", aulas["id_b"])

    respuesta = cliente_a.post("/contabilidad/cuentas", data={
        "codigo": CODIGO_PRIVADO,
        "nombre": NOMBRE_PRIVADO,
        "naturaleza": "DEUDORA",
        "clasificacion": "ACTIVO_CORRIENTE",
        "nivel": 4,
        "acepta_movimiento": 1,
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    assert NOMBRE_PRIVADO in respuesta.get_data(as_text=True)

    # La cuenta existe en el aula de A...
    assert _escalar(aulas["a"], "SELECT COUNT(*) FROM cuentas WHERE codigo = ?",
                    (CODIGO_PRIVADO,)) == 1
    # ...y no en el aula de B ni en la base de control.
    assert _escalar(aulas["b"], "SELECT COUNT(*) FROM cuentas WHERE codigo = ?",
                    (CODIGO_PRIVADO,)) == 0
    assert _escalar(aulas["control"], "SELECT COUNT(*) FROM cuentas WHERE codigo = ?",
                    (CODIGO_PRIVADO,)) == 0

    # Plan de cuentas en pantalla: A la ve, B no.
    texto_a = cliente_a.get("/contabilidad/cuentas").get_data(as_text=True)
    assert CODIGO_PRIVADO in texto_a and NOMBRE_PRIVADO in texto_a

    pagina_b = cliente_b.get("/contabilidad/cuentas")
    assert pagina_b.status_code == 200
    texto_b = pagina_b.get_data(as_text=True)
    assert CODIGO_PRIVADO not in texto_b
    assert NOMBRE_PRIVADO not in texto_b

    # API de cuentas (/api/accounts): B solo recibe su propio plan de cuentas.
    api_b = cliente_b.get("/api/accounts")
    assert api_b.status_code == 200
    cuentas_b = api_b.get_json()["accounts"]
    assert cuentas_b, "B debe recibir su propio plan de cuentas (clonado de la plantilla)"
    assert all(cuenta["codigo"] != CODIGO_PRIVADO for cuenta in cuentas_b)
    assert all(cuenta["nombre"] != NOMBRE_PRIVADO for cuenta in cuentas_b)

    # La misma API, con la sesión de A, sí devuelve la cuenta privada.
    cuentas_a = cliente_a.get("/api/accounts").get_json()["accounts"]
    assert any(cuenta["codigo"] == CODIGO_PRIVADO for cuenta in cuentas_a)


# --------------------------------------------------------------------------- 2. Asientos
def test_asiento_de_a_no_aparece_en_el_diario_ni_en_el_balance_de_b(aulas):
    cliente_a = _cliente("estudiante_a", "Estudiante", "B", aulas["id_a"])
    cliente_b = _cliente("estudiante_b", "Estudiante", "B", aulas["id_b"])

    caja = _escalar(aulas["a"], "SELECT id FROM cuentas WHERE codigo = '1.1.01'")
    ingresos = _escalar(aulas["a"], "SELECT id FROM cuentas WHERE codigo = '4.1.01'")
    assert caja and ingresos, "El aula debe tener el plan de cuentas de la plantilla"

    respuesta = cliente_a.post("/contabilidad/diario", data={
        "fecha": "2026-09-25",
        "glosa": GLOSA_PRIVADA,
        "tipo_documento": "MANUAL",
        "numero_documento": "A-001",
        "cuenta_id[]": [caja, ingresos],
        "debe[]": [MONTO_PRIVADO, 0],
        "haber[]": [0, MONTO_PRIVADO],
        "referencia[]": ["", ""],
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    assert GLOSA_PRIVADA in respuesta.get_data(as_text=True)

    # El asiento quedó en el aula de A...
    assert _escalar(aulas["a"], "SELECT COUNT(*) FROM asientos WHERE glosa = ?",
                    (GLOSA_PRIVADA,)) == 1
    assert round(_escalar(aulas["a"], "SELECT SUM(debe) FROM detalle_asientos"), 2) == MONTO_PRIVADO
    # ...y el aula de B sigue sin movimientos.
    assert _escalar(aulas["b"], "SELECT COUNT(*) FROM asientos") == 0
    assert _escalar(aulas["b"], "SELECT COUNT(*) FROM detalle_asientos") == 0

    # Libro Diario de B: no aparece el asiento de A.
    diario_b = cliente_b.get("/contabilidad/diario")
    assert diario_b.status_code == 200
    texto_diario_b = diario_b.get_data(as_text=True)
    assert GLOSA_PRIVADA not in texto_diario_b
    assert MONTO_FORMATO not in texto_diario_b

    # Balance de Comprobación de B: sin débitos y sin rastro del asiento de A.
    balance_b = cliente_b.get("/contabilidad/balance")
    assert balance_b.status_code == 200
    texto_balance_b = balance_b.get_data(as_text=True)
    assert MONTO_FORMATO not in texto_balance_b
    assert "Total Débitos: $0.00" in texto_balance_b
    assert "Total Créditos: $0.00" in texto_balance_b

    # El balance de A sí refleja su propio asiento (la prueba no es un falso positivo).
    texto_balance_a = cliente_a.get("/contabilidad/balance").get_data(as_text=True)
    assert MONTO_FORMATO in texto_balance_a


# -------------------------------------------- 3. Estudiante sin aula: modo demostración
def test_estudiante_sin_aula_trabaja_en_la_base_de_control_sin_errores(aulas):
    """La cuenta demostrativa `estudiante` no tiene aula: su trabajo va a la base de control."""
    _marcar_cuenta(aulas["control"], CODIGO_CONTROL)
    id_demo = _escalar(aulas["control"], "SELECT id FROM usuarios WHERE username = 'estudiante'")
    assert id_demo, "La base de control de prueba debe tener el usuario demostrativo 'estudiante'"

    assert not existe_aula("estudiante", "B"), "Esta prueba requiere que 'estudiante' no tenga aula"

    cliente = _cliente("estudiante", "Estudiante", "B", id_demo)

    # El plan de cuentas que ve es el de la base de control (incluye la cuenta marcada).
    pagina = cliente.get("/contabilidad/cuentas")
    assert pagina.status_code == 200
    texto = pagina.get_data(as_text=True)
    assert CODIGO_CONTROL in texto

    # Registra un asiento y queda en la base de control, no en un aula.
    caja = _escalar(aulas["control"], "SELECT id FROM cuentas WHERE codigo = '1.1.01'")
    ingresos = _escalar(aulas["control"], "SELECT id FROM cuentas WHERE codigo = '4.1.01'")
    respuesta = cliente.post("/contabilidad/diario", data={
        "fecha": "2026-09-25",
        "glosa": "ASIENTO DEMOSTRATIVO SIN AULA",
        "tipo_documento": "MANUAL",
        "cuenta_id[]": [caja, ingresos],
        "debe[]": [250.0, 0],
        "haber[]": [0, 250.0],
        "referencia[]": ["", ""],
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    assert "ASIENTO DEMOSTRATIVO SIN AULA" in respuesta.get_data(as_text=True)
    assert _escalar(aulas["control"], "SELECT COUNT(*) FROM asientos WHERE glosa = ?",
                    ("ASIENTO DEMOSTRATIVO SIN AULA",)) == 1
    assert _escalar(aulas["b"], "SELECT COUNT(*) FROM asientos") == 0
    assert _escalar(aulas["a"], "SELECT COUNT(*) FROM asientos") == 0

    # El resto de pantallas contables responde sin errores en modo demostración.
    for ruta in ("/contabilidad/diario", "/contabilidad/mayor", "/contabilidad/balance",
                 "/dashboard"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 200, "Falló %s con estado %s" % (ruta, respuesta.status_code)


# --------------------------------------- 4. Resolución de get_db_contable() (sin HTTP)
def test_get_db_contable_resuelve_el_aula_del_estudiante(aulas, monkeypatch):
    """Prueba unitaria directa de models.get_db_contable(): aula vs. base de control."""
    import app as app_module

    _marcar_cuenta(aulas["a"], CODIGO_AULA_A)
    _marcar_cuenta(aulas["control"], CODIGO_CONTROL)
    aplicacion = app_module.create_app()

    # (a) Con contexto de aplicación (sin petición ni sesión) -> base de control.
    with aplicacion.app_context():
        assert CODIGO_CONTROL in _codigos_visibles_para_el_usuario_en_sesion()
        assert CODIGO_AULA_A not in _codigos_visibles_para_el_usuario_en_sesion()

    # (b) Dentro de una petición con distintas sesiones.
    with aplicacion.test_request_context("/contabilidad/cuentas"):
        flask_session.clear()
        assert CODIGO_CONTROL in _codigos_visibles_para_el_usuario_en_sesion(), "anónimo -> control"

        flask_session["user_id"] = 1
        flask_session["username"] = "docente"
        flask_session["user_role"] = "Docente"
        assert CODIGO_CONTROL in _codigos_visibles_para_el_usuario_en_sesion(), "docente -> control"
        assert CODIGO_AULA_A not in _codigos_visibles_para_el_usuario_en_sesion()

        flask_session["user_role"] = "Auditor"
        flask_session["username"] = "auditor"
        assert CODIGO_CONTROL in _codigos_visibles_para_el_usuario_en_sesion(), "auditor -> control"

        # Estudiante QUE NO TIENE aula -> base de control (modo demostración).
        flask_session["user_role"] = "Estudiante"
        flask_session["username"] = "estudiante_sin_aula"
        flask_session["paralelo"] = "B"
        assert CODIGO_CONTROL in _codigos_visibles_para_el_usuario_en_sesion()

        # Estudiante CON aula -> su aula.
        flask_session["username"] = "estudiante_a"
        visibles = _codigos_visibles_para_el_usuario_en_sesion()
        assert CODIGO_AULA_A in visibles, "estudiante con aula -> su aula"
        assert CODIGO_CONTROL not in visibles, "el estudiante no ve la base de control"

        # El paralelo de la sesión es el que ubica la carpeta del aula.
        flask_session["paralelo"] = "Z"
        assert CODIGO_CONTROL in _codigos_visibles_para_el_usuario_en_sesion(), \
            "con otro paralelo no encuentra aula y cae en la base de control"

        # El otro estudiante ve su propia aula, no la de A.
        flask_session["paralelo"] = "B"
        flask_session["username"] = "estudiante_b"
        visibles_b = _codigos_visibles_para_el_usuario_en_sesion()
        assert CODIGO_AULA_A not in visibles_b

        # Una ruta explícita siempre manda sobre la sesión.
        conexion = get_db_contable(aulas["a"])
        try:
            codigos = {f["codigo"] for f in conexion.execute("SELECT codigo FROM cuentas").fetchall()}
        finally:
            conexion.close()
        assert CODIGO_AULA_A in codigos

    # (c) Modo de un solo curso (multiestudiante desactivado) -> base de control, como siempre.
    monkeypatch.setattr(Config, "MULTIESTUDIANTE", False)
    with aplicacion.test_request_context("/contabilidad/cuentas"):
        flask_session["user_id"] = aulas["id_a"]
        flask_session["username"] = "estudiante_a"
        flask_session["user_role"] = "Estudiante"
        flask_session["paralelo"] = "B"
        assert CODIGO_CONTROL in _codigos_visibles_para_el_usuario_en_sesion()
