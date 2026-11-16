"""Práctica de jornalización básica para Contabilidad I: 10 transacciones + solucionario.

Las cuentas NO se inventan: se toman del plan de cuentas del simulador y cada asiento se verifica
(las cuentas existen, el asiento cuadra y se puede registrar en el Libro Diario). Se generan dos
documentos: el enunciado para el estudiante y el solucionario para la docente, más un Excel con
las respuestas.

    python gen/practica_transacciones.py
    python gen/practica_transacciones.py --probar     # además registra los 10 asientos en un aula
                                                      # temporal (copia de la plantilla) y muestra
                                                      # los saldos resultantes
"""
import argparse
import os
import shutil
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402
from gen.plan_cuentas_documento import leer_cuentas, ruta_plantilla  # noqa: E402

ASIGNATURA = "Contabilidad I (AUD ONLINE) · Periodo 2026-P2"
CARRERA = "Universidad Técnica de Manabí · Carrera de Contabilidad y Auditoría"
DOCENTE = "Ing. Angélica Victoria Guillén Pinargote, Mg."

# --------------------------------------------------------------------------------- transacciones
# Cada línea: (código de cuenta, debe, haber, referencia)
TRANSACCIONES = [
    {
        "fecha": "01/10/2026",
        "enunciado": "Los socios de Comercial Aula aportan USD 5.000,00 en efectivo para iniciar "
                     "las operaciones de la empresa.",
        "lineas": [("1.1.01", 5000.00, 0, "Aporte de los socios"),
                   ("3.1.01", 0, 5000.00, "Capital suscrito y pagado")],
        "por_que": "Ingresa dinero a la caja (activo) y nace el capital aportado por los socios "
                   "(patrimonio).",
    },
    {
        "fecha": "03/10/2026",
        "enunciado": "Compra 10 unidades de mercadería a USD 20,00 cada una, más IVA del 15 %. "
                     "Cancela el total con transferencia desde el Banco Pichincha.",
        "lineas": [("1.1.06", 200.00, 0, "10 unidades a $20"),
                   ("1.1.07", 30.00, 0, "IVA 15 % de 200"),
                   ("1.1.02", 0, 230.00, "Transferencia")],
        "por_que": "La mercadería entra al inventario, el IVA pagado es crédito tributario y sale "
                   "dinero del banco. La compra queda al costo, sin IVA.",
    },
    {
        "fecha": "05/10/2026",
        "enunciado": "Vende 4 unidades a USD 35,00 cada una, más IVA del 15 %, cobrando en "
                     "efectivo. El costo de esas unidades es de USD 20,00 cada una.",
        "lineas": [("1.1.01", 161.00, 0, "Cobro en efectivo"),
                   ("4.1.01", 0, 140.00, "Ingreso por venta"),
                   ("2.1.02", 0, 21.00, "IVA 15 % de 140"),
                   ("5.1.01", 80.00, 0, "Costo de 4 unidades a $20"),
                   ("1.1.06", 0, 80.00, "Salida del inventario")],
        "por_que": "En inventario perpetuo son dos asientos: el de la venta (caja, ingreso e IVA "
                   "por pagar) y el del costo (gasto contra inventario).",
    },
    {
        "fecha": "07/10/2026",
        "enunciado": "Compra 15 unidades de mercadería a USD 20,00 cada una, más IVA del 15 %, a "
                     "crédito con el proveedor a 30 días.",
        "lineas": [("1.1.06", 300.00, 0, "15 unidades a $20"),
                   ("1.1.07", 45.00, 0, "IVA 15 % de 300"),
                   ("2.1.01", 0, 345.00, "Deuda a 30 días")],
        "por_que": "El inventario y el IVA aumentan; como no se paga, nace una cuenta por pagar.",
    },
    {
        "fecha": "09/10/2026",
        "enunciado": "Vende 10 unidades a USD 35,00 cada una, más IVA del 15 %, a crédito a 30 "
                     "días. El costo es de USD 20,00 por unidad.",
        "lineas": [("1.1.04", 402.50, 0, "Factura a crédito"),
                   ("4.1.01", 0, 350.00, "Ingreso por venta"),
                   ("2.1.02", 0, 52.50, "IVA 15 % de 350"),
                   ("5.1.01", 200.00, 0, "Costo de 10 unidades a $20"),
                   ("1.1.06", 0, 200.00, "Salida del inventario")],
        "por_que": "Cambia la caja por cuentas por cobrar: el ingreso y el IVA son los mismos; la "
                   "salida del inventario va contra el costo.",
    },
    {
        "fecha": "12/10/2026",
        "enunciado": "El cliente anterior paga USD 200,00 mediante transferencia al Banco "
                     "Pichincha, como abono a su deuda.",
        "lineas": [("1.1.02", 200.00, 0, "Transferencia recibida"),
                   ("1.1.04", 0, 200.00, "Abono de cartera")],
        "por_que": "Entra dinero al banco y baja la cuenta por cobrar; el ingreso ya se registró "
                   "en la venta, no se vuelve a registrar.",
    },
    {
        "fecha": "15/10/2026",
        "enunciado": "Paga USD 200,00 al proveedor con un cheque del Banco Pichincha, como abono "
                     "a la deuda de la compra a crédito.",
        "lineas": [("2.1.01", 200.00, 0, "Abono a proveedor"),
                   ("1.1.02", 0, 200.00, "Cheque del Banco Pichincha")],
        "por_que": "Baja la deuda y sale dinero del banco; no es un gasto, porque la compra ya se "
                   "registró al inventario.",
    },
    {
        "fecha": "18/10/2026",
        "enunciado": "Recibe la planilla de energía eléctrica por USD 120,00 más IVA del 15 %, "
                     "que paga por transferencia desde el Banco Pichincha.",
        "lineas": [("6.1.03", 120.00, 0, "Servicio básico del mes"),
                   ("1.1.07", 18.00, 0, "IVA 15 % de 120"),
                   ("1.1.02", 0, 138.00, "Transferencia")],
        "por_que": "Es un gasto del período (no un activo) y su IVA es crédito tributario; se paga "
                   "con dinero del banco.",
    },
    {
        "fecha": "20/10/2026",
        "enunciado": "El Banco Pichincha le acredita un préstamo de USD 2.000,00 en la cuenta "
                     "corriente, a pagar en 12 meses.",
        "lineas": [("1.1.02", 2000.00, 0, "Préstamo acreditado"),
                   ("2.1.05", 0, 2000.00, "Préstamo a corto plazo")],
        "por_que": "Entra dinero al banco y nace una obligación (pasivo). No es ingreso: hay que "
                   "devolverlo.",
    },
    {
        "fecha": "25/10/2026",
        "enunciado": "Compra 2 equipos de cómputo PARA USO ADMINISTRATIVO por USD 1.000,00 más "
                     "IVA del 15 %. Paga el IVA con cheque del Banco Pichincha y deja el valor "
                     "de los equipos pendiente de pago.",
        "lineas": [("1.2.03", 1000.00, 0, "2 equipos de cómputo"),
                   ("1.1.07", 150.00, 0, "IVA 15 % de 1.000"),
                   ("2.1.01", 0, 1000.00, "Queda pendiente de pago"),
                   ("1.1.02", 0, 150.00, "Cheque por el IVA")],
        "por_que": "Al ser para uso y no para la reventa, va a activo fijo (1.2.03), no a "
                   "inventario. El pago es mixto: el IVA al contado y los equipos a crédito.",
    },
]


