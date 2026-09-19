# -*- coding: utf-8 -*-
"""Esquema del módulo educativo del Simulador Contable (Contabilidad I).

Complementa el esquema base de `database/db_init.py` con las tablas que exige el
Prompt Maestro para el trabajo con estudiantes: actividades del syllabus, asignaciones
individuales, seguimiento de accesos, evidencias verificables y sus versiones.

Es idempotente: se puede ejecutar las veces que haga falta sobre una base ya creada.

Uso:
    python database/esquema_educativo.py          # aplica sobre la base configurada
    from database.esquema_educativo import aplicar; aplicar(ruta_db)
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config  # noqa: E402

SCHEMA_EDUCATIVO_SQL = """
-- ==========================================================================
--  MÓDULO EDUCATIVO — Contabilidad I (AUD ONLINE)
-- ==========================================================================

-- Actividades del syllabus, creadas por el docente.
CREATE TABLE IF NOT EXISTS actividades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,            -- U1-A1, U2-A2, U2-A3, U3-A4, U3-A5, U4-A6
    titulo TEXT NOT NULL,
    unidad INTEGER NOT NULL,                -- 1..4
    componente TEXT NOT NULL,               -- DOCENCIA | PRACTICA | AUTONOMO
    resultado_aprendizaje TEXT,
    instrucciones TEXT,
    evidencia_requerida TEXT,
    puntaje REAL DEFAULT 0,
    fecha_apertura TIMESTAMP,
    fecha_cierre TIMESTAMP,
    intentos_maximos INTEGER DEFAULT 1,
    modo_practica INTEGER DEFAULT 0,        -- 1 = oculta ayudas y clasificación ya resuelta
    tutor_ia INTEGER DEFAULT 0,             -- 1 = permite Tutor IA (nunca en evaluación)
    modulos_habilitados TEXT,               -- CSV: CUENTAS,DIARIO,MAYOR,BALANCE,ESTADOS
    tipo_evidencia TEXT,                    -- PLAN_CUENTAS | DIARIO | MAYOR | BALANCE | INTEGRAL
    estado TEXT DEFAULT 'BORRADOR',         -- BORRADOR | ABIERTA | CERRADA
    creada_por INTEGER,
    creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creada_por) REFERENCES usuarios(id)
);

-- Asignación de una actividad a un estudiante concreto (aislamiento individual).
CREATE TABLE IF NOT EXISTS asignaciones_actividad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actividad_id INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL,
    empresa_id INTEGER,
    estado TEXT DEFAULT 'PENDIENTE',        -- PENDIENTE | EN_CURSO | ENTREGADA | REVISADA
    intentos_usados INTEGER DEFAULT 0,
    abierta_en TIMESTAMP,
    cerrada_en TIMESTAMP,
    nota REAL,
    observacion_docente TEXT,
    asignada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (actividad_id, estudiante_id),
    FOREIGN KEY (actividad_id) REFERENCES actividades(id),
    FOREIGN KEY (estudiante_id) REFERENCES usuarios(id)
);

-- Sesiones de trabajo: permiten saber quién ingresó realmente y por cuánto tiempo.
CREATE TABLE IF NOT EXISTS sesiones_usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fin TIMESTAMP,
    duracion_seg INTEGER DEFAULT 0,
    ip_origen TEXT,
    navegador TEXT,
    activa INTEGER DEFAULT 1,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Eventos relevantes del estudiante (trazabilidad pedagógica, no vigilancia invasiva).
CREATE TABLE IF NOT EXISTS eventos_estudiante (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    empresa_id INTEGER,
    sesion_id INTEGER,
    actividad_id INTEGER,
    evento TEXT NOT NULL,                   -- LOGIN, LOGOUT, INICIO_ACTIVIDAD, CREAR_CUENTA, ...
    modulo TEXT,
    registro_id TEXT,
    detalle TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (sesion_id) REFERENCES sesiones_usuario(id)
);

