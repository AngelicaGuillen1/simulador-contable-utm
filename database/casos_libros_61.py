# -*- coding: utf-8 -*-
"""Los 19 casos prácticos del banco §61 — DATOS puros (Prompt Maestro v2).

Cada elemento de `CASOS` es un diccionario con la ficha completa que exige §62.9:
fuente, página (con doble numeración §62.7), año, si la solución está o no en la fuente y si
hubo corrección de erratas. El módulo no conoce la base de datos ni Flask.

Claves de cada caso
-------------------
codigo              C61.01 … C61.19 (§61.1 … §61.19)
nombre              título del caso
unidad              unidad del syllabus (1–4)
tipo                familia pedagógica del caso
dificultad          BASICO | INTERMEDIO | AVANZADO
fuente              código de fuente (U2, U3, U4, SENA)
paginas_impresas    página(s) en numeración IMPRESA del libro
anio                año del ejercicio
estado_validacion   VERIFICADO | VERIFICADO_CON_RESERVA | SIN_SOLUCION | CON_ERRATA | PARCIAL_CON_ERRATA
solucion_en_fuente  True si la fuente publica la solución
solucion_visible    True si el simulador puede mostrar esa solución al estudiante
tipo_verificacion   ASIENTO | TOTALES | ECUACION | MECANICA
enunciado           texto del enunciado
datos               líneas de datos entregados por la fuente
asientos_esperados  partidas resueltas (fecha, glosa, líneas con cuenta/código, debe y haber)
saldos_finales      saldos finales publicados (para el balance de comprobación)
totales_verificados totales comprobados aritméticamente en el propio caso
correcciones        erratas corregidas: valor del libro, valor corregido y razón (§62.1)
etiquetas           avisos de fidelidad mostrados en la ficha (§62.4)
advertencias        notas de contexto del caso
contexto_normativo  marco de la fuente (§62.6)
subcasos            ejercicios numerados dentro de un mismo §61.x (con `cargable`)
intentos_maximos    intentos permitidos en el simulador
puntaje             puntaje máximo de la actividad
"""

