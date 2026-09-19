# -*- coding: utf-8 -*-
"""Banco de casos prácticos de los libros — soporte de DATOS del Prompt Maestro v2.

Este módulo **no contiene lógica de negocio**: contiene únicamente DATOS estructurados que el
resto del sistema (esquema, servicio, rutas, plantillas y pruebas) consume.

Fuente normativa interna:
    * §61 — BANCO DE CASOS PRÁCTICOS CON CIFRAS (19 casos con fuente, enunciado, datos,
      asientos esperados, solución y estado de validación).
    * §62 — ADVERTENCIAS DE FIDELIDAD Y CALIDAD (reglas de trazabilidad de las fuentes).
    * §59 — PLAN DE CUENTAS BASE y erratas de la fuente que NO deben replicarse.

Estados de validación de un caso (§61):
    VERIFICADO             solución presente en la fuente o comprobada aritméticamente.
    VERIFICADO_CON_RESERVA solución presente, con parte del detalle reconstruido (pendiente
                           de cotejo con el facsímil).
    SIN_SOLUCION           la fuente no trae solución: se carga como práctica sin solución
                           visible (§62.5).
    CON_ERRATA             la fuente trae errores: solo se carga la versión corregida (§62.1).
    PARCIAL_CON_ERRATA     parte del ejercicio es utilizable y parte está excluida.

Uso:
    from database.banco_casos_libros import CASOS, FUENTES, REGLAS_TRAZABILIDAD
"""

VERSION_PROMPT_MAESTRO = ("Prompt Maestro v2 — secciones §61 (banco de casos prácticos con "
                          "cifras) y §62 (advertencias de fidelidad y calidad)")

