"""Asiento de apertura completo del simulador: guía, hoja de trabajo y ejemplo resuelto.

La empresa de cada estudiante se constituye con aportes de los socios (la mercadería que ya está
en bodega, efectivo, muebles, equipo de cómputo y un vehículo) y asume un préstamo. El capital no
se suma: se calcula como activo menos pasivo, de modo que cambia en cada empresa porque el
inventario es distinto.

    python gen/asiento_apertura.py
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CARRERA = "Universidad Técnica de Manabí · Carrera de Contabilidad y Auditoría"
ASIGNATURA = "Contabilidad I (AUD ONLINE) · Periodo 2026-P2"
DOCENTE = "Ing. Angélica Victoria Guillén Pinargote, Mg."

# Valores fijos del ejercicio (los dicta la docente en clase).
EFECTIVO = 5000.00
MUEBLES = 3000.00
EQUIPO = 2500.00
VEHICULO = 15000.00
PRESTAMO = 4000.00
EJEMPLO_INVENTARIO = 7500.00

# El capital es la diferencia: activo menos pasivo.
CAPITAL_SOBRE_INVENTARIO = EFECTIVO + MUEBLES + EQUIPO + VEHICULO - PRESTAMO   # 21.500,00
EJEMPLO_CAPITAL = EJEMPLO_INVENTARIO + CAPITAL_SOBRE_INVENTARIO                 # 29.000,00
EJEMPLO_TOTAL = EJEMPLO_INVENTARIO + EFECTIVO + MUEBLES + EQUIPO + VEHICULO     # 33.000,00


def _preparar():
    from docx import Document
    from docx.shared import Pt
    from docx.oxml.ns import qn

    documento = Document()
    estilo = documento.styles["Normal"]
    estilo.font.name = "Times New Roman"
    estilo.font.size = Pt(11)
    estilo.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    return documento


def _encabezado(documento, titulo, subtitulo):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    def linea(texto, tamano, negrita=False, cursiva=False, espacio=0):
        p = documento.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(espacio)
        corrida = p.add_run(texto)
        corrida.bold = negrita
        corrida.italic = cursiva
        corrida.font.size = Pt(tamano)
        corrida.font.name = "Times New Roman"

    linea("UNIVERSIDAD TÉCNICA DE MANABÍ", 12, negrita=True)
    linea(CARRERA, 9.5)
    linea(ASIGNATURA, 9.5, espacio=10)
    linea(titulo, 14, negrita=True, espacio=2)
    linea(subtitulo, 10, cursiva=True, espacio=8)
    linea("Docente: %s" % DOCENTE, 9.5, cursiva=True, espacio=12)


def _parrafo(documento, texto, tamano=10.5, negrita=False, cursiva=False,
             alineacion="justify", espacio=6, sangria=None):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    p = documento.add_paragraph()
    p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                   "left": WD_ALIGN_PARAGRAPH.LEFT}[alineacion]
    p.paragraph_format.space_after = Pt(espacio)
    if sangria:
        p.paragraph_format.left_indent = Cm(sangria)
    corrida = p.add_run(texto)
    corrida.bold = negrita
    corrida.italic = cursiva
    corrida.font.size = Pt(tamano)
    corrida.font.name = "Times New Roman"
    return p


def _formato(valor):
    return ("{:,.2f}".format(valor)).replace(",", "X").replace(".", ",").replace("X", ".")


def _tabla_asiento(documento, filas, total_debe, total_haber):
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    tabla = documento.add_table(rows=1, cols=4)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.style = "Table Grid"
    for indice, texto in enumerate(["Código", "Cuenta", "Debe", "Haber"]):
        celda = tabla.rows[0].cells[indice]
        celda.text = ""
        p = celda.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        corrida = p.add_run(texto)
        corrida.bold = True
        corrida.font.size = Pt(9)
        corrida.font.name = "Times New Roman"
        corrida.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombreado = OxmlElement("w:shd")
        sombreado.set(qn("w:fill"), "1F3864")
        celda._tc.get_or_add_tcPr().append(sombreado)

    for codigo, cuenta, debe, haber in filas:
        celdas = tabla.add_row().cells
        valores = [codigo, cuenta, debe if debe is not None else "", haber if haber is not None else ""]
        for indice, valor in enumerate(valores):
            celdas[indice].text = ""
            p = celdas[indice].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if indice >= 2 else WD_ALIGN_PARAGRAPH.LEFT
            corrida = p.add_run(valor)
            corrida.font.size = Pt(9.5)
            corrida.font.name = "Times New Roman"

    celdas = tabla.add_row().cells
    for indice, valor in enumerate(["", "Totales", total_debe, total_haber]):
        celdas[indice].text = ""
        p = celdas[indice].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if indice >= 2 else WD_ALIGN_PARAGRAPH.LEFT
        corrida = p.add_run(valor)
        corrida.bold = True
        corrida.font.size = Pt(9.5)
        corrida.font.name = "Times New Roman"

    for fila in tabla.rows:
        for indice, celda in enumerate(fila.cells):
            celda.width = [Cm(1.8), Cm(8.6), Cm(3.1), Cm(3.1)][indice]
    return tabla


def _tabla_datos(documento, filas):
    """Cuadro de los datos del ejercicio: concepto, cuenta y valor."""
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    tabla = documento.add_table(rows=1, cols=3)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.style = "Table Grid"
    for indice, texto in enumerate(["Concepto", "Cuenta", "Valor"]):
        celda = tabla.rows[0].cells[indice]
        celda.text = ""
        p = celda.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        corrida = p.add_run(texto)
        corrida.bold = True
        corrida.font.size = Pt(9)
        corrida.font.name = "Times New Roman"
        corrida.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombreado = OxmlElement("w:shd")
        sombreado.set(qn("w:fill"), "1F3864")
        celda._tc.get_or_add_tcPr().append(sombreado)

    for concepto, cuenta, valor in filas:
        celdas = tabla.add_row().cells
        for indice, texto in enumerate([concepto, cuenta, valor]):
            celdas[indice].text = ""
            p = celdas[indice].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if indice == 2 else WD_ALIGN_PARAGRAPH.LEFT
            corrida = p.add_run(texto)
            corrida.font.size = Pt(9.5)
            corrida.font.name = "Times New Roman"

    for fila in tabla.rows:
        for indice, celda in enumerate(fila.cells):
            celda.width = [Cm(6.4), Cm(3.0), Cm(5.6)][indice]
    return tabla


def escribir_guia(destino):
    """Guía para la docente: qué dictar, cómo se arma y qué revisar."""
    documento = _preparar()
    _encabezado(documento, "Asiento de apertura completo: guía para la clase",
                "Constitución de la empresa: aportes de los socios y un préstamo asumido")

    _parrafo(documento,
             "La empresa se constituye con bienes que aportan los socios (la mercadería que ya está "
             "en bodega, efectivo, muebles, equipo de cómputo y un vehículo) y con un préstamo que "
             "la empresa asume. El asiento de apertura refleja esas tres masas: activo, pasivo y "
             "patrimonio. El capital NO se suma: se calcula como activo menos pasivo.", 10.5)

    _parrafo(documento, "1. Los datos del ejercicio (los dicta la docente)", 11.5, negrita=True,
             espacio=3)
    _tabla_datos(documento, [
        ("Inventario que ya está en bodega", "1.1.06", "el valor de su Dashboard"),
        ("Efectivo aportado por los socios", "1.1.01", _formato(EFECTIVO)),
        ("Muebles y enseres aportados", "1.2.01", _formato(MUEBLES)),
        ("Equipo de cómputo aportado", "1.2.03", _formato(EQUIPO)),
        ("Vehículo de reparto aportado", "1.2.05", _formato(VEHICULO)),
        ("Préstamo que asume la empresa", "2.1.05", _formato(PRESTAMO)),
        ("Capital (activo − pasivo)", "3.1.01", "inventario + " + _formato(CAPITAL_SOBRE_INVENTARIO)),
    ])

    _parrafo(documento, "2. Qué explicar antes de que registren", 11.5, negrita=True, espacio=3)
    for texto in (
        "El inventario ya está en bodega, pero todavía no está en los libros: por eso se registra.",
        "La mercadería y los bienes entran por su costo, sin IVA: son aportes de los socios.",
        "El préstamo es un pasivo: la empresa lo debe, aunque no haya recibido dinero en efectivo.",
        "El capital es la diferencia: lo que vale la empresa (activo) menos lo que debe (pasivo).",
        "Si el capital se calculara sumando solo los activos, el asiento no cuadraría con el pasivo.",
    ):
        _parrafo(documento, "• " + texto, 10, sangria=0.5, espacio=3)

    _parrafo(documento, "3. La estructura del asiento", 11.5, negrita=True, espacio=3)
    _tabla_asiento(documento, [
        ("1.1.06", "Inventario de Mercaderías", "su inventario", ""),
        ("1.1.01", "Caja General", _formato(EFECTIVO), ""),
        ("1.2.01", "Muebles y Enseres de Oficina", _formato(MUEBLES), ""),
        ("1.2.03", "Equipo de Cómputo y Software", _formato(EQUIPO), ""),
        ("1.2.05", "Vehículo de Reparto", _formato(VEHICULO), ""),
        ("2.1.05", "Préstamo Bancario por Pagar CP", "", _formato(PRESTAMO)),
        ("3.1.01", "Capital Social Suscrito y Pagado", "",
         "inventario + " + _formato(CAPITAL_SOBRE_INVENTARIO)),
    ], "inventario + 25.500,00", "inventario + 25.500,00")

    _parrafo(documento, "4. Ejemplo resuelto", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "Con un inventario de USD %s, el asiento queda así (cada estudiante cambia ese valor "
             "y el capital; lo demás es igual):" % _formato(EJEMPLO_INVENTARIO), 10)
    _tabla_asiento(documento, [
        ("1.1.06", "Inventario de Mercaderías", _formato(EJEMPLO_INVENTARIO), ""),
        ("1.1.01", "Caja General", _formato(EFECTIVO), ""),
        ("1.2.01", "Muebles y Enseres de Oficina", _formato(MUEBLES), ""),
        ("1.2.03", "Equipo de Cómputo y Software", _formato(EQUIPO), ""),
        ("1.2.05", "Vehículo de Reparto", _formato(VEHICULO), ""),
        ("2.1.05", "Préstamo Bancario por Pagar CP", "", _formato(PRESTAMO)),
        ("3.1.01", "Capital Social Suscrito y Pagado", "", _formato(EJEMPLO_CAPITAL)),
    ], _formato(EJEMPLO_TOTAL), _formato(EJEMPLO_TOTAL))
    _parrafo(documento,
             "Comprobación: activo %s − pasivo %s = capital %s."
             % (_formato(EJEMPLO_TOTAL), _formato(PRESTAMO), _formato(EJEMPLO_CAPITAL)), 10,
             cursiva=True)

    _parrafo(documento, "5. Los pasos en el simulador", 11.5, negrita=True, espacio=3)
    for numero, texto in enumerate((
        "Abrir el Dashboard: el aviso amarillo muestra el valor de su inventario.",
        "Pulsar «Registrar el aporte inicial en el Libro Diario».",
        "Fecha dentro del período (21/09/2026 al 16/01/2027) y glosa: «Asiento de apertura».",
        "Cargar las cinco líneas del Debe: inventario (su valor), caja, muebles, equipo y vehículo.",
        "Cargar las dos líneas del Haber: préstamo por pagar y capital (inventario + %s)."
        % _formato(CAPITAL_SOBRE_INVENTARIO),
        "Verificar que el aviso se ponga verde («Asiento Cuadrado») y contabilizar.",
    ), start=1):
        _parrafo(documento, "%d. %s" % (numero, texto), 10, sangria=0.5, espacio=3)

    _parrafo(documento, "6. Qué revisar después", 11.5, negrita=True, espacio=3)
    for texto in (
        "Libro Diario: un asiento de siete líneas con el Debe igual al Haber.",
        "Balance de Comprobación: inventario, caja, muebles, equipo y vehículo en el debe; "
        "préstamo y capital en el haber; las dos tarjetas en verde.",
        "Estado de Situación Financiera: activo total = pasivo + patrimonio.",
        "El aviso amarillo del Dashboard desaparece.",
    ):
        _parrafo(documento, "• " + texto, 10, sangria=0.5, espacio=3)

    _parrafo(documento, "7. Errores frecuentes", 11.5, negrita=True, espacio=3)
    for texto in (
        "Calcular el capital sumando solo los activos: se olvidan del préstamo y el asiento no cuadra.",
        "Poner el inventario con IVA: son aportes, no compras.",
        "Registrar el préstamo en el Debe: es un pasivo, va en el Haber.",
        "Poner un saldo en el banco: no hay ningún depósito que lo respalde.",
        "Usar el inventario de otro compañero: cada empresa tiene el suyo.",
        "Elegir cuentas agrupadoras (1.2, 1.1) en lugar de las de detalle.",
    ):
        _parrafo(documento, "• " + texto, 10, sangria=0.5, espacio=3)

    documento.save(destino)
    return destino


def escribir_hoja(destino):
    """Hoja de trabajo del estudiante: sus datos, el cuadro de análisis y el asiento."""
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    documento = _preparar()
    _encabezado(documento, "Hoja de trabajo: asiento de apertura completo",
                "Constitución de la empresa · primer registro en el simulador")

    _parrafo(documento, "Nombre: ______________________________________   "
                        "Paralelo: ______   Fecha: ______________", 10.5, espacio=10)

    _parrafo(documento, "Paso 1. Tus datos", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "El único valor que cambia en tu empresa es el del inventario: lo encuentras en el "
             "aviso de tu Dashboard. Los demás son los que dictó la docente.", 10)
    _tabla_datos(documento, [
        ("Inventario en bodega", "1.1.06", "____________"),
        ("Efectivo de los socios", "1.1.01", _formato(EFECTIVO)),
        ("Muebles y enseres", "1.2.01", _formato(MUEBLES)),
        ("Equipo de cómputo", "1.2.03", _formato(EQUIPO)),
        ("Vehículo de reparto", "1.2.05", _formato(VEHICULO)),
        ("Préstamo asumido", "2.1.05", _formato(PRESTAMO)),
    ])

    _parrafo(documento, "Paso 2. Calcula tu capital", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "Capital = activo − pasivo = (inventario + %s + %s + %s + %s) − %s"
             % (_formato(EFECTIVO), _formato(MUEBLES), _formato(EQUIPO), _formato(VEHICULO),
                _formato(PRESTAMO)), 10)
    _parrafo(documento, "Mi capital es:  ______________________", 11, negrita=True, espacio=8)

    _parrafo(documento, "Paso 3. Completa el cuadro de análisis", 11.5, negrita=True, espacio=3)
    cuadro = documento.add_table(rows=3, cols=3)
    cuadro.alignment = WD_TABLE_ALIGNMENT.CENTER
    cuadro.style = "Table Grid"
    preguntas = [("¿Qué se recibe?", "¿Cuáles son las cuentas deudoras que intervienen?",
                  "¿Por cuánto recibe?"),
                 ("¿Qué se entrega?", "¿Cuáles son las cuentas acreedoras que intervienen?",
                  "¿Por cuánto entrega?")]
    for indice, texto in enumerate(["Primera pregunta", "Segunda pregunta", "Tercer pregunta"]):
        celda = cuadro.rows[0].cells[indice]
        celda.text = ""
        p = celda.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        corrida = p.add_run(texto)
        corrida.bold = True
        corrida.font.size = Pt(9)
        corrida.font.name = "Times New Roman"
    for fila, preguntas_fila in enumerate(preguntas, start=1):
        for indice, texto in enumerate(preguntas_fila):
            celda = cuadro.rows[fila].cells[indice]
            celda.text = ""
            p = celda.paragraphs[0]
            p.paragraph_format.space_after = Pt(14)
            corrida = p.add_run(texto)
            corrida.bold = True
            corrida.font.size = Pt(8.5)
            corrida.font.name = "Times New Roman"
    for fila in cuadro.rows:
        for indice, celda in enumerate(fila.cells):
            celda.width = [Cm(4.6), Cm(7.6), Cm(4.2)][indice]

    _parrafo(documento, "Paso 4. Registra el asiento en el Libro Diario", 11.5, negrita=True,
             espacio=3)
    _tabla_asiento(documento, [
        ("1.1.06", "Inventario de Mercaderías", "", ""),
        ("1.1.01", "Caja General", "", ""),
        ("1.2.01", "Muebles y Enseres de Oficina", "", ""),
        ("1.2.03", "Equipo de Cómputo y Software", "", ""),
        ("1.2.05", "Vehículo de Reparto", "", ""),
        ("2.1.05", "Préstamo Bancario por Pagar CP", "", ""),
        ("3.1.01", "Capital Social Suscrito y Pagado", "", ""),
    ], "", "")

    _parrafo(documento, "Paso 5. Comprueba", 11.5, negrita=True, espacio=3)
    for texto in (
        "El aviso del formulario se puso verde y pudiste contabilizar.",
        "El aviso amarillo del Dashboard desapareció.",
        "En el Balance de Comprobación las dos tarjetas están en verde.",
        "El activo total es igual al pasivo más el patrimonio.",
    ):
        _parrafo(documento, "☐  " + texto, 10, sangria=0.5, espacio=4)

    documento.save(destino)
    return destino


def escribir_solucionario(destino):
    """Ejemplo resuelto con un inventario de 7.500,00."""
    documento = _preparar()
    _encabezado(documento, "Asiento de apertura completo: ejemplo resuelto",
                "Modelo para revisar el primer registro de los estudiantes")

    _parrafo(documento,
             "Los socios aportan la mercadería que ya está en bodega, %s en efectivo, muebles por "
             "%s, equipo de cómputo por %s y un vehículo por %s; la empresa asume un préstamo de "
             "%s. El ejemplo usa un inventario de %s; cada empresa tiene el suyo."
             % (_formato(EFECTIVO), _formato(MUEBLES), _formato(EQUIPO), _formato(VEHICULO),
                _formato(PRESTAMO), _formato(EJEMPLO_INVENTARIO)), 10.5)

    _tabla_asiento(documento, [
        ("1.1.06", "Inventario de Mercaderías", _formato(EJEMPLO_INVENTARIO), ""),
        ("1.1.01", "Caja General", _formato(EFECTIVO), ""),
        ("1.2.01", "Muebles y Enseres de Oficina", _formato(MUEBLES), ""),
        ("1.2.03", "Equipo de Cómputo y Software", _formato(EQUIPO), ""),
        ("1.2.05", "Vehículo de Reparto", _formato(VEHICULO), ""),
        ("2.1.05", "Préstamo Bancario por Pagar CP", "", _formato(PRESTAMO)),
        ("3.1.01", "Capital Social Suscrito y Pagado", "", _formato(EJEMPLO_CAPITAL)),
    ], _formato(EJEMPLO_TOTAL), _formato(EJEMPLO_TOTAL))

    _parrafo(documento, "Cómo se lee", 11.5, negrita=True, espacio=3)
    for texto in (
        "Recibe cinco bienes: mercadería, efectivo, muebles, equipo de cómputo y vehículo "
        "(cuentas deudoras).",
        "Entrega dos compromisos: el préstamo que asume y la participación de los socios en el "
        "capital (cuentas acreedoras).",
        "El capital es la diferencia: %s de activo menos %s de pasivo = %s."
        % (_formato(EJEMPLO_TOTAL), _formato(PRESTAMO), _formato(EJEMPLO_CAPITAL)),
        "La ecuación contable se cumple: activo %s = pasivo %s + patrimonio %s."
        % (_formato(EJEMPLO_TOTAL), _formato(PRESTAMO), _formato(EJEMPLO_CAPITAL)),
    ):
        _parrafo(documento, "• " + texto, 10, sangria=0.5, espacio=3)

    _parrafo(documento, "Qué debe salir en el balance de comprobación", 11.5, negrita=True,
             espacio=3)
    _parrafo(documento,
             "En el debe: inventario %s, caja %s, muebles %s, equipo %s, vehículo %s. En el haber: "
             "préstamo %s y capital %s. Total %s en cada lado, con las dos tarjetas en verde."
             % (_formato(EJEMPLO_INVENTARIO), _formato(EFECTIVO), _formato(MUEBLES),
                _formato(EQUIPO), _formato(VEHICULO), _formato(PRESTAMO), _formato(EJEMPLO_CAPITAL),
                _formato(EJEMPLO_TOTAL)), 10)

    _parrafo(documento, "Cómo cambia para cada estudiante", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "Solo dos cifras: el inventario (el valor de su dashboard) y el capital (ese valor más "
             "%s). Los bienes aportados y el préstamo son iguales para todo el curso, así que los "
             "resultados siguen siendo distintos en cada empresa." % _formato(CAPITAL_SOBRE_INVENTARIO),
             10)

    documento.save(destino)
    return destino


def main():
    analizador = argparse.ArgumentParser(
        description="Asiento de apertura completo: guía, hoja de trabajo y ejemplo resuelto.")
    analizador.add_argument("--salida", default=os.path.join(
        os.path.expanduser("~"), "Desktop", "2026", "S2", "Clases", "Contabilidad 1"))
    argumentos = analizador.parse_args()

    os.makedirs(argumentos.salida, exist_ok=True)
    ruta_guia = os.path.join(argumentos.salida, "Apertura_completa_guia.docx")
    ruta_hoja = os.path.join(argumentos.salida, "Apertura_completa_hoja_de_trabajo.docx")
    ruta_solucion = os.path.join(argumentos.salida, "Apertura_completa_ejemplo_resuelto.docx")
    for nombre, funcion, ruta in (("Guía de la docente", escribir_guia, ruta_guia),
                                  ("Hoja de trabajo", escribir_hoja, ruta_hoja),
                                  ("Ejemplo resuelto", escribir_solucionario, ruta_solucion)):
        try:
            funcion(ruta)
            print("%-22s %s" % (nombre + ":", ruta))
        except PermissionError:
            print("%-22s [ABIERTO EN WORD] %s" % (nombre + ":", ruta))
    print("Datos del ejercicio: caja %s | muebles %s | equipo %s | vehículo %s | préstamo %s"
          % (_formato(EFECTIVO), _formato(MUEBLES), _formato(EQUIPO), _formato(VEHICULO),
             _formato(PRESTAMO)))
    print("Capital = inventario + %s | ejemplo con inventario %s: capital %s, total %s"
          % (_formato(CAPITAL_SOBRE_INVENTARIO), _formato(EJEMPLO_INVENTARIO),
             _formato(EJEMPLO_CAPITAL), _formato(EJEMPLO_TOTAL)))


if __name__ == "__main__":
    main()
