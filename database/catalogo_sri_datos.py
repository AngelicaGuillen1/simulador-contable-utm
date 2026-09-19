# -*- coding: utf-8 -*-
"""catalogo_sri_datos.py — catálogo normativo de documentos fuente (Ecuador).

DATOS, no código: aquí vive el catálogo de tipos de documento y las reglas de negocio que el
simulador usa para validar los comprobantes que emiten los estudiantes. Se siembra con
`python database/esquema_documentos_sri.py`.

Fuente: Reglamento de comprobantes de venta, retención y documentos complementarios (D.E. 430) y
formatos oficiales del SRI, según la sección 57 del Prompt Maestro v2. Cada entrada cita la página
de la fuente. Los umbrales y plazos son DATO CONFIGURABLE: deben verificarse en la normativa vigente
antes de usarse como referencia real.
"""

# Campos preimpresos comunes (Art. 18) y de llenado de la factura (Art. 19).
PREIMPRESOS_ART18 = [
    "Número, día, mes y año de la autorización de impresión (SRI)",
    "RUC del emisor",
    "Apellidos y nombres o razón social del emisor",
    "Denominación del documento",
    "Numeración de 15 dígitos (establecimiento 3 + punto de emisión 3 + secuencial 9)",
    "Dirección de la matriz y del establecimiento emisor",
    "Fecha de caducidad de la autorización",
    "Datos del establecimiento gráfico (RUC, razón social, N° de autorización)",
    "Destinatarios de los ejemplares (original al adquirente, copia al emisor)",
    "Leyenda «Contribuyente Especial» con N° de resolución, si aplica",
    "Leyenda «Contribuyente RISE / Régimen Simplificado», si aplica",
    "Frase «Obligado a Llevar Contabilidad», si aplica",
]

LLENADO_FACTURA_ART19 = [
    "Identificación del adquirente: nombres o razón social y RUC / cédula / pasaporte",
    "Descripción o concepto del bien o servicio, con cantidad y unidad de medida",
    "Precio unitario",
    "Valor subtotal de la transacción sin impuestos",
    "Descuentos o bonificaciones, cuando existan",
    "IVA señalando la tarifa",
    "Propina (solo hoteles, bares y restaurantes calificados)",
    "Impuesto a la salida de divisas percibido, cuando aplique",
    "ICE por separado, cuando aplique",
    "Importe total de la transacción",
    "Signo y denominación de la moneda, si es distinta a la de curso legal",
    "Fecha de emisión",
    "Número de las guías de remisión, cuando corresponda",
    "Firma del adquirente como constancia de entrega",
]

LLENADO_NOTA_AJUSTE = [
    "Apellidos y nombres o razón social del adquirente",
    "RUC / cédula / pasaporte del adquirente",
    "Denominación y número del comprobante de venta que se modifica",
    "Razón por la que se efectúa la modificación",
    "Valor por el que se modifica la transacción",
    "ICE correspondiente, cuando proceda",
    "IVA respectivo",
    "Valor total de la modificación incluido impuestos",
    "Fecha de emisión",
]

