#!/usr/bin/env bash
# =============================================================================
#  Gestor de AULAS AISLADAS del Simulador Contable para un VPS (Ubuntu 22.04/24.04).
#
#  Cada estudiante trabaja en SU PROPIA instancia: su base de datos, su empresa
#  simulada y su contraseña. Así la práctica es individual y evaluable, y el
#  docente puede extraer las evidencias de todas las aulas desde el servidor.
#
#  Uso (como root):
#     sudo bash gestionar_aulas.sh instalar --dominio contabilidad.utm.edu.ec --correo docente@utm.edu.ec --aulas 45
#     sudo bash gestionar_aulas.sh crear   --aulas 45 [--nombres nombres.csv]
#     sudo bash gestionar_aulas.sh estado
#     sudo bash gestionar_aulas.sh reiniciar --aula 07
#     sudo bash gestionar_aulas.sh reestablecer --aula 07
#     sudo bash gestionar_aulas.sh exportar --salida /root/evidencias --min-asientos 20
#     sudo bash gestionar_aulas.sh credenciales
#
#  Puertos:   internos 8101..  (solo localhost)   |   públicos 9101..  (con HTTPS)
#  Datos:     /var/datos/aulas/aulaNN/simulator.db
#  Claves:    /root/credenciales_aulas.csv  (solo lectura del docente)
# =============================================================================
set -euo pipefail

PROYECTO_DIR="/opt/simulador"
DATOS_RAIZ="/var/datos/aulas"
CONF_DIR="/etc/simulador/aulas"
LOG_DIR="/var/log/simulador"
USUARIO="simulador"
AULAS=45
DESDE_INTERNO=8101
DESDE_PUBLICO=9101
DOMINIO=""
CORREO=""
NOMBRES_CSV=""
SALIDA=""
MIN_ASIENTOS=0
PRIMERA_AULA=1

azul()   { printf '\033[1;34m%s\033[0m\n' "$*"; }
verde()  { printf '\033[1;32m%s\033[0m\n' "$*"; }
amar()   { printf '\033[1;33m%s\033[0m\n' "$*"; }
rojo()   { printf '\033[1;31m%s\033[0m\n' "$*"; }

ACCION="${1:-ayuda}"; shift || true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dominio) DOMINIO="${2:-}"; shift 2 ;;
    --correo) CORREO="${2:-}"; shift 2 ;;
    --aulas) AULAS="${2:-}"; shift 2 ;;
    --aula) AULAS="1"; PRIMERA_AULA="${2:-}"; shift 2 ;;
    --nombres) NOMBRES_CSV="${2:-}"; shift 2 ;;
    --salida) SALIDA="${2:-}"; shift 2 ;;
    --min-asientos) MIN_ASIENTOS="${2:-}"; shift 2 ;;
    *) rojo "Opción desconocida: $1"; exit 1 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then rojo "Ejecute como root (sudo)."; exit 1; fi

dos_digitos() { printf '%02d' "$1"; }
puerto_interno() { echo $((DESDE_INTERNO + $1 - 1)); }
puerto_publico() { echo $((DESDE_PUBLICO + $1 - 1)); }
dir_aula() { echo "$DATOS_RAIZ/aula$(dos_digitos "$1")"; }
nombre_aula() { echo "aula$(dos_digitos "$1")"; }

