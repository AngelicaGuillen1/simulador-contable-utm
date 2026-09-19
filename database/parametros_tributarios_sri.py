# -*- coding: utf-8 -*-
"""parametros_tributarios_sri.py — porcentajes oficiales del SRI para compras y ventas.

Deja la configuración tributaria del simulador conforme a la normativa vigente en Ecuador:

* **IVA** — tarifa general 15 % (LRTI; tarifas 5 % construcción, 8 % turístico y 0 %).
* **Retención del IVA** — Resolución NAC-DGERCGC20-00000061 (sin cambios en 2026):
  30 % bienes, 70 % servicios y derechos, 100 % profesionales/arrendamiento/liquidaciones de compra,
  y 10 % / 20 % cuando el proveedor es contribuyente especial.
* **Retención en la fuente del Impuesto a la Renta** — Resolución NAC-DGERCGC26-00000009,
  vigente desde el 1 de marzo de 2026 (deroga la NAC-DGERCGC24-00000008): 2 % bienes muebles de
  naturaleza corporal (antes 1,75 %), 3 % servicios con predominio de mano de obra (antes 2 %),
  5 % servicios profesionales de sociedades (categoría nueva), 10 % honorarios y arrendamiento de
  inmuebles (antes 8 %), 3 % residual para pagos sin porcentaje específico.

Los porcentajes son DATO, no código: se guardan en la tabla `impuestos` con su código del SRI, su
fuente y su fecha de vigencia, y el docente puede ajustarlos desde el sistema cuando la normativa
cambie.

Uso:
    python database/parametros_tributarios_sri.py                 # base de control
    python database/parametros_tributarios_sri.py --todas-las-aulas
    python database/parametros_tributarios_sri.py --listar
"""
import argparse
import glob
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config  # noqa: E402

FUENTE_IVA = "LRTI y Reglamento de aplicación; tarifa general vigente"
FUENTE_RET_IVA = "Resolución NAC-DGERCGC20-00000061 (retención de IVA)"
FUENTE_RET_RENTA = "Resolución NAC-DGERCGC26-00000009, vigente desde 01/03/2026"

# La cuenta de retención de IVA se resuelve en tiempo de ejecución porque el plan de cuentas
# pedagógico puede tener ocupado el código 2.1.04: ver _asegurar_cuenta_retencion().
SENTINELA_RET_IVA = "RET_IVA_POR_PAGAR"

# Cuentas del lado VENTA: cuando el cliente es agente de retención, lo que le retiene al vendedor
# queda como cuenta por cobrar (anticipo de Renta y crédito tributario de IVA a su favor). El código
# se asigna al vuelo, porque el plan de cuentas pedagógico puede tener ocupados los previstos.
CUENTAS_VENTA = [
    ("RETENCION_IVA", "Retención en la Fuente de IVA por Cobrar (Crédito Tributario)", "DEUDORA",
     "ACTIVO_CORRIENTE", ("retencion", "iva", "cobrar")),
    ("RETENCION_RENTA", "Retención en la Fuente de Renta por Cobrar (Anticipo IR)", "DEUDORA",
     "ACTIVO_CORRIENTE", ("retencion", "renta", "cobrar")),
]

# Código canónico de cada cuenta del lado venta (se respeta si está libre).
CODIGO_VENTA_CANONICO = {"RETENCION_IVA": "1.1.09", "RETENCION_RENTA": "1.1.10"}

# ---------------------------------------------------------------------------------------------
# IVA
IVA = [
    # codigo, nombre, porcentaje, tipo, cuenta, codigo_sri, aplica_a, fuente, vigencia
    ("IVA-15-VTA", "IVA tarifa general 15 % en ventas", 15.0, "IVA_VENTAS", "2.1.02", None,
     "VENTA", FUENTE_IVA, "2024-04-01"),
    ("IVA-15-COM", "IVA tarifa general 15 % en compras (crédito tributario)", 15.0, "IVA_COMPRAS", "1.1.07",
     None, "COMPRA", FUENTE_IVA, "2024-04-01"),
    ("IVA-05-CON", "IVA 5 % en servicios de construcción", 5.0, "IVA_CONSTRUCCION", "1.1.07", None,
     "COMPRA", "LRTI, tarifa especial de construcción", "2024-04-01"),
    ("IVA-08-TUR", "IVA 8 % en servicios turísticos (feriados decretados)", 8.0, "IVA_TURISTICO", "1.1.07",
     None, "VENTA", "LRTI, tarifa especial turística", "2024-04-01"),
]