TIPOS_DOCUMENTO = [
    {
        "codigo": "FACTURA",
        "nombre": "Factura",
        "categoria": "COMPROBANTE_VENTA",
        "cuando_se_emite": "Con ocasión de la transferencia de bienes, la prestación de servicios o "
                           "la realización de otras transacciones gravadas con impuestos.",
        "emisor": "Todo sujeto pasivo que realice la transacción, aunque el adquirente no la solicite.",
        "acompanantes": "Guía de remisión cuando hay traslado de mercadería; comprobante de retención "
                        "cuando el comprador actúa como agente de retención.",
        "campos_preimpresos": PREIMPRESOS_ART18,
        "campos_llenado": LLENADO_FACTURA_ART19,
        "requisitos": [
            "Desglose de impuestos obligatorio si el adquirente sustenta crédito tributario o gastos personales.",
            "A consumidores finales no se desglosa el impuesto.",
            "Cada factura se totaliza y cierra individualmente; original y copias se emiten juntos.",
            "La forma de pago es campo del formato oficial, no un requisito del Art. 19.",
        ],
        "pagina_fuente": "Art. 11 p. 8; Art. 18 p. 11-13; Art. 19 p. 13-15; Art. 20 p. 15",
    },
    {
        "codigo": "NOTA_VENTA_RISE",
        "nombre": "Nota de venta (RISE / Régimen Simplificado)",
        "categoria": "COMPROBANTE_VENTA",
        "cuando_se_emite": "La emiten exclusivamente los contribuyentes inscritos en el Régimen Simplificado.",
        "emisor": "Contribuyente del RISE.",
        "acompanantes": "—",
        "campos_preimpresos": PREIMPRESOS_ART18,
        "campos_llenado": [
            "Descripción o concepto, con cantidad y unidad de medida",
            "Precio de los bienes o servicios incluyendo impuestos",
            "Importe total de la transacción incluyendo impuestos y propina",
            "Fecha de emisión",
            "RUC o cédula y nombre del comprador, si este va a sustentar costos y gastos (por cualquier monto)",
        ],
        "requisitos": [
            "No desglosa el IVA.",
            "Cada nota se totaliza y cierra individualmente.",
        ],
        "pagina_fuente": "Art. 12 p. 8; Art. 21 p. 15",
    },
    {
        "codigo": "LIQUIDACION_COMPRA",
        "nombre": "Liquidación de compra de bienes y prestación de servicios",
        "categoria": "COMPROBANTE_VENTA",
        "cuando_se_emite": "En adquisiciones a personas no residentes, sociedades extranjeras sin "
                           "domicilio, personas naturales no obligadas a llevar contabilidad ni inscritas "
                           "en el RUC que no puedan emitir comprobantes, y compras al propio empleado.",
        "emisor": "El adquirente (agente de retención).",
        "acompanantes": "Comprobante de retención del 100 % del IVA y del porcentaje de renta.",
        "campos_preimpresos": PREIMPRESOS_ART18,
        "campos_llenado": [
            "Nombres y apellidos del proveedor",
            "Cédula o pasaporte del proveedor",
            "Domicilio del proveedor (provincia, ciudad y lugar de la operación)",
            "Descripción del bien o servicio, con cantidad y unidad de medida",
            "Precios unitarios",
            "Subtotal sin IVA",
            "IVA con la tarifa aplicada",
            "Importe total con impuestos",
            "Fecha de emisión",
        ],
        "requisitos": [
            "Debe practicarse la retención del 100 % del IVA y el porcentaje correspondiente de renta "
            "para que dé crédito tributario y sustente costos y gastos.",
            "No sirve si el proveedor tiene RUC activo a la fecha de la transacción.",
        ],
        "pagina_fuente": "Art. 13 p. 8-9; Art. 22 p. 15-16",
    },
    {
        "codigo": "TIQUETE_MAQUINA",
        "nombre": "Tiquete emitido por máquinas registradoras",
        "categoria": "COMPROBANTE_VENTA",
        "cuando_se_emite": "Solo en transacciones con consumidores finales, con máquinas de programa cerrado autorizadas.",
        "emisor": "Contribuyente autorizado que además posee facturas o notas de venta autorizadas.",
        "acompanantes": "Copia o cinta testigo de la propia máquina.",
        "campos_preimpresos": [
            "RUC, nombre o razón social y domicilio del emisor",
            "Número secuencial autogenerado de al menos 4 dígitos",
            "Marca, modelo de fabricación y número de serie de la máquina",
            "Número de autorización otorgado por el SRI",
            "Denominación «Tiquete», opcional",
        ],
        "campos_llenado": [
            "Descripción o concepto del bien o servicio",
            "Importe de la venta o servicio, con el impuesto desglosado si corresponde",
            "Fecha y hora de emisión",
            "Destino opcional de los ejemplares",
        ],
        "requisitos": [
            "No da lugar a crédito tributario de IVA ni sustenta costos y gastos: no identifica al adquirente.",
            "El adquirente puede exigir el cambio por factura o nota de venta, y el emisor debe hacerlo de inmediato.",
            "La máquina debe ser de programa cerrado y no permitir alterar los datos de control.",
        ],
        "pagina_fuente": "Art. 14 p. 9; Art. 23 p. 16-17; Art. 43 p. 29",
    },
    {
        "codigo": "BOLETO_ESPECTACULO",
        "nombre": "Boletos o entradas a espectáculos públicos",
        "categoria": "COMPROBANTE_VENTA",
        "cuando_se_emite": "Al emitir entradas a espectáculos públicos.",
        "emisor": "El organizador, con documentos preimpresos o sistema computarizado autorizado.",
        "acompanantes": "—",
        "campos_preimpresos": [
            "Número, día, mes y año de la autorización de impresión",
            "RUC del emisor",
            "Apellidos y nombres o razón social del emisor",
            "Denominación «Boleto»",
            "Numeración de 15 dígitos",
            "Fecha de caducidad de la autorización",
            "Datos de la imprenta",
        ],
        "campos_llenado": ["Importe total incluido impuestos"],
        "requisitos": [
            "Solo para consumidores finales: no da crédito tributario ni sustenta costos y gastos.",
            "Baja obligatoria si no se usan para el espectáculo autorizado.",
        ],
        "pagina_fuente": "Art. 14 p. 9; Art. 24 p. 17; Art. 49.14 p. 34",
    },
    {
        "codigo": "NOTA_CREDITO",
        "nombre": "Nota de crédito",
        "categoria": "COMPLEMENTARIO",
        "cuando_se_emite": "Para anular operaciones, aceptar devoluciones y conceder descuentos o bonificaciones.",
        "emisor": "El vendedor que emitió el comprobante original.",
        "acompanantes": "Comprobante de venta que modifica.",
        "campos_preimpresos": PREIMPRESOS_ART18,
        "campos_llenado": LLENADO_NOTA_AJUSTE,
        "requisitos": [
            "Debe consignar la denominación, serie y número del comprobante que modifica.",
            "El adquirente anota en original y copia su nombre, identificación y fecha de recepción.",
            "No puede modificar facturas comerciales negociables ya negociadas.",
        ],
        "pagina_fuente": "Art. 15 p. 10; Art. 25 p. 17-18",
    },
    {
        "codigo": "NOTA_DEBITO",
        "nombre": "Nota de débito",
        "categoria": "COMPLEMENTARIO",
        "cuando_se_emite": "Para cobrar intereses de mora y recuperar costos y gastos incurridos por el "
                           "vendedor después de emitido el comprobante de venta.",
        "emisor": "El vendedor que emitió el comprobante original.",
        "acompanantes": "Comprobante de venta que modifica.",
        "campos_preimpresos": PREIMPRESOS_ART18,
        "campos_llenado": LLENADO_NOTA_AJUSTE,
        "requisitos": [
            "Debe referenciar el comprobante que modifica.",
            "No puede modificar facturas comerciales negociables ya negociadas.",
        ],
        "pagina_fuente": "Art. 16 p. 10; Art. 25 p. 17-18",
    },
    {
        "codigo": "GUIA_REMISION",
        "nombre": "Guía de remisión",
        "categoria": "COMPLEMENTARIO",
        "cuando_se_emite": "Sustenta el traslado de mercaderías dentro del territorio nacional y se emite "
                           "ANTES del traslado.",
        "emisor": "Sociedades y personas naturales obligadas, en los 13 supuestos del Art. 28.",
        "acompanantes": "Comprobante de venta que respalda la mercadería trasladada (con excepciones).",
        "campos_preimpresos": PREIMPRESOS_ART18,
        "campos_llenado": [
            "Identificación del destinatario (RUC / cédula / pasaporte y nombres o razón social)",
            "Direcciones de punto de partida y destino(s)",
            "Identificación del conductor",
            "Placas del vehículo",
            "Identificación del remitente, cuando la guía la emite el transportista o el destinatario",
            "Descripción detallada de las mercaderías: denominación, características, unidad de medida y cantidad",
            "Motivo del traslado",
            "Denominación, número de autorización, fecha de emisión y numeración del comprobante de venta",
            "Número de declaración aduanera, cuando corresponda",
            "Fechas de inicio y terminación del traslado",
        ],
        "requisitos": [
            "Se emite antes del traslado, en forma nítida y sin tachones ni enmendaduras.",
            "Debe portarla cada unidad de transporte.",
            "El destinatario la conserva en un archivo ordenado secuencialmente.",
        ],
        "pagina_fuente": "Art. 27-30 p. 18-23; Art. 36 p. 23-24",
    },
    {
        "codigo": "COMPROBANTE_RETENCION",
        "nombre": "Comprobante de retención",
        "categoria": "RETENCION",
        "cuando_se_emite": "Al pagar o acreditar en cuenta el valor de la transacción, lo que ocurra primero.",
        "emisor": "El agente de retención designado.",
        "acompanantes": "Comprobante de venta que motiva la retención (puede ir en anexo integrante).",
        "campos_preimpresos": PREIMPRESOS_ART18 + [
            "Denominación «Comprobante de retención»",
            "Ejemplares: «ORIGINAL: SUJETO PASIVO RETENIDO» y «COPIA-AGENTE DE RETENCIÓN»",
        ],
        "campos_llenado": [
            "Nombres o razón social del retenido",
            "RUC / cédula / pasaporte del retenido",
            "Impuesto por el que se retiene: Renta, IVA o ISD",
            "Denominación y número del comprobante de venta que motiva la retención",
            "Valor de la transacción o base de la retención",
            "Porcentaje aplicado",
            "Valor retenido",
            "Ejercicio fiscal",
            "Fecha de emisión y firma del agente de retención",
        ],
        "requisitos": [
            "Debe estar disponible para el proveedor dentro de los 5 días hábiles siguientes al de "
            "presentación del comprobante de venta (2 días hábiles en el caso del ISD).",
            "Se emite aun cuando un convenio internacional exima de la retención.",
            "Cada comprobante se totaliza y cierra individualmente.",
        ],
        "pagina_fuente": "Art. 8 p. 6; Art. 39-40 p. 24-27",
    },
    {
        "codigo": "LIQUIDACION_VEHICULOS_USADOS",
        "nombre": "Liquidación de compra de vehículos usados",
        "categoria": "COMPROBANTE_VENTA",
        "cuando_se_emite": "Venta de vehículos usados por quien no puede emitir comprobante (casos del Art. 13).",
        "emisor": "El adquirente (comisionista o particular).",
        "acompanantes": "Acta de entrega-recepción del vehículo.",
        "campos_preimpresos": PREIMPRESOS_ART18,
        "campos_llenado": [
            "Datos del vendedor (nombres, identificación, dirección, teléfono, profesión, correo)",
            "Descripción del vehículo: placa, marca, modelo, tipo, año, país de origen, color, cilindraje, "
            "combustible, número de motor y de chasis, estado",
            "Precio de venta y forma de pago",
            "Lugar y fecha de celebración",
            "Firmas del adquirente y del vendedor",
        ],
        "requisitos": ["Original para el adquirente y copia para el vendedor."],
        "pagina_fuente": "Formato oficial p. 1; Art. 13 p. 8; Art. 22 p. 15",
    },
    {
        "codigo": "ACTA_VEHICULOS_USADOS",
        "nombre": "Acta de entrega-recepción de vehículos usados",
        "categoria": "DOCUMENTO_SOPORTE",
        "cuando_se_emite": "Cuando el comisionista recepciona un vehículo para venderlo en comisión.",
        "emisor": "El comisionista.",
        "acompanantes": "Liquidación de compra de vehículos usados.",
        "campos_preimpresos": ["Numeración con autorización del SRI", "Denominación del documento"],
        "campos_llenado": [
            "Datos del vehículo y del vendedor",
            "Comisión pactada (10 % del precio de venta del vehículo en el formato oficial)",
            "Observaciones",
        ],
        "requisitos": ["No es comprobante de venta: es documento de soporte del encargo."],
        "pagina_fuente": "Formato oficial p. 1",
    },
    {
        "codigo": "FACTURA_SERVICIOS_TURISTICOS",
        "nombre": "Factura de servicios turísticos",
        "categoria": "COMPROBANTE_VENTA",
        "cuando_se_emite": "Prestación de servicios turísticos por establecimientos registrados.",
        "emisor": "Establecimiento turístico registrado.",
        "acompanantes": "—",
        "campos_preimpresos": PREIMPRESOS_ART18,
        "campos_llenado": LLENADO_FACTURA_ART19 + ["Tarifa de servicios turísticos, cuando aplique"],
        "requisitos": ["La tarifa de servicios turísticos es dato configurable del período."],
        "pagina_fuente": "Formato oficial p. 1",
    },
    {
        "codigo": "FACTURA_TRANSPORTE",
        "nombre": "Factura de transporte (excepto taxi y carga pesada)",
        "categoria": "COMPROBANTE_VENTA",
        "cuando_se_emite": "Servicio de transporte de pasajeros o carga, incluida la emisión a socios o accionistas.",
        "emisor": "Operadora de transporte autorizada.",
        "acompanantes": "—",
        "campos_preimpresos": PREIMPRESOS_ART18 + ["Puntos de emisión asignados a socios o accionistas, si aplica"],
        "campos_llenado": LLENADO_FACTURA_ART19 + [
            "Recorrido y número de comprobante del servicio",
            "Datos del socio o accionista cuando la emisión es a su nombre",
        ],
        "requisitos": ["Cada punto de emisión se controla por separado."],
        "pagina_fuente": "Formatos oficiales p. 1",
    },
    {
        "codigo": "ACTA_PET",
        "nombre": "Acta de entrega-recepción de botellas plásticas no retornables (PET)",
        "categoria": "DOCUMENTO_SOPORTE",
        "cuando_se_emite": "Entrega-recepción de envases PET en el marco del sistema de depósito, "
                           "reembolso y retorno.",
        "emisor": "Establecimiento que recepciona los envases.",
        "acompanantes": "Factura de la venta original.",
        "campos_preimpresos": ["Pendiente de revisión manual: el formato de la carpeta es una imagen "
                               "escaneada sin capa de texto"],
        "campos_llenado": ["Pendiente de revisión manual"],
        "requisitos": ["Tipo configurable: no se infirieron sus campos para no inventar información."],
        "pagina_fuente": "Formato pendiente de revisión manual",
    },
]