# --------------------------------------------------------------------------------------
# Fuentes: correlación de páginas (§62.7), contexto normativo (§62.3 y §62.6)
# --------------------------------------------------------------------------------------
# §62.7 — doble numeración obligatoria: U2 impresa = PDF − 19 · U4 un pliego por hoja ·
#         U3 impresa = PDF − 32 · SENA impresa = PDF − 2.
FUENTES = {
    "U2": {
        "codigo": "U2",
        "nombre": "Libro Unidad 2 — Personificación, clasificación, codificación y dinámica de cuentas",
        "edicion": "Libro Unidad 2 (2025); ejercicio BrilloCar (2023)",
        "anio": "2023–2025",
        "tipo": "Libro de texto de la asignatura (PDF de la docente)",
        "pais_contexto": "Ecuador — material didáctico de la asignatura (UTM)",
        "correlacion_paginas": "impresa = PDF − 19",
        "delta_pdf": 19,
        "paginas_sin_texto": (
            "~34 páginas casi vacías en la extracción, sin capa de texto (figuras y tablas resueltas clave): "
            "balance de comprobación con cifras de BrilloCar (PDF 188–190 / imp. 169–172), estado de situación "
            "financiera y tablas de aumentos y disminuciones por cuenta (Tablas 20–54, PDF 115–134)"),
        "erratas_conocidas": [
            "imp. 77: \"Todas las cuentas del activo tienen saldos acreedor\" — debe decir pasivo y patrimonio",
            "imp. 89 (Tabla 14): cuarto nivel rotulado «0000» y quinto «00000» — se usan 5 y 7 dígitos",
            "imp. 119: `12104` asignado a dos cuentas distintas",
            "imp. 117: `21101` y `21102` repetidos dentro del grupo `22`",
            "imp. 92 vs. 93 (Tablas 17 y 18): grupos 31–34 y 41–42 contradictorios — prevalece la Tabla 18/55",
            "imp. 116–119: el plan no incluye código de «Costo de ventas» (se crea, §59.7)",
            "imp. 120–121: quinta fila del Ejercicio N°1 con patrimonio negativo (−150.000,00)",
        ],
        "notas": [
            "El catálogo semilla (§59) se toma de U2 Tabla 55 (imp. 116–119) más los códigos del caso BrilloCar (imp. 140–142).",
            "Esta fuente NO explica el IVA ni las retenciones como normativa (§62.3): el IVA aparece como cuenta del plan (`11601`, `21301`) y como línea de cálculo al 15 % en los ejemplos, y las retenciones solo como nombres de cuenta (`11602`, `11603`, `21304`, `21305`).",
        ],
    },
    "U3": {
        "codigo": "U3",
        "nombre": "Libro Unidad 3 — Jornalización y mayorización (Horngren, traducción de la edición estadounidense 2009)",
        "edicion": "1.ª edición en español (2010–2011)",
        "anio": "2009–2011",
        "tipo": "Libro de texto de la asignatura (PDF de la docente)",
        "pais_contexto": "Estados Unidos, 2009–2011 — HISTÓRICO Y EXTRANJERO",
        "correlacion_paginas": "impresa = PDF − 32",
        "delta_pdf": 32,
        "paginas_sin_texto": "Fórmulas y ejercicios ilustrados reproducidos como imagen en algunas páginas.",
        "erratas_conocidas": [],
        "notas": [
            "§62.3: cero apariciones de «impuesto al valor agregado» o «IVA». Su única línea fiscal es el «Impuesto (3 %)» de una factura de compra de 2011, dato histórico y estadounidense.",
            "§62.3: sus «retenciones» son de nómina estadounidense (formulario W-4), NO retención en la fuente.",
            "§62.6: las cifras usan formato angloamericano; el simulador normaliza la visualización a `es-EC` sin alterar valores.",
            "De esta fuente solo se puede tomar como modelo: la factura con línea de impuesto (p. 275) y el memo de crédito para devoluciones (p. 277).",
        ],
    },
    "U4": {
        "codigo": "U4",
        "nombre": "Libro Unidad 4 — Balance de comprobación de sumas y saldos, ventas, costos y estados financieros",
        "edicion": "Libro Unidad 4 (2024)",
        "anio": "2024",
        "tipo": "Libro de texto de la asignatura (PDF de la docente)",
        "pais_contexto": "Ecuador — material didáctico de la asignatura (UTM)",
        "correlacion_paginas": "un pliego por hoja (se cita por pliego del PDF)",
        "delta_pdf": 0,
        "paginas_sin_texto": (
            "La solución del Caso Práctico 1 (Servicios Unidos, imp. 124–127) está en páginas de imagen."),
        "erratas_conocidas": [
            "imp. 92–93 (Guápulo): asiento del 25-jun descuadrado (`Caja 4.000,00` frente a un Haber de 4.600,00)",
            "imp. 96–97 (Servindustria): reconocimiento mensual de 500,00 en lugar de 600,00 (7.200,00 ÷ 12)",
        ],
        "notas": [
            "§62.3: no explica el IVA como normativa; el 15 % aparece como línea de cálculo en los ejemplos.",
            "Es la fuente de los códigos citados en los ejemplos de imp. 95–120 usados para completar el plan de cuentas (§59.1).",
        ],
    },
    "SENA": {
        "codigo": "SENA",
        "nombre": "SENA — Contabilidad (unidad didáctica, Comprobante de Diario, Libro Mayor y Balances)",
        "edicion": "SENA, enero de 1977",
        "anio": "1977",
        "tipo": "Material didáctico (PDF de la docente)",
        "pais_contexto": "Colombia, 1977 — HISTÓRICO Y EXTRANJERO",
        "correlacion_paginas": "impresa = PDF − 2",
        "delta_pdf": 2,
        "paginas_sin_texto": ("El OCR de 1977 mezcla las columnas del rayado con el texto: los detalles de los "
                              "comprobantes 001 y 002 de Muebles el Cóndor y las cifras de las páginas 52–57 "
                              "son reconstrucción y requieren revisión del facsímil."),
        "erratas_conocidas": [
            "El OCR de 1977 mezcla columnas; los detalles de los comprobantes 001 y 002 de Muebles el Cóndor y las cifras de la p. 52–57 son reconstrucción y requieren revisión del facsímil.",
        ],
        "notas": [
            "§62.3: es anterior a la creación del IVA en Colombia — CERO apariciones de IVA. Sus operaciones son al contado o a crédito con devoluciones en ventas y en compras.",
            "§62.6: los requisitos legales del Libro Mayor («libro principal exigido por la Ley», p. 56) son de Colombia 1977 y NO pueden citarse como normativa vigente; el «Diario Columnario», el «Comprobante de Diario» y el «Libro Mayor y Balances» se usan únicamente como MODELO VISUAL.",
        ],
    },
}

# Advertencias normativas que toda ficha de caso debe mostrar (§62.3).
ADVERTENCIA_IVA_RETENCIONES = (
    "Las fuentes usadas (U2, U3, U4 y SENA) NO explican el IVA ni las retenciones como normativa: "
    "el IVA aparece como cuenta del plan de U2 (`11601` IVA pagado, `21301` IVA cobrado) y como línea de "
    "cálculo al 15 % en los ejemplos de U4, y las retenciones solo como nombres de cuenta "
    "(`11602`, `11603`, `21304`, `21305`), sin ningún asiento resuelto que las calcule. "
    "El módulo de IVA y retenciones debe documentarse con el material de la asignatura (UTM/CAAFL) y la "
    "normativa del SRI vigente, con parámetros configurables."
)

ADVERTENCIA_MARCO_EXTRANJERO = (
    "Este caso proviene de un marco normativo extranjero o histórico y se usa únicamente como MODELO "
    "VISUAL: la terminología del simulador es la del syllabus ecuatoriano (jornalización, mayorización, "
    "Libro Diario, Libro Mayor, balance de comprobación)."
)

