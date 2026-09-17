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
FIREWALL="si"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dominio) DOMINIO="${2:-}"; shift 2 ;;
    --correo) CORREO="${2:-}"; shift 2 ;;
    --puerto) PUERTO="${2:-}"; shift 2 ;;
    --ruta) PROYECTO_DIR="${2:-}"; shift 2 ;;
    --datos) DATOS_DIR="${2:-}"; shift 2 ;;
    --usuario) USUARIO="${2:-}"; shift 2 ;;
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
verde "    Flask + waitress + openpyxl instalados"

# --------------------------------------------------------- 5) Secretos
paso "5/9 Configurando secretos"
if [[ ! -f /etc/simulador/secrets.env ]]; then
  CLAVE="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  cat > /etc/simulador/secrets.env <<EOF
# Generado por instalar_vps.sh - permisos 600, no versionar.
SECRET_KEY=$CLAVE
SESSION_COOKIE_SECURE=false
EOF
  verde "    SECRET_KEY aleatoria generada"
else
  verde "    Se conserva el archivo de secretos existente"
fi
chmod 600 /etc/simulador/secrets.env
chown "$USUARIO:$USUARIO" /etc/simulador/secrets.env

chown -R "$USUARIO:$USUARIO" "$PROYECTO_DIR" "$DATOS_DIR" "$LOG_DIR"

# --------------------------------------------------------- 6) Servicio systemd
paso "6/9 Registrando el servicio systemd"
cat > /etc/systemd/system/simulador-contable.service <<EOF
[Unit]
Description=Simulador Integral de Sistema Contable (waitress)
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
EnvironmentFile=-/etc/simulador/secrets.env
ExecStart=$PROYECTO_DIR/.venv/bin/python serve.py
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
0 22 * * * $USUARIO cd $PROYECTO_DIR && DATABASE_PATH=$DATOS_DIR/simulator.db $PROYECTO_DIR/.venv/bin/python deploy/backup_db.py --origen $DATOS_DIR/simulator.db --destino $PROYECTO_DIR/deploy/respaldos --conservar 30 >> $LOG_DIR/respaldo.log 2>&1
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
amarillo " PENDIENTE OBLIGATORIO DE SEGURIDAD: cambie las contraseñas de demostración"
echo "     sudo -u $USUARIO bash -c 'cd $PROYECTO_DIR && DATABASE_PATH=$DATOS_DIR/simulator.db .venv/bin/python deploy/cambiar_credenciales.py'"
echo
echo " Verificación del despliegue desde su equipo:"
echo "     python deploy/verificar_despliegue.py --url http://$DOMINIO"
echo "==============================================================================="