# --------------------------------------------------------------------------- #
instalar() {
  [[ -n "$DOMINIO" ]] || { rojo "Falta --dominio"; exit 1; }
  azul "==> Instalando el Simulador Contable para $AULAS aulas en $DOMINIO"

  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq python3 python3-venv python3-pip nginx rsync curl ufw openssl >/dev/null
  [[ -n "$CORREO" ]] && apt-get install -y -qq certbot python3-certbot-nginx >/dev/null

  id -u "$USUARIO" >/dev/null 2>&1 || \
    adduser --system --group --home "$PROYECTO_DIR" --shell /usr/sbin/nologin "$USUARIO" >/dev/null
  mkdir -p "$PROYECTO_DIR" "$DATOS_RAIZ" "$CONF_DIR" "$LOG_DIR" /etc/simulador

  # Código compartido (una sola copia y un solo entorno virtual)
  ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  rsync -a --delete \
    --exclude '.venv' --exclude '__pycache__' --exclude '.git' --exclude '.pytest_cache' \
    --exclude 'logs' --exclude '*.pyc' \
    --exclude 'database/*.db' --exclude 'database/*.db-wal' --exclude 'database/*.db-shm' \
    --exclude 'deploy/respaldos' \
    "$ORIGEN/" "$PROYECTO_DIR/"

  [[ -x "$PROYECTO_DIR/.venv/bin/python" ]] || python3 -m venv "$PROYECTO_DIR/.venv"
  "$PROYECTO_DIR/.venv/bin/pip" install --quiet --upgrade pip
  "$PROYECTO_DIR/.venv/bin/pip" install --quiet -r "$PROYECTO_DIR/requirements.txt"
  chown -R "$USUARIO:$USUARIO" "$PROYECTO_DIR" "$DATOS_RAIZ" "$LOG_DIR"

  # Servicio plantilla: una instancia por aula (simulador-aula@07, etc.)
  cat > /etc/systemd/system/simulador-aula@.service <<EOF
[Unit]
Description=Simulador Contable - aula %i
After=network.target

[Service]
Type=simple
User=$USUARIO
Group=$USUARIO
WorkingDirectory=$PROYECTO_DIR
EnvironmentFile=/etc/simulador/aulas/aula%i.env
ExecStart=$PROYECTO_DIR/.venv/bin/python serve.py
Restart=always
RestartSec=3
KillSignal=SIGINT
TimeoutStopSec=25
StandardOutput=append:$LOG_DIR/aula%i.log
StandardError=append:$LOG_DIR/aula%i.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  verde "    Servicio plantilla instalado"

  crear_aulas
  configurar_nginx
  habilitar_https
  programar_respaldo

  azul "==> Instalación terminada"
  resumen_acceso
}

# --------------------------------------------------------------------------- #
crear_aulas() {
  azul "==> Creando/actualizando $AULAS aula(s)"
  local creadas=0

  for ((n = PRIMERA_AULA; n < PRIMERA_AULA + AULAS; n++)); do
    local nombre puerto_i puerto_p env clave
    nombre="$(nombre_aula "$n")"
    puerto_i="$(puerto_interno "$n")"
    puerto_p="$(puerto_publico "$n")"
    env="$CONF_DIR/$nombre.env"

    mkdir -p "$(dir_aula "$n")"

    if [[ ! -f "$env" ]]; then
      clave="$(openssl rand -base64 48 | tr -d '\n')"
      cat > "$env" <<EOF
# Aula $nombre - generado por gestionar_aulas.sh
HOST=127.0.0.1
PORT=$puerto_i
PUERTO_PUBLICO=$puerto_p
THREADS=4
DATABASE_PATH=$(dir_aula "$n")/simulator.db
SECRET_KEY=$clave
SESSION_COOKIE_NAME=sesion_$nombre
SESSION_COOKIE_SECURE=true
SIMULADOR_DEBUG=0
EOF
      chmod 600 "$env"
      creadas=$((creadas + 1))
    fi

    chown -R "$USUARIO:$USUARIO" "$(dir_aula "$n")"
    systemctl enable "simulador-aula@$nombre" >/dev/null 2>&1
    systemctl restart "simulador-aula@$nombre"

    # Arranque por lotes: las bases se generan al primer arranque de cada aula
    if (( n % 5 == 0 )); then
      echo "    esperando a las aulas $(printf '%02d' $((n - 3)))-$nombre ..."
      esperar_aulas "$n"
    fi
  done

  esperar_aulas $((PRIMERA_AULA + AULAS - 1))
  chown -R "$USUARIO:$USUARIO" "$DATOS_RAIZ"
  verde "    Aulas listas: $AULAS (nuevas configuraciones: $creadas)"

  [[ -n "$NOMBRES_CSV" ]] && aplicar_nombres "$NOMBRES_CSV"
  preparar_credenciales
}

esperar_aulas() {
  local hasta="$1" intentos ok
  for ((intento = 1; intento <= 30; intento++)); do
    ok=0
    for ((n = PRIMERA_AULA; n <= hasta; n++)); do
      local pi; pi="$(puerto_interno "$n")"
      curl -fsS --max-time 3 "http://127.0.0.1:$pi/api/health" >/dev/null 2>&1 && ok=$((ok + 1))
    done
    (( ok == hasta - PRIMERA_AULA + 1 )) && return 0
    sleep 4
  done
  amar "    Algunas aulas aún no responden: revise 'journalctl -u simulador-aula@aulaNN'"
}