# §62.2 — Tarifas de las fuentes: datos históricos o demostrativos, NUNCA tasas vigentes.
ETIQUETA_TASAS = "Configuración académica / demostrativa"
TASAS_DEMOSTRATIVAS = {
    "iva": {
        "clave_parametro": "academico.iva_tarifa",
        "nombre": "Tarifa de IVA usada en los ejemplos de U4 (2024) y en el plan de U2",
        "valor_fuente": 0.15,
        "unidad": "porcentaje",
        "fuente": "U4 imp. 95–120 (2024) y U2 imp. 116–119",
        "etiqueta": ETIQUETA_TASAS,
        "editable_desde_panel": True,
        "fijar_en_codigo": False,
    },
    "iess_personal": {
        "clave_parametro": "academico.iess_aporte_personal",
        "nombre": "Aporte personal al IESS del asiento de BrilloCar",
        "valor_fuente": 0.0945,
        "unidad": "porcentaje",
        "fuente": "U2, plan de cuentas (`21501`) y asiento de BrilloCar (imp. 140–142)",
        "etiqueta": ETIQUETA_TASAS,
        "editable_desde_panel": True,
        "fijar_en_codigo": False,
    },
    "iess_patronal": {
        "clave_parametro": "academico.iess_aporte_patronal",
        "nombre": "Aporte patronal al IESS del plan de cuentas",
        "valor_fuente": 0.1215,
        "unidad": "porcentaje",
        "fuente": "U2, plan de cuentas (`21502`)",
        "etiqueta": ETIQUETA_TASAS,
        "editable_desde_panel": True,
        "fijar_en_codigo": False,
    },
    "participacion_trabajadores": {
        "clave_parametro": "academico.participacion_trabajadores",
        "nombre": "Participación a los trabajadores aplicada en el ejemplo de BrilloCar",
        "valor_fuente": 0.15,
        "unidad": "porcentaje",
        "fuente": "U2 imp. 166–168",
        "etiqueta": ETIQUETA_TASAS,
        "editable_desde_panel": True,
        "fijar_en_codigo": False,
    },
    "impuesto_renta_implicito": {
        "clave_parametro": "academico.impuesto_renta_implicito",
        "nombre": ("Impuesto a la renta implícito en el ejemplo de BrilloCar "
                   "(637,50 sobre 2.550,00) — la fuente NO lo declara como tarifa"),
        "valor_fuente": 0.25,
        "unidad": "porcentaje",
        "fuente": "U2 imp. 166–168 (cálculo derivado, no impreso como tarifa)",
        "etiqueta": ETIQUETA_TASAS,
        "editable_desde_panel": True,
        "fijar_en_codigo": False,
    },
    "depreciacion_edificios": {
        "clave_parametro": "academico.depreciacion_edificios",
        "nombre": "Depreciación de edificios — 20 años / 5 % (método legal)",
        "valor_fuente": 0.05,
        "unidad": "porcentaje anual",
        "fuente": "U2 Tabla 13, imp. 88",
        "etiqueta": ETIQUETA_TASAS,
        "editable_desde_panel": True,
        "fijar_en_codigo": False,
    },
    "depreciacion_maquinaria": {
        "clave_parametro": "academico.depreciacion_maquinaria",
        "nombre": "Depreciación de maquinaria y equipo — 10 años / 10 %",
        "valor_fuente": 0.10,
        "unidad": "porcentaje anual",
        "fuente": "U2 Tabla 13, imp. 88",
        "etiqueta": ETIQUETA_TASAS,
        "editable_desde_panel": True,
        "fijar_en_codigo": False,
    },
    "depreciacion_muebles": {
        "clave_parametro": "academico.depreciacion_muebles",
        "nombre": "Depreciación de muebles y enseres — 10 años / 10 %",
        "valor_fuente": 0.10,
        "unidad": "porcentaje anual",
        "fuente": "U2 Tabla 13, imp. 88",
        "etiqueta": ETIQUETA_TASAS,
        "editable_desde_panel": True,
        "fijar_en_codigo": False,
    },
    "depreciacion_computacion": {
        "clave_parametro": "academico.depreciacion_computacion",
        "nombre": "Depreciación de equipo de computación — 3 años / 33,33 %",
        "valor_fuente": 0.3333,
        "unidad": "porcentaje anual",
        "fuente": "U2 Tabla 13, imp. 88",
        "etiqueta": ETIQUETA_TASAS,
        "editable_desde_panel": True,
        "fijar_en_codigo": False,
    },
}

