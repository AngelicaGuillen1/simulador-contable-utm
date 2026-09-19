# -*- coding: utf-8 -*-
"""Servicio del BANCO DE CASOS PRÁCTICOS DE LOS LIBROS (§61) y de las reglas de trazabilidad
de las fuentes (§62) del Prompt Maestro v2.

Responsabilidades
-----------------
* Leer el banco de casos y sus fichas (DATOS en la base de control, no en el código).
* Aplicar las 9 reglas de §62 (8 de trazabilidad de fuentes + §62.8 del catálogo semilla):
  erratas corregidas y registradas, tarifas demostrativas editables, advertencia de IVA y
  retenciones, etiquetas de dato reconstruido, práctica sin solución visible, aviso de marco
  extranjero, doble numeración de páginas y ficha obligatoria antes de activar un caso.
* Verificar los INTENTOS de los estudiantes: puntaje, retroalimentación, registro del intento
  y control de intentos máximos. Cuando la fuente no trae solución, la verificación es
  MECÁNICA y NO OFICIAL (§62.5).

Convenciones del proyecto:
    * Se usa `models.get_db_control()` (contenido académico compartido) y `dicts_from_rows`.
    * Todas las funciones aceptan `db_path` para las pruebas.
    * Los errores de negocio son `ErrorCasoLibro` con `estado_http`.
"""

import json
import os
import re
import sqlite3
import unicodedata
from datetime import datetime

from config import Config
from models import dicts_from_rows
from database.banco_casos_libros import (
    ADVERTENCIA_CATALOGO_SEMILLA, ADVERTENCIA_IVA_RETENCIONES, ADVERTENCIA_MARCO_EXTRANJERO,
    ETIQUETA_CALCULADA, ETIQUETA_RECONSTRUIDO, ETIQUETA_TASAS, MODOS_CATALOGO,
    PLAN_CUENTAS_BASE, REGLAS_MECANICAS, TASAS_DEMOSTRATIVAS, cita_fuente, formato_es_ec,
    paginas_pdf,
)
from database.esquema_casos_libros import ficha_incompleta

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"
TOLERANCIA = 0.02
PUNTAJE = {"cuentas": 40.0, "posicion": 30.0, "importes": 20.0, "cuadre": 10.0}
UMBRAL_CORRECTO = 85.0
UMBRAL_PARCIAL = 50.0

# Sinónimos de nombres de cuenta usados por las fuentes (libros) frente al catálogo semilla.
SINONIMOS_CUENTAS = {
    "ventas": "41101",
    "venta de mercaderias": "41101",
    "venta de bienes": "41101",
    "ingresos por servicios": "41201",
    "ingresos por mantenimiento": "41201",
    "comisiones ganadas": "42201",
    "intereses por ventas a credito": "42201",
    "intereses ganados": "42201",
    "costo de ventas": "51301",
    "costo de los bienes vendidos": "51301",
    "costo de mercaderias vendidas": "51301",
    "inventarios": "11402",
    "inventario de mercaderia": "11402",
    "inventario de mercaderias": "11402",
    "mercaderias": "11402",
    "inv. de mercaderia en almacen comprada a terceros": "11402",
    "suministros": "11405",
    "suministros de oficina": "11405",
    "materiales y suministros de limpieza": "11401",
    "inv. de suministros o materiales a ser consumidos": "11401",
    "cuentas por cobrar": "11301",
    "cuentas y documentos por cobrar": "11301",
    "cuentas y documentos por cobrar no relacionados": "11301",
    "cuentas y documentos por cobrar comerciales": "11301",
    "cuentas por pagar": "21101",
    "proveedores": "21101",
    "cuentas y documentos por pagar proveedores": "21101",
    "documentos por pagar": "21104",
    "efectivo": "11101",
    "caja": "11101",
    "bancos": "11103",
    "banco": "11103",
    "iva cobrado": "21301",
    "iva ventas": "21301",
    "iva en ventas": "21301",
    "iva compras": "11601",
    "iva pagado": "11601",
    "capital": "31101",
    "capital social": "31101",
    "capital suscrito y pagado": "31101",
    "terrenos": "12101",
    "terreno": "12101",
    "muebles y enseres": "12104",
    "maquinaria y equipo": "12105",
    "maquinaria": "12105",
    "equipo de computacion": "12107",
    "computadora": "12107",
    "sueldos y salarios": "51101",
    "gastos de personal": "51101",
    "publicidad y propaganda": "51204",
    "aporte personal 9,45 %": "21501",
    "aporte personal": "21501",
    "utilidad neta del periodo": "31401",
    "participacion trabajadores por pagar": "21403",
    "impuesto a la renta por pagar": "21302",
    "perdidas y ganancias (cuenta transitoria de cierre)": "61302",
}