aplicar_nombres() {
  local csv="$1"
  azul "==> Asignando nombres de estudiantes ($csv)"
  while IFS=';' read -r aula nombre; do
    [[ -z "${aula:-}" || "$aula" == "aula" ]] && continue
    local dir; dir="$DATOS_RAIZ/$aula"
    [[ -f "$dir/simulator.db" ]] || continue
    printf '%s\n' "$nombre" > "$dir/estudiante.txt"
    DATABASE_PATH="$dir/simulator.db" "$PROYECTO_DIR/.venv/bin/python" - "$nombre" <<'PY'
import os, sqlite3, sys
nombre = sys.argv[1].strip()
conexion = sqlite3.connect(os.environ["DATABASE_PATH"])
conexion.execute("UPDATE usuarios SET nombre_completo = ? WHERE username = 'estudiante'", (nombre,))
conexion.commit()
conexion.close()
PY
    chown "$USUARIO:$USUARIO" "$dir/estudiante.txt"
    echo "    $aula -> $nombre"
  done < "$csv"
}

preparar_credenciales() {
  local archivo="/root/credenciales_aulas.csv"
  azul "==> Credenciales por aula (contraseña única de cada estudiante)"
  [[ -f "$archivo" ]] && cp "$archivo" "$archivo.bak"

  echo "aula;estudiante;puerto_publico;usuario;contrasena" > "$archivo"
  for ((n = PRIMERA_AULA; n < PRIMERA_AULA + AULAS; n++)); do
    local nombre dir nombre_est clave
    nombre="$(nombre_aula "$n")"
    dir="$(dir_aula "$n")"
    [[ -f "$dir/simulator.db" ]] || continue

    nombre_est="$(cat "$dir/estudiante.txt" 2>/dev/null || echo "Estudiante $nombre")"
    if [[ -f "$dir/contrasena.txt" ]]; then
      clave="$(cat "$dir/contrasena.txt")"
    else
      clave="$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-12)"
      DATABASE_PATH="$dir/simulator.db" NUEVA_CLAVE="$clave" \
        "$PROYECTO_DIR/.venv/bin/python" - <<'PY'
import os, sqlite3
from werkzeug.security import generate_password_hash
conexion = sqlite3.connect(os.environ["DATABASE_PATH"])
conexion.execute("UPDATE usuarios SET password_hash = ? WHERE username = 'estudiante'",
                 (generate_password_hash(os.environ["NUEVA_CLAVE"]),))
conexion.commit()
conexion.close()
PY
      printf '%s' "$clave" > "$dir/contrasena.txt"
      chmod 600 "$dir/contrasena.txt"
      chown "$USUARIO:$USUARIO" "$dir/contrasena.txt"
    fi

    echo "$nombre;$nombre_est;$(puerto_publico "$n");estudiante;$clave" >> "$archivo"
  done

  chmod 600 "$archivo"
  verde "    Archivo del docente: $archivo (permisos 600)"
}