# --------------------------------------------------------------------------------- verificación
def verificar(transacciones=None):
    transacciones = transacciones or TRANSACCIONES
    plan = {c["codigo"]: c for c in leer_cuentas()}
    problemas = []
    for numero, t in enumerate(transacciones, start=1):
        debe = round(sum(l[1] for l in t["lineas"]), 2)
        haber = round(sum(l[2] for l in t["lineas"]), 2)
        if abs(debe - haber) >= 0.01:
            problemas.append("Transacción %d: no cuadra (%.2f vs %.2f)" % (numero, debe, haber))
        for codigo, _, _, _ in t["lineas"]:
            if codigo not in plan:
                problemas.append("Transacción %d: la cuenta %s no existe" % (numero, codigo))
            elif not plan[codigo]["tipo"] == "Detalle":
                problemas.append("Transacción %d: la cuenta %s no acepta movimientos"
                                 % (numero, codigo))
    return problemas


def probar_registro(transacciones=None):
    """Registra los asientos en una copia temporal de la plantilla y devuelve los saldos."""
    transacciones = transacciones or TRANSACCIONES
    from services.accounting_service import AccountingService

    temporal = os.path.join(tempfile.mkdtemp(prefix="practica_"), "aula.db")
    shutil.copyfile(ruta_plantilla(), temporal)
    conexion = sqlite3.connect(temporal)
    conexion.row_factory = sqlite3.Row
    ids = {}
    for codigo in {l[0] for t in transacciones for l in t["lineas"]}:
        fila = conexion.execute("SELECT id FROM cuentas WHERE codigo = ?", (codigo,)).fetchone()
        ids[codigo] = fila["id"]
    conexion.close()

    for t in transacciones:
        lineas = [{"cuenta_id": ids[l[0]], "debe": l[1], "haber": l[2], "referencia": l[3]}
                  for l in t["lineas"]]
        fecha = t["fecha"][6:10] + "-" + t["fecha"][3:5] + "-" + t["fecha"][0:2]
        AccountingService.create_journal_entry(1, fecha, t["enunciado"][:80], lineas,
                                               db_path=temporal)

    conexion = sqlite3.connect(temporal)
    conexion.row_factory = sqlite3.Row
    saldos = []
    for codigo in sorted(ids):
        fila = conexion.execute("SELECT nombre FROM cuentas WHERE id = ?", (ids[codigo],)).fetchone()
        debe = conexion.execute("SELECT COALESCE(SUM(debe),0) FROM detalle_asientos WHERE cuenta_id = ?",
                                (ids[codigo],)).fetchone()[0]
        haber = conexion.execute("SELECT COALESCE(SUM(haber),0) FROM detalle_asientos WHERE cuenta_id = ?",
                                 (ids[codigo],)).fetchone()[0]
        saldos.append((codigo, fila["nombre"], round(debe, 2), round(haber, 2), round(debe - haber, 2)))
    total_debe = conexion.execute("SELECT COALESCE(SUM(debe),0) FROM detalle_asientos").fetchone()[0]
    total_haber = conexion.execute("SELECT COALESCE(SUM(haber),0) FROM detalle_asientos").fetchone()[0]
    conexion.close()
    return saldos, round(total_debe, 2), round(total_haber, 2)


