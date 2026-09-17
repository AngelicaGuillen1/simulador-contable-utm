"""Pruebas de estados financieros, cierre contable, evaluación del estudiante y API."""
import json
import pytest

from models import get_db_connection
from services.accounting_service import AccountingService
from services.simulation_service import SimulationService
from services.evaluation_service import EvaluationService
from services.document_service import DocumentService
from services.period_service import PeriodService


# ---------------------------------------------------------------- Estados financieros
def test_estado_de_resultados_se_construye_con_los_movimientos_reales(db):
    income = AccountingService.get_income_statement(db_path=db)
    conn = get_db_connection(db)
    try:
        ventas = conn.execute("""
            SELECT COALESCE(SUM(d.haber - d.debe), 0) as total
            FROM detalle_asientos d JOIN asientos a ON d.asiento_id = a.id
            JOIN cuentas c ON d.cuenta_id = c.id
            WHERE c.codigo = '4.1.01' AND a.estado = 'CONTABILIZADO'
        """).fetchone()["total"]
    finally:
        conn.close()

    assert income["ventas_bienes"] == pytest.approx(round(ventas, 2), abs=0.01)
    assert income["total_ingresos_operacionales"] == pytest.approx(
        income["ventas_bienes"] + income["ingresos_servicios"], abs=0.01)
    assert income["utilidad_bruta"] == pytest.approx(
        income["total_ingresos_operacionales"] - income["costo_ventas"], abs=0.01)
    assert income["utilidad_neta"] == pytest.approx(
        income["utilidad_operacional"] + income["otros_ingresos"] - income["gastos_financieros"], abs=0.01)


def test_estado_de_situacion_financiera_valida_la_ecuacion(db):
    bs = AccountingService.get_balance_sheet(db_path=db)
    assert bs["balanceado"] is True
    assert bs["total_activo"] == pytest.approx(bs["total_pasivo_y_patrimonio"], abs=0.01)
    assert bs["total_pasivo"] == pytest.approx(
        bs["total_pasivo_corriente"] + bs["total_pasivo_no_corriente"], abs=0.01)
    assert bs["total_activo"] == pytest.approx(
        bs["total_activo_corriente"] + bs["total_activo_no_corriente"], abs=0.01)


def test_flujo_de_efectivo_clasifica_movimientos(db):
    cf = AccountingService.get_cash_flow_statement(db_path=db)
    assert len(cf["flujo_operacion"]) > 0
    assert cf["total_operacion"] == pytest.approx(
        round(sum(i["monto"] for i in cf["flujo_operacion"]), 2), abs=0.01)
    assert cf["variacion_neta_efectivo"] == pytest.approx(
        cf["total_operacion"] + cf["total_inversion"] + cf["total_financiamiento"], abs=0.01)


def test_documentos_fuente_respaldan_las_operaciones(db):
    documentos = DocumentService.get_documents(db_path=db)
    assert len(documentos) >= 30, "Cada operación debe tener al menos un documento fuente"

    tipos = {d["tipo"] for d in documentos}
    for esperado in ["FACTURA_VENTA", "FACTURA_COMPRA", "FACTURA_SERVICIO", "COMPROBANTE_INGRESO",
                     "COMPROBANTE_EGRESO", "NOTA_DEBITO_BCO", "NOTA_CREDITO_BCO", "PAPELETA_DEPOSITO",
                     "ARQUEO_CAJA", "ROL_PAGOS", "COMPROBANTE_AJUSTE"]:
        assert esperado in tipos, f"Falta el tipo de documento {esperado}"

    con_asiento = [d for d in documentos if d["asiento_id"]]
    assert len(con_asiento) == len(documentos), "Todos los documentos deben estar vinculados a un asiento"

    resumen = DocumentService.get_tipos_resumen(db_path=db)
    assert sum(r["cantidad"] for r in resumen) == len(documentos)


