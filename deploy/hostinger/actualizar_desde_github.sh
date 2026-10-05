#!/usr/bin/env bash
# ============================================================================
#  Actualiza el simulador en el VPS trayendo el código del repositorio público.
#
#  Hace todo el despliegue en un solo paso:
#    1. clona la última versión del repositorio,
#    2. la instala (systemd + nginx, conservando el HTTPS y los datos),
#    3. abre las actividades al inicio de su unidad (fechas del cronograma intactas),
#    4. da a cada estudiante valores propios en su empresa,
#    5. reinicia el servicio y comprueba que responde.
#
#  Uso (en la terminal del hPanel, como root):
#      bash actualizar_desde_github.sh
#      DOMINIO=otro.dominio bash actualizar_desde_github.sh
# ============================================================================
set -u

REPO="${REPO:-https://github.com/AngelicaGuillen1/simulador-contable-utm.git}"
DOMINIO="${DOMINIO:-simuladorcontablecaavgputm.tech}"
DESTINO="${DESTINO:-/tmp/simulador-actualizar}"
PROYECTO="${PROYECTO_DIR:-/opt/simulador}"
DATOS="${DATOS_DIR:-/var/datos}"

verde() { echo -e "\033[32m$*\033[0m"; }
rojo()  { echo -e "\033[31m$*\033[0m"; }
paso()  { echo; echo "==> $*"; }

if [[ $EUID -ne 0 ]]; then
  rojo "Ejecútelo como root."
  exit 1
fi

paso "1/5 Descargando la última versión del repositorio"
rm -rf "$DESTINO"
if ! git clone --depth 1 "$REPO" "$DESTINO" >/tmp/actualizar-clon.log 2>&1; then
  rojo "No se pudo clonar el repositorio. Detalle:"
  tail -5 /tmp/actualizar-clon.log
  exit 1
fi
verde "    Código descargado en $DESTINO"

paso "2/5 Instalando (conserva HTTPS, datos y claves)"
cd "$DESTINO" || exit 1
if ! bash deploy/hostinger/instalar_vps.sh --dominio "$DOMINIO" >/tmp/actualizar-instalar.log 2>&1; then
  rojo "El instalador falló. Últimas líneas:"
  tail -15 /tmp/actualizar-instalar.log
  exit 1
fi
tail -6 /tmp/actualizar-instalar.log | sed 's/^/    /'

paso "3/5 Aplicando las fechas de las actividades"
cd "$PROYECTO" || exit 1
export DATABASE_PATH="$DATOS/simulator.db" RUTA_AULAS="$DATOS/aulas" RUTA_PLANTILLA="$DATOS/plantilla/aula_base.db"
"$PROYECTO/.venv/bin/python" database/ajustar_fechas_actividades.py --unidades --aplicar 2>&1 | tail -3 | sed 's/^/    /'

paso "4/5 Valores propios por estudiante"
"$PROYECTO/.venv/bin/python" database/variar_catalogos.py --aplicar 2>&1 | tail -3 | sed 's/^/    /'
"$PROYECTO/.venv/bin/python" database/variar_terceros.py --aplicar 2>&1 | tail -3 | sed 's/^/    /'
"$PROYECTO/.venv/bin/python" database/actualizar_texto_actividades.py --aplicar 2>&1 | tail -2 | sed 's/^/    /'
"$PROYECTO/.venv/bin/python" database/variar_casos.py --aplicar 2>&1 | tail -2 | sed 's/^/    /'

paso "5/5 Reinicio y comprobación"
systemctl restart simulador-contable
sleep 6
systemctl is-active simulador-contable | sed 's/^/    servicio: /'
echo "    --- estado de las aulas ---"
"$PROYECTO/.venv/bin/python" deploy/verificar_aulas.py --detalle 2>&1 | sed 's/^/    /'
ESTADO="$(curl -s -o /dev/null -w '%{http_code}' -k "https://$DOMINIO/api/health" || echo fallo)"
echo "    salud por HTTPS: $ESTADO"
ALUMNOS="$("$PROYECTO/.venv/bin/python" - <<'PY'
import glob, os, sqlite3, sys
sys.path.insert(0, os.environ.get("PROYECTO_DIR", "/opt/simulador"))
from config import Config
try:
    conexion = sqlite3.connect(Config.DATABASE_PATH)
    total = conexion.execute("""SELECT COUNT(*) FROM usuarios u JOIN roles r ON r.id = u.rol_id
                                WHERE r.nombre = 'Estudiante' AND COALESCE(u.es_demo, 0) = 0""").fetchone()[0]
    conexion.close()
except Exception:
    total = -1
print(total)
PY
)"
AULAS="$(ls -1 "$DATOS/aulas/B" 2>/dev/null | wc -l)"
echo "    estudiantes reales: $ALUMNOS | aulas: $AULAS"

echo
if [[ "$ESTADO" == "200" ]]; then
  verde "LISTO. Simulador actualizado y respondiendo en https://$DOMINIO"
  echo "   Los estudiantes ya tienen la tarea 1 disponible, sin el módulo de casos de los"
  echo "   libros y con los valores propios de su empresa."
else
  rojo "El servicio no responde por HTTPS ($ESTADO). Revise:  journalctl -u simulador-contable -n 40"
fi