# §62.8 — la sección 14 del prompt maestro autoriza tres modos de catálogo de cuentas.
MODOS_CATALOGO = [
    {
        "codigo": "BASE",
        "nombre": "Catálogo base",
        "descripcion": "Se siembra el plan de cuentas completo (clase, grupo, subgrupo, cuenta y subcuenta).",
        "siembra_cuentas": True,
        "oculta_clasificacion": False,
    },
    {
        "codigo": "INCOMPLETO",
        "nombre": "Catálogo incompleto",
        "descripcion": ("No se siembran las cuentas que la actividad pide construir: el estudiante las crea."),
        "siembra_cuentas": False,
        "oculta_clasificacion": False,
    },
    {
        "codigo": "PROPIO",
        "nombre": "Catálogo propio / modo práctica",
        "descripcion": ("En modo evaluación no se muestra ninguna clasificación ni naturaleza "
                        "(modalidad «Plan de cuentas en modo práctica», §2)."),
        "siembra_cuentas": False,
        "oculta_clasificacion": True,
    },
]
ADVERTENCIA_CATALOGO_SEMILLA = (
    "El catálogo semilla (§59) es un PUNTO DE PARTIDA, no el plan definitivo: la sección 14 del prompt "
    "maestro autoriza los modos catálogo base, catálogo incompleto y catálogo propio. En modo «catálogo "
    "incompleto» no deben sembrarse las cuentas que la actividad pide construir."
)

