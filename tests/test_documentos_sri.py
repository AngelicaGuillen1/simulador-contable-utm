# -*- coding: utf-8 -*-
"""Pruebas del módulo de Documentos del SRI.

Comprueban que el catálogo normativo se lee como DATOS de cada base, que las validaciones del
Reglamento de comprobantes de venta, retención y documentos complementarios se aplican de verdad
al emitir un comprobante, y que la emisión, el listado, el detalle y la anulación funcionan por la
interfaz web.
"""
import json
import sqlite3
from datetime import date, timedelta

import pytest

from database.parametros_tributarios_sri import aplicar as aplicar_catalogo_tributario
from services.document_service import DocumentService, PARAMETROS_DOCUMENTO


@pytest.fixture()
def db_sri(db):
    """Copia de la base demostrativa con el catálogo tributario oficial del SRI aplicado."""
    aplicar_catalogo_tributario(db, verboso=False)
    return db

LEYENDA_ESPERADA = "DOCUMENTO PARA USO EDUCATIVO (SIN VALIDEZ COMERCIAL)"

TIPOS_ESPERADOS = [
    "ACTA_PET", "ACTA_VEHICULOS_USADOS", "BOLETO_ESPECTACULO", "COMPROBANTE_RETENCION", "FACTURA",
    "FACTURA_SERVICIOS_TURISTICOS", "FACTURA_TRANSPORTE", "GUIA_REMISION", "LIQUIDACION_COMPRA",
    "LIQUIDACION_VEHICULOS_USADOS", "NOTA_CREDITO", "NOTA_DEBITO", "NOTA_VENTA_RISE",
    "TIQUETE_MAQUINA",
]


# ------------------------------------------------------------------------------- utilidades
def _hallazgos(lista, codigo):
    """Mensajes que provienen de una regla concreta (van rotulados con su código)."""
    return [m for m in lista if m.startswith("[%s]" % codigo)]


def _sumar_dias_habiles(fecha_iso, dias):
    """Suma días hábiles (lunes a viernes) a una fecha ISO."""
    actual = date.fromisoformat(fecha_iso)
    pendientes = dias
    while pendientes > 0:
        actual += timedelta(days=1)
        if actual.weekday() < 5:
            pendientes -= 1
    return actual.isoformat()


def _datos_factura(**cambios):
    """Factura completa y válida según el reglamento (el punto de partida de las pruebas)."""
    datos = {
        "fecha": "2026-04-20",
        "numero_autorizacion": "110620260001234567890123456789012345678901234567890123A",
        "fecha_autorizacion": "2026-01-02",
        "fecha_caducidad_autorizacion": "2027-01-01",
        "establecimiento": "001",
        "punto_emision": "002",
        "secuencial": "000000123",
        "tipo_emision": "NORMAL",
        "ruc_emisor": "1792345678001",
        "emisor": "Comercial y Servicios Nueva Esperanza S.A.",
        "adquirente_tipo_id": "RUC",
        "adquirente_identificacion": "1790012345001",
        "adquirente_nombre": "Distribuidora Andina Cía. Ltda.",
        "forma_pago": "EFECTIVO",
        "subtotal": "100.00",
        "iva_tarifa": "15",
        "iva_valor": "15.00",
        "monto_total": "115.00",
        "descripcion": "Venta de mercadería según pedido 001",
    }
    datos.update(cambios)
    return datos


