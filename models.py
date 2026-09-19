import sqlite3
import os
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config


def ruta_aula(username, paralelo=None):
    """Devuelve la ruta del aula (base de datos propia) de un estudiante.

    Estructura: database/aulas/<PARALELO>/<usuario>.db   (sin paralelo: database/aulas/<usuario>.db)
    """
    usuario = (username or "").strip().lower()
    if not usuario:
        return None
    carpeta = Config.RUTA_AULAS
    if paralelo:
        carpeta = os.path.join(carpeta, str(paralelo).strip().upper())
    return os.path.join(carpeta, "%s.db" % usuario)


def existe_aula(username, paralelo=None):
    ruta = ruta_aula(username, paralelo)
    return bool(ruta) and os.path.exists(ruta)


def _crear_conexion(db_path):
    conn = sqlite3.connect(db_path, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db_control(db_path=None):
    """Base de CONTROL: usuarios, roles, cursos, matrículas, actividades y el índice de evidencias."""
    if db_path is None:
        db_path = Config.DATABASE_PATH
    return _crear_conexion(db_path)


def get_db_connection(db_path=None):
    """Se mantiene por compatibilidad: sin argumentos devuelve la base de control.

    Para el trabajo contable del estudiante use `get_db_contable()`.
    """
    return get_db_control(db_path)


def get_db_contable(db_path=None):
    """Base donde vive el trabajo del usuario en sesión.

    - Estudiante con aula propia  -> su archivo (aislamiento total).
    - Docente, administrador, auditor o sesión anónima -> base de control (empresa demostrativa).
    - Modo multiestudiante desactivado -> base de control, como siempre.
    """
    if db_path is not None:
        return _crear_conexion(db_path)
    if not Config.MULTIESTUDIANTE:
        return get_db_control()
    aula = aula_actual()
    if aula and os.path.exists(aula):
        return _crear_conexion(aula)
    return get_db_control()


def aula_actual():
    """Ruta del aula del usuario en sesión, o None si no aplica (sin contexto, docente, demo)."""
    try:
        from flask import has_request_context, session
    except ImportError:  # fuera de una petición (scripts, pruebas)
        return None
    if not has_request_context():
        return None
    if (session.get("user_role") or "") != "Estudiante":
        return None
    username = session.get("username")
    if not username:
        return None
    paralelo = session.get("paralelo")
    ruta = ruta_aula(username, paralelo)
    if ruta and os.path.exists(ruta):
        return ruta
    # El usuario existe pero aún no tiene aula creada: se busca sin paralelo.
    alternativa = ruta_aula(username, None)
    if alternativa and os.path.exists(alternativa):
        return alternativa
    return None


def esta_en_aula_propia():
    """True cuando el trabajo del usuario está aislado en su propia aula."""
    return aula_actual() is not None


@contextmanager
def db_session(db_path=None):
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


@contextmanager
def db_sesion_contable(db_path=None):
    """Igual que `db_session` pero resolviendo el aula del usuario en sesión."""
    conn = get_db_contable(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def dict_from_row(row):
    if row is None:
        return None
    return dict(row)


def dicts_from_rows(rows):
    return [dict(r) for r in rows]
