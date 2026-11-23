"""Asiento de apertura del simulador: guía para la docente y hoja de trabajo del estudiante.

El aula de cada estudiante arranca con la mercadería cargada (20 productos al costo) y sin ningún
asiento. El primer registro que hacen es el aporte inicial de los socios: inventario + efectivo
contra capital. El valor del inventario es distinto en cada empresa, así que los documentos
enseñan a usar el valor propio (el que muestra el aviso del dashboard), no una cifra única.

    python gen/asiento_apertura.py
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CARRERA = "Universidad Técnica de Manabí · Carrera de Contabilidad y Auditoría"
ASIGNATURA = "Contabilidad I (AUD ONLINE) · Periodo 2026-P2"
DOCENTE = "Ing. Angélica Victoria Guillén Pinargote, Mg."
EFECTIVO = 5000.00
EJEMPLO_INVENTARIO = 7500.00


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


def _formato(valor):
    return ("{:,.2f}".format(valor)).replace(",", "X").replace(".", ",").replace("X", ".")


def escribir_guia(destino):
    """Guía para la docente: qué explicar, el orden de los pasos y qué revisar."""
    documento = _preparar()
    _encabezado(documento, "Asiento de apertura: guía para acompañar el primer registro",
                "Aporte inicial de los socios en el Simulador Integral de Sistema Contable")

    _parrafo(documento,
             "Cada empresa del curso nace con la mercadería cargada en bodega y sin ninguna "
             "operación registrada. El primer asiento que hace el estudiante es el aporte inicial "
             "de los socios: la mercadería y el efectivo que aportan forman el capital de la "
             "empresa. Las tres cuentas ya existen en su plan de cuentas.", 10.5)

    _parrafo(documento, "1. Qué debe explicar antes de que registren", 11.5, negrita=True, espacio=3)
    for texto in (
        "El inventario ya está en bodega, pero todavía no está en los libros: por eso se registra.",
        "La mercadería entra por su costo (sin IVA), porque es una compra de inventario, no un gasto.",
        "El efectivo que aportan los socios entra a Caja General.",
        "El capital es la suma de las dos cosas: es lo que los socios pusieron en la empresa.",
        "El Debe y el Haber deben dar exactamente lo mismo.",
    ):
        _parrafo(documento, "• " + texto, 10, sangria=0.5, espacio=3)

    _parrafo(documento, "2. La estructura del asiento", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "El valor del inventario es distinto en cada empresa: cada estudiante debe tomar el "
             "que aparece en su propio aviso del dashboard, en «Catálogo de Productos» o en la "
             "pantalla de Inventario. El efectivo es el mismo para todo el curso: USD %s." % _formato(EFECTIVO), 10)
    _tabla_asiento(documento,
                   [("1.1.06", "Inventario de Mercaderías", "su valor de inventario", ""),
                    ("1.1.01", "Caja General", _formato(EFECTIVO), ""),
                    ("3.1.01", "Capital Social Suscrito y Pagado", "",
                     "inventario + " + _formato(EFECTIVO))],
                   "suma de los dos", "suma de los dos")

    _parrafo(documento, "3. Ejemplo con cifras redondas", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "Si el inventario de esa empresa fuera de USD %s y el efectivo de USD %s, el asiento "
             "quedaría así:" % (_formato(EJEMPLO_INVENTARIO), _formato(EFECTIVO)), 10)
    _tabla_asiento(documento,
                   [("1.1.06", "Inventario de Mercaderías", _formato(EJEMPLO_INVENTARIO), ""),
                    ("1.1.01", "Caja General", _formato(EFECTIVO), ""),
                    ("3.1.01", "Capital Social Suscrito y Pagado", "",
                     _formato(EJEMPLO_INVENTARIO + EFECTIVO))],
                   _formato(EJEMPLO_INVENTARIO + EFECTIVO),
                   _formato(EJEMPLO_INVENTARIO + EFECTIVO))

    _parrafo(documento, "4. Los pasos en el simulador", 11.5, negrita=True, espacio=3)
    for numero, texto in enumerate((
        "Entrar con el correo institucional y abrir el Dashboard: aparece el aviso amarillo con su "
        "valor de inventario.",
        "Pulsar «Registrar el aporte inicial en el Libro Diario».",
        "Escribir la fecha (dentro del período: 21/09/2026 al 16/01/2027) y la glosa: «Aporte "
        "inicial de los socios».",
        "Cargar las tres líneas: 1.1.06 con el inventario en el Debe; 1.1.01 con %s en el " % _formato(EFECTIVO) +
        "Debe; 3.1.01 con la suma en el Haber.",
        "Verificar que el aviso de la parte superior se ponga verde («Asiento Cuadrado») y pulsar "
        "«Contabilizar Asiento».",
        "Volver al Dashboard: el aviso amarillo desaparece y el capital aparece en el patrimonio.",
    ), start=1):
        _parrafo(documento, "%d. %s" % (numero, texto), 10, sangria=0.5, espacio=3)

    _parrafo(documento, "5. Qué revisar después", 11.5, negrita=True, espacio=3)
    for texto in (
        "En el Libro Diario: un asiento con tres líneas y el Debe igual al Haber.",
        "En el Balance de Comprobación: Caja %s; Inventario por el valor de su empresa; " % _formato(EFECTIVO) +
        "Capital por la suma, en el saldo acreedor. Las dos tarjetas de control en verde.",
        "En el Estado de Situación Financiera: el capital en el patrimonio y el inventario en el "
        "activo corriente.",
    ):
        _parrafo(documento, "• " + texto, 10, sangria=0.5, espacio=3)

    _parrafo(documento, "6. Errores frecuentes", 11.5, negrita=True, espacio=3)
    for texto in (
        "Registrar el capital sin el inventario (el asiento queda descuadrado).",
        "Poner el inventario con IVA: aquí no hay IVA, es el aporte de los socios.",
        "Cargar el inventario en el Haber y el capital en el Debe (se invierte la partida).",
        "Usar el valor de otro compañero: cada empresa tiene su propio inventario.",
        "Elegir una cuenta agrupadora (1.1 o 1) en lugar de las de detalle.",
    ):
        _parrafo(documento, "• " + texto, 10, sangria=0.5, espacio=3)

    documento.save(destino)
    return destino


def escribir_hoja(destino):
    """Hoja de trabajo del estudiante: lee su valor y arma el asiento."""
    documento = _preparar()
    _encabezado(documento, "Hoja de trabajo: asiento de apertura",
                "Aporte inicial de los socios · primer registro en el simulador")

    _parrafo(documento, "Nombre: ______________________________________   "
                        "Paralelo: ______   Fecha: ______________", 10.5, espacio=12)

    _parrafo(documento, "Paso 1. Busca tus datos", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "En tu Dashboard, el aviso amarillo dice cuánto vale tu mercadería. Ese valor es el "
             "de tu empresa; no lo cambies por el de un compañero.", 10)

    _parrafo(documento, "Paso 2. Completa el cuadro de análisis", 11.5, negrita=True, espacio=3)
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    cuadro = documento.add_table(rows=3, cols=3)
    cuadro.alignment = WD_TABLE_ALIGNMENT.CENTER
    cuadro.style = "Table Grid"
    preguntas = [("¿Qué se recibe?", "¿Cuáles son las cuentas deudoras que intervienen?",
                  "¿Por cuánto recibe?"),
                 ("¿Qué se entrega?", "¿Cuáles son las cuentas acreedoras que intervienen?",
                  "¿Por cuánto entrega?")]
    encabezados = ["Primera pregunta", "Segunda pregunta", "Tercer pregunta"]
    for indice, texto in enumerate(encabezados):
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
            p.paragraph_format.space_after = Pt(10)
            corrida = p.add_run(texto + "\n")
            corrida.bold = True
            corrida.font.size = Pt(8.5)
            corrida.font.name = "Times New Roman"
            corrida2 = p.add_run(" " * 3)
            corrida2.font.size = Pt(9.5)
    for fila in cuadro.rows:
        for indice, celda in enumerate(fila.cells):
            celda.width = [Cm(4.6), Cm(7.6), Cm(4.2)][indice]

    _parrafo(documento, "Paso 3. Registra el asiento en el Libro Diario", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "Con los datos de tu empresa, completa tu asiento (recuerda: Debe = Haber):", 10)
    _tabla_asiento(documento,
                   [("1.1.06", "Inventario de Mercaderías", "", ""),
                    ("1.1.01", "Caja General", "", ""),
                    ("3.1.01", "Capital Social Suscrito y Pagado", "", "")],
                   "", "")

    _parrafo(documento, "Paso 4. Comprueba", 11.5, negrita=True, espacio=3)
    for texto in (
        "El aviso del formulario se puso verde (asiento cuadrado) y pudiste contabilizar.",
        "El aviso amarillo del Dashboard desapareció.",
        "En el Balance de Comprobación las dos tarjetas están en verde.",
    ):
        _parrafo(documento, "☐  " + texto, 10, sangria=0.5, espacio=4)

    documento.save(destino)
    return destino


def escribir_solucionario(destino):
    """Ejemplo resuelto del asiento de apertura, con las cifras del ejemplo."""
    documento = _preparar()
    _encabezado(documento, "Asiento de apertura: ejemplo resuelto",
                "Modelo para revisar el primer registro de los estudiantes")

    _parrafo(documento,
             "Este ejemplo usa cifras redondas para que sirva de modelo. Cada empresa tiene su "
             "propio valor de inventario, así que el capital de cada estudiante será distinto: "
             "lo único que cambia son dos números (inventario y capital).", 10.5)

    _parrafo(documento, "Aporte inicial de los socios", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "Los socios aportan la mercadería que ya está en bodega (inventario) y USD %s en "
             "efectivo. El total forma el capital de la empresa." % _formato(EFECTIVO), 10)
    _tabla_asiento(documento,
                   [("1.1.06", "Inventario de Mercaderías", _formato(EJEMPLO_INVENTARIO), ""),
                    ("1.1.01", "Caja General", _formato(EFECTIVO), ""),
                    ("3.1.01", "Capital Social Suscrito y Pagado", "",
                     _formato(EJEMPLO_INVENTARIO + EFECTIVO))],
                   _formato(EJEMPLO_INVENTARIO + EFECTIVO),
                   _formato(EJEMPLO_INVENTARIO + EFECTIVO))

    _parrafo(documento, "Cómo se lee", 11.5, negrita=True, espacio=3)
    for texto in (
        "La empresa recibe la mercadería (inventario) y el efectivo: son cuentas deudoras.",
        "Entrega a cambio la participación de los socios: es una cuenta acreedora (capital).",
        "El asiento cuadra porque el Debe (inventario + caja) es igual al Haber (capital).",
    ):
        _parrafo(documento, "• " + texto, 10, sangria=0.5, espacio=3)

    _parrafo(documento, "Qué debe salir en el balance de comprobación", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "Caja %s · Inventario %s · Capital %s, con las sumas y los saldos en verde. En el "
             "Estado de Situación Financiera, el inventario y la caja en el activo corriente, y el "
             "capital en el patrimonio."
             % (_formato(EFECTIVO), _formato(EJEMPLO_INVENTARIO),
                _formato(EJEMPLO_INVENTARIO + EFECTIVO)), 10)

    _parrafo(documento, "Cómo cambia para cada estudiante", 11.5, negrita=True, espacio=3)
    _parrafo(documento,
             "Solo dos cifras: el inventario (el valor que muestra su dashboard) y el capital "
             "(ese mismo valor más %s). La caja siempre es %s y las cuentas son las mismas."
             % (_formato(EFECTIVO), _formato(EFECTIVO)), 10)

    documento.save(destino)
    return destino


def main():
    analizador = argparse.ArgumentParser(description="Asiento de apertura: guía y hoja de trabajo.")
    analizador.add_argument("--salida", default=os.path.join(
        os.path.expanduser("~"), "Desktop", "2026", "S2", "Clases", "Contabilidad 1"))
    argumentos = analizador.parse_args()

    os.makedirs(argumentos.salida, exist_ok=True)
    ruta_guia = os.path.join(argumentos.salida, "Asiento_de_apertura_guia.docx")
    ruta_hoja = os.path.join(argumentos.salida, "Asiento_de_apertura_hoja_de_trabajo.docx")
    ruta_solucion = os.path.join(argumentos.salida, "Asiento_de_apertura_ejemplo_resuelto.docx")
    for nombre, funcion, ruta in (("Guía de la docente", escribir_guia, ruta_guia),
                                  ("Hoja de trabajo", escribir_hoja, ruta_hoja),
                                  ("Ejemplo resuelto", escribir_solucionario, ruta_solucion)):
        try:
            funcion(ruta)
            print("%-22s %s" % (nombre + ":", ruta))
        except PermissionError:
            print("%-22s [ABIERTO EN WORD] %s" % (nombre + ":", ruta))
    print("Efectivo de referencia: USD %s" % _formato(EFECTIVO))


if __name__ == "__main__":
    main()
