#!/usr/bin/env python
"""
Verificador de despliegue del Simulador Integral de Sistema Contable.

Comprueba, contra un servidor ya desplegado, que:
  * la aplicación está operativa y responde con el servidor de producción;
  * todos los módulos de la interfaz devuelven 200 y sin rastros de error;
  * el manual de usuario se sirve y su fuente es descargable;
  * los directorios internos (database/, docs/, deploy/) NO quedan expuestos;
  * la base de datos responde con la integridad contable esperada.

Uso:
    python deploy/verificar_despliegue.py
    python deploy/verificar_despliegue.py --url https://contabilidad.utm.edu.ec
    python deploy/verificar_despliegue.py --url http://127.0.0.1:8080 --usuario admin --password admin123

Salida: código 0 si todo está correcto, 1 si alguna comprobación falla.
"""

import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

RUTAS_GET = [
    "/dashboard",
    "/contabilidad/cuentas", "/contabilidad/diario", "/contabilidad/mayor",
    "/contabilidad/balance", "/contabilidad/ajustes", "/contabilidad/cierre",
    "/ventas", "/ventas/nueva", "/servicios", "/compras/", "/compras/nueva",
    "/inventarios/", "/inventarios/productos", "/inventarios/kardex", "/inventarios/kardex/1",
    "/inventarios/stock", "/clientes", "/proveedores", "/cuentas-cobrar", "/cuentas-pagar",
    "/caja", "/bancos", "/conciliacion", "/impuestos/", "/documentos/",
    "/estados-financieros/", "/estados-financieros/resultados", "/estados-financieros/flujo-efectivo",
    "/estados-financieros/situacion-financiera",
    "/simulador", "/evaluaciones", "/docente/panel", "/tutor/", "/reportes/",
    "/admin/", "/admin/usuarios", "/admin/impuestos", "/admin/auditoria",
    "/manual",
]

RUTAS_API = [
    "/api/health", "/api/dashboard", "/api/accounts", "/api/products", "/api/inventory",
    "/api/inventory/alerts", "/api/customers", "/api/suppliers", "/api/receivables",
    "/api/payables", "/api/treasury", "/api/taxes", "/api/statements?tipo=situacion-financiera",
    "/api/statements?tipo=resultados", "/api/documents", "/api/simulations", "/api/periods",
    "/api/audit", "/api/tools", "/api/search?q=caja",
]

# Endpoints que existen pero solo admiten POST: deben responder 405 a un GET.
RUTAS_SOLO_POST = ["/api/sales", "/api/purchases", "/api/collections", "/api/payments",
                   "/api/journal/validate", "/api/evaluate"]

RUTAS_PRIVADAS = [
    "/database/simulator.db",
    "/database/seed_data.py",
    "/docs/MANUAL_DE_USUARIO.md",
    "/deploy/backup_db.py",
    "/config.py",
    "/.env",
]