# --------------------------------------------------------------------------------------
# §59.5–59.7 — Catálogo semilla: (código: (nombre, naturaleza))
# --------------------------------------------------------------------------------------
PLAN_CUENTAS_BASE = {
    # Nivel 1 — clase
    "1": ("ACTIVO", "DEUDORA"),
    "2": ("PASIVO", "ACREEDORA"),
    "3": ("PATRIMONIO", "ACREEDORA"),
    "4": ("INGRESOS", "ACREEDORA"),
    "5": ("GASTOS", "DEUDORA"),
    "6": ("CUENTAS DE ORDEN", "NO_AFECTA_EEFF"),
    # Nivel 2 — grupo
    "11": ("Activo corriente", "DEUDORA"),
    "12": ("Activo no corriente", "DEUDORA"),
    "21": ("Pasivo corriente", "ACREEDORA"),
    "22": ("Pasivo no corriente", "ACREEDORA"),
    "31": ("Capital", "ACREEDORA"),
    "32": ("Reservas", "ACREEDORA"),
    "33": ("Resultados acumulados", "ACREEDORA"),
    "34": ("Resultados del ejercicio", "ACREEDORA"),
    "41": ("Ingresos de actividades ordinarias", "ACREEDORA"),
    "42": ("Otros ingresos", "ACREEDORA"),
    "51": ("Gastos operacionales", "DEUDORA"),
    "52": ("Gastos no operacionales", "DEUDORA"),
    "61": ("Deudoras (orden)", "NO_AFECTA_EEFF"),
    "62": ("Acreedoras (orden)", "NO_AFECTA_EEFF"),
    # Nivel 3 — subgrupo
    "111": ("Efectivo y equivalentes del efectivo", "DEUDORA"),
    "113": ("Activos financieros", "DEUDORA"),
    "114": ("Inventarios", "DEUDORA"),
    "115": ("Servicios y otros pagos anticipados", "DEUDORA"),
    "116": ("Activos por impuestos corrientes", "DEUDORA"),
    "121": ("Propiedad, planta y equipo", "DEUDORA"),
    "122": ("Activo intangible", "DEUDORA"),
    "211": ("Cuentas y documentos por pagar", "ACREEDORA"),
    "212": ("Obligaciones con instituciones financieras", "ACREEDORA"),
    "213": ("Con la administración tributaria", "ACREEDORA"),
    "214": ("Obligaciones con los empleados", "ACREEDORA"),
    "215": ("Obligaciones con el IESS", "ACREEDORA"),
    "216": ("Anticipos", "ACREEDORA"),
    "217": ("Otros pasivos corrientes", "ACREEDORA"),
    "221": ("Cuentas y documentos por pagar de largo plazo", "ACREEDORA"),
    "311": ("Capital individual / social", "ACREEDORA"),
    "312": ("Reservas", "ACREEDORA"),
    "313": ("Resultados acumulados", "ACREEDORA"),
    "314": ("Resultados del ejercicio", "ACREEDORA"),
    "411": ("Venta de bienes", "ACREEDORA"),
    "412": ("Prestación de servicios", "ACREEDORA"),
    "422": ("Intereses financieros", "ACREEDORA"),
    "511": ("Gastos administrativos", "DEUDORA"),
    "512": ("Gastos de ventas", "DEUDORA"),
    "513": ("Costo de ventas y costo de servicios [añadido del simulador]", "DEUDORA"),
    "611": ("Mercaderías entregadas en consignación", "NO_AFECTA_EEFF"),
    "621": ("Mercaderías recibidas en consignación", "NO_AFECTA_EEFF"),
    # Nivel 4 — cuenta de mayor
    "11101": ("Caja", "DEUDORA"),
    "11102": ("Caja chica", "DEUDORA"),
    "11103": ("Bancos", "DEUDORA"),
    "11301": ("Cuentas y documentos por cobrar no relacionados", "DEUDORA"),
    "11302": ("Cuentas y documentos por cobrar relacionados", "DEUDORA"),
    "11303": ("(-) Provisión por cuentas incobrables y deterioro", "ACREEDORA"),
    "11401": ("Inv. de suministros o materiales a ser consumidos", "DEUDORA"),
    "11402": ("Inv. de mercadería en almacén comprada a terceros", "DEUDORA"),
    "11405": ("Inventarios de útiles de oficina", "DEUDORA"),
    "11406": ("(-) Provisión por valor neto de realización", "ACREEDORA"),
    "11501": ("Seguros pagados por anticipado", "DEUDORA"),
    "11502": ("Arriendos pagados por anticipado", "DEUDORA"),
    "11503": ("Anticipos a proveedores", "DEUDORA"),
    "11601": ("IVA pagado (IVA compras)", "DEUDORA"),
    "11602": ("Retenciones en la fuente anticipada IVA", "DEUDORA"),
    "11603": ("Retenciones en la fuente anticipada I.R.", "DEUDORA"),
    "11604": ("Crédito tributario a favor de la empresa (IVA)", "DEUDORA"),
    "12101": ("Terrenos", "DEUDORA"),
    "12102": ("Edificios", "DEUDORA"),
    "12103": ("(-) Depreciación acumulada edificios", "ACREEDORA"),
    "12104": ("Muebles y enseres", "DEUDORA"),
    "12105": ("Maquinaria y equipo", "DEUDORA"),
    "12107": ("Equipo de computación", "DEUDORA"),
    "12109": ("Vehículos, equipos de transporte y equipo caminero", "DEUDORA"),
    "21101": ("Proveedores", "ACREEDORA"),
    "21102": ("Honorarios por pagar", "ACREEDORA"),
    "21103": ("Servicios básicos por pagar", "ACREEDORA"),
    "21104": ("Documentos por pagar", "ACREEDORA"),
    "21201": ("Préstamos bancarios", "ACREEDORA"),
    "21301": ("IVA cobrado (IVA ventas)", "ACREEDORA"),
    "21302": ("Impuesto a la renta por pagar", "ACREEDORA"),
    "21303": ("Impuestos por pagar", "ACREEDORA"),
    "21304": ("Retenciones en la fuente cobrada IVA", "ACREEDORA"),
    "21305": ("Retenciones en la fuente cobrada I.R.", "ACREEDORA"),
    "21401": ("Sueldos por pagar", "ACREEDORA"),
    "21402": ("Beneficios sociales por pagar", "ACREEDORA"),
    "21403": ("Participación trabajadores por pagar", "ACREEDORA"),
    "21501": ("Aporte personal 9,45 %", "ACREEDORA"),
    "21502": ("Aporte patronal 12,15 %", "ACREEDORA"),
    "21503": ("Fondos de reserva", "ACREEDORA"),
    "21601": ("Anticipos de clientes", "ACREEDORA"),
    "22101": ("Préstamos bancarios de largo plazo", "ACREEDORA"),
    "31101": ("Capital suscrito y pagado", "ACREEDORA"),
    "31102": ("Capital suscrito no pagado", "ACREEDORA"),
    "31201": ("Reserva legal", "ACREEDORA"),
    "31301": ("Ganancias acumuladas", "ACREEDORA"),
    "31302": ("(-) Pérdidas acumuladas", "DEUDORA"),
    "31401": ("Utilidad neta del periodo", "ACREEDORA"),
    "31402": ("(-) Pérdida neta del periodo", "DEUDORA"),
    "41101": ("Venta de mercaderías", "ACREEDORA"),
    "41201": ("Ingresos por servicios", "ACREEDORA"),
    "42201": ("Intereses ganados", "ACREEDORA"),
    "61302": ("Pérdidas y ganancias (cuenta transitoria de cierre)", "TRANSITORIA"),
}

