# -*- coding: utf-8 -*-
"""services/document_service.py — Documentos fuente del simulador y módulo del SRI.

Este servicio tiene dos capas:

1. **Documentos fuente** (la capa clásica del simulador): cada operación contable queda respaldada
   por uno o varios documentos (facturas, comprobantes de ingreso/egreso, notas, papeletas,
   arqueos, roles de pago, órdenes).  Cadena verificable:
   Documento → Transacción → Asiento → Diario → Mayor → Balance → EEFF.

2. **Comprobantes del SRI** (Reglamento de comprobantes de venta, retención y documentos
   complementarios): emisión de comprobantes ecuatorianos con sus campos obligatorios y las
   validaciones del reglamento.  El catálogo normativo NO vive en el código sino en las tablas
   `tipos_documento` y `reglas_documento` de cada base (ver database/catalogo_sri_datos.py y
   database/esquema_documentos_sri.py), de modo que la docente puede ajustarlo sin programar.

Los umbrales y plazos (tope de consumidor final, días hábiles de retención, porcentaje de IVA de
las liquidaciones de compra, leyenda educativa, feriados…) tampoco están escritos dentro de las
validaciones: viven en `PARAMETROS_DOCUMENTO` y pueden sobrescribirse desde la tabla `parametros`
con claves `sri.<nombre>`.
"""
import json
import re
import unicodedata
from datetime import date, datetime, timedelta

from config import Config
from models import get_db_contable
from services.audit_service import AuditService

# ---------------------------------------------------------------------------------------------
# Documentos fuente del simulador (capa clásica)
TIPOS_DOCUMENTO = [
    ("FACTURA_VENTA", "Factura de Venta", "factura"),
    ("FACTURA_COMPRA", "Factura de Compra", "factura"),
    ("FACTURA_SERVICIO", "Factura de Servicio", "factura"),
    ("COMPROBANTE_INGRESO", "Comprobante de Ingreso", "comprobante"),
    ("COMPROBANTE_EGRESO", "Comprobante de Egreso", "comprobante"),
    ("COMPROBANTE_CAJA", "Comprobante de Caja", "tesoreria"),
    ("COMPROBANTE_CIERRE", "Comprobante de Cierre Contable", "ajuste"),
    ("NOTA_CREDITO", "Nota de Crédito", "nota"),
    ("NOTA_DEBITO", "Nota de Débito", "nota"),
    ("PAPELETA_DEPOSITO", "Papeleta de Depósito", "banco"),
    ("NOTA_DEBITO_BCO", "Nota de Débito Bancaria", "banco"),
    ("NOTA_CREDITO_BCO", "Nota de Crédito Bancaria", "banco"),
    ("NOTA_BANCARIA", "Nota Bancaria", "banco"),
    ("ESTADO_CUENTA_BANCARIO", "Estado de Cuenta Bancario", "banco"),
    ("ARQUEO_CAJA", "Acta de Arqueo de Caja", "tesoreria"),
    ("ROL_PAGOS", "Rol de Pagos", "nomina"),
    ("ORDEN_COMPRA", "Orden de Compra", "compra"),
    ("COMPROBANTE_AJUSTE", "Comprobante de Ajuste", "ajuste"),
    ("DOCUMENTO_POR_COBRAR", "Documento por Cobrar", "cartera"),
    ("DOCUMENTO_POR_PAGAR", "Documento por Pagar", "cartera"),
    ("DOCUMENTO_INTERNO", "Documento Interno", "ajuste"),
]

# ---------------------------------------------------------------------------------------------
# Parámetros configurables del módulo (umbrales y plazos del reglamento).
# Cada uno puede sobrescribirse en la tabla `parametros` con la clave "sri.<nombre>".
PARAMETROS_DOCUMENTO = {
    # R-57.7 — tope de la factura a CONSUMIDOR FINAL (USD, sin identificación del adquirente).
    "tope_consumidor_final": 200.0,
    # R-57.12 — plazo de entrega del comprobante de retención, en días hábiles.
    "dias_habiles_retencion": 5,             # IVA / Renta
    "alerta_desde_retencion": 4,             # desde qué día hábil se advierte al estudiante
    "dias_habiles_retencion_isd": 2,         # ISD
    "alerta_desde_retencion_isd": 2,
    # R-57.14 — porcentaje de IVA que debe retenerse en una liquidación de compra.
    "porcentaje_retencion_iva_liquidacion": 100.0,
    # R-57.21 — días hábiles para comunicar la baja al SRI (informativo).
    "dias_habiles_baja": 15,
    # R-57.2 — longitudes de la numeración 3-3-9.
    "longitud_establecimiento": 3,
    "longitud_punto_emision": 3,
    "longitud_secuencial": 9,
    # Tipos que no dan crédito tributario ni sustentan costos y gastos (R-57.10).
    "tipos_sin_sustento_de_gasto": ["TIQUETE_MAQUINA", "BOLETO_ESPECTACULO"],
    "usos_que_exigen_comprobante_valido": ["GASTO", "COSTO", "SOPORTE_GASTO", "CREDITO_TRIBUTARIO"],
    # Tipos que no desglosan el IVA (R-57.8).
    "tipos_sin_desglose_iva": ["NOTA_VENTA_RISE"],
    # Tipos que, por excepción de la docente, no exigen numeración del SRI (vacío por defecto).
    "tipos_exentos_de_numeracion": [],
    # Feriados nacionales/locales que no cuentan como días hábiles (formato AAAA-MM-DD).
    "feriados": [],
    # R-57.23 — leyenda educativa que se imprime en todo comprobante.
    "leyenda_educativa": "DOCUMENTO PARA USO EDUCATIVO (SIN VALIDEZ COMERCIAL)",
}

# Etiquetas legibles de las categorías del catálogo.
CATEGORIA_ETIQUETAS = {
    "COMPROBANTE_VENTA": "Comprobantes de venta",
    "COMPLEMENTARIO": "Documentos complementarios",
    "RETENCION": "Comprobantes de retención",
    "DOCUMENTO_SOPORTE": "Documentos de soporte",
}

# Porcentajes del catálogo tributario que se ofrecen en el formulario de cada tipo de documento
# (prefijos del campo `impuestos.tipo`: IVA_* son tarifas, RET_* son porcentajes de retención).
PORCENTAJES_POR_TIPO = {
    "COMPROBANTE_RETENCION": ("RET",),
    "LIQUIDACION_COMPRA": ("IVA", "RET"),
    "LIQUIDACION_VEHICULOS_USADOS": ("IVA", "RET"),
    "NOTA_VENTA_RISE": (),
}

# Identificaciones válidas del adquirente (Art. 19 num. 1).
TIPOS_IDENTIFICACION = ("RUC", "CEDULA", "PASAPORTE", "CONSUMIDOR_FINAL")
IDENTIFICACIONES_POSITIVAS = ("RUC", "CEDULA", "PASAPORTE")
FORMAS_PAGO = ("EFECTIVO", "CREDITO", "TARJETA_CREDITO", "TARJETA_DEBITO", "TRANSFERENCIA", "OTROS")
IMPUESTOS_RETENCION = ("RENTA", "IVA", "ISD")
TIPOS_EMISION = ("NORMAL", "OFFLINE")
USOS_DOCUMENTO = ("CONSUMO_PROPIO", "GASTO", "COSTO", "CREDITO_TRIBUTARIO", "REVENTA")

# Columnas del comprobante ecuatoriano que deben existir en documentos_fuente
# (las crea database/esquema_documentos_sri.py; aquí se verifican para no fallar en una base nueva).
COLUMNAS_COMPROBANTE = (
    "ruc_emisor", "numero_autorizacion", "fecha_autorizacion", "establecimiento",
    "punto_emision", "secuencial", "numero_completo", "tipo_emision", "adquirente_tipo_id",
    "adquirente_identificacion", "adquirente_nombre", "forma_pago", "subtotal", "descuento",
    "iva_tarifa", "iva_valor", "ice_valor", "propina", "documento_modificado",
    "motivo_modificacion", "base_retencion", "porcentaje_retencion", "valor_retenido",
    "impuesto_retenido", "fecha_entrega_retencion", "valor_modificacion", "motivo_traslado",
    "direccion_partida", "direccion_destino", "transportista", "placa_vehiculo", "estado",
    "origen_actividad_id",
)

# Estados del comprobante.
ESTADOS_DOCUMENTO = ("EMITIDO", "ENTREGADO", "ANULADO", "DADO_DE_BAJA")

# Bases cuyo catálogo del SRI ya fue verificado (una vez por archivo y proceso).
_BASES_CON_CATALOGO = set()

