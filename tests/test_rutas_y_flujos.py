"""
Pruebas de navegación y de los flujos completos de la interfaz:
recorre TODOS los módulos (GET) y registra operaciones reales por formulario (POST),
comprobando que los saldos y estados financieros se actualicen de forma coherente.
"""
import pytest

from models import get_db_connection
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from services.period_service import PeriodService


# ---------------------------------------------------------------- Navegación (GET)
RUTAS_GET = [
    "/dashboard",
    "/contabilidad/cuentas", "/contabilidad/diario", "/contabilidad/mayor",
    "/contabilidad/balance", "/contabilidad/ajustes", "/contabilidad/cierre",
    "/ventas", "/ventas/nueva", "/servicios", "/compras/", "/compras/nueva",
    "/inventarios/", "/inventarios/productos", "/inventarios/kardex", "/inventarios/kardex/1",
    "/inventarios/stock", "/clientes", "/proveedores", "/cuentas-cobrar", "/cuentas-pagar",
    "/caja", "/bancos", "/conciliacion", "/impuestos/", "/documentos/",
    "/estados-financieros/", "/estados-financieros/resultados", "/estados-financieros/flujo-efectivo",
    "/estados-financieros/situacion-financiera",
    "/simulador", "/evaluaciones", "/docente/panel", "/tutor/", "/reportes/",
    "/admin/", "/admin/usuarios", "/admin/impuestos", "/admin/auditoria",
    "/manual",
]


@pytest.mark.parametrize("ruta", RUTAS_GET)
def test_modulo_responde_correctamente(admin_client, ruta):
    respuesta = admin_client.get(ruta)
    assert respuesta.status_code == 200, f"{ruta} devolvió {respuesta.status_code}"
    cuerpo = respuesta.get_data(as_text=True)
    assert "Traceback" not in cuerpo
    assert len(cuerpo) > 500, f"{ruta} devolvió una página vacía"


def test_manual_de_usuario_disponible_y_descargable(app_client):
    """El manual se sirve dentro del sistema y su fuente Markdown es descargable."""
    pagina = app_client.get("/manual")
    assert pagina.status_code == 200
    cuerpo = pagina.get_data(as_text=True)
    for marcador in ["Manual de Usuario", "Simulador Integral de Sistema Contable",
                     "Requisitos e instalación", "Usuarios, contraseñas y roles",
                     "Solución de problemas", "Glosario"]:
        assert marcador in cuerpo, f"Falta la sección: {marcador}"
    # El manual es público: se puede consultar antes de iniciar sesión.
    assert b"Traceback" not in pagina.data

    fuente = app_client.get("/manual/fuente")
    assert fuente.status_code == 200
    assert "attachment" in fuente.headers["Content-Disposition"]
    assert "MANUAL_DE_USUARIO.md" in fuente.headers["Content-Disposition"]
    assert b"# Manual de Usuario" in fuente.data


def test_inicio_publico_para_usuario_anonimo(app_client):
    assert app_client.get("/").status_code == 200
    assert app_client.get("/login").status_code == 200


def test_inicio_y_login_redirigen_a_usuario_autenticado(admin_client):
    assert admin_client.get("/").status_code == 302
    assert admin_client.get("/login").status_code == 302


def test_auditor_puede_consultar_libros_y_trazabilidad(app_client):
    app_client.post("/login", data={"username": "auditor", "password": "auditor123"}, follow_redirects=True)
    for ruta in ["/contabilidad/diario", "/contabilidad/mayor", "/estados-financieros/",
                 "/documentos/", "/admin/auditoria"]:
        assert app_client.get(ruta).status_code == 200
    # El rol Auditor no puede administrar usuarios
    assert app_client.get("/admin/usuarios").status_code == 403


# ---------------------------------------------------------------- Flujos por formulario
def _saldos(db):
    return {
        "caja": AccountingService.get_account_balance(3, db_path=db),
        "banco1": AccountingService.get_account_balance(4, db_path=db),
        "banco2": AccountingService.get_account_balance(5, db_path=db),
        "cxc": AccountingService.get_account_balance(6, db_path=db),
        "inventario": AccountingService.get_account_balance(8, db_path=db),
        "iva_compras": AccountingService.get_account_balance(9, db_path=db),
        "cxp": AccountingService.get_account_balance(20, db_path=db),
        "iva_ventas": AccountingService.get_account_balance(21, db_path=db),
        "ventas": AccountingService.get_account_balance(31, db_path=db),
        "servicios": AccountingService.get_account_balance(32, db_path=db),
    }


