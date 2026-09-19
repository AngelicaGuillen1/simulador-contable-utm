# -*- coding: utf-8 -*-
"""Carga las 6 actividades del syllabus de Contabilidad I en el simulador.

Toma las fechas, el puntaje, el componente, los contenidos y los criterios directamente de
`cronograma.json` (la fuente de verdad del sílabo) y deja las actividades en estado ABIERTA
con su evidencia requerida.

Es IDEMPOTENTE: se puede ejecutar las veces que haga falta.
    * `services.activity_service.crear_actividad` hace upsert por `codigo`, así que las
      actividades no se duplican ni se pierden sus asignaciones.
    * Las asignaciones usan INSERT OR IGNORE (UNIQUE actividad_id + estudiante_id).

Uso:
    .venv/Scripts/python.exe database/seed_actividades.py                 # asigna al estudiante de prueba
    .venv/Scripts/python.exe database/seed_actividades.py --todos         # asigna a TODOS los estudiantes
    .venv/Scripts/python.exe database/seed_actividades.py --sin-asignar   # solo crea/actualiza actividades
    .venv/Scripts/python.exe database/seed_actividades.py --db ruta.db
"""

import argparse
import difflib
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config                                    # noqa: E402
from database.esquema_educativo import aplicar               # noqa: E402
from models import get_db_connection                         # noqa: E402
from services.activity_service import (                      # noqa: E402
    asignar_a_estudiantes, asignar_a_todos_los_estudiantes, crear_actividad, estudiantes_activos,
)

# Ruta del cronograma oficial del sílabo (se puede sobreescribir con la variable de entorno).
CRONOGRAMA_PATH = os.environ.get("CRONOGRAMA_PATH") or (
    "C:/Users/1161150/Desktop/2026/S2/Clases/Contabilidad 1/datos/cronograma.json"
)

# --------------------------------------------------------------------------- Las 6 actividades
# `titulo_cronograma` es el nombre EXACTO del cronograma.json; se usa para localizar las fechas.
ACTIVIDADES = [
    {
        "codigo": "U1-A1",
        "titulo": "Taller asistido: objeto, objetivos y usuarios de la información contable",
        "titulo_cronograma": "Taller asistido: objeto, objetivos y usuarios de la información contable",
        "unidad": 1,
        "componente": "DOCENCIA",
        "puntaje": 10,
        "tipo_evidencia": "INTEGRAL",
        "modulos_habilitados": ["CUENTAS", "ESTADOS"],
    },
    {
        "codigo": "U2-A2",
        "titulo": "Práctica de laboratorio: clasificación, naturaleza y dinámica de las cuentas contables",
        "titulo_cronograma": "Práctica de laboratorio: clasificación, naturaleza y dinámica de las cuentas contables",
        "unidad": 2,
        "componente": "PRACTICA",
        "puntaje": 12,
        "tipo_evidencia": "PLAN_CUENTAS",
        "modulos_habilitados": ["CUENTAS", "DIARIO", "MAYOR"],
    },
    {
        "codigo": "U2-A3",
        "titulo": "Fichero autónomo de cuentas: codificación, naturaleza y dinámica",
        "titulo_cronograma": "Fichero autónomo de cuentas: codificación, naturaleza y dinámica",
        "unidad": 2,
        "componente": "AUTONOMO",
        "puntaje": 10,
        "tipo_evidencia": "PLAN_CUENTAS",
        "modulos_habilitados": ["CUENTAS", "MAYOR"],
    },
    {
        "codigo": "U3-A4",
        "titulo": "Jornalización integral de transacciones comerciales con IVA y documentos soporte",
        "titulo_cronograma": "Jornalización integral de transacciones comerciales con IVA y documentos soporte",
        "unidad": 3,
        "componente": "DOCENCIA",
        "puntaje": 10,
        "tipo_evidencia": "DIARIO",
        "modulos_habilitados": ["DIARIO", "CUENTAS"],
    },
    {
        "codigo": "U3-A5",
        "titulo": "Portafolio autónomo de jornalización y mayorización",
        "titulo_cronograma": "Portafolio autónomo de jornalización y mayorización",
        "unidad": 3,
        "componente": "AUTONOMO",
        "puntaje": 10,
        "tipo_evidencia": "INTEGRAL",
        "modulos_habilitados": ["DIARIO", "MAYOR", "CUENTAS"],
    },
    {
        "codigo": "U4-A6",
        "titulo": ("Trabajo autónomo integrador: balance de comprobación de sumas y saldos y "
                   "corrección de errores contables"),
        "titulo_cronograma": ("Trabajo autónomo integrador: balance de comprobación de sumas y saldos "
                              "y corrección de errores contables"),
        "unidad": 4,
        "componente": "AUTONOMO",
        "puntaje": 10,
        "tipo_evidencia": "BALANCE",
        "modulos_habilitados": ["BALANCE", "MAYOR", "ESTADOS"],
    },
]

COMPONENTE_POR_CODIGO = {"ACD": "DOCENCIA", "APE": "PRACTICA", "AA": "AUTONOMO"}


