#!/usr/bin/env bash
# =============================================================================
#  Instalador del Simulador Integral de Sistema Contable en un VPS de Hostinger
#  (Ubuntu 22.04 / 24.04 LTS). Deja el sistema sirviendo 24/7 con Nginx + waitress
#  y certificado HTTPS de Let's Encrypt.
#
#  Uso (dentro del VPS, como root o con sudo):
#     sudo bash instalar_vps.sh --dominio contabilidad.midominio.com --correo docente@utm.edu.ec
#
#  Opciones:
#     --dominio DOMINIO      dominio o subdominio que apuntará al VPS (obligatorio)
#     --correo CORREO        correo para Let's Encrypt (si se omite, no se activa HTTPS)
#     --puerto PUERTO        puerto interno de la aplicación (por defecto 8080)
#     --ruta RUTA            carpeta de instalación (por defecto /opt/simulador)
#     --datos RUTA           carpeta de la base de datos (por defecto /var/datos)
#     --usuario USUARIO      usuario Linux de servicio (por defecto simulador)
#     --servidor SERVIDOR    waitress (por defecto) o gunicorn
#     --sin-firewall         no configurar ufw
#
#  El script es idempotente: puede volver a ejecutarse para actualizar el sistema.
# =============================================================================
set -euo pipefail

DOMINIO=""
CORREO=""
PUERTO="8080"
PROYECTO_DIR="/opt/simulador"
DATOS_DIR="/var/datos"
USUARIO="simulador"
SERVIDOR="waitress"
FIREWALL="si"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dominio) DOMINIO="${2:-}"; shift 2 ;;
    --correo) CORREO="${2:-}"; shift 2 ;;
    --puerto) PUERTO="${2:-}"; shift 2 ;;
    --ruta) PROYECTO_DIR="${2:-}"; shift 2 ;;
    --datos) DATOS_DIR="${2:-}"; shift 2 ;;
    --usuario) USUARIO="${2:-}"; shift 2 ;;
    --servidor) SERVIDOR="${2:-}"; shift 2 ;;
    --sin-firewall) FIREWALL="no"; shift ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $1"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------- utilidades
azul()   { printf '\033[1;34m%s\033[0m\n' "$*"; }
verde()  { printf '\033[1;32m%s\033[0m\n' "$*"; }
amarillo(){ printf '\033[1;33m%s\033[0m\n' "$*"; }
rojo()   { printf '\033[1;31m%s\033[0m\n' "$*"; }
paso()   { azul "==> $*"; }

if [[ $EUID -ne 0 ]]; then
  rojo "Este instalador debe ejecutarse como root:  sudo bash instalar_vps.sh --dominio ..."
  exit 1
fi

if [[ -z "$DOMINIO" ]]; then
  rojo "Falta --dominio. Ejemplo: sudo bash instalar_vps.sh --dominio contabilidad.midominio.com"
  exit 1
fi

# Carpeta desde la que se ejecuta el instalador = raíz del proyecto
ORIGEN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="/var/log/simulador"

paso "Simulador Integral de Sistema Contable - instalación en VPS Hostinger"
echo "    Dominio        : $DOMINIO"
echo "    Proyecto       : $PROYECTO_DIR"
echo "    Base de datos  : $DATOS_DIR/simulator.db"
echo "    Puerto interno : $PUERTO"
echo "    Usuario        : $USUARIO"
echo "    Origen         : $ORIGEN_DIR"
echo

# ------------------------------------------------- 1) Paquetes del sistema
paso "1/9 Instalando paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx rsync curl ufw >/dev/null
if [[ -n "$CORREO" ]]; then
  apt-get install -y -qq certbot python3-certbot-nginx >/dev/null
fi
verde "    Paquetes instalados ($(python3 --version))"

# --------------------------------------------------------- 2) Usuario y rutas
paso "2/9 Preparando usuario y carpetas"
if ! id -u "$USUARIO" >/dev/null 2>&1; then
  adduser --system --group --home "$PROYECTO_DIR" --shell /usr/sbin/nologin "$USUARIO" >/dev/null
  verde "    Usuario de sistema '$USUARIO' creado"
else
  verde "    El usuario '$USUARIO' ya existe"
fi
mkdir -p "$PROYECTO_DIR" "$DATOS_DIR" "$LOG_DIR" /etc/simulador