# ---------------------------------------------------------------------------------------------
# Retención del IVA (se calcula sobre el IVA de la factura, no sobre la base)
RETENCION_IVA = [
    ("RET-IVA-30-BIE", "Retención de IVA 30 % — transferencia de bienes gravados", 30.0,
     "RET_IVA_BIENES", SENTINELA_RET_IVA, "721", "COMPRA_BIENES", FUENTE_RET_IVA, "2020-10-29"),
    ("RET-IVA-70-SRV", "Retención de IVA 70 % — servicios, derechos, comisiones y consultoría", 70.0,
     "RET_IVA_SERVICIOS", SENTINELA_RET_IVA, "723", "COMPRA_SERVICIOS", FUENTE_RET_IVA, "2020-10-29"),
    ("RET-IVA-100-PRO", "Retención de IVA 100 % — servicios profesionales de personas naturales y "
                        "arrendamiento de inmuebles de personas naturales", 100.0,
     "RET_IVA_PROFESIONALES", SENTINELA_RET_IVA, "725", "COMPRA_SERVICIOS", FUENTE_RET_IVA, "2020-10-29"),
    ("RET-IVA-100-LIQ", "Retención de IVA 100 % — liquidaciones de compra de bienes y servicios", 100.0,
     "RET_IVA_LIQUIDACION", SENTINELA_RET_IVA, "729", "LIQUIDACION_COMPRA", FUENTE_RET_IVA, "2020-10-29"),
    ("RET-IVA-100-CON", "Retención de IVA 100 % — importación de servicios y servicios digitales", 100.0,
     "RET_IVA_IMPORTACION", SENTINELA_RET_IVA, "725", "COMPRA_SERVICIOS",
     FUENTE_RET_IVA, "2020-10-29"),
    ("RET-IVA-10-BIE-ESP", "Retención de IVA 10 % — bienes adquiridos a otro contribuyente especial", 10.0,
     "RET_IVA_BIENES_ESPECIALES", SENTINELA_RET_IVA, "721", "COMPRA_BIENES", FUENTE_RET_IVA, "2020-10-29"),
    ("RET-IVA-20-SRV-ESP", "Retención de IVA 20 % — servicios de otro contribuyente especial", 20.0,
     "RET_IVA_SERVICIOS_ESPECIALES", SENTINELA_RET_IVA, "723", "COMPRA_SERVICIOS", FUENTE_RET_IVA, "2020-10-29"),
]