# --------------------------------------------------------------------------- Utilidades
def _normalizar(texto):
    """minúsculas, sin acentos ni puntuación, para comparar títulos con tolerancia."""
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = "".join(c for c in base if not unicodedata.combining(c)).lower()
    return " ".join("".join(c if c.isalnum() else " " for c in base).split())


def cargar_cronograma(ruta=None):
    ruta = ruta or CRONOGRAMA_PATH
    if not os.path.exists(ruta):
        print("[AVISO] No se encontró el cronograma en %s" % ruta)
        return None
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def _unidad_del_cronograma(cronograma, numero):
    for unidad in (cronograma or {}).get("unidades", []):
        if int(unidad.get("numero") or 0) == int(numero):
            return unidad
    return None


def buscar_en_cronograma(cronograma, actividad):
    """Localiza la actividad del cronograma por título (con coincidencia aproximada)."""
    lista = (cronograma or {}).get("actividades") or []
    objetivo = _normalizar(actividad["titulo_cronograma"])
    por_titulo = {_normalizar(item.get("nombre")): item for item in lista}
    if objetivo in por_titulo:
        return por_titulo[objetivo]

    for normalizado, item in por_titulo.items():
        if objetivo and (objetivo in normalizado or normalizado in objetivo):
            return item

    candidatos = difflib.get_close_matches(objetivo, list(por_titulo), n=1, cutoff=0.6)
    if candidatos:
        return por_titulo[candidatos[0]]

    # Último recurso: misma unidad y mismo componente declarado en el cronograma.
    for item in lista:
        componente = COMPONENTE_POR_CODIGO.get(str(item.get("componente") or "").upper())
        if (int(item.get("unidad") or 0) == int(actividad["unidad"])
                and componente == actividad["componente"]):
            return item
    return None


def _texto_lista(titulo, valores):
    valores = [v for v in (valores or []) if str(v).strip()]
    if not valores:
        return ""
    return "%s\n%s\n" % (titulo, "\n".join("  - %s" % v for v in valores))


def construir_instrucciones(actividad, item, unidad):
    """Arma las instrucciones del estudiante con los datos del sílabo."""
    if not item:
        return None
    partes = []
    partes.append("Componente %s · Puntaje: %s puntos" % (actividad["componente"], actividad["puntaje"]))
    if item.get("disponibilidad"):
        partes.append("Disponibilidad: %s" % item["disponibilidad"])
    if item.get("fecha_limite"):
        partes.append("Fecha límite de entrega: %s" % item["fecha_limite"])
    if item.get("tipo"):
        partes.append("Tipo de actividad: %s" % item["tipo"])
    partes.append("")
    if item.get("estrategia"):
        partes.append("PROPÓSITO DE LA ACTIVIDAD:\n%s" % item["estrategia"])
        partes.append("")
    partes.append(_texto_lista("CONTENIDOS DE LA UNIDAD:", item.get("contenidos")
                               or (unidad or {}).get("contenidos")))
    partes.append(_texto_lista("CRITERIOS DE EVALUACIÓN:", item.get("criterios")))
    if item.get("uso_simulador"):
        partes.append("USO DEL SIMULADOR:\n%s" % item["uso_simulador"])
    # Bloque fijo: cómo entra el estudiante y dónde queda su trabajo. Deja cada tarea
    # autocontenida (usuario = correo institucional, aula propia, entrega de evidencia).
    partes.append("")
    partes.append(
        "CÓMO INGRESAS Y DÓNDE TRABAJAS:\n"
        "Ingrese al simulador con su CORREO INSTITUCIONAL como usuario (la clave inicial se le "
        "entregó; cámbiela al primer ingreso). Su trabajo queda en SU PROPIA AULA: su plan de "
        "cuentas, sus libros y sus evidencias; nadie más los ve. Trabaje en los módulos indicados "
        "en «Uso del simulador». Al terminar, entregue la evidencia en Mis Evidencias y conserve "
        "el código de verificación que le entrega el sistema."
    )
    parametros = item.get("parametros") or {}
    if parametros.get("bibliografia"):
        partes.append("")
        partes.append("Bibliografía: %s" % parametros["bibliografia"])
    return "\n".join(p for p in partes if p is not None).strip()


def _estudiante_de_prueba(db_path):
    """Estudiante de prueba ya existente en la base (rol Estudiante)."""
    conn = get_db_connection(db_path)
    try:
        fila = conn.execute("""
            SELECT u.id, u.username, u.nombre_completo
            FROM usuarios u JOIN roles r ON u.rol_id = r.id
            WHERE r.nombre = 'Estudiante' AND u.activo = 1
            ORDER BY (u.username = 'estudiante') DESC, u.id ASC
            LIMIT 1
        """).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


