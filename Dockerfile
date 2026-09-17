# Simulador Integral de Sistema Contable - imagen de producción
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    DATABASE_PATH=/datos/simulator.db \
    SESSION_COOKIE_SECURE=false

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /datos debe ser un volumen persistente: ahí vive el archivo SQLite.
VOLUME ["/datos"]
EXPOSE 8080

# serve.py genera la base de demostración en el primer arranque si no existe.
CMD ["python", "serve.py"]
