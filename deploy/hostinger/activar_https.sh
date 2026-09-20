#!/usr/bin/env bash
# ============================================================================
#  Activa el HTTPS (certificado Let's Encrypt) para el dominio del simulador.
#
#  Antes de correrlo el dominio debe APUNTAR al servidor: en el panel de Hostinger
#  (Dominios -> DNS) los registros A de "@" y "www" tienen que apuntar a la IP del VPS.
#  El script lo comprueba y, si aún no apunta, no toca nada y explica qué falta.
#
#  Uso:
#     sudo bash deploy/hostinger/activar_https.sh --dominio simuladorcontablecaavgputm.tech
#     sudo bash deploy/hostinger/activar_https.sh --dominio mi.dominio.com --correo correo@utm.edu.ec
#     sudo bash deploy/hostinger/activar_https.sh --dominio mi.dominio.com --comprobar   (solo revisa)
# ============================================================================
set -u

DOMINIO=""
CORREO=""
SOLO_COMPROBAR=0
ARCHIVO_ENTORNO="/etc/simulador/secrets.env"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dominio)     DOMINIO="$2"; shift 2 ;;
    --correo)      CORREO="$2"; shift 2 ;;
    --comprobar)   SOLO_COMPROBAR=1; shift ;;
    -h|--help)     grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opción no reconocida: $1"; exit 2 ;;
  esac
done

verde()  { echo -e "\033[32m$*\033[0m"; }
rojo()   { echo -e "\033[31m$*\033[0m"; }
amarillo(){ echo -e "\033[33m$*\033[0m"; }

if [[ -z "$DOMINIO" ]]; then
  rojo "Falta --dominio. Ejemplo:"
  echo "   sudo bash deploy/hostinger/activar_https.sh --dominio simuladorcontablecaavgputm.tech"
  exit 2
fi

if [[ $EUID -ne 0 ]]; then
  rojo "Ejecútelo con sudo."
  exit 2
fi

echo "=== 1) IP pública de este servidor ==="
IP_SERVIDOR="$(curl -s --max-time 15 https://api.ipify.org || true)"
[[ -z "$IP_SERVIDOR" ]] && IP_SERVIDOR="$(hostname -I | awk '{print $1}')"
echo "   $IP_SERVIDOR"

echo
echo "=== 2) ¿a dónde apunta el dominio? ==="
IP_DOMINIO="$(getent hosts "$DOMINIO" | awk '{print $1}' | head -1 || true)"
IP_WWW="$(getent hosts "www.$DOMINIO" | awk '{print $1}' | head -1 || true)"
echo "   $DOMINIO     -> ${IP_DOMINIO:-sin registro}"
echo "   www.$DOMINIO -> ${IP_WWW:-sin registro}"

if [[ "$IP_DOMINIO" != "$IP_SERVIDOR" ]]; then
  echo
  rojo "El dominio todavía NO apunta a este servidor."
  echo "   Falta cambiar los registros DNS en el panel de Hostinger:"
  echo "      Dominios -> $DOMINIO -> DNS / Nameservers"
  echo "      Registro A   nombre: @     valor: $IP_SERVIDOR"
  echo "      Registro A   nombre: www   valor: $IP_SERVIDOR"
  echo "   (borre los registros A actuales que apuntan a la IP de aparcado)"
  echo "   Cuando Hostinger diga que la propagación terminó, vuelva a correr este script."
  exit 1
fi

echo
verde "El dominio apunta correctamente a este servidor."

if [[ $SOLO_COMPROBAR -eq 1 ]]; then
  echo "   (--comprobar: no se cambió nada)"
  exit 0
fi

echo
echo "=== 3) Certificado Let's Encrypt ==="
if ! command -v certbot >/dev/null 2>&1; then
  amarillo "   certbot no está instalado; se instala ahora..."
  apt-get update -qq && apt-get install -y -qq certbot python3-certbot-nginx
fi

PARAMETROS=(-d "$DOMINIO" -d "www.$DOMINIO" --nginx --redirect --non-interactive --agree-tos)
if [[ -n "$CORREO" ]]; then
  PARAMETROS+=(--email "$CORREO")
else
  PARAMETROS+=(--register-unsafely-without-email)
fi

if certbot "${PARAMETROS[@]}"; then
  verde "   Certificado instalado."
else
  rojo "   certbot falló. Revise que el dominio apunte al servidor y que el puerto 80 esté abierto."
  exit 1
fi

echo
echo "=== 4) Cookies seguras (obligatorio con HTTPS) ==="
if [[ -f "$ARCHIVO_ENTORNO" ]]; then
  if grep -q '^SESSION_COOKIE_SECURE=' "$ARCHIVO_ENTORNO"; then
    sed -i 's/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=true/' "$ARCHIVO_ENTORNO"
  else
    echo "SESSION_COOKIE_SECURE=true" >> "$ARCHIVO_ENTORNO"
  fi
  echo "   SESSION_COOKIE_SECURE=true en $ARCHIVO_ENTORNO"
else
  amarillo "   No existe $ARCHIVO_ENTORNO: revise que SESSION_COOKIE_SECURE=true"
fi
systemctl restart simulador-contable
sleep 5

echo
echo "=== 5) Comprobación final ==="
curl -s -o /dev/null -w "   https://$DOMINIO       -> %{http_code}\n" "https://$DOMINIO/" || true
curl -s -o /dev/null -w "   https://www.$DOMINIO   -> %{http_code}\n" "https://www.$DOMINIO/" || true
curl -s -o /dev/null -w "   http  -> redirige a   %{redirect_url}\n" "http://$DOMINIO/" || true
curl -s -o /dev/null -w "   salud de la aplicación -> %{http_code}\n" "https://$DOMINIO/api/health" || true

echo
verde "LISTO. Enlace para los estudiantes:  https://$DOMINIO"
echo "   Certificado: certbot certificates"
echo "   Renovación automática: systemctl list-timers | grep certbot"
