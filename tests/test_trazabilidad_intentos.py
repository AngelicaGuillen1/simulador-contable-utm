# -*- coding: utf-8 -*-
"""Trazabilidad de los INTENTOS RECHAZADOS (regla §58.3 del prompt maestro).

El prompt exige que un intento fallido quede registrado como evidencia pedagógica
con su mensaje, aunque la interfaz responda con redirect + flash (HTTP 302) y no
con un error 4xx.

Cubre:
  1. Un asiento descuadrado se registra como INTENTO_FALLIDO_ASIENTO con el mensaje
     del rechazo, y NO como CREAR_ASIENTO.
  2. Un asiento correcto se registra como CREAR_ASIENTO (sin falsos positivos).
  3. Un comprobante rechazado se registra como INTENTO_FALLIDO_DOCUMENTO.
"""
import pytest

from models import get_db_connection
from services.access_service import registrar_evento_desde_request

CREDENCIALES_ESTUDIANTE = {"username": "estudiante", "password": "estudiante123"}
GLOSA_RECHAZADA = "Asiento de prueba descuadrado (verificación de trazabilidad)"
GLOSA_VALIDA = "Asiento de prueba cuadrado (verificación de trazabilidad)"


# --------------------------------------------------------------------------- utilidades
def _conexion(db):
    return get_db_connection(db)


def _eventos(db, tipo=None):
    conn = _conexion(db)
    try:
        sql = "SELECT * FROM eventos_estudiante WHERE 1=1"
        params = []
        if tipo:
            sql += " AND evento = ?"
            params.append(tipo)
        sql += " ORDER BY id ASC"
        return [dict(f) for f in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _escalar(db, sql, params=()):
    conn = _conexion(db)
    try:
        fila = conn.execute(sql, params).fetchone()
        return fila[0] if fila else None
    finally:
        conn.close()


def _cuenta_id(db, codigo):
    cuenta = _escalar(db, "SELECT id FROM cuentas WHERE codigo = ?", (codigo,))
    assert cuenta, f"La base de prueba debe tener la cuenta {codigo}"
    return cuenta


# --------------------------------------------------------------------------- fixtures
@pytest.fixture()
def app_hook(db):
    """Aplicación Flask real con el hook global de trazabilidad activo."""
    import app as app_module

    aplicacion = app_module.create_app()
    aplicacion.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    aplicacion.after_request(registrar_evento_desde_request)
    return aplicacion


@pytest.fixture()
def cliente(app_hook):
    """Cliente con sesión de ESTUDIANTE (único rol que se traza pedagógicamente)."""
    cliente = app_hook.test_client()
    respuesta = cliente.post("/login", data=dict(CREDENCIALES_ESTUDIANTE), follow_redirects=True)
    assert respuesta.status_code == 200, "El estudiante demostrativo debe poder iniciar sesión"
    return cliente


def _enviar_asiento(cliente, db, debe, haber, glosa):
    """Envía un asiento manual por la misma ruta que usa la interfaz."""
    return cliente.post("/contabilidad/diario", data={
        "fecha": "2026-09-25",
        "glosa": glosa,
        "tipo_documento": "MANUAL",
        "numero_documento": "",
        "cuenta_id[]": [_cuenta_id(db, "1.1.01"), _cuenta_id(db, "4.1.01")],
        "debe[]": [debe, 0],
        "haber[]": [0, haber],
        "referencia[]": ["", ""],
    }, follow_redirects=True)


# --------------------------------------------------------------------------- 1. rechazo
def test_asiento_descuadrado_queda_como_intento_fallido(cliente, db):
    asientos_antes = _escalar(db, "SELECT COUNT(*) FROM asientos")

    respuesta = _enviar_asiento(cliente, db, 500.00, 450.00, GLOSA_RECHAZADA)
    assert respuesta.status_code == 200

    fallidos = _eventos(db, "INTENTO_FALLIDO_ASIENTO")
    assert fallidos, ("Un asiento rechazado debe registrarse como INTENTO_FALLIDO_ASIENTO: "
                      "es evidencia pedagógica (§58.3)")
    ultimo = fallidos[-1]
    assert "no cuadra" in (ultimo.get("detalle") or ""), (
        "El registro del intento debe conservar el mensaje del rechazo: %r" % ultimo.get("detalle"))
    assert "50.00" in (ultimo.get("detalle") or ""), "El mensaje debe indicar la diferencia"

    # No se guardó ningún asiento y el rechazo NO se cuenta como creación.
    assert _escalar(db, "SELECT COUNT(*) FROM asientos") == asientos_antes
    assert not [e for e in _eventos(db, "CREAR_ASIENTO") if GLOSA_RECHAZADA in (e.get("detalle") or "")]


def test_asiento_correcto_no_se_marca_como_fallido(cliente, db):
    fallidos_antes = len(_eventos(db, "INTENTO_FALLIDO_ASIENTO"))
    asientos_antes = _escalar(db, "SELECT COUNT(*) FROM asientos")

    respuesta = _enviar_asiento(cliente, db, 300.00, 300.00, GLOSA_VALIDA)
    assert respuesta.status_code == 200
    assert GLOSA_VALIDA in respuesta.get_data(as_text=True)

    assert _escalar(db, "SELECT COUNT(*) FROM asientos") == asientos_antes + 1
    assert len(_eventos(db, "INTENTO_FALLIDO_ASIENTO")) == fallidos_antes, \
        "Un asiento aceptado no debe registrarse como intento fallido"
    assert [e for e in _eventos(db, "CREAR_ASIENTO")], "El asiento aceptado sí debe trazarse"


# --------------------------------------------------------------------------- 3. documentos
def test_comprobante_rechazado_queda_como_intento_fallido(cliente, db):
    """Una factura a consumidor final por encima del tope (R-57.7) debe dejar traza."""
    respuesta = cliente.post("/documentos/nuevo", data={
        "tipo": "FACTURA",
        "fecha": "2026-11-18",
        "numero_autorizacion": "1234567890",
        "fecha_autorizacion": "2026-09-01",
        "fecha_caducidad_autorizacion": "2027-09-01",
        "establecimiento": "001",
        "punto_emision": "002",
        "secuencial": "000000231",
        "adquirente_tipo_id": "CONSUMIDOR_FINAL",
        "adquirente_nombre": "CONSUMIDOR FINAL",
        "descripcion": "Compra de consumidor final",
        "subtotal": "250",
        "iva_tarifa": "15",
        "iva_valor": "37.5",
        "monto_total": "287.5",
        "forma_pago": "EFECTIVO",
    }, follow_redirects=True)
    assert respuesta.status_code == 200

    fallidos = _eventos(db, "INTENTO_FALLIDO_DOCUMENTO")
    assert fallidos, "Un comprobante rechazado debe registrarse como intento fallido"
    detalle = fallidos[-1].get("detalle") or ""
    assert "R-57.7" in detalle, "El registro debe citar la regla incumplida: %r" % detalle
    assert "FACTURA" in detalle, "El registro debe guardar el documento elegido"