def test_trazabilidad_historial_de_cliente_y_proveedor(db):
    """La cadena venta -> asiento -> documento debe poder reconstruirse consultando la cartera."""
    conn = get_db_connection(db)
    try:
        cxc = conn.execute("""
            SELECT * FROM cuentas_cobrar WHERE tipo_origen = 'VENTA_PRODUCTOS'
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        venta = conn.execute("SELECT * FROM ventas WHERE numero_factura = ?",
                             (cxc["numero_documento"],)).fetchone()
        documento = conn.execute("SELECT * FROM documentos_fuente WHERE numero = ?",
                                 (cxc["numero_documento"],)).fetchone()
    finally:
        conn.close()

    assert venta is not None and venta["asiento_id"] is not None
    assert documento is not None and documento["asiento_id"] == venta["asiento_id"]


# ---------------------------------------------------------------- Cierre contable
def test_cierre_contable_cancela_resultados_y_bloquea_el_periodo(db):
    income_antes = AccountingService.get_income_statement(db_path=db)
    utilidad = income_antes["utilidad_neta"]

    exito, mensaje = AccountingService.execute_period_closing(1, 1, usuario_id=1, db_path=db)
    assert exito is True, mensaje
    assert str(utilidad)[:4] in mensaje.replace(",", "")

    income_despues = AccountingService.get_income_statement(db_path=db)
    assert income_despues["ventas_bienes"] == pytest.approx(0.0, abs=0.01)
    assert income_despues["ingresos_servicios"] == pytest.approx(0.0, abs=0.01)
    assert income_despues["costo_ventas"] == pytest.approx(0.0, abs=0.01)

    bs = AccountingService.get_balance_sheet(db_path=db)
    assert bs["balanceado"] is True, "La ecuación patrimonial debe mantenerse tras el cierre"

    periodo = PeriodService.get_active_period(db_path=db)
    assert periodo is None or periodo["estado"] == "CERRADO"

    # Un período cerrado no admite nuevas operaciones ordinarias
    from services.sales_service import SalesService
    with pytest.raises(ValueError):
        SalesService.create_sale(
            1, 3, [{"producto_id": 1, "cantidad": 1, "precio_unitario": 5.20}],
            forma_pago="EFECTIVO", fecha="2026-04-30", db_path=db
        )


# ---------------------------------------------------------------- Simulaciones y evaluación
def test_simulaciones_por_niveles_con_casos(db):
    simulaciones = SimulationService.get_simulations(db_path=db)
    niveles = {s["nivel"] for s in simulaciones}
    assert {1, 2, 3, 4}.issubset(niveles)
    for sim in simulaciones:
        assert sim["total_casos"] >= 4


def test_evaluacion_de_respuesta_correcta_otorga_puntaje_alto(db):
    conn = get_db_connection(db)
    try:
        caso = conn.execute("""
            SELECT * FROM casos_simulacion WHERE titulo LIKE '%contado%' ORDER BY id LIMIT 1
        """).fetchone()
        estudiante_id = conn.execute("SELECT id FROM usuarios WHERE username = 'estudiante'").fetchone()["id"]
    finally:
        conn.close()

    intento_id = SimulationService.start_attempt(caso["simulacion_id"], estudiante_id, db_path=db)
    solucion = json.loads(caso["solucion_esperada_json"])

    lineas = []
    for bloque in ("asiento", "asiento_venta", "asiento_costo"):
        for l in solucion.get(bloque, []):
            cuenta = AccountingService.get_account_by_code(l["cuenta"], db_path=db)
            lineas.append({"cuenta_id": cuenta["id"], "debe": l["debe"], "haber": l["haber"]})

    resultado = EvaluationService.evaluate_attempt(
        intento_id, caso["id"], lineas, pistas_usadas=0, tiempo_segundos=120,
        usuario_id=estudiante_id, db_path=db
    )
    assert resultado["puntuacion"] >= 85
    assert resultado["resultado"] == "CORRECTO"
    assert resultado["detalles_evaluacion"]["partida_doble"] == 10.0

    conn = get_db_connection(db)
    try:
        registro = conn.execute("""
            SELECT * FROM intentos_estudiante WHERE id = ?
        """, (intento_id,)).fetchone()
        detalle = conn.execute("""
            SELECT * FROM detalle_intentos WHERE intento_id = ?
        """, (intento_id,)).fetchall()
    finally:
        conn.close()

    assert registro["estado"] == "COMPLETADO"
    assert len(detalle) == 1
    assert "Partida doble cuadrada" in detalle[0]["retroalimentacion_especifica"]


def test_evaluacion_incorrecta_genera_retroalimentacion_especifica(db):
    conn = get_db_connection(db)
    try:
        caso = conn.execute("SELECT * FROM casos_simulacion ORDER BY id LIMIT 1").fetchone()
        estudiante_id = conn.execute("SELECT id FROM usuarios WHERE username = 'estudiante'").fetchone()["id"]
    finally:
        conn.close()

    intento_id = SimulationService.start_attempt(caso["simulacion_id"], estudiante_id, db_path=db)
    solucion = json.loads(caso["solucion_esperada_json"])
    esperada = (solucion.get("asiento") or solucion.get("asiento_venta"))[0]
    cuenta_ok = AccountingService.get_account_by_code(esperada["cuenta"], db_path=db)
    cuenta_mala = AccountingService.get_account_by_code("6.1.01", db_path=db)

    # Cuenta correcta pero en la posición contraria (Debe/Haber invertidos) y descuadre
    lineas = [
        {"cuenta_id": cuenta_ok["id"], "debe": 0.0, "haber": esperada["debe"]},
        {"cuenta_id": cuenta_mala["id"], "debe": esperada["debe"] + 10, "haber": 0.0},
    ]
    resultado = EvaluationService.evaluate_attempt(
        intento_id, caso["id"], lineas, pistas_usadas=1, tiempo_segundos=60,
        usuario_id=estudiante_id, db_path=db
    )
    assert resultado["resultado"] in ("INCORRECTO", "PARCIALMENTE_CORRECTO")
    assert "descuadrado" in resultado["retroalimentacion"] or "no coincide" in resultado["retroalimentacion"]
    assert resultado["detalles_evaluacion"]["penalizacion_pistas"] == 5.0


def test_progreso_y_analitica_docente(db):
    conn = get_db_connection(db)
    try:
        caso = conn.execute("SELECT * FROM casos_simulacion ORDER BY id LIMIT 1").fetchone()
        estudiante_id = conn.execute("SELECT id FROM usuarios WHERE username = 'estudiante'").fetchone()["id"]
    finally:
        conn.close()

    intento_id = SimulationService.start_attempt(caso["simulacion_id"], estudiante_id, db_path=db)
    solucion = json.loads(caso["solucion_esperada_json"])
    lineas = []
    for bloque in ("asiento", "asiento_venta", "asiento_costo"):
        for l in solucion.get(bloque, []):
            cuenta = AccountingService.get_account_by_code(l["cuenta"], db_path=db)
            lineas.append({"cuenta_id": cuenta["id"], "debe": l["debe"], "haber": l["haber"]})
    EvaluationService.evaluate_attempt(intento_id, caso["id"], lineas, usuario_id=estudiante_id, db_path=db)

    intentos = SimulationService.get_student_attempts(estudiante_id=estudiante_id, db_path=db)
    assert any(i["id"] == intento_id for i in intentos)

    analitica = SimulationService.get_teacher_analytics(db_path=db)
    assert analitica["total_intentos"] >= 1
    assert analitica["promedio_general"] >= 0
    assert "niveles_stats" in analitica


# ---------------------------------------------------------------- API interna
def test_api_health_y_dashboard(admin_client):
    salud = admin_client.get("/api/health")
    assert salud.status_code == 200
    datos = salud.get_json()
    assert datos["success"] is True
    assert datos["estado"] == "OPERATIVO"
    assert datos["periodo_activo"]["estado"] == "ABIERTO"

    dash = admin_client.get("/api/dashboard").get_json()
    assert dash["success"] is True
    assert "caja" in dash["indicadores"]


def test_api_tools_catalogo_completo(admin_client):
    datos = admin_client.get("/api/tools").get_json()
    assert datos["success"] is True
    assert datos["faltantes"] == [], f"Herramientas faltantes: {datos['faltantes']}"
    assert datos["total"] >= 37


def test_api_endpoints_principales(admin_client):
    for ruta in ["/api/accounts", "/api/products", "/api/inventory", "/api/customers", "/api/suppliers",
                 "/api/receivables", "/api/payables", "/api/taxes", "/api/documents", "/api/simulations",
                 "/api/periods", "/api/treasury", "/api/audit", "/api/statements"]:
        respuesta = admin_client.get(ruta)
        assert respuesta.status_code == 200, f"{ruta} devolvió {respuesta.status_code}"
        assert respuesta.get_json()["success"] is True, f"{ruta} no respondió success"

    balance = admin_client.get("/api/statements?tipo=balance_sheet").get_json()
    assert balance["statement"]["balanceado"] is True


def test_api_calculo_tributario(admin_client):
    respuesta = admin_client.post("/api/taxes/calculate", json={"base": 200.0, "tipo": "IVA_VENTAS"})
    datos = respuesta.get_json()
    assert datos["success"] is True
    assert datos["valor"] == pytest.approx(30.00, abs=0.01)

    error = admin_client.post("/api/taxes/calculate", json={"base": 100.0, "codigo": "NO-EXISTE"})
    assert error.status_code == 400
    assert error.get_json()["success"] is False


def test_api_historial_de_clientes_y_proveedores(admin_client):
    """Contrato que consumen las fichas/historiales de los módulos Clientes y Proveedores."""
    clientes = admin_client.get("/api/customers").get_json()["clientes"]
    cliente = next(c for c in clientes if c["id"] == 2)  # Supermercado San José (tiene ventas y cobros)
    historia = admin_client.get(f"/api/customers/{cliente['id']}/history").get_json()
    assert historia["success"] is True
    for clave in ("cliente", "ventas", "servicios", "cobros", "cuentas_cobrar"):
        assert clave in historia, f"Falta la clave '{clave}' en el historial del cliente"
    assert historia["cliente"]["id"] == cliente["id"]
    assert len(historia["ventas"]) >= 1
    assert len(historia["cobros"]) >= 1
    assert all("saldo_actual" in c and "estado" in c for c in historia["cuentas_cobrar"])

    proveedores = admin_client.get("/api/suppliers").get_json()["proveedores"]
    proveedor = next(p for p in proveedores if p["id"] == 1)  # Pronaca (tiene compras y pagos)
    historia = admin_client.get(f"/api/suppliers/{proveedor['id']}/history").get_json()
    assert historia["success"] is True
    for clave in ("proveedor", "compras", "pagos", "cuentas_pagar"):
        assert clave in historia, f"Falta la clave '{clave}' en el historial del proveedor"
    assert len(historia["compras"]) >= 1
    assert all("saldo_actual" in c and "estado" in c for c in historia["cuentas_pagar"])

    assert admin_client.get("/api/customers/9999/history").status_code == 404
    assert admin_client.get("/api/suppliers/9999/history").status_code == 404


def test_api_validacion_y_creacion_de_asiento(admin_client):
    cuentas = admin_client.get("/api/accounts").get_json()["accounts"]
    cuenta_caja = next(c for c in cuentas if c["codigo"] == "1.1.01")
    cuenta_ventas = next(c for c in cuentas if c["codigo"] == "4.1.01")

    desbalanceado = admin_client.post("/api/journal/validate", json={"lineas": [
        {"cuenta_id": cuenta_caja["id"], "debe": 100.0, "haber": 0.0},
        {"cuenta_id": cuenta_ventas["id"], "debe": 0.0, "haber": 90.0},
    ]}).get_json()
    assert desbalanceado["valid"] is False

    balanceado = admin_client.post("/api/journal/validate", json={"lineas": [
        {"cuenta_id": cuenta_caja["id"], "debe": 100.0, "haber": 0.0},
        {"cuenta_id": cuenta_ventas["id"], "debe": 0.0, "haber": 100.0},
    ]}).get_json()
    assert balanceado["valid"] is True

    creado = admin_client.post("/api/journal/create", json={
        "fecha": "2026-04-28", "glosa": "Asiento de prueba vía API",
        "lineas": [{"cuenta_id": cuenta_caja["id"], "debe": 50.0, "haber": 0.0},
                   {"cuenta_id": cuenta_ventas["id"], "debe": 0.0, "haber": 50.0}],
        "origen_modulo": "API"
    }).get_json()
    assert creado["success"] is True
    assert creado["data"]["numero_asiento"] > 0


def test_api_venta_crea_registros_completos(admin_client, db):
    respuesta = admin_client.post("/api/sales", json={
        "cliente_id": 3,
        "items": [{"producto_id": 13, "cantidad": 5, "precio_unitario": 1.65}],
        "forma_pago": "EFECTIVO"
    })
    datos = respuesta.get_json()
    assert datos["success"] is True, datos
    assert datos["data"]["total"] == pytest.approx(5 * 1.65 * 1.15, abs=0.02)


def test_api_error_controlado_en_venta_invalida(admin_client):
    respuesta = admin_client.post("/api/sales", json={"cliente_id": 999, "items": [{"producto_id": 1, "cantidad": 1}]})
    assert respuesta.status_code == 400
    assert "Cliente no encontrado" in respuesta.get_json()["error"]


# ---------------------------------------------------------------- Seguridad y roles
def test_rutas_protegidas_redirigen_al_login(app_client):
    respuesta = app_client.get("/dashboard")
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_modulo_administrativo_restringido_por_rol(estudiante_client):
    respuesta = estudiante_client.get("/admin/usuarios")
    assert respuesta.status_code == 403
    assert "Administrador" in respuesta.get_data(as_text=True)


def test_pagina_404_personalizada(app_client):
    respuesta = app_client.get("/ruta/que/no/existe")
    assert respuesta.status_code == 404
    cuerpo = respuesta.get_data(as_text=True)
    assert "/ruta/que/no/existe" in cuerpo


def test_login_con_credenciales_invalidas(app_client):
    respuesta = app_client.post("/login", data={"username": "admin", "password": "incorrecta"},
                                follow_redirects=True)
    assert "Credenciales incorrectas" in respuesta.get_data(as_text=True)


def test_contrasenas_almacenadas_con_hash(db):
    conn = get_db_connection(db)
    try:
        usuarios = conn.execute("SELECT username, password_hash FROM usuarios").fetchall()
    finally:
        conn.close()
    for u in usuarios:
        assert u["password_hash"] != "admin123"
        assert u["password_hash"].startswith(("pbkdf2:", "scrypt:"))


def test_registro_de_auditoria_guarda_trazabilidad(db):
    from services.audit_service import AuditService
    AuditService.log(1, "admin", "CREAR_VENTA", "VENTAS", "TEST-1", {"a": 1}, {"b": 2},
                     agente_utilizado="AgenteContable", herramienta_ejecutada="create_sale", db_path=db)
    logs = AuditService.get_logs(modulo="VENTAS", limit=10, db_path=db)
    assert len(logs) >= 1
    assert any(l["herramienta_ejecutada"] == "create_sale" for l in logs)