class Cliente:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def pedir(self, ruta, datos=None, cabeceras=None):
        url = self.base + ruta
        cuerpo = urllib.parse.urlencode(datos).encode() if datos else None
        peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras or {})
        try:
            with self.opener.open(peticion, timeout=30) as respuesta:
                return respuesta.status, respuesta.read(), dict(respuesta.headers)
        except urllib.error.HTTPError as error:
            return error.code, error.read(), dict(error.headers)
        except urllib.error.URLError as error:
            return 0, str(error).encode(), {}

    def json(self, ruta):
        estado, cuerpo, _ = self.pedir(ruta)
        if estado != 200:
            return estado, None
        try:
            return estado, json.loads(cuerpo.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return estado, None


def main():
    parser = argparse.ArgumentParser(description="Verificación de un despliegue del simulador")
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="URL base del despliegue")
    parser.add_argument("--usuario", default="admin")
    parser.add_argument("--password", default="admin123")
    args = parser.parse_args()

    cliente = Cliente(args.url)
    fallos = []
    avisos = []

    print("=" * 78)
    print(f" VERIFICACION DEL DESPLIEGUE - {args.url}")
    print("=" * 78)

    # 1) Estado del servicio
    estado, datos = cliente.json("/api/health")
    if estado == 200 and datos:
        print(f" [OK]  /api/health -> {datos.get('estado')} | período: "
              f"{datos.get('periodo_activo', {}).get('nombre')} | fecha de trabajo: {datos.get('fecha_trabajo')}")
    else:
        fallos.append(f"/api/health devolvió {estado}: el servicio no está operativo")
        print(f" [FALLA] /api/health -> {estado}")

    # 2) Servidor de producción
    estado, _, cabeceras = cliente.pedir("/")
    servidor = cabeceras.get("Server", "desconocido")
    if "waitress" in servidor.lower():
        print(f" [OK]  Servidor de producción activo ({servidor})")
    else:
        avisos.append(f"El encabezado Server es '{servidor}': confirme que no está usando el servidor de desarrollo")

    # 3) Sesión
    estado, cuerpo, _ = cliente.pedir("/login", datos={"username": args.usuario, "password": args.password})
    if estado == 200 and b"dashboard" in cuerpo.lower():
        print(f" [OK]  Inicio de sesión correcto como '{args.usuario}'")
    else:
        fallos.append(f"No fue posible iniciar sesión como '{args.usuario}'")
        print(f" [FALLA] Inicio de sesión -> {estado}")

    # 4) Módulos de la interfaz
    malos = []
    for ruta in RUTAS_GET:
        estado, cuerpo, _ = cliente.pedir(ruta)
        texto = cuerpo.decode("utf-8", "ignore")
        if estado != 200 or "Traceback" in texto or len(texto) < 500:
            malos.append(f"{ruta} ({estado})")
    if malos:
        fallos.append("Módulos con respuesta incorrecta: " + ", ".join(malos))
        print(f" [FALLA] {len(malos)} módulos con problemas: {', '.join(malos[:6])}")
    else:
        print(f" [OK]  {len(RUTAS_GET)} módulos de la interfaz responden 200 y sin errores")

    # 5) Endpoints de la API
    malos_api = []
    for ruta in RUTAS_API:
        estado, cuerpo, _ = cliente.pedir(ruta)
        if estado != 200:
            malos_api.append(f"{ruta} ({estado})")
        else:
            try:
                json.loads(cuerpo.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                malos_api.append(f"{ruta} (no devuelve JSON)")
    if malos_api:
        fallos.append("Endpoints de la API con problemas: " + ", ".join(malos_api))
        print(f" [FALLA] {len(malos_api)} endpoints de la API con problemas: {', '.join(malos_api[:5])}")
    else:
        print(f" [OK]  {len(RUTAS_API)} endpoints de la API responden 200 con JSON válido")

    # 5.b) Endpoints de escritura: deben existir y rechazar el método GET (405)
    inexistentes = []
    for ruta in RUTAS_SOLO_POST:
        estado, _, _ = cliente.pedir(ruta)
        if estado != 405:
            inexistentes.append(f"{ruta} ({estado})")
    if inexistentes:
        fallos.append("Endpoints de escritura con respuesta inesperada: " + ", ".join(inexistentes))
        print(f" [FALLA] Endpoints POST con problemas: {', '.join(inexistentes)}")
    else:
        print(f" [OK]  {len(RUTAS_SOLO_POST)} endpoints de escritura existen y exigen POST")

    # 6) Manual de usuario
    estado, cuerpo, _ = cliente.pedir("/manual")
    texto_manual = cuerpo.decode("utf-8", "ignore")
    if estado == 200 and "Manual de Usuario" in texto_manual and len(texto_manual) > 20000:
        print(f" [OK]  /manual sirve el manual ({len(texto_manual):,} caracteres)")
    else:
        fallos.append(f"/manual devolvió {estado} o contenido incompleto")

    estado, cuerpo, cabeceras = cliente.pedir("/manual/fuente")
    if estado == 200 and "attachment" in cabeceras.get("Content-Disposition", ""):
        print(f" [OK]  /manual/fuente descarga la fuente Markdown ({len(cuerpo):,} bytes)")
    else:
        fallos.append(f"/manual/fuente devolvió {estado}")

    # 7) Archivos internos no expuestos
    expuestos = []
    for ruta in RUTAS_PRIVADAS:
        estado, _, _ = cliente.pedir(ruta)
        if estado == 200:
            expuestos.append(ruta)
    if expuestos:
        fallos.append("Archivos internos accesibles públicamente: " + ", ".join(expuestos))
        print(f" [FALLA] Archivos internos expuestos: {', '.join(expuestos)}")
    else:
        print(f" [OK]  {len(RUTAS_PRIVADAS)} rutas internas (base de datos, docs, deploy) NO están expuestas")

    # 8) Integridad contable
    estado, datos = cliente.json("/api/statements?tipo=situacion-financiera")
    if estado == 200 and datos:
        balance = datos.get("statement") or datos
        activo = balance.get("total_activo")
        pasivo_patrimonio = balance.get("total_pasivo_y_patrimonio")
        diferencia = balance.get("diferencia")
        if activo is not None and round(float(activo), 2) == round(float(pasivo_patrimonio), 2):
            print(f" [OK]  Ecuación patrimonial: Activo {activo:,.2f} = Pasivo + Patrimonio "
                  f"{pasivo_patrimonio:,.2f} (diferencia {diferencia})")
        else:
            fallos.append(f"La ecuación patrimonial no cuadra: {activo} vs {pasivo_patrimonio}")

    # Resumen
    print("-" * 78)
    if avisos:
        for aviso in avisos:
            print(f" [AVISO] {aviso}")
    if fallos:
        print(f" RESULTADO: {len(fallos)} comprobación(es) FALLIDA(S)")
        for fallo in fallos:
            print(f"   - {fallo}")
        return 1
    print(" RESULTADO: DESPLIEGUE VERIFICADO CORRECTAMENTE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