# Mapas de "tipo de transacción" → documento que corresponde (ver soporte_sugerido).
TABLA_SOPORTE = {
    "COMPRA_BIENES": {
        "tipo": "FACTURA",
        "por_que": "Al comprar bienes a un proveedor inscrito en el RUC, el proveedor está obligado "
                   "a emitirte factura: es el comprobante que sustenta el costo y el crédito "
                   "tributario del IVA, siempre que te identifique y desglose el impuesto.",
        "acompanantes": ["COMPROBANTE_RETENCION"],
    },
    "COMPRA_SERVICIOS": {
        "tipo": "FACTURA",
        "por_que": "La prestación de servicios también se respalda con factura; para que el gasto sea "
                   "deducible debe identificar a tu empresa y desglosar el IVA por separado.",
        "acompanantes": ["COMPROBANTE_RETENCION"],
    },
    "COMPRA_A_NO_OBLIGADO": {
        "tipo": "LIQUIDACION_COMPRA",
        "por_que": "Cuando le compras a una persona natural que no está inscrita en el RUC ni puede "
                   "emitir comprobantes, la liquidación de compra la emites TÚ (como adquirente) y "
                   "retienes el 100 % del IVA y el porcentaje de renta.",
        "acompanantes": ["COMPROBANTE_RETENCION"],
    },
    "COMPRA_VEHICULO_USADO": {
        "tipo": "LIQUIDACION_VEHICULOS_USADOS",
        "por_que": "Para la compra de un vehículo usado a quien no puede emitir comprobante se usa el "
                   "formato oficial de liquidación de compra de vehículos usados, con los datos "
                   "completos del vehículo y de las partes.",
        "acompanantes": ["ACTA_VEHICULOS_USADOS"],
    },
    "VENTA_BIENES": {
        "tipo": "FACTURA",
        "por_que": "Toda transferencia de bienes gravada se respalda con factura, aunque el cliente no "
                   "la pida y aunque la tarifa sea 0 %.",
        "acompanantes": ["GUIA_REMISION"],
    },
    "VENTA_SERVICIOS": {
        "tipo": "FACTURA",
        "por_que": "La prestación de servicios se respalda con factura; el IVA se desglosa cuando el "
                   "cliente sustenta crédito tributario o gastos personales.",
        "acompanantes": [],
    },
    "VENTA_SERVICIOS_TURISTICOS": {
        "tipo": "FACTURA_SERVICIOS_TURISTICOS",
        "por_que": "Los establecimientos turísticos registrados emiten el formato oficial de factura de "
                   "servicios turísticos, que puede aplicar la tarifa especial del período.",
        "acompanantes": [],
    },
    "VENTA_TRANSPORTE": {
        "tipo": "FACTURA_TRANSPORTE",
        "por_que": "Las operadoras de transporte autorizadas emiten su formato oficial de factura, "
                   "incluso cuando facturan a sus socios o accionistas.",
        "acompanantes": [],
    },
    "VENTA_CONSUMIDOR_FINAL": {
        "tipo": "FACTURA",
        "por_que": "Al consumidor final se le puede entregar factura (o tiquete si el negocio usa "
                   "máquinas registradoras). El impuesto no se desglosa y el total no debe superar el "
                   "tope configurado cuando no se identifica al cliente.",
        "acompanantes": [],
    },
    "VENTA_RISE": {
        "tipo": "NOTA_VENTA_RISE",
        "por_que": "Los contribuyentes del Régimen Simplificado emiten notas de venta: no desglosan el "
                   "IVA y solo identifican al comprador cuando este va a sustentar costos y gastos.",
        "acompanantes": [],
    },
    "VENTA_ESPECTACULO": {
        "tipo": "BOLETO_ESPECTACULO",
        "por_que": "Las entradas a espectáculos públicos se documentan con boletos preimpresos o "
                   "autorizados; por ser de consumidor final no dan crédito tributario.",
        "acompanantes": [],
    },
    "TRASLADO": {
        "tipo": "GUIA_REMISION",
        "por_que": "Siempre que la mercadería sale del establecimiento (venta, devolución, traslado "
                   "entre locales) se emite la guía de remisión ANTES de iniciar el traslado y la "
                   "porta cada unidad de transporte.",
        "acompanantes": ["FACTURA"],
    },
    "RETENCION": {
        "tipo": "COMPROBANTE_RETENCION",
        "por_que": "Si tu empresa actúa como agente de retención, al pagar o acreditar en cuenta "
                   "(lo que ocurra primero) emite el comprobante de retención y lo entrega al "
                   "proveedor dentro de los plazos del reglamento.",
        "acompanantes": [],
    },
    "DEVOLUCION_DESCUENTO": {
        "tipo": "NOTA_CREDITO",
        "por_que": "Para anular operaciones, aceptar devoluciones o conceder descuentos y "
                   "bonificaciones se emite la nota de crédito, citando el comprobante que modifica.",
        "acompanantes": [],
    },
    "COBRO_POSTERIOR": {
        "tipo": "NOTA_DEBITO",
        "por_que": "Los intereses de mora y los costos y gastos incurridos después de emitida la "
                   "factura se cobran con nota de débito, referenciando el comprobante original.",
        "acompanantes": [],
    },
    "COMPRA_CON_TIQUETE": {
        "tipo": "TIQUETE_MAQUINA",
        "por_que": "El tiquete de máquina registradora solo acredita la compra con consumidores "
                   "finales: NO identifica a tu empresa, así que no sustenta costos y gastos ni da "
                   "crédito tributario. Pide que lo cambien por factura.",
        "acompanantes": [],
    },
}

# Alias en lenguaje natural para la ayuda didáctica.
ALIAS_SOPORTE = {
    "COMPRA": "COMPRA_BIENES",
    "COMPRAS": "COMPRA_BIENES",
    "COMPRA_MERCADERIA": "COMPRA_BIENES",
    "COMPRA_BIENES": "COMPRA_BIENES",
    "COMPRA_SERVICIO": "COMPRA_SERVICIOS",
    "COMPRA_SERVICIOS": "COMPRA_SERVICIOS",
    "SERVICIO_RECIBIDO": "COMPRA_SERVICIOS",
    "LIQUIDACION": "COMPRA_A_NO_OBLIGADO",
    "COMPRA_PERSONA_NATURAL": "COMPRA_A_NO_OBLIGADO",
    "COMPRA_SIN_RUC": "COMPRA_A_NO_OBLIGADO",
    "VEHICULO_USADO": "COMPRA_VEHICULO_USADO",
    "VENTA": "VENTA_BIENES",
    "VENTAS": "VENTA_BIENES",
    "VENTA_BIEN": "VENTA_BIENES",
    "VENTA_SERVICIO": "VENTA_SERVICIOS",
    "VENTA_SERVICIOS": "VENTA_SERVICIOS",
    "SERVICIO": "VENTA_SERVICIOS",
    "TURISTICO": "VENTA_SERVICIOS_TURISTICOS",
    "TRANSPORTE": "VENTA_TRANSPORTE",
    "CONSUMIDOR_FINAL": "VENTA_CONSUMIDOR_FINAL",
    "RISE": "VENTA_RISE",
    "ESPECTACULO": "VENTA_ESPECTACULO",
    "GUIA": "TRASLADO",
    "TRASLADO": "TRASLADO",
    "RETENCION": "RETENCION",
    "NOTA_CREDITO": "DEVOLUCION_DESCUENTO",
    "DEVOLUCION": "DEVOLUCION_DESCUENTO",
    "DESCUENTO": "DEVOLUCION_DESCUENTO",
    "NOTA_DEBITO": "COBRO_POSTERIOR",
    "MORA": "COBRO_POSTERIOR",
    "INTERESES": "COBRO_POSTERIOR",
    "TIQUETE": "COMPRA_CON_TIQUETE",
    "COMPROBANTE_RETENCION": "RETENCION",
    "GUIA_REMISION": "TRASLADO",
    "NOTA_VENTA_RISE": "VENTA_RISE",
    "LIQUIDACION_COMPRA": "COMPRA_A_NO_OBLIGADO",
}


# =============================================================================================
# Utilidades internas
# =============================================================================================
def _texto(valor):
    """Devuelve el texto limpio de un valor de formulario (None si viene vacío)."""
    if valor is None:
        return ""
    return str(valor).strip()


def _a_float(valor, por_defecto=None):
    """Convierte a número admitiendo coma decimal y símbolos de moneda."""
    if valor is None or valor == "":
        return por_defecto
    if isinstance(valor, (int, float)):
        return float(valor)
    limpio = _texto(valor).replace("$", "").replace(" ", "")
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(",", "")
    limpio = limpio.replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return por_defecto