CASOS = [

    # -------------------------------------------------------------------------------- 61.1
    {
        "codigo": "C61.01",
        "nombre": "BrilloCar: ejercicio integral de ciclo contable",
        "unidad": 2,
        "tipo": "CICLO_CONTABLE_INTEGRAL",
        "dificultad": "AVANZADO",
        "fuente": "U2",
        "paginas_impresas": "134–172",
        "anio": 2023,
        "estado_validacion": "VERIFICADO",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 15,
        "enunciado": (
            "Empresa de servicios de lavado y encerado de vehículos. El propietario aporta dinero y bienes "
            "el 1 de abril de 2023; durante el mes se abre cuenta bancaria, se adquiere maquinaria con cheque "
            "y letra de cambio, se compran suministros, se prestan servicios al contado, se cancela parte de "
            "la deuda documentada y se pagan los sueldos con descuento del aporte personal al IESS. Se pide "
            "jornalizar, mayorizar, elaborar el balance de comprobación, los estados financieros y los "
            "asientos de cierre."),
        "datos": [
            "Aporte del propietario: Caja 4.500,00 + Terreno 60.000,00 + Muebles y enseres 3.500,00 + "
            "Equipo de computación 2.000,00 = Capital 70.000,00.",
            "Depósito del 80 % del efectivo en cuenta bancaria = 3.600,00.",
            "Maquinaria: 2 unidades × 1.600,00 = 3.200,00 (cheque 1.000,00 + letra de cambio 2.200,00).",
            "Suministros de limpieza por 1.400,00 pagados con cheque.",
            "Servicios prestados al contado por 4.500,00.",
            "Abono a documentos por pagar: 600,00.",
            "Sueldos 1.500,00 con descuento del aporte personal al IESS de 141,75 (9,45 %).",
        ],
        "asientos_esperados": [
            {"fecha": "1-abril-2023", "glosa": "Aporte del propietario en efectivo",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 4500.00, "haber": 0.0},
                        {"codigo": "31101", "cuenta": "Capital suscrito y pagado", "debe": 0.0, "haber": 4500.00}]},
            {"fecha": "1-abril-2023", "glosa": "Aporte del propietario: terreno",
             "lineas": [{"codigo": "12101", "cuenta": "Terrenos", "debe": 60000.00, "haber": 0.0},
                        {"codigo": "31101", "cuenta": "Capital suscrito y pagado", "debe": 0.0, "haber": 60000.00}]},
            {"fecha": "1-abril-2023", "glosa": "Aporte del propietario: muebles y enseres",
             "lineas": [{"codigo": "12104", "cuenta": "Muebles y enseres", "debe": 3500.00, "haber": 0.0},
                        {"codigo": "31101", "cuenta": "Capital suscrito y pagado", "debe": 0.0, "haber": 3500.00}]},
            {"fecha": "1-abril-2023", "glosa": "Aporte del propietario: equipo de computación",
             "lineas": [{"codigo": "12107", "cuenta": "Equipo de computación", "debe": 2000.00, "haber": 0.0},
                        {"codigo": "31101", "cuenta": "Capital suscrito y pagado", "debe": 0.0, "haber": 2000.00}]},
            {"fecha": "abril-2023", "glosa": "Apertura de cuenta bancaria con el 80 % del efectivo",
             "lineas": [{"codigo": "11103", "cuenta": "Bancos", "debe": 3600.00, "haber": 0.0},
                        {"codigo": "11101", "cuenta": "Caja", "debe": 0.0, "haber": 3600.00}]},
            {"fecha": "abril-2023", "glosa": "Adquisición de maquinaria (cheque y letra de cambio)",
             "lineas": [{"codigo": "12105", "cuenta": "Maquinaria y equipo", "debe": 3200.00, "haber": 0.0},
                        {"codigo": "11103", "cuenta": "Bancos", "debe": 0.0, "haber": 1000.00},
                        {"codigo": "21104", "cuenta": "Documentos por pagar", "debe": 0.0, "haber": 2200.00}]},
            {"fecha": "abril-2023", "glosa": "Compra de suministros de limpieza con cheque",
             "lineas": [{"codigo": "11401", "cuenta": "Inv. de suministros o materiales a ser consumidos",
                         "debe": 1400.00, "haber": 0.0},
                        {"codigo": "11103", "cuenta": "Bancos", "debe": 0.0, "haber": 1400.00}]},
            {"fecha": "abril-2023", "glosa": "Servicios prestados al contado",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 4500.00, "haber": 0.0},
                        {"codigo": "41201", "cuenta": "Ingresos por servicios", "debe": 0.0, "haber": 4500.00}]},
            {"fecha": "abril-2023", "glosa": "Abono a documentos por pagar",
             "lineas": [{"codigo": "21104", "cuenta": "Documentos por pagar", "debe": 600.00, "haber": 0.0},
                        {"codigo": "11101", "cuenta": "Caja", "debe": 0.0, "haber": 600.00}]},
            {"fecha": "abril-2023", "glosa": "Pago de sueldos con retención del aporte personal al IESS",
             "lineas": [{"codigo": "51101", "cuenta": "Sueldos y salarios", "debe": 1500.00, "haber": 0.0},
                        {"codigo": "11101", "cuenta": "Caja", "debe": 0.0, "haber": 1358.25},
                        {"codigo": "21501", "cuenta": "Aporte personal 9,45 %", "debe": 0.0, "haber": 141.75}]},
        ],
        "saldos_finales": {
            "debitos": {"Caja": 3441.75, "Terrenos": 60000.00, "Muebles y enseres": 3500.00,
                        "Equipo de computación": 2000.00, "Bancos": 1200.00, "Maquinaria y equipo": 3200.00,
                        "Inv. de suministros": 1400.00, "Sueldos y salarios": 1500.00},
            "creditos": {"Capital suscrito y pagado": 70000.00, "Documentos por pagar": 1600.00,
                         "Ingresos por servicios": 4500.00, "Aporte personal 9,45 %": 141.75},
        },
        "totales_verificados": {"sumas_debe": 84800.00, "sumas_haber": 84800.00,
                                "saldos_debe": 76241.75, "saldos_haber": 76241.75},
        "solucion": [
            "Libro Mayor (U2 imp. 146–149): Caja 9.000,00 / 5.558,25 → saldo deudor 3.441,75; Terrenos 60.000,00; "
            "Muebles 3.500,00; Equipo de computación 2.000,00; Capital pagado 70.000,00; Bancos 3.600,00 / 2.400,00 "
            "→ 1.200,00; Maquinaria 3.200,00; Documentos por pagar 600,00 / 2.200,00 → 1.600,00 acreedor; "
            "Suministros 1.400,00; Ingresos por servicios 4.500,00; Sueldos 1.500,00; Aporte personal 141,75.",
            "Totales del mayor: 84.800,00 = 84.800,00; saldos 76.241,75 = 76.241,75.",
            "Estado de Resultados (U2 imp. 167): ingresos 4.500,00 − gastos 1.500,00 = utilidad operacional "
            "3.000,00; − 15 % trabajadores 450,00 = utilidad imponible 2.550,00; − impuesto a la renta 637,50 = "
            "utilidad del ejercicio 1.912,50.",
            "Cierre: 3 asientos (véase §60.4.2) cuya serie totaliza 180.700,00 en ambos lados (U2 imp. 168).",
        ],
        "correcciones": [],
        "etiquetas": [
            "dato reconstruido — pendiente de validación con el facsímil",
        ],
        "advertencias": [
            "El balance de comprobación tabulado de BrilloCar está en páginas de imagen (PDF 188–190 / "
            "imp. 169–172) y no tiene capa de texto: el saldo post-cierre de 74.741,75 es reconstrucción por "
            "cálculo, no cifra impresa, y no puede usarse como respuesta oficial de una actividad evaluable.",
            "Las 10 partidas cargadas corresponden a los 10 asientos que menciona §61.1 (el aporte se presenta "
            "desglosado por bien aportado); sus sumas totalizan los 84.800,00 publicados por el libro.",
            "Tarifas usadas: IVA 15 %, aporte personal al IESS 9,45 %, participación a los trabajadores 15 % e "
            "impuesto a la renta implícito del 25 % — todas «Configuración académica / demostrativa» (§62.2).",
        ],
        "contexto_normativo": "Ecuador — ejercicio demostrativo del libro U2 (2023)",
    },

    # -------------------------------------------------------------------------------- 61.2
    {
        "codigo": "C61.02",
        "nombre": "Ambato Cía. Ltda.: venta, costo de ventas y devolución",
        "unidad": 4,
        "tipo": "VENTAS_CON_COSTO",
        "dificultad": "INTERMEDIO",
        "fuente": "U4",
        "paginas_impresas": "102–103",
        "anio": 2024,
        "estado_validacion": "VERIFICADO",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Venta en efectivo de 20 juegos de sábanas a 75,00 cada uno más IVA (factura 001-001-00987); el "
            "costo unitario es 45,00. El 22 de mayo el cliente devuelve 10 juegos con la nota de crédito "
            "001-001-00901 y se le entrega efectivo."),
        "datos": [
            "Venta: 20 juegos × 75,00 = 1.500,00 más IVA 15 % = 225,00 → cobrado 1.725,00.",
            "Costo de ventas: 20 juegos × 45,00 = 900,00.",
            "Devolución del 22 de mayo: 10 juegos × 75,00 = 750,00 más IVA 112,50 = 862,50.",
            "Reverso al costo de la devolución: 10 juegos × 45,00 = 450,00.",
        ],
        "asientos_esperados": [
            {"fecha": "mayo-2024", "glosa": "Venta en efectivo factura 001-001-00987",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 1725.00, "haber": 0.0},
                        {"codigo": "41101", "cuenta": "Venta de mercaderías", "debe": 0.0, "haber": 1500.00},
                        {"codigo": "21301", "cuenta": "IVA cobrado (IVA ventas)", "debe": 0.0, "haber": 225.00}]},
            {"fecha": "mayo-2024", "glosa": "Costo de ventas de los 20 juegos",
             "lineas": [{"codigo": "51301", "cuenta": "Costo de ventas", "debe": 900.00, "haber": 0.0},
                        {"codigo": "11402", "cuenta": "Inv. de mercadería en almacén comprada a terceros",
                         "debe": 0.0, "haber": 900.00}]},
            {"fecha": "22-mayo-2024", "glosa": "Devolución en ventas con nota de crédito 001-001-00901",
             "lineas": [{"codigo": "41101", "cuenta": "Venta de mercaderías", "debe": 750.00, "haber": 0.0},
                        {"codigo": "21301", "cuenta": "IVA cobrado (IVA ventas)", "debe": 112.50, "haber": 0.0},
                        {"codigo": "11101", "cuenta": "Caja", "debe": 0.0, "haber": 862.50}]},
            {"fecha": "22-mayo-2024", "glosa": "Reverso del costo de ventas de la devolución",
             "lineas": [{"codigo": "11402", "cuenta": "Inv. de mercadería en almacén comprada a terceros",
                         "debe": 450.00, "haber": 0.0},
                        {"codigo": "51301", "cuenta": "Costo de ventas", "debe": 0.0, "haber": 450.00}]},
        ],
        "saldos_finales": {},
        "totales_verificados": {"sumas_debe": 3987.50, "sumas_haber": 3987.50},
        "solucion": [
            "Las cuatro partidas están resueltas en la fuente y cuadran: venta 1.725,00 = 1.500,00 + 225,00; "
            "costo 900,00; devolución 862,50 = 750,00 + 112,50; reverso al costo 450,00.",
        ],
        "correcciones": [
            {"campo": "fecha del asiento de devolución",
             "valor_libro": "20-may",
             "valor_corregido": "22-may",
             "razon": "inconsistencia de fecha entre el enunciado (22 de mayo) y el rotulado del asiento; "
                      "las cifras coinciden."},
        ],
        "etiquetas": [],
        "advertencias": [
            "La fuente rotula los asientos de devolución como 20-may aunque el enunciado dice 22-may: se "
            "carga con la fecha del enunciado.",
        ],
        "contexto_normativo": "Ecuador — ejercicio demostrativo del libro U4 (2024); IVA 15 % demostrativo",
    },

    # -------------------------------------------------------------------------------- 61.3
    {
        "codigo": "C61.03",
        "nombre": "Coral Cía. Ltda. / Portal Cía. Ltda.: interés implícito en ventas a crédito",
        "unidad": 4,
        "tipo": "INTERES_IMPLICITO",
        "dificultad": "AVANZADO",
        "fuente": "U4",
        "paginas_impresas": "94–95",
        "anio": 2024,
        "estado_validacion": "VERIFICADO",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Venta de mercancías a 30 días por 12.000,00 más IVA recaudado en efectivo; la política de "
            "precios incluye un interés implícito del 24 % anual, por lo que se debe separar el ingreso "
            "financiero del ingreso por la venta."),
        "datos": [
            "Valor nominal 12.000,00 · valor actual 11.764,71 · ingreso financiero diferido 235,29.",
            "IVA 15 % recaudado en efectivo: 1.800,00.",
            "Caso de nivel avanzado: usarlo solo en actividades de profundización.",
        ],
        "asientos_esperados": [
            {"fecha": "2024", "glosa": "Venta a 30 días reconociendo el interés implícito",
             "lineas": [
                 {"codigo": "11301", "cuenta": "Cuentas y documentos por cobrar no relacionados",
                  "debe": 12000.00, "haber": 0.0},
                 {"codigo": "11101", "cuenta": "Caja", "debe": 1800.00, "haber": 0.0},
                 {"codigo": "41101", "cuenta": "Venta de bienes", "debe": 0.0, "haber": 11764.71},
                 {"codigo": "", "cuenta": "Ingresos diferidos (interés implícito)", "debe": 0.0, "haber": 235.29},
                 {"codigo": "21301", "cuenta": "IVA cobrado (IVA ventas)", "debe": 0.0, "haber": 1800.00}]},
            {"fecha": "2024", "glosa": "Cobro de la venta a los 30 días",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 12000.00, "haber": 0.0},
                        {"codigo": "11301", "cuenta": "Cuentas y documentos por cobrar no relacionados",
                         "debe": 0.0, "haber": 12000.00}]},
            {"fecha": "2024", "glosa": "Realización del ingreso financiero diferido",
             "lineas": [{"codigo": "", "cuenta": "Ingresos diferidos (interés implícito)", "debe": 235.29, "haber": 0.0},
                        {"codigo": "42201", "cuenta": "Intereses por ventas a crédito", "debe": 0.0, "haber": 235.29}]},
        ],
        "saldos_finales": {},
        "totales_verificados": {"sumas_debe": 27600.00, "sumas_haber": 27600.00},
        "solucion": [
            "Los asientos cuadran (13.800,00 = 13.800,00 en el registro de la venta).",
            "El ingreso financiero se separa del ingreso por venta: 12.000,00 − 235,29 = 11.764,71 de valor actual.",
        ],
        "correcciones": [],
        "etiquetas": [],
        "advertencias": [
            "El libro de la fuente no existe en el plan de cuentas semilla: la cuenta «Ingresos diferidos» "
            "debe crearse (pasivo) y el ingreso financiero se registra en `42201` Intereses ganados.",
            "El interés implícito del 24 % anual es un dato demostrativo del caso, no una tasa vigente (§62.2).",
        ],
        "contexto_normativo": "Ecuador — ejercicio demostrativo del libro U4 (2024)",
    },

    # -------------------------------------------------------------------------------- 61.4
    {
        "codigo": "C61.04",
        "nombre": "Smart Touch Learning: doce hechos de abril de 2010",
        "unidad": 3,
        "tipo": "JORNALIZACION_Y_BALANZA",
        "dificultad": "BASICO",
        "fuente": "U3",
        "paginas_impresas": "75–82",
        "anio": 2010,
        "estado_validacion": "VERIFICADO",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 12,
        "enunciado": (
            "Empresa de aprendizaje electrónico: se registran el aporte de la propietaria y once operaciones "
            "de abril (compra de terreno, compra a crédito, cobros, servicios a crédito, gastos, pago a "
            "proveedor, venta de terreno al costo, factura pendiente de pago y retiro del propietario). El "
            "hecho «Sheena Bright remodeló su casa con fondos personales» NO se registra por el concepto de "
            "entidad. Es el ejercicio base recomendado del simulador."),
        "datos": [
            "Aporte de la propietaria en efectivo 30.000 · compra de terreno 20.000 pagado en efectivo.",
            "Compra de suministros por 500 a crédito.",
            "Servicios cobrados 5.500 y servicios a crédito 3.000.",
            "Asiento compuesto de gastos por 3.200 (renta de computadora 600 + renta de oficina 1.200 + "
            "salarios 1.000 + servicios generales 400).",
            "Abono a proveedor 300 · cobro a crédito 2.000 · venta de terreno al costo 9.000 · factura "
            "telefónica pendiente de pago 100 · retiro del propietario 2.000.",
            "El hecho «remodeló su casa con fondos personales» no se registra (concepto de entidad).",
        ],
        "asientos_esperados": [
            {"fecha": "abril-2010", "glosa": "Aporte de la propietaria",
             "lineas": [{"cuenta": "Efectivo", "debe": 30000.00, "haber": 0.0},
                        {"cuenta": "Capital", "debe": 0.0, "haber": 30000.00}]},
            {"fecha": "abril-2010", "glosa": "Compra de terreno",
             "lineas": [{"cuenta": "Terreno", "debe": 20000.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 20000.00}]},
            {"fecha": "abril-2010", "glosa": "Compra de suministros a crédito",
             "lineas": [{"cuenta": "Suministros", "debe": 500.00, "haber": 0.0},
                        {"cuenta": "Cuentas por pagar", "debe": 0.0, "haber": 500.00}]},
            {"fecha": "abril-2010", "glosa": "Servicios prestados cobrados en efectivo",
             "lineas": [{"cuenta": "Efectivo", "debe": 5500.00, "haber": 0.0},
                        {"cuenta": "Ingresos por servicios", "debe": 0.0, "haber": 5500.00}]},
            {"fecha": "abril-2010", "glosa": "Servicios prestados a crédito",
             "lineas": [{"cuenta": "Cuentas por cobrar", "debe": 3000.00, "haber": 0.0},
                        {"cuenta": "Ingresos por servicios", "debe": 0.0, "haber": 3000.00}]},
            {"fecha": "abril-2010", "glosa": "Asiento compuesto de gastos del mes",
             "lineas": [{"cuenta": "Gastos (renta de computadora, renta de oficina, salarios y servicios generales)",
                         "debe": 3200.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 3200.00}]},
            {"fecha": "abril-2010", "glosa": "Abono a proveedor",
             "lineas": [{"cuenta": "Cuentas por pagar", "debe": 300.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 300.00}]},
            {"fecha": "abril-2010", "glosa": "Cobro a cuenta de servicios a crédito",
             "lineas": [{"cuenta": "Efectivo", "debe": 2000.00, "haber": 0.0},
                        {"cuenta": "Cuentas por cobrar", "debe": 0.0, "haber": 2000.00}]},
            {"fecha": "abril-2010", "glosa": "Venta del terreno al costo",
             "lineas": [{"cuenta": "Efectivo", "debe": 9000.00, "haber": 0.0},
                        {"cuenta": "Terreno", "debe": 0.0, "haber": 9000.00}]},
            {"fecha": "abril-2010", "glosa": "Factura telefónica pendiente de pago",
             "lineas": [{"cuenta": "Gastos", "debe": 100.00, "haber": 0.0},
                        {"cuenta": "Cuentas por pagar", "debe": 0.0, "haber": 100.00}]},
            {"fecha": "abril-2010", "glosa": "Retiro de la propietaria",
             "lineas": [{"cuenta": "Retiros del propietario", "debe": 2000.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 2000.00}]},
        ],
        "saldos_finales": {
            "debitos": {"Efectivo": 21000.00, "Cuentas por cobrar": 1000.00, "Suministros": 500.00,
                        "Terreno": 11000.00, "Retiros del propietario": 2000.00, "Gastos": 3300.00},
            "creditos": {"Cuentas por pagar": 300.00, "Capital": 30000.00, "Ingresos por servicios": 8500.00},
        },
        "totales_verificados": {"sumas_debe": 38800.00, "sumas_haber": 38800.00},
        "solucion": [
            "Saldos finales del mayor (p. 81): Efectivo 21.000 · Cuentas por cobrar 1.000 · Suministros 500 · "
            "Terreno 11.000 · Cuentas por pagar 300 · Capital 30.000 · Retiros 2.000 · Ingresos por servicios "
            "8.500 · Gastos 3.300.",
            "Balanza de comprobación 38.800,00 = 38.800,00 (p. 82).",
        ],
        "correcciones": [
            {"campo": "saldo final de Cuentas por pagar",
             "valor_libro": "500,00 (ficha §61.4)",
             "valor_corregido": "300,00",
             "razon": "con 500,00 los créditos suman 39.000,00 y la balanza publicada 38.800,00 = 38.800,00 "
                      "no cuadra; el movimiento correcto es 500,00 (compra) − 300,00 (abono) + 100,00 "
                      "(factura telefónica) = 300,00."},
        ],
        "etiquetas": [],
        "advertencias": [
            "La fuente es una traducción estadounidense (2010): sus cifras se usan como ejercicio de "
            "jornalización y su cifra fiscal «Impuesto (3 %)» no es referente ecuatoriano (§62.3 y §62.6).",
            "El simulador normaliza la visualización de todas las cifras a formato es-EC sin alterar valores.",
        ],
        "contexto_normativo": "Estados Unidos, 2010 — HISTÓRICO Y EXTRANJERO (modelo visual)",
    },

    # -------------------------------------------------------------------------------- 61.5
    {
        "codigo": "C61.05",
        "nombre": "Harper Service Center: resumen del capítulo 2",
        "unidad": 3,
        "tipo": "CUENTA_T_Y_BALANZA",
        "dificultad": "BASICO",
        "fuente": "U3",
        "paginas_impresas": "86–89",
        "anio": 2009,
        "estado_validacion": "VERIFICADO",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 12,
        "enunciado": (
            "Se entregan los saldos iniciales y diez operaciones (a–j) de marzo; se pide abrir las cuentas en "
            "formato de cuenta-T, jornalizar identificando cada asiento con su letra, traspasar al mayor y "
            "elaborar la balanza de comprobación al 31 de marzo."),
        "datos": [
            "Saldos al 1-mar: Efectivo 26.000 · Cuentas por cobrar 4.500 · Cuentas por pagar 2.000 · "
            "Capital 28.500 (total 30.500).",
            "Operaciones: préstamo con pagaré 45.000 · terreno 40.000 · servicio cobrado 5.000 · suministros "
            "a crédito 300 · servicio a crédito 2.600 · pago a proveedor 1.200 · gastos 4.900 (salarios 3.000 "
            "+ renta 1.500 + intereses 400) · cobro 3.100 · factura de servicios generales 200 · retiro 1.800.",
        ],
        "asientos_esperados": [
            {"fecha": "marzo-2009", "letra": "a", "glosa": "Préstamo con pagaré",
             "lineas": [{"cuenta": "Efectivo", "debe": 45000.00, "haber": 0.0},
                        {"cuenta": "Documentos por pagar", "debe": 0.0, "haber": 45000.00}]},
            {"fecha": "marzo-2009", "letra": "b", "glosa": "Compra de terreno",
             "lineas": [{"cuenta": "Terreno", "debe": 40000.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 40000.00}]},
            {"fecha": "marzo-2009", "letra": "c", "glosa": "Servicio prestado cobrado",
             "lineas": [{"cuenta": "Efectivo", "debe": 5000.00, "haber": 0.0},
                        {"cuenta": "Ingresos por servicios", "debe": 0.0, "haber": 5000.00}]},
            {"fecha": "marzo-2009", "letra": "d", "glosa": "Compra de suministros a crédito",
             "lineas": [{"cuenta": "Suministros", "debe": 300.00, "haber": 0.0},
                        {"cuenta": "Cuentas por pagar", "debe": 0.0, "haber": 300.00}]},
            {"fecha": "marzo-2009", "letra": "e", "glosa": "Servicio prestado a crédito",
             "lineas": [{"cuenta": "Cuentas por cobrar", "debe": 2600.00, "haber": 0.0},
                        {"cuenta": "Ingresos por servicios", "debe": 0.0, "haber": 2600.00}]},
            {"fecha": "marzo-2009", "letra": "f", "glosa": "Pago a proveedor",
             "lineas": [{"cuenta": "Cuentas por pagar", "debe": 1200.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 1200.00}]},
            {"fecha": "marzo-2009", "letra": "g", "glosa": "Pago de gastos del mes",
             "lineas": [{"cuenta": "Gastos por salarios", "debe": 3000.00, "haber": 0.0},
                        {"cuenta": "Gastos por renta", "debe": 1500.00, "haber": 0.0},
                        {"cuenta": "Gastos por intereses", "debe": 400.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 4900.00}]},
            {"fecha": "marzo-2009", "letra": "h", "glosa": "Cobro a cuenta de clientes",
             "lineas": [{"cuenta": "Efectivo", "debe": 3100.00, "haber": 0.0},
                        {"cuenta": "Cuentas por cobrar", "debe": 0.0, "haber": 3100.00}]},
            {"fecha": "marzo-2009", "letra": "i", "glosa": "Factura de servicios generales pendiente de pago",
             "lineas": [{"cuenta": "Gastos por servicios generales", "debe": 200.00, "haber": 0.0},
                        {"cuenta": "Cuentas por pagar", "debe": 0.0, "haber": 200.00}]},
            {"fecha": "marzo-2009", "letra": "j", "glosa": "Retiro del propietario",
             "lineas": [{"cuenta": "Retiros del propietario", "debe": 1800.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 1800.00}]},
        ],
        "saldos_finales": {
            "debitos": {"Efectivo": 31200.00, "Cuentas por cobrar": 4000.00, "Suministros": 300.00,
                        "Terreno": 40000.00, "Retiros del propietario": 1800.00,
                        "Gastos por salarios": 3000.00, "Gastos por renta": 1500.00,
                        "Gastos por servicios generales": 200.00, "Gastos por intereses": 400.00},
            "creditos": {"Cuentas por pagar": 1300.00, "Documentos por pagar": 45000.00,
                         "Capital": 28500.00, "Ingresos por servicios": 7600.00},
        },
        "totales_verificados": {"sumas_debe": 82400.00, "sumas_haber": 82400.00},
        "solucion": [
            "Saldos finales: Efectivo 31.200 · CxC 4.000 · Suministros 300 · Terreno 40.000 · Cuentas por "
            "pagar 1.300 · Documentos por pagar 45.000 · Retiros 1.800 · Capital 28.500 · Ingresos 7.600 · "
            "Gastos por salarios 3.000 · renta 1.500 · servicios generales 200 · intereses 400.",
            "Balanza de comprobación 82.400,00 = 82.400,00.",
        ],
        "correcciones": [],
        "etiquetas": [],
        "advertencias": [
            "La fuente usa el rayado estadounidense (cuenta-T) como modelo visual; la terminología del "
            "simulador es la del syllabus ecuatoriano (§62.6).",
        ],
        "contexto_normativo": "Estados Unidos, 2009 — HISTÓRICO Y EXTRANJERO (modelo visual)",
    },

    # -------------------------------------------------------------------------------- 61.6
    {
        "codigo": "C61.06",
        "nombre": "Heat Miser Air Conditioner Company: compras, ventas, descuentos y flete",
        "unidad": 3,
        "tipo": "DESCUENTOS_Y_FLETE",
        "dificultad": "INTERMEDIO",
        "fuente": "U3",
        "paginas_impresas": "284–285",
        "anio": 2011,
        "estado_validacion": "VERIFICADO",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 12,
        "enunciado": (
            "Once operaciones del mes de junio con compras y ventas a crédito, descuentos por pronto pago, "
            "devoluciones y flete, más un préstamo bancario para aprovechar el descuento. Es el mejor caso "
            "para enseñar el orden de cálculo (compra − devolución) × % de descuento."),
        "datos": [
            "Jun 3: compra 1.600 (1/10, neto eom). Jun 9: devolución del 40 % = 640.",
            "Jun 12: venta al contado 920 (costo 550). Jun 15: compra 5.000 (3/15, n/30).",
            "Jun 16: flete 260. Jun 18: venta a crédito 2.000 (2/10, n/30; costo 1.180).",
            "Jun 22: devolución de venta 800 (costo 480).",
            "Jun 24: préstamo con pagaré 4.850 y pago al proveedor 4.850 (descuento 150).",
            "Jun 28: cobro 1.176 (descuento sobre ventas 24). Jun 29: pago 960.",
        ],
        "asientos_esperados": [
            {"fecha": "03-jun", "glosa": "Compra a crédito 1.600 (1/10, neto eom)",
             "lineas": [{"cuenta": "Inventarios", "debe": 1600.00, "haber": 0.0},
                        {"cuenta": "Cuentas por pagar", "debe": 0.0, "haber": 1600.00}]},
            {"fecha": "09-jun", "glosa": "Devolución en compras del 40 % (640)",
             "lineas": [{"cuenta": "Cuentas por pagar", "debe": 640.00, "haber": 0.0},
                        {"cuenta": "Inventarios", "debe": 0.0, "haber": 640.00}]},
            {"fecha": "12-jun", "glosa": "Venta al contado 920",
             "lineas": [{"cuenta": "Efectivo", "debe": 920.00, "haber": 0.0},
                        {"cuenta": "Ventas", "debe": 0.0, "haber": 920.00}]},
            {"fecha": "12-jun", "glosa": "Costo de la venta al contado",
             "lineas": [{"cuenta": "Costo de los bienes vendidos", "debe": 550.00, "haber": 0.0},
                        {"cuenta": "Inventarios", "debe": 0.0, "haber": 550.00}]},
            {"fecha": "15-jun", "glosa": "Compra a crédito 5.000 (3/15, n/30)",
             "lineas": [{"cuenta": "Inventarios", "debe": 5000.00, "haber": 0.0},
                        {"cuenta": "Cuentas por pagar", "debe": 0.0, "haber": 5000.00}]},
            {"fecha": "16-jun", "glosa": "Flete en compras pagado en efectivo",
             "lineas": [{"cuenta": "Inventarios", "debe": 260.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 260.00}]},
            {"fecha": "18-jun", "glosa": "Venta a crédito 2.000 (2/10, n/30)",
             "lineas": [{"cuenta": "Cuentas por cobrar", "debe": 2000.00, "haber": 0.0},
                        {"cuenta": "Ventas", "debe": 0.0, "haber": 2000.00}]},
            {"fecha": "18-jun", "glosa": "Costo de la venta a crédito",
             "lineas": [{"cuenta": "Costo de los bienes vendidos", "debe": 1180.00, "haber": 0.0},
                        {"cuenta": "Inventarios", "debe": 0.0, "haber": 1180.00}]},
            {"fecha": "22-jun", "glosa": "Devolución en ventas 800",
             "lineas": [{"cuenta": "Ventas", "debe": 800.00, "haber": 0.0},
                        {"cuenta": "Cuentas por cobrar", "debe": 0.0, "haber": 800.00}]},
            {"fecha": "22-jun", "glosa": "Reverso del costo de la devolución en ventas",
             "lineas": [{"cuenta": "Inventarios", "debe": 480.00, "haber": 0.0},
                        {"cuenta": "Costo de los bienes vendidos", "debe": 0.0, "haber": 480.00}]},
            {"fecha": "24-jun", "glosa": "Préstamo con pagaré para aprovechar el descuento",
             "lineas": [{"cuenta": "Efectivo", "debe": 4850.00, "haber": 0.0},
                        {"cuenta": "Documentos por pagar", "debe": 0.0, "haber": 4850.00}]},
            {"fecha": "24-jun", "glosa": "Pago al proveedor dentro del período de descuento (3 %)",
             "lineas": [{"cuenta": "Cuentas por pagar", "debe": 5000.00, "haber": 0.0},
                        {"cuenta": "Descuento sobre compras", "debe": 0.0, "haber": 150.00},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 4850.00}]},
            {"fecha": "28-jun", "glosa": "Cobro al cliente dentro del período de descuento (2 %)",
             "lineas": [{"cuenta": "Efectivo", "debe": 1176.00, "haber": 0.0},
                        {"cuenta": "Descuento sobre ventas", "debe": 24.00, "haber": 0.0},
                        {"cuenta": "Cuentas por cobrar", "debe": 0.0, "haber": 1200.00}]},
            {"fecha": "29-jun", "glosa": "Pago de la factura del 3 de junio (1.600 − 640)",
             "lineas": [{"cuenta": "Cuentas por pagar", "debe": 960.00, "haber": 0.0},
                        {"cuenta": "Efectivo", "debe": 0.0, "haber": 960.00}]},
        ],
        "saldos_finales": {},
        "totales_verificados": {
            "inventarios": 4820.00,
            "costo_de_los_bienes_vendidos": 1250.00,
            "comprobacion_inventarios": "1.600 − 640 + 5.000 + 260 − 550 − 1.180 + 480 − 150 = 4.820",
            "comprobacion_cdv": "550 + 1.180 − 480 = 1.250",
        },
        "solucion": [
            "Inventarios 4.820,00 y Costo de los bienes vendidos 1.250,00 (comprobados aritméticamente).",
            "Análisis: el descuento obtenido (150) supera los intereses pagados (90); beneficio neto 60.",
        ],
        "correcciones": [],
        "etiquetas": [],
        "advertencias": [
            "Fuente estadounidense (2011): las operaciones no llevan IVA porque la fuente es anterior a su "
            "tratamiento en ese material; el caso se usa para descuentos, devoluciones y flete (§62.3).",
            "El «Impuesto (3 %)» de una factura de compra de 2011 es un dato histórico y estadounidense.",
        ],
        "contexto_normativo": "Estados Unidos, 2011 — HISTÓRICO Y EXTRANJERO (modelo visual)",
    },

    # -------------------------------------------------------------------------------- 61.7
    {
        "codigo": "C61.07",
        "nombre": "Muebles el Cóndor Ltda.: comprobante de diario, Mayor y Balances y balance de comprobación",
        "unidad": 3,
        "tipo": "MAYOR_Y_BALANCES",
        "dificultad": "INTERMEDIO",
        "fuente": "SENA",
        "paginas_impresas": "57–63",
        "anio": 1977,
        "estado_validacion": "VERIFICADO_CON_RESERVA",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "TOTALES",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Se entrega el «Libro Mayor y Balances» al 1 de enero de 1977 con 16 cuentas y cuatro "
            "comprobantes de diario del mes; se pide elaborar el balance de comprobación inicial, trasladar "
            "los comprobantes al Diario Columnario, hacer los pases al Libro Mayor y Balances y obtener el "
            "nuevo balance (una hora de tiempo máximo)."),
        "datos": [
            "Saldos al 1-ene-1977 — débitos: Caja 71.000 · Bancos 600.000 · Letras por cobrar 250.000 · "
            "Cuentas por cobrar 180.000 · Mercancías 130.000 · Edificios 950.000 · Terrenos 45.000 · "
            "Seguro prepagado 90.000 · Vehículos 145.000 · Equipo de oficina 180.000 · Arrendamiento "
            "prepagado 30.000.",
            "Saldos al 1-ene-1977 — créditos: Cuentas por pagar 170.000 · Letras por pagar 230.000 · "
            "Obligaciones bancarias 794.000 · Obligaciones hipotecarias 490.000 · Capital 987.000.",
            "Comprobantes del mes (totales verificados): No. 001 (ene 8) 385.000 = 385.000; No. 002 (ene 16) "
            "910.000 = 910.000; No. 003 (ene 24) 412.100 = 412.100; No. 004 (ene 31) 65.000 = 65.000.",
        ],
        "asientos_esperados": [],
        "saldos_finales": {
            "debitos": {"Caja": 71000.00, "Bancos": 600000.00, "Letras por cobrar": 250000.00,
                        "Cuentas por cobrar": 180000.00, "Mercancías": 130000.00, "Edificios": 950000.00,
                        "Terrenos": 45000.00, "Seguro prepagado": 90000.00, "Vehículos": 145000.00,
                        "Equipo de oficina": 180000.00, "Arrendamiento prepagado": 30000.00},
            "creditos": {"Cuentas por pagar": 170000.00, "Letras por pagar": 230000.00,
                         "Obligaciones bancarias": 794000.00, "Obligaciones hipotecarias": 490000.00,
                         "Capital": 987000.00},
        },
        "totales_verificados": {"sumas_debe": 2671000.00, "sumas_haber": 2671000.00,
                                "comprobante_001": 385000.00, "comprobante_002": 910000.00,
                                "comprobante_003": 412100.00, "comprobante_004": 65000.00},
        "solucion": [
            "La unidad trae el Libro Mayor y Balances diligenciado (pp. 62–63).",
            "El balance de comprobación inicial suma 2.671.000,00 = 2.671.000,00.",
        ],
        "correcciones": [],
        "etiquetas": [
            "dato reconstruido — pendiente de validación con el facsímil",
        ],
        "advertencias": [
            "Reserva obligatoria: el OCR de la Fuente B es defectuoso; el DETALLE de los comprobantes 001 y "
            "002 es reconstrucción basada en los totales legibles y debe verificarse contra el facsímil "
            "(pp. 58–59) antes de publicar el caso. Hasta entonces solo se cargan los saldos iniciales y los "
            "totales de los comprobantes.",
            "Los requisitos legales del Libro Mayor («libro principal exigido por la Ley», SENA p. 56) son de "
            "Colombia, 1977, y no pueden citarse como normativa vigente.",
        ],
        "contexto_normativo": "Colombia, 1977 — HISTÓRICO Y EXTRANJERO (solo modelo visual del rayado)",
        "contenido_publicable": ["saldos_iniciales", "totales_de_comprobantes"],
    },

    # -------------------------------------------------------------------------------- 61.8
    {
        "codigo": "C61.08",
        "nombre": "Autocontroles breves del SENA (pases al mayor, saldos y balance)",
        "unidad": 3,
        "tipo": "AUTOCONTROLES",
        "dificultad": "BASICO",
        "fuente": "SENA",
        "paginas_impresas": "17–57",
        "anio": 1977,
        "estado_validacion": "VERIFICADO",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Cuatro autocontroles breves: (1) pase al Mayor de cuatro asientos del diario (pp. 17–19); "
            "(2) cálculo de saldos (pp. 23–25); (3) balance de comprobación desde cinco cuentas del mayor "
            "(pp. 42–44); (4) Libro Mayor y Balances con saldos anteriores y movimiento de noviembre en el "
            "Diario Columnario, comprobantes 025 a 028 (pp. 52–57)."),
        "datos": [
            "pp. 17–19: venta al contado 10.000 · consignación 9.000 · compra de escritorio al contado con "
            "cheque No. 40 por 2.000 · pago de la factura No. 14 de A. GOE por 4.000.",
            "pp. 23–25: Caja débitos 2.000 / créditos 1.500 → saldo débito 500; Cuentas por pagar créditos "
            "500 / débitos 400 → saldo crédito 100.",
            "pp. 42–44: Caja 5.000, Bancos 7.000, Muebles y enseres 2.000 y Cuentas por cobrar 1.000 en "
            "débitos; Ventas 10.000 y Cuentas por cobrar 4.000 en créditos → 14.000 = 14.000.",
            "pp. 52–57: cifras de lectura OCR, pendientes de verificación contra el facsímil.",
        ],
        "asientos_esperados": [
            {"fecha": "1977", "subcaso": "p. 17–19", "glosa": "Venta al contado",
             "lineas": [{"cuenta": "Caja", "debe": 10000.00, "haber": 0.0},
                        {"cuenta": "Ventas", "debe": 0.0, "haber": 10000.00}]},
            {"fecha": "1977", "subcaso": "p. 17–19", "glosa": "Consignación bancaria",
             "lineas": [{"cuenta": "Bancos", "debe": 9000.00, "haber": 0.0},
                        {"cuenta": "Caja", "debe": 0.0, "haber": 9000.00}]},
            {"fecha": "1977", "subcaso": "p. 17–19", "glosa": "Compra de escritorio con cheque No. 40",
             "lineas": [{"cuenta": "Muebles y enseres", "debe": 2000.00, "haber": 0.0},
                        {"cuenta": "Bancos", "debe": 0.0, "haber": 2000.00}]},
            {"fecha": "1977", "subcaso": "p. 17–19", "glosa": "Pago de la factura No. 14 de A. GOE",
             "lineas": [{"cuenta": "Cuentas por pagar (A. GOE)", "debe": 4000.00, "haber": 0.0},
                        {"cuenta": "Caja", "debe": 0.0, "haber": 4000.00}]},
        ],
        "saldos_finales": {},
        "totales_verificados": {
            "saldo_caja_p23_25": 500.00,
            "saldo_cuentas_por_pagar_p23_25": 100.00,
            "balance_p42_44_debe": 14000.00,
            "balance_p42_44_haber": 14000.00,
        },
        "solucion": [
            "Solución de los cuatro asientos en pp. 19–21; saldos en pp. 23–25 (Caja débito 500, Cuentas por "
            "pagar crédito 100); balance de comprobación 14.000 = 14.000 en pp. 42–44.",
            "Las cifras de la p. 52–57 son lectura OCR y deben verificarse contra el facsímil antes de usarse.",
        ],
        "correcciones": [],
        "etiquetas": [
            "dato reconstruido — pendiente de validación con el facsímil",
        ],
        "advertencias": [
            "El autocontrol de las pp. 52–57 se carga SOLO como referencia visual: sus cifras requieren "
            "cotejo con el facsímil y no pueden ser respuesta oficial.",
        ],
        "contexto_normativo": "Colombia, 1977 — HISTÓRICO Y EXTRANJERO (modelo visual)",
        "contenido_publicable": ["asientos_pp17_19", "saldos_pp23_25", "balance_pp42_44"],
    },

    # -------------------------------------------------------------------------------- 61.9
    {
        "codigo": "C61.09",
        "nombre": "Ejercicios cortos resueltos de U4 (suministros, aportes, comisiones e inventario permanente)",
        "unidad": 4,
        "tipo": "EJERCICIOS_CORTOS",
        "dificultad": "INTERMEDIO",
        "fuente": "U4",
        "paginas_impresas": "42–97",
        "anio": 2024,
        "estado_validacion": "VERIFICADO",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 12,
        "enunciado": (
            "Seis ejercicios cortos resueltos: compra de suministros con pago parcial, compra a crédito con "
            "IVA pagado con cheque, aporte individual, aporte de compañía con parciales por socio, comisiones "
            "ganadas y venta con inventario permanente y su devolución."),
        "datos": [
            "Suministros (imp. 42–43): compra de 200,00 más IVA 30,00; paga 100,00 en efectivo y el saldo a crédito.",
            "Compra a crédito con IVA con cheque (imp. 46–47): cinco computadoras por 3.000,00 con IVA 450,00 "
            "pagado con cheque.",
            "Aporte individual (imp. 88–89): dinero 15.000,00 y muebles y enseres 3.000,00.",
            "Aporte de compañía con parciales (imp. 88–89): Arcos 8.000,00 en efectivo + Lapo 5.000,00 en "
            "muebles + Bonilla 3.000,00 en mercaderías. Patrón recomendado para el registro de aportes.",
            "Comisiones ganadas (imp. 96–97): cobro de 2.800,00 más IVA.",
            "Inventario permanente con unidades (imp. 80–81): venta de 600 unidades por 27.000,00 + IVA "
            "4.050,00 con costo 24.000,00; devolución de 150 unidades por 6.750,00 + IVA 1.012,50 con reverso "
            "al costo de 6.000,00.",
        ],
        "asientos_esperados": [
            {"subcaso": "suministros (imp. 42–43)", "glosa": "Compra de suministros con pago parcial",
             "lineas": [{"codigo": "11405", "cuenta": "Suministros de oficina", "debe": 200.00, "haber": 0.0},
                        {"codigo": "11601", "cuenta": "IVA compras", "debe": 30.00, "haber": 0.0},
                        {"codigo": "11101", "cuenta": "Caja", "debe": 0.0, "haber": 100.00},
                        {"codigo": "21101", "cuenta": "Cuentas y documentos por pagar proveedores",
                         "debe": 0.0, "haber": 130.00}]},
            {"subcaso": "compra con cheque (imp. 46–47)", "glosa": "Cinco computadoras a crédito con IVA pagado con cheque",
             "lineas": [{"codigo": "11402", "cuenta": "Inventario de mercadería", "debe": 3000.00, "haber": 0.0},
                        {"codigo": "11601", "cuenta": "IVA compras", "debe": 450.00, "haber": 0.0},
                        {"codigo": "21101", "cuenta": "Cuentas y documentos por pagar proveedores",
                         "debe": 0.0, "haber": 3000.00},
                        {"codigo": "11103", "cuenta": "Bancos", "debe": 0.0, "haber": 450.00}]},
            {"subcaso": "aporte individual (imp. 88–89)", "glosa": "Aporte individual de Jaime Astudillo",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 15000.00, "haber": 0.0},
                        {"codigo": "12104", "cuenta": "Muebles y enseres", "debe": 3000.00, "haber": 0.0},
                        {"codigo": "31101", "cuenta": "Capital Jaime Astudillo", "debe": 0.0, "haber": 18000.00}]},
            {"subcaso": "aporte de compañía (imp. 88–89)", "glosa": "Aporte de compañía con parciales por socio",
             "lineas": [{"codigo": "11101", "cuenta": "Caja (Arcos)", "debe": 8000.00, "haber": 0.0},
                        {"codigo": "11402", "cuenta": "Inventario de mercadería (Bonilla)", "debe": 3000.00, "haber": 0.0},
                        {"codigo": "12104", "cuenta": "Muebles y enseres (Lapo)", "debe": 5000.00, "haber": 0.0},
                        {"codigo": "31101", "cuenta": "Capital social", "debe": 0.0, "haber": 16000.00}]},
            {"subcaso": "comisiones ganadas (imp. 96–97)", "glosa": "Cobro de comisiones más IVA",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 3220.00, "haber": 0.0},
                        {"codigo": "42201", "cuenta": "Comisiones ganadas", "debe": 0.0, "haber": 2800.00},
                        {"codigo": "21301", "cuenta": "IVA cobrado (IVA ventas)", "debe": 0.0, "haber": 420.00}]},
            {"subcaso": "inventario permanente — venta (imp. 80–81)", "glosa": "Venta de 600 unidades",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 31050.00, "haber": 0.0},
                        {"codigo": "41101", "cuenta": "Venta de mercaderías", "debe": 0.0, "haber": 27000.00},
                        {"codigo": "21301", "cuenta": "IVA cobrado (IVA ventas)", "debe": 0.0, "haber": 4050.00}]},
            {"subcaso": "inventario permanente — costo (imp. 80–81)", "glosa": "Costo de la venta de 600 unidades",
             "lineas": [{"codigo": "51301", "cuenta": "Costo de ventas", "debe": 24000.00, "haber": 0.0},
                        {"codigo": "11402", "cuenta": "Inventario de mercadería", "debe": 0.0, "haber": 24000.00}]},
            {"subcaso": "inventario permanente — devolución (imp. 80–81)",
             "glosa": "Devolución de 150 unidades con nota de crédito",
             "lineas": [{"codigo": "41101", "cuenta": "Venta de mercaderías", "debe": 6750.00, "haber": 0.0},
                        {"codigo": "21301", "cuenta": "IVA cobrado (IVA ventas)", "debe": 1012.50, "haber": 0.0},
                        {"codigo": "11101", "cuenta": "Caja", "debe": 0.0, "haber": 7762.50}]},
            {"subcaso": "inventario permanente — reverso al costo (imp. 80–81)",
             "glosa": "Reverso del costo de las 150 unidades devueltas",
             "lineas": [{"codigo": "11402", "cuenta": "Inventario de mercadería", "debe": 6000.00, "haber": 0.0},
                        {"codigo": "51301", "cuenta": "Costo de ventas", "debe": 0.0, "haber": 6000.00}]},
        ],
        "saldos_finales": {},
        "totales_verificados": {"iva_compras_suministros": 30.00, "iva_compras_computadoras": 450.00,
                                "iva_venta_600_unidades": 4050.00, "iva_devolucion_150_unidades": 1012.50},
        "solucion": [
            "Los seis ejercicios traen su asiento resuelto en la fuente y cuadran (IVA 15 % demostrativo).",
            "El asiento de aporte de compañía con parciales por socio es el patrón recomendado para el "
            "registro de aportes en el simulador.",
        ],
        "correcciones": [],
        "etiquetas": [],
        "advertencias": [
            "El IVA del 15 % es línea de cálculo demostrativa de los ejemplos de U4; la fuente no lo explica "
            "como normativa (§62.3).",
        ],
        "contexto_normativo": "Ecuador — ejercicios demostrativos del libro U4 (2024)",
    },

    # -------------------------------------------------------------------------------- 61.10
    {
        "codigo": "C61.10",
        "nombre": "Ejercicios cortos del capítulo 5 de U3 (descuentos por pronto pago)",
        "unidad": 3,
        "tipo": "DESCUENTOS_POR_PRONTO_PAGO",
        "dificultad": "INTERMEDIO",
        "fuente": "U3",
        "paginas_impresas": "300–301",
        "anio": 2011,
        "estado_validacion": "VERIFICADO",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "TOTALES",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Cuatro ejercicios cortos del capítulo 5: compra con devolución y descuento por pronto pago "
            "(EC5-2/EC5-3, The Funhouse ↔ PegaBlock), venta a crédito con devolución y descuento (EC5-6/EC5-7, "
            "Southam.com), compra pagada dentro del período de descuento (EC5-1, Ronny's) y compra a crédito "
            "con descuento (EC5-4, BullsEye ↔ Muddy John)."),
        "datos": [
            "EC5-2 / EC5-3: compra de juguetes por 105.900, términos 2/10, n/45; devolución de 10.540 por "
            "daño → a pagar después del período de descuento 95.360; dentro del período 93.452,80. Fechas: "
            "compra 8-jul-2011, devolución 12-jul-2011, pago 15-jul-2011.",
            "EC5-6 / EC5-7: venta a crédito de 2.000 libros a 19,00 = 38.000 (costo 22.800); devolución de "
            "100 libros dañados el 13-oct (costo 1.140); pago el 22-oct; términos 2/20, n/45 → devolución "
            "sobre ventas 1.900 (CxC 36.100), descuento sobre ventas 722, cobro 35.378. Luego calcular ventas "
            "netas y utilidad bruta.",
            "EC5-1 (Ronny's): compra a crédito de 18.130 con términos 3/15, n/45 pagada dentro del período "
            "→ neto 17.586,10 (cálculo aritmético del extractor, no cifra impresa).",
            "EC5-4 (BullsEye ↔ Muddy John): compra a crédito de 60.000 el 1-jul-2011 con pago el 10-jul-2011 "
            "dentro del período de descuento. La extracción no transcribió el porcentaje del término: "
            "NO CARGABLE hasta verificar en la fuente.",
        ],
        "asientos_esperados": [],
        "saldos_finales": {},
        "totales_verificados": {
            "ec5_2_3_compra": 105900.00, "ec5_2_3_devolucion": 10540.00,
            "ec5_2_3_a_pagar_fuera_de_plazo": 95360.00, "ec5_2_3_a_pagar_en_plazo": 93452.80,
            "ec5_6_7_venta": 38000.00, "ec5_6_7_costo": 22800.00, "ec5_6_7_devolucion": 1900.00,
            "ec5_6_7_saldo_por_cobrar": 36100.00, "ec5_6_7_descuento": 722.00, "ec5_6_7_cobro": 35378.00,
            "ec5_1_neto": 17586.10,
        },
        "solucion": [
            "EC5-2/EC5-3: 105.900 − 10.540 = 95.360; 95.360 × 98 % = 93.452,80.",
            "EC5-6/EC5-7: devolución 100 × 19,00 = 1.900; CxC 38.000 − 1.900 = 36.100; descuento 2 % = 722; "
            "cobro 35.378.",
            "EC5-1: 18.130 × 97 % = 17.586,10 (cálculo aritmético, no cifra impresa).",
        ],
        "correcciones": [],
        "etiquetas": [
            "solución calculada, no publicada por el libro",
        ],
        "advertencias": [
            "EC5-4 NO se carga: la extracción no transcribió el porcentaje del término de descuento y debe "
            "verificarse en la fuente antes de usarlo.",
            "Las cifras de la fuente usan formato angloamericano; el simulador las muestra en formato es-EC "
            "sin alterar valores (§62.6).",
        ],
        "contexto_normativo": "Estados Unidos, 2011 — HISTÓRICO Y EXTRANJERO (modelo visual)",
        "subcasos": [
            {"codigo": "EC5-2/EC5-3", "cargable": True, "nota": "Resultado verificado aritméticamente."},
            {"codigo": "EC5-6/EC5-7", "cargable": True, "nota": "Resultado verificado aritméticamente."},
            {"codigo": "EC5-1", "cargable": True,
             "nota": "Neto calculado (17.586,10): no es cifra impresa."},
            {"codigo": "EC5-4", "cargable": False,
             "nota": "Falta el porcentaje del término de descuento: verificar en la fuente antes de cargarlo."},
        ],
    },

    # -------------------------------------------------------------------------------- 61.11
    {
        "codigo": "C61.11",
        "nombre": "Limpia-Full: ecuación contable ampliada",
        "unidad": 2,
        "tipo": "ECUACION_CONTABLE",
        "dificultad": "BASICO",
        "fuente": "U2",
        "paginas_impresas": "121",
        "anio": 2025,
        "estado_validacion": "SIN_SOLUCION",
        "solucion_en_fuente": False,
        "solucion_visible": False,
        "solucion_referencial": {"activo": 74650.00, "pasivo": 22800.00, "capital": 41850.00,
                                 "ingresos": 14000.00, "gastos": 4000.00},
        "tipo_verificacion": "ECUACION",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Con los saldos dados, «Calcular los elementos de la ecuación contable ampliada» "
            "(Activo = Pasivo + Capital + Ingresos − Gastos). El libro deja la tabla en blanco."),
        "datos": [
            "Caja 450,00 · Bancos 44.000,00 · Materiales y suministros de limpieza 28.500,00 · Equipo de "
            "computación 1.700,00.",
            "Préstamo bancario 16.000,00 · Proveedores 6.800,00.",
            "Gastos de personal 3.500,00 · Publicidad y propaganda 500,00 · Ingresos por servicios 14.000,00.",
        ],
        "asientos_esperados": [],
        "saldos_finales": {},
        "totales_verificados": {"activo": 74650.00, "pasivo": 22800.00, "gastos": 4000.00,
                                "ingresos": 14000.00, "capital": 41850.00,
                                "comprobacion": "22.800 + 41.850 + 14.000 − 4.000 = 74.650"},
        "solucion": [],
        "correcciones": [],
        "etiquetas": [
            "solución calculada, no publicada por el libro",
        ],
        "advertencias": [
            "La fuente NO trae solución: se carga como enunciado de práctica sin solución visible (§62.5).",
            "La cifra de capital (41.850,00) es cálculo del simulador: se muestra solo como verificación "
            "referencial y no como respuesta oficial de una actividad evaluable.",
        ],
        "contexto_normativo": "Ecuador — ejercicio propuesto del libro U2 (2025)",
    },

    # -------------------------------------------------------------------------------- 61.12
    {
        "codigo": "C61.12",
        "nombre": "TechnoBoy: identificación de cuentas y ecuación contable",
        "unidad": 2,
        "tipo": "ECUACION_CONTABLE",
        "dificultad": "BASICO",
        "fuente": "U2",
        "paginas_impresas": "121–122",
        "anio": 2023,
        "estado_validacion": "SIN_SOLUCION",
        "solucion_en_fuente": False,
        "solucion_visible": False,
        "tipo_verificacion": "MECANICA",
        "intentos_maximos": 2,
        "puntaje": 10,
        "enunciado": (
            "La empresa inicia el 01/03/2023 con aporte de 40.000,00 en efectivo; abre cuenta corriente en el "
            "Banco del Austro depositando 38.000,00; paga arriendo en efectivo; adquiere computadora y "
            "maquinaria; factura servicios de mantenimiento. Se pide identificar cuentas, representar la "
            "ecuación contable y analizar variaciones. El enunciado continúa el 14/03."),
        "datos": [
            "Aporte 40.000,00 · depósito 38.000,00 · arriendo 450,00 en efectivo.",
            "Computadora HP 2.500,00 (2.000,00 con cheque y 500,00 a 15 días).",
            "Maquinaria al proveedor «Entre Microchips» con cheque: osciloscopio 1.120,00 + cables 100,00 + "
            "multímetro 720,00 + fuente 400,00 + estación de soldado 1.000,00 + pinzas 380,00 + "
            "destornilladores 350,00 + aspiradora 500,00 = 4.570,00 (suma calculada).",
            "Mantenimiento 3.800,00 cobrado 80 % en efectivo (3.040,00) y saldo a 30 días (760,00) "
            "(cálculo).",
        ],
        "asientos_esperados": [],
        "saldos_finales": {},
        "totales_verificados": {"maquinaria_calculada": 4570.00, "mantenimiento_cobrado": 3040.00,
                                "mantenimiento_a_credito": 760.00},
        "solucion": [],
        "correcciones": [],
        "etiquetas": [
            "solución calculada, no publicada por el libro",
        ],
        "advertencias": [
            "Sin solución impresa: el simulador NO debe mostrar solución; la corrección es del docente o por "
            "reglas mecánicas verificables (§62.5).",
        ],
        "contexto_normativo": "Ecuador — ejercicio propuesto del libro U2 (2023)",
    },

    # -------------------------------------------------------------------------------- 61.13
    {
        "codigo": "C61.13",
        "nombre": "Clean Solutions: identificación de cuenta y lado (Debe/Haber)",
        "unidad": 2,
        "tipo": "IDENTIFICACION_CUENTAS",
        "dificultad": "BASICO",
        "fuente": "U2",
        "paginas_impresas": "123–124",
        "anio": 2025,
        "estado_validacion": "SIN_SOLUCION",
        "solucion_en_fuente": False,
        "solucion_visible": False,
        "tipo_verificacion": "MECANICA",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Once hechos económicos donde el estudiante debe marcar en qué cuenta y en qué lado (Debe/Haber) "
            "se registra cada uno. Es la matriz ideal para el módulo de identificación de cuentas."),
        "datos": [
            "Apertura de cuenta bancaria 25.000,00.",
            "Compra de materiales 2.000,00 (50 % con cheque, resto a 30 días).",
            "Préstamo bancario 20.000,00.",
            "Venta de servicio al cliente Ramones 1.800,00 a crédito.",
            "Pago de arriendo 500,00 con cheque.",
        ],
        "asientos_esperados": [],
        "saldos_finales": {},
        "totales_verificados": {},
        "solucion": [],
        "correcciones": [],
        "etiquetas": [],
        "advertencias": [
            "Sin solución en la fuente: la corrección debe ser del docente o por reglas mecánicas "
            "verificables (cuentas válidas y posición Debe/Haber, §62.5).",
        ],
        "contexto_normativo": "Ecuador — ejercicio propuesto del libro U2 (2025)",
    },

    # -------------------------------------------------------------------------------- 61.14
    {
        "codigo": "C61.14",
        "nombre": "Ejercicios N°6, N°7, N°8 y N°10 de U2 (cuentas, movimientos y estado financiero)",
        "unidad": 2,
        "tipo": "CLASIFICACION_Y_MOVIMIENTOS",
        "dificultad": "INTERMEDIO",
        "fuente": "U2",
        "paginas_impresas": "124–129",
        "anio": 2025,
        "estado_validacion": "SIN_SOLUCION",
        "solucion_en_fuente": False,
        "solucion_visible": False,
        "tipo_verificacion": "MECANICA",
        "intentos_maximos": 2,
        "puntaje": 12,
        "enunciado": (
            "Cuatro ejercicios propuestos: N°6 (30 actividades para nombrar la cuenta y clasificarla por "
            "saldo, por grupo y por estado financiero), N°7 (clasificar cuentas en activo corriente, "
            "propiedad planta y equipo y su subgrupo), N°8 (calcular movimientos deudor y acreedor y el tipo "
            "de saldo resultante) y N°10 (a partir de una política contable: balance de comprobación "
            "ordenado, estado de resultados, asientos de cierre, mayorización y estado de situación "
            "financiera)."),
        "datos": [
            "N°6: 30 actividades para nombrar la cuenta y clasificarla.",
            "N°7: clasificación en activo corriente, propiedad planta y equipo y subgrupos.",
            "N°8: cálculo de movimientos y tipo de saldo.",
            "N°10: balance de comprobación ordenado, estado de resultados, asientos de cierre, mayorización "
            "y estado de situación financiera.",
        ],
        "asientos_esperados": [],
        "saldos_finales": {},
        "totales_verificados": {},
        "solucion": [],
        "correcciones": [],
        "etiquetas": [],
        "advertencias": [
            "Los cuatro ejercicios carecen de solución impresa: N°6 y N°7 son evaluables con reglas "
            "mecánicas; N°10 exige revisión docente (§62.5).",
        ],
        "contexto_normativo": "Ecuador — ejercicios propuestos del libro U2 (2025)",
    },

    # -------------------------------------------------------------------------------- 61.15
    {
        "codigo": "C61.15",
        "nombre": "Servicios Unidos Cía. Ltda.: estados financieros básicos con ajustes",
        "unidad": 4,
        "tipo": "ESTADOS_FINANCIEROS",
        "dificultad": "AVANZADO",
        "fuente": "U4",
        "paginas_impresas": "124–127",
        "anio": 2024,
        "estado_validacion": "SIN_SOLUCION",
        "solucion_en_fuente": False,
        "solucion_visible": False,
        "tipo_verificacion": "MECANICA",
        "intentos_maximos": 2,
        "puntaje": 15,
        "enunciado": (
            "La compañía inicia actividades el 1 de enero de 20XX; se pide realizar los estados financieros "
            "básicos a partir de la situación inicial y ocho transacciones de enero, aplicando además tres "
            "ajustes (consumo del 60 % de los suministros de oficina, depreciación por el método legal y "
            "registro de valores devengados en pagos anticipados)."),
        "datos": [
            "Situación inicial: Efectivo 10.000,00 · Banco De Guayaquil 22.000,00 · Suministros de oficina "
            "300,00 · Maquinaria y equipo 24.000,00 · Muebles y enseres 15.000,00 · Cuentas por pagar "
            "5.000,00 · Préstamo bancario 12.000,00.",
            "ene 07 deposita el 80 % del efectivo · ene 09 servicios 400,00 + IVA en efectivo (fact. 006) · "
            "ene 12 publicidad 500,00 + IVA con cheque (fact. 0345) · ene 13 servicios 350,00 + IVA con "
            "cheque (fact. 009) · ene 16 suministros 100,00 + IVA en efectivo (fact. 00890) · ene 18 "
            "servicios 700,00 + IVA a crédito al Sr. Pedro Alvarado (fact. 00546) · ene 20 arriendo de enero "
            "y febrero, 200,00 + IVA mensuales (fact. 00234) · ene 23 pago del 30 % de la deuda con "
            "proveedores.",
            "Cálculo derivado (no impreso) de la situación inicial: Activo 71.300,00 · Pasivo 17.000,00 · "
            "Patrimonio 54.300,00 (A = P + Pat).",
            "Con IVA 15 %: ene 09 = 460,00; ene 12 = 575,00; ene 13 = 402,50; ene 16 = 115,00; ene 18 = "
            "805,00; ene 20 = 460,00 por los dos meses; ene 23 = 1.500,00.",
        ],
        "asientos_esperados": [],
        "saldos_finales": {
            "debitos": {"Efectivo": 10000.00, "Banco De Guayaquil": 22000.00, "Suministros de oficina": 300.00,
                        "Maquinaria y equipo": 24000.00, "Muebles y enseres": 15000.00},
            "creditos": {"Cuentas por pagar": 5000.00, "Préstamo bancario": 12000.00,
                         "Patrimonio": 54300.00},
        },
        "totales_verificados": {"activo_inicial": 71300.00, "pasivo_inicial": 17000.00,
                                "patrimonio_inicial": 54300.00,
                                "iva_ene09": 460.00, "iva_ene12": 575.00, "iva_ene13": 402.50,
                                "iva_ene16": 115.00, "iva_ene18": 805.00, "iva_ene20": 460.00,
                                "pago_proveedores_ene23": 1500.00},
        "solucion": [],
        "correcciones": [],
        "etiquetas": [
            "dato reconstruido — pendiente de validación con el facsímil",
            "solución calculada, no publicada por el libro",
        ],
        "advertencias": [
            "La solución del caso aparece en páginas de imagen y no está disponible en el texto: se cargan "
            "solo la situación inicial y las transacciones, marcadas como «sin solución validada» (§62.4 y §62.5).",
            "Los importes de IVA y de la situación inicial son cálculos derivados del simulador, no cifras "
            "impresas.",
        ],
        "contexto_normativo": "Ecuador — caso práctico del libro U4 (2024); IVA 15 % demostrativo",
    },

    # -------------------------------------------------------------------------------- 61.16
    {
        "codigo": "C61.16",
        "nombre": "Guápulo Cía. Ltda.: ventas al contado y a crédito con costo de ventas",
        "unidad": 4,
        "tipo": "VENTAS_CON_COSTO",
        "dificultad": "INTERMEDIO",
        "fuente": "U4",
        "paginas_impresas": "92–93",
        "anio": 2024,
        "estado_validacion": "CON_ERRATA",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Venta de mercaderías al contado el 2 de junio por 2.200,00 más IVA (costo 1.200,00), y venta el "
            "25 de junio por 4.000,00 más IVA con entrega en quince días (costo 2.600,00); se registran "
            "también los dos asientos de costo de ventas."),
        "datos": [
            "2-jun: venta al contado 2.200,00 + IVA 330,00 = 2.530,00; costo 1.200,00.",
            "25-jun: venta 4.000,00 + IVA 600,00 = 4.600,00 de efectivo real; costo 2.600,00.",
        ],
        "asientos_esperados": [
            {"fecha": "02-jun-2024", "glosa": "Venta de mercaderías al contado",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 2530.00, "haber": 0.0},
                        {"codigo": "41101", "cuenta": "Venta de mercaderías", "debe": 0.0, "haber": 2200.00},
                        {"codigo": "21301", "cuenta": "IVA cobrado (IVA ventas)", "debe": 0.0, "haber": 330.00}]},
            {"fecha": "02-jun-2024", "glosa": "Costo de ventas del 2 de junio",
             "lineas": [{"codigo": "51301", "cuenta": "Costo de ventas", "debe": 1200.00, "haber": 0.0},
                        {"codigo": "11402", "cuenta": "Inv. de mercadería en almacén comprada a terceros",
                         "debe": 0.0, "haber": 1200.00}]},
            {"fecha": "25-jun-2024", "glosa": "Venta del 25 de junio (valor de efectivo corregido)",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 4600.00, "haber": 0.0},
                        {"codigo": "41101", "cuenta": "Venta de mercaderías", "debe": 0.0, "haber": 4000.00},
                        {"codigo": "21301", "cuenta": "IVA cobrado (IVA ventas)", "debe": 0.0, "haber": 600.00}]},
            {"fecha": "25-jun-2024", "glosa": "Costo de ventas del 25 de junio",
             "lineas": [{"codigo": "51301", "cuenta": "Costo de ventas", "debe": 2600.00, "haber": 0.0},
                        {"codigo": "11402", "cuenta": "Inv. de mercadería en almacén comprada a terceros",
                         "debe": 0.0, "haber": 2600.00}]},
        ],
        "saldos_finales": {},
        "totales_verificados": {"venta_2_jun": 2530.00, "venta_25_jun_corregida": 4600.00},
        "solucion": [
            "Los asientos del 2 de junio sí cuadran (2.530,00 = 2.200,00 + 330,00) y se usan tal como están.",
            "El asiento del 25 de junio se carga con el valor corregido: Caja 4.600,00 (4.000,00 + IVA de 600,00).",
        ],
        "correcciones": [
            {"campo": "valor de Caja del asiento del 25-jun",
             "valor_libro": "Caja 4.000,00 (Debe) frente a un Haber de 4.600,00 — descuadrado",
             "valor_corregido": "Caja 4.600,00",
             "razon": "el Debe no cuadraba con el Haber (4.000,00 vs. 4.600,00); el efectivo real es "
                      "4.000,00 + 15 % de IVA = 4.600,00."},
        ],
        "etiquetas": [],
        "advertencias": [
            "La versión del libro NO se publica: solo se publica el caso con el valor corregido y la "
            "corrección registrada en la ficha (§62.1).",
        ],
        "contexto_normativo": "Ecuador — caso práctico del libro U4 (2024); IVA 15 % demostrativo",
    },

    # -------------------------------------------------------------------------------- 61.17
    {
        "codigo": "C61.17",
        "nombre": "Servindustria Cía. Ltda.: ingresos diferidos con reconocimiento mensual",
        "unidad": 4,
        "tipo": "INGRESOS_DIFERIDOS",
        "dificultad": "INTERMEDIO",
        "fuente": "U4",
        "paginas_impresas": "96–97",
        "anio": 2024,
        "estado_validacion": "CON_ERRATA",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ASIENTO",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Contrato anual de mantenimiento industrial por 7.200,00 más IVA, cobrado por transferencia "
            "bancaria; se reconoce el ingreso mes a mes."),
        "datos": [
            "Contrato: 7.200,00 + IVA 1.080,00 = 8.280,00 cobrados por transferencia bancaria.",
            "Reconocimiento mensual correcto: 7.200,00 ÷ 12 meses = 600,00.",
        ],
        "asientos_esperados": [
            {"fecha": "2024", "glosa": "Cobro anticipado del contrato anual",
             "lineas": [{"codigo": "11103", "cuenta": "Bancos", "debe": 8280.00, "haber": 0.0},
                        {"codigo": "", "cuenta": "Ingresos diferidos", "debe": 0.0, "haber": 7200.00},
                        {"codigo": "21301", "cuenta": "IVA cobrado (IVA ventas)", "debe": 0.0, "haber": 1080.00}]},
            {"fecha": "mes", "glosa": "Reconocimiento mensual del ingreso (contrato ÷ número de meses)",
             "lineas": [{"codigo": "", "cuenta": "Ingresos diferidos", "debe": 600.00, "haber": 0.0},
                        {"codigo": "41201", "cuenta": "Ingresos por servicios", "debe": 0.0, "haber": 600.00}]},
        ],
        "saldos_finales": {},
        "totales_verificados": {"contrato": 7200.00, "iva": 1080.00, "cobro": 8280.00,
                                "reconocimiento_mensual_correcto": 600.00},
        "parametros_caso": {"importe_contrato": 7200.00, "meses": 12,
                            "formula_reconocimiento": "importe del contrato ÷ número de meses"},
        "solucion": [
            "Asiento inicial (cuadra): Bancos 8.280,00 // Ingresos diferidos 7.200,00 / IVA ventas 1.080,00.",
            "Reconocimiento mensual: 7.200,00 ÷ 12 = 600,00 (la fuente usa 500,00 por errata).",
        ],
        "correcciones": [
            {"campo": "reconocimiento mensual del ingreso diferido",
             "valor_libro": "500,00",
             "valor_corregido": "600,00",
             "razon": "el contrato de 7.200,00 ÷ 12 meses = 600,00; el sistema calcula el valor como "
                      "«importe del contrato ÷ número de meses» y no replica el 500,00."},
        ],
        "etiquetas": [],
        "advertencias": [
            "El sistema implementa el reconocimiento mensual como parámetro (`importe ÷ meses`) en lugar de "
            "replicar la cifra de la fuente (§62.1).",
        ],
        "contexto_normativo": "Ecuador — caso práctico del libro U4 (2024); IVA 15 % demostrativo",
    },

    # -------------------------------------------------------------------------------- 61.18
    {
        "codigo": "C61.18",
        "nombre": "Ejercicio N°1 y Ejercicio N°4 de ecuación contable",
        "unidad": 2,
        "tipo": "ECUACION_CONTABLE",
        "dificultad": "BASICO",
        "fuente": "U2",
        "paginas_impresas": "120–123",
        "anio": 2025,
        "estado_validacion": "PARCIAL_CON_ERRATA",
        "solucion_en_fuente": True,
        "solucion_visible": True,
        "tipo_verificacion": "ECUACION",
        "intentos_maximos": 3,
        "puntaje": 10,
        "enunciado": (
            "Ejercicio N°1: completar el valor faltante en cada fila aplicando Activo = Pasivo + Patrimonio. "
            "Ejercicio N°4: analizar los efectos de cinco hechos en la ecuación contable (apertura con aporte, "
            "apertura de cuenta corriente, arriendo del mes, compra de computadora y asesoramiento cobrado)."),
        "datos": [
            "Ejercicio N°1 — filas verificadas: 280.000,00 = 170.000,00 + 110.000,00; 340.000,00 = 135.000,00 "
            "+ 205.000,00; 565.000,00 = 288.000,00 + 277.000,00; 824.000,00 = 304.000,00 + 520.000,00.",
            "Ejercicio N°4: (a) el Sr. Pérez inicia asesoría contable aportando 18.000,00 en efectivo; "
            "(b) apertura de cuenta corriente depositando 17.500,00; (c) arriendo del mes 400,00; "
            "(d) computadora por 2.000,00 (cheque 1.000,00 y diferencia a 30 días); (e) asesoramiento a "
            "clientes por 900,00 en efectivo. Solo la fila (a) trae solución en la fuente.",
        ],
        "asientos_esperados": [
            {"subcaso": "Ejercicio N°4 fila (a)", "glosa": "Aporte inicial del Sr. Pérez",
             "lineas": [{"codigo": "11101", "cuenta": "Caja", "debe": 18000.00, "haber": 0.0},
                        {"codigo": "31101", "cuenta": "Capital", "debe": 0.0, "haber": 18000.00}]},
        ],
        "saldos_finales": {},
        "totales_verificados": {"fila_1": 110000.00, "fila_2": 340000.00, "fila_3": 277000.00,
                                "fila_4": 304000.00, "efecto_aporte_a": 18000.00},
        "solucion": [
            "Ejercicio N°1: las cuatro filas verificadas cuadran con Activo = Pasivo + Patrimonio.",
            "Ejercicio N°4 fila (a) resuelta en la fuente: Caja +18.000,00 / Capital +18.000,00.",
        ],
        "correcciones": [
            {"campo": "quinta fila del Ejercicio N°1",
             "valor_libro": "650.000,00 = 800.000,00 + …",
             "valor_corregido": "fila excluida",
             "razon": "implicaría un patrimonio negativo de −150.000,00 y es inconsistente; no debe cargarse "
                      "hasta verificarla contra el PDF (§59.10 errata 8)."},
        ],
        "etiquetas": [],
        "advertencias": [
            "La quinta fila del Ejercicio N°1 NO se carga (§59.10 errata 8 y §61.18).",
            "De las cinco filas del Ejercicio N°4 solo la (a) trae solución: las demás se resuelven con "
            "reglas mecánicas o revisión docente (§62.5).",
        ],
        "contexto_normativo": "Ecuador — ejercicios propuestos del libro U2 (2025)",
        "filas_excluidas": ["650.000,00 = 800.000,00 + … (patrimonio negativo inconsistente)"],
    },

    # -------------------------------------------------------------------------------- 61.19
    {
        "codigo": "C61.19",
        "nombre": "Préstamo bancario con contribución del 0,5 %",
        "unidad": 4,
        "tipo": "PRESTAMO_BANCARIO",
        "dificultad": "AVANZADO",
        "fuente": "U4",
        "paginas_impresas": "82–83",
        "anio": 2024,
        "estado_validacion": "SIN_SOLUCION",
        "solucion_en_fuente": False,
        "solucion_visible": False,
        "tipo_verificacion": "MECANICA",
        "intentos_maximos": 2,
        "puntaje": 10,
        "enunciado": (
            "Préstamo bancario con interés anual del 15 %, plazo de 5 años y pagos semestrales; el banco "
            "retiene el 0,5 % por contribución; la primera cuota es de 2.913,72. Se documenta el enunciado."),
        "datos": [
            "Tasa de interés anual 15 % · plazo 5 años · pagos semestrales.",
            "Retención del banco por contribución: 0,5 %.",
            "Primera cuota: 2.913,72.",
        ],
        "asientos_esperados": [],
        "saldos_finales": {},
        "totales_verificados": {},
        "solucion": [],
        "correcciones": [],
        "etiquetas": [],
        "advertencias": [
            "No hay tabla de amortización ni asientos resueltos en la fuente: NO debe presentarse como caso "
            "resuelto (§62.5). La tasa del 15 % es un dato demostrativo del ejercicio (§62.2).",
        ],
        "contexto_normativo": "Ecuador — ejercicio del libro U4 (2024); tasa demostrativa",
    },
]


def caso(codigo):
    """Devuelve un caso por su código (C61.01 … C61.19) o None."""
    buscado = (codigo or "").strip().upper()
    for item in CASOS:
        if item["codigo"].upper() == buscado:
            return item
    return None


def casos_cargables():
    """Los casos activables en el simulador (§62.9: todos traen ficha completa)."""
    return [c for c in CASOS if not c.get("bloqueado")]


def casos_por_estado(estado):
    """Casos de un estado de validación (§61)."""
    return [c for c in CASOS if c["estado_validacion"] == estado]
