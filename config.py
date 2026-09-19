"""
Configuración central del Simulador Integral de Sistema Contable.

Todos los valores sensibles o dependientes del entorno se leen de variables de entorno,
de modo que la misma aplicación sirva para uso local y para un despliegue 24/7:

    SECRET_KEY              clave de firma de sesiones (obligatoria en producción)
    DATABASE_PATH           ruta del archivo SQLite (use un disco persistente en hosting)
    HOST / PORT             dirección y puerto del servidor
    SIMULADOR_DEBUG         "1" activa el modo desarrollo (recarga automática)
    SESSION_COOKIE_SECURE   "1" cuando el sitio se sirve por HTTPS
    SESSION_COOKIE_SAMESITE Lax (por defecto) | Strict | None
    SESSION_HORAS           duración de la sesión en horas (8 por defecto)
    THREADS                 hilos del servidor de producción (8 por defecto)

Ver docs/DESPLIEGUE.md para el procedimiento completo.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def cargar_env(ruta=None):
    """Carga las variables de un archivo .env, sin dependencias externas.

    El entorno REAL siempre manda: los valores ya definidos no se sobrescriben, así
    que en producción (/etc/simulador/secrets.env, panel del hosting) el .env se
    ignora. Sirve para desarrollo local: copie .env.example como .env y ajuste.
    """
    ruta = ruta or os.path.join(BASE_DIR, ".env")
    if not os.path.exists(ruta):
        return 0
    cargadas = 0
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            if clave and clave not in os.environ:
                os.environ[clave] = valor
                cargadas += 1
    return cargadas


cargar_env()


def _bool_env(nombre, por_defecto=False):
    """Lee una variable de entorno booleana admitiendo 1/true/si/on."""
    valor = os.environ.get(nombre)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in ("1", "true", "yes", "si", "sí", "on")


class Config:
    # ------------------------------------------------------------------ Seguridad
    # En producción SIEMPRE defina SECRET_KEY en el entorno: si se usa el valor por
    # defecto, las sesiones no son seguras. El arranque avisa de esta situación.
    SECRET_KEY_POR_DEFECTO = "simulador-contable-secret-key-2026-prod"
    SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY_POR_DEFECTO)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _bool_env("SESSION_COOKIE_SECURE", False)
    # Permite aislar las sesiones cuando varias instancias (aulas) comparten dominio
    # y solo se diferencian por el puerto: las cookies NO distinguen puertos.
    SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "session")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get("SESSION_HORAS", "8")))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_MB", "16")) * 1024 * 1024

    # ----------------------------------------------------------------- Base de datos
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or os.path.join(
        BASE_DIR, "database", "simulator.db"
    )

    # ------------------------------------------------------------------ Aulas
    # Un aula (base de datos propia) por estudiante. Cuando el modo multiestudiante está
    # activo, cada estudiante trabaja en su archivo y la base de control conserva usuarios,
    # roles, cursos y la definición de las actividades del syllabus.
    MULTIESTUDIANTE = _bool_env("SIMULADOR_MULTIESTUDIANTE", True)
    RUTA_AULAS = os.environ.get("RUTA_AULAS") or os.path.join(BASE_DIR, "database", "aulas")
    RUTA_PLANTILLA = os.environ.get("RUTA_PLANTILLA") or os.path.join(
        BASE_DIR, "database", "plantilla", "aula_base.db"
    )

    # ---------------------------------------------------------------------- Servidor
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DEBUG = _bool_env("SIMULADOR_DEBUG", False)

    # ----------------------------------------------------------------------- Empresa
    COMPANY_NAME = "Comercial y Servicios Nueva Esperanza"
    COMPANY_RUC = "1792345678001"
    APP_NAME = "Simulador Integral de Sistema Contable"
    APP_SUBTITLE = "Servicios y Comercialización de Productos"