def test_flujo_venta_compra_servicio_cobro_y_pago_por_interfaz(admin_client, db):
    antes = _saldos(db)
    stock_harina = InventoryService.get_product(5, db_path=db)["stock_actual"]

    # 1) Venta de contado en efectivo
    respuesta = admin_client.post("/ventas/nueva", data={
        "cliente_id": "3", "forma_pago": "EFECTIVO", "metodo_kardex": "PROMEDIO",
        "producto_id[]": ["5"], "cantidad[]": ["20"], "precio[]": ["1.30"], "descuento[]": ["0"],
    }, follow_redirects=True)
    assert "emitida y contabilizada correctamente" in respuesta.get_data(as_text=True)

    # 2) Compra a crédito (aumenta inventario y cuentas por pagar)
    respuesta = admin_client.post("/compras/nueva", data={
        "proveedor_id": "6", "numero_factura": "FAC-UI-0001", "forma_pago": "CREDITO", "dias_credito": "30",
        "producto_id[]": ["5"], "cantidad[]": ["100"], "costo[]": ["0.85"], "descuento[]": ["0"],
    }, follow_redirects=True)
    assert "registrada" in respuesta.get_data(as_text=True)

    # 3) Servicio facturado por transferencia
    respuesta = admin_client.post("/servicios", data={
        "cliente_id": "4", "servicio_id": "1", "cantidad": "2", "tarifa": "45",
        "descripcion": "Servicio de logística de prueba", "forma_pago": "TRANSFERENCIA", "banco_id": "1",
    }, follow_redirects=True)
    assert "registrada y contabilizada" in respuesta.get_data(as_text=True)

    despues = _saldos(db)

    assert despues["caja"] > antes["caja"], "La venta de contado debe aumentar la caja"
    assert despues["cxp"] > antes["cxp"], "La compra a crédito debe aumentar las cuentas por pagar"
    assert despues["inventario"] > antes["inventario"], "La compra debe aumentar el inventario"
    assert despues["banco1"] > antes["banco1"], "El servicio por transferencia debe aumentar el banco"
    assert despues["ventas"] > antes["ventas"]
    assert despues["servicios"] > antes["servicios"]
    assert InventoryService.get_product(5, db_path=db)["stock_actual"] == pytest.approx(
        stock_harina + 100 - 20, abs=0.01)

    # 4) Cobro de cartera por interfaz
    conn = get_db_connection(db)
    try:
        cxc = conn.execute("""
            SELECT * FROM cuentas_cobrar WHERE estado IN ('PENDIENTE','PARCIAL')
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        cxp = conn.execute("""
            SELECT * FROM cuentas_pagar WHERE estado IN ('PENDIENTE','PARCIAL')
            ORDER BY id DESC LIMIT 1
        """).fetchone()
    finally:
        conn.close()

    monto_cobro = round(cxc["saldo_actual"] / 2, 2)
    respuesta = admin_client.post("/cuentas-cobrar", data={
        "cuenta_cobrar_id": str(cxc["id"]), "monto": str(monto_cobro),
        "medio_pago": "TRANSFERENCIA", "banco_id": "1", "numero_comprobante": "CI-UI-001",
    }, follow_redirects=True)
    assert "registrado exitosamente" in respuesta.get_data(as_text=True)

    monto_pago = round(cxp["saldo_actual"] / 2, 2)
    respuesta = admin_client.post("/cuentas-pagar", data={
        "cuenta_pagar_id": str(cxp["id"]), "monto": str(monto_pago),
        "medio_pago": "TRANSFERENCIA", "banco_id": "1", "numero_comprobante": "CE-UI-001",
    }, follow_redirects=True)
    assert "procesado" in respuesta.get_data(as_text=True)

    conn = get_db_connection(db)
    try:
        cxc_despues = conn.execute("SELECT saldo_actual, estado FROM cuentas_cobrar WHERE id = ?",
                                   (cxc["id"],)).fetchone()
        cxp_despues = conn.execute("SELECT saldo_actual, estado FROM cuentas_pagar WHERE id = ?",
                                   (cxp["id"],)).fetchone()
    finally:
        conn.close()

    assert cxc_despues["saldo_actual"] == pytest.approx(cxc["saldo_actual"] - monto_cobro, abs=0.01)
    assert cxp_despues["saldo_actual"] == pytest.approx(cxp["saldo_actual"] - monto_pago, abs=0.01)

    # La integridad contable se mantiene después de todo el flujo
    trial = AccountingService.get_trial_balance(db_path=db)
    bs = AccountingService.get_balance_sheet(db_path=db)
    assert trial["cuadrado_sumas"] and trial["cuadrado_saldos"]
    assert bs["balanceado"] is True


def test_flujo_tesoreria_arqueo_movimientos_y_conciliacion(admin_client, db):
    saldo_caja = AccountingService.get_account_balance(3, db_path=db)

    # Arqueo con faltante: detecta la diferencia y la reporta (aún sin ajuste contable)
    respuesta = admin_client.post("/caja", data={
        "caja_id": "1", "saldo_fisico": str(round(saldo_caja - 4.00, 2)),
        "observaciones": "Arqueo de prueba por interfaz",
    }, follow_redirects=True)
    cuerpo = respuesta.get_data(as_text=True)
    assert "FALTANTE" in cuerpo or "faltante" in cuerpo
    assert AccountingService.get_account_balance(3, db_path=db) == pytest.approx(saldo_caja, abs=0.02)

    conn = get_db_connection(db)
    try:
        arqueo = conn.execute("SELECT * FROM arqueos_caja ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    assert arqueo["asiento_ajuste_id"] is None

    # Regularización contable del faltante (genera el asiento y lo vincula al arqueo)
    respuesta = admin_client.post(f"/caja/regularizar/{arqueo['id']}", follow_redirects=True)
    assert "regularizada mediante el asiento" in respuesta.get_data(as_text=True)
    assert AccountingService.get_account_balance(3, db_path=db) == pytest.approx(saldo_caja - 4.00, abs=0.02)

    conn = get_db_connection(db)
    try:
        arqueo = conn.execute("SELECT * FROM arqueos_caja WHERE id = ?", (arqueo["id"],)).fetchone()
    finally:
        conn.close()
    assert arqueo["asiento_ajuste_id"] is not None

    # Movimiento de caja (ingreso)
    saldo_caja = AccountingService.get_account_balance(3, db_path=db)
    respuesta = admin_client.post("/caja/movimiento", data={
        "caja_id": "1", "tipo_movimiento": "INGRESO", "monto": "150.00",
        "concepto": "Ingreso de prueba", "numero_comprobante": "CI-CAJA-01",
    }, follow_redirects=True)
    assert "Movimiento de caja registrado" in respuesta.get_data(as_text=True)
    assert AccountingService.get_account_balance(3, db_path=db) == pytest.approx(saldo_caja + 150.00, abs=0.05)

    # Movimiento bancario (depósito)
    saldo_banco = AccountingService.get_account_balance(4, db_path=db)
    respuesta = admin_client.post("/bancos/movimiento", data={
        "banco_id": "1", "tipo_movimiento": "DEPOSITO", "monto": "500.00",
        "concepto": "Depósito de prueba", "numero_referencia": "DEP-UI-01",
    }, follow_redirects=True)
    assert "Movimiento bancario registrado" in respuesta.get_data(as_text=True)
    assert AccountingService.get_account_balance(4, db_path=db) == pytest.approx(saldo_banco + 500.00, abs=0.05)

    # Conciliación bancaria exacta
    saldo_libros = AccountingService.get_account_balance(4, db_path=db)
    respuesta = admin_client.post("/conciliacion", data={
        "banco_id": "1", "periodo_id": "1", "fecha_corte": "2026-04-30",
        "saldo_extracto": str(saldo_libros), "depositos_transito": "0", "cheques_transito": "0",
        "notas_debito": "0", "notas_credito": "0", "observaciones": "Conciliación de prueba",
    }, follow_redirects=True)
    assert "sin diferencias" in respuesta.get_data(as_text=True)


def test_flujo_asiento_manual_ajuste_y_reversion(admin_client, db):
    cuentas = {c["codigo"]: c["id"] for c in AccountingService.get_accounts(db_path=db)}
    saldo_caja = AccountingService.get_account_balance(3, db_path=db)

    # Asiento manual balanceado
    respuesta = admin_client.post("/contabilidad/diario", data={
        "fecha": "2026-04-29", "glosa": "Aporte de capital adicional de prueba",
        "tipo_documento": "DOCUMENTO_INTERNO", "numero_documento": "DOC-UI-01",
        "cuenta_id[]": [str(cuentas["1.1.01"]), str(cuentas["3.1.01"])],
        "debe[]": ["1000", "0"], "haber[]": ["0", "1000"],
        "referencia[]": ["Ingreso a caja", "Aporte de capital"],
    }, follow_redirects=True)
    assert "registrado exitosamente" in respuesta.get_data(as_text=True)
    assert AccountingService.get_account_balance(3, db_path=db) == pytest.approx(saldo_caja + 1000.00, abs=0.02)

    # Asiento descuadrado: debe rechazarse con mensaje explicativo
    respuesta = admin_client.post("/contabilidad/diario", data={
        "fecha": "2026-04-29", "glosa": "Asiento descuadrado de prueba",
        "cuenta_id[]": [str(cuentas["1.1.01"]), str(cuentas["3.1.01"])],
        "debe[]": ["500", "0"], "haber[]": ["0", "450"],
    }, follow_redirects=True)
    cuerpo = respuesta.get_data(as_text=True)
    assert "no cuadra" in cuerpo and "Diferencia" in cuerpo

    # Ajuste de depreciación por interfaz
    respuesta = admin_client.post("/contabilidad/ajustes", data={
        "tipo_ajuste": "DEPRECIACION", "glosa": "Depreciación de prueba",
        "monto": "300.00", "fecha": "2026-04-30",
    }, follow_redirects=True)
    assert "registrado y mayorizado" in respuesta.get_data(as_text=True)

    # Reversión de un asiento
    conn = get_db_connection(db)
    try:
        asiento = conn.execute("""
            SELECT id FROM asientos WHERE glosa LIKE 'Aporte de capital adicional%' AND estado = 'CONTABILIZADO'
        """).fetchone()
    finally:
        conn.close()
    respuesta = admin_client.post(f"/contabilidad/diario/{asiento['id']}/revertir",
                                  data={"motivo": "Anulación de prueba"}, follow_redirects=True)
    assert "revertido con éxito" in respuesta.get_data(as_text=True)

    trial = AccountingService.get_trial_balance(db_path=db)
    assert trial["cuadrado_sumas"] and trial["cuadrado_saldos"]
    assert AccountingService.get_balance_sheet(db_path=db)["balanceado"] is True


def test_flujo_simulador_completo_con_tutor(estudiante_client, db):
    # Iniciar una simulación
    respuesta = estudiante_client.get("/simulador/1/iniciar", follow_redirects=True)
    assert respuesta.status_code == 200

    conn = get_db_connection(db)
    try:
        intento = conn.execute("""
            SELECT i.* FROM intentos_estudiante i ORDER BY i.id DESC LIMIT 1
        """).fetchone()
        caso = conn.execute("""
            SELECT * FROM casos_simulacion WHERE simulacion_id = ? ORDER BY orden LIMIT 1
        """, (intento["simulacion_id"],)).fetchone()
    finally:
        conn.close()

    # Página de juego del caso
    respuesta = estudiante_client.get(f"/simulador/{intento['simulacion_id']}/jugar?intento_id={intento['id']}")
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert caso["titulo"][:20] in cuerpo
    assert "simLinesBody" in cuerpo  # integración con static/js/simulation.js

    # Pista del Tutor IA
    pista = estudiante_client.post("/tutor/preguntar", json={
        "pregunta": "¿Por qué se debita la cuenta de caja?",
        "nivel_ayuda": "PISTA",
        "context": {"caso_id": caso["id"]},
    }).get_json()
    assert pista.get("respuesta")
    assert pista.get("agente")

    # Enviar la solución correcta y verificar la evaluación
    import json as _json
    solucion = _json.loads(caso["solucion_esperada_json"])
    lineas = []
    for bloque in ("asiento", "asiento_venta", "asiento_costo"):
        for l in solucion.get(bloque, []):
            cuenta = AccountingService.get_account_by_code(l["cuenta"], db_path=db)
            lineas.append({"cuenta_id": cuenta["id"], "debe": l["debe"], "haber": l["haber"]})

    evaluacion = estudiante_client.post("/simulador/evaluar", json={
        "intento_id": intento["id"], "caso_id": caso["id"], "lineas": lineas,
        "pistas_usadas": 1, "tiempo_segundos": 90,
    }).get_json()
    assert evaluacion["success"] is True
    assert evaluacion["evaluacion"]["puntuacion"] >= 80
    assert "Fundamento Teórico" in evaluacion["evaluacion"]["retroalimentacion"]


def test_exportaciones_csv_excel_e_impresion(admin_client):
    tipos = ["diario", "mayor", "balance", "ventas", "compras", "servicios", "inventario", "kardex",
             "caja", "bancos", "cartera", "cuentas-pagar", "resultados", "situacion-financiera",
             "flujo-efectivo", "academico"]

    for tipo in tipos:
        csv_resp = admin_client.get(f"/reportes/exportar/csv/{tipo}")
        assert csv_resp.status_code == 200, tipo
        assert "attachment" in csv_resp.headers["Content-Disposition"]
        assert len(csv_resp.data) > 40

        excel_resp = admin_client.get(f"/reportes/exportar/excel/{tipo}")
        assert excel_resp.status_code == 200, tipo
        assert excel_resp.data[:2] == b"PK", "El archivo Excel debe ser un XLSX válido"

        print_resp = admin_client.get(f"/reportes/imprimible/{tipo}")
        assert print_resp.status_code == 200
        assert "NUEVA ESPERANZA" in print_resp.get_data(as_text=True)

    assert admin_client.get("/reportes/exportar/csv/no-existe").status_code == 404


def test_panel_administrativo_actualiza_parametros(admin_client, db):
    respuesta = admin_client.post("/admin", data={
        "fecha_trabajo": "2026-04-20",
        "razon_social": "Comercial y Servicios Nueva Esperanza S.A.",
        "nombre_comercial": "Comercial y Servicios Nueva Esperanza",
        "ruc": "1792345678001",
        "direccion": "Av. Amazonas N34-120 y Naciones Unidas, Quito",
        "telefono": "02-2987-654",
        "email": "info@nuevaesperanza.com.ec",
        "actividad_comercial": "Comercialización de productos de primera necesidad",
        "actividad_servicios": "Prestación de servicios de logística y asesoría",
        "metodo_kardex_defecto": "FIFO",
    }, follow_redirects=True)
    assert "actualizados correctamente" in respuesta.get_data(as_text=True)
    assert PeriodService.get_fecha_trabajo(db_path=db) == "2026-04-20"

    conn = get_db_connection(db)
    try:
        empresa = conn.execute("SELECT metodo_kardex_defecto FROM empresas WHERE id = 1").fetchone()
    finally:
        conn.close()
    assert empresa["metodo_kardex_defecto"] == "FIFO"

    # Fecha inválida: se rechaza con mensaje
    respuesta = admin_client.post("/admin", data={
        "fecha_trabajo": "2026-12-31", "razon_social": "X", "ruc": "1",
    }, follow_redirects=True)
    assert "fuera del periodo" in respuesta.get_data(as_text=True)
    assert PeriodService.get_fecha_trabajo(db_path=db) == "2026-04-20"


def test_creacion_de_usuario_y_parametro_tributario(admin_client, db):
    respuesta = admin_client.post("/admin/usuarios", data={
        "username": "estudiante2", "password": "claveSegura123",
        "nombre_completo": "Luis Fernando Castro - Estudiante", "email": "lcastro@estudiantes.edu.ec",
        "rol_id": "3",
    }, follow_redirects=True)
    assert "creado exitosamente" in respuesta.get_data(as_text=True)

    conn = get_db_connection(db)
    try:
        nuevo = conn.execute("SELECT * FROM usuarios WHERE username = 'estudiante2'").fetchone()
    finally:
        conn.close()
    assert nuevo is not None and nuevo["password_hash"] != "claveSegura123"

    respuesta = admin_client.post("/admin/impuestos", data={
        "impuesto_id": "1", "nombre": "IVA 15% en Ventas (ajustado)", "porcentaje": "15",
        "tipo": "IVA_VENTAS", "cuenta_contable_id": "21", "activo": "1",
    }, follow_redirects=True)
    assert "actualizado correctamente" in respuesta.get_data(as_text=True)


def test_pagina_de_inicio_publica_muestra_indicadores(app_client, db):
    respuesta = app_client.get("/")
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "Simulador Integral de Sistema Contable" in cuerpo
    assert "Iniciar simulación" in cuerpo
    assert "Ir al sistema contable" in cuerpo
    assert "Ver mis resultados" in cuerpo
    # Los indicadores provienen de SQLite (no son valores fijos)
    assert "$" in cuerpo