# --------------------------------------------------------------------------------- documentos
def _estilos(documento):
    from docx.shared import Pt
    from docx.oxml.ns import qn
    estilo = documento.styles["Normal"]
    estilo.font.name = "Times New Roman"
    estilo.font.size = Pt(11)
    estilo.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")


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
        return p

    linea("UNIVERSIDAD TÉCNICA DE MANABÍ", 12, negrita=True)
    linea(CARRERA, 9.5)
    linea(ASIGNATURA, 9.5, espacio=10)
    linea(titulo, 14, negrita=True, espacio=2)
    linea(subtitulo, 10, cursiva=True, espacio=10)
    linea("Docente: %s" % DOCENTE, 9.5, cursiva=True, espacio=12)


def _tabla_enunciados(documento, transacciones, con_espacio=True):
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    tabla = documento.add_table(rows=1, cols=3)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.style = "Table Grid"
    for indice, texto in enumerate(["N°", "Fecha", "Transacción"]):
        celda = tabla.rows[0].cells[indice]
        celda.text = ""
        p = celda.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        corrida = p.add_run(texto)
        corrida.bold = True
        corrida.font.size = Pt(9.5)
        corrida.font.name = "Times New Roman"
        corrida.font.color.rgb = __import__("docx").shared.RGBColor(0xFF, 0xFF, 0xFF)
        sombreado = OxmlElement("w:shd")
        sombreado.set(qn("w:fill"), "1F3864")
        celda._tc.get_or_add_tcPr().append(sombreado)

    for numero, t in enumerate(transacciones, start=1):
        celdas = tabla.add_row().cells
        for indice, valor in enumerate([str(numero), t["fecha"], t["enunciado"]]):
            celdas[indice].text = ""
            p = celdas[indice].paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if indice < 2 else WD_ALIGN_PARAGRAPH.JUSTIFY
            corrida = p.add_run(valor)
            corrida.font.size = Pt(9.5)
            corrida.font.name = "Times New Roman"
            if indice == 0:
                corrida.bold = True
    for fila in tabla.rows:
        for indice, celda in enumerate(fila.cells):
            celda.width = [Cm(1.0), Cm(2.2), Cm(13.2)][indice]
    return tabla


