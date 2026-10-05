"""Da cifras propias a los 19 casos del simulador de práctica, sin romper la contabilidad.

Cada estudiante recibe un factor propio por caso (0,70 a 1,35) que se aplica a TODAS las cifras
del caso: el enunciado, los datos de la transacción, la solución esperada y la explicación. Como
el factor es el mismo para todas las líneas del caso, las proporciones se mantienen (el IVA sigue
siendo el 15 % del subtotal, el margen y el costo conservan su relación) y la partida doble sigue
cuadrando: si el redondeo deja un centavo suelto, se corrige en la línea mayor del asiento.

El trabajo se hace SIEMPRE desde los casos originales de la plantilla, nunca sobre los ya
modificados, así que es idempotente: repetirlo no acumula cambios.

    python database/variar_casos.py              # informe
    python database/variar_casos.py --aplicar    # aplica a todas las aulas
    python database/variar_casos.py --aplicar --aula ealcivar4002
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

MINIMO, MAXIMO = 0.70, 1.35
CAMPOS_TEXTO = ("enunciado", "pistas_json", "explicacion_pedagogica")


def factor(usuario, caso_id):
    """Factor propio y estable del caso para ese estudiante (dos decimales)."""
    dato = hashlib.sha256(("%s|caso-%s" % (usuario, caso_id)).encode()).hexdigest()
    pasos = int(round((MAXIMO - MINIMO) * 100))
    return round(MINIMO + (int(dato[:8], 16) % (pasos + 1)) / 100.0, 2)


def descubre(ruta):
    """Casos originales de la plantilla (nunca los ya variados)."""
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    try:
        casos = {}
        for fila in conexion.execute("SELECT * FROM casos_simulacion"):
            casos[fila["id"]] = {c: fila[c] for c in ("titulo", "enunciado",
                                                      "datos_transaccion_json",
                                                      "solucion_esperada_json", "pistas_json",
                                                      "explicacion_pedagogica",
                                                      "documento_fuente_numero")}
        return casos
    finally:
        conexion.close()


def escala_numero(valor, k):
    return round(float(valor) * k, 2)


def escala_json(objeto, k, claves_sin_tocar=()):
    """Multiplica los números decimales del JSON (los identificadores enteros no se tocan)."""
    if isinstance(objeto, dict):
        return {clave: escala_json(valor, k, claves_sin_tocar)
                for clave, valor in objeto.items()}
    if isinstance(objeto, list):
        return [escala_json(valor, k, claves_sin_tocar) for valor in objeto]
    if isinstance(objeto, float):
        return escala_numero(objeto, k)
    return objeto


def cuadra_asiento(lineas):
    """Deja el asiento cuadrado ajustando el centavo del redondeo en la línea mayor.

    Si sobra débito hay que reducirlo (y al revés): se ajusta la línea más grande del lado que
    corresponde, nunca la del lado contrario, que empeoraría el descuadre.
    """
    debe = round(sum(float(l.get("debe") or 0) for l in lineas), 2)
    haber = round(sum(float(l.get("haber") or 0) for l in lineas), 2)
    diferencia = round(debe - haber, 2)
    if not diferencia:
        return lineas, 0.0
    lado = "debe" if diferencia > 0 else "haber"
    candidatas = [l for l in lineas if float(l.get(lado) or 0)]
    if candidatas:
        mayor = max(candidatas, key=lambda l: float(l.get(lado) or 0))
        # Si sobra débito se rebaja el debe; si sobra haber, se rebaja el haber (la diferencia
        # viene con signo, así que el ajuste del haber se suma).
        mayor[lado] = round(float(mayor[lado]) - diferencia, 2) if lado == "debe" \
            else round(float(mayor[lado]) + diferencia, 2)
    else:                                  # asiento con un solo lado: se ajusta el contrario
        contrario = "haber" if lado == "debe" else "debe"
        mayor = max(lineas, key=lambda l: float(l.get(contrario) or 0))
        mayor[contrario] = round(float(mayor[contrario]) + diferencia, 2) if lado == "debe" \
            else round(float(mayor[contrario]) - diferencia, 2)
    return lineas, diferencia


def reemplaza_cifras(texto, equivalencias):
    """Cambia en el texto las cifras que corresponden a valores del caso (formato con punto)."""
    if not texto:
        return texto
    def cambia(coincidencia):
        valor = float(coincidencia.group(0))
        nuevo = equivalencias.get(round(valor, 2))
        if nuevo is None:
            return coincidencia.group(0)
        return ("%.2f" % nuevo)
    return re.sub(r"\d+(?:\.\d{1,2})?", cambia, texto)


def aplica_caso(caso, k):
    """Devuelve el caso con las cifras del estudiante."""
    equivalencias = {}
    datos = json.loads(caso["datos_transaccion_json"] or "{}")
    solucion = json.loads(caso["solucion_esperada_json"] or "{}")

    nuevos_datos = escala_json(datos, k)
    nueva_solucion = {}
    for nombre, asiento in solucion.items():
        if isinstance(asiento, list):
            escalado = escala_json(asiento, k)
            escalado, _ = cuadra_asiento(escalado)
            nueva_solucion[nombre] = escalado
        else:
            nueva_solucion[nombre] = escala_json(asiento, k)

    # Mapa de "cifra vieja" -> "cifra nueva" para los textos, tomando los valores del caso.
    def recoge(viejo, nuevo):
        if isinstance(viejo, dict) and isinstance(nuevo, dict):
            for clave in viejo:
                recoge(viejo[clave], nuevo.get(clave))
        elif isinstance(viejo, list) and isinstance(nuevo, list):
            for a, b in zip(viejo, nuevo):
                recoge(a, b)
        elif isinstance(viejo, float) and isinstance(nuevo, float):
            equivalencias[round(viejo, 2)] = nuevo
    recoge(datos, nuevos_datos)
    recoge(solucion, nueva_solucion)

    resultado = {
        "datos_transaccion_json": json.dumps(nuevos_datos, ensure_ascii=False),
        "solucion_esperada_json": json.dumps(nueva_solucion, ensure_ascii=False),
    }
    for campo in CAMPOS_TEXTO:
        resultado[campo] = reemplaza_cifras(caso[campo], equivalencias)

    # El número de documento fuente también es propio de cada estudiante.
    documento = caso["documento_fuente_numero"] or ""
    if documento:
        nuevo_documento = re.sub(r"\d{4,}$", lambda m: "%06d" % (int(hashlib.sha256(
            ("%s|%s|doc" % (resultado["datos_transaccion_json"][:24], k)).encode()
        ).hexdigest()[:6], 16) % 1000000), documento)
        resultado["documento_fuente_numero"] = nuevo_documento
        if nuevo_documento != documento:
            for campo in CAMPOS_TEXTO:
                if resultado.get(campo):
                    resultado[campo] = resultado[campo].replace(documento, nuevo_documento)
    else:
        resultado["documento_fuente_numero"] = documento
    return resultado


def aplica_en(ruta, originales, usuario, escribir=False):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    cambios = 0
    try:
        for fila in conexion.execute("SELECT * FROM casos_simulacion").fetchall():
            original = originales.get(fila["id"])
            if not original:
                continue
            nuevos = aplica_caso(original, factor(usuario, fila["id"]))
            for campo, valor in nuevos.items():
                if (fila[campo] or "") != (valor or ""):
                    cambios += 1
                    if escribir:
                        conexion.execute("UPDATE casos_simulacion SET %s = ? WHERE id = ?"
                                         % campo, (valor, fila["id"]))
        if escribir:
            conexion.commit()
    finally:
        conexion.close()
    return cambios


def main():
    analizador = argparse.ArgumentParser(description="Cifras propias en los casos del simulador.")
    analizador.add_argument("--aplicar", action="store_true", help="escribe los cambios")
    analizador.add_argument("--aula", help="solo este estudiante")
    argumentos = analizador.parse_args()

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plantilla = os.path.join(Config.RUTA_PLANTILLA, "aula_base.db")
    if not os.path.exists(plantilla):
        plantilla = os.path.join(raiz, "database", "plantilla", "aula_base.db")
    originales = descubre(plantilla)
    print("Casos originales tomados de la plantilla: %d" % len(originales))
    print("Modo: %s\n" % ("APLICAR" if argumentos.aplicar else "solo informe (agregue --aplicar)"))

    rutas = sorted(glob.glob(os.path.join(Config.RUTA_AULAS, "B", "*.db")))
    if argumentos.aula:
        usuario = argumentos.aula.split("@")[0]
        rutas = [r for r in rutas if os.path.basename(r) == "%s.db" % usuario]
        if not rutas:
            raise SystemExit("No encontré el aula de %s" % usuario)

    conteos = {}
    for ruta in rutas:
        usuario = os.path.basename(ruta)[:-3]
        conteos[ruta] = aplica_en(ruta, originales, usuario, escribir=argumentos.aplicar)

    if rutas:
        print("%-16s %8s %10s %10s   %s"
              % ("ESTUDIANTE", "CAMBIOS", "FACTOR", "CIFRA C1", "PRIMERA LÍNEA DEL ASIENTO"))
        print("-" * 96)
        original = originales.get(1)
        for ruta in rutas[:5]:
            usuario = os.path.basename(ruta)[:-3]
            solucion = json.loads(aplica_caso(original, factor(usuario, 1))["solucion_esperada_json"])
            primera = list(solucion.values())[0][0]
            print("%-16s %8d %10.2f %10.2f   %s %s"
                  % (usuario, conteos[ruta], factor(usuario, 1),
                     round(json.loads(original["datos_transaccion_json"])["total"] * factor(usuario, 1), 2),
                     primera["cuenta"], primera["debe"] or primera["haber"]))
        print("-" * 96)

    print("Aulas revisadas: %d | campos con cifras ajenas: %d" % (len(rutas), sum(conteos.values())))
    print("Aplicado. Las cifras quedan estables: repetirlo no las mueve." if argumentos.aplicar
          else "Ejecute con --aplicar para escribir.")


if __name__ == "__main__":
    sys.exit(main() or 0)