class ErrorCasoLibro(ValueError):
    """Error de negocio del banco de casos."""

    def __init__(self, mensaje, estado_http=400, codigo="VALIDACION"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.estado_http = estado_http
        self.codigo = codigo


class CasoNoEncontrado(ErrorCasoLibro):
    def __init__(self, mensaje="El caso no existe en el banco de casos prácticos."):
        super().__init__(mensaje, estado_http=404, codigo="CASO_NO_ENCONTRADO")


class CasoNoDisponible(ErrorCasoLibro):
    def __init__(self, mensaje):
        super().__init__(mensaje, estado_http=409, codigo="CASO_NO_DISPONIBLE")


class SinIntentos(ErrorCasoLibro):
    def __init__(self, mensaje):
        super().__init__(mensaje, estado_http=409, codigo="SIN_INTENTOS")


# --------------------------------------------------------------------------- Utilidades
def _conectar(db_path=None):
    ruta = db_path or Config.DATABASE_PATH
    conn = sqlite3.connect(ruta, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def normalizar(texto):
    """minúsculas, sin acentos ni puntuación: permite comparar nombres de cuenta."""
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = "".join(c for c in base if not unicodedata.combining(c)).lower()
    return " ".join("".join(c if c.isalnum() or c == "%" else " " for c in base).split())


def _json_cargar(texto, por_defecto):
    if not texto:
        return por_defecto
    try:
        return json.loads(texto)
    except (TypeError, ValueError):
        return por_defecto


def _fila_a_caso(fila, para_estudiante=False):
    """Convierte una fila de `casos_libros` en el diccionario de la ficha del caso.

    Cuando `para_estudiante=True` se aplica §62.5: nunca se entrega la solución de un caso
    cuya solución no esté en la fuente, ni los asientos esperados de esos casos.
    """
    caso = dict(fila)
    caso["datos"] = _json_cargar(caso.pop("datos_json", None), [])
    caso["asientos_esperados"] = _json_cargar(caso.pop("asientos_esperados_json", None), [])
    caso["saldos_finales"] = _json_cargar(caso.pop("saldos_finales_json", None), {})
    caso["totales_verificados"] = _json_cargar(caso.pop("totales_verificados_json", None), {})
    caso["solucion"] = _json_cargar(caso.pop("solucion_json", None), [])
    caso["correcciones"] = _json_cargar(caso.pop("correcciones_json", None), [])
    caso["etiquetas"] = _json_cargar(caso.pop("etiquetas_json", None), [])
    caso["advertencias"] = _json_cargar(caso.pop("advertencias_json", None), [])
    extra = _json_cargar(caso.pop("extra_json", None), {})
    caso.update(extra or {})
    caso["solucion_en_fuente"] = bool(caso.get("solucion_en_fuente"))
    caso["solucion_visible"] = bool(caso.get("solucion_visible"))
    caso["publicable"] = bool(caso.get("publicable"))
    caso["activo"] = bool(caso.get("activo"))
    caso["hubo_correccion"] = bool(caso.get("hubo_correccion"))
    caso["cita_fuente"] = caso.get("cita_fuente") or cita_fuente(caso.get("fuente_codigo"),
                                                                caso.get("paginas_impresas"))
    caso["fuentes_no_explican_iva_retenciones"] = True
    caso["advertencia_normativa"] = ADVERTENCIA_IVA_RETENCIONES
    caso["practica_sin_solucion"] = not caso["solucion_visible"]
    caso["es_dato_reconstruido"] = ETIQUETA_RECONSTRUIDO in (caso.get("etiquetas") or [])
    caso["solucion_calculada"] = ETIQUETA_CALCULADA in (caso.get("etiquetas") or [])
    # §62.4/§62.5 — solo es «respuesta oficial» la que se apoya en una solución publicada y
    # verificada por la fuente: nunca una solución calculada ni un dato reconstruido.
    caso["respuesta_oficial_permitida"] = bool(
        caso["solucion_en_fuente"] and not caso["solucion_calculada"])
    if not caso["respuesta_oficial_permitida"]:
        caso["motivo_no_oficial"] = (
            "Solución no publicada por la fuente o dato reconstruido: la cifra no puede usarse como "
            "respuesta oficial de una actividad evaluable (§62.4 y §62.5). La corrección queda a cargo "
            "del docente o de reglas mecánicas verificables.")
    if _es_contexto_externo(caso.get("contexto_normativo")):
        caso["advertencia_marco_externo"] = ADVERTENCIA_MARCO_EXTRANJERO
    if para_estudiante and not caso["solucion_visible"]:
        caso["solucion"] = []
        caso["solucion_referencial"] = {}
        caso["asientos_esperados"] = []
        caso["saldos_finales"] = {}
        caso["oculta_solucion"] = True
    caso["ficha"] = ficha_del_caso(caso)
    return caso


def _es_contexto_externo(contexto):
    texto = (contexto or "").upper()
    return any(palabra in texto for palabra in ("EXTRANJERO", "ESTADOS UNIDOS", "COLOMBIA"))


def _fila_a_fuente(fila):
    fuente = dict(fila)
    fuente["erratas_conocidas"] = _json_cargar(fuente.pop("erratas_conocidas", None), [])
    fuente["notas"] = _json_cargar(fuente.pop("notas", None), [])
    return fuente


# --------------------------------------------------------------------------- Banco de casos
def listar_casos(filtros=None, para_estudiante=False, db_path=None):
    """Lista los casos del banco §61 con su ficha resumida."""
    filtros = filtros or {}
    sql = "SELECT * FROM casos_libros WHERE 1 = 1"
    parametros = []
    if filtros.get("unidad"):
        sql += " AND unidad = ?"
        parametros.append(int(filtros["unidad"]))
    if filtros.get("estado_validacion"):
        sql += " AND estado_validacion = ?"
        parametros.append(str(filtros["estado_validacion"]).upper())
    if filtros.get("fuente"):
        sql += " AND fuente_codigo = ?"
        parametros.append(str(filtros["fuente"]).upper())
    if filtros.get("tipo"):
        sql += " AND tipo = ?"
        parametros.append(str(filtros["tipo"]).upper())
    if para_estudiante or str(filtros.get("solo_publicados") or "") in ("1", "true", "on"):
        sql += " AND activo = 1 AND publicable = 1"
    texto = (filtros.get("q") or "").strip()
    if texto:
        sql += " AND (nombre LIKE ? OR enunciado LIKE ? OR codigo LIKE ?)"
        patron = "%%%s%%" % texto
        parametros.extend([patron, patron, patron])
    sql += " ORDER BY numero ASC"
    conn = _conectar(db_path)
    try:
        filas = conn.execute(sql, parametros).fetchall()
        return [_fila_a_caso(f, para_estudiante=para_estudiante) for f in filas]
    finally:
        conn.close()


def obtener_caso(codigo, para_estudiante=False, db_path=None):
    """Ficha completa de un caso (lanza CasoNoEncontrado si no existe)."""
    conn = _conectar(db_path)
    try:
        fila = conn.execute("SELECT * FROM casos_libros WHERE codigo = ?",
                            (str(codigo or "").strip().upper(),)).fetchone()
        if not fila:
            raise CasoNoEncontrado("El caso %s no existe en el banco de casos prácticos." % codigo)
        caso = _fila_a_caso(fila, para_estudiante=para_estudiante)
        caso["trazabilidad"] = [dict(r) for r in conn.execute(
            "SELECT tipo, regla_codigo, campo, valor_libro, valor_aplicado, razon, registrado_en "
            "FROM casos_libros_trazabilidad WHERE caso_codigo = ? ORDER BY id",
            (caso["codigo"],)).fetchall()]
        caso["fuente_detalle"] = None
        fila_fuente = conn.execute("SELECT * FROM casos_libros_fuentes WHERE codigo = ?",
                                   (caso.get("fuente_codigo"),)).fetchone()
        if fila_fuente:
            caso["fuente_detalle"] = _fila_a_fuente(fila_fuente)
        caso["ficha"] = ficha_del_caso(caso)
        return caso
    finally:
        conn.close()


def ficha_del_caso(caso):
    """§62.9 — ficha obligatoria: fuente completa, página, año, solución y correcciones."""
    return {
        "codigo": caso.get("codigo"),
        "nombre": caso.get("nombre"),
        "fuente": caso.get("fuente_nombre") or caso.get("fuente_codigo"),
        "fuente_codigo": caso.get("fuente_codigo"),
        "paginas_impresas": caso.get("paginas_impresas"),
        "paginas_pdf": caso.get("paginas_pdf"),
        "cita": caso.get("cita_fuente"),
        "anio": caso.get("anio"),
        "estado_validacion": caso.get("estado_validacion"),
        "solucion_en_fuente": caso.get("solucion_en_fuente"),
        "solucion_visible": caso.get("solucion_visible"),
        "correccion_de_erratas": caso.get("hubo_correccion"),
        "correcciones": caso.get("correcciones") or [],
        "etiquetas": caso.get("etiquetas") or [],
        "contexto_normativo": caso.get("contexto_normativo"),
        "completa": not ficha_incompleta(caso),
        "falta": ficha_incompleta(caso),
    }


def resumen_banco(db_path=None):
    """Conteo del banco por estado de validación (para la interfaz y las pruebas)."""
    conn = _conectar(db_path)
    try:
        filas = conn.execute(
            "SELECT estado_validacion, COUNT(*) AS n FROM casos_libros GROUP BY estado_validacion"
        ).fetchall()
        por_estado = {f["estado_validacion"]: f["n"] for f in filas}
        total = conn.execute("SELECT COUNT(*) AS n FROM casos_libros").fetchone()["n"]
        activos = conn.execute("SELECT COUNT(*) AS n FROM casos_libros WHERE activo = 1 AND publicable = 1"
                               ).fetchone()["n"]
        con_correccion = conn.execute(
            "SELECT COUNT(*) AS n FROM casos_libros WHERE hubo_correccion = 1").fetchone()["n"]
        sin_solucion = conn.execute(
            "SELECT COUNT(*) AS n FROM casos_libros WHERE solucion_en_fuente = 0").fetchone()["n"]
        reconstruidos = conn.execute(
            "SELECT COUNT(*) AS n FROM casos_libros WHERE etiquetas_json LIKE ?",
            ("%%%s%%" % ETIQUETA_RECONSTRUIDO,)).fetchone()["n"]
        return {"total": total, "por_estado": por_estado, "activos": activos,
                "con_correccion_de_erratas": con_correccion, "sin_solucion_en_fuente": sin_solucion,
                "con_dato_reconstruido": reconstruidos}
    finally:
        conn.close()


def fuentes(db_path=None):
    """Fuentes de los libros con su correlación de páginas y su contexto normativo."""
    conn = _conectar(db_path)
    try:
        return [_fila_a_fuente(f) for f in conn.execute(
            "SELECT * FROM casos_libros_fuentes ORDER BY codigo").fetchall()]
    finally:
        conn.close()


def reglas(solo_trazabilidad=False, db_path=None):
    """Reglas §62 almacenadas como datos (las 9, o solo las 8 de trazabilidad de fuentes)."""
    sql = "SELECT * FROM casos_libros_reglas WHERE codigo LIKE 'R62.%'"
    if solo_trazabilidad:
        sql += " AND trazabilidad_fuentes = 1"
    sql += " ORDER BY numero"
    conn = _conectar(db_path)
    try:
        return [dict(f) for f in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def erratas_catalogo(db_path=None):
    """Erratas del plan de cuentas de la fuente (§59.10) que no deben replicarse."""
    conn = _conectar(db_path)
    try:
        return [dict(f) for f in conn.execute(
            "SELECT * FROM casos_libros_reglas WHERE codigo LIKE 'E59.%' ORDER BY numero").fetchall()]
    finally:
        conn.close()


def modos_catalogo():
    """§62.8 — modos de catálogo de cuentas autorizados."""
    return list(MODOS_CATALOGO)


def advertencias_trazabilidad():
    """Advertencias fixas que la interfaz debe mostrar (§62.3, §62.6 y §62.8)."""
    return {
        "iva_retenciones": ADVERTENCIA_IVA_RETENCIONES,
        "marco_extranjero": ADVERTENCIA_MARCO_EXTRANJERO,
        "catalogo_semilla": ADVERTENCIA_CATALOGO_SEMILLA,
        "etiqueta_tasas": ETIQUETA_TASAS,
        "etiqueta_reconstruido": ETIQUETA_RECONSTRUIDO,
        "etiqueta_calculada": ETIQUETA_CALCULADA,
    }


def activar_caso(codigo, activo=True, db_path=None):
    """Activa o desactiva un caso. §62.9: no se activa un caso con ficha incompleta."""
    caso = obtener_caso(codigo, db_path=db_path)
    if activo:
        faltantes = ficha_incompleta(caso)
        if faltantes:
            raise ErrorCasoLibro(
                "El caso %s no puede activarse: su ficha está incompleta (%s). §62.9 exige fuente "
                "completa, página, año, si la solución está en la fuente y si hubo corrección de "
                "erratas." % (caso["codigo"], ", ".join(faltantes)), estado_http=409,
                codigo="FICHA_INCOMPLETA")
    conn = _conectar(db_path)
    try:
        conn.execute("UPDATE casos_libros SET activo = ? WHERE codigo = ?",
                     (1 if activo else 0, caso["codigo"]))
        conn.commit()
    finally:
        conn.close()
    return obtener_caso(caso["codigo"], db_path=db_path)


# --------------------------------------------------------------------------- Tarifas (§62.2)
def _nombre_parametro(clave):
    return "academico.tasa.%s" % clave


def tasas_demostrativas(db_path=None):
    """Tarifas de las fuentes etiquetadas como «Configuración académica / demostrativa».

    Lee el valor vigente de la tabla `parametros` de la base de control y lo combina con el
    dato de la fuente. Nunca se fija en código: el docente puede editarlo (§62.2).
    """
    conn = _conectar(db_path)
    try:
        guardados = {f["clave"]: f["valor"] for f in conn.execute(
            "SELECT clave, valor FROM parametros WHERE clave LIKE 'academico.tasa.%'").fetchall()}
    finally:
        conn.close()
    resultado = []
    for clave, ficha in TASAS_DEMOSTRATIVAS.items():
        item = dict(ficha)
        item["clave"] = clave
        item["valor_vigente"] = float(ficha["valor_fuente"])
        item["origen_valor"] = "fuente"
        guardado = guardados.get(_nombre_parametro(clave))
        if guardado not in (None, ""):
            try:
                item["valor_vigente"] = float(guardado)
                item["origen_valor"] = "configuración académica"
            except (TypeError, ValueError):
                pass
        item["editada"] = item["origen_valor"] == "configuración académica"
        resultado.append(item)
    return resultado


def ajustar_tasa_demostrativa(clave, valor, db_path=None):
    """Fija una tarifa demostrativa como parámetro editable de la base de control (§62.2)."""
    if clave not in TASAS_DEMOSTRATIVAS:
        raise ErrorCasoLibro("Tarifa demostrativa desconocida: %s" % clave)
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorCasoLibro("El valor de la tarifa debe ser numérico.")
    if numero < 0:
        raise ErrorCasoLibro("La tarifa no puede ser negativa.")
    ficha = TASAS_DEMOSTRATIVAS[clave]
    conn = _conectar(db_path)
    try:
        conn.execute("""
            INSERT INTO parametros (clave, valor, descripcion) VALUES (?, ?, ?)
            ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor,
                descripcion = COALESCE(excluded.descripcion, parametros.descripcion),
                actualizado_en = CURRENT_TIMESTAMP
        """, (_nombre_parametro(clave), str(numero),
              "%s · %s (editable por el docente)" % (ficha["nombre"], ETIQUETA_TASAS)))
        conn.commit()
    finally:
        conn.close()
    return [t for t in tasas_demostrativas(db_path=db_path) if t["clave"] == clave][0]


# --------------------------------------------------------------------------- Verificación
def _catalogo_cuentas(db_path=None):
    """Cuentas válidas: PLAN_CUENTAS_BASE + las cuentas registradas en el sistema."""
    catalogo = {}
    for codigo, valor in PLAN_CUENTAS_BASE.items():
        nombre, naturaleza = valor
        catalogo[str(codigo)] = {"codigo": str(codigo), "nombre": nombre, "naturaleza": naturaleza}
    conn = _conectar(db_path)
    try:
        try:
            filas = conn.execute("SELECT codigo, nombre, naturaleza FROM cuentas").fetchall()
        except sqlite3.Error:
            filas = []
        for fila in filas:
            codigo = str(fila["codigo"])
            naturaleza = str(fila["naturaleza"] or "").upper()
            catalogo.setdefault(codigo, {"codigo": codigo, "nombre": fila["nombre"],
                                         "naturaleza": naturaleza})
    finally:
        conn.close()
    return catalogo


def _indice_nombres(catalogo):
    indice = {}
    for cuenta in catalogo.values():
        indice.setdefault(normalizar(cuenta["nombre"]), cuenta["codigo"])
    for nombre, codigo in SINONIMOS_CUENTAS.items():
        indice.setdefault(normalizar(nombre), codigo)
    return indice


def _resolver_cuenta(linea, catalogo, indice):
    """Devuelve (cuenta, codigo) de una línea enviada por el estudiante.

    Acepta el código (``11101``) o el nombre de la cuenta (``Caja``), en cualquiera de los dos
    campos: el formulario de la interfaz admite «código o nombre».
    """
    codigo = str(linea.get("codigo") or linea.get("cuenta_codigo") or "").strip()
    nombre = str(linea.get("cuenta") or linea.get("cuenta_nombre") or "").strip()
    if codigo and codigo in catalogo:
        return catalogo[codigo], codigo
    if nombre and nombre in catalogo:
        return catalogo[nombre], nombre
    if not nombre:
        return None, codigo or None
    candidato = indice.get(normalizar(nombre))
    if candidato:
        return catalogo.get(candidato), candidato
    # Coincidencia parcial (el nombre del libro contiene o está contenido en el del catálogo).
    normalizado = normalizar(nombre)
    if len(normalizado) >= 5:
        for indice_nombre, indice_codigo in indice.items():
            if len(indice_nombre) >= 5 and (indice_nombre in normalizado
                                            or normalizado in indice_nombre):
                return catalogo.get(indice_codigo), indice_codigo
    return None, codigo or None


def _asientos_aplanados(caso):
    planos = []
    for asiento in caso.get("asientos_esperados") or []:
        for linea in asiento.get("lineas") or []:
            planos.append({
                "cuenta": linea.get("cuenta"),
                "codigo": str(linea.get("codigo") or ""),
                "debe": round(float(linea.get("debe") or 0.0), 2),
                "haber": round(float(linea.get("haber") or 0.0), 2),
                "glosa": asiento.get("glosa"),
                "subcaso": asiento.get("subcaso"),
                "letra": asiento.get("letra"),
            })
    return planos


_EXTRAER_NUMEROS = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:[.,]\d+)?)")


def _coincide_cuenta(esperada, variantes, codigo_estudiante):
    """True si la línea del estudiante corresponde a la cuenta esperada del caso.

    Compara por código y por nombre, admitiendo el nombre del libro (fuente) o el nombre del
    catálogo semilla cuando son sinónimos.
    """
    if codigo_estudiante and esperada.get("codigo") and codigo_estudiante == esperada["codigo"]:
        return True
    esperado = normalizar(esperada.get("cuenta"))
    if not esperado:
        return False
    for variante in variantes or ():
        if not variante:
            continue
        if esperado == variante:
            return True
        if len(esperado) >= 5 and len(variante) >= 5 and (esperado in variante or variante in esperado):
            return True
    return False


def _numeros_de_texto(texto):
    """Extrae cifras de un texto del libro (admite 1.234,56 y 1234.56)."""
    numeros = []
    for crudo in _EXTRAER_NUMEROS.findall(str(texto or "")):
        limpio = crudo.strip()
        if "," in limpio and "." in limpio:
            limpio = limpio.replace(".", "").replace(",", ".")
        elif "," in limpio:
            limpio = limpio.replace(",", ".")
        else:
            grupos = limpio.split(".")
            if len(grupos) > 1 and all(len(g) == 3 for g in grupos[1:]):
                limpio = "".join(grupos)  # separador de miles angloamericano
        try:
            numeros.append(round(float(limpio), 2))
        except ValueError:
            continue
    return numeros


def _valores_errata(caso):
    """Cifras impresas en la fuente que el simulador corrige (§62.1)."""
    valores = []
    for correccion in caso.get("correcciones") or []:
        for numero in _numeros_de_texto(correccion.get("valor_libro")):
            valores.append({"valor_libro": numero, "campo": correccion.get("campo"),
                            "valor_corregido": correccion.get("valor_corregido"),
                            "razon": correccion.get("razon")})
    return valores


def _verificacion_mecanica(caso, lineas, catalogo, indice):
    """Reglas mecánicas verificables de §62.5 (casos sin solución en la fuente)."""
    mensajes = []
    detalle = {}
    lineas = list(lineas or [])
    total_debe = round(sum(float(l.get("debe") or 0.0) for l in lineas), 2)
    total_haber = round(sum(float(l.get("haber") or 0.0) for l in lineas), 2)

    # 1) Asiento cuadrado
    cuadrado = len(lineas) >= 2 and abs(total_debe - total_haber) < TOLERANCIA and total_debe > 0
    detalle["ASIENTO_CUADRADO"] = 40.0 if cuadrado else 0.0
    mensajes.append("✓ Asiento cuadrado: Debe %s = Haber %s." % (formato_es_ec(total_debe),
                                                                 formato_es_ec(total_haber))
                    if cuadrado else
                    "✗ Asiento descuadrado: Debe %s frente a Haber %s." % (formato_es_ec(total_debe),
                                                                          formato_es_ec(total_haber)))

    # 2) Cuentas válidas del catálogo
    invalidas = []
    for linea in lineas:
        cuenta, _ = _resolver_cuenta(linea, catalogo, indice)
        if not cuenta:
            invalidas.append(linea.get("cuenta") or linea.get("codigo") or "(sin cuenta)")
    detalle["CUENTAS_VALIDAS"] = 20.0 if lineas and not invalidas else 0.0
    mensajes.append("✓ Todas las cuentas existen en el catálogo." if lineas and not invalidas
                    else "✗ Cuentas no reconocidas en el catálogo: %s." % ", ".join(
                        str(i) for i in invalidas))

    # 3) Posición Debe/Haber coherente con la naturaleza de la cuenta
    mal_posicionadas = []
    for linea in lineas:
        cuenta, _ = _resolver_cuenta(linea, catalogo, indice)
        debe = round(float(linea.get("debe") or 0.0), 2)
        haber = round(float(linea.get("haber") or 0.0), 2)
        if not cuenta or (debe <= 0 and haber <= 0):
            continue
        naturaleza = (cuenta.get("naturaleza") or "").upper()
        if naturaleza.startswith("DEUDORA") and debe <= 0:
            mal_posicionadas.append(cuenta["nombre"])
        elif naturaleza.startswith("ACREEDORA") and haber <= 0:
            mal_posicionadas.append(cuenta["nombre"])
    detalle["POSICION_DEBE_HABER"] = 30.0 if lineas and not mal_posicionadas else 0.0
    mensajes.append("✓ Posición Debe/Haber coherente con la naturaleza de cada cuenta."
                    if lineas and not mal_posicionadas else
                    "✗ Revise la posición Debe/Haber de: %s." % ", ".join(mal_posicionadas))

    # 4) Balance cuadrado: cada línea con un solo lado y saldo no negativo
    con_ambos = [l for l in lineas if float(l.get("debe") or 0) > 0 and float(l.get("haber") or 0) > 0]
    sin_lado = [l for l in lineas if float(l.get("debe") or 0) <= 0 and float(l.get("haber") or 0) <= 0]
    balance_ok = bool(lineas) and not con_ambos and not sin_lado
    detalle["BALANCE_CUADRADO"] = 10.0 if balance_ok else 0.0
    mensajes.append("✓ Cada línea tiene un solo lado (Debe o Haber)." if balance_ok else
                    "✗ Hay líneas con Debe y Haber a la vez o sin importe.")

    puntuacion = round(sum(detalle.values()), 2)
    return {"puntuacion": min(100.0, puntuacion), "detalle": detalle, "mensajes": mensajes,
            "reglas_aplicadas": list(REGLAS_MECANICAS)}


def _comparar_con_solucion(caso, lineas, catalogo, indice):
    """Compara las líneas del estudiante con los asientos esperados (fuente con solución)."""
    esperadas = _asientos_aplanados(caso)
    mensajes = []
    total_esperadas = len(esperadas) or 1
    score_cuentas = score_posicion = score_importes = 0.0
    usadas = set()
    total_debe = round(sum(float(l.get("debe") or 0.0) for l in lineas), 2)
    total_haber = round(sum(float(l.get("haber") or 0.0) for l in lineas), 2)
    score_cuadre = PUNTAJE["cuadre"] if abs(total_debe - total_haber) < TOLERANCIA and total_debe > 0 else 0.0
    mensajes.append("✓ Partida doble cuadrada: Debe %s = Haber %s." % (formato_es_ec(total_debe),
                                                                      formato_es_ec(total_haber))
                    if score_cuadre else
                    "✗ Asiento descuadrado: Debe %s frente a Haber %s." % (formato_es_ec(total_debe),
                                                                          formato_es_ec(total_haber)))

    for indice_linea, linea in enumerate(lineas):
        cuenta, codigo = _resolver_cuenta(linea, catalogo, indice)
        debe = round(float(linea.get("debe") or 0.0), 2)
        haber = round(float(linea.get("haber") or 0.0), 2)
        nombre_estudiante = (cuenta or {}).get("nombre") or linea.get("cuenta") or "(sin cuenta)"
        crudo = str(linea.get("cuenta") or linea.get("cuenta_codigo") or "")
        variantes = {normalizar(nombre_estudiante), normalizar(crudo)}
        encontrada = None
        for posicion, esperada in enumerate(esperadas):
            if posicion in usadas:
                continue
            if _coincide_cuenta(esperada, variantes, codigo):
                encontrada = (posicion, esperada)
                break
        if not encontrada:
            mensajes.append("✗ La cuenta %s no corresponde al registro de este caso." % nombre_estudiante)
            continue
        usadas.add(encontrada[0])
        esperada = encontrada[1]
        score_cuentas += PUNTAJE["cuentas"] / total_esperadas
        posicion_ok = (esperada["debe"] > 0 and debe > 0) or (esperada["haber"] > 0 and haber > 0)
        if posicion_ok:
            score_posicion += PUNTAJE["posicion"] / total_esperadas
            if abs(esperada["debe"] - debe) < TOLERANCIA and abs(esperada["haber"] - haber) < TOLERANCIA:
                score_importes += PUNTAJE["importes"] / total_esperadas
                mensajes.append("✓ %s registrada correctamente en %s por %s."
                                % (nombre_estudiante, "Debe" if debe > 0 else "Haber",
                                   formato_es_ec(max(debe, haber))))
            else:
                mensajes.append("⚠ %s está en la posición correcta pero su importe %s no coincide con el "
                                "esperado %s." % (nombre_estudiante,
                                                  formato_es_ec(max(debe, haber)),
                                                  formato_es_ec(max(esperada["debe"], esperada["haber"]))))
        else:
            mensajes.append("✗ %s fue registrada en %s en lugar de %s."
                            % (nombre_estudiante, "el Haber" if haber > 0 else "el Debe",
                               "el Debe" if esperada["debe"] > 0 else "el Haber"))

    for posicion, esperada in enumerate(esperadas):
        if posicion not in usadas:
            mensajes.append("✗ Faltó registrar %s por %s."
                            % (esperada["cuenta"],
                               formato_es_ec(max(esperada["debe"], esperada["haber"]))))

    detalle = {"cuentas": round(score_cuentas, 2), "posicion": round(score_posicion, 2),
               "importes": round(score_importes, 2), "cuadre": round(score_cuadre, 2)}
    return {"puntuacion": min(100.0, round(sum(detalle.values()), 2)), "detalle": detalle,
            "mensajes": mensajes, "reglas_aplicadas": []}


def _comparar_totales(caso, totales, lineas, catalogo, indice):
    """Verificación de casos cuyo respaldo son totales comprobados (sin partidas publicadas)."""
    esperados = caso.get("totales_verificados") or {}
    numericos = {k: v for k, v in esperados.items() if isinstance(v, (int, float))}
    mensajes = []
    aciertos = 0
    total = len(numericos) or 1
    for clave, valor in numericos.items():
        enviado = None
        for nombre in (clave, clave.replace("_", " "), clave.lower()):
            if isinstance(totales, dict) and nombre in totales:
                enviado = totales[nombre]
                break
        if enviado is None:
            mensajes.append("• No se verificó %s (esperado %s)." % (clave, formato_es_ec(valor)))
            continue
        if abs(float(enviado) - float(valor)) < TOLERANCIA:
            aciertos += 1
            mensajes.append("✓ %s correcto: %s." % (clave, formato_es_ec(valor)))
        else:
            mensajes.append("✗ %s incorrecto: enviado %s, esperado %s."
                            % (clave, formato_es_ec(enviado), formato_es_ec(valor)))
    puntuacion = round(100.0 * aciertos / total, 2)
    if lineas:
        mecanica = _verificacion_mecanica(caso, lineas, catalogo, indice)
        mensajes.extend(mecanica["mensajes"])
        puntuacion = round((puntuacion + mecanica["puntuacion"]) / 2, 2)
        detalle = {"totales": puntuacion, "mecanica": mecanica["detalle"]}
    else:
        detalle = {"totales": puntuacion}
    return {"puntuacion": puntuacion, "detalle": detalle, "mensajes": mensajes,
            "reglas_aplicadas": list(REGLAS_MECANICAS) if lineas else []}


def _comparar_ecuacion(caso, ecuacion):
    """Ecuación contable ampliada: Activo = Pasivo + Capital + Ingresos − Gastos."""
    referencial = caso.get("solucion_referencial") or {}
    verificados = {k: v for k, v in (caso.get("totales_verificados") or {}).items()
                   if isinstance(v, (int, float))}
    mensajes = []
    if not referencial:
        activo = float((ecuacion or {}).get("activo") or 0)
        pasivo = float((ecuacion or {}).get("pasivo") or 0)
        capital = float((ecuacion or {}).get("capital") or 0)
        ingresos = float((ecuacion or {}).get("ingresos") or 0)
        gastos = float((ecuacion or {}).get("gastos") or 0)
        cuadra = abs(activo - (pasivo + capital + ingresos - gastos)) < TOLERANCIA
        mensajes.append("✓ La ecuación contable ampliada cuadra." if cuadra else
                        "✗ La ecuación contable ampliada no cuadra: Activo %s frente a Pasivo + Capital "
                        "+ Ingresos − Gastos %s." % (formato_es_ec(activo),
                                                     formato_es_ec(pasivo + capital + ingresos - gastos)))
        return {"puntuacion": 100.0 if cuadra else 40.0, "detalle": {"ecuacion": cuadra},
                "mensajes": mensajes, "reglas_aplicadas": ["ECUACION_CONTABLE"]}
    aciertos = 0
    total = len(referencial)
    for clave, valor in referencial.items():
        enviado = (ecuacion or {}).get(clave)
        if enviado is None:
            mensajes.append("• No se verificó %s (referencial %s)." % (clave, formato_es_ec(valor)))
            continue
        if abs(float(enviado) - float(valor)) < TOLERANCIA:
            aciertos += 1
            mensajes.append("✓ %s correcto: %s." % (clave, formato_es_ec(valor)))
        else:
            mensajes.append("✗ %s incorrecto: enviado %s, referencial %s."
                            % (clave, formato_es_ec(enviado), formato_es_ec(valor)))
    puntuacion = round(100.0 * aciertos / (total or 1), 2)
    detalle = {"elementos_correctos": aciertos, "elementos_totales": total, "ecuacion": True}
    detalle.update({k: v for k, v in verificados.items() if isinstance(v, (int, float))})
    return {"puntuacion": puntuacion, "detalle": detalle, "mensajes": mensajes,
            "reglas_aplicadas": ["ECUACION_CONTABLE"]}


def _mensajes_errata(caso, lineas):
    """§62.1 — advierte cuando el estudiante replica la cifra errada del libro."""
    mensajes = []
    for errata in _valores_errata(caso):
        for linea in lineas or []:
            for lado in ("debe", "haber"):
                valor = round(float(linea.get(lado) or 0.0), 2)
                if valor and abs(valor - errata["valor_libro"]) < TOLERANCIA:
                    mensajes.append(
                        "⚠ El importe %s coincide con el valor impreso en el libro (%s), que está "
                        "corregido en el simulador: %s. Motivo registrado: %s"
                        % (formato_es_ec(valor), errata["campo"], errata["valor_corregido"],
                           errata["razon"]))
    return mensajes


def verificar_respuesta(caso, lineas=None, totales=None, ecuacion=None, db_path=None):
    """Verifica una respuesta sin guardarla (útil para la interfaz y las pruebas)."""
    catalogo = _catalogo_cuentas(db_path=db_path)
    indice = _indice_nombres(catalogo)
    lineas = list(lineas or [])
    tipo = caso.get("tipo_verificacion")
    if tipo == "ECUACION":
        resultado = _comparar_ecuacion(caso, ecuacion)
    elif tipo == "TOTALES":
        resultado = _comparar_totales(caso, totales, lineas, catalogo, indice)
    elif tipo == "MECANICA" or not caso.get("solucion_en_fuente"):
        resultado = _verificacion_mecanica(caso, lineas, catalogo, indice)
    else:
        resultado = _comparar_con_solucion(caso, lineas, catalogo, indice)
    resultado["mensajes"] = list(resultado["mensajes"]) + _mensajes_errata(caso, lineas)
    puntuacion = round(float(resultado["puntuacion"]), 2)
    if puntuacion >= UMBRAL_CORRECTO:
        resultado["resultado"] = "CORRECTO"
    elif puntuacion >= UMBRAL_PARCIAL:
        resultado["resultado"] = "PARCIALMENTE_CORRECTO"
    else:
        resultado["resultado"] = "INCORRECTO"
    resultado["puntuacion"] = puntuacion
    mecanica = tipo == "MECANICA" or not caso.get("solucion_en_fuente")
    resultado["verificacion_mecanica"] = mecanica
    resultado["oficial"] = bool(caso.get("respuesta_oficial_permitida")) and not mecanica
    resultado["requiere_revision_docente"] = mecanica or not caso.get("respuesta_oficial_permitida")
    resultado["etiquetas"] = caso.get("etiquetas") or []
    resultado["retroalimentacion"] = "\n".join(resultado["mensajes"])
    return resultado


# --------------------------------------------------------------------------- Intentos
def listar_intentos(codigo=None, estudiante_id=None, db_path=None, limite=200):
    """Intentos registrados (por caso y/o por estudiante), del más reciente al más antiguo."""
    sql = """SELECT i.*, c.nombre AS caso_nombre, c.puntaje AS caso_puntaje
             FROM casos_libros_intentos i
             JOIN casos_libros c ON c.codigo = i.caso_codigo
             WHERE 1 = 1"""
    parametros = []
    if codigo:
        sql += " AND i.caso_codigo = ?"
        parametros.append(str(codigo).strip().upper())
    if estudiante_id:
        sql += " AND i.estudiante_id = ?"
        parametros.append(int(estudiante_id))
    sql += " ORDER BY i.id DESC LIMIT ?"
    parametros.append(int(limite))
    conn = _conectar(db_path)
    try:
        filas = conn.execute(sql, parametros).fetchall()
        intentos = dicts_from_rows(filas)
        for intento in intentos:
            intento["respuesta"] = _json_cargar(intento.pop("respuesta_json", None), [])
            intento["verificacion"] = _json_cargar(intento.pop("verificacion_json", None), {})
            intento["oficial"] = bool(intento.get("oficial"))
            intento["requiere_revision_docente"] = bool(intento.get("requiere_revision_docente"))
        return intentos
    finally:
        conn.close()


def resumen_intentos(codigo, db_path=None):
    """Resumen de intentos de un caso (para el panel docente)."""
    intentos = listar_intentos(codigo=codigo, db_path=db_path)
    return {
        "caso_codigo": codigo,
        "total": len(intentos),
        "evaluados": sum(1 for i in intentos if i.get("estado") == "EVALUADO"),
        "correctos": sum(1 for i in intentos if i.get("resultado") == "CORRECTO"),
        "promedio": round(sum(float(i.get("puntuacion") or 0) for i in intentos
                              if i.get("estado") == "EVALUADO")
                          / max(1, sum(1 for i in intentos if i.get("estado") == "EVALUADO")), 2),
        "intentos": intentos,
    }


def _siguiente_numero(conn, codigo, estudiante_id):
    fila = conn.execute("""SELECT COALESCE(MAX(numero_intento), 0) AS n FROM casos_libros_intentos
                           WHERE caso_codigo = ? AND estudiante_id = ?""",
                        (codigo, estudiante_id)).fetchone()
    return int(fila["n"]) + 1


def iniciar_intento(codigo, estudiante_id, db_path=None):
    """Abre un intento nuevo verificando intentos máximos y la activación del caso (§61/§62.9)."""
    caso = obtener_caso(codigo, para_estudiante=True, db_path=db_path)
    if not caso.get("activo") or not caso.get("publicable"):
        raise CasoNoDisponible("El caso %s no está activado para los estudiantes." % caso["codigo"])
    conn = _conectar(db_path)
    try:
        numero = _siguiente_numero(conn, caso["codigo"], int(estudiante_id))
        maximos = int(caso.get("intentos_maximos") or 1)
        if numero > maximos:
            raise SinIntentos("Se agotaron los intentos permitidos (%d de %d) para el caso %s."
                              % (maximos, maximos, caso["codigo"]))
        cursor = conn.execute("""
            INSERT INTO casos_libros_intentos (caso_codigo, estudiante_id, numero_intento, estado)
            VALUES (?, ?, ?, 'EN_PROCESO')
        """, (caso["codigo"], int(estudiante_id), numero))
        conn.commit()
        intento_id = cursor.lastrowid
    finally:
        conn.close()
    return {"intento_id": intento_id, "numero_intento": numero, "caso_codigo": caso["codigo"],
            "intentos_maximos": int(caso.get("intentos_maximos") or 1),
            "practica_sin_solucion": caso["practica_sin_solucion"],
            "mensaje": "Intento %d de %d iniciado." % (numero, int(caso.get("intentos_maximos") or 1))}


def enviar_intento(codigo, estudiante_id, lineas=None, totales=None, ecuacion=None,
                   intento_id=None, tiempo_segundos=0, db_path=None):
    """Registra y verifica la respuesta de un intento.

    Devuelve la verificación completa: puntuación, resultado, retroalimentación, si es oficial
    (§62.4/§62.5) y el registro del intento.
    """
    caso = obtener_caso(codigo, para_estudiante=True, db_path=db_path)
    estudiante_id = int(estudiante_id)
    if not caso.get("activo") or not caso.get("publicable"):
        raise CasoNoDisponible("El caso %s no está activado para los estudiantes." % caso["codigo"])

    conn = _conectar(db_path)
    try:
        if intento_id:
            fila = conn.execute("""SELECT * FROM casos_libros_intentos
                                   WHERE id = ? AND estudiante_id = ?""",
                                (int(intento_id), estudiante_id)).fetchone()
            if not fila:
                raise CasoNoEncontrado("El intento %s no existe para este estudiante." % intento_id)
            if fila["estado"] == "EVALUADO":
                raise ErrorCasoLibro("El intento %s ya fue evaluado." % intento_id,
                                     estado_http=409, codigo="INTENTO_EVALUADO")
            numero = int(fila["numero_intento"])
        else:
            numero = _siguiente_numero(conn, caso["codigo"], estudiante_id)
            maximos = int(caso.get("intentos_maximos") or 1)
            if numero > maximos:
                raise SinIntentos("Se agotaron los intentos permitidos (%d de %d) para el caso %s."
                                  % (maximos, maximos, caso["codigo"]))
            cursor = conn.execute("""
                INSERT INTO casos_libros_intentos (caso_codigo, estudiante_id, numero_intento, estado)
                VALUES (?, ?, ?, 'EN_PROCESO')
            """, (caso["codigo"], estudiante_id, numero))
            intento_id = cursor.lastrowid
            conn.commit()
    finally:
        conn.close()

    # La verificación usa el caso COMPLETO (con su solución y datos reconstruidos) aunque el
    # estudiante nunca los vea: lo que se marca es si el resultado puede ser OFICIAL (§62.4/§62.5).
    caso_interno = obtener_caso(caso["codigo"], para_estudiante=False, db_path=db_path)
    verificacion = verificar_respuesta(caso_interno, lineas=lineas, totales=totales,
                                       ecuacion=ecuacion, db_path=db_path)
    respuesta = {"lineas": lineas or [], "totales": totales or {}, "ecuacion": ecuacion or {}}
    conn = _conectar(db_path)
    try:
        conn.execute("""
            UPDATE casos_libros_intentos
               SET estado = 'EVALUADO', respuesta_json = ?, puntuacion = ?, resultado = ?,
                   oficial = ?, requiere_revision_docente = ?, verificacion_json = ?,
                   retroalimentacion = ?, finalizado_en = ?
             WHERE id = ?
        """, (json.dumps(respuesta, ensure_ascii=False), verificacion["puntuacion"],
              verificacion["resultado"], 1 if verificacion["oficial"] else 0,
              1 if verificacion["requiere_revision_docente"] else 0,
              json.dumps(verificacion, ensure_ascii=False, default=str),
              verificacion["retroalimentacion"], datetime.now().strftime(FORMATO_FECHA),
              int(intento_id)))
        conn.commit()
    finally:
        conn.close()

    return {
        "caso_codigo": caso["codigo"],
        "caso_nombre": caso["nombre"],
        "intento_id": int(intento_id),
        "numero_intento": numero,
        "puntuacion": verificacion["puntuacion"],
        "resultado": verificacion["resultado"],
        "oficial": verificacion["oficial"],
        "requiere_revision_docente": verificacion["requiere_revision_docente"],
        "verificacion_mecanica": verificacion["verificacion_mecanica"],
        "detalle": verificacion["detalle"],
        "mensajes": verificacion["mensajes"],
        "retroalimentacion": verificacion["retroalimentacion"],
        "etiquetas": verificacion["etiquetas"],
        "ficha": ficha_del_caso(caso),
        "advertencia_normativa": ADVERTENCIA_IVA_RETENCIONES,
        "cita_fuente": caso["cita_fuente"],
    }
