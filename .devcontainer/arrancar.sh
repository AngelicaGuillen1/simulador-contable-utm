#!/usr/bin/env bash
# Arranca el servidor de producción (waitress) cada vez que se inicia el entorno.
# Codespaces publica el puerto 5000 como URL https://<codespace>-5000.app.github.dev
set -uo pipefail

cd "$(dirname "$0")/.."

export HOST="0.0.0.0"
export PORT="5000"
export SIMULADOR_DEBUG="0"
: "${DATABASE_PATH:=database/simulator.db}"
export DATABASE_PATH

# Clave de sesión propia del entorno (no versionada)
if [ ! -f .devcontainer/entorno.local.sh ]; then
  echo "export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" > .devcontainer/entorno.local.sh
  chmod 600 .devcontainer/entorno.local.sh
fi
# shellcheck disable=SC1091
source .devcontainer/entorno.local.sh

# Si ya hay un servidor escuchando en el puerto, no se arranca otro
if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
  echo "El servidor ya está en ejecución en el puerto ${PORT}."
  exit 0
fi

echo "Iniciando el Simulador Contable en el puerto ${PORT}..."
nohup python serve.py > /tmp/simulador.log 2>&1 &

for intento in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    echo "Servidor disponible en el puerto ${PORT} (intento ${intento})."
    exit 0
  fi
  sleep 3
done

echo "El servidor no respondió; revise /tmp/simulador.log"
tail -20 /tmp/simulador.log || true
