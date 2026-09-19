# -*- coding: utf-8 -*-
"""Esquema y siembra del BANCO DE CASOS PRÁCTICOS DE LOS LIBROS (§61) y de las reglas de
trazabilidad de las fuentes (§62) del Prompt Maestro v2.

Vive en la base de CONTROL (`database/simulator.db`), porque es contenido académico
compartido: el catálogo de casos, su ficha de trazabilidad, las reglas §62 y los intentos de
los estudiantes (el aula de cada estudiante conserva su trabajo contable).

Tablas
------
casos_libros_fuentes      fuentes de los libros con su correlación de páginas y contexto (§62.6/62.7)
casos_libros              los 19 casos de §61 con su ficha completa (§62.9) y su payload JSON
casos_libros_trazabilidad correcciones de erratas, etiquetas de fidelidad y reglas aplicadas
casos_libros_reglas       las reglas §62 como DATOS (§62.1 – §62.9)
casos_libros_intentos     intentos de los estudiantes con su verificación y su puntaje

Es IDEMPOTENTE: se puede ejecutar las veces que haga falta.

Uso:
    python database/esquema_casos_libros.py                 # aplica y siembra sobre la base configurada
    from database.esquema_casos_libros import aplicar, sembrar; aplicar(ruta); sembrar(ruta)
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config                                            # noqa: E402
from database.banco_casos_libros import (                            # noqa: E402
    CAMPOS_FICHA_OBLIGATORIOS, ERRATAS_PLAN_CUENTAS, ETIQUETA_RECONSTRUIDO, FUENTES,
    MODOS_CATALOGO, REGLAS_TRAZABILIDAD, cita_fuente,
)
from database.casos_libros_61 import CASOS                           # noqa: E402

SCHEMA_CASOS_LIBROS_SQL = """
-- ==========================================================================
--  BANCO DE CASOS PRÁCTICOS DE LOS LIBROS (§61) Y TRAZABILIDAD (§62)
-- ==========================================================================

-- Fuentes de los libros, con su correlación de páginas (§62.7) y su contexto (§62.3/§62.6).
CREATE TABLE IF NOT EXISTS casos_libros_fuentes (
    codigo TEXT PRIMARY KEY,                -- U2 | U3 | U4 | SENA
    nombre TEXT NOT NULL,
    edicion TEXT,
    anio TEXT,
    tipo TEXT,
    pais_contexto TEXT,                     -- permite advertir el marco extranjero o histórico
    correlacion_paginas TEXT,               -- §62.7: impresa = PDF − 19, etc.
    paginas_sin_texto TEXT,                 -- §62.4: páginas que eran imagen y no pudieron validarse
    erratas_conocidas TEXT,                 -- JSON
    notas TEXT,                             -- JSON
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Los 19 casos de §61. El payload completo viaja en JSON; las columnas permiten filtrar y
-- exigir la ficha obligatoria de §62.9 antes de activar un caso.
CREATE TABLE IF NOT EXISTS casos_libros (
    codigo TEXT PRIMARY KEY,                -- C61.01 … C61.19
    numero INTEGER NOT NULL,                -- 1..19 (orden de §61)
    nombre TEXT NOT NULL,
    unidad INTEGER,
    tipo TEXT,
    dificultad TEXT,
    fuente_codigo TEXT,                     -- ficha §62.9: fuente completa
    fuente_nombre TEXT,
    paginas_impresas TEXT,                  -- ficha §62.9: página
    paginas_pdf TEXT,                       -- §62.7: doble numeración
    cita_fuente TEXT,                       -- cita lista para mostrar (impresa + PDF)
    anio TEXT,                              -- ficha §62.9: año
    estado_validacion TEXT,                 -- VERIFICADO | VERIFICADO_CON_RESERVA | SIN_SOLUCION | CON_ERRATA | PARCIAL_CON_ERRATA
    solucion_en_fuente INTEGER DEFAULT 0,   -- ficha §62.9: ¿la solución está en la fuente?
    solucion_visible INTEGER DEFAULT 0,     -- §62.5: ¿puede mostrarse al estudiante?
    hubo_correccion INTEGER DEFAULT 0,      -- ficha §62.9: ¿se corrigieron erratas?
    tipo_verificacion TEXT,                 -- ASIENTO | TOTALES | ECUACION | MECANICA
    intentos_maximos INTEGER DEFAULT 3,
    puntaje REAL DEFAULT 10,
    publicable INTEGER DEFAULT 1,           -- permite activarlo para estudiantes
    activo INTEGER DEFAULT 1,
    contexto_normativo TEXT,                -- §62.6
    enunciado TEXT,
    datos_json TEXT,
    asientos_esperados_json TEXT,
    saldos_finales_json TEXT,
    totales_verificados_json TEXT,
    solucion_json TEXT,
    correcciones_json TEXT,                 -- §62.1: valor del libro, valor corregido y razón
    etiquetas_json TEXT,                    -- §62.4: «dato reconstruido…»
    advertencias_json TEXT,
    extra_json TEXT,                        -- subcasos, contenido publicable, parámetros del caso
    cargado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fuente_codigo) REFERENCES casos_libros_fuentes(codigo)
);