# --------------------------------------------------------------------------- Proceso
def sembrar(db_path=None, todos=False, asignar=True, cronograma_path=None, verbose=True):
    db_path = db_path or Config.DATABASE_PATH
    aplicar(db_path, verboso=False)

    cronograma = cargar_cronograma(cronograma_path)
    if not cronograma:
        print("[AVISO] Se cargarán las actividades SIN fechas (quedarán NULL).")

    creadas, sin_fecha, sin_cronograma = [], [], []

    for actividad in ACTIVIDADES:
        item = buscar_en_cronograma(cronograma, actividad) if cronograma else None
        unidad = _unidad_del_cronograma(cronograma, actividad["unidad"]) if cronograma else None

        apertura = (item or {}).get("desde")
        cierre = (item or {}).get("hasta")
        if item and not apertura:
            sin_fecha.append("%s (apertura)" % actividad["codigo"])
        if item and not cierre:
            sin_fecha.append("%s (cierre)" % actividad["codigo"])
        if not item:
            sin_cronograma.append(actividad["codigo"])

        datos = {
            "codigo": actividad["codigo"],
            "titulo": actividad["titulo"],
            "unidad": actividad["unidad"],
            "componente": actividad["componente"],
            "resultado_aprendizaje": (unidad or {}).get("ra"),
            "instrucciones": construir_instrucciones(actividad, item, unidad),
            "evidencia_requerida": (item or {}).get("forma_de_evidenciar"),
            "puntaje": actividad["puntaje"],
            "fecha_apertura": apertura,
            "fecha_cierre": cierre,
            "intentos_maximos": 1,
            "modo_practica": 0,
            "tutor_ia": 0,
            "modulos_habilitados": actividad["modulos_habilitados"],
            "tipo_evidencia": actividad["tipo_evidencia"],
            "estado": "ABIERTA",
            "creada_por": 2,   # docente del sistema
        }
        creadas.append(crear_actividad(datos, db_path=db_path))

    resumen_asignacion = None
    if asignar:
        if todos:
            destino = estudiantes_activos(db_path=db_path)
            if verbose:
                print("Asignando a TODOS los estudiantes activos (%d)..." % len(destino))
            resumen_asignacion = {}
            for actividad in creadas:
                resultado = asignar_a_todos_los_estudiantes(actividad["id"], db_path=db_path)
                resumen_asignacion[actividad["codigo"]] = resultado
        else:
            estudiante = _estudiante_de_prueba(db_path)
            if not estudiante:
                print("[AVISO] No hay ningún estudiante en la base: no se asignó nada.")
                resumen_asignacion = {}
            else:
                if verbose:
                    print("Asignando las 6 actividades al estudiante de prueba: %s (%s)"
                          % (estudiante["nombre_completo"], estudiante["username"]))
                resumen_asignacion = {}
                for actividad in creadas:
                    resultado = asignar_a_estudiantes(actividad["id"], [estudiante["id"]],
                                                      db_path=db_path)
                    resumen_asignacion[actividad["codigo"]] = resultado

    if verbose:
        print("=" * 78)
        print(" ACTIVIDADES DEL SYLLABUS CARGADAS")
        print("=" * 78)
        for actividad, fila in zip(ACTIVIDADES, creadas):
            print(" %-6s U%d %-9s %5s pts  %s → %s  [%s]"
                  % (fila["codigo"], fila["unidad"], fila["componente"], fila["puntaje"],
                     fila["fecha_apertura"] or "SIN FECHA", fila["fecha_cierre"] or "SIN FECHA",
                     fila["estado"]))
            print("        %s" % fila["titulo"])
        print("-" * 78)
        print(" Total de actividades del syllabus: %d" % len(creadas))
        if resumen_asignacion:
            nuevas = sum(r["asignadas"] for r in resumen_asignacion.values())
            existentes = sum(r["ya_existentes"] for r in resumen_asignacion.values())
            print(" Asignaciones nuevas: %d · Asignaciones que ya existían: %d" % (nuevas, existentes))
        if sin_cronograma:
            print(" [AVISO] Sin correspondencia en cronograma.json: %s" % ", ".join(sin_cronograma))
        if sin_fecha:
            print(" [AVISO] Sin fecha en cronograma.json (quedaron NULL): %s" % ", ".join(sin_fecha))
        print("=" * 78)

    return {"actividades": creadas, "asignaciones": resumen_asignacion,
            "sin_cronograma": sin_cronograma, "sin_fecha": sin_fecha}


def main():
    analizador = argparse.ArgumentParser(
        description="Carga las actividades del syllabus de Contabilidad I (idempotente).")
    analizador.add_argument("--db", dest="db", default=None,
                            help="Ruta de la base SQLite (por defecto la configurada en config.py).")
    analizador.add_argument("--todos", action="store_true",
                            help="Asigna las actividades a TODOS los estudiantes activos.")
    analizador.add_argument("--sin-asignar", action="store_true",
                            help="Crea/actualiza las actividades sin asignarlas.")
    analizador.add_argument("--cronograma", dest="cronograma", default=None,
                            help="Ruta alternativa de cronograma.json.")
    argumentos = analizador.parse_args()

    sembrar(db_path=argumentos.db, todos=argumentos.todos,
            asignar=not argumentos.sin_asignar, cronograma_path=argumentos.cronograma)


if __name__ == "__main__":
    main()
