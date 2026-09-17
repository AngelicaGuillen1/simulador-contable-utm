#!/usr/bin/env bash
# Instalación del entorno de Codespaces / contenedor de desarrollo:
# dependencias + datos de demostración. Se ejecuta una sola vez al crear el entorno.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Instalando dependencias de Python"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo "==> Generando la empresa simulada (periodo Abril 2026)"
if [ ! -f database/simulator.db ]; then
  python database/seed_data.py
else
  echo "    La base de datos ya existe: se conserva su trabajo."
fi

echo "==> Ejecutando la suite de pruebas (113 pruebas)"
python -m pytest tests -q || true

echo
echo "======================================================================"
echo " LISTO. El sistema se abre solo en el puerto 5000."
echo " Si la vista previa no aparece: pestaña PUERTOS -> 5000 -> Abrir en el navegador"
echo " Usuarios: admin/admin123 - docente/docente123 - estudiante/estudiante123"
echo " Manual: http://localhost:5000/manual"
echo "======================================================================"