-- Ficha de trazabilidad: una fila por corrección, etiqueta, advertencia o regla aplicada.
CREATE TABLE IF NOT EXISTS casos_libros_trazabilidad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caso_codigo TEXT NOT NULL,
    tipo TEXT NOT NULL,                     -- FICHA | CORRECCION | ETIQUETA | ADVERTENCIA | REGLA
    regla_codigo TEXT,                      -- R62.1 … R62.9
    campo TEXT,
    valor_libro TEXT,                       -- lo que dice la fuente
    valor_aplicado TEXT,                    -- lo que aplica el simulador
    razon TEXT,
    registrado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (caso_codigo) REFERENCES casos_libros(codigo)
);

-- Las reglas §62 como DATOS consultables desde la interfaz y desde las pruebas.
CREATE TABLE IF NOT EXISTS casos_libros_reglas (
    codigo TEXT PRIMARY KEY,                -- R62.1 … R62.9
    numero INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    texto_fuente TEXT NOT NULL,
    trazabilidad_fuentes INTEGER DEFAULT 1,
    aplicacion TEXT,
    verificable INTEGER DEFAULT 1
);

-- Intentos de los estudiantes: verificación, puntaje y trazabilidad del intento.
CREATE TABLE IF NOT EXISTS casos_libros_intentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caso_codigo TEXT NOT NULL,
    estudiante_id INTEGER NOT NULL,
    numero_intento INTEGER NOT NULL,
    estado TEXT DEFAULT 'EN_PROCESO',       -- EN_PROCESO | EVALUADO | ANULADO
    respuesta_json TEXT,
    puntuacion REAL,
    resultado TEXT,                         -- CORRECTO | PARCIALMENTE_CORRECTO | INCORRECTO
    oficial INTEGER DEFAULT 0,              -- 1 solo si la fuente trae solución válida
    requiere_revision_docente INTEGER DEFAULT 0,
    verificacion_json TEXT,
    retroalimentacion TEXT,
    iniciado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finalizado_en TIMESTAMP,
    UNIQUE (caso_codigo, estudiante_id, numero_intento),
    FOREIGN KEY (caso_codigo) REFERENCES casos_libros(codigo)
);