# §59.6 — detalle de gastos administrativos y de ventas (naturaleza deudora).
PLAN_CUENTAS_BASE.update({
    "51101": ("Sueldos y salarios", "DEUDORA"),
    "51102": ("Beneficios sociales", "DEUDORA"),
    "51103": ("Aportes a la seguridad social", "DEUDORA"),
    "51104": ("Horas extraordinarias", "DEUDORA"),
    "51105": ("Seguros", "DEUDORA"),
    "51106": ("Gastos de representación", "DEUDORA"),
    "51107": ("Servicios básicos", "DEUDORA"),
    "51108": ("Suministros de oficina", "DEUDORA"),
    "51109": ("Seguridad y vigilancia", "DEUDORA"),
    "51110": ("Depreciaciones", "DEUDORA"),
    "51111": ("Amortizaciones", "DEUDORA"),
    "51112": ("Aseo y limpieza", "DEUDORA"),
    "51113": ("Arriendo de local", "DEUDORA"),
    "51114": ("Gastos de cuentas incobrables", "DEUDORA"),
    "51201": ("Sueldos y salarios", "DEUDORA"),
    "51202": ("Beneficios sociales", "DEUDORA"),
    "51203": ("Aportes a la seguridad social", "DEUDORA"),
    "51204": ("Comisiones a vendedores", "DEUDORA"),
    "51205": ("Viáticos a empleados", "DEUDORA"),
    "51206": ("Depreciaciones", "DEUDORA"),
    "51207": ("Transporte y movilización", "DEUDORA"),
    "51208": ("Combustibles y lubricantes", "DEUDORA"),
    "51209": ("Mantenimiento", "DEUDORA"),
    # §59.7 — la fuente omite el código de "Costo de ventas": se crea bajo la clase 5.
    "51301": ("Costo de ventas de mercaderías [añadido del simulador]", "DEUDORA"),
    "51302": ("Costo de servicios prestados [añadido del simulador]", "DEUDORA"),
})

# §59.10 — erratas del plan de cuentas de la fuente que NO deben replicarse.
ERRATAS_PLAN_CUENTAS = [
    {"numero": 1, "errata": "«Todas las cuentas del activo normalmente tienen saldos crédito o acreedor»",
     "fuente": "U2 imp. 77", "regla": "Pasivo y patrimonio son acreedoras."},
    {"numero": 2, "errata": "Cuarto nivel rotulado «0000» y quinto «00000»",
     "fuente": "U2 imp. 89 (Tabla 14)", "regla": "Usar 5 dígitos (cuenta) y 7 dígitos (subcuenta)."},
    {"numero": 3, "errata": "`12104` asignado a dos cuentas (Muebles y enseres y Depreciación acumulada edificios)",
     "fuente": "U2 imp. 119", "regla": "`12104` = Muebles y enseres; `12103` = (-) Depreciación acumulada edificios."},
    {"numero": 4, "errata": "`21101` y `21102` repetidos dentro del grupo `22` Pasivo no corriente",
     "fuente": "U2 imp. 117", "regla": "No duplicar códigos: el simulador rechaza código repetido."},
    {"numero": 5, "errata": "Tabla 17 contradice a la Tabla 18 en los grupos 31–34 y 41–42",
     "fuente": "U2 imp. 92 vs. 93", "regla": "Usar la Tabla 18 y la Tabla 55: `41` Ingresos de actividades ordinarias."},
    {"numero": 6, "errata": "La Tabla 18 codifica `112`–`115`; la Tabla 55 desplaza a `113`–`116`",
     "fuente": "U2 imp. 93 vs. 116", "regla": "Adoptar un solo esquema: el de la Tabla 55."},
    {"numero": 7, "errata": "El plan no incluye código de «Costo de ventas»",
     "fuente": "U2 imp. 116–119", "regla": "Crearla bajo la clase 5 (`51301`/`51302`) y marcarla como añadido."},
    {"numero": 8, "errata": "Fila 5 del Ejercicio N°1 implica patrimonio negativo (−150.000,00)",
     "fuente": "U2 imp. 120–121", "regla": "No cargar esa fila."},
]