# ----------------------------------------------------------- 3) Copiar código
paso "3/9 Copiando la aplicación a $PROYECTO_DIR"
rsync -a --delete \
  --exclude '.venv' --exclude '__pycache__' --exclude '.git' --exclude '.pytest_cache' \
  --exclude 'logs' --exclude '*.pyc' \
  --exclude 'database/*.db' --exclude 'database/*.db-wal' --exclude 'database/*.db-shm' \
  --exclude 'database/aulas' --exclude 'database/plantilla' \
  --exclude 'credenciales*' --exclude '*credenciales*.csv' --exclude 'datos' \
  --exclude '.env' \
  --exclude 'deploy/respaldos' \
  "$ORIGEN_DIR/" "$PROYECTO_DIR/"
verde "    Archivos copiados"

# ------------------------------------------------ 4) Entorno virtual y deps
paso "4/9 Creando entorno virtual e instalando dependencias"
if [[ ! -x "$PROYECTO_DIR/.venv/bin/python" ]]; then
  python3 -m venv "$PROYECTO_DIR/.venv"
fi
"$PROYECTO_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$PROYECTO_DIR/.venv/bin/pip" install --quiet -r "$PROYECTO_DIR/requirements.txt"
if [[ "$SERVIDOR" == "gunicorn" ]]; then
  "$PROYECTO_DIR/.venv/bin/pip" install --quiet -r "$PROYECTO_DIR/deploy/hostinger/requirements-vps.txt"
  verde "    Flask + waitress + gunicorn + openpyxl instalados"
else
  verde "    Flask + waitress + openpyxl instalados"
fi

# --------------------------------------------------------- 5) Secretos
paso "5/9 Configurando secretos"
if [[ ! -f /etc/simulador/secrets.env ]]; then
  CLAVE="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  if [[ -n "$CORREO" ]]; then SEGURO="true"; else SEGURO="false"; fi
  cat > /etc/simulador/secrets.env <<EOF
# Generado por instalar_vps.sh - permisos 600, no versionar.
SECRET_KEY=$CLAVE
# true cuando el sitio se sirve por HTTPS (con --correo se activa Let's Encrypt).
SESSION_COOKIE_SECURE=$SEGURO
SESSION_HORAS=8
MAX_CONTENT_MB=16
# Datos FUERA de la carpeta del código: las actualizaciones no los tocan.
DATABASE_PATH=$DATOS_DIR/simulator.db
RUTA_AULAS=$DATOS_DIR/aulas
RUTA_PLANTILLA=$DATOS_DIR/plantilla/aula_base.db
EOF
  verde "    SECRET_KEY aleatoria generada y rutas de datos configuradas"
else
  verde "    Se conserva el archivo de secretos existente"
  amarillo "    Revise /etc/simulador/secrets.env: debe apuntar a $DATOS_DIR"
fi
chmod 600 /etc/simulador/secrets.env
chown "$USUARIO:$USUARIO" /etc/simulador/secrets.env

chown -R "$USUARIO:$USUARIO" "$PROYECTO_DIR" "$DATOS_DIR" "$LOG_DIR"

# --------------------------------------------------------- 6) Servicio systemd
paso "6/9 Registrando el servicio systemd"
if [[ "$SERVIDOR" == "gunicorn" ]]; then
  DESCRIPCION="Simulador Integral de Sistema Contable (gunicorn)"
  EXEC_START="$PROYECTO_DIR/.venv/bin/gunicorn --workers 3 --threads 4 --bind 127.0.0.1:$PUERTO --timeout 120 --access-logfile - --error-logfile - wsgi:application"
else
  DESCRIPCION="Simulador Integral de Sistema Contable (waitress)"
  EXEC_START="$PROYECTO_DIR/.venv/bin/python serve.py"
fi
cat > /etc/systemd/system/simulador-contable.service <<EOF
[Unit]
Description=$DESCRIPCION
After=network.target

[Service]
Type=simple
User=$USUARIO
Group=$USUARIO
WorkingDirectory=$PROYECTO_DIR
Environment=HOST=127.0.0.1
Environment=PORT=$PUERTO
Environment=THREADS=8
Environment=DATABASE_PATH=$DATOS_DIR/simulator.db
Environment=RUTA_AULAS=$DATOS_DIR/aulas
Environment=RUTA_PLANTILLA=$DATOS_DIR/plantilla/aula_base.db
EnvironmentFile=-/etc/simulador/secrets.env
ExecStart=$EXEC_START
Restart=always
RestartSec=3
KillSignal=SIGINT
TimeoutStopSec=25
StandardOutput=append:$LOG_DIR/servidor.log
StandardError=append:$LOG_DIR/servidor.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable simulador-contable >/dev/null
systemctl restart simulador-contable
verde "    Servicio habilitado y arrancado"