# ---------------------------------------------------------------------------------------------
# Retención de Impuesto a la Renta (se calcula sobre el valor del bien o servicio)
RETENCION_RENTA = [
    ("RET-RENTA-02-BIE", "Retención Renta 2 % — adquisición de bienes muebles de naturaleza corporal "
                         "(mercadería en general)", 2.0, "RET_RENTA_BIENES", "2.1.03", "312",
     "COMPRA_BIENES", FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-03-SRV", "Retención Renta 3 % — servicios de personas naturales donde predomina la "
                         "mano de obra (limpieza, mantenimiento)", 3.0, "RET_RENTA_SERVICIOS", "2.1.03",
     "304", "COMPRA_SERVICIOS", FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-10-HON", "Retención Renta 10 % — honorarios y servicios profesionales de personas "
                         "naturales; arrendamiento de bienes inmuebles; cánones y regalías", 10.0,
     "RET_RENTA_HONORARIOS", "2.1.03", "303", "COMPRA_SERVICIOS", FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-05-SOC", "Retención Renta 5 % — servicios profesionales y comisiones pagados a "
                         "sociedades residentes", 5.0, "RET_RENTA_SERVICIOS_SOCIEDADES", "2.1.03", "308",
     "COMPRA_SERVICIOS", FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-01-AGR", "Retención Renta 1 % — bienes de origen agrícola, avícola, pecuario y forestal "
                         "comprados directamente al productor", 1.0, "RET_RENTA_AGRICOLA_PRODUCTOR",
     "2.1.03", "312", "COMPRA_BIENES", FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-175-AGR", "Retención Renta 1,75 % — bienes agrícolas, avícolas y pecuarios comprados a "
                          "comercializadores", 1.75, "RET_RENTA_AGRICOLA_COMERCIALIZADOR", "2.1.03", "312",
     "COMPRA_BIENES", FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-01-RIMPE", "Retención Renta 1 % — compras a contribuyentes RIMPE Emprendedor", 1.0,
     "RET_RENTA_RIMPE_EMPRENDEDOR", "2.1.03", "343", "COMPRA", FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-00-RIMPE", "Retención Renta 0 % — compras a RIMPE Negocio Popular (con comprobante "
                           "preimpreso)", 0.0, "RET_RENTA_RIMPE_POPULAR", "2.1.03", "332", "COMPRA",
     FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-03-LIQ", "Retención Renta 3 % — liquidaciones de compra a personas sin RUC o con RUC "
                         "suspendido", 3.0, "RET_RENTA_LIQUIDACION", "2.1.03", "341", "LIQUIDACION_COMPRA",
     FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-03-RES", "Retención Renta 3 % — pagos sin porcentaje específico (regla residual)", 3.0,
     "RET_RENTA_RESIDUAL", "2.1.03", "340", "COMPRA", FUENTE_RET_RENTA, "2026-03-01"),
    ("RET-RENTA-00-BAN", "Retención Renta 0 % — intereses pagados a bancos y entidades financieras "
                         "supervisadas", 0.0, "RET_RENTA_BANCOS", "2.1.03", "332", "COMPRA", FUENTE_RET_RENTA,
     "2026-03-01"),
]

TODOS = IVA + RETENCION_IVA + RETENCION_RENTA

# Cuenta del lado VENTA que corresponde a cada tipo de retención (lo retenido al vendedor).
CUENTA_VENTA_POR_TIPO = {
    "RET_RENTA_BIENES": "RETENCION_RENTA",
    "RET_RENTA_SERVICIOS": "RETENCION_RENTA",
    "RET_RENTA_HONORARIOS": "RETENCION_RENTA",
    "RET_RENTA_SERVICIOS_SOCIEDADES": "RETENCION_RENTA",
    "RET_RENTA_AGRICOLA_PRODUCTOR": "RETENCION_RENTA",
    "RET_RENTA_AGRICOLA_COMERCIALIZADOR": "RETENCION_RENTA",
    "RET_RENTA_RIMPE_EMPRENDEDOR": "RETENCION_RENTA",
    "RET_RENTA_RIMPE_POPULAR": "RETENCION_RENTA",
    "RET_RENTA_LIQUIDACION": "RETENCION_RENTA",
    "RET_RENTA_RESIDUAL": "RETENCION_RENTA",
    "RET_RENTA_BANCOS": "RETENCION_RENTA",
    "RET_IVA_BIENES": "RETENCION_IVA",
    "RET_IVA_SERVICIOS": "RETENCION_IVA",
    "RET_IVA_PROFESIONALES": "RETENCION_IVA",
    "RET_IVA_LIQUIDACION": "RETENCION_IVA",
    "RET_IVA_IMPORTACION": "RETENCION_IVA",
    "RET_IVA_BIENES_ESPECIALES": "RETENCION_IVA",
    "RET_IVA_SERVICIOS_ESPECIALES": "RETENCION_IVA",
}

# Cuenta contable nueva: en el compendio de la Unidad 3 las retenciones de Renta y de IVA se
# acreditan por separado.
CUENTA_RETENCION_IVA = ("2.1.06")


def _normalizar_codigos_venta(conn, cuentas_venta):
    """Deja las cuentas del lado venta con su código canónico, sin importar en qué orden se crearon.

    Canónico: 1.1.09 = retención de IVA por cobrar; 1.1.10 = retención de Renta por cobrar.
    El intercambio se hace en tres pasos (temporales → canónicos → reubicación de terceros) porque
    `cuentas.codigo` es UNIQUE y un intercambio directo la violaría.
    """
    asignaciones = [(cuentas_venta[clave], canonico)
                    for clave, canonico in CODIGO_VENTA_CANONICO.items() if cuentas_venta.get(clave)]
    if not asignaciones:
        return 0
    ocupados = {r["id"]: r["codigo"] for r in conn.execute("SELECT id, codigo FROM cuentas")}
    nuestras = {cuenta_id for cuenta_id, _ in asignaciones}
    implicadas = set(nuestras)
    for cuenta_id, canonico in asignaciones:
        for otro_id, codigo in ocupados.items():
            if codigo == canonico:
                implicadas.add(otro_id)

    if all(ocupados.get(cuenta_id) == canonico
           for cuenta_id, canonico in asignaciones if cuenta_id in ocupados):
        return 0

    # 1) todas las implicadas pasan a un código temporal
    for indice, cuenta_id in enumerate(sorted(implicadas)):
        conn.execute("UPDATE cuentas SET codigo = ? WHERE id = ?",
                     ("_tmp_norm_%d" % indice, cuenta_id))
    # 2) nuestras cuentas toman su código canónico
    for cuenta_id, canonico in asignaciones:
        conn.execute("UPDATE cuentas SET codigo = ? WHERE id = ?", (canonico, cuenta_id))
    # 3) las cuentas ajenas que estaban en un canónico reciben un código libre de su serie
    ajenas = implicadas - nuestras
    if ajenas:
        en_uso = {r[0] for r in conn.execute("SELECT codigo FROM cuentas")}
        for cuenta_id in sorted(ajenas):
            actual = conn.execute("SELECT codigo FROM cuentas WHERE id = ?", (cuenta_id,)).fetchone()
            if not actual or not str(actual["codigo"]).startswith("_tmp_norm_"):
                continue
            prefijo = "1.1."
            libre = None
            for sufijo in range(11, 60):
                candidato = "%s%02d" % (prefijo, sufijo)
                if candidato not in en_uso:
                    libre = candidato
                    break
            if libre:
                en_uso.add(libre)
                conn.execute("UPDATE cuentas SET codigo = ? WHERE id = ?", (libre, cuenta_id))
    return len(asignaciones)


def _conectar(ruta):
    conn = sqlite3.connect(ruta, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def _columnas(conn, tabla):
    return [r[1] for r in conn.execute("PRAGMA table_info(%s)" % tabla)]


def _asegurar_columnas(conn):
    columnas = _columnas(conn, "impuestos")
    nuevas = 0
    for columna, tipo in (("codigo_sri", "TEXT"), ("fuente", "TEXT"), ("aplica_a", "TEXT"),
                          ("cuenta_venta_id", "INTEGER")):
        if columna not in columnas:
            conn.execute("ALTER TABLE impuestos ADD COLUMN %s %s" % (columna, tipo))
            nuevas += 1
    return nuevas


def _asegurar_cuenta(conn, codigo, nombre, naturaleza, clasificacion):
    """Devuelve el id de la cuenta indicada, creándola si no existe (idempotente)."""
    fila = conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (codigo,)).fetchone()
    if fila:
        return fila["id"]
    columnas = _columnas(conn, "cuentas")
    datos = {"codigo": codigo, "nombre": nombre, "naturaleza": naturaleza,
             "clasificacion": clasificacion, "acepta_movimiento": 1}
    if "activo" in columnas:
        datos["activo"] = 1
    if "nivel" in columnas:
        datos["nivel"] = 2
    if "cuenta_padre_id" in columnas:
        padre = conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (codigo[:3],)).fetchone()
        datos["cuenta_padre_id"] = padre["id"] if padre else None
    campos = [c for c in datos if c in columnas]
    conn.execute("INSERT INTO cuentas (%s) VALUES (%s)" % (",".join(campos),
                ",".join("?" for _ in campos)), [datos[c] for c in campos])
    return conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (codigo,)).fetchone()["id"]