def _tabla_asiento(documento, t, numero):
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    plan = {c["codigo"]: c for c in leer_cuentas()}
    p = documento.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    corrida = p.add_run("%d. %s" % (numero, t["fecha"]))
    corrida.bold = True
    corrida.font.size = Pt(10)
    corrida.font.name = "Times New Roman"

    # El enunciado completo, para que el asiento se lea junto a la transacción que lo origina.
    enunciado = documento.add_paragraph()
    enunciado.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    enunciado.paragraph_format.space_after = Pt(4)
    corrida = enunciado.add_run(t["enunciado"])
    corrida.font.size = Pt(10)
    corrida.font.name = "Times New Roman"

    tabla = documento.add_table(rows=1, cols=4)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.style = "Table Grid"
    for indice, texto in enumerate(["Código", "Cuenta", "Debe", "Haber"]):
        celda = tabla.rows[0].cells[indice]
        celda.text = ""
        parrafo = celda.paragraphs[0]
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = parrafo.add_run(texto)
        run.bold = True
        run.font.size = Pt(9)
        run.font.name = "Times New Roman"
        run.font.color.rgb = __import__("docx").shared.RGBColor(0xFF, 0xFF, 0xFF)
        sombreado = OxmlElement("w:shd")
        sombreado.set(qn("w:fill"), "1F3864")
        celda._tc.get_or_add_tcPr().append(sombreado)

    for codigo, debe, haber, referencia in t["lineas"]:
        celdas = tabla.add_row().cells
        nombre = plan[codigo]["nombre"]
        valores = [codigo, "%s — %s" % (nombre, referencia) if referencia else nombre,
                   ("%.2f" % debe).replace(".", ",") if debe else "",
                   ("%.2f" % haber).replace(".", ",") if haber else ""]
        for indice, valor in enumerate(valores):
            celdas[indice].text = ""
            parrafo = celdas[indice].paragraphs[0]
            parrafo.paragraph_format.space_after = Pt(0)
            parrafo.alignment = WD_ALIGN_PARAGRAPH.RIGHT if indice >= 2 else WD_ALIGN_PARAGRAPH.LEFT
            run = parrafo.add_run(valor)
            run.font.size = Pt(9)
            run.font.name = "Times New Roman"
            if codigo.startswith(("2", "3", "4")) and indice == 1:
                parrafo.paragraph_format.left_indent = Cm(0.8)

    total_debe = round(sum(l[1] for l in t["lineas"]), 2)
    total_haber = round(sum(l[2] for l in t["lineas"]), 2)
    celdas = tabla.add_row().cells
    for indice, valor in enumerate(["", "Totales",
                                    ("%.2f" % total_debe).replace(".", ","),
                                    ("%.2f" % total_haber).replace(".", ",")]):
        celdas[indice].text = ""
        parrafo = celdas[indice].paragraphs[0]
        parrafo.alignment = WD_ALIGN_PARAGRAPH.RIGHT if indice >= 2 else WD_ALIGN_PARAGRAPH.LEFT
        run = parrafo.add_run(valor)
        run.bold = True
        run.font.size = Pt(9)
        run.font.name = "Times New Roman"

    for fila in tabla.rows:
        for indice, celda in enumerate(fila.cells):
            celda.width = [Cm(1.8), Cm(9.6), Cm(2.6), Cm(2.6)][indice]

    nota = documento.add_paragraph()
    nota.paragraph_format.space_after = Pt(2)
    corrida = nota.add_run("Por qué: " + t["por_que"])
    corrida.italic = True
    corrida.font.size = Pt(9)
    corrida.font.name = "Times New Roman"


def escribir_estudiante(destino, transacciones=None):
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    transacciones = transacciones or TRANSACCIONES
    documento = Document()
    _estilos(documento)
    _encabezado(documento, "Práctica de jornalización básica",
                "Registro de transacciones en el Libro Diario")
    p = documento.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(8)
    corrida = p.add_run(
        "Registre cada transacción en el Libro Diario del simulador (Contabilidad → Libro Diario), "
        "aplicando la partida doble. El IVA es del 15 %. Las transacciones no llevan retenciones. "
        "Use las cuentas del plan de cuentas de su empresa y verifique que el asiento quede "
        "cuadrado antes de contabilizarlo.")
    corrida.font.size = Pt(10.5)
    corrida.font.name = "Times New Roman"

    _tabla_enunciados(documento, transacciones)

    cierre = documento.add_paragraph()
    cierre.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    cierre.paragraph_format.space_before = Pt(10)
    corrida = cierre.add_run(
        "Al terminar, abra el Balance de Comprobación y verifique que las sumas y los saldos "
        "cuadren. Entregue la evidencia con la captura del balance y el detalle de sus asientos.")
    corrida.italic = True
    corrida.font.size = Pt(9.5)
    corrida.font.name = "Times New Roman"

    documento.save(destino)
    return destino