REGLAS_DOCUMENTO = [
    {"codigo": "R-57.1", "titulo": "Emisión previa autorización", "aplica_a": "TODO",
     "regla": "Ningún comprobante puede emitirse sin número de autorización de impresión vigente del SRI.",
     "validacion": "Exigir `numero_autorizacion` no vacío y su fecha; rechazar la emisión si falta.",
     "mensaje": "Este comprobante necesita el número de autorización de impresión del SRI. Sin él no "
                "puede emitirse.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 18 p. 11-13"},

    {"codigo": "R-57.2", "titulo": "Numeración de 15 dígitos", "aplica_a": "TODO",
     "regla": "La numeración se compone de 3 dígitos de establecimiento + 3 de punto de emisión + 9 "
              "de secuencial.",
     "validacion": "Validar el patrón ^[0-9]{3}-?[0-9]{3}-?[0-9]{9}$ y el secuencial correlativo por "
                   "punto de emisión.",
     "mensaje": "La numeración debe tener 15 dígitos: 3 del establecimiento, 3 del punto de emisión y 9 "
                "del secuencial.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 18 num. 5 p. 12"},

    {"codigo": "R-57.3", "titulo": "Vigencia de la autorización", "aplica_a": "TODO",
     "regla": "Un año si el contribuyente está al día; tres meses improrrogables si tiene declaraciones "
              "pendientes o deuda firme.",
     "validacion": "Comparar la fecha de emisión con la fecha de caducidad de la autorización.",
     "mensaje": "La autorización de este comprobante está caducada para la fecha de emisión.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 6 p. 4-5"},

    {"codigo": "R-57.4", "titulo": "Obligación universal de emitir", "aplica_a": "TODO",
     "regla": "Todo sujeto pasivo emite comprobante por sus transacciones, aunque el adquirente no lo "
              "solicite y aunque la operación esté gravada con tarifa 0 %.",
     "validacion": "Toda transacción registrada debe tener al menos un documento asociado.",
     "mensaje": "Toda transacción necesita su comprobante, aunque el cliente no lo pida.",
     "severidad": "ADVERTENCIA", "pagina_fuente": "Art. 8 p. 6"},

    {"codigo": "R-57.5", "titulo": "Obligados a llevar contabilidad", "aplica_a": "TODO",
     "regla": "Sociedades y personas naturales obligadas a llevar contabilidad emiten comprobantes en "
              "todas sus transacciones, sin importar el monto.",
     "validacion": "Marcar la condición del emisor y no aplicar umbrales mínimos cuando está obligado.",
     "mensaje": "Como tu empresa está obligada a llevar contabilidad, debes emitir comprobante en todas "
                "las transacciones, sin importar el monto.",
     "severidad": "INFORMATIVA", "pagina_fuente": "Art. 8 p. 6"},

    {"codigo": "R-57.6", "titulo": "Transacciones propias", "aplica_a": "TODO",
     "regla": "Solo se emiten comprobantes por transacciones propias del sujeto pasivo autorizado.",
     "validacion": "El emisor del documento debe coincidir con la empresa simulada en sesión.",
     "mensaje": "Solo puedes emitir documentos a nombre de tu propia empresa simulada.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 8 p. 6"},

    {"codigo": "R-57.7", "titulo": "Identificación del adquirente o «CONSUMIDOR FINAL»", "aplica_a": "FACTURA",
     "regla": "Se identifica al adquirente cuando requiere sustentar costos y gastos o crédito "
              "tributario; si la transacción no supera los US$ 200 puede consignarse «CONSUMIDOR FINAL».",
     "validacion": "Si el adquirente es CONSUMIDOR_FINAL, exigir que el total no supere el umbral "
                   "configurado (por defecto 200 USD).",
     "mensaje": "Una factura a «CONSUMIDOR FINAL» no puede superar el tope configurado (200 USD). "
                "Identifica al cliente o divide la operación.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 19 num. 1 p. 13-14"},

    {"codigo": "R-57.8", "titulo": "Desglose del IVA según el adquirente", "aplica_a": "FACTURA",
     "regla": "El impuesto se desglosa cuando el adquirente sustenta crédito tributario o gastos "
              "personales; a consumidores finales no se desglosa.",
     "validacion": "Exigir iva_tarifa e iva_valor cuando el adquirente está identificado; ocultarlos "
                   "cuando es consumidor final.",
     "mensaje": "Al cliente identificado se le desglosa el IVA; al consumidor final, no.",
     "severidad": "ADVERTENCIA", "pagina_fuente": "Art. 11 p. 8"},

    {"codigo": "R-57.9", "titulo": "Crédito tributario de IVA", "aplica_a": "FACTURA",
     "regla": "Para dar crédito tributario, el comprobante debe identificar al comprador y hacer constar "
              "el IVA por separado.",
     "validacion": "Verificar identificación + desglose antes de aceptar el documento como crédito.",
     "mensaje": "Sin la identificación del cliente y el IVA por separado, este comprobante no da crédito "
                "tributario.",
     "severidad": "ADVERTENCIA", "pagina_fuente": "Art. 9 p. 7"},

    {"codigo": "R-57.10", "titulo": "Sustento de costos y gastos", "aplica_a": "TODO",
     "regla": "Los costos y gastos se sustentan con un comprobante que identifique con precisión al "
              "adquirente o beneficiario.",
     "validacion": "No permitir contabilizar gastos cuyo documento sea un tiquete o boleto sin "
                   "identificación.",
     "mensaje": "Un tiquete o boleto no identifica a tu empresa: para sustentar el gasto necesitas una "
                "factura o nota de venta.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 10 p. 7; Art. 14 p. 9"},

    {"codigo": "R-57.11", "titulo": "Tiquetes: cambio obligatorio", "aplica_a": "TIQUETE_MAQUINA",
     "regla": "El adquirente puede exigir el cambio del tiquete por factura o nota de venta, y el emisor "
              "debe hacerlo de inmediato.",
     "validacion": "Ofrecer la acción «cambiar por factura» cuando hay tiquetes asociados a una operación "
                   "de un contribuyente identificado.",
     "mensaje": "El cliente pidió factura: debes cambiar el tiquete de inmediato.",
     "severidad": "INFORMATIVA", "pagina_fuente": "Art. 43 p. 29"},

    {"codigo": "R-57.12", "titulo": "Plazo del comprobante de retención", "aplica_a": "COMPROBANTE_RETENCION",
     "regla": "Debe estar disponible para el proveedor dentro de los 5 días hábiles siguientes al de "
              "presentación del comprobante de venta; 2 días hábiles en el caso del ISD.",
     "validacion": "Calcular los días hábiles transcurridos entre la entrega y la fecha base; alertar "
                   "cuando se acerque el plazo y bloquear cuando lo exceda.",
     "mensaje": "El comprobante de retención debe entregarse dentro de 5 días hábiles. Te quedan %d días "
                "hábiles.",
     "severidad": "ADVERTENCIA", "pagina_fuente": "Art. 8 p. 6; Art. 39 p. 24-26"},

    {"codigo": "R-57.13", "titulo": "Retención aun con convenio internacional", "aplica_a": "COMPROBANTE_RETENCION",
     "regla": "El comprobante se emite incluso cuando un convenio de doble tributación exima de la "
              "retención.",
     "validacion": "No omitir el comprobante cuando el proveedor sea extranjero.",
     "mensaje": "Aunque el convenio exima de la retención, debes emitir el comprobante de retención.",
     "severidad": "ADVERTENCIA", "pagina_fuente": "Art. 40 p. 26-27"},

    {"codigo": "R-57.14", "titulo": "Retención del 100 % del IVA en liquidaciones de compra",
     "aplica_a": "LIQUIDACION_COMPRA",
     "regla": "Para que la liquidación de compra dé crédito tributario y sustente costos y gastos debe "
              "retener el 100 % del IVA y el porcentaje correspondiente de renta.",
     "validacion": "Si tipo = LIQUIDACION_COMPRA, exigir retención de IVA del 100 %.",
     "mensaje": "En la liquidación de compra debes retener el 100 % del IVA y el porcentaje de renta.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 13 p. 9"},

    {"codigo": "R-57.15", "titulo": "Liquidación de compra a contribuyente con RUC activo",
     "aplica_a": "LIQUIDACION_COMPRA",
     "regla": "No sirve para sustentar crédito tributario ni costos y gastos la liquidación de compra "
              "emitida a un contribuyente inscrito en el RUC a la fecha de la transacción.",
     "validacion": "Si el proveedor está inscrito en el RUC, sugerir factura en lugar de liquidación de "
                   "compra.",
     "mensaje": "Tu proveedor tiene RUC activo: corresponde una factura, no una liquidación de compra.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 13 p. 9"},

    {"codigo": "R-57.16", "titulo": "Notas de crédito y débito: referencia obligatoria",
     "aplica_a": "NOTA_CREDITO,NOTA_DEBITO",
     "regla": "Deben consignar la denominación, serie y número del comprobante de venta que modifican, "
              "con su motivación.",
     "validacion": "Exigir `documento_modificado` y `motivo_modificacion`.",
     "mensaje": "Una nota de crédito o débito debe indicar qué comprobante modifica y por qué.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 15-16 p. 10; Art. 25 p. 17-18"},

    {"codigo": "R-57.17", "titulo": "Notas de crédito: recepción del adquirente", "aplica_a": "NOTA_CREDITO",
     "regla": "El adquirente anota en el original y la copia su nombre, identificación y la fecha de "
              "recepción.",
     "validacion": "Registrar la fecha de recepción del adquirente.",
     "mensaje": "Anota en la nota de crédito el nombre, la identificación y la fecha en que la recibió "
                "el cliente.",
     "severidad": "INFORMATIVA", "pagina_fuente": "Art. 15 p. 10"},

    {"codigo": "R-57.18", "titulo": "Facturas comerciales negociables", "aplica_a": "NOTA_CREDITO,NOTA_DEBITO",
     "regla": "No pueden modificarse las facturas comerciales negociables ya negociadas.",
     "validacion": "Marcar la factura como negociada y bloquear su modificación.",
     "mensaje": "Esta factura ya fue negociada: no puede modificarse con una nota.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 15-16 p. 10"},

    {"codigo": "R-57.19", "titulo": "Guía de remisión previa al traslado", "aplica_a": "GUIA_REMISION",
     "regla": "Se emite antes del traslado, sin tachones ni enmendaduras, y la porta cada unidad de "
              "transporte.",
     "validacion": "La fecha de la guía debe ser anterior o igual al inicio del traslado; exigir motivo, "
                   "destino, conductor y placa.",
     "mensaje": "La guía de remisión debe emitirse antes de iniciar el traslado de la mercadería.",
     "severidad": "BLOQUEO", "pagina_fuente": "Art. 30 p. 21-23; Art. 36 p. 23-24"},

    {"codigo": "R-57.20", "titulo": "Archivo y conservación", "aplica_a": "TODO",
     "regla": "Los comprobantes se conservan en archivo ordenado secuencialmente durante el plazo "
              "previsto por la normativa (7 años).",
     "validacion": "Guardar siempre tipo, número completo, fecha y estado; no permitir borrar "
                   "documentos emitidos.",
     "mensaje": "Los comprobantes no se eliminan: se anulan o se dan de baja, y se conservan en archivo "
                "ordenado.",
     "severidad": "INFORMATIVA", "pagina_fuente": "Art. 36 p. 23-24; normativa de archivo"},

    {"codigo": "R-57.21", "titulo": "Anulación y baja de documentos", "aplica_a": "TODO",
     "regla": "La baja de documentos se comunica al SRI dentro de los 15 días hábiles siguientes, con "
              "expresión de causa.",
     "validacion": "Al anular o dar de baja, exigir motivo y registrar la fecha; nunca borrar el registro.",
     "mensaje": "Para anular o dar de baja un comprobante debes indicar el motivo; el documento queda "
                "registrado.",
     "severidad": "ADVERTENCIA", "pagina_fuente": "Art. 49 p. 30-34"},

    {"codigo": "R-57.22", "titulo": "Suspensión de la autorización", "aplica_a": "TODO",
     "regla": "Los comprobantes emitidos mientras dura la suspensión no sustentan crédito tributario ni "
              "costos y gastos.",
     "validacion": "Marcar la autorización como suspendida y advertir al emitir.",
     "mensaje": "Atención: la autorización está suspendida; este comprobante no tendrá validez tributaria.",
     "severidad": "ADVERTENCIA", "pagina_fuente": "Art. 7 p. 5"},

    {"codigo": "R-57.23", "titulo": "Leyenda educativa obligatoria", "aplica_a": "TODO",
     "regla": "Los documentos del simulador son material de práctica, sin validez comercial.",
     "validacion": "Imprimir en todo comprobante la leyenda «DOCUMENTO PARA USO EDUCATIVO (SIN VALIDEZ "
                   "COMERCIAL)».",
     "mensaje": "Documento para uso educativo (sin validez comercial).",
     "severidad": "INFORMATIVA", "pagina_fuente": "Disposición General Novena p. 36"},
]