# --------------------------------------------------------- 7) Nginx
paso "7/9 Configurando Nginx para $DOMINIO"
cat > /etc/nginx/sites-available/simulador-contable <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMINIO;

    client_max_body_size 16m;
    access_log /var/log/nginx/simulador-access.log;
    error_log  /var/log/nginx/simulador-error.log;

    location /static/ {
        proxy_pass http://127.0.0.1:$PUERTO;
        expires 7d;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:$PUERTO;
        proxy_http_version 1.1;
        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/simulador-contable /etc/nginx/sites-enabled/simulador-contable
rm -f /etc/nginx/sites-enabled/default
nginx -t >/dev/null
systemctl reload nginx
verde "    Nginx configurado y recargado"

if [[ "$FIREWALL" == "si" ]]; then
  ufw allow OpenSSH >/dev/null 2>&1 || true
  ufw allow 'Nginx Full' >/dev/null 2>&1 || true
  ufw --force enable >/dev/null 2>&1 || true
  verde "    Cortafuegos (ufw) habilitado: SSH + HTTP/HTTPS"
fi

# -------------------------------------- 8) Primer arranque: generar la base
paso "8/9 Esperando el primer arranque (genera los datos de demostración)"
LISTO="no"
for intento in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:$PUERTO/api/health" >/tmp/salud.json 2>/dev/null; then
    LISTO="si"
    break
  fi
  sleep 3
done

if [[ "$LISTO" == "si" ]]; then
  verde "    La aplicación responde: $(tr -d '\n' </tmp/salud.json | cut -c1-120)…"
else
  amarillo "    La aplicación aún no responde. Revise:  journalctl -u simulador-contable -n 50"
fi

# ------------------------------- 8b) Plantilla de aulas y carpeta de datos
paso "8/9 Plantilla de aulas y carpeta de datos"
mkdir -p "$DATOS_DIR/aulas" "$DATOS_DIR/plantilla"
chown -R "$USUARIO:$USUARIO" "$DATOS_DIR"

ENTORNO="DATABASE_PATH=$DATOS_DIR/simulator.db RUTA_AULAS=$DATOS_DIR/aulas RUTA_PLANTILLA=$DATOS_DIR/plantilla/aula_base.db"

if [[ ! -f "$DATOS_DIR/plantilla/aula_base.db" ]]; then
  if sudo -u "$USUARIO" env $ENTORNO \
       "$PROYECTO_DIR/.venv/bin/python" "$PROYECTO_DIR/database/crear_aula.py" --plantilla >/tmp/plantilla.log 2>&1; then
    verde "    Plantilla de aulas creada en $DATOS_DIR/plantilla/aula_base.db"
  else
    amarillo "    No se pudo crear la plantilla de aulas. Revise /tmp/plantilla.log"
  fi
else
  verde "    La plantilla de aulas ya existía (se conserva)"
fi

if sudo -u "$USUARIO" env $ENTORNO \
     "$PROYECTO_DIR/.venv/bin/python" "$PROYECTO_DIR/deploy/backup_db.py" --todas \
     --destino "$PROYECTO_DIR/deploy/respaldos" --conservar 30 >/tmp/respaldo.log 2>&1; then
  verde "    Respaldo completo de prueba creado (detalle en /tmp/respaldo.log)"
else
  amarillo "    No se pudo crear el respaldo de prueba. Revise /tmp/respaldo.log"
fi

# Las NÓMINAS y las CREDENCIALES no viajan con el código: súbalas aparte y luego
#   sudo -u $USUARIO env $ENTORNO $PROYECTO_DIR/.venv/bin/python $PROYECTO_DIR/database/importar_nomina.py --csv /root/nomina.csv --paralelo B

# --------------------------------------------------------- 9) HTTPS
paso "9/9 Certificado HTTPS"
if [[ -n "$CORREO" ]]; then
  if certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos -m "$CORREO" --redirect >/tmp/certbot.log 2>&1; then
    sed -i 's/^SESSION_COOKIE_SECURE=false/SESSION_COOKIE_SECURE=true/' /etc/simulador/secrets.env
    systemctl restart simulador-contable
    verde "    HTTPS activo y sesiones marcadas como seguras"
  else
    amarillo "    No se pudo emitir el certificado. Revise /tmp/certbot.log"
    amarillo "    Causa habitual: el dominio todavía no apunta a la IP de este VPS (registro DNS A)."
  fi
else
  amarillo "    Sin --correo no se emitió certificado. Cuando el DNS apunte al VPS ejecute:"
  echo "        sudo certbot --nginx -d $DOMINIO --redirect"
  echo "        sudo sed -i 's/^SESSION_COOKIE_SECURE=false/SESSION_COOKIE_SECURE=true/' /etc/simulador/secrets.env"
  echo "        sudo systemctl restart simulador-contable"
fi

# ------------------------------------------------ 10) Respaldos diarios
cat > /etc/cron.d/simulador-respaldo <<EOF
# Respaldo diario de la base de datos del simulador (22:00) y limpieza de antiguos (conserva 30)
0 22 * * * $USUARIO cd $PROYECTO_DIR && DATABASE_PATH=$DATOS_DIR/simulator.db RUTA_AULAS=$DATOS_DIR/aulas RUTA_PLANTILLA=$DATOS_DIR/plantilla/aula_base.db $PROYECTO_DIR/.venv/bin/python deploy/backup_db.py --todas --destino $PROYECTO_DIR/deploy/respaldos --conservar 30 >> $LOG_DIR/respaldo.log 2>&1
EOF
chmod 644 /etc/cron.d/simulador-respaldo

echo
verde "=============================== INSTALACIÓN COMPLETADA ==============================="
echo " Aplicación        : http://$DOMINIO"
[[ -n "$CORREO" ]] && echo " Con HTTPS         : https://$DOMINIO"
echo " Manual de usuario : http://$DOMINIO/manual"
echo " Estado del servicio: systemctl status simulador-contable --no-pager"
echo " Registros          : journalctl -u simulador-contable -n 50   |   $LOG_DIR/servidor.log"
echo " Base de datos      : $DATOS_DIR/simulator.db  (respaldos diarios en $PROYECTO_DIR/deploy/respaldos)"
echo
echo " COMANDOS DEL DÍA A DÍA (cópielos tal cual):"
echo "   Estado del servicio : sudo systemctl status simulador-contable --no-pager"
echo "   Reiniciar           : sudo systemctl restart simulador-contable"
echo "   Detener / arrancar  : sudo systemctl stop simulador-contable  |  sudo systemctl start simulador-contable"
echo "   Registros en vivo   : sudo journalctl -u simulador-contable -f"
echo "   Salud de la app     : curl -s http://127.0.0.1:$PUERTO/api/health"
echo
echo " DATOS Y RESPALDOS:"
echo "   Base de control     : $DATOS_DIR/simulator.db"
echo "   Aulas de estudiantes: $DATOS_DIR/aulas/B/<usuario>.db"
echo "   Plantilla de aulas  : $DATOS_DIR/plantilla/aula_base.db"
echo "   Respaldo manual     : sudo -u $USUARIO env DATABASE_PATH=$DATOS_DIR/simulator.db RUTA_AULAS=$DATOS_DIR/aulas RUTA_PLANTILLA=$DATOS_DIR/plantilla/aula_base.db $PROYECTO_DIR/.venv/bin/python $PROYECTO_DIR/deploy/backup_db.py --todas"
echo "   Ver respaldos       : $PROYECTO_DIR/.venv/bin/python $PROYECTO_DIR/deploy/restaurar_db.py --listar"
echo "   Restaurar (simular) : $PROYECTO_DIR/.venv/bin/python $PROYECTO_DIR/deploy/restaurar_db.py --desde <carpeta>"
echo "   Restaurar (real)    : $PROYECTO_DIR/.venv/bin/python $PROYECTO_DIR/deploy/restaurar_db.py --desde <carpeta> --si"
echo "   (el respaldo diario de las 22:00 ya incluye control + plantilla + TODAS las aulas)"
echo
echo " ACTUALIZAR EL SISTEMA (cuando cambie el código):"
echo "   suba el nuevo paquete y repita:  sudo bash deploy/hostinger/instalar_vps.sh --dominio $DOMINIO"
echo "   (el instalador es idempotente: conserva /etc/simulador/secrets.env y $DATOS_DIR)"
echo
echo " NÓMINA Y CREDENCIALES (no viajan con el código):"
echo "   sudo -u $USUARIO env DATABASE_PATH=$DATOS_DIR/simulator.db RUTA_AULAS=$DATOS_DIR/aulas RUTA_PLANTILLA=$DATOS_DIR/plantilla/aula_base.db $PROYECTO_DIR/.venv/bin/python $PROYECTO_DIR/database/importar_nomina.py --csv /root/nomina.csv --paralelo B"
echo
echo " HTTPS MANUAL (si no usó --correo):"
echo "   sudo certbot --nginx -d $DOMINIO --redirect"
echo "   sudo sed -i 's/^SESSION_COOKIE_SECURE=false/SESSION_COOKIE_SECURE=true/' /etc/simulador/secrets.env"
echo "   sudo systemctl restart simulador-contable"
echo
# ------------------------------------------------ 10.b Claves de administración
# Las cuentas de fábrica (admin, docente, auditor, estudiante) traen contraseñas
# conocidas. En un sistema publicado hay que cambiarlas: se generan claves nuevas y se
# guardan en un archivo del servidor para que el responsable las tenga a mano.
# Solo se cambian las que AÚN tienen la clave de fábrica, así una reinstalación no
# invalida las claves ya en uso.
ARCHIVO_ACCESOS="$DATOS_DIR/ACCESOS_DEL_SERVIDOR.txt"
TEMPORAL_CLAVE="$(mktemp)"
CAMBIADAS=""
for CUENTA in admin docente auditor estudiante; do
  printf '%s123\n' "$CUENTA" > "$TEMPORAL_CLAVE"
  if sudo -u "$USUARIO" env $ENTORNO "$PY" "$PROYECTO_DIR/deploy/fijar_clave.py" \
       --usuario "$CUENTA" --comprobar --archivo "$TEMPORAL_CLAVE" >/dev/null 2>&1; then
    if [ ! -f "$ARCHIVO_ACCESOS" ]; then
      {
        echo "ACCESOS DE ADMINISTRACION - SERVIDOR DEL SIMULADOR CONTABLE"
        echo "Generados automaticamente al instalar el $(date '+%d/%m/%Y %H:%M')."
        echo "NO comparta este archivo: contiene las contrasenas del sistema."
        echo
      } > "$ARCHIVO_ACCESOS"
    fi
    sudo -u "$USUARIO" env $ENTORNO "$PY" "$PROYECTO_DIR/deploy/fijar_clave.py" \
         --usuario "$CUENTA" --generar --archivo "/tmp/clave_${CUENTA}.txt" >/dev/null 2>&1
    {
      echo "  $CUENTA"
      echo "      usuario: $CUENTA"
      echo "      contrasena: $(cat /tmp/clave_${CUENTA}.txt)"
      echo
    } >> "$ARCHIVO_ACCESOS"
    rm -f "/tmp/clave_${CUENTA}.txt"
    CAMBIADAS="$CAMBIADAS $CUENTA"
  fi
done
rm -f "$TEMPORAL_CLAVE"
if [ -n "$CAMBIADAS" ]; then
  chown "$USUARIO:$USUARIO" "$ARCHIVO_ACCESOS" 2>/dev/null || true
  chmod 600 "$ARCHIVO_ACCESOS"
  amarillo " Claves de fábrica reemplazadas en:$CAMBIADAS"
  echo "     Se guardaron en: $ARCHIVO_ACCESOS   (léalo con: sudo cat $ARCHIVO_ACCESOS)"
else
  verde " Ninguna cuenta conserva la clave de fábrica."
fi

echo
amarillo " PENDIENTE OBLIGATORIO DE SEGURIDAD: revise las claves de administración"
echo "     sudo cat $ARCHIVO_ACCESOS        (nombres de usuario y contrasenas generadas)"
echo "     Para cambiarlas cuando quiera:"
echo "     sudo -u $USUARIO bash -c 'cd $PROYECTO_DIR && DATABASE_PATH=$DATOS_DIR/simulator.db .venv/bin/python deploy/cambiar_credenciales.py'"
echo
echo " Verificación del despliegue desde su equipo:"
echo "     python deploy/verificar_despliegue.py --url http://$DOMINIO"
echo "     python deploy/verificar_produccion.py --base https://$DOMINIO     (11 comprobaciones funcionales)"
echo "==============================================================================="