def escribir_solucionario(destino, transacciones=None):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    transacciones = transacciones or TRANSACCIONES
    documento = Document()
    _estilos(documento)
    _encabezado(documento, "Solucionario de la práctica de jornalización",
                "10 transacciones básicas con su asiento y su explicación")
    for numero, t in enumerate(transacciones, start=1):
        _tabla_asiento(documento, t, numero)
    documento.save(destino)
    return destino


def escribir_excel(destino, transacciones=None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    transacciones = transacciones or TRANSACCIONES
    plan = {c["codigo"]: c for c in leer_cuentas()}
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Solucionario"
    encabezados = ["N°", "Fecha", "Transacción", "Código", "Cuenta", "Debe", "Haber"]
    hoja.append(encabezados)
    for celda in hoja[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F3864")
        celda.alignment = Alignment(horizontal="center")
    for numero, t in enumerate(transacciones, start=1):
        for codigo, debe, haber, _ in t["lineas"]:
            hoja.append([numero, t["fecha"], t["enunciado"], codigo,
                         plan[codigo]["nombre"], debe or None, haber or None])
    for fila in hoja.iter_rows(min_row=2):
        fila[2].alignment = Alignment(wrap_text=True, vertical="top")
    for columna, ancho in zip("ABCDEFG", (5, 12, 70, 9, 44, 11, 11)):
        hoja.column_dimensions[columna].width = ancho
    hoja.freeze_panes = "A2"
    libro.save(destino)
    return destino


def main():
    analizador = argparse.ArgumentParser(description="Práctica de jornalización básica.")
    analizador.add_argument("--salida", default=os.path.join(
        os.path.expanduser("~"), "Desktop", "2026", "S2", "Clases", "Contabilidad 1"))
    analizador.add_argument("--probar", action="store_true",
                            help="registra los asientos en un aula temporal y muestra los saldos")
    analizador.add_argument("--solo-probar", action="store_true",
                            help="solo hace la prueba de registro (no genera los documentos)")
    argumentos = analizador.parse_args()

    problemas = verificar()
    print("Transacciones: %d | verificadas: %s"
          % (len(TRANSACCIONES), "todas cuadran y usan cuentas válidas" if not problemas else "CON PROBLEMAS"))
    for problema in problemas:
        print("   [PROBLEMA] %s" % problema)

    if argumentos.solo_probar:
        saldos, debe, haber = probar_registro()
        print()
        print("Registradas en un aula temporal: totales debe %.2f = haber %.2f" % (debe, haber))
        print("   %-8s %-48s %10s %10s %10s" % ("CÓDIGO", "CUENTA", "DEBE", "HABER", "SALDO"))
        for codigo, nombre, d, h, s in saldos:
            print("   %-8s %-48s %10.2f %10.2f %10.2f" % (codigo, nombre[:48], d, h, s))
        return

    os.makedirs(argumentos.salida, exist_ok=True)
    ruta_estudiante = os.path.join(argumentos.salida, "Practica_10_transacciones_basicas.docx")
    ruta_solucion = os.path.join(argumentos.salida, "Practica_10_transacciones_solucionario.docx")
    ruta_excel = os.path.join(argumentos.salida, "Practica_10_transacciones_solucionario.xlsx")
    escribir_estudiante(ruta_estudiante)
    escribir_solucionario(ruta_solucion)
    escribir_excel(ruta_excel)
    print("Estudiante: %s" % ruta_estudiante)
    print("Solucionario: %s" % ruta_solucion)
    print("Excel: %s" % ruta_excel)

    if argumentos.probar:
        saldos, debe, haber = probar_registro()
        print()
        print("Registradas en un aula temporal: totales debe %.2f = haber %.2f" % (debe, haber))
        print("   %-8s %-48s %10s %10s %10s" % ("CÓDIGO", "CUENTA", "DEBE", "HABER", "SALDO"))
        for codigo, nombre, d, h, s in saldos:
            print("   %-8s %-48s %10.2f %10.2f %10.2f" % (codigo, nombre[:48], d, h, s))


if __name__ == "__main__":
    main()
