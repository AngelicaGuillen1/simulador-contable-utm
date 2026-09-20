"""El aviso del aporte inicial: guía al estudiante cuando su empresa aún no opera.

La empresa de cada estudiante arranca con mercadería en bodega (catálogo de productos) y
sin ninguna operación registrada. Mientras el aula esté así, el Dashboard debe mostrarle
el asiento de apertura que le toca registrar; una vez que registra algo, el aviso
desaparece para no estorbar.
"""
import sqlite3

from database.limpiar_aulas import limpiar


def _dashboard(cliente):
    respuesta = cliente.get("/dashboard")
    assert respuesta.status_code == 200, "el dashboard debe abrir para el estudiante"
    return respuesta.get_data(as_text=True)


def _valor_catalogo(ruta):
    conexion = sqlite3.connect(ruta)
    try:
        return round(conexion.execute(
            "SELECT COALESCE(SUM(stock_actual * costo_unitario), 0) FROM productos WHERE activo = 1"
        ).fetchone()[0] or 0, 2)
    finally:
        conexion.close()


def test_el_aviso_aparece_cuando_el_aula_no_tiene_operaciones(estudiante_client, db):
    limpiar(db, confirmar=True)

    cuerpo = _dashboard(estudiante_client)

    assert "Tu empresa ya tiene mercadería" in cuerpo, (
        "debe avisarle que su empresa arranca con mercadería sin operaciones")
    assert "aporte inicial" in cuerpo.lower()
    assert "Inventario de Mercaderías" in cuerpo
    assert "Capital Social" in cuerpo
    assert "Libro Diario" in cuerpo, "debe darle el enlace para registrarlo"


def test_el_aviso_muestra_el_valor_real_del_catalogo(estudiante_client, db):
    limpiar(db, confirmar=True)
    esperado = _valor_catalogo(db)
    assert esperado > 0, "el catálogo de productos debe traer mercadería valorada"

    cuerpo = _dashboard(estudiante_client)

    miles = "{:,.2f}".format(esperado)
    assert miles in cuerpo or miles.replace(",", ",") in cuerpo, (
        "el aviso debe indicar el inventario al costo del catálogo (%s)" % miles)


def test_el_aviso_desaparece_cuando_ya_hay_operaciones(estudiante_client, db):
    conexion = sqlite3.connect(db)
    try:
        asientos = conexion.execute(
            "SELECT COUNT(*) FROM asientos WHERE estado IN ('CONTABILIZADO', 'REVERTIDO')"
        ).fetchone()[0]
    finally:
        conexion.close()
    assert asientos > 0, "la base demostrativa debe traer operaciones para esta prueba"

    cuerpo = _dashboard(estudiante_client)

    assert "Tu empresa ya tiene mercadería" not in cuerpo, (
        "con operaciones registradas el aviso no debe aparecer")
