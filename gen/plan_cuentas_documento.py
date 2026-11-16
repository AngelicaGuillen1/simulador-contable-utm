"""Genera el plan de cuentas del simulador como producto final, en Excel y en Word.

Los datos NO se escriben a mano: se leen del catálogo del propio simulador (la plantilla del
aula), de modo que el documento siempre coincide con lo que ven los estudiantes.

    python gen/plan_cuentas_documento.py
    python gen/plan_cuentas_documento.py --salida "C:/.../Contabilidad 1"
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

TITULO = "Plan de Cuentas del Simulador Integral de Sistema Contable"
ASIGNATURA = "Contabilidad I (AUD ONLINE) · Periodo 2026-P2"
CARRERA = "Carrera de Contabilidad y Auditoría · Universidad Técnica de Manabí"
DOCENTE = "Ing. Angélica Victoria Guillén Pinargote, Mg."

CLASIFICACIONES = {
    "ACTIVO_CORRIENTE": "Activo corriente",
    "ACTIVO_NO_CORRIENTE": "Activo no corriente",
    "PASIVO_CORRIENTE": "Pasivo corriente",
    "PATRIMONIO": "Patrimonio",
    "INGRESOS_OPERACIONALES": "Ingresos operacionales",
    "INGRESOS_NO_OPERACIONALES": "Ingresos no operacionales",
    "COSTOS": "Costos",
    "GASTOS_ADMIN": "Gastos administrativos",
    "GASTOS_VENTAS": "Gastos de ventas",
    "GASTOS_FINANCIEROS": "Gastos financieros",
}


def ruta_plantilla():
    ruta = Config.RUTA_PLANTILLA
    if os.path.isdir(ruta):
        ruta = os.path.join(ruta, "aula_base.db")
    if not os.path.exists(ruta):
        ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "database", "plantilla", "aula_base.db")
    return ruta


GRUPOS = {"1": "Activo", "2": "Pasivo", "3": "Patrimonio", "4": "Ingresos",
          "5": "Costos", "6": "Gastos"}


def leer_cuentas():
    conexion = sqlite3.connect(ruta_plantilla())
    conexion.row_factory = sqlite3.Row
    try:
        filas = conexion.execute(
            "SELECT codigo, nombre, clasificacion, naturaleza, nivel, acepta_movimiento "
            "FROM cuentas ORDER BY codigo").fetchall()
    finally:
        conexion.close()
    cuentas = []
    for f in filas:
        nivel = int(f["nivel"] or 1)
        # La clasificación detallada se muestra en las cuentas de detalle (aceptan movimientos);
        # las agrupadoras se presentan con el grupo al que pertenecen (Activo, Pasivo, ...).
        if f["acepta_movimiento"]:
            clasificacion = CLASIFICACIONES.get(
                f["clasificacion"], (f["clasificacion"] or "").replace("_", " ").title())
        else:
            clasificacion = GRUPOS.get(str(f["codigo"]).split(".")[0],
                                       CLASIFICACIONES.get(f["clasificacion"], "—"))
        cuentas.append({
            "codigo": f["codigo"],
            "nombre": f["nombre"],
            "clasificacion": clasificacion,
            "naturaleza": (f["naturaleza"] or "").capitalize(),
            "nivel": nivel,
            "tipo": "Detalle" if f["acepta_movimiento"] else "Agrupadora",
            "acepta": "Sí" if f["acepta_movimiento"] else "No",
        })
    return cuentas


def resumen(cuentas):
    por_clasificacion, por_nivel, por_naturaleza = {}, {}, {}
    for c in cuentas:
        por_clasificacion.setdefault(c["clasificacion"], [0, 0])
        por_clasificacion[c["clasificacion"]][0] += 1
        por_clasificacion[c["clasificacion"]][1] += 1 if c["tipo"] == "Detalle" else 0
        por_nivel[c["nivel"]] = por_nivel.get(c["nivel"], 0) + 1
        por_naturaleza[c["naturaleza"]] = por_naturaleza.get(c["naturaleza"], 0) + 1
    return por_clasificacion, por_nivel, por_naturaleza


# ----------------------------------------------------------------------------- Excel
def escribir_excel(cuentas, destino):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    azul = "1F3864"
    gris = "F2F2F2"
    borde = Border(*[Side(style="thin", color="BFBFBF")] * 4)

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Plan de cuentas"

    hoja.merge_cells("A1:G1")
    hoja["A1"] = TITULO
    hoja["A1"].font = Font(name="Calibri", size=15, bold=True, color=azul)
    hoja["A1"].alignment = Alignment(horizontal="center", vertical="center")
    hoja.row_dimensions[1].height = 26

    hoja.merge_cells("A2:G2")
    hoja["A2"] = "%s · %s" % (CARRERA, ASIGNATURA)
    hoja["A2"].font = Font(size=10, italic=True, color="595959")
    hoja["A2"].alignment = Alignment(horizontal="center")

    hoja.merge_cells("A3:G3")
    hoja["A3"] = "Docente: %s · %d cuentas · Fuente: catálogo del simulador" % (DOCENTE, len(cuentas))
    hoja["A3"].font = Font(size=9, color="7F7F7F")
    hoja["A3"].alignment = Alignment(horizontal="center")

    encabezados = ["N°", "Código", "Cuenta contable", "Clasificación", "Naturaleza",
                   "Nivel", "Tipo"]
    fila = 5
    for columna, texto in enumerate(encabezados, start=1):
        celda = hoja.cell(row=fila, column=columna, value=texto)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=azul)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        celda.border = borde
    hoja.row_dimensions[fila].height = 30

    for numero, cuenta in enumerate(cuentas, start=1):
        fila += 1
        valores = [numero, cuenta["codigo"], cuenta["nombre"], cuenta["clasificacion"],
                   cuenta["naturaleza"], cuenta["nivel"], cuenta["tipo"]]
        for columna, valor in enumerate(valores, start=1):
            celda = hoja.cell(row=fila, column=columna, value=valor)
            celda.border = borde
            celda.font = Font(bold=(cuenta["nivel"] == 1), size=10)
            celda.alignment = Alignment(vertical="center",
                                        horizontal="center" if columna in (1, 5, 6, 7) else "left",
                                        indent=0 if columna in (1, 5, 6, 7) else (cuenta["nivel"] - 1) * 2)
            if cuenta["nivel"] == 1:
                celda.fill = PatternFill("solid", fgColor=gris)

    fila += 1
    hoja.cell(row=fila, column=3, value="TOTAL DE CUENTAS").font = Font(bold=True)
    hoja.cell(row=fila, column=4, value=len(cuentas)).font = Font(bold=True)

    for columna, ancho in zip("ABCDEFG", (6, 12, 52, 24, 13, 8, 13)):
        hoja.column_dimensions[columna].width = ancho
    hoja.freeze_panes = "A6"
    hoja.auto_filter.ref = "A5:G%d" % (5 + len(cuentas))

    # --- hoja de resumen ---
    detalle = libro.create_sheet("Resumen")
    detalle["A1"] = "Resumen del plan de cuentas"
    detalle["A1"].font = Font(size=14, bold=True, color=azul)
    detalle["A3"] = "Por clasificación"
    detalle["A3"].font = Font(bold=True)
    for columna, texto in enumerate(["Clasificación", "Cuentas", "De detalle"], start=1):
        celda = detalle.cell(row=4, column=columna, value=texto)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=azul)
    por_clasificacion, por_nivel, por_naturaleza = resumen(cuentas)
    fila_resumen = 5
    for clasificacion, (total, movimientos) in sorted(por_clasificacion.items()):
        detalle.cell(row=fila_resumen, column=1, value=clasificacion)
        detalle.cell(row=fila_resumen, column=2, value=total)
        detalle.cell(row=fila_resumen, column=3, value=movimientos)
        fila_resumen += 1
    detalle.cell(row=fila_resumen, column=1, value="TOTAL").font = Font(bold=True)
    detalle.cell(row=fila_resumen, column=2, value=len(cuentas)).font = Font(bold=True)

    fila_resumen += 2
    detalle.cell(row=fila_resumen, column=1, value="Por nivel").font = Font(bold=True)
    for indice, (nivel, total) in enumerate(sorted(por_nivel.items()), start=1):
        detalle.cell(row=fila_resumen + indice, column=1, value="Nivel %d" % nivel)
        detalle.cell(row=fila_resumen + indice, column=2, value=total)

    fila_resumen += len(por_nivel) + 3
    detalle.cell(row=fila_resumen, column=1, value="Por naturaleza").font = Font(bold=True)
    for indice, (naturaleza, total) in enumerate(sorted(por_naturaleza.items()), start=1):
        detalle.cell(row=fila_resumen + indice, column=1, value=naturaleza)
        detalle.cell(row=fila_resumen + indice, column=2, value=total)

    for columna, ancho in zip("ABC", (34, 12, 14)):
        detalle.column_dimensions[columna].width = ancho

    libro.save(destino)
    return destino


# ------------------------------------------------------------------------------ Word
def escribir_word(cuentas, destino):
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    documento = Document()

    seccion = documento.sections[0]
    seccion.orientation = WD_ORIENT.PORTRAIT
    seccion.top_margin = Cm(2)
    seccion.bottom_margin = Cm(2)
    seccion.left_margin = Cm(2.2)
    seccion.right_margin = Cm(2.2)

    estilo = documento.styles["Normal"]
    estilo.font.name = "Times New Roman"
    estilo.font.size = Pt(11)
    estilo.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

    def parrafo(texto, tamano=11, negrita=False, cursiva=False, centrado=False, espacio=6):
        p = documento.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if centrado else WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(espacio)
        corrida = p.add_run(texto)
        corrida.bold = negrita
        corrida.italic = cursiva
        corrida.font.size = Pt(tamano)
        corrida.font.name = "Times New Roman"
        return p

    parrafo("UNIVERSIDAD TÉCNICA DE MANABÍ", 12, negrita=True, centrado=True, espacio=0)
    parrafo(CARRERA, 10, centrado=True, espacio=0)
    parrafo(ASIGNATURA, 10, centrado=True, espacio=12)
    parrafo(TITULO, 14, negrita=True, centrado=True, espacio=4)
    parrafo("Docente: %s" % DOCENTE, 10, cursiva=True, centrado=True, espacio=14)

    por_clasificacion, por_nivel, por_naturaleza = resumen(cuentas)
    parrafo(
        "El plan de cuentas del simulador es el catálogo con el que trabajan todas las empresas "
        "del curso: %d cuentas organizadas en %d niveles, de las cuales %d son de detalle (reciben "
        "movimientos) y %d son agrupadoras. La estructura es idéntica para todos los estudiantes; "
        "cada uno la aplica sobre su propia empresa."
        % (len(cuentas), len(por_nivel), sum(1 for c in cuentas if c["tipo"] == "Detalle"),
           sum(1 for c in cuentas if c["tipo"] == "Agrupadora")),
        11, espacio=10)

    tabla = documento.add_table(rows=1, cols=6)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.style = "Table Grid"
    encabezados = ["Código", "Cuenta contable", "Clasificación", "Naturaleza", "Nivel", "Tipo"]
    anchos = [Cm(2.1), Cm(7.4), Cm(4.0), Cm(2.3), Cm(1.2), Cm(2.2)]
    cabecera = tabla.rows[0].cells
    for indice, texto in enumerate(encabezados):
        cabecera[indice].text = ""
        p = cabecera[indice].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        corrida = p.add_run(texto)
        corrida.bold = True
        corrida.font.size = Pt(9.5)
        corrida.font.name = "Times New Roman"
        corrida.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombreado = OxmlElement("w:shd")
        sombreado.set(qn("w:fill"), "1F3864")
        cabecera[indice]._tc.get_or_add_tcPr().append(sombreado)

    for cuenta in cuentas:
        celdas = tabla.add_row().cells
        valores = [cuenta["codigo"], cuenta["nombre"], cuenta["clasificacion"],
                   cuenta["naturaleza"], str(cuenta["nivel"]), cuenta["tipo"]]
        for indice, valor in enumerate(valores):
            celdas[indice].text = ""
            p = celdas[indice].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if indice in (0, 3, 4, 5) else WD_ALIGN_PARAGRAPH.LEFT
            corrida = p.add_run(valor)
            corrida.font.size = Pt(9)
            corrida.font.name = "Times New Roman"
            corrida.bold = cuenta["nivel"] == 1
            if cuenta["nivel"] == 1:
                sombreado = OxmlElement("w:shd")
                sombreado.set(qn("w:fill"), "F2F2F2")
                celdas[indice]._tc.get_or_add_tcPr().append(sombreado)

    for fila in tabla.rows:
        for indice, celda in enumerate(fila.cells):
            celda.width = anchos[indice]

    documento.add_paragraph()
    parrafo(
        "Resumen por clasificación: "
        + "; ".join("%s (%d)" % (clasificacion, total)
                    for clasificacion, (total, _) in sorted(por_clasificacion.items()))
        + ".", 9.5, cursiva=True, espacio=4)
    parrafo(
        "Nota: el plan es el mismo para todos los estudiantes y no se modifica desde el aula. "
        "Cada estudiante puede cambiar el nombre de sus cuentas para adaptarlas a su empresa, "
        "pero el código se mantiene, de modo que el balance, los estados financieros y las "
        "evidencias siguen siendo comparables.", 9.5, cursiva=True, espacio=4)
    parrafo("Fuente: catálogo del Simulador Integral de Sistema Contable (%d cuentas)." % len(cuentas),
            9, cursiva=True, centrado=True)

    documento.save(destino)
    return destino


def main():
    analizador = argparse.ArgumentParser(description="Plan de cuentas del simulador en Excel y Word.")
    analizador.add_argument("--salida", default=os.path.join(
        os.path.expanduser("~"), "Desktop", "2026", "S2", "Clases", "Contabilidad 1"))
    argumentos = analizador.parse_args()

    cuentas = leer_cuentas()
    if not cuentas:
        raise SystemExit("No encontré el plan de cuentas en la plantilla del simulador.")
    os.makedirs(argumentos.salida, exist_ok=True)
    ruta_xlsx = os.path.join(argumentos.salida, "Plan_de_cuentas_del_simulador.xlsx")
    ruta_docx = os.path.join(argumentos.salida, "Plan_de_cuentas_del_simulador.docx")
    escribir_excel(cuentas, ruta_xlsx)
    escribir_word(cuentas, ruta_docx)
    print("Cuentas: %d | de detalle: %d | agrupadoras: %d"
          % (len(cuentas), sum(1 for c in cuentas if c["tipo"] == "Detalle"),
             sum(1 for c in cuentas if c["tipo"] == "Agrupadora")))
    print("Excel: %s (%d bytes)" % (ruta_xlsx, os.path.getsize(ruta_xlsx)))
    print("Word : %s (%d bytes)" % (ruta_docx, os.path.getsize(ruta_docx)))


if __name__ == "__main__":
    main()
