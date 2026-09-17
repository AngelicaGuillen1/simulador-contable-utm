# ---------------------------------------------------------------------------
#  Archivo WSGI para PythonAnywhere (plan gratuito, URL publica sin Hostinger).
#
#  Como usarlo:
#   1. Cree una cuenta en pythonanywhere.com (plan "Beginner", gratuito).
#   2. Abra una consola Bash y suba el proyecto:
#         git clone https://github.com/AngelicaGuillen1/simulador-contable-utm.git
#         cd simulador-contable-utm
#         python3.10 -m venv .venv && source .venv/bin/activate
#         pip install -r requirements.txt
#         python database/seed_data.py
#   3. Web -> Add a new web app -> Manual configuration -> Python 3.10
#   4. En "Virtualenv", escriba:  /home/USUARIO/simulador-contable-utm/.venv
#   5. En "WSGI configuration file", pegue TODO el contenido de este archivo
#      (reemplace USUARIO y el nombre de la carpeta si son distintos).
#   6. Pulse "Reload" y abra https://USUARIO.pythonanywhere.com
#
#  Antes de usarlo en clase: cambie las contrasenas demo con
#      python deploy/cambiar_credenciales.py
# ---------------------------------------------------------------------------

import os
import sys

# --- 1. Ajuste estas dos rutas -------------------------------------------------
USUARIO = "USUARIO"                              # su usuario de PythonAnywhere
PROYECTO = f"/home/{USUARIO}/simulador-contable-utm"
# ------------------------------------------------------------------------------

if PROYECTO not in sys.path:
    sys.path.insert(0, PROYECTO)

# El proyecto usa rutas relativas a su raíz (templates, static, docs, base de datos)
os.chdir(PROYECTO)

# --- 2. Configuración por variables de entorno --------------------------------
os.environ.setdefault("SECRET_KEY", "CAMBIA-ESTA-CLAVE-POR-UNA-ALEATORIA-LARGA")
os.environ.setdefault("DATABASE_PATH", os.path.join(PROYECTO, "database", "simulator.db"))
os.environ.setdefault("SESSION_COOKIE_SECURE", "true")   # PythonAnywhere sirve por HTTPS
os.environ.setdefault("SIMULADOR_DEBUG", "0")

# --- 3. Aplicación -------------------------------------------------------------
from app import create_app  # noqa: E402

application = create_app()