configurar_nginx() {
  azul "==> Configurando Nginx (HTTPS por aula)"
  local cert="/etc/letsencrypt/live/$DOMINIO/fullchain.pem"
  local ssl_cfg=""

  if [[ -f "$cert" ]]; then
    ssl_cfg=$(cat <<EOF
    listen $(puerto_publico 1) ssl;
    ssl_certificate     $cert;
    ssl_certificate_key /etc/letsencrypt/live/$DOMINIO/privkey.pem;
EOF
)
  fi

  for ((n = PRIMERA_AULA; n < PRIMERA_AULA + AULAS; n++)); do
    local nombre pi pp conf
    nombre="$(nombre_aula "$n")"; pi="$(puerto_interno "$n")"; pp="$(puerto_publico "$n")"
    conf="/etc/nginx/sites-available/$nombre"

    if [[ -n "$ssl_cfg" ]]; then
      cat > "$conf" <<EOF
server {
    listen $pp ssl;
    server_name $DOMINIO;
    ssl_certificate     $cert;
    ssl_certificate_key /etc/letsencrypt/live/$DOMINIO/privkey.pem;

    client_max_body_size 16m;
    access_log /var/log/nginx/$nombre-access.log;

    location / {
        proxy_pass http://127.0.0.1:$pi;
        proxy_http_version 1.1;
        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    else
      cat > "$conf" <<EOF
server {
    listen $pp;
    server_name $DOMINIO;
    client_max_body_size 16m;
    access_log /var/log/nginx/$nombre-access.log;

    location / {
        proxy_pass http://127.0.0.1:$pi;
        proxy_http_version 1.1;
        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    fi

    ln -sf "$conf" "/etc/nginx/sites-enabled/$nombre"
  done

  ln -sf "$CONF_DIR/../../nginx-default-disabled" /dev/null 2>/dev/null || true
  nginx -t >/dev/null && systemctl reload nginx
  verde "    Configuración de Nginx aplicada ($AULAS puertos)"

  if [[ "$(puerto_publico 1)" -ge 1024 ]]; then
    ufw allow OpenSSH >/dev/null 2>&1 || true
    ufw allow "$(puerto_publico 1):$(puerto_publico "$AULAS")/tcp" >/dev/null 2>&1 || true
    ufw --force enable >/dev/null 2>&1 || true
    verde "    Cortafuegos: puertos $(puerto_publico 1)-$(puerto_publico "$AULAS") habilitados"
  fi
}

habilitar_https() {
  if [[ -z "$CORREO" ]]; then
    amar "    Sin --correo no se emite certificado. Cuando el DNS apunte al VPS:"
    echo "        sudo apt-get install -y certbot python3-certbot-nginx"
    echo "        sudo certbot certonly --nginx -d $DOMINIO --agree-tos -m $CORREO"
    echo "        sudo bash $0 instalar --dominio $DOMINIO --aulas $AULAS   # regenera los bloques con TLS"
    return 0
  fi
  if [[ -f "/etc/letsencrypt/live/$DOMINIO/fullchain.pem" ]]; then
    verde "    Certificado existente reutilizado"
    return 0
  fi
  cat > /etc/nginx/sites-available/temporal-acme <<EOF
server {
    listen 80;
    server_name $DOMINIO;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 200 'listo'; }
}
EOF
  mkdir -p /var/www/html
  ln -sf /etc/nginx/sites-available/temporal-acme /etc/nginx/sites-enabled/temporal-acme
  nginx -t >/dev/null && systemctl reload nginx

  if certbot certonly --nginx -d "$DOMINIO" --non-interactive --agree-tos -m "$CORREO" >/tmp/certbot-aulas.log 2>&1; then
    verde "    Certificado emitido con Let's Encrypt"
    rm -f /etc/nginx/sites-enabled/temporal-acme
    configurar_nginx
  else
    amar "    No se pudo emitir el certificado (revise /tmp/certbot-aulas.log)"
    amar "    Causa habitual: el DNS del dominio todavía no apunta a este VPS."
    rm -f /etc/nginx/sites-enabled/temporal-acme
    nginx -t >/dev/null && systemctl reload nginx
  fi
  ufw allow 80/tcp >/dev/null 2>&1 || true
  ufw allow 443/tcp >/dev/null 2>&1 || true
}

programar_respaldo() {
  cat > /etc/cron.d/simulador-aulas <<EOF
# Respaldo diario de TODAS las aulas (22:00) y evidencias semanales (lunes 07:00)
0 22 * * * root rsync -a --delete $DATOS_RAIZ/ /var/respaldos/aulas/ && find /var/respaldos/aulas -name 'simulator.db*' -mtime +30 -delete
0 7 * * 1 root cd $PROYECTO_DIR && $PROYECTO_DIR/.venv/bin/python deploy/multiaula/exportar_evidencias.py --datos $DATOS_RAIZ --salida /var/evidencias > $LOG_DIR/evidencias.log 2>&1
EOF
  chmod 644 /etc/cron.d/simulador-aulas
  mkdir -p /var/respaldos/aulas /var/evidencias
  verde "    Respaldos diarios y evidencias semanales programados"
}

# --------------------------------------------------------------------------- #
estado() {
  azul "==> Estado de las aulas"
  printf '  %-8s %-8s %-8s %-10s %s\n' "AULA" "INTERNO" "PUBLICO" "HTTP" "ASIENTOS"
  for ((n = 1; n <= AULAS; n++)); do
    local nombre dir pi pp code asientos
    nombre="$(nombre_aula "$n")"; dir="$DATOS_RAIZ/$nombre"
    pi="$(puerto_interno "$n")"; pp="$(puerto_publico "$n")"
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "http://127.0.0.1:$pi/api/health" || echo '---')"
    if [[ -f "$dir/simulator.db" ]]; then
      asientos="$("$PROYECTO_DIR/.venv/bin/python" -c "
import sqlite3,sys
try:
    print(sqlite3.connect(sys.argv[1]).execute('SELECT COUNT(*) FROM asientos').fetchone()[0])
except Exception:
    print('?')
" "$dir/simulator.db")"
    else
      asientos="-"
    fi
    printf '  %-8s %-8s %-8s %-10s %s\n' "$nombre" "$pi" "$pp" "$code" "$asientos"
  done
}

reiniciar_aula() {
  local nombre; nombre="$(nombre_aula "$PRIMERA_AULA")"
  systemctl restart "simulador-aula@$nombre"
  sleep 6
  curl -s -o /dev/null -w "  $nombre -> HTTP %{http_code}\n" --max-time 6 \
    "http://127.0.0.1:$(puerto_interno "$PRIMERA_AULA")/api/health"
}

reestablecer_aula() {
  local nombre dir; nombre="$(nombre_aula "$PRIMERA_AULA")"; dir="$DATOS_RAIZ/$nombre"
  amar "==> Reestableciendo $nombre (se borran sus datos y se generan de nuevo)"
  systemctl stop "simulador-aula@$nombre"
  rm -f "$dir/simulator.db" "$dir/simulator.db-wal" "$dir/simulator.db-shm"
  systemctl start "simulador-aula@$nombre"
  esperar_aulas_pos "${PRIMERA_AULA}"
  DATABASE_PATH="$dir/simulator.db" NUEVA_CLAVE="$(cat "$dir/contrasena.txt" 2>/dev/null || echo 'estudiante123')" \
    "$PROYECTO_DIR/.venv/bin/python" - <<'PY'
import os, sqlite3
from werkzeug.security import generate_password_hash
conexion = sqlite3.connect(os.environ["DATABASE_PATH"])
conexion.execute("UPDATE usuarios SET password_hash = ? WHERE username = 'estudiante'",
                 (generate_password_hash(os.environ["NUEVA_CLAVE"]),))
conexion.commit(); conexion.close()
PY
  verde "    $nombre reestablecida con los saldos iniciales"
}

esperar_aulas_pos() {
  local n="$1" pi; pi="$(puerto_interno "$n")"
  for _ in $(seq 1 30); do
    curl -fsS --max-time 3 "http://127.0.0.1:$pi/api/health" >/dev/null 2>&1 && return 0
    sleep 4
  done
}

exportar() {
  local salida="${SALIDA:-/var/evidencias}"
  mkdir -p "$salida"
  "$PROYECTO_DIR/.venv/bin/python" "$PROYECTO_DIR/deploy/multiaula/exportar_evidencias.py" \
    --datos "$DATOS_RAIZ" --salida "$salida" --min-asientos "$MIN_ASIENTOS"
  ls -la "$salida" | tail -4
}

credenciales() { cat /root/credenciales_aulas.csv; }

resumen_acceso() {
  azul "==> Accesos para los estudiantes"
  echo "    Aula 01: http://$DOMINIO:$(puerto_publico 1)/   (HTTPS si el certificado se emitió)"
  echo "    Aula $(printf '%02d' "$AULAS"): http://$DOMINIO:$(puerto_publico "$AULAS")/"
  echo "    Usuario/contraseña de cada estudiante: /root/credenciales_aulas.csv"
  echo "    Evidencias:  sudo bash $0 exportar --salida /root/evidencias --min-asientos 20"
  echo
  amar " RECUERDE: cada aula es independiente; las pruebas viven en $DATOS_RAIZ"
}

case "$ACCION" in
  instalar)      instalar ;;
  crear)         crear_aulas ;;
  estado)        estado ;;
  reiniciar)     reiniciar_aula ;;
  reestablecer)  reestablecer_aula ;;
  exportar)      exportar ;;
  credenciales)  credenciales ;;
  *) sed -n '2,26p' "$0" ;;
esac
