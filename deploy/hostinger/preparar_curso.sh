#!/usr/bin/env bash
# =============================================================================
#  Carga el CURSO en el VPS: los 59 estudiantes del paralelo B y sus aulas.
#
#  Se ejecuta DESPUÉS de instalar_vps.sh, con el CSV de credenciales subido al
#  servidor. Respeta las claves que trae el CSV, así que el servidor queda con
#  EXACTAMENTE las claves de la lista que se entrega a los estudiantes.
#
#  Uso (dentro del VPS, como root):
#     sudo bash preparar_curso.sh --csv /root/credenciales_paralelo_B.csv
#
#  Opciones:
#     --csv RUTA        CSV con columnas usuario, nombre, cedula, correo, password_inicial
#     --ruta RUTA       carpeta del proyecto (por defecto /opt/simulador)
#     --datos RUTA      carpeta de datos      (por defecto /var/datos)
#     --usuario USUARIO usuario de servicio   (por defecto simulador)
#     --paralelo LETRA  paralelo (por defecto lo que traiga el CSV, o B)
# =============================================================================
set -euo pipefail

PROYECTO_DIR="/opt/simulador"
DATOS_DIR="/var/datos"
USUARIO="simulador"
CSV=""
PARALELO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --csv) CSV="${2:-}"; shift 2 ;;
    --ruta) PROYECTO_DIR="${2:-}"; shift 2 ;;
    --datos) DATOS_DIR="${2:-}"; shift 2 ;;
    --usuario) USUARIO="${2:-}"; shift 2 ;;
    --paralelo) PARALELO="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $1"; exit 1 ;;
  esac
done

azul()   { printf '\033[1;34m%s\033[0m\n' "$*"; }
verde()  { printf '\033[1;32m%s\033[0m\n' "$*"; }
rojo()   { printf '\033[1;31m%s\033[0m\n' "$*"; }

if [[ $EUID -ne 0 ]]; then
  rojo "Ejecútelo como root:  sudo bash preparar_curso.sh --csv /root/credenciales.csv"
  exit 1
fi
if [[ -z "$CSV" || ! -f "$CSV" ]]; then
  rojo "Falta --csv o el archivo no existe: $CSV"
  exit 1
fi
if [[ ! -x "$PROYECTO_DIR/.venv/bin/python" ]]; then
  rojo "No encuentro el proyecto instalado en $PROYECTO_DIR (ejecute antes instalar_vps.sh)"
  exit 1
fi

ENTORNO="DATABASE_PATH=$DATOS_DIR/simulator.db RUTA_AULAS=$DATOS_DIR/aulas RUTA_PLANTILLA=$DATOS_DIR/plantilla/aula_base.db"
PY="$PROYECTO_DIR/.venv/bin/python"

# El usuario de servicio NO puede leer /root (permisos 700): si el CSV está ahí,
# se copia a la carpeta de datos, que sí es accesible.
CSV_ACCESIBLE="$CSV"
if ! sudo -u "$USUARIO" test -r "$CSV"; then
  CSV_ACCESIBLE="$DATOS_DIR/$(basename "$CSV")"
  cp "$CSV" "$CSV_ACCESIBLE"
  chown "$USUARIO:$USUARIO" "$CSV_ACCESIBLE"
  chmod 600 "$CSV_ACCESIBLE"
  verde "    CSV copiado a $CSV_ACCESIBLE (el usuario $USUARIO no puede leer $CSV)"
fi

# ---- 1) Usuarios + aulas (respetando las claves del CSV) --------------------
azul "==> 1/5 Cargando estudiantes y creando sus aulas"
PARAM_PARALELO=()
[[ -n "$PARALELO" ]] && PARAM_PARALELO=(--paralelo "$PARALELO")
sudo -u "$USUARIO" env $ENTORNO "$PY" "$PROYECTO_DIR/database/importar_nomina.py" \
  --nomina "$CSV_ACCESIBLE" --credenciales "$DATOS_DIR/credenciales_aplicadas.csv" "${PARAM_PARALELO[@]}"

# ---- 2) Catálogo tributario oficial en TODAS las bases (control, plantilla y aulas)
# Las aulas se clonan de la plantilla que crea el instalador; si esa plantilla trae el
# catálogo heredado del seed (1,75 % / 2,75 %), las compras retendrían con tasas viejas.
azul "==> 2/6 Aplicando el catálogo tributario del SRI (IVA y retenciones)"
sudo -u "$USUARIO" env $ENTORNO "$PY" "$PROYECTO_DIR/database/parametros_tributarios_sri.py" \
  --todas-las-aulas | tail -3

# ---- 3) Simulador de práctica en las aulas ---------------------------------
azul "==> 3/6 Sembrando el simulador de práctica (niveles y casos)"
sudo -u "$USUARIO" env $ENTORNO "$PY" "$PROYECTO_DIR/database/sembrar_simulaciones.py" | tail -2

# ---- 4) Actividades del sílabo (las 6 tareas de la asignatura) --------------
azul "==> 4/6 Cargando las actividades del sílabo y asignándolas"
if sudo -u "$USUARIO" env $ENTORNO "$PY" "$PROYECTO_DIR/database/seed_actividades.py" --todos \
     >/tmp/actividades.log 2>&1; then
  verde "    Actividades cargadas (detalle en /tmp/actividades.log)"
else
  rojo "    No se pudieron cargar las actividades. Revise /tmp/actividades.log"
fi

# ---- 5) Reinicio del servicio ----------------------------------------------
azul "==> 5/6 Reiniciando el servicio"
systemctl restart simulador-contable
sleep 5

# ---- 6) Comprobación --------------------------------------------------------
azul "==> 6/6 Comprobación"
sudo -u "$USUARIO" env $ENTORNO PROYECTO_DIR="$PROYECTO_DIR" "$PY" - <<'PYFIN'
import glob, os, sqlite3, sys
sys.path.insert(0, os.environ.get("PROYECTO_DIR", "/opt/simulador"))
from config import Config

control = sqlite3.connect(Config.DATABASE_PATH)
estudiantes = control.execute(
    "SELECT COUNT(*) FROM usuarios WHERE paralelo IS NOT NULL AND paralelo <> ''").fetchone()[0]
con_aula = 0
sin_datos = 0
for ruta in glob.glob(os.path.join(Config.RUTA_AULAS, "*", "*.db")):
    con_aula += 1
    c = sqlite3.connect(ruta)
    asientos = c.execute("SELECT COUNT(*) FROM asientos").fetchone()[0]
    niveles = c.execute("SELECT COUNT(*) FROM simulaciones").fetchone()[0]
    if asientos == 0 and niveles == 4:
        sin_datos += 1
    c.close()
print("   estudiantes registrados : %d" % estudiantes)
print("   aulas creadas           : %d" % con_aula)
print("   aulas listas para el curso (0 asientos y 4 niveles): %d" % sin_datos)
print("   plantilla de aulas      : %s" % ("sí" if os.path.exists(Config.RUTA_PLANTILLA) else "NO"))
PYFIN

echo
verde "=============================================================================="
verde " CURSO CARGADO"
echo "   Estudiantes y aulas listos. Cada estudiante entra con su correo institucional."
echo "   Credenciales aplicadas: $DATOS_DIR/credenciales_aplicadas.csv"
echo "   Salud del servicio    : curl -s http://127.0.0.1:8080/api/health"
echo "   Verificación completa : .venv/bin/python deploy/verificar_produccion.py"
verde "=============================================================================="