def _fila_documento(db, doc_id):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        fila = conn.execute("SELECT * FROM documentos_fuente WHERE id = ?", (doc_id,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


# ------------------------------------------------------- 1. Catálogo normativo como datos
def test_catalogo_tipos_reglas_y_agrupacion(db):
    """El catálogo trae los 14 tipos y las 23 reglas, agrupados por categoría."""
    catalogo = DocumentService.catalogo(db_path=db)
    assert len(catalogo) == 14
    assert sorted(t["codigo"] for t in catalogo) == TIPOS_ESPERADOS

    reglas = DocumentService.reglas(db_path=db)
    assert len(reglas) == 23
    assert [r["codigo"] for r in reglas][:3] == ["R-57.1", "R-57.10", "R-57.11"]
    assert {r["severidad"] for r in reglas} <= {"BLOQUEO", "ADVERTENCIA", "INFORMATIVA"}

    agrupado = DocumentService.catalogo(agrupado_por_categoria=True, db_path=db)
    assert sum(len(tipos) for tipos in agrupado.values()) == 14
    assert set(agrupado) == {"COMPROBANTE_VENTA", "COMPLEMENTARIO", "RETENCION", "DOCUMENTO_SOPORTE"}
    assert len(agrupado["COMPROBANTE_VENTA"]) == 8
    assert len(agrupado["DOCUMENTO_SOPORTE"]) == 2

    # Cada tipo trae sus campos y las reglas que le aplican.
    factura = DocumentService.tipo_documento("FACTURA", db_path=db)
    assert factura["nombre"] == "Factura"
    assert len(factura["campos_llenado"]) >= 10
    assert factura["campos_preimpresos"] and factura["requisitos"]
    reglas_factura = [r["codigo"] for r in factura["reglas"]]
    assert "R-57.1" in reglas_factura and "R-57.7" in reglas_factura
    # R-57.7 aplica solo a la factura; las reglas "TODO" aplican a todos.
    guia = DocumentService.tipo_documento("GUIA_REMISION", db_path=db)
    assert "R-57.7" not in [r["codigo"] for r in guia["reglas"]]
    assert "R-57.19" in [r["codigo"] for r in guia["reglas"]]
    assert "R-57.2" in [r["codigo"] for r in guia["reglas"]]


# -------------------------------------------- 2. Autorización de impresión obligatoria
def test_factura_sin_autorizacion_se_rechaza(db):
    datos = _datos_factura(numero_autorizacion="")
    ok, errores, _advertencias = DocumentService.validar_documento("FACTURA", datos, db_path=db)
    assert ok is False
    assert len(_hallazgos(errores, "R-57.1")) == 1
    mensaje = _hallazgos(errores, "R-57.1")[0]
    assert "autorización" in mensaje.lower()
    assert len(mensaje) > 60, "el mensaje debe explicarle al estudiante qué falta y por qué"

    with pytest.raises(ValueError) as error:
        DocumentService.emitir_documento("FACTURA", datos, db_path=db)
    assert "R-57.1" in str(error.value)
    assert "no se emitió" in str(error.value)


# ----------------------------------------------------------------- 3. Numeración 3-3-9
def test_factura_con_numeracion_incorrecta_se_rechaza(db):
    ok, errores, _ = DocumentService.validar_documento(
        "FACTURA", _datos_factura(punto_emision="02"), db_path=db)
    assert ok is False
    assert _hallazgos(errores, "R-57.2")

    ok, errores, _ = DocumentService.validar_documento(
        "FACTURA", _datos_factura(secuencial="123"), db_path=db)
    assert ok is False and _hallazgos(errores, "R-57.2")

    # La numeración correcta (con o sin guiones) pasa la regla.
    ok, errores, _ = DocumentService.validar_documento(
        "FACTURA", _datos_factura(secuencial="000000123"), db_path=db)
    assert not _hallazgos(errores, "R-57.2")

    sin_guiones = _datos_factura(establecimiento="", punto_emision="", secuencial="",
                                 numero_completo="001002000000123")
    ok, errores, _ = DocumentService.validar_documento("FACTURA", sin_guiones, db_path=db)
    assert not _hallazgos(errores, "R-57.2"), "el patrón admite guiones opcionales"


# --------------------------------------------- 4. Tope de la factura a consumidor final
def test_factura_a_consumidor_final_con_tope_configurable(db):
    caro = _datos_factura(adquirente_tipo_id="CONSUMIDOR_FINAL", adquirente_identificacion="",
                          adquirente_nombre="Consumidor final", subtotal="250.00",
                          iva_valor="", iva_tarifa="", monto_total="250.00")
    ok, errores, _ = DocumentService.validar_documento("FACTURA", caro, db_path=db)
    assert ok is False
    assert _hallazgos(errores, "R-57.7")
    assert "200" in _hallazgos(errores, "R-57.7")[0]
    assert "250" in _hallazgos(errores, "R-57.7")[0]

    barato = dict(caro, subtotal="150.00", monto_total="150.00")
    ok, errores, _ = DocumentService.validar_documento("FACTURA", barato, db_path=db)
    assert ok is True
    assert not _hallazgos(errores, "R-57.7")

    # El tope es DATO CONFIGURABLE: se puede subir en la tabla `parametros`.
    conn = sqlite3.connect(db)
    try:
        conn.execute("INSERT OR REPLACE INTO parametros (clave, valor, descripcion) VALUES (?,?,?)",
                     ("sri.tope_consumidor_final", "300", "Tope de factura a consumidor final"))
        conn.commit()
    finally:
        conn.close()
    parametros = DocumentService.parametros_efectivos(db_path=db)
    assert float(parametros["tope_consumidor_final"]) == 300.0
    ok, errores, _ = DocumentService.validar_documento("FACTURA", caro, db_path=db)
    assert ok is True and not _hallazgos(errores, "R-57.7")


# ------------------------------------------------- 5. Notas de crédito y débito
def test_nota_credito_exige_comprobante_y_motivo(db):
    sin_referencia = _datos_factura(documento_modificado="", motivo_modificacion="")
    ok, errores, _ = DocumentService.validar_documento("NOTA_CREDITO", sin_referencia, db_path=db)
    assert ok is False
    assert len(_hallazgos(errores, "R-57.16")) == 2

    con_referencia = _datos_factura(
        documento_modificado="FACTURA 001-002-000000123",
        motivo_modificacion="Devolución de mercadería defectuosa",
        valor_modificacion="23.00")
    ok, errores, _ = DocumentService.validar_documento("NOTA_CREDITO", con_referencia, db_path=db)
    assert ok is True
    assert not _hallazgos(errores, "R-57.16")

    # La nota de débito tiene la misma exigencia.
    ok, errores, _ = DocumentService.validar_documento("NOTA_DEBITO", sin_referencia, db_path=db)
    assert ok is False and _hallazgos(errores, "R-57.16")


# ------------------------------------------------------------ 6. Guía de remisión
def test_guia_remision_se_emite_antes_del_traslado(db):
    tarde = _datos_factura(fecha="2026-04-22", fecha_inicio_traslado="2026-04-20",
                           motivo_traslado="Venta", direccion_partida="Quito, bodega matriz",
                           direccion_destino="Guayaquil, cliente final",
                           transportista="Juan Pérez (conductor)", placa_vehiculo="ABC-1234")
    ok, errores, _ = DocumentService.validar_documento("GUIA_REMISION", tarde, db_path=db)
    assert ok is False
    assert _hallazgos(errores, "R-57.19")

    a_tiempo = dict(tarde, fecha="2026-04-19")
    ok, errores, _ = DocumentService.validar_documento("GUIA_REMISION", a_tiempo, db_path=db)
    assert ok is True and not _hallazgos(errores, "R-57.19")

    # Faltan motivo, destino, conductor y placa: la guía no puede emitirse.
    incompleta = dict(a_tiempo, motivo_traslado="", direccion_destino="", transportista="",
                      placa_vehiculo="")
    ok, errores, _ = DocumentService.validar_documento("GUIA_REMISION", incompleta, db_path=db)
    assert ok is False
    assert _hallazgos(errores, "R-57.19")


# ------------------------------------------- 7. Plazo del comprobante de retención
def test_plazo_del_comprobante_de_retencion(db):
    base = "2026-06-01"
    assert date.fromisoformat(base).weekday() == 0, "la prueba necesita un lunes como punto de partida"

    a_tiempo = _datos_factura(fecha=_sumar_dias_habiles(base, 3),
                              impuesto_retenido="RENTA", base_retencion="100.00",
                              porcentaje_retencion="2", valor_retenido="2.00",
                              fecha_comprobante_venta=base,
                              fecha_entrega_retencion=_sumar_dias_habiles(base, 3))
    ok, errores, _ = DocumentService.validar_documento("COMPROBANTE_RETENCION", a_tiempo, db_path=db)
    assert ok is True, errores
    assert not _hallazgos(errores, "R-57.12")

    tarde = dict(a_tiempo, fecha=_sumar_dias_habiles(base, 6),
                 fecha_entrega_retencion=_sumar_dias_habiles(base, 6))
    ok, errores, _ = DocumentService.validar_documento("COMPROBANTE_RETENCION", tarde, db_path=db)
    assert ok is False
    assert _hallazgos(errores, "R-57.12")

    # Al cuarto día hábil todavía se puede emitir, pero con advertencia.
    aviso = dict(a_tiempo, fecha=_sumar_dias_habiles(base, 4),
                 fecha_entrega_retencion=_sumar_dias_habiles(base, 4))
    ok, errores, advertencias = DocumentService.validar_documento(
        "COMPROBANTE_RETENCION", aviso, db_path=db)
    assert ok is True
    assert _hallazgos(advertencias, "R-57.12")

    # Con ISD el plazo se reduce a 2 días hábiles.
    isd_tarde = dict(a_tiempo, impuesto_retenido="ISD", fecha=_sumar_dias_habiles(base, 3),
                     fecha_entrega_retencion=_sumar_dias_habiles(base, 3))
    ok, errores, _ = DocumentService.validar_documento(
        "COMPROBANTE_RETENCION", isd_tarde, db_path=db)
    assert ok is False and _hallazgos(errores, "R-57.12")


# ------------------------------- 8. Retención del 100 % del IVA en liquidaciones de compra
def test_liquidacion_de_compra_exige_retencion_total_del_iva(db):
    sin_iva = _datos_factura(impuesto_retenido="RENTA", base_retencion="100.00",
                             porcentaje_retencion="1.75", valor_retenido="1.75")
    ok, errores, _ = DocumentService.validar_documento("LIQUIDACION_COMPRA", sin_iva, db_path=db)
    assert ok is False
    assert _hallazgos(errores, "R-57.14")

    parcial = dict(sin_iva, impuesto_retenido="IVA", porcentaje_retencion="30",
                   valor_retenido="4.50")
    ok, errores, _ = DocumentService.validar_documento("LIQUIDACION_COMPRA", parcial, db_path=db)
    assert ok is False and _hallazgos(errores, "R-57.14")

    correcta = dict(sin_iva, impuesto_retenido="IVA", porcentaje_retencion="100",
                    valor_retenido="15.00")
    ok, errores, _ = DocumentService.validar_documento("LIQUIDACION_COMPRA", correcta, db_path=db)
    assert ok is True and not _hallazgos(errores, "R-57.14")


# ------------------------------------------ 9. Emisión y anulación (nunca borrado físico)
def test_emitir_y_anular_conserva_la_fila_y_la_leyenda(db):
    datos = _datos_factura(secuencial="000000777")
    documento = DocumentService.emitir_documento("FACTURA", datos, db_path=db)

    assert documento["id"]
    assert documento["estado"] == "EMITIDO"
    assert documento["numero_completo"] == "001-002-000000777"
    assert documento["numero"] == "001-002-000000777"
    assert documento["monto_total"] == pytest.approx(115.00)
    assert documento["adquirente_nombre"] == "Distribuidora Andina Cía. Ltda."
    assert documento["tipo"] == "FACTURA"

    contenido = json.loads(documento["datos_json"])
    assert contenido["leyenda_educativa"] == LEYENDA_ESPERADA
    assert contenido["desglose"]["total"] == pytest.approx(115.00)
    assert "R-57.1" in contenido["reglas_aplicadas"] and "R-57.23" in contenido["reglas_aplicadas"]

    fila = _fila_documento(db, documento["id"])
    assert fila is not None and fila["estado"] == "EMITIDO"
    assert json.loads(fila["datos_json"])["leyenda_educativa"] == LEYENDA_ESPERADA

    # Sin motivo no se anula.
    with pytest.raises(ValueError):
        DocumentService.anular_documento(documento["id"], "   ", db_path=db)

    anulado = DocumentService.anular_documento(documento["id"], "Error en el valor facturado",
                                               db_path=db)
    assert anulado["estado"] == "ANULADO"
    motivo = json.loads(anulado["datos_json"])["anulacion"]["motivo"]
    assert motivo == "Error en el valor facturado"

    fila = _fila_documento(db, documento["id"])
    assert fila is not None, "la fila nunca se elimina: solo cambia de estado"
    assert fila["estado"] == "ANULADO"
    assert json.loads(fila["datos_json"])["anulacion"]["motivo"] == "Error en el valor facturado"

    # Una segunda anulación se rechaza con un mensaje claro.
    with pytest.raises(ValueError):
        DocumentService.anular_documento(documento["id"], "otra vez", db_path=db)


# ------------------------------------------------- 10. Interfaz: listado, detalle, emisión
def test_listado_detalle_y_emision_por_interfaz(admin_client, db):
    documento = DocumentService.emitir_documento(
        "FACTURA", _datos_factura(secuencial="000000888"), db_path=db)

    listado = admin_client.get("/documentos/?numero=000000888")
    assert listado.status_code == 200
    cuerpo = listado.get_data(as_text=True)
    assert "001-002-000000888" in cuerpo
    assert "EMITIDO" in cuerpo
    assert "Traceback" not in cuerpo

    detalle = admin_client.get("/documentos/%s" % documento["id"])
    assert detalle.status_code == 200
    cuerpo = detalle.get_data(as_text=True)
    assert "001-002-000000888" in cuerpo
    assert "EMITIDO" in cuerpo
    assert LEYENDA_ESPERADA in cuerpo
    assert "Reglas del reglamento aplicadas" in cuerpo

    detalle_json = admin_client.get("/documentos/%s?formato=json" % documento["id"]).get_json()
    assert detalle_json["success"] is True
    assert detalle_json["documento"]["numero_completo"] == "001-002-000000888"
    assert detalle_json["leyenda_educativa"] == LEYENDA_ESPERADA
    assert detalle_json["revision"]["ok"] is True

    assert admin_client.get("/documentos/catalogo").status_code == 200
    assert admin_client.get("/documentos/catalogo?formato=json").get_json()["total_tipos"] == 14
    assert admin_client.get("/documentos/nuevo?tipo=FACTURA").status_code == 200
    assert admin_client.get("/documentos/soporte?tipo=COMPRA_BIENES").status_code == 200
    assert admin_client.get("/documentos/").status_code == 200

    # Emisión por formulario: primero un intento que incumple y luego uno correcto.
    rechazado = admin_client.post("/documentos/nuevo", data=dict(
        _datos_factura(numero_autorizacion="", secuencial="000000889"), tipo="FACTURA"),
        follow_redirects=True)
    assert rechazado.status_code == 200
    assert "no se emitió" in rechazado.get_data(as_text=True)

    aceptado = admin_client.post("/documentos/nuevo", data=dict(
        _datos_factura(secuencial="000000890"), tipo="FACTURA"), follow_redirects=True)
    assert aceptado.status_code == 200
    cuerpo = aceptado.get_data(as_text=True)
    assert "001-002-000000890" in cuerpo and "EMITIDO" in cuerpo

    # Anulación por formulario.
    nuevo = DocumentService.get_documents(numero="000000890", db_path=db)[0]
    anulado = admin_client.post("/documentos/%s/anular" % nuevo["id"],
                                data={"motivo": "Prueba de anulación por interfaz"},
                                follow_redirects=True)
    assert anulado.status_code == 200
    cuerpo = anulado.get_data(as_text=True)
    assert "ANULADO" in cuerpo and "Prueba de anulación por interfaz" in cuerpo


def test_soporte_sugerido_explica_por_que(db):
    """La ayuda didáctica dice qué documento corresponde y por qué."""
    compra = DocumentService.soporte_sugerido("compra de bienes", {"proveedor_tiene_ruc": True},
                                              db_path=db)
    assert compra["tipo"] == "FACTURA"
    assert len(compra["por_que"]) > 60
    assert any(a["tipo"] == "COMPROBANTE_RETENCION" for a in compra["acompanantes"])

    sin_ruc = DocumentService.soporte_sugerido("COMPRA_BIENES", {"proveedor_tiene_ruc": False},
                                               db_path=db)
    assert sin_ruc["tipo"] == "LIQUIDACION_COMPRA"

    traslado = DocumentService.soporte_sugerido("traslado", {}, db_path=db)
    assert traslado["tipo"] == "GUIA_REMISION"
    assert "ANTES" in traslado["aviso"].upper()

    retencion = DocumentService.soporte_sugerido("retencion", {}, db_path=db)
    assert retencion["tipo"] == "COMPROBANTE_RETENCION"
    assert retencion["reglas"]

    tiquete = DocumentService.soporte_sugerido("compra con tiquete", {}, db_path=db)
    assert tiquete["tipo"] == "TIQUETE_MAQUINA"
    assert "factura" in tiquete["aviso"].lower()

    desconocido = DocumentService.soporte_sugerido("operación rarísima", {}, db_path=db)
    assert desconocido["tipo"] is None
    assert desconocido["alternativas"]


def test_reglas_no_implementadas_informan_pero_no_bloquean(db):
    """El catálogo sigue siendo la fuente de verdad: lo no implementado solo advierte."""
    datos = _datos_factura(secuencial="000000901")
    revision = DocumentService.revisar_documento("FACTURA", datos, db_path=db)
    assert revision["ok"] is True and revision["errores"] == []

    informativas = [r for r in revision["reglas"] if r["resultado"] == "NO_IMPLEMENTADA"]
    assert {r["codigo"] for r in informativas} == {"R-57.4", "R-57.5", "R-57.6", "R-57.20", "R-57.22"}
    for regla in informativas:
        assert regla["mensajes"], "toda regla del catálogo debe explicarse al estudiante"
        assert all(m.startswith("[%s]" % regla["codigo"]) for m in regla["mensajes"])

    # R-57.10 sí bloquea cuando un tiquete se quiere usar como soporte del gasto.
    tiquete = _datos_factura(uso_documento="GASTO")
    ok, errores, _ = DocumentService.validar_documento("TIQUETE_MAQUINA", tiquete, db_path=db)
    assert ok is False and _hallazgos(errores, "R-57.10")
    ok, errores, _ = DocumentService.validar_documento("TIQUETE_MAQUINA",
                                                       _datos_factura(uso_documento="CONSUMO_PROPIO"),
                                                       db_path=db)
    assert ok is True and not _hallazgos(errores, "R-57.10")


def test_porcentajes_del_catalogo_por_tipo(db_sri):
    """El formulario ofrece los porcentajes del catálogo tributario que corresponden al tipo."""
    iva = DocumentService.porcentajes_disponibles("FACTURA", db_path=db_sri)
    assert iva and all(p["tipo"].startswith("IVA") for p in iva)
    assert any(p["porcentaje"] == 15.0 for p in iva)

    retencion = DocumentService.porcentajes_disponibles("COMPROBANTE_RETENCION", db_path=db_sri)
    assert retencion and all(p["tipo"].startswith("RET") for p in retencion)
    assert any(p["porcentaje"] == 100.0 for p in retencion)

    liquidacion = DocumentService.porcentajes_disponibles("LIQUIDACION_COMPRA", db_path=db_sri)
    assert any(p["porcentaje"] == 100.0 and p["tipo"].startswith("RET") for p in liquidacion)

    # La nota de venta del RISE no desglosa impuestos.
    assert DocumentService.porcentajes_disponibles("NOTA_VENTA_RISE", db_path=db_sri) == []


def test_parametros_por_defecto_documentados():
    """Los umbrales viven en un diccionario de parámetros, no dispersos en el código."""
    assert PARAMETROS_DOCUMENTO["tope_consumidor_final"] == 200.0
    assert PARAMETROS_DOCUMENTO["dias_habiles_retencion"] == 5
    assert PARAMETROS_DOCUMENTO["porcentaje_retencion_iva_liquidacion"] == 100.0
    assert PARAMETROS_DOCUMENTO["leyenda_educativa"] == LEYENDA_ESPERADA
    assert PARAMETROS_DOCUMENTO["tipos_sin_sustento_de_gasto"] == ["TIQUETE_MAQUINA",
                                                                  "BOLETO_ESPECTACULO"]