# --------------------------------------------------------------------------------------
# §62 — Reglas de trazabilidad de las fuentes (DATOS, no lógica)
# --------------------------------------------------------------------------------------
# Las reglas §62.1 a §62.7 y §62.9 son reglas de TRAZABILIDAD DE LAS FUENTES (8 reglas);
# §62.8 regula el catálogo semilla de cuentas y se conserva como regla complementaria.
REGLAS_TRAZABILIDAD = [
    {
        "numero": 1,
        "codigo": "R62.1",
        "titulo": "No replicar erratas; registrar toda corrección",
        "texto_fuente": (
            "El sistema no debe replicar ninguna de las erratas listadas en §59.10 ni de las marcadas "
            "[CON ERRATA] en §61. Toda corrección aplicada debe quedar registrada en la ficha del caso "
            "(campo de observaciones) indicando el valor original del libro, el valor corregido y la razón."),
        "trazabilidad_fuentes": True,
        "aplicacion": "casos_libros_trazabilidad + correcciones por caso + bloqueo de casos con errata sin corregir",
        "verificable": True,
    },
    {
        "numero": 2,
        "codigo": "R62.2",
        "titulo": "Las tarifas de las fuentes son datos históricos o demostrativos",
        "texto_fuente": (
            "El sistema debe rechazar como dato cualquier cifra de ejercicio tomada como tasa vigente. "
            "Las tarifas que aparecen en las fuentes son datos históricos o demostrativos (IVA 15 %, "
            "aporte personal al IESS 9,45 %, aporte patronal 12,15 %, participación a los trabajadores 15 %, "
            "impuesto a la renta aplicado sobre la utilidad imponible, y las depreciaciones de U2 Tabla 13). "
            "Ninguna debe fijarse en código; todas deben etiquetarse «Configuración académica / demostrativa» "
            "y poder editarse desde el panel docente antes de cada actividad."),
        "trazabilidad_fuentes": True,
        "aplicacion": "TASAS_DEMOSTRATIVAS + parámetros editables en la tabla `parametros`",
        "verificable": True,
    },
    {
        "numero": 3,
        "codigo": "R62.3",
        "titulo": "Las fuentes no explican el IVA ni las retenciones como normativa",
        "texto_fuente": (
            "El sistema debe advertir, en la interfaz y en toda ficha de caso, que las fuentes usadas no "
            "explican el IVA ni las retenciones como normativa. El módulo de IVA y retenciones debe "
            "documentarse con el material de la asignatura (UTM/CAAFL) y la normativa del SRI vigente."),
        "trazabilidad_fuentes": True,
        "aplicacion": "advertencia fija en las fichas (ADVERTENCIA_IVA_RETENCIONES) y en el panel docente",
        "verificable": True,
    },
    {
        "numero": 4,
        "codigo": "R62.4",
        "titulo": "Constancia de las páginas que eran imágenes sin texto",
        "texto_fuente": (
            "El sistema debe dejar constancia expresa de qué páginas eran imágenes sin texto y, por lo "
            "tanto, no pudieron validarse. Toda cifra reconstruida debe mostrarse con la etiqueta "
            "«dato reconstruido — pendiente de validación con el facsímil» y no puede usarse como respuesta "
            "oficial de una actividad evaluable."),
        "trazabilidad_fuentes": True,
        "aplicacion": "FUENTES[].paginas_sin_texto + etiquetas por caso + exclusión como respuesta oficial",
        "verificable": True,
    },
    {
        "numero": 5,
        "codigo": "R62.5",
        "titulo": "Ningún ejercicio sin solución se presenta como resuelto",
        "texto_fuente": (
            "El sistema no debe presentar como resuelto ningún ejercicio cuya solución no esté en la fuente. "
            "Deben cargarse como enunciado de práctica sin solución visible, y la corrección debe quedar a "
            "cargo del docente o de reglas mecánicas verificables (asiento cuadrado, cuentas válidas, "
            "posición Debe/Haber, balance cuadrado)."),
        "trazabilidad_fuentes": True,
        "aplicacion": "solucion_visible=False y verificación mecánica no oficial (REGLA_MECANICA)",
        "verificable": True,
    },
    {
        "numero": 6,
        "codigo": "R62.6",
        "titulo": "Advertir el marco normativo extranjero o histórico y normalizar el formato",
        "texto_fuente": (
            "El sistema debe advertir cuando una cifra provenga de un marco normativo extranjero o histórico "
            "y no del contexto ecuatoriano: requisitos legales del Libro Mayor (Colombia 1977), rayado, "
            "«Diario Columnario», «Comprobante de Diario» y «Libro Mayor y Balances» como modelo visual; "
            "y las cifras de U3 (formato angloamericano) deben normalizar su visualización a `es-EC` (1.234,56) "
            "sin alterar ningún valor."),
        "trazabilidad_fuentes": True,
        "aplicacion": "contexto_normativo por caso + filtros num_ec/money_ec + conversión de cifras de U3",
        "verificable": True,
    },
    {
        "numero": 7,
        "codigo": "R62.7",
        "titulo": "Citar siempre la doble numeración de páginas",
        "texto_fuente": (
            "El sistema debe citar siempre la doble numeración de páginas al referenciar una fuente "
            "(U2: impresa = PDF − 19; U4: un pliego por hoja; U3: impresa = PDF − 32; SENA: impresa = PDF − 2), "
            "para que la docente pueda verificar cada dato en el PDF original."),
        "trazabilidad_fuentes": True,
        "aplicacion": "FUENTES[].correlacion_paginas + cita_fuente() en toda ficha",
        "verificable": True,
    },
    {
        "numero": 8,
        "codigo": "R62.8",
        "titulo": "El catálogo semilla es un punto de partida, no el plan definitivo",
        "texto_fuente": (
            "El sistema debe tratar el catálogo semilla como punto de partida, no como plan definitivo: la "
            "sección 14 autoriza tres modos (catálogo base, catálogo incompleto, catálogo propio). Al activar "
            "el modo «catálogo incompleto» no deben sembrarse las cuentas que la actividad pide construir, y "
            "en modo evaluación no debe mostrarse ninguna clasificación ni naturaleza."),
        "trazabilidad_fuentes": False,
        "aplicacion": "MODOS_CATALOGO + advertencia en el panel docente",
        "verificable": True,
    },
    {
        "numero": 9,
        "codigo": "R62.9",
        "titulo": "Ficha obligatoria antes de publicar un caso",
        "texto_fuente": (
            "Antes de publicar cualquier caso del banco §61, el desarrollador debe dejar por escrito, en el "
            "README o en la ficha del caso: fuente completa, página, año, si la solución está o no en la "
            "fuente y si hubo corrección de erratas. Un caso sin esa ficha no debe activarse para los estudiantes."),
        "trazabilidad_fuentes": True,
        "aplicacion": "ficha_caso() con campos obligatorios + activar_caso() que rechaza fichas incompletas",
        "verificable": True,
    },
]

