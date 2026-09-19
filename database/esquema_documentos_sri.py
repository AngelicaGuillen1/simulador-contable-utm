# -*- coding: utf-8 -*-
"""esquema_documentos_sri.py — catálogo de documentos del SRI como DATOS + migración.

Convierte la sección 57 del Prompt Maestro v2 (redactada a partir del Reglamento de comprobantes
de venta, retención y documentos complementarios y de los formatos oficiales del SRI) en dos
tablas de datos —`tipos_documento` y `reglas_documento`— más las columnas que necesita
`documentos_fuente` para guardar un comprobante ecuatoriano completo.

Nada de esto va escrito en el código del negocio: los tipos, sus campos y las reglas se leen de
la base de datos, de modo que la docente pueda ajustarlos sin programar.

Uso:
    python database/esquema_documentos_sri.py            # aplica y siembra
    python database/esquema_documentos_sri.py --listar   # muestra el catálogo cargado
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config  # noqa: E402

# --------------------------------------------------------------------------------------
# Columnas nuevas de documentos_fuente (todas admiten NULL: los documentos ya registrados
# en la demostración siguen siendo válidos).
COLUMNAS_DOCUMENTO = [
    ("ruc_emisor", "TEXT"),
    ("numero_autorizacion", "TEXT"),
    ("fecha_autorizacion", "DATE"),
    ("establecimiento", "TEXT"),
    ("punto_emision", "TEXT"),
    ("secuencial", "TEXT"),
    ("numero_completo", "TEXT"),          # 001-002-000000123 (15 dígitos sin guiones)
    ("tipo_emision", "TEXT"),             # NORMAL | OFFLINE
    ("adquirente_tipo_id", "TEXT"),       # RUC | CEDULA | PASAPORTE | CONSUMIDOR_FINAL
    ("adquirente_identificacion", "TEXT"),
    ("adquirente_nombre", "TEXT"),
    ("forma_pago", "TEXT"),               # EFECTIVO | TARJETA_CREDITO | TARJETA_DEBITO | OTROS | CREDITO
    ("subtotal", "REAL"),
    ("descuento", "REAL"),
    ("iva_tarifa", "REAL"),
    ("iva_valor", "REAL"),
    ("ice_valor", "REAL"),
    ("propina", "REAL"),
    ("documento_modificado", "TEXT"),     # comprobante que modifica (notas de crédito/débito)
    ("motivo_modificacion", "TEXT"),
    ("base_retencion", "REAL"),
    ("porcentaje_retencion", "REAL"),
    ("valor_retenido", "REAL"),
    ("impuesto_retenido", "TEXT"),        # RENTA | IVA | ISD
    ("fecha_entrega_retencion", "DATE"),
    ("valor_modificacion", "REAL"),
    ("motivo_traslado", "TEXT"),          # guía de remisión
    ("direccion_partida", "TEXT"),
    ("direccion_destino", "TEXT"),
    ("transportista", "TEXT"),
    ("placa_vehiculo", "TEXT"),
    ("estado", "TEXT DEFAULT 'EMITIDO'"),  # EMITIDO | ENTREGADO | ANULADO | DADO_DE_BAJA
    ("origen_actividad_id", "INTEGER"),
]

ESQUEMA_SRI_SQL = """
-- Tipos de documento del catálogo normativo ecuatoriano.
CREATE TABLE IF NOT EXISTS tipos_documento (
    codigo TEXT PRIMARY KEY,                 -- FACTURA, NOTA_VENTA_RISE, ...
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,                 -- COMPROBANTE_VENTA | COMPLEMENTARIO | RETENCION | DOCUMENTO_SOPORTE
    cuando_se_emite TEXT,
    emisor TEXT,
    acompanantes TEXT,
    campos_preimpresos TEXT,                 -- JSON con la lista de campos
    campos_llenado TEXT,                     -- JSON con la lista de campos
    requisitos TEXT,                         -- JSON con las condiciones normativas
    pagina_fuente TEXT,
    activo INTEGER DEFAULT 1
);

