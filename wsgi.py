"""
Punto de entrada WSGI del Simulador Integral de Sistema Contable.

Lo usan los servidores de producción:

    waitress-serve --host=0.0.0.0 --port=8080 wsgi:application   (Windows y Linux)
    gunicorn -w 2 -b 0.0.0.0:8080 wsgi:application               (Linux)
    gunicorn -k uvicorn.workers.UvicornWorker ...                (no aplica: app WSGI pura)

Para arrancar con el servidor de producción incluido en el proyecto:  python serve.py
"""

from app import create_app

application = create_app()
app = application

if __name__ == "__main__":
    from serve import main

    main()