# Campos obligatorios de la ficha de un caso (§62.9).
CAMPOS_FICHA_OBLIGATORIOS = (
    "fuente_codigo", "fuente_nombre", "paginas_impresas", "anio",
    "solucion_en_fuente", "estado_validacion",
)

# Reglas mecánicas verificables usadas cuando la fuente no trae solución (§62.5, §34).
REGLAS_MECANICAS = (
    "ASIENTO_CUADRADO",
    "CUENTAS_VALIDAS",
    "POSICION_DEBE_HABER",
    "BALANCE_CUADRADO",
)

ETIQUETA_RECONSTRUIDO = "dato reconstruido — pendiente de validación con el facsímil"
ETIQUETA_CALCULADA = "solución calculada, no publicada por el libro"


# --------------------------------------------------------------------------------------
# Utilidades de datos (sin acceso a base de datos)
# --------------------------------------------------------------------------------------
def fuente(codigo):
    """Devuelve la ficha de una fuente (o None)."""
    return FUENTES.get((codigo or "").strip().upper())


def reglas_trazabilidad():
    """Las 8 reglas de trazabilidad de las fuentes (§62.1–§62.7 y §62.9) más §62.8."""
    return list(REGLAS_TRAZABILIDAD)


def reglas_trazabilidad_fuentes():
    """Solo las reglas que regulan la trazabilidad de las fuentes (8 de las 9 reglas de §62)."""
    return [r for r in REGLAS_TRAZABILIDAD if r["trazabilidad_fuentes"]]


def _entero(valor):
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return None


def paginas_pdf(fuente_codigo, paginas_impresas):
    """Aplica la correlación de §62.7 para expresar las páginas en numeración del PDF.

    U2: impresa = PDF − 19 · U3: impresa = PDF − 32 · SENA: impresa = PDF − 2 ·
    U4: un pliego por hoja (se cita por pliego del PDF).
    """
    ficha = fuente(fuente_codigo) or {}
    delta = int(ficha.get("delta_pdf") or 0)
    texto = str(paginas_impresas or "").strip()
    if not texto:
        return ""
    limite = "–" if "–" in texto else ("-" if "-" in texto else None)
    if limite:
        partes = [p.strip() for p in texto.split(limite, 1)]
        numeros = [_entero(p) for p in partes]
        if all(n is not None for n in numeros):
            return "%d%s%d" % (numeros[0] + delta, limite, numeros[1] + delta)
    numero = _entero(texto)
    if numero is not None:
        return str(numero + delta)
    return ""


def cita_fuente(fuente_codigo, paginas_impresas):
    """Cita con DOBLE numeración (§62.7): página impresa y su equivalente en el PDF."""
    ficha = fuente(fuente_codigo) or {}
    nombre = ficha.get("codigo") or (fuente_codigo or "")
    anio = ficha.get("anio") or ""
    correlacion = ficha.get("correlacion_paginas") or ""
    equivalente = paginas_pdf(fuente_codigo, paginas_impresas)
    if equivalente:
        etiqueta_pdf = "PDF %s" % equivalente if ficha.get("delta_pdf") else "pliego %s del PDF" % equivalente
        return "%s, imp. %s (%s) · %s" % (nombre, paginas_impresas, etiqueta_pdf, anio)
    return "%s, imp. %s (%s) · %s" % (nombre, paginas_impresas, correlacion, anio)


def formato_es_ec(valor, decimales=2):
    """Normaliza la visualización de cifras al formato `es-EC` (§62.6): 1.234,56.

    No altera el valor: solo cambia la representación (punto de miles, coma decimal).
    """
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        return str(valor)
    texto = ("{:,.%df}" % int(decimales)).format(numero)
    return texto.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")