-- Reglas de negocio del reglamento, convertidas en validaciones del sistema.
CREATE TABLE IF NOT EXISTS reglas_documento (
    codigo TEXT PRIMARY KEY,                 -- R-57.1 ...
    titulo TEXT NOT NULL,
    aplica_a TEXT,                           -- CSV de tipos de documento o TODO
    regla TEXT NOT NULL,
    validacion TEXT NOT NULL,
    mensaje TEXT NOT NULL,                   -- mensaje que ve el estudiante
    severidad TEXT DEFAULT 'BLOQUEO',        -- BLOQUEO | ADVERTENCIA | INFORMATIVA
    pagina_fuente TEXT,
    activo INTEGER DEFAULT 1
);
"""


def _conectar(ruta=None):
    conn = sqlite3.connect(ruta or Config.DATABASE_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def aplicar(ruta=None, verboso=True):
    conn = _conectar(ruta)
    try:
        conn.executescript(ESQUEMA_SRI_SQL)
        existentes = {r[1] for r in conn.execute("PRAGMA table_info(documentos_fuente)")}
        agregadas = 0
        for columna, tipo in COLUMNAS_DOCUMENTO:
            if columna not in existentes:
                conn.execute("ALTER TABLE documentos_fuente ADD COLUMN %s %s" % (columna, tipo))
                agregadas += 1
        conn.commit()
        if verboso:
            print("Catálogo del SRI aplicado: 2 tablas y %d columnas nuevas en documentos_fuente"
                  % agregadas)
        return agregadas
    finally:
        conn.close()


def sembrar(ruta=None, verboso=True):
    """Carga el catálogo y las reglas (idempotente: vuelve a escribirlas si cambian)."""
    from database.catalogo_sri_datos import TIPOS_DOCUMENTO, REGLAS_DOCUMENTO
    conn = _conectar(ruta)
    try:
        for t in TIPOS_DOCUMENTO:
            conn.execute(
                """INSERT INTO tipos_documento (codigo, nombre, categoria, cuando_se_emite, emisor,
                       acompanantes, campos_preimpresos, campos_llenado, requisitos, pagina_fuente, activo)
                   VALUES (?,?,?,?,?,?,?,?,?,?,1)
                   ON CONFLICT(codigo) DO UPDATE SET
                       nombre=excluded.nombre, categoria=excluded.categoria,
                       cuando_se_emite=excluded.cuando_se_emite, emisor=excluded.emisor,
                       acompanantes=excluded.acompanantes, campos_preimpresos=excluded.campos_preimpresos,
                       campos_llenado=excluded.campos_llenado, requisitos=excluded.requisitos,
                       pagina_fuente=excluded.pagina_fuente, activo=1""",
                (t["codigo"], t["nombre"], t["categoria"], t.get("cuando_se_emite"), t.get("emisor"),
                 t.get("acompanantes"), json.dumps(t.get("campos_preimpresos", []), ensure_ascii=False),
                 json.dumps(t.get("campos_llenado", []), ensure_ascii=False),
                 json.dumps(t.get("requisitos", []), ensure_ascii=False),
                 t.get("pagina_fuente")))
        for r in REGLAS_DOCUMENTO:
            conn.execute(
                """INSERT INTO reglas_documento (codigo, titulo, aplica_a, regla, validacion, mensaje,
                       severidad, pagina_fuente, activo)
                   VALUES (?,?,?,?,?,?,?,?,1)
                   ON CONFLICT(codigo) DO UPDATE SET
                       titulo=excluded.titulo, aplica_a=excluded.aplica_a, regla=excluded.regla,
                       validacion=excluded.validacion, mensaje=excluded.mensaje,
                       severidad=excluded.severidad, pagina_fuente=excluded.pagina_fuente, activo=1""",
                (r["codigo"], r["titulo"], r.get("aplica_a"), r["regla"], r["validacion"],
                 r["mensaje"], r.get("severidad", "BLOQUEO"), r.get("pagina_fuente")))
        conn.commit()
        if verboso:
            print("Sembrado: %d tipos de documento y %d reglas" % (len(TIPOS_DOCUMENTO), len(REGLAS_DOCUMENTO)))
    finally:
        conn.close()


def listar(ruta=None):
    conn = _conectar(ruta)
    try:
        print("TIPOS DE DOCUMENTO")
        for r in conn.execute("SELECT codigo, nombre, categoria, pagina_fuente FROM tipos_documento ORDER BY categoria, codigo"):
            print("  %-24s %-46s %s" % (r["codigo"], r["nombre"][:46], r["categoria"]))
        print("\nREGLAS")
        for r in conn.execute("SELECT codigo, titulo, severidad FROM reglas_documento ORDER BY codigo"):
            print("  %-9s %-58s %s" % (r["codigo"], r["titulo"][:58], r["severidad"]))
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description="Catálogo de documentos del SRI del simulador")
    p.add_argument("--listar", action="store_true")
    p.add_argument("--db", default=None)
    args = p.parse_args()
    aplicar(args.db)
    if args.listar:
        listar(args.db)
    else:
        sembrar(args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