def _resolver_cuenta(conn, palabras, nombre_nuevo, naturaleza, clasificacion,
                     prefijo="1.1.", desde=8, hasta=30):
    """Devuelve una cuenta que coincida con las palabras del nombre; si no existe, la crea con el
    primer código libre de la serie (1.1.08, 1.1.09, ...) para no pisar cuentas del plan."""
    columnas = _columnas(conn, "cuentas")
    filas = conn.execute("SELECT id, nombre, codigo FROM cuentas").fetchall()
    for fila in filas:
        nombre = (fila["nombre"] or "").lower().replace("ó", "o").replace("í", "i")
        if all(p in nombre for p in palabras):
            return fila["id"]
    ocupados = {f["codigo"] for f in filas}
    codigo = None
    for sufijo in range(desde, hasta):
        candidato = "%s%02d" % (prefijo, sufijo)
        if candidato not in ocupados:
            codigo = candidato
            break
    if codigo is None:
        return None
    datos = {"codigo": codigo, "nombre": nombre_nuevo, "naturaleza": naturaleza,
             "clasificacion": clasificacion, "acepta_movimiento": 1}
    if "activo" in columnas:
        datos["activo"] = 1
    if "nivel" in columnas:
        datos["nivel"] = 2
    if "cuenta_padre_id" in columnas:
        padre = conn.execute("SELECT id FROM cuentas WHERE codigo = ?",
                             (prefijo.rstrip("."),)).fetchone()
        datos["cuenta_padre_id"] = padre["id"] if padre else None
    campos = [c for c in datos if c in columnas]
    conn.execute("INSERT INTO cuentas (%s) VALUES (%s)" % (",".join(campos),
                ",".join("?" for _ in campos)), [datos[c] for c in campos])
    nuevo_id = conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (codigo,)).fetchone()["id"]
    print("     cuenta creada: %s %s (id %s)" % (codigo, nombre_nuevo, nuevo_id))
    return nuevo_id