-- Evidencias generadas por el estudiante, con código verificable por el docente.
CREATE TABLE IF NOT EXISTS evidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,            -- CONT1-B-2026-XXXXXXXX
    actividad_id INTEGER,
    estudiante_id INTEGER NOT NULL,
    empresa_id INTEGER,
    titulo TEXT NOT NULL,
    tipo TEXT,                              -- PLAN_CUENTAS | DIARIO | MAYOR | BALANCE | INTEGRAL
    resumen_texto TEXT,
    contenido_json TEXT,
    huella TEXT,                            -- SHA-256 del contenido al momento de finalizar
    estado TEXT DEFAULT 'BORRADOR',         -- BORRADOR | FINAL | INVALIDADA
    modificada_despues INTEGER DEFAULT 0,
    generada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES usuarios(id),
    FOREIGN KEY (actividad_id) REFERENCES actividades(id)
);

-- Historial de versiones de una evidencia.
CREATE TABLE IF NOT EXISTS versiones_evidencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidencia_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    contenido_json TEXT,
    huella TEXT,
    motivo TEXT,
    generada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evidencia_id) REFERENCES evidencias(id)
);

-- Índice de evidencias en la base de control: permite al docente verificar un código sin
-- abrir las 59 aulas, y saber en qué aula vive cada evidencia.
CREATE TABLE IF NOT EXISTS evidencias_indice (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    estudiante_id INTEGER,
    estudiante_username TEXT,
    paralelo TEXT,
    ruta_aula TEXT,
    actividad_codigo TEXT,
    titulo TEXT,
    tipo TEXT,
    estado TEXT,
    huella TEXT,
    modificada_despues INTEGER DEFAULT 0,
    generada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ficha de matrícula por estudiante: curso, paralelo y ruta de su aula.
CREATE TABLE IF NOT EXISTS aulas_estudiante (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER UNIQUE NOT NULL,
    username TEXT NOT NULL,
    paralelo TEXT,
    ruta_aula TEXT NOT NULL,
    plan_cuentas TEXT DEFAULT 'completo',
    creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_asig_estudiante ON asignaciones_actividad(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_asig_actividad ON asignaciones_actividad(actividad_id);
CREATE INDEX IF NOT EXISTS idx_eventos_usuario ON eventos_estudiante(usuario_id);
CREATE INDEX IF NOT EXISTS idx_eventos_evento ON eventos_estudiante(evento);
CREATE INDEX IF NOT EXISTS idx_sesiones_usuario ON sesiones_usuario(usuario_id);
CREATE INDEX IF NOT EXISTS idx_evidencias_estudiante ON evidencias(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_evidencias_codigo ON evidencias(codigo);
"""

# Columnas que se agregan a tablas existentes (multi-estudiante). Cada una se aplica
# solo si falta, porque SQLite no admite ADD COLUMN IF NOT EXISTS.
COLUMNAS_NUEVAS = [
    ("usuarios", "paralelo", "TEXT"),                 # A, B, C...
    ("usuarios", "matricula", "TEXT"),
    ("empresas", "estudiante_id", "INTEGER"),         # empresa simulada de cada estudiante
    ("empresas", "es_demo", "INTEGER DEFAULT 0"),
    ("impuestos", "es_demo", "INTEGER DEFAULT 0"),
]


def _columnas_existentes(conn, tabla):
    filas = conn.execute("PRAGMA table_info(%s)" % tabla).fetchall()
    return {f[1] for f in filas}


def aplicar(db_path=None, verboso=True):
    """Crea las tablas del módulo educativo y agrega las columnas que falten."""
    if db_path is None:
        db_path = Config.DATABASE_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_EDUCATIVO_SQL)
        for tabla, columna, tipo in COLUMNAS_NUEVAS:
            try:
                existentes = _columnas_existentes(conn, tabla)
            except sqlite3.Error:
                continue
            if columna not in existentes:
                conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (tabla, columna, tipo))
                if verboso:
                    print("   + columna %s.%s" % (tabla, columna))
        conn.commit()
        tablas = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        nuevas = [t for t in ("actividades", "asignaciones_actividad", "sesiones_usuario",
                              "eventos_estudiante", "evidencias", "versiones_evidencia")
                  if t in tablas]
        if verboso:
            print("Módulo educativo aplicado en %s (%d tablas presentes: %s)"
                  % (db_path, len(nuevas), ", ".join(nuevas)))
        return nuevas
    finally:
        conn.close()


if __name__ == "__main__":
    aplicar()