def _a_fecha(valor):
    """Convierte 'AAAA-MM-DD' (o date/datetime) a date; None si no es una fecha válida."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = _texto(valor)[:10]
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _formato_usd(valor):
    return "$%.2f" % float(valor or 0)


def _dias_habiles(desde, hasta, feriados=()):
    """Días hábiles (lunes a viernes, sin feriados) contados desde el día SIGUIENTE a `desde`.

    Corresponde a la fórmula del reglamento: el plazo de 5 días hábiles corre a partir del día
    siguiente al de presentación del comprobante de venta. Devuelve None si faltan fechas.
    """
    inicio = _a_fecha(desde)
    fin = _a_fecha(hasta)
    if inicio is None or fin is None:
        return None
    if fin <= inicio:
        return 0
    festivos = {f for f in (_a_fecha(x) for x in (feriados or ())) if f}
    dias = 0
    actual = inicio
    while actual < fin:
        actual += timedelta(days=1)
        if actual.weekday() < 5 and actual not in festivos:
            dias += 1
    return dias


def _es_identificado(datos):
    """True si el adquirente está identificado con RUC, cédula o pasaporte."""
    tipo_id = _texto(datos.get("adquirente_tipo_id")).upper()
    return tipo_id in IDENTIFICACIONES_POSITIVAS


def _total_documento(datos):
    """Importe total de la transacción: subtotal - descuento + IVA + ICE + propina."""
    total = _a_float(datos.get("monto_total"), None)
    if total is not None:
        return round(total, 2)
    subtotal = _a_float(datos.get("subtotal"), 0.0) or 0.0
    descuento = _a_float(datos.get("descuento"), 0.0) or 0.0
    iva = _a_float(datos.get("iva_valor"), 0.0) or 0.0
    ice = _a_float(datos.get("ice_valor"), 0.0) or 0.0
    propina = _a_float(datos.get("propina"), 0.0) or 0.0
    return round(subtotal - descuento + iva + ice + propina, 2)


def _fecha_emision(datos):
    """Fecha de emisión del comprobante: la del formulario o la fecha de trabajo del simulador."""
    fecha = _a_fecha(datos.get("fecha") or datos.get("fecha_emision"))
    if fecha:
        return fecha
    try:
        fecha = _a_fecha(fecha_trabajo())
        if fecha:
            return fecha
    except Exception:
        pass
    return date.today()


def fecha_trabajo(db_path=None):
    """Fecha de trabajo del simulador (la que aparece en la barra superior)."""
    from services.period_service import PeriodService
    return PeriodService.get_fecha_trabajo(db_path=db_path)


def _rotular(regla, texto):
    """Antepone el código de la regla al mensaje para que el estudiante sepa de dónde sale."""
    return "[%s] %s" % (regla.get("codigo", "R-57"), texto)


def _mensaje_catalogo(regla):
    """Mensaje tal cual está redactado en el catálogo normativo."""
    return _rotular(regla, _texto(regla.get("mensaje")))


def _catalogo_etiqueta(tipo_documento):
    """Nombre legible de un tipo de documento del catálogo (o el propio código)."""
    return (tipo_documento or "").replace("_", " ").capitalize()


def _normalizar_clave(texto):
    """Convierte 'compra de bienes' o 'Compra-De-Bienes' en COMPRA_DE_BIENES."""
    sin_acentos = unicodedata.normalize("NFKD", _texto(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", sin_acentos).strip("_").upper()


def _clave_soporte(texto):
    """Traduce lo que escribe el estudiante a una clave de la tabla de soportes."""
    clave = _normalizar_clave(texto)
    if clave in ALIAS_SOPORTE:
        return ALIAS_SOPORTE[clave]
    if clave in TABLA_SOPORTE:
        return clave
    for alias in sorted(ALIAS_SOPORTE, key=len, reverse=True):
        if alias in clave:
            return ALIAS_SOPORTE[alias]
    return clave


def _partes_numeracion(datos, parametros):
    """Separa establecimiento, punto de emisión y secuencial de la numeración del comprobante.

    Acepta los campos por separado o un `numero_completo` con o sin guiones.
    """
    l_est = int(parametros.get("longitud_establecimiento", 3))
    l_pto = int(parametros.get("longitud_punto_emision", 3))
    l_sec = int(parametros.get("longitud_secuencial", 9))
    total = l_est + l_pto + l_sec
    est = _texto(datos.get("establecimiento"))
    pto = _texto(datos.get("punto_emision"))
    sec = _texto(datos.get("secuencial"))
    if est and pto and sec:
        return est, pto, sec
    completo = _texto(datos.get("numero_completo") or datos.get("numero"))
    digitos = re.sub(r"\D", "", completo)
    if len(digitos) == total:
        return digitos[:l_est], digitos[l_est:l_est + l_pto], digitos[l_est + l_pto:]
    return est, pto, sec


def _armar_numero_completo(datos, parametros):
    """Numeración de 15 dígitos en la forma legible 001-002-000000123."""
    est, pto, sec = _partes_numeracion(datos, parametros)
    if not (est and pto and sec):
        return None
    return "%s-%s-%s" % (est, pto, sec)


# =============================================================================================
# Validadores del reglamento. Cada uno recibe (tipo, datos, parametros, regla, db_path) y
# devuelve una lista de tuplas (severidad, mensaje).
# =============================================================================================
def _v_autorizacion(tipo, datos, parametros, regla, db_path=None):
    hallazgos = []
    if not _texto(datos.get("numero_autorizacion")):
        hallazgos.append(("BLOQUEO", _rotular(
            regla, "Falta el número de autorización de impresión del SRI. Ningún comprobante puede "
                   "emitirse sin ese número: pídelo al establecimiento gráfico o al SRI.")))
    if not _a_fecha(datos.get("fecha_autorizacion")):
        hallazgos.append(("ADVERTENCIA", _rotular(
            regla, "No consta la fecha de la autorización de impresión; regístrala para controlar su "
                   "vigencia.")))
    return hallazgos


def _v_numeracion(tipo, datos, parametros, regla, db_path=None):
    if tipo in [t.upper() for t in parametros.get("tipos_exentos_de_numeracion", [])]:
        return []
    l_est = int(parametros.get("longitud_establecimiento", 3))
    l_pto = int(parametros.get("longitud_punto_emision", 3))
    l_sec = int(parametros.get("longitud_secuencial", 9))
    total = l_est + l_pto + l_sec
    est, pto, sec = _partes_numeracion(datos, parametros)
    if not (est or pto or sec):
        return [("BLOQUEO", _rotular(
            regla, "Falta la numeración del comprobante. Escribe los %d dígitos del establecimiento, "
                   "los %d del punto de emisión y los %d del secuencial (por ejemplo 001-002-000000123)."
                   % (l_est, l_pto, l_sec)))]
    if (len(est) != l_est or len(pto) != l_pto or len(sec) != l_sec
            or not est.isdigit() or not pto.isdigit() or not sec.isdigit()):
        return [("BLOQUEO", _rotular(
            regla, "La numeración %s-%s-%s no cumple el formato: deben ser %d dígitos del "
                   "establecimiento, %d del punto de emisión y %d del secuencial (15 en total, "
                   "por ejemplo 001-002-000000123)."
                   % (est or "?", pto or "?", sec or "?", l_est, l_pto, l_sec)))]
    if len(est) + len(pto) + len(sec) != total:  # defensa extra por si se cambian las longitudes
        return [("BLOQUEO", _rotular(regla, "La numeración debe tener %d dígitos en total." % total))]
    # Correlatividad: el mismo establecimiento + punto de emisión + secuencial no se repite.
    numero = "%s-%s-%s" % (est, pto, sec)
    propio = datos.get("_documento_id") or datos.get("documento_id")
    try:
        conn = get_db_contable(db_path)
        try:
            sql = ("SELECT id, estado FROM documentos_fuente WHERE (numero_completo = ? "
                   "OR (establecimiento = ? AND punto_emision = ? AND secuencial = ?))")
            parametros_consulta = [numero, est, pto, sec]
            if propio:
                sql += " AND id <> ?"
                parametros_consulta.append(int(propio))
            repetido = conn.execute(sql + " LIMIT 1", parametros_consulta).fetchone()
        finally:
            conn.close()
        if repetido:
            return [("BLOQUEO", _rotular(
                regla, "La numeración %s ya fue usada en otro comprobante. El secuencial debe ser "
                       "correlativo y no repetirse dentro del mismo punto de emisión." % numero))]
    except Exception:
        pass
    return []


def _v_vigencia(tipo, datos, parametros, regla, db_path=None):
    caducidad = _a_fecha(datos.get("fecha_caducidad_autorizacion"))
    emision = _fecha_emision(datos)
    if not caducidad:
        return [("ADVERTENCIA", _rotular(
            regla, "No consta la fecha de caducidad de la autorización: sin ella no se puede "
                   "verificar si el comprobante se emite dentro de su vigencia."))]
    if emision and caducidad < emision:
        return [("BLOQUEO", _rotular(
            regla, "La autorización de impresión caducó el %s y el comprobante se emite el %s. "
                   "Solicita una autorización vigente antes de emitir."
                   % (caducidad.isoformat(), emision.isoformat())))]
    return []


def _v_consumidor_final(tipo, datos, parametros, regla, db_path=None):
    tipo_id = _texto(datos.get("adquirente_tipo_id")).upper()
    if tipo_id != "CONSUMIDOR_FINAL":
        return []
    tope = _a_float(parametros.get("tope_consumidor_final"), 200.0)
    total = _total_documento(datos)
    if tope is not None and total > tope:
        return [("BLOQUEO", _rotular(
            regla, "Una factura a «CONSUMIDOR FINAL» no puede superar %s y esta llega a %s. "
                   "Identifica al cliente con su RUC o cédula, o divide la operación."
                   % (_formato_usd(tope), _formato_usd(total))))]
    return []


def _v_desglose_iva(tipo, datos, parametros, regla, db_path=None):
    if tipo in [t.upper() for t in parametros.get("tipos_sin_desglose_iva", [])]:
        return []
    tipo_id = _texto(datos.get("adquirente_tipo_id")).upper()
    iva_valor = _a_float(datos.get("iva_valor"), None)
    iva_tarifa = _a_float(datos.get("iva_tarifa"), None)
    if tipo_id in IDENTIFICACIONES_POSITIVAS:
        if not iva_valor and not iva_tarifa:
            return [("ADVERTENCIA", _rotular(
                regla, "Al cliente identificado se le desglosa el IVA: registra la tarifa y el valor "
                       "del impuesto para que la factura le sirva como crédito tributario."))]
    elif tipo_id == "CONSUMIDOR_FINAL" and (iva_valor or iva_tarifa):
        return [("ADVERTENCIA", _rotular(
            regla, "A un consumidor final no se le desglosa el impuesto: consigna el importe total "
                   "con el IVA incluido."))]
    return []


def _v_credito_tributario(tipo, datos, parametros, regla, db_path=None):
    if not _es_identificado(datos):
        return [("ADVERTENCIA", _rotular(
            regla, "Sin la identificación del cliente (RUC, cédula o pasaporte) y el IVA por "
                   "separado, este comprobante no da crédito tributario."))]
    return []


def _v_sustento_gasto(tipo, datos, parametros, regla, db_path=None):
    sin_sustento = [t.upper() for t in parametros.get("tipos_sin_sustento_de_gasto", [])]
    if tipo not in sin_sustento:
        return []
    uso = _texto(datos.get("uso_documento") or datos.get("uso")).upper()
    usos = [u.upper() for u in parametros.get("usos_que_exigen_comprobante_valido", [])]
    if uso in usos or bool(datos.get("sustenta_gasto")):
        return [("BLOQUEO", _rotular(
            regla, "Un tiquete o boleto no identifica a tu empresa: no sustenta costos y gastos ni da "
                   "crédito tributario. Pide el cambio por factura o nota de venta."))]
    return [("INFORMATIVA", _mensaje_catalogo(regla))]


def _v_plazo_retencion(tipo, datos, parametros, regla, db_path=None):
    impuesto = _texto(datos.get("impuesto_retenido")).upper()
    es_isd = impuesto == "ISD"
    if es_isd:
        limite = int(parametros.get("dias_habiles_retencion_isd", 2))
        alerta = int(parametros.get("alerta_desde_retencion_isd", limite))
        nombre_plazo = "2 días hábiles por tratarse del ISD"
    else:
        limite = int(parametros.get("dias_habiles_retencion", 5))
        alerta = int(parametros.get("alerta_desde_retencion", limite - 1))
        nombre_plazo = "%d días hábiles" % limite
    base = datos.get("fecha_comprobante_venta") or datos.get("fecha_documento_base")
    entrega = datos.get("fecha_entrega_retencion") or _fecha_emision(datos)
    if not _a_fecha(base):
        return [("ADVERTENCIA", _rotular(
            regla, "Indica la fecha del comprobante de venta que motiva la retención: desde el día "
                   "siguiente corre el plazo de %s para entregar el comprobante." % nombre_plazo))]
    dias = _dias_habiles(base, entrega, parametros.get("feriados"))
    if dias is None:
        return []
    if dias > limite:
        return [("BLOQUEO", _rotular(
            regla, "El comprobante de retención se entrega a los %d días hábiles y el plazo máximo es "
                   "%s. Al excederlo corresponde regularizar la entrega y comunicar la novedad al SRI."
                   % (dias, nombre_plazo)))]
    if dias >= alerta:
        restantes = max(limite - dias, 0)
        mensaje = _texto(regla.get("mensaje"))
        if "%d" in mensaje:
            detalle = mensaje % restantes
        else:
            detalle = mensaje
        return [("ADVERTENCIA", _rotular(
            regla, "Llevas %d de %s y te queda%s %d día%s hábil%s. %s"
                   % (dias, nombre_plazo, "" if restantes == 1 else "n", restantes,
                      "" if restantes == 1 else "es", "" if restantes == 1 else "es", detalle)))]
    return []


def _v_retencion_liquidacion(tipo, datos, parametros, regla, db_path=None):
    requerido = _a_float(parametros.get("porcentaje_retencion_iva_liquidacion"), 100.0)
    impuesto = _texto(datos.get("impuesto_retenido")).upper()
    porcentaje = _a_float(datos.get("porcentaje_retencion"), None)
    if impuesto != "IVA" or porcentaje is None or porcentaje < requerido:
        return [("BLOQUEO", _rotular(
            regla, "En la liquidación de compra debes retener el %s %% del IVA (y el porcentaje de "
                   "renta que corresponda) para que sustente costos y gastos. Registra impuesto "
                   "retenido = IVA y porcentaje de retención = %s %%."
                   % ("%.0f" % requerido, "%.0f" % requerido)))]
    return []


def _v_notas_ajuste(tipo, datos, parametros, regla, db_path=None):
    hallazgos = []
    if not _texto(datos.get("documento_modificado")):
        hallazgos.append(("BLOQUEO", _rotular(
            regla, "Indica la denominación, serie y número del comprobante de venta que esta nota "
                   "modifica (por ejemplo FACTURA 001-002-000000123).")))
    if not _texto(datos.get("motivo_modificacion")):
        hallazgos.append(("BLOQUEO", _rotular(
            regla, "Explica el motivo de la modificación: anulación de la operación, devolución, "
                   "descuento o bonificación, intereses de mora, costos y gastos posteriores.")))
    return hallazgos


def _v_guia_remision(tipo, datos, parametros, regla, db_path=None):
    hallazgos = []
    emision = _fecha_emision(datos)
    inicio = _a_fecha(datos.get("fecha_inicio_traslado") or datos.get("fecha_traslado"))
    if not inicio:
        hallazgos.append(("BLOQUEO", _rotular(
            regla, "Registra la fecha de inicio del traslado: la guía de remisión debe emitirse antes "
                   "de que la mercadería salga del establecimiento.")))
    elif emision and emision > inicio:
        hallazgos.append(("BLOQUEO", _rotular(
            regla, "La guía se emitió el %s y el traslado inicia el %s. La guía de remisión se emite "
                   "ANTES del traslado: emítela primero y luego moviliza la mercadería."
                   % (emision.isoformat(), inicio.isoformat()))))
    faltantes = []
    if not _texto(datos.get("motivo_traslado")):
        faltantes.append("el motivo del traslado")
    if not _texto(datos.get("direccion_destino")):
        faltantes.append("la dirección de destino")
    if not _texto(datos.get("transportista")) and not _texto(datos.get("conductor")):
        faltantes.append("la identificación del conductor o transportista")
    if not _texto(datos.get("placa_vehiculo")):
        faltantes.append("la placa del vehículo")
    if faltantes:
        hallazgos.append(("BLOQUEO", _rotular(
            regla, "A la guía de remisión le falta: %s. La guía debe portarla cada unidad de "
                   "transporte y con esos datos el destinatario la conserva en su archivo."
                   % ", ".join(faltantes))))
    return hallazgos


def _v_anulacion(tipo, datos, parametros, regla, db_path=None):
    accion = _texto(datos.get("accion") or datos.get("estado")).upper()
    motivo = _texto(datos.get("motivo_anulacion") or datos.get("motivo_modificacion"))
    if accion in ("ELIMINAR", "BORRAR") or datos.get("eliminar"):
        return [("BLOQUEO", _rotular(
            regla, "Los comprobantes no se eliminan: se anulan o se dan de baja con su motivo y se "
                   "conservan en un archivo ordenado secuencialmente."))]
    if accion in ("ANULAR", "ANULADO", "DAR_DE_BAJA", "BAJA"):
        if not motivo:
            return [("BLOQUEO", _rotular(
                regla, "Para anular o dar de baja el comprobante debes indicar el motivo; el documento "
                       "queda registrado y no se borra."))]
        return [("ADVERTENCIA", _rotular(
            regla, "El comprobante quedará ANULADO con su motivo registrado. Recuerda comunicar la "
                   "baja al SRI dentro de los %s días hábiles siguientes."
                   % int(parametros.get("dias_habiles_baja", 15))))]
    return [("INFORMATIVA", _mensaje_catalogo(regla))]


def _v_leyenda(tipo, datos, parametros, regla, db_path=None):
    return [("INFORMATIVA", _rotular(regla, _texto(parametros.get("leyenda_educativa"))))]


# Reglas implementadas individualmente (clave = código de la regla en el catálogo).
VALIDADORES_IMPLEMENTADOS = {
    "R-57.1": _v_autorizacion,
    "R-57.2": _v_numeracion,
    "R-57.3": _v_vigencia,
    "R-57.7": _v_consumidor_final,
    "R-57.8": _v_desglose_iva,
    "R-57.9": _v_credito_tributario,
    "R-57.10": _v_sustento_gasto,
    "R-57.12": _v_plazo_retencion,
    "R-57.14": _v_retencion_liquidacion,
    "R-57.16": _v_notas_ajuste,
    "R-57.19": _v_guia_remision,
    "R-57.21": _v_anulacion,
    "R-57.23": _v_leyenda,
}


# =============================================================================================
# Campos del formulario de emisión (se arman a partir del catálogo de tipos)
# =============================================================================================
def _campo(nombre, etiqueta, ayuda, tipo="text", opciones=None, obligatorio=False, regla=None,
           seccion="Datos del comprobante", ancho=4):
    return {"nombre": nombre, "etiqueta": etiqueta, "ayuda": ayuda, "tipo": tipo,
            "opciones": opciones or [], "obligatorio": obligatorio, "regla": regla,
            "seccion": seccion, "ancho": ancho}


SECCION_COMPROBANTE = "Identificación del comprobante"
SECCION_EMISOR = "Datos del emisor"
SECCION_ADQUIRENTE = "Datos del adquirente"
SECCION_VALORES = "Valores e impuestos"
SECCION_ESPECIFICA = "Datos propios de este documento"
SECCION_TRAZABILIDAD = "Trazabilidad"

CAMPOS_BASE = [
    _campo("fecha", "Fecha de emisión", "Día, mes y año en que se entrega el comprobante.",
           tipo="date", obligatorio=True, seccion=SECCION_COMPROBANTE, ancho=3),
    _campo("numero_autorizacion", "N° de autorización de impresión",
           "Número que el SRI otorga al emisor para imprimir el comprobante (Art. 18 num. 1).",
           obligatorio=True, regla="R-57.1", seccion=SECCION_COMPROBANTE, ancho=3),
    _campo("fecha_autorizacion", "Fecha de la autorización",
           "Día, mes y año de la autorización de impresión.", tipo="date",
           regla="R-57.1", seccion=SECCION_COMPROBANTE, ancho=3),
    _campo("fecha_caducidad_autorizacion", "Caducidad de la autorización",
           "Un año si el contribuyente está al día; tres meses si tiene pendientes. La emisión no "
           "puede ser posterior a esta fecha.", tipo="date", regla="R-57.3",
           seccion=SECCION_COMPROBANTE, ancho=3),
    _campo("establecimiento", "Establecimiento (3 dígitos)",
           "Código del local donde se emite. Es la primera parte de la numeración de 15 dígitos.",
           obligatorio=True, regla="R-57.2", seccion=SECCION_COMPROBANTE, ancho=2),
    _campo("punto_emision", "Punto de emisión (3 dígitos)",
           "Punto de emisión del establecimiento: cada caja o serie lleva el suyo.",
           obligatorio=True, regla="R-57.2", seccion=SECCION_COMPROBANTE, ancho=2),
    _campo("secuencial", "Secuencial (9 dígitos)",
           "Número correlativo del comprobante dentro del punto de emisión; no se repite.",
           obligatorio=True, regla="R-57.2", seccion=SECCION_COMPROBANTE, ancho=3),
    _campo("tipo_emision", "Tipo de emisión",
           "NORMAL si el comprobante se emite conectado; OFFLINE si se emite sin conexión y luego "
           "se envía al SRI.", tipo="select", opciones=TIPOS_EMISION,
           seccion=SECCION_COMPROBANTE, ancho=3),
    _campo("ruc_emisor", "RUC del emisor", "RUC de la empresa que emite el comprobante.",
           regla="R-57.6", seccion=SECCION_EMISOR, ancho=4),
    _campo("emisor", "Razón social del emisor",
           "Apellidos y nombres o razón social de quien emite.", seccion=SECCION_EMISOR, ancho=8),
    _campo("adquirente_tipo_id", "Tipo de identificación del adquirente",
           "RUC o cédula cuando el cliente sustenta costos y gastos; PASAPORTE para no residentes; "
           "CONSUMIDOR_FINAL cuando no se identifica.", tipo="select", opciones=TIPOS_IDENTIFICACION,
           regla="R-57.7", seccion=SECCION_ADQUIRENTE, ancho=4),
    _campo("adquirente_identificacion", "Identificación del adquirente",
           "RUC, cédula o pasaporte del cliente.", seccion=SECCION_ADQUIRENTE, ancho=4),
    _campo("adquirente_nombre", "Nombre o razón social del adquirente",
           "Quién recibe el comprobante.", seccion=SECCION_ADQUIRENTE, ancho=4),
    _campo("forma_pago", "Forma de pago",
           "Cómo paga el cliente: contado, crédito, tarjeta, transferencia u otros.",
           tipo="select", opciones=FORMAS_PAGO, seccion=SECCION_ADQUIRENTE, ancho=4),
    _campo("subtotal", "Subtotal (sin impuestos)",
           "Valor de la transacción antes de impuestos y descuentos.", tipo="number",
           seccion=SECCION_VALORES, ancho=3),
    _campo("descuento", "Descuento o bonificación",
           "Se registra cuando existe; rebaja la base del impuesto.", tipo="number",
           seccion=SECCION_VALORES, ancho=3),
    _campo("iva_tarifa", "Tarifa de IVA (%)",
           "Tarifa vigente del período (15 % general; 5 % construcción; 8 % turístico en feriados).",
           tipo="number", regla="R-57.8", seccion=SECCION_VALORES, ancho=2),
    _campo("iva_valor", "Valor del IVA",
           "Impuesto desglosado, obligatorio si el adquirente está identificado.",
           tipo="number", regla="R-57.8", seccion=SECCION_VALORES, ancho=2),
    _campo("ice_valor", "ICE", "Impuesto a los consumos especiales, cuando aplique.", tipo="number",
           seccion=SECCION_VALORES, ancho=2),
    _campo("propina", "Propina", "Solo hoteles, bares y restaurantes calificados.", tipo="number",
           seccion=SECCION_VALORES, ancho=2),
    _campo("monto_total", "Importe total",
           "Subtotal - descuento + IVA + ICE + propina. Si lo dejas vacío se calcula.", tipo="number",
           seccion=SECCION_VALORES, ancho=3),
    _campo("descripcion", "Descripción o concepto",
           "Detalle de los bienes o servicios: cantidad, unidad de medida y precio unitario.",
           tipo="textarea", seccion=SECCION_TRAZABILIDAD, ancho=12),
]

CAMPOS_POR_TIPO = {
    "NOTA_CREDITO": [
        _campo("documento_modificado", "Comprobante que modifica",
               "Denominación, serie y número del comprobante de venta que esta nota modifica.",
               obligatorio=True, regla="R-57.16", seccion=SECCION_ESPECIFICA, ancho=6),
        _campo("motivo_modificacion", "Motivo de la modificación",
               "Anulación de la operación, devolución, descuento o bonificación.",
               obligatorio=True, regla="R-57.16", seccion=SECCION_ESPECIFICA, ancho=6),
        _campo("valor_modificacion", "Valor de la modificación",
               "Valor por el que se modifica la transacción, impuestos incluidos.", tipo="number",
               seccion=SECCION_ESPECIFICA, ancho=4),
    ],
    "NOTA_DEBITO": [
        _campo("documento_modificado", "Comprobante que modifica",
               "Comprobante de venta al que se cargan intereses de mora o gastos posteriores.",
               obligatorio=True, regla="R-57.16", seccion=SECCION_ESPECIFICA, ancho=6),
        _campo("motivo_modificacion", "Motivo de la modificación",
               "Intereses de mora o recuperación de costos y gastos posteriores a la venta.",
               obligatorio=True, regla="R-57.16", seccion=SECCION_ESPECIFICA, ancho=6),
        _campo("valor_modificacion", "Valor de la modificación",
               "Valor por el que se modifica la transacción.", tipo="number",
               seccion=SECCION_ESPECIFICA, ancho=4),
    ],
    "GUIA_REMISION": [
        _campo("fecha_inicio_traslado", "Fecha de inicio del traslado",
               "La guía se emite ANTES de movilizar la mercadería.", tipo="date", obligatorio=True,
               regla="R-57.19", seccion=SECCION_ESPECIFICA, ancho=4),
        _campo("motivo_traslado", "Motivo del traslado",
               "Venta, devolución, traslado entre locales, exhibición, importación, exportación…",
               obligatorio=True, regla="R-57.19", seccion=SECCION_ESPECIFICA, ancho=8),
        _campo("direccion_partida", "Dirección de partida",
               "Lugar donde se retira la mercadería.", obligatorio=True, regla="R-57.19",
               seccion=SECCION_ESPECIFICA, ancho=6),
        _campo("direccion_destino", "Dirección de destino",
               "Lugar donde se entrega la mercadería.", obligatorio=True, regla="R-57.19",
               seccion=SECCION_ESPECIFICA, ancho=6),
        _campo("transportista", "Conductor o transportista",
               "Quién transporta la mercadería y su identificación.", obligatorio=True,
               regla="R-57.19", seccion=SECCION_ESPECIFICA, ancho=6),
        _campo("placa_vehiculo", "Placa del vehículo",
               "Placa de la unidad de transporte.", obligatorio=True, regla="R-57.19",
               seccion=SECCION_ESPECIFICA, ancho=6),
    ],
    "COMPROBANTE_RETENCION": [
        _campo("impuesto_retenido", "Impuesto que se retiene",
               "Renta, IVA o ISD. Cada impuesto tiene su propia tabla de porcentajes.",
               tipo="select", opciones=IMPUESTOS_RETENCION, obligatorio=True,
               seccion=SECCION_ESPECIFICA, ancho=4),
        _campo("fecha_comprobante_venta", "Fecha del comprobante de venta",
               "Fecha en que el proveedor presentó su comprobante: desde el día siguiente corre el "
               "plazo de entrega de la retención.", tipo="date", obligatorio=True, regla="R-57.12",
               seccion=SECCION_ESPECIFICA, ancho=4),
        _campo("fecha_entrega_retencion", "Fecha de entrega al proveedor",
               "Debe estar disponible dentro de 5 días hábiles (2 si es ISD).", tipo="date",
               regla="R-57.12", seccion=SECCION_ESPECIFICA, ancho=4),
        _campo("base_retencion", "Base de la retención",
               "Valor de la transacción sobre el que se aplica el porcentaje.", tipo="number",
               seccion=SECCION_ESPECIFICA, ancho=4),
        _campo("porcentaje_retencion", "Porcentaje aplicado (%)",
               "Se toma del catálogo de porcentajes del SRI (30 %/70 %/100 % en IVA; 1 %, 2 %, 3 %… "
               "en renta).", tipo="number", obligatorio=True, seccion=SECCION_ESPECIFICA, ancho=4),
        _campo("valor_retenido", "Valor retenido",
               "Base x porcentaje. Es lo que se paga al SRI en nombre del proveedor.",
               tipo="number", obligatorio=True, seccion=SECCION_ESPECIFICA, ancho=4),
    ],
    "LIQUIDACION_COMPRA": [
        _campo("impuesto_retenido", "Impuesto que se retiene",
               "En la liquidación de compra el IVA se retiene al 100 %.", tipo="select",
               opciones=IMPUESTOS_RETENCION, obligatorio=True, regla="R-57.14",
               seccion=SECCION_ESPECIFICA, ancho=4),
        _campo("porcentaje_retencion", "Porcentaje de retención del IVA (%)",
               "Debe ser 100 % para que la liquidación sustente costos y gastos.", tipo="number",
               obligatorio=True, regla="R-57.14", seccion=SECCION_ESPECIFICA, ancho=4),
        _campo("base_retencion", "Base de la retención",
               "Base sobre la que se calcula la retención del IVA.", tipo="number",
               seccion=SECCION_ESPECIFICA, ancho=4),
        _campo("valor_retenido", "Valor retenido", "IVA retenido en la liquidación.", tipo="number",
               seccion=SECCION_ESPECIFICA, ancho=4),
    ],
    "TIQUETE_MAQUINA": [
        _campo("uso_documento", "Para qué se usará el documento",
               "Si el tiquete se quiere usar como soporte de un gasto, el sistema lo rechaza: no "
               "identifica al adquirente.", tipo="select", opciones=USOS_DOCUMENTO,
               regla="R-57.10", seccion=SECCION_ESPECIFICA, ancho=6),
    ],
    "BOLETO_ESPECTACULO": [
        _campo("uso_documento", "Para qué se usará el documento",
               "Los boletos son de consumidor final: no dan crédito tributario ni sustentan gastos.",
               tipo="select", opciones=USOS_DOCUMENTO, regla="R-57.10",
               seccion=SECCION_ESPECIFICA, ancho=6),
    ],
    "NOTA_VENTA_RISE": [
        _campo("adquirente_tipo_id", "Identificación del comprador",
               "Solo se identifica al comprador cuando va a sustentar costos y gastos, por cualquier "
               "monto. La nota de venta no desglosa el IVA.", tipo="select",
               opciones=("CONSUMIDOR_FINAL", "RUC", "CEDULA", "PASAPORTE"),
               seccion=SECCION_ESPECIFICA, ancho=6),
    ],
}


class DocumentoInvalido(ValueError):
    """Error legible para el estudiante cuando el comprobante no puede emitirse."""


class DocumentService:
    # --------------------------------------------------------------------------------------
    # Documentos fuente (capa clásica del simulador)
    # --------------------------------------------------------------------------------------
    @staticmethod
    def register(tipo, numero, fecha, emisor, receptor, monto_total, descripcion="", datos=None,
                 asiento_id=None, simulacion_caso_id=None, db_path=None):
        """Registra un documento fuente. Evita duplicar el mismo tipo+numero+asiento."""
        conn = get_db_contable(db_path)
        try:
            if asiento_id:
                existente = conn.execute("""
                    SELECT id FROM documentos_fuente WHERE tipo = ? AND numero = ? AND asiento_id = ?
                """, (tipo, numero, asiento_id)).fetchone()
                if existente:
                    return existente["id"]

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documentos_fuente
                    (tipo, numero, fecha, emisor, receptor, monto_total, descripcion, datos_json, asiento_id, simulacion_caso_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (tipo, numero, fecha, emisor, receptor, round(float(monto_total), 2), descripcion,
                  json.dumps(datos, ensure_ascii=False) if datos is not None else None,
                  asiento_id, simulacion_caso_id))
            doc_id = cursor.lastrowid
            conn.commit()
            AuditService.log(1, "sistema", "CREAR_DOCUMENTO", "DOCUMENTOS", doc_id, None,
                             {"tipo": tipo, "numero": numero, "monto": round(float(monto_total), 2)},
                             db_path=db_path)
            return doc_id
        finally:
            conn.close()

    @staticmethod
    def get_documents(tipo=None, fecha_inicio=None, fecha_fin=None, limit=300, db_path=None,
                      numero=None, tercero=None, estado=None, categoria=None):
        """Listado de documentos fuente con los filtros del módulo."""
        DocumentService._asegurar_catalogo(db_path)
        conn = get_db_contable(db_path)
        try:
            query = """
                SELECT d.*, a.numero_asiento, a.glosa as asiento_glosa, a.estado as asiento_estado
                FROM documentos_fuente d
                LEFT JOIN asientos a ON d.asiento_id = a.id
                WHERE 1 = 1
            """
            params = []
            if tipo:
                query += " AND d.tipo = ?"
                params.append(tipo)
            if numero:
                query += " AND (d.numero LIKE ? OR COALESCE(d.numero_completo, '') LIKE ?)"
                params.extend(["%%%s%%" % numero, "%%%s%%" % numero])
            if tercero:
                query += (" AND (COALESCE(d.emisor, '') LIKE ? OR COALESCE(d.receptor, '') LIKE ?"
                          " OR COALESCE(d.adquirente_nombre, '') LIKE ?)")
                params.extend(["%%%s%%" % tercero] * 3)
            if estado:
                query += " AND COALESCE(d.estado, 'EMITIDO') = ?"
                params.append(estado)
            if fecha_inicio:
                query += " AND d.fecha >= ?"
                params.append(fecha_inicio)
            if fecha_fin:
                query += " AND d.fecha <= ?"
                params.append(fecha_fin)
            query += " ORDER BY d.fecha DESC, d.id DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(query, params).fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_document(doc_id, db_path=None):
        DocumentService._asegurar_catalogo(db_path)
        conn = get_db_contable(db_path)
        try:
            row = conn.execute("""
                SELECT d.*, a.numero_asiento, a.glosa as asiento_glosa, a.estado as asiento_estado
                FROM documentos_fuente d
                LEFT JOIN asientos a ON d.asiento_id = a.id
                WHERE d.id = ?
            """, (doc_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_tipos_resumen(db_path=None):
        """Resumen por tipo de documento con conteo y monto acumulado."""
        DocumentService._asegurar_catalogo(db_path)
        conn = get_db_contable(db_path)
        try:
            rows = conn.execute("""
                SELECT tipo, COUNT(*) as cantidad, COALESCE(SUM(monto_total), 0) as monto_total
                FROM documentos_fuente
                GROUP BY tipo
                ORDER BY tipo ASC
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_etiqueta(tipo):
        for codigo, etiqueta, _grupo in TIPOS_DOCUMENTO:
            if codigo == tipo:
                return etiqueta
        try:
            conn = get_db_contable()
            try:
                fila = conn.execute("SELECT nombre FROM tipos_documento WHERE codigo = ?",
                                    (tipo,)).fetchone()
                if fila:
                    return fila["nombre"]
            finally:
                conn.close()
        except Exception:
            pass
        return tipo.replace("_", " ").title() if tipo else "Documento"

    @staticmethod
    def estados(usados=()):
        """Estados para el filtro del listado, incluyendo los que ya existen en la base."""
        lista = list(ESTADOS_DOCUMENTO)
        for e in usados or ():
            if e and e not in lista:
                lista.append(e)
        return lista

    # --------------------------------------------------------------------------------------
    # Catálogo normativo del SRI (lee las tablas de datos)
    # --------------------------------------------------------------------------------------
    @staticmethod
    def _asegurar_catalogo(db_path=None):
        """Comprueba que la base de trabajo tenga el catálogo del SRI cargado y, si no lo tiene
        (por ejemplo una base recién creada), lo aplica desde database/esquema_documentos_sri.py.
        Es idempotente y se ejecuta una sola vez por archivo y proceso."""
        try:
            conn = get_db_contable(db_path)
            try:
                ruta = None
                for fila in conn.execute("PRAGMA database_list"):
                    if fila["name"] == "main":
                        ruta = fila["file"]
                        break
                columnas = {r[1] for r in conn.execute("PRAGMA table_info(documentos_fuente)")}
                tablas = {r["name"] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('tipos_documento','reglas_documento')")}
                tipos = reglas = 0
                if len(tablas) == 2:
                    tipos = conn.execute("SELECT COUNT(*) AS c FROM tipos_documento").fetchone()["c"]
                    reglas = conn.execute("SELECT COUNT(*) AS c FROM reglas_documento").fetchone()["c"]
            finally:
                conn.close()
        except Exception:
            return None

        clave = ruta or Config.DATABASE_PATH
        if clave in _BASES_CON_CATALOGO:
            return clave
        faltan_columnas = [c for c in COLUMNAS_COMPROBANTE if c not in columnas]
        if len(tablas) != 2 or not tipos or not reglas or faltan_columnas:
            try:
                from database.esquema_documentos_sri import aplicar, sembrar
                aplicar(clave, verboso=False)
                sembrar(clave, verboso=False)
            except Exception as exc:  # base sin la tabla documentos_fuente, permisos, etc.
                print("[documentos] no se pudo preparar el catálogo del SRI en %s: %s" % (clave, exc))
        _BASES_CON_CATALOGO.add(clave)
        return clave

    @staticmethod
    def catalogo(agrupado_por_categoria=False, db_path=None, solo_activos=True):
        """Tipos de documento del catálogo normativo.

        Con `agrupado_por_categoria=True` devuelve un diccionario {categoría: [tipos]} en el orden
        de CATEGORIA_ETIQUETAS; si no, una lista plana.
        """
        DocumentService._asegurar_catalogo(db_path)
        conn = get_db_contable(db_path)
        try:
            sql = "SELECT * FROM tipos_documento"
            if solo_activos:
                sql += " WHERE COALESCE(activo, 1) = 1"
            sql += " ORDER BY categoria, codigo"
            filas = [dict(r) for r in conn.execute(sql).fetchall()]
        except Exception:
            filas = []
        finally:
            conn.close()

        for fila in filas:
            for campo in ("campos_preimpresos", "campos_llenado", "requisitos"):
                fila[campo] = _json_lista(fila.get(campo))
            fila["categoria_etiqueta"] = CATEGORIA_ETIQUETAS.get(
                fila.get("categoria"), _catalogo_etiqueta(fila.get("categoria")))
            fila["reglas"] = DocumentService.reglas_para(fila["codigo"], db_path=db_path)

        if not agrupado_por_categoria:
            return filas

        agrupado = {}
        for categoria in list(CATEGORIA_ETIQUETAS):
            tipos = [f for f in filas if f.get("categoria") == categoria]
            if tipos:
                agrupado[categoria] = tipos
        for fila in filas:  # categorías que no estén en las etiquetas conocidas
            categoria = fila.get("categoria")
            if categoria not in agrupado:
                agrupado.setdefault(categoria, [])
                if fila not in agrupado[categoria]:
                    agrupado[categoria].append(fila)
        return agrupado

    @staticmethod
    def reglas(db_path=None, aplica_a=None):
        """Todas las reglas activas del catálogo (opcionalmente, las de un tipo de documento)."""
        DocumentService._asegurar_catalogo(db_path)
        conn = get_db_contable(db_path)
        try:
            sql = "SELECT * FROM reglas_documento WHERE COALESCE(activo, 1) = 1 ORDER BY codigo"
            reglas = [dict(r) for r in conn.execute(sql).fetchall()]
        except Exception:
            reglas = []
        finally:
            conn.close()
        for regla in reglas:
            regla["implementada"] = regla["codigo"] in VALIDADORES_IMPLEMENTADOS
        if aplica_a:
            reglas = [r for r in reglas if _regla_aplica(r, aplica_a)]
        return reglas

    @staticmethod
    def reglas_para(tipo_documento, db_path=None):
        """Reglas activas que aplican a un tipo de documento (aplica_a contiene el código o TODO)."""
        return DocumentService.reglas(db_path=db_path, aplica_a=tipo_documento)

    @staticmethod
    def parametros_efectivos(db_path=None):
        """Umbrales y plazos vigentes: los del código, sobrescritos por la tabla `parametros`.

        Clave esperada: `sri.<nombre>` (por ejemplo sri.tope_consumidor_final = 250).
        """
        vigentes = dict(PARAMETROS_DOCUMENTO)
        try:
            conn = get_db_contable(db_path)
            try:
                filas = conn.execute("SELECT clave, valor FROM parametros WHERE clave LIKE 'sri.%'")
                for fila in filas:
                    nombre = fila["clave"][4:]
                    if nombre not in vigentes:
                        continue
                    valor = fila["valor"]
                    referencia = vigentes[nombre]
                    if isinstance(referencia, bool):
                        vigentes[nombre] = _texto(valor).lower() in ("1", "true", "si", "sí", "on")
                    elif isinstance(referencia, (int, float)) and not isinstance(referencia, bool):
                        numero = _a_float(valor, None)
                        if numero is not None:
                            vigentes[nombre] = int(numero) if isinstance(referencia, int) else numero
                    elif isinstance(referencia, list):
                        vigentes[nombre] = [x.strip() for x in _texto(valor).split(",") if x.strip()]
                    else:
                        vigentes[nombre] = valor
            finally:
                conn.close()
        except Exception:
            pass
        return vigentes

    @staticmethod
    def porcentajes_disponibles(tipo_documento=None, db_path=None):
        """Porcentajes del catálogo tributario (tabla `impuestos`) que sirven para el comprobante.

        Una factura necesita las tarifas de IVA; un comprobante de retención o una liquidación de
        compra, los porcentajes de retención (IVA 30/70/100 %, renta 1 %, 2 %, 3 %…).
        """
        conn = get_db_contable(db_path)
        try:
            filas = [dict(r) for r in conn.execute("""
                SELECT codigo, nombre, porcentaje, tipo, aplica_a, codigo_sri, fuente
                FROM impuestos WHERE COALESCE(activo, 1) = 1
                ORDER BY tipo, porcentaje
            """).fetchall()]
        except Exception:
            filas = []
        finally:
            conn.close()

        if not tipo_documento:
            return filas
        clave = _texto(tipo_documento).upper()
        prefijos = PORCENTAJES_POR_TIPO.get(clave)
        if prefijos is None:
            ficha = DocumentService.tipo_documento(clave, db_path=db_path) or {}
            categoria = _texto(ficha.get("categoria")).upper()
            prefijos = ("RET",) if categoria == "RETENCION" else ("IVA",)
        return [f for f in filas if _texto(f.get("tipo")).upper().startswith(tuple(prefijos))]

    # --------------------------------------------------------------------------------------
    # Campos del formulario
    # --------------------------------------------------------------------------------------
    @staticmethod
    def tipo_documento(tipo_documento, db_path=None):
        """Ficha completa de un tipo del catálogo (o None)."""
        for ficha in DocumentService.catalogo(db_path=db_path):
            if ficha["codigo"] == _texto(tipo_documento).upper():
                return ficha
        return None

    @staticmethod
    def campos_formulario(tipo_documento, db_path=None):
        """Campos que el estudiante debe llenar para emitir el tipo elegido.

        Se arma con los campos comunes más los propios del tipo; cada campo indica su explicación y
        la regla del reglamento con la que se valida. Junto a ellos, la plantilla muestra el detalle
        normativo (`campos_llenado`, `campos_preimpresos`, `requisitos`) del catálogo.
        """
        tipo = _texto(tipo_documento).upper()
        campos = [dict(c) for c in CAMPOS_BASE]
        especificos = CAMPOS_POR_TIPO.get(tipo, [])
        for campo in especificos:
            base = next((c for c in campos if c["nombre"] == campo["nombre"]), None)
            if base:  # permite que un tipo redefina el comportamiento de un campo común
                base.update(campo)
            else:
                campos.append(dict(campo))
        secciones = []
        for campo in campos:
            if not secciones or secciones[-1]["titulo"] != campo["seccion"]:
                secciones.append({"titulo": campo["seccion"], "campos": []})
            secciones[-1]["campos"].append(campo)
        return secciones

    # --------------------------------------------------------------------------------------
    # Validación de comprobantes
    # --------------------------------------------------------------------------------------
    @staticmethod
    def revisar_documento(tipo, datos, db_path=None):
        """Ejecuta todas las reglas que aplican al tipo y devuelve el detalle por regla.

        {ok, errores, advertencias, reglas: [{codigo, titulo, severidad, resultado, mensajes}]}
        resultado ∈ {CUMPLE, INCUMPLE, ADVIERTE, INFORMATIVA, NO_IMPLEMENTADA}
        """
        tipo = _texto(tipo).upper()
        datos = dict(datos or {})
        parametros = DocumentService.parametros_efectivos(db_path)
        reglas = DocumentService.reglas_para(tipo, db_path=db_path)
        errores, advertencias, detalle = [], [], []

        for regla in reglas:
            validador = VALIDADORES_IMPLEMENTADOS.get(regla["codigo"])
            if validador is None:
                mensaje = _mensaje_catalogo(regla)
                advertencias.append(mensaje)
                detalle.append({
                    "codigo": regla["codigo"], "titulo": regla["titulo"],
                    "severidad": regla["severidad"], "resultado": "NO_IMPLEMENTADA",
                    "regla": regla["regla"], "validacion": regla["validacion"],
                    "pagina_fuente": regla["pagina_fuente"], "mensajes": [mensaje],
                })
                continue

            try:
                hallazgos = validador(tipo, datos, parametros, regla, db_path)
            except Exception as exc:  # nunca debe romper la emisión por un dato raro
                hallazgos = [("ADVERTENCIA", _rotular(
                    regla, "No se pudo verificar esta regla: %s" % exc))]

            resultado = "CUMPLE"
            mensajes = []
            for severidad, mensaje in hallazgos:
                mensajes.append(mensaje)
                if severidad == "BLOQUEO":
                    errores.append(mensaje)
                    resultado = "INCUMPLE"
                else:
                    advertencias.append(mensaje)
                    if resultado != "INCUMPLE":
                        resultado = "ADVIERTE" if severidad == "ADVERTENCIA" else "INFORMATIVA"
            detalle.append({
                "codigo": regla["codigo"], "titulo": regla["titulo"],
                "severidad": regla["severidad"], "resultado": resultado,
                "regla": regla["regla"], "validacion": regla["validacion"],
                "pagina_fuente": regla["pagina_fuente"],
                "mensajes": mensajes or [_mensaje_catalogo(regla)],
            })

        return {"ok": not errores, "errores": errores, "advertencias": advertencias,
                "reglas": detalle, "tipo": tipo}

    @staticmethod
    def validar_documento(tipo, datos, db_path=None):
        """Valida un comprobante contra las reglas del reglamento.

        Devuelve (ok, errores, advertencias): dos listas de mensajes ya redactados para el
        estudiante. Si no hay errores, el documento puede emitirse.
        """
        revision = DocumentService.revisar_documento(tipo, datos, db_path=db_path)
        return revision["ok"], revision["errores"], revision["advertencias"]

    # --------------------------------------------------------------------------------------
    # Emisión, anulación y ayuda didáctica
    # --------------------------------------------------------------------------------------
    @staticmethod
    def emitir_documento(tipo, datos, db_path=None):
        """Valida y emite el comprobante. Devuelve el documento creado.

        Lanza DocumentoInvalido (ValueError) con los bloqueos redactados si no puede emitirse.
        """
        tipo = _texto(tipo).upper()
        datos = dict(datos or {})
        revision = DocumentService.revisar_documento(tipo, datos, db_path=db_path)
        if revision["errores"]:
            raise DocumentoInvalido(
                "El comprobante no se emitió porque incumple el reglamento:\n- "
                + "\n- ".join(revision["errores"]))
        if not revision["reglas"]:
            raise DocumentoInvalido(
                "El tipo de documento «%s» no existe en el catálogo del SRI." % (tipo or "(vacío)"))

        parametros = DocumentService.parametros_efectivos(db_path)
        ficha = DocumentService.tipo_documento(tipo, db_path=db_path) or {"nombre": tipo}
        est, pto, sec = _partes_numeracion(datos, parametros)
        numero_completo = _armar_numero_completo(datos, parametros) or _texto(
            datos.get("numero") or datos.get("numero_completo"))
        fecha = _fecha_emision(datos).isoformat()
        leyenda = _texto(parametros.get("leyenda_educativa"))

        total = _total_documento(datos)
        subtotal_declarado = _a_float(datos.get("subtotal"), None)
        if subtotal_declarado is None:
            # Sin subtotal declarado se reconstruye a partir del total y sus componentes.
            subtotal = round(max(total - (_a_float(datos.get("iva_valor"), 0.0) or 0.0)
                                 - (_a_float(datos.get("ice_valor"), 0.0) or 0.0)
                                 - (_a_float(datos.get("propina"), 0.0) or 0.0)
                                 + (_a_float(datos.get("descuento"), 0.0) or 0.0), 0.0), 2)
        else:
            subtotal = subtotal_declarado
        emisor = _texto(datos.get("emisor")) or Config.COMPANY_NAME
        ruc_emisor = _texto(datos.get("ruc_emisor")) or Config.COMPANY_RUC
        adquirente_nombre = _texto(datos.get("adquirente_nombre")) or _texto(datos.get("receptor"))

        desglose = {
            "subtotal": round(_a_float(datos.get("subtotal"), subtotal) or 0.0, 2),
            "descuento": round(_a_float(datos.get("descuento"), 0.0) or 0.0, 2),
            "iva_tarifa": _a_float(datos.get("iva_tarifa"), None),
            "iva_valor": round(_a_float(datos.get("iva_valor"), 0.0) or 0.0, 2),
            "ice_valor": round(_a_float(datos.get("ice_valor"), 0.0) or 0.0, 2),
            "propina": round(_a_float(datos.get("propina"), 0.0) or 0.0, 2),
            "total": total,
        }
        contenido = {
            "tipo_documento": tipo,
            "nombre_documento": ficha.get("nombre"),
            "comprobante": {
                "numero_completo": numero_completo,
                "establecimiento": est, "punto_emision": pto, "secuencial": sec,
                "fecha": fecha,
                "numero_autorizacion": _texto(datos.get("numero_autorizacion")),
                "fecha_autorizacion": _texto(datos.get("fecha_autorizacion")),
                "fecha_caducidad_autorizacion": _texto(datos.get("fecha_caducidad_autorizacion")),
                "tipo_emision": _texto(datos.get("tipo_emision")) or "NORMAL",
                "ruc_emisor": ruc_emisor, "emisor": emisor,
                "adquirente_tipo_id": _texto(datos.get("adquirente_tipo_id")),
                "adquirente_identificacion": _texto(datos.get("adquirente_identificacion")),
                "adquirente_nombre": adquirente_nombre,
                "forma_pago": _texto(datos.get("forma_pago")),
                "documento_modificado": _texto(datos.get("documento_modificado")),
                "motivo_modificacion": _texto(datos.get("motivo_modificacion")),
                "valor_modificacion": _a_float(datos.get("valor_modificacion"), None),
                "impuesto_retenido": _texto(datos.get("impuesto_retenido")),
                "base_retencion": _a_float(datos.get("base_retencion"), None),
                "porcentaje_retencion": _a_float(datos.get("porcentaje_retencion"), None),
                "valor_retenido": _a_float(datos.get("valor_retenido"), None),
                "fecha_comprobante_venta": _texto(datos.get("fecha_comprobante_venta")),
                "fecha_entrega_retencion": _texto(datos.get("fecha_entrega_retencion")),
                "motivo_traslado": _texto(datos.get("motivo_traslado")),
                "direccion_partida": _texto(datos.get("direccion_partida")),
                "direccion_destino": _texto(datos.get("direccion_destino")),
                "transportista": _texto(datos.get("transportista")),
                "placa_vehiculo": _texto(datos.get("placa_vehiculo")),
                "fecha_inicio_traslado": _texto(datos.get("fecha_inicio_traslado")
                                                or datos.get("fecha_traslado")),
                "uso_documento": _texto(datos.get("uso_documento")),
                "descripcion": _texto(datos.get("descripcion")),
            },
            "desglose": desglose,
            "partes_numeracion": {"establecimiento": est, "punto_emision": pto, "secuencial": sec},
            "reglas_aplicadas": [r["codigo"] for r in revision["reglas"]],
            "advertencias": revision["advertencias"],
            "leyenda_educativa": leyenda,
            "pagina_fuente": ficha.get("pagina_fuente"),
        }

        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documentos_fuente
                    (tipo, numero, fecha, emisor, receptor, monto_total, descripcion, datos_json,
                     estado, ruc_emisor, numero_autorizacion, fecha_autorizacion, establecimiento,
                     punto_emision, secuencial, numero_completo, tipo_emision, adquirente_tipo_id,
                     adquirente_identificacion, adquirente_nombre, forma_pago, subtotal, descuento,
                     iva_tarifa, iva_valor, ice_valor, propina, documento_modificado,
                     motivo_modificacion, base_retencion, porcentaje_retencion, valor_retenido,
                     impuesto_retenido, fecha_entrega_retencion, valor_modificacion, motivo_traslado,
                     direccion_partida, direccion_destino, transportista, placa_vehiculo,
                     origen_actividad_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                tipo, numero_completo, fecha, emisor, adquirente_nombre, total,
                _texto(datos.get("descripcion")), json.dumps(contenido, ensure_ascii=False),
                "EMITIDO", ruc_emisor, _texto(datos.get("numero_autorizacion")),
                _texto(datos.get("fecha_autorizacion")) or None, est, pto, sec, numero_completo,
                contenido["comprobante"]["tipo_emision"], _texto(datos.get("adquirente_tipo_id")),
                _texto(datos.get("adquirente_identificacion")), adquirente_nombre,
                _texto(datos.get("forma_pago")), desglose["subtotal"], desglose["descuento"],
                desglose["iva_tarifa"], desglose["iva_valor"], desglose["ice_valor"],
                desglose["propina"], _texto(datos.get("documento_modificado")) or None,
                _texto(datos.get("motivo_modificacion")) or None,
                _a_float(datos.get("base_retencion"), None),
                _a_float(datos.get("porcentaje_retencion"), None),
                _a_float(datos.get("valor_retenido"), None),
                _texto(datos.get("impuesto_retenido")) or None,
                _texto(datos.get("fecha_entrega_retencion")) or None,
                _a_float(datos.get("valor_modificacion"), None),
                _texto(datos.get("motivo_traslado")) or None,
                _texto(datos.get("direccion_partida")) or None,
                _texto(datos.get("direccion_destino")) or None,
                _texto(datos.get("transportista")) or None,
                _texto(datos.get("placa_vehiculo")) or None,
                _a_float(datos.get("origen_actividad_id"), None),
            ))
            doc_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()

        AuditService.log(1, _texto(datos.get("usuario")) or "estudiante", "EMITIR_COMPROBANTE",
                         "DOCUMENTOS", doc_id, None,
                         {"tipo": tipo, "numero_completo": numero_completo, "total": total},
                         db_path=db_path)
        documento = DocumentService.get_document(doc_id, db_path=db_path)
        if documento is not None:
            documento["advertencias"] = revision["advertencias"]
        return documento

    @staticmethod
    def anular_documento(doc_id, motivo, usuario="estudiante", db_path=None):
        """Anula un comprobante con su motivo. Nunca borra la fila (R-57.21)."""
        motivo = _texto(motivo)
        if not motivo:
            raise DocumentoInvalido(
                "Para anular o dar de baja un comprobante debes indicar el motivo (Art. 49 del "
                "reglamento). El documento se conserva en el archivo, nunca se elimina.")
        conn = get_db_contable(db_path)
        try:
            fila = conn.execute("SELECT * FROM documentos_fuente WHERE id = ?", (doc_id,)).fetchone()
            if not fila:
                raise DocumentoInvalido("El documento %s no existe." % doc_id)
            documento = dict(fila)
            estado = _texto(documento.get("estado") or "EMITIDO").upper()
            if estado == "ANULADO":
                raise DocumentoInvalido("El comprobante %s ya está ANULADO."
                                        % (documento.get("numero") or doc_id))
            try:
                contenido = json.loads(documento.get("datos_json") or "{}")
            except (TypeError, ValueError):
                contenido = {}
            contenido["anulacion"] = {
                "motivo": motivo,
                "fecha": _fecha_emision({}).isoformat(),
                "usuario": _texto(usuario) or "estudiante",
                "estado_anterior": estado,
            }
            contenido["leyenda_educativa"] = _texto(
                DocumentService.parametros_efectivos(db_path).get("leyenda_educativa"))
            conn.execute("UPDATE documentos_fuente SET estado = 'ANULADO', datos_json = ? WHERE id = ?",
                         (json.dumps(contenido, ensure_ascii=False), doc_id))
            conn.commit()
        finally:
            conn.close()

        AuditService.log(1, _texto(usuario) or "estudiante", "ANULAR_DOCUMENTO", "DOCUMENTOS", doc_id,
                         {"estado": "EMITIDO"}, {"estado": "ANULADO", "motivo": motivo},
                         db_path=db_path)
        return DocumentService.get_document(doc_id, db_path=db_path)

    @staticmethod
    def soporte_sugerido(tipo_transaccion, contexto=None, db_path=None):
        """Qué documento corresponde a una operación y POR QUÉ (ayuda didáctica).

        Devuelve {clave, tipo, nombre, por_que, acompanantes, reglas, alternativas, aviso}.
        """
        contexto = dict(contexto or {})
        clave = _clave_soporte(tipo_transaccion)
        # Ajustes por contexto (los casos particulares se explican solos).
        if contexto.get("es_rise") or contexto.get("regimen") == "RISE":
            clave = "VENTA_RISE"
        if contexto.get("requiere_traslado"):
            clave = "TRASLADO"
        if contexto.get("es_isd") and clave == "RETENCION":
            clave = "RETENCION"
        if contexto.get("proveedor_tiene_ruc") is False and clave in ("COMPRA_BIENES", "COMPRA_SERVICIOS"):
            clave = "COMPRA_A_NO_OBLIGADO"
        if contexto.get("es_consumidor_final") and clave in ("VENTA_BIENES", "VENTA_SERVICIOS"):
            clave = "VENTA_CONSUMIDOR_FINAL"
        if contexto.get("es_turistico"):
            clave = "VENTA_SERVICIOS_TURISTICOS"
        if contexto.get("es_vehiculo_usado"):
            clave = "COMPRA_VEHICULO_USADO"

        ficha = TABLA_SOPORTE.get(clave)
        if not ficha:
            return {
                "clave": clave, "tipo": None, "nombre": None,
                "por_que": ("No reconozco esa operación. Prueba con: compra de bienes, compra de "
                            "servicios, compra a quien no tiene RUC, venta, venta al consumidor "
                            "final, traslado de mercadería, retención, devolución o descuento, "
                            "cobro de intereses de mora."),
                "acompanantes": [], "reglas": [], "alternativas": sorted(TABLA_SOPORTE),
                "aviso": None,
            }

        tipo = ficha["tipo"]
        catalogo_tipo = DocumentService.tipo_documento(tipo, db_path=db_path) or {}
        por_que = ficha["por_que"]
        aviso = None
        if tipo == "FACTURA" and contexto.get("es_consumidor_final"):
            tope = _a_float(DocumentService.parametros_efectivos(db_path).get("tope_consumidor_final"), 200.0)
            aviso = ("Sin identificar al cliente, el total no puede superar %s."
                     % _formato_usd(tope))
        elif tipo == "TIQUETE_MAQUINA":
            aviso = ("No lo uses como soporte del gasto: pide el cambio por factura o nota de venta "
                     "(R-57.10).")
        elif tipo == "COMPROBANTE_RETENCION":
            params = DocumentService.parametros_efectivos(db_path)
            dias = params.get("dias_habiles_retencion_isd") if contexto.get("es_isd") else params.get("dias_habiles_retencion")
            aviso = ("Debe estar disponible para el proveedor dentro de %s días hábiles."
                     % dias)
        elif tipo == "GUIA_REMISION":
            aviso = "Se emite ANTES de iniciar el traslado (R-57.19)."

        alternativas = []
        for otra_clave, otra in TABLA_SOPORTE.items():
            if otra["tipo"] == tipo or otra_clave == clave:
                continue
            alternativas.append({"clave": otra_clave, "tipo": otra["tipo"],
                                 "nombre": (DocumentService.tipo_documento(otra["tipo"], db_path=db_path)
                                            or {}).get("nombre")})

        return {
            "clave": clave,
            "tipo": tipo,
            "nombre": catalogo_tipo.get("nombre") or _catalogo_etiqueta(tipo),
            "categoria": catalogo_tipo.get("categoria"),
            "cuando_se_emite": catalogo_tipo.get("cuando_se_emite"),
            "emisor": catalogo_tipo.get("emisor"),
            "por_que": por_que,
            "acompanantes": [
                {"tipo": t, "nombre": (DocumentService.tipo_documento(t, db_path=db_path) or {}).get("nombre")
                 or _catalogo_etiqueta(t)} for t in ficha.get("acompanantes", [])
            ],
            "reglas": DocumentService.reglas_para(tipo, db_path=db_path),
            "requisitos": catalogo_tipo.get("requisitos", []),
            "alternativas": alternativas,
            "aviso": aviso,
        }

    @staticmethod
    def datos_desde_documento(documento):
        """Reconstruye el diccionario de datos con el que se validó/emitió un documento guardado."""
        if not documento:
            return {}
        documento = dict(documento)
        datos = {}
        try:
            contenido = json.loads(documento.get("datos_json") or "{}")
        except (TypeError, ValueError):
            contenido = {}
        if isinstance(contenido, dict):
            datos.update(contenido.get("comprobante") or {})
            datos["leyenda_educativa"] = contenido.get("leyenda_educativa")
            datos["reglas_aplicadas"] = contenido.get("reglas_aplicadas") or []
            datos["anulacion"] = contenido.get("anulacion")
            datos["desglose"] = contenido.get("desglose")
        # Identificador propio: al revalidar un comprobante guardado, su propia numeración
        # no debe contarse como duplicada.
        datos["_documento_id"] = documento.get("id")
        for clave in ("fecha", "establecimiento", "punto_emision", "secuencial", "numero_completo",
                      "numero_autorizacion", "fecha_autorizacion", "tipo_emision", "adquirente_tipo_id",
                      "adquirente_identificacion", "adquirente_nombre", "forma_pago", "subtotal",
                      "descuento", "iva_tarifa", "iva_valor", "ice_valor", "propina", "monto_total",
                      "documento_modificado", "motivo_modificacion", "base_retencion",
                      "porcentaje_retencion", "valor_retenido", "impuesto_retenido",
                      "fecha_entrega_retencion", "valor_modificacion", "motivo_traslado",
                      "direccion_partida", "direccion_destino", "transportista", "placa_vehiculo"):
            if datos.get(clave) in (None, "") and documento.get(clave) not in (None, ""):
                datos[clave] = documento.get(clave)
        datos["tipo_documento"] = documento.get("tipo")
        return datos

    @staticmethod
    def desglose_documento(documento):
        """Desglose de valores de un comprobante emitido (para el detalle)."""
        datos = DocumentService.datos_desde_documento(documento)
        desglose = datos.get("desglose")
        if isinstance(desglose, dict) and desglose:
            return desglose
        return {
            "subtotal": _a_float(datos.get("subtotal"), 0.0) or 0.0,
            "descuento": _a_float(datos.get("descuento"), 0.0) or 0.0,
            "iva_tarifa": _a_float(datos.get("iva_tarifa"), None),
            "iva_valor": _a_float(datos.get("iva_valor"), 0.0) or 0.0,
            "ice_valor": _a_float(datos.get("ice_valor"), 0.0) or 0.0,
            "propina": _a_float(datos.get("propina"), 0.0) or 0.0,
            "total": _a_float(documento.get("monto_total"), 0.0) or 0.0,
        }

    @staticmethod
    def leyenda_educativa(db_path=None):
        """Leyenda que debe imprimirse en todo comprobante del simulador (R-57.23)."""
        return _texto(DocumentService.parametros_efectivos(db_path).get("leyenda_educativa"))


def _json_lista(valor):
    """Convierte a lista un campo que puede venir como JSON, lista o texto."""
    if valor is None:
        return []
    if isinstance(valor, list):
        return valor
    if isinstance(valor, (tuple, set)):
        return list(valor)
    texto = _texto(valor)
    if not texto:
        return []
    try:
        decodificado = json.loads(texto)
    except (TypeError, ValueError):
        return [texto]
    if isinstance(decodificado, list):
        return decodificado
    return [texto]


def _regla_aplica(regla, tipo_documento):
    """True si la regla aplica al tipo de documento (aplica_a = TODO o CSV de códigos)."""
    aplica = _texto(regla.get("aplica_a") or "TODO").upper()
    if aplica in ("TODO", "TODOS", "*", ""):
        return True
    codigos = [c.strip().upper() for c in aplica.split(",") if c.strip()]
    return _texto(tipo_documento).upper() in codigos