def _asegurar_cuenta_retencion(conn):
    """Devuelve el id de la cuenta donde se acredita la retención de IVA por pagar.

    Cuidado: en el plan de cuentas pedagógico el código 2.1.04 ya está ocupado por «Sueldos y
    Beneficios Sociales por Pagar». Primero se busca una cuenta cuyo nombre sea de retención de
    IVA; si no existe, se crea con el primer código libre de la serie 2.1.0x.
    """
    fila = conn.execute("""SELECT id FROM cuentas
                           WHERE REPLACE(LOWER(nombre), 'ó', 'o') LIKE '%retencion%'
                             AND LOWER(nombre) LIKE '%iva%'
                           ORDER BY id LIMIT 1""").fetchone()
    if fila:
        return fila["id"]

    columnas = _columnas(conn, "cuentas")
    ocupados = {r[0] for r in conn.execute("SELECT codigo FROM cuentas")}
    codigo = None
    for sufijo in range(4, 20):
        candidato = "2.1.%02d" % sufijo
        if candidato not in ocupados:
            codigo = candidato
            break
    if codigo is None:
        return None

    datos = {"codigo": codigo, "nombre": "Retención en la Fuente de IVA por Pagar",
             "naturaleza": "ACREEDORA", "clasificacion": "PASIVO_CORRIENTE", "acepta_movimiento": 1}
    if "activo" in columnas:
        datos["activo"] = 1
    if "nivel" in columnas:
        datos["nivel"] = 2
    if "cuenta_padre_id" in columnas:
        padre = conn.execute("SELECT id FROM cuentas WHERE codigo = '2.1'").fetchone()
        datos["cuenta_padre_id"] = padre["id"] if padre else None
    campos = [c for c in datos if c in columnas]
    conn.execute("INSERT INTO cuentas (%s) VALUES (%s)" % (",".join(campos),
                ",".join("?" for _ in campos)), [datos[c] for c in campos])
    conexion_id = conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (codigo,)).fetchone()["id"]
    print("     cuenta creada: %s %s (id %s)" % (codigo, datos["nombre"], conexion_id))
    return conexion_id


