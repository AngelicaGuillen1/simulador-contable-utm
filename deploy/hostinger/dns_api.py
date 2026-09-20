"""Apunta el dominio al servidor del simulador usando la API de Hostinger (DNS).

Evita tener que editar el DNS a mano en el panel. El token se lee de un archivo, nunca se
pasa por la línea de comandos y no se imprime.

    # Ver cómo está la zona hoy
    python deploy/hostinger/dns_api.py --dominio simuladorcontablecaavgputm.tech \
        --ip 2.25.173.123 --token-archivo "C:/.../token_hostinger.txt" --ver

    # Aplicar el cambio (registros A de @ y www -> IP del servidor)
    python deploy/hostinger/dns_api.py --dominio simuladorcontablecaavgputm.tech \
        --ip 2.25.173.123 --token-archivo "C:/.../token_hostinger.txt"

La petición va con "overwrite": true y solo los registros A de @ y www, así que reemplaza
solamente esos dos y deja intactos los MX, TXT, CNAME y demás.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://developers.hostinger.com/api/dns/v1"


def llamar(metodo, ruta, token, cuerpo=None):
    peticion = urllib.request.Request(
        API + ruta, method=metodo,
        data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
        headers={"Authorization": "Bearer %s" % token,
                 "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(peticion, timeout=45) as respuesta:
            texto = respuesta.read().decode("utf-8", "ignore")
            try:
                return respuesta.status, (json.loads(texto) if texto.strip() else {})
            except ValueError:
                return respuesta.status, texto
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", "ignore")
        try:
            detalle = json.loads(detalle)
        except ValueError:
            pass
        return error.code, detalle
    except Exception as error:  # noqa: BLE001
        return None, "%s: %s" % (type(error).__name__, error)


def leer_token(ruta):
    if not os.path.exists(ruta):
        raise SystemExit("No está el archivo del token: %s" % ruta)
    with open(ruta, encoding="utf-8-sig") as entrada:
        for linea in entrada:
            linea = linea.strip()
            if linea and not linea.startswith("#"):
                return linea
    raise SystemExit("El archivo del token está vacío: %s" % ruta)


def contenidos(registro):
    """La API devuelve records = [{"content": "...", "is_disabled": false}]."""
    salida = []
    for elemento in registro.get("records") or []:
        if isinstance(elemento, dict):
            salida.append(elemento.get("content"))
        else:
            salida.append(elemento)
    return [c for c in salida if c]


def main():
    analizador = argparse.ArgumentParser(description="Apunta el dominio al servidor por la API de Hostinger.")
    analizador.add_argument("--dominio", required=True)
    analizador.add_argument("--ip", required=True)
    analizador.add_argument("--token-archivo", required=True)
    analizador.add_argument("--ver", action="store_true", help="solo muestra la zona actual")
    argumentos = analizador.parse_args()

    token = leer_token(argumentos.token_archivo)

    print("=== Zona DNS actual de %s ===" % argumentos.dominio)
    estado, zona = llamar("GET", "/zones/%s" % argumentos.dominio, token)
    if estado != 200:
        print("   la API respondió %s" % estado)
        print("   detalle:", json.dumps(zona, ensure_ascii=False)[:500])
        if estado in (401, 403):
            print("\n   El token no sirve para DNS: revise que sea válido y que no esté vencido.")
        raise SystemExit(1)

    registros = zona if isinstance(zona, list) else (zona.get("records") or [])
    for registro in registros:
        print("   %-6s %-30s ttl=%-7s %s"
              % (registro.get("type"), registro.get("name"), registro.get("ttl"),
                 ", ".join(str(c) for c in contenidos(registro))))

    if argumentos.ver:
        raise SystemExit(0)

    # Solo se tocan los registros A de la raíz y de www.
    zona_nueva = []
    cambios = []
    tiene_a_raiz = False
    tiene_a_www = False
    for registro in registros:
        tipo = (registro.get("type") or "").upper()
        nombre = (registro.get("name") or "").strip()
        anterior = contenidos(registro)
        if tipo == "A" and nombre in ("@", ""):
            tiene_a_raiz = True
            zona_nueva.append({"name": "@", "type": "A", "ttl": registro.get("ttl") or 3600,
                               "records": [{"content": argumentos.ip}]})
            cambios.append(("A @", anterior, argumentos.ip))
        elif tipo == "A" and nombre == "www":
            tiene_a_www = True
            zona_nueva.append({"name": "www", "type": "A", "ttl": registro.get("ttl") or 3600,
                               "records": [{"content": argumentos.ip}]})
            cambios.append(("A www", anterior, argumentos.ip))

    if not tiene_a_raiz:
        zona_nueva.append({"name": "@", "type": "A", "ttl": 3600,
                           "records": [{"content": argumentos.ip}]})
        cambios.append(("A @ (nuevo)", [], argumentos.ip))

    if not tiene_a_www:
        tiene_cname_www = any((r.get("type") or "").upper() == "CNAME"
                              and (r.get("name") or "").strip() in ("www", "www.%s" % argumentos.dominio)
                              for r in registros)
        if tiene_cname_www:
            print("\n   www tiene un CNAME: se deja como está (seguirá al dominio solo).")
        else:
            zona_nueva.append({"name": "www", "type": "A", "ttl": 3600,
                               "records": [{"content": argumentos.ip}]})
            cambios.append(("A www (nuevo)", [], argumentos.ip))

    print("\n=== Cambios a aplicar ===")
    for etiqueta, antes, despues in cambios:
        print("   %-14s %-30s -> %s"
              % (etiqueta, ", ".join(str(a) for a in antes) or "(nuevo)", despues))
    print("   (MX, TXT, CNAME, NS: no se tocan)")

    cuerpo = {"overwrite": True, "zone": zona_nueva}

    print("\n=== 1/2 Validación previa (Hostinger) ===")
    estado, resultado = llamar("POST", "/zones/%s/validate" % argumentos.dominio, token, cuerpo)
    print("   respuesta:", estado,
          json.dumps(resultado, ensure_ascii=False)[:300] if isinstance(resultado, dict) else resultado)
    if estado not in (200, 201, 204):
        print("   La validación no pasó. No se cambió nada.")
        raise SystemExit(1)

    print("\n=== 2/2 Aplicando el cambio ===")
    estado, resultado = llamar("PUT", "/zones/%s" % argumentos.dominio, token, cuerpo)
    print("   respuesta:", estado,
          json.dumps(resultado, ensure_ascii=False)[:300] if isinstance(resultado, dict) else resultado)
    if estado not in (200, 201, 204):
        raise SystemExit(1)

    print("\n=== Zona después del cambio ===")
    estado, zona = llamar("GET", "/zones/%s" % argumentos.dominio, token)
    for registro in (zona if isinstance(zona, list) else zona.get("records") or []):
        if (registro.get("type") or "").upper() in ("A", "CNAME"):
            print("   %-6s %-30s %s" % (registro.get("type"), registro.get("name"),
                                        ", ".join(str(c) for c in contenidos(registro))))
    print("\n   Hecho. La propagación en Internet puede tardar de minutos a un par de horas.")


if __name__ == "__main__":
    sys.exit(main() or 0)