CREATE INDEX IF NOT EXISTS idx_casos_libros_estado ON casos_libros(estado_validacion);
CREATE INDEX IF NOT EXISTS idx_casos_libros_unidad ON casos_libros(unidad);
CREATE INDEX IF NOT EXISTS idx_casos_traz_caso ON casos_libros_trazabilidad(caso_codigo);
CREATE INDEX IF NOT EXISTS idx_casos_intentos_est ON casos_libros_intentos(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_casos_intentos_caso ON casos_libros_intentos(caso_codigo);
"""


def _json(valor):
    return json.dumps(valor if valor is not None else [], ensure_ascii=False)


def _conectar(db_path=None):
    ruta = db_path or Config.DATABASE_PATH
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    conn = sqlite3.connect(ruta, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def aplicar(db_path=None, verboso=True):
    """Crea (si faltan) las tablas del banco de casos y de las reglas §62."""
    conn = _conectar(db_path)
    try:
        conn.executescript(SCHEMA_CASOS_LIBROS_SQL)
        conn.commit()
        tablas = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'casos_libros%' "
            "ORDER BY name").fetchall()]
        if verboso:
            print("Banco de casos §61 aplicado en %s (%d tablas: %s)"
                  % (db_path or Config.DATABASE_PATH, len(tablas), ", ".join(tablas)))
        return tablas
    finally:
        conn.close()


def ficha_incompleta(caso):
    """§62.9 — devuelve la lista de campos obligatorios que faltan en la ficha de un caso."""
    faltantes = [campo for campo in CAMPOS_FICHA_OBLIGATORIOS if not caso.get(campo) and caso.get(campo) != 0]
    if caso.get("estado_validacion") == "CON_ERRATA" and not caso.get("correcciones"):
        faltantes.append("correcciones (errata sin corregir y sin razón registrada)")
    return faltantes


def _filas_trazabilidad(caso, ficha_fuente):
    """Construye las filas de la ficha de trazabilidad de un caso (§62.1, §62.4, §62.9)."""
    filas = []
    detalle = {
        "fuente": ficha_fuente.get("nombre"),
        "pagina_impresa": caso.get("paginas_impresas"),
        "pagina_pdf": caso.get("paginas_pdf"),
        "anio": caso.get("anio"),
        "solucion_en_fuente": bool(caso.get("solucion_en_fuente")),
        "correccion_de_erratas": bool(caso.get("correcciones")),
    }
    filas.append(("FICHA", "R62.9", "ficha del caso", None,
                  _json(detalle),
                  "Fuente completa, página (doble numeración), año, si la solución está en la fuente y si "
                  "hubo corrección de erratas."))
    for correccion in caso.get("correcciones") or []:
        filas.append(("CORRECCION", "R62.1", correccion.get("campo"),
                      correccion.get("valor_libro"), correccion.get("valor_corregido"),
                      correccion.get("razon")))
    for etiqueta in caso.get("etiquetas") or []:
        filas.append(("ETIQUETA", "R62.4", "etiqueta de fidelidad", etiqueta, etiqueta,
                      "Cifra reconstruida o calculada: no puede usarse como respuesta oficial de una "
                      "actividad evaluable."))
    if ETIQUETA_RECONSTRUIDO in (caso.get("etiquetas") or []):
        publicable = caso.get("contenido_publicable") or []
        filas.append(("REGLA", "R62.4", "contenido reconstruido",
                      "detalle completo del caso en la fuente",
                      "publicable: %s" % (", ".join(publicable) if publicable
                                          else "solo las cifras verificadas contra los totales del libro"),
                      "Toda cifra reconstruida se etiqueta «%s» y no puede usarse como respuesta "
                      "oficial de una actividad evaluable." % ETIQUETA_RECONSTRUIDO))
    for advertencia in caso.get("advertencias") or []:
        filas.append(("ADVERTENCIA", "R62.4", "advertencia", None, advertencia, None))
    if not caso.get("solucion_en_fuente"):
        filas.append(("REGLA", "R62.5", "solución", "publicada en la fuente: no",
                      "práctica sin solución visible",
                      "El sistema no presenta como resuelto ningún ejercicio cuya solución no esté en la fuente."))
    if caso.get("contexto_normativo") and any(
            palabra in caso["contexto_normativo"].upper()
            for palabra in ("EXTRANJERO", "ESTADOS UNIDOS", "COLOMBIA")):
        filas.append(("REGLA", "R62.6", "contexto normativo", caso.get("fuente"),
                      caso.get("contexto_normativo"),
                      "Marco normativo extranjero o histórico: se usa como modelo visual y sus cifras se "
                      "muestran en formato es-EC."))
    filas.append(("REGLA", "R62.7", "páginas",
                  caso.get("paginas_impresas"), caso.get("cita_fuente"),
                  ficha_fuente.get("correlacion_paginas")))
    return filas


def sembrar(db_path=None, verboso=True):
    """Carga fuentes, reglas §62 y los 19 casos con su ficha de trazabilidad (idempotente)."""
    conn = _conectar(db_path)
    try:
        for codigo, ficha in FUENTES.items():
            conn.execute("""
                INSERT INTO casos_libros_fuentes
                    (codigo, nombre, edicion, anio, tipo, pais_contexto, correlacion_paginas,
                     paginas_sin_texto, erratas_conocidas, notas, actualizado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(codigo) DO UPDATE SET
                    nombre = excluded.nombre, edicion = excluded.edicion, anio = excluded.anio,
                    tipo = excluded.tipo, pais_contexto = excluded.pais_contexto,
                    correlacion_paginas = excluded.correlacion_paginas,
                    paginas_sin_texto = excluded.paginas_sin_texto,
                    erratas_conocidas = excluded.erratas_conocidas, notas = excluded.notas,
                    actualizado_en = CURRENT_TIMESTAMP
            """, (codigo, ficha["nombre"], ficha.get("edicion"), ficha.get("anio"), ficha.get("tipo"),
                  ficha.get("pais_contexto"), ficha.get("correlacion_paginas"),
                  ficha.get("paginas_sin_texto"), _json(ficha.get("erratas_conocidas")),
                  _json(ficha.get("notas"))))

        # Las erratas de §59.10 también son erratas de trazabilidad del plan de cuentas.
        conn.execute("DELETE FROM casos_libros_reglas WHERE codigo LIKE 'E59.%'")
        for errata in ERRATAS_PLAN_CUENTAS:
            conn.execute("""
                INSERT INTO casos_libros_reglas (codigo, numero, titulo, texto_fuente,
                                                 trazabilidad_fuentes, aplicacion, verificable)
                VALUES (?, ?, ?, ?, 1, ?, 1)
            """, ("E59.%d" % errata["numero"], errata["numero"],
                  "Errata §59.10 n.º %d" % errata["numero"], errata["errata"],
                  "%s → %s" % (errata["fuente"], errata["regla"])))

        for regla in REGLAS_TRAZABILIDAD:
            conn.execute("""
                INSERT INTO casos_libros_reglas (codigo, numero, titulo, texto_fuente,
                                                 trazabilidad_fuentes, aplicacion, verificable)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo) DO UPDATE SET
                    numero = excluded.numero, titulo = excluded.titulo,
                    texto_fuente = excluded.texto_fuente,
                    trazabilidad_fuentes = excluded.trazabilidad_fuentes,
                    aplicacion = excluded.aplicacion, verificable = excluded.verificable
            """, (regla["codigo"], regla["numero"], regla["titulo"], regla["texto_fuente"],
                  1 if regla["trazabilidad_fuentes"] else 0, regla["aplicacion"],
                  1 if regla["verificable"] else 0))

        for indice, caso in enumerate(CASOS, start=1):
            ficha_fuente = FUENTES.get(caso["fuente"], {})
            numero = int(caso["codigo"].split(".")[-1])
            faltantes = ficha_incompleta(dict(caso, fuente_codigo=caso.get("fuente"),
                                              fuente_nombre=ficha_fuente.get("nombre")))
            publicable = 1 if not faltantes else 0
            extra = {
                "subcasos": caso.get("subcasos") or [],
                "contenido_publicable": caso.get("contenido_publicable") or [],
                "parametros_caso": caso.get("parametros_caso") or {},
                "filas_excluidas": caso.get("filas_excluidas") or [],
                "solucion_referencial": caso.get("solucion_referencial") or {},
                "dificultad": caso.get("dificultad"),
                "tipo": caso.get("tipo"),
                "ficha_incompleta": faltantes,
            }
            conn.execute("""
                INSERT INTO casos_libros
                    (codigo, numero, nombre, unidad, tipo, dificultad, fuente_codigo, fuente_nombre,
                     paginas_impresas, paginas_pdf, cita_fuente, anio, estado_validacion,
                     solucion_en_fuente, solucion_visible, hubo_correccion, tipo_verificacion,
                     intentos_maximos, puntaje, publicable, activo, contexto_normativo, enunciado,
                     datos_json, asientos_esperados_json, saldos_finales_json, totales_verificados_json,
                     solucion_json, correcciones_json, etiquetas_json, advertencias_json, extra_json,
                     cargado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(codigo) DO UPDATE SET
                    numero = excluded.numero, nombre = excluded.nombre, unidad = excluded.unidad,
                    tipo = excluded.tipo, dificultad = excluded.dificultad,
                    fuente_codigo = excluded.fuente_codigo, fuente_nombre = excluded.fuente_nombre,
                    paginas_impresas = excluded.paginas_impresas, paginas_pdf = excluded.paginas_pdf,
                    cita_fuente = excluded.cita_fuente, anio = excluded.anio,
                    estado_validacion = excluded.estado_validacion,
                    solucion_en_fuente = excluded.solucion_en_fuente,
                    solucion_visible = excluded.solucion_visible,
                    hubo_correccion = excluded.hubo_correccion,
                    tipo_verificacion = excluded.tipo_verificacion,
                    intentos_maximos = excluded.intentos_maximos, puntaje = excluded.puntaje,
                    publicable = excluded.publicable, contexto_normativo = excluded.contexto_normativo,
                    enunciado = excluded.enunciado, datos_json = excluded.datos_json,
                    asientos_esperados_json = excluded.asientos_esperados_json,
                    saldos_finales_json = excluded.saldos_finales_json,
                    totales_verificados_json = excluded.totales_verificados_json,
                    solucion_json = excluded.solucion_json,
                    correcciones_json = excluded.correcciones_json,
                    etiquetas_json = excluded.etiquetas_json,
                    advertencias_json = excluded.advertencias_json, extra_json = excluded.extra_json,
                    cargado_en = CURRENT_TIMESTAMP
            """, (
                caso["codigo"], numero, caso["nombre"], caso.get("unidad"), caso.get("tipo"),
                caso.get("dificultad"), caso.get("fuente"), ficha_fuente.get("nombre"),
                caso.get("paginas_impresas"), "", "",
                str(caso.get("anio") or ""), caso.get("estado_validacion"),
                1 if caso.get("solucion_en_fuente") else 0,
                1 if caso.get("solucion_visible") else 0,
                1 if caso.get("correcciones") else 0,
                caso.get("tipo_verificacion"), int(caso.get("intentos_maximos") or 3),
                float(caso.get("puntaje") or 10), publicable,
                caso.get("contexto_normativo"), caso.get("enunciado"),
                _json(caso.get("datos")), _json(caso.get("asientos_esperados")),
                _json(caso.get("saldos_finales")), _json(caso.get("totales_verificados")),
                _json(caso.get("solucion")), _json(caso.get("correcciones")),
                _json(caso.get("etiquetas")), _json(caso.get("advertencias")), _json(extra),
            ))

            # Doble numeración (§62.7) y cita lista para la ficha.
            cita = cita_fuente(caso["fuente"], caso["paginas_impresas"])
            conn.execute("UPDATE casos_libros SET cita_fuente = ?, paginas_pdf = ? WHERE codigo = ?",
                         (cita, cita.split("(")[-1].split(")")[0] if "(" in cita else "",
                          caso["codigo"]))

            conn.execute("DELETE FROM casos_libros_trazabilidad WHERE caso_codigo = ?", (caso["codigo"],))
            caso_con_cita = dict(caso, paginas_pdf="", cita_fuente=cita)
            for fila in _filas_trazabilidad(caso_con_cita, ficha_fuente):
                conn.execute("""
                    INSERT INTO casos_libros_trazabilidad
                        (caso_codigo, tipo, regla_codigo, campo, valor_libro, valor_aplicado, razon)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (caso["codigo"], fila[0], fila[1], fila[2], fila[3], fila[4], fila[5]))

        conn.commit()
        total = conn.execute("SELECT COUNT(*) AS n FROM casos_libros").fetchone()["n"]
        if verboso:
            print("Banco de casos: %d fuentes, %d reglas §62, %d casos cargados en %s"
                  % (len(FUENTES), len(REGLAS_TRAZABILIDAD), total,
                     db_path or Config.DATABASE_PATH))
        return {"fuentes": len(FUENTES), "reglas": len(REGLAS_TRAZABILIDAD), "casos": total}
    finally:
        conn.close()


def descripcion_modos_catalogo():
    """§62.8 — los tres modos de catálogo de cuentas autorizados por la sección 14."""
    return list(MODOS_CATALOGO)


if __name__ == "__main__":
    aplicar(verboso=True)
    sembrar(verboso=True)
