#!/usr/bin/env bash
# =============================================================================
#  Empaqueta el Simulador Contable para subirlo al VPS de Hostinger.
#
#  Genera en la carpeta dist/ un archivo .tar.gz con todo el proyecto (sin el
#  entorno virtual, sin cachés y sin la base de datos: el VPS la genera solo).
#
#  Uso:  bash deploy/hostinger/empaquetar.sh
# =============================================================================
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="$RAIZ/dist"
FECHA="$(date +%Y%m%d)"
NOMBRE="simulador-contable-$FECHA.tar.gz"

mkdir -p "$DIST"

tar -czf "$DIST/$NOMBRE" \
  -C "$RAIZ" \
  --exclude='./.venv' \
  --exclude='./.git' \
  --exclude='./dist' \
  --exclude='./logs' \
  --exclude='./.pytest_cache' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='./database/*.db' \
  --exclude='./database/*.db-wal' \
  --exclude='./database/*.db-shm' \
  --exclude='./database/*.bak' \
  --exclude='./deploy/respaldos' \
  .

TAMANO="$(du -h "$DIST/$NOMBRE" | cut -f1)"
echo "Paquete listo: $DIST/$NOMBRE ($TAMANO)"
echo
echo "Siguientes pasos:"
echo "  1. Súbalo al VPS  (hPanel > VPS > Administrador de archivos, o scp)"
echo "  2. En la terminal del VPS:"
echo "       tar -xzf $NOMBRE -C /tmp/simulador-contable && cd /tmp/simulador-contable"
echo "       sudo bash deploy/hostinger/instalar_vps.sh --dominio SU-DOMINIO --correo SU-CORREO"