def aplicar(ruta, verboso=True):
    """Escribe los porcentajes oficiales en la base indicada. Idempotente."""
    conn = _conectar(ruta)
    try:
        columnas_nuevas = _asegurar_columnas(conn)
        cuenta_ret_iva = _asegurar_cuenta_retencion(conn)
        cuentas_venta = {clave: _resolver_cuenta(conn, palabras, nombre, naturaleza, clasificacion)
                         for clave, nombre, naturaleza, clasificacion, palabras in CUENTAS_VENTA}
        _normalizar_codigos_venta(conn, cuentas_venta)
        actualizados = creados = 0
        for codigo, nombre, porcentaje, tipo, cuenta_codigo, codigo_sri, aplica_a, fuente, vigencia in TODOS:
            if cuenta_codigo == SENTINELA_RET_IVA:
                cuenta_id = cuenta_ret_iva
            else:
                cuenta = conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (cuenta_codigo,)).fetchone()
                cuenta_id = cuenta["id"] if cuenta else None
            cuenta_venta_codigo = CUENTA_VENTA_POR_TIPO.get(tipo)
            cuenta_venta_id = (cuentas_venta.get(cuenta_venta_codigo) if cuenta_venta_codigo else None)
            existente = conn.execute("SELECT id FROM impuestos WHERE codigo = ?", (codigo,)).fetchone()
            if existente:
                conn.execute("""UPDATE impuestos SET nombre=?, porcentaje=?, tipo=?, cuenta_contable_id=?,
                                vigencia_desde=?, activo=1, codigo_sri=?, fuente=?, aplica_a=?,
                                cuenta_venta_id=?
                                WHERE codigo=?""",
                             (nombre, float(porcentaje), tipo, cuenta_id, vigencia, codigo_sri,
                              fuente, aplica_a, cuenta_venta_id, codigo))
                actualizados += 1
            else:
                conn.execute("""INSERT INTO impuestos (codigo, nombre, porcentaje, tipo, cuenta_contable_id,
                                vigencia_desde, activo, codigo_sri, fuente, aplica_a, cuenta_venta_id)
                                VALUES (?,?,?,?,?,?,1,?,?,?,?)""",
                             (codigo, nombre, float(porcentaje), tipo, cuenta_id, vigencia,
                              codigo_sri, fuente, aplica_a, cuenta_venta_id))
                creados += 1

        # Se retiran los porcentajes que la normativa de 2026 dejó sin efecto y los códigos
        # heredados de la maqueta inicial, que quedaron reemplazados por los códigos oficiales.
        heredados = ("RET-FTE-BIE", "RET-IVA-BIE", "RET-IVA-SRV", "RET-FTE-SRV")
        eliminados = []
        for codigo in heredados:
            fila = conn.execute("SELECT porcentaje, nombre FROM impuestos WHERE codigo = ?",
                                (codigo,)).fetchone()
            if fila:
                conn.execute("DELETE FROM impuestos WHERE codigo = ?", (codigo,))
                eliminados.append("%s (%s %%)" % (codigo, fila["porcentaje"]))

        desactivados = []

        conn.commit()
        if verboso:
            print("  %s" % ruta)
            print("     cuentas/columnas nuevas: %d columnas | cuenta 2.1.04 id=%s"
                  % (columnas_nuevas, cuenta_ret_iva))
            print("     porcentajes: %d actualizados, %d creados" % (actualizados, creados))
            if eliminados:
                print("     códigos heredados retirados: %s" % ", ".join(eliminados))
            if desactivados:
                print("     desactivados por obsoletos: %s" % ", ".join(desactivados))
        return actualizados + creados
    finally:
        conn.close()


def aplicar_a_todas_las_aulas(verboso=True):
    aulas = sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db")))
    if os.path.exists(Config.RUTA_PLANTILLA):
        aulas.insert(0, Config.RUTA_PLANTILLA)   # las aulas nuevas nacen ya actualizadas
    if not aulas:
        print("No hay aulas creadas.")
        return 0
    if verboso:
        print("Aplicando los porcentajes oficiales a %d bases (aulas + plantilla)..." % len(aulas))
    total = 0
    for aula in aulas:
        try:
            total += aplicar(aula, verboso=False)
        except sqlite3.Error as error:
            print("   aviso: %s -> %s" % (os.path.basename(aula), error))
    if verboso:
        print("Aulas actualizadas: %d (%d filas de impuestos)" % (len(aulas), total))
    return total


def listar(ruta=None):
    conn = _conectar(ruta or Config.DATABASE_PATH)
    try:
        print("%-22s %-8s %-6s %-26s %s" % ("CÓDIGO", "SRI", "%", "CONCEPTO", "APLICA A"))
        print("-" * 118)
        for r in conn.execute("""SELECT codigo, codigo_sri, porcentaje, nombre, aplica_a, activo
                                 FROM impuestos ORDER BY tipo, porcentaje"""):
            print("%-22s %-8s %-6s %-26s %s%s"
                  % (r["codigo"], r["codigo_sri"] or "-", r["porcentaje"], (r["nombre"] or "")[:26],
                     r["aplica_a"] or "-", "" if r["activo"] else "   (INACTIVO)"))
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description="Porcentajes oficiales del SRI para el simulador")
    p.add_argument("--db", default=None)
    p.add_argument("--todas-las-aulas", action="store_true")
    p.add_argument("--listar", action="store_true")
    args = p.parse_args()
    if args.listar:
        listar(args.db)
        return 0
    aplicar(args.db or Config.DATABASE_PATH)
    if args.todas_las_aulas:
        aplicar_a_todas_las_aulas()
    return 0


if __name__ == "__main__":
    sys.exit(main())
