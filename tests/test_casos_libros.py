# -*- coding: utf-8 -*-
"""Pruebas automáticas del BANCO DE CASOS PRÁCTICOS DE LOS LIBROS (§61) y de las reglas de
trazabilidad de las fuentes (§62) del Prompt Maestro v2.

Cubren:
    1. Los 19 casos como DATOS (ficha completa, aritmética, erratas, doble numeración).
    2. La carga en la base de control y las 9 reglas de §62 (8 de trazabilidad de fuentes).
    3. La verificación de intentos (puntaje, retroalimentación, oficialidad, intentos máximos).
    4. La interfaz (rutas de estudiante y de docente, HTML y JSON).
"""
import json
import os
import re
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from database.banco_casos_libros import (                              # noqa: E402
    ADVERTENCIA_IVA_RETENCIONES, CAMPOS_FICHA_OBLIGATORIOS, ERRATAS_PLAN_CUENTAS, ETIQUETA_CALCULADA,
    ETIQUETA_RECONSTRUIDO, ETIQUETA_TASAS, FUENTES, MODOS_CATALOGO, PLAN_CUENTAS_BASE,
    REGLAS_TRAZABILIDAD, TASAS_DEMOSTRATIVAS, cita_fuente, formato_es_ec, paginas_pdf,
)
from database.casos_libros_61 import CASOS, caso as caso_de_datos   # noqa: E402
from services import casos_libros_service as S                      # noqa: E402


# --------------------------------------------------------------------------- Utilidades
def lineas_del_caso(caso):
    """Todas las líneas de los asientos esperados, listas para enviarlas como respuesta."""
    lineas = []
    for asiento in caso.get("asientos_esperados") or []:
        for linea in asiento.get("lineas") or []:
            lineas.append({"cuenta": linea.get("codigo") or linea.get("cuenta"),
                           "debe": linea.get("debe") or 0.0, "haber": linea.get("haber") or 0.0})
    return lineas


def totales_del_caso(caso):
    return {clave: valor for clave, valor in (caso.get("totales_verificados") or {}).items()
            if isinstance(valor, (int, float))}


def cliente_docente():
    """Cliente Flask nuevo autenticado como Docente (independiente del de estudiante)."""
    from app import create_app
    cliente = create_app().test_client()
    cliente.post("/login", data={"username": "docente", "password": "docente123"},
                 follow_redirects=True)
    return cliente


# ============================================================================ §61 — DATOS
def test_existen_los_diecinueve_casos_de_la_seccion_61():
    assert len(CASOS) == 19
    assert [c["codigo"] for c in CASOS] == ["C61.%02d" % n for n in range(1, 20)]
    for caso in CASOS:
        assert caso["nombre"] and caso["enunciado"] and caso["datos"], caso["codigo"]
        assert caso["fuente"] in FUENTES, caso["codigo"]
        assert caso["unidad"] in (1, 2, 3, 4)
        assert caso["tipo_verificacion"] in ("ASIENTO", "TOTALES", "ECUACION", "MECANICA")


def test_estados_de_validacion_coinciden_con_la_seccion_61():
    por_estado = {}
    for caso in CASOS:
        por_estado[caso["estado_validacion"]] = por_estado.get(caso["estado_validacion"], 0) + 1
    assert por_estado == {"VERIFICADO": 9, "VERIFICADO_CON_RESERVA": 1, "SIN_SOLUCION": 6,
                          "CON_ERRATA": 2, "PARCIAL_CON_ERRATA": 1}
    # §61.11 a §61.19 son los casos sin solución publicada (seis de ellos marcados SIN_SOLUCION).
    sin_solucion = [c["codigo"] for c in CASOS if not c["solucion_en_fuente"]]
    assert sin_solucion == ["C61.11", "C61.12", "C61.13", "C61.14", "C61.15", "C61.19"]


def test_todo_caso_tiene_ficha_completa_segun_62_9():
    for caso in CASOS:
        ficha = dict(caso, fuente_codigo=caso["fuente"],
                     fuente_nombre=FUENTES[caso["fuente"]]["nombre"])
        for campo in CAMPOS_FICHA_OBLIGATORIOS:
            assert ficha.get(campo) not in (None, ""), "%s sin %s" % (caso["codigo"], campo)
        # Fuente completa, página, año, solución y corrección de erratas por escrito.
        assert caso["anio"]
        assert caso["paginas_impresas"]
        assert isinstance(caso["solucion_en_fuente"], bool)
        assert isinstance(caso.get("correcciones"), list)


def test_cita_con_doble_numeracion_de_paginas_62_7():
    assert paginas_pdf("U2", "134–172") == "153–191"      # impresa = PDF − 19
    assert paginas_pdf("U3", "75–82") == "107–114"        # impresa = PDF − 32
    assert paginas_pdf("SENA", "57–63") == "59–65"        # impresa = PDF − 2
    for caso in CASOS:
        cita = cita_fuente(caso["fuente"], caso["paginas_impresas"])
        assert "imp." in cita
        assert ("PDF" in cita) or ("pliego" in cita), cita


def test_los_asientos_esperados_cuadran_partida_doble():
    for caso in CASOS:
        for asiento in caso.get("asientos_esperados") or []:
            debe = round(sum(float(l.get("debe") or 0) for l in asiento["lineas"]), 2)
            haber = round(sum(float(l.get("haber") or 0) for l in asiento["lineas"]), 2)
            assert debe == haber, "%s · %s" % (caso["codigo"], asiento.get("glosa"))
            assert debe > 0


def test_los_saldos_finales_y_totales_cuadran():
    for caso in CASOS:
        saldos = caso.get("saldos_finales") or {}
        if saldos.get("debitos") or saldos.get("creditos"):
            debe = round(sum(saldos.get("debitos", {}).values()), 2)
            haber = round(sum(saldos.get("creditos", {}).values()), 2)
            assert debe == haber, "%s: %s != %s" % (caso["codigo"], debe, haber)
        totales = caso.get("totales_verificados") or {}
        if totales.get("sumas_debe") is not None:
            assert round(totales["sumas_debe"], 2) == round(totales["sumas_haber"], 2)
        if totales.get("saldos_debe") is not None:
            assert round(totales["saldos_debe"], 2) == round(totales["saldos_haber"], 2)


def test_codigos_de_cuenta_citados_existen_en_el_catalogo_semilla_59():
    for caso in CASOS:
        for asiento in caso.get("asientos_esperados") or []:
            for linea in asiento["lineas"]:
                codigo = str(linea.get("codigo") or "")
                if codigo:
                    assert codigo in PLAN_CUENTAS_BASE, "%s: código %s" % (caso["codigo"], codigo)


def test_erratas_corregidas_y_registradas_62_1():
    # §61.16 — Guápulo: el asiento del 25-jun se carga con el efectivo real (4.600,00).
    guapulo = caso_de_datos("C61.16")
    assert guapulo["estado_validacion"] == "CON_ERRATA"
    caja = [l for a in guapulo["asientos_esperados"] for l in a["lineas"]
            if l["cuenta"] == "Caja" and l["debe"] == 4600.00]
    assert caja, "el asiento corregido del 25-jun debe registrar Caja 4.600,00"
    assert not [l for a in guapulo["asientos_esperados"] for l in a["lineas"]
                if l["cuenta"] == "Caja" and l["debe"] == 4000.00]
    correccion = guapulo["correcciones"][0]
    assert "4.000,00" in correccion["valor_libro"] and "4.600,00" in correccion["valor_corregido"]
    assert correccion["razon"]

    # §61.17 — Servindustria: reconocimiento mensual 7.200,00 ÷ 12 = 600,00 y no 500,00.
    servindustria = caso_de_datos("C61.17")
    assert servindustria["parametros_caso"]["meses"] == 12
    mensuales = [l for a in servindustria["asientos_esperados"] for l in a["lineas"]
                 if l["cuenta"] == "Ingresos diferidos" and l["debe"] == 600.00]
    assert mensuales
    assert "500,00" in servindustria["correcciones"][0]["valor_libro"]
    assert "600,00" in servindustria["correcciones"][0]["valor_corregido"]

    # Todo caso con [CON ERRATA] tiene su corrección registrada con razón.
    for caso in CASOS:
        if caso["estado_validacion"] in ("CON_ERRATA", "PARCIAL_CON_ERRATA"):
            assert caso["correcciones"], caso["codigo"]
            for correccion in caso["correcciones"]:
                assert correccion["razon"] and correccion["valor_corregido"]


def test_caso_61_18_excluye_la_fila_inconsistente():
    ejercicio = caso_de_datos("C61.18")
    assert ejercicio["filas_excluidas"]
    assert any("650.000,00" in fila for fila in ejercicio["filas_excluidas"])
    assert "650.000,00" not in json.dumps(ejercicio["totales_verificados"])
    # El caso con errata del plan de cuentas (§59.10 n.º 8) coincide con esta fila excluida.
    assert any("150.000,00" in errata["errata"] for errata in ERRATAS_PLAN_CUENTAS)


def test_erratas_del_plan_de_cuentas_no_se_replican():
    # §59.10 n.º 3 y n.º 7: `12104` es Muebles y enseres, `12103` la depreciación, y el costo
    # de ventas existe aunque la fuente lo omita.
    assert PLAN_CUENTAS_BASE["12104"][0] == "Muebles y enseres"
    assert "Depreciación acumulada edificios" in PLAN_CUENTAS_BASE["12103"][0]
    assert "51301" in PLAN_CUENTAS_BASE and "Costo de ventas" in PLAN_CUENTAS_BASE["51301"][0]
    assert len(PLAN_CUENTAS_BASE) == len(set(PLAN_CUENTAS_BASE))  # sin códigos duplicados


def test_tasas_demostrativas_etiquetadas_y_configurables_62_2():
    assert TASAS_DEMOSTRATIVAS, "debe haber tarifas demostrativas documentadas"
    for clave, ficha in TASAS_DEMOSTRATIVAS.items():
        assert ficha["etiqueta"] == ETIQUETA_TASAS
        assert ficha["editable_desde_panel"] is True
        assert ficha["fijar_en_codigo"] is False
        assert ficha["fuente"]
    assert TASAS_DEMOSTRATIVAS["iva"]["valor_fuente"] == 0.15
    assert TASAS_DEMOSTRATIVAS["iess_personal"]["valor_fuente"] == 0.0945


def test_formato_es_ec_sin_alterar_valores_62_6():
    assert formato_es_ec(1234.56) == "1.234,56"
    assert formato_es_ec(84800) == "84.800,00"
    assert formato_es_ec(141.75) == "141,75"
    patron_anglo = re.compile(r"\d,\d{3}\.\d{2}")
    for caso in CASOS:
        for texto in [caso["enunciado"]] + list(caso["datos"]):
            assert not patron_anglo.search(str(texto)), "%s: formato angloamericano" % caso["codigo"]


def test_las_fuentes_declaran_su_contexto_y_sus_paginas_sin_texto_62_3_62_4():
    for codigo, ficha in FUENTES.items():
        assert ficha["correlacion_paginas"] and ficha["pais_contexto"]
        assert ficha["paginas_sin_texto"]
    assert "IVA" in ADVERTENCIA_IVA_RETENCIONES and "retenciones" in ADVERTENCIA_IVA_RETENCIONES
    assert any("EXTRANJERO" in f["pais_contexto"].upper() or "HISTÓRICO" in f["pais_contexto"].upper()
               for f in FUENTES.values())


def test_nueve_reglas_62_de_las_cuales_ocho_son_de_trazabilidad_de_fuentes():
    assert len(REGLAS_TRAZABILIDAD) == 9
    numerales = [r["codigo"] for r in REGLAS_TRAZABILIDAD]
    assert numerales == ["R62.%d" % n for n in range(1, 10)]
    trazabilidad = [r for r in REGLAS_TRAZABILIDAD if r["trazabilidad_fuentes"]]
    assert len(trazabilidad) == 8, "las 8 reglas de trazabilidad de las fuentes (§62.1–62.9)"
    assert "R62.8" not in [r["codigo"] for r in trazabilidad]  # §62.8 regula el catálogo semilla
    for regla in REGLAS_TRAZABILIDAD:
        assert regla["texto_fuente"] and regla["aplicacion"] and regla["verificable"]


def test_modos_de_catalogo_semilla_62_8():
    assert len(MODOS_CATALOGO) == 3
    incompleto = [m for m in MODOS_CATALOGO if m["codigo"] == "INCOMPLETO"][0]
    assert incompleto["siembra_cuentas"] is False
    assert "no se siembran" in incompleto["descripcion"].lower()


# ============================================================================ Carga en la BD
@pytest.fixture()
def base(db):
    """Base de control ya sembrada con el banco de casos."""
    return db


def test_el_banco_queda_cargado_en_la_base_de_control(base):
    resumen = S.resumen_banco(base)
    assert resumen["total"] == 19
    assert resumen["activos"] == 19
    assert resumen["sin_solucion_en_fuente"] == 6
    assert resumen["con_correccion_de_erratas"] == 5      # 61.2, 61.4, 61.16, 61.17, 61.18
    assert resumen["con_dato_reconstruido"] == 4          # 61.1, 61.7, 61.8, 61.15
    assert resumen["por_estado"]["CON_ERRATA"] == 2
    assert len(S.fuentes(base)) == 4
    assert len(S.reglas(db_path=base)) == 9
    assert len(S.reglas(solo_trazabilidad=True, db_path=base)) == 8
    assert len(S.erratas_catalogo(base)) == 8


def test_cada_caso_guarda_su_ficha_y_su_trazabilidad(base):
    for codigo in ["C61.%02d" % n for n in range(1, 20)]:
        caso = S.obtener_caso(codigo, db_path=base)
        assert caso["ficha"]["completa"] is True
        assert caso["cita_fuente"]
        tipos = [fila["tipo"] for fila in caso["trazabilidad"]]
        assert "FICHA" in tipos
        assert any(fila["regla_codigo"] == "R62.7" for fila in caso["trazabilidad"])


def test_trazabilidad_de_erratas_y_datos_reconstruidos(base):
    guapulo = S.obtener_caso("C61.16", db_path=base)
    correcciones = [f for f in guapulo["trazabilidad"] if f["tipo"] == "CORRECCION"]
    assert correcciones and correcciones[0]["regla_codigo"] == "R62.1"
    assert correcciones[0]["valor_libro"] and correcciones[0]["valor_aplicado"]
    assert correcciones[0]["razon"]

    brilla = S.obtener_caso("C61.01", db_path=base)
    assert ETIQUETA_RECONSTRUIDO in [f["valor_aplicado"] for f in brilla["trazabilidad"]]
    assert any(f["regla_codigo"] == "R62.4" and f["campo"] == "contenido reconstruido"
               for f in brilla["trazabilidad"])
    assert any(f["regla_codigo"] == "R62.6" for f in brilla["trazabilidad"]) is False  # Ecuador


def test_fuentes_guardan_contexto_y_paginas_sin_texto_62_4(base):
    fuentes = {f["codigo"]: f for f in S.fuentes(base)}
    assert set(fuentes) == {"U2", "U3", "U4", "SENA"}
    assert fuentes["U2"]["correlacion_paginas"] == "impresa = PDF − 19"
    for fuente in fuentes.values():
        assert fuente["pais_contexto"]
        assert "páginas" in fuente["paginas_sin_texto"] or "página" in fuente["paginas_sin_texto"]
    assert "capa de texto" in fuentes["U2"]["paginas_sin_texto"]
    assert fuentes["SENA"]["notas"], "las notas de fidelidad de la fuente son obligatorias"


def test_no_se_muestra_la_solucion_de_los_casos_sin_solucion_62_5(base):
    for codigo in ["C61.11", "C61.12", "C61.13", "C61.14", "C61.15", "C61.19"]:
        estudiante = S.obtener_caso(codigo, para_estudiante=True, db_path=base)
        assert estudiante["solucion_visible"] is False
        assert estudiante["solucion"] == []
        assert estudiante["asientos_esperados"] == []
        assert estudiante["solucion_referencial"] == {}
        assert estudiante["practica_sin_solucion"] is True
        assert estudiante["respuesta_oficial_permitida"] is False
        docente = S.obtener_caso(codigo, para_estudiante=False, db_path=base)
        assert docente["solucion_visible"] is False  # tampoco la presenta como resuelta
    # Un caso verificado sí conserva su solución para el estudiante.
    ambato = S.obtener_caso("C61.02", para_estudiante=True, db_path=base)
    assert ambato["solucion"] and ambato["solucion_visible"] is True


def test_activar_un_caso_exige_ficha_completa_62_9(base):
    S.activar_caso("C61.02", activo=True, db_path=base)          # ficha completa: se permite
    import sqlite3
    conexion = sqlite3.connect(base)
    try:
        conexion.execute("UPDATE casos_libros SET anio = NULL, paginas_impresas = NULL "
                         "WHERE codigo = 'C61.05'")
        conexion.commit()
    finally:
        conexion.close()
    with pytest.raises(S.ErrorCasoLibro) as error:
        S.activar_caso("C61.05", activo=True, db_path=base)
    assert error.value.codigo == "FICHA_INCOMPLETA"
    assert "anio" in error.value.mensaje or "paginas_impresas" in error.value.mensaje


def test_tarifas_demostrativas_se_editan_desde_el_simulador_62_2(base):
    tasas = {t["clave"]: t for t in S.tasas_demostrativas(base)}
    assert tasas["iva"]["etiqueta"] == ETIQUETA_TASAS
    assert tasas["iva"]["valor_vigente"] == 0.15
    assert tasas["iva"]["editada"] is False
    ajustada = S.ajustar_tasa_demostrativa("iva", 0.12, db_path=base)
    assert ajustada["valor_vigente"] == 0.12
    assert ajustada["editada"] is True
    assert S.tasas_demostrativas(base)[0]["origen_valor"] in ("configuración académica", "fuente")
    assert {t["clave"] for t in S.tasas_demostrativas(base)} >= {"iva", "iess_personal"}
    with pytest.raises(S.ErrorCasoLibro):
        S.ajustar_tasa_demostrativa("no_existe", 0.5, db_path=base)


# ============================================================================ Intentos
def test_intento_correcto_se_verifica_y_se_registra(base):
    caso = S.obtener_caso("C61.02", db_path=base)
    abierto = S.iniciar_intento("C61.02", 3, db_path=base)
    assert abierto["numero_intento"] == 1 and abierto["intentos_maximos"] == 3
    resultado = S.enviar_intento("C61.02", 3, lineas=lineas_del_caso(caso),
                                 intento_id=abierto["intento_id"], db_path=base)
    assert resultado["puntuacion"] == 100.0
    assert resultado["resultado"] == "CORRECTO"
    assert resultado["oficial"] is True
    assert resultado["ficha"]["completa"] is True

    intentos = S.listar_intentos(codigo="C61.02", estudiante_id=3, db_path=base)
    assert len(intentos) == 1
    assert intentos[0]["estado"] == "EVALUADO"
    assert intentos[0]["puntuacion"] == 100.0
    assert intentos[0]["respuesta"]["lineas"]
    assert intentos[0]["verificacion"]["detalle"]


def test_intento_incorrecto_da_retroalimentacion(base):
    resultado = S.enviar_intento(
        "C61.02", 4, lineas=[{"cuenta": "Caja", "debe": 1500.00, "haber": 0.0},
                             {"cuenta": "Venta de mercaderías", "debe": 0.0, "haber": 1500.00}],
        db_path=base)
    assert resultado["puntuacion"] < 100
    assert resultado["resultado"] in ("PARCIALMENTE_CORRECTO", "INCORRECTO")
    assert any(mensaje.startswith("✗") for mensaje in resultado["mensajes"])
    assert "Faltó registrar" in resultado["retroalimentacion"]


def test_al_enviar_la_cifra_errada_del_libro_se_avisa_de_la_correccion_62_1(base):
    caso = S.obtener_caso("C61.16", db_path=base)
    lineas = lineas_del_caso(caso)
    for linea in lineas:
        if linea["cuenta"] == "11101" and linea["debe"] == 4600.00:
            linea["debe"] = 4000.00                      # la cifra impresa (errónea) del libro
    resultado = S.enviar_intento("C61.16", 5, lineas=lineas, db_path=base)
    avisos = [m for m in resultado["mensajes"] if "libro" in m and "corregid" in m]
    assert avisos, resultado["mensajes"]
    assert "4.600,00" in avisos[0]

    servindustria = S.obtener_caso("C61.17", db_path=base)
    lineas_17 = lineas_del_caso(servindustria)
    for linea in lineas_17:
        if linea["cuenta"] == "Ingresos diferidos" and linea["debe"] == 600.00:
            linea["debe"] = 500.00
            linea["haber"] = 0.0
    lineas_17.append({"cuenta": "Ingresos por servicios", "debe": 0.0, "haber": 500.00})
    resultado_17 = S.enviar_intento("C61.17", 5, lineas=lineas_17, db_path=base)
    assert any("600,00" in m for m in resultado_17["mensajes"])


def test_caso_sin_solucion_se_verifica_con_reglas_mecanicas_62_5(base):
    resultado = S.enviar_intento(
        "C61.12", 6, lineas=[{"cuenta": "Caja", "debe": 40000.00, "haber": 0.0},
                             {"cuenta": "31101", "debe": 0.0, "haber": 40000.00}],
        db_path=base)
    assert resultado["verificacion_mecanica"] is True
    assert resultado["oficial"] is False
    assert resultado["requiere_revision_docente"] is True
    assert set(resultado["detalle"]) == {"ASIENTO_CUADRADO", "CUENTAS_VALIDAS",
                                         "POSICION_DEBE_HABER", "BALANCE_CUADRADO"}
    assert resultado["puntuacion"] == 100.0

    descuadrado = S.enviar_intento(
        "C61.12", 7, lineas=[{"cuenta": "Caja", "debe": 40000.00, "haber": 0.0},
                             {"cuenta": "Banco del Austro", "debe": 0.0, "haber": 39000.00}],
        db_path=base)
    assert descuadrado["detalle"]["ASIENTO_CUADRADO"] == 0.0
    assert descuadrado["puntuacion"] < 100


def test_intentos_maximos_se_controlan(base):
    lineas = [{"cuenta": "Caja", "debe": 1.0, "haber": 0.0},
              {"cuenta": "31101", "debe": 0.0, "haber": 1.0}]
    for _ in range(3):                                   # C61.13 permite 3 intentos
        S.enviar_intento("C61.13", 8, lineas=lineas, db_path=base)
    assert len(S.listar_intentos(codigo="C61.13", estudiante_id=8, db_path=base)) == 3
    with pytest.raises(S.SinIntentos):
        S.iniciar_intento("C61.13", 8, db_path=base)
    with pytest.raises(S.SinIntentos):
        S.enviar_intento("C61.13", 8, lineas=lineas, db_path=base)


def test_ecuacion_contable_ampliada_61_11(base):
    resultado = S.enviar_intento("C61.11", 9, ecuacion={"activo": 74650.00, "pasivo": 22800.00,
                                                       "capital": 41850.00, "ingresos": 14000.00,
                                                       "gastos": 4000.00}, db_path=base)
    assert resultado["puntuacion"] == 100.0
    assert resultado["oficial"] is False                 # solución calculada por el simulador
    assert resultado["requiere_revision_docente"] is True
    malo = S.enviar_intento("C61.11", 10, ecuacion={"activo": 74650.00, "pasivo": 22800.00,
                                                    "capital": 40000.00, "ingresos": 14000.00,
                                                    "gastos": 4000.00}, db_path=base)
    assert malo["puntuacion"] < 100


def test_caso_con_totales_comprobados_61_7(base):
    caso = S.obtener_caso("C61.07", db_path=base)
    bueno = S.enviar_intento("C61.07", 11, totales=totales_del_caso(caso), db_path=base)
    assert bueno["puntuacion"] == 100.0
    assert bueno["oficial"] is True                      # saldos y totales publicados por la fuente
    assert caso["etiquetas"] and ETIQUETA_RECONSTRUIDO in caso["etiquetas"]
    malo = S.enviar_intento("C61.07", 12, totales={"sumas_debe": 1.0, "sumas_haber": 2.0},
                            db_path=base)
    assert malo["puntuacion"] < 100


def test_resumen_de_intentos_para_el_docente(base):
    caso = S.obtener_caso("C61.02", db_path=base)
    S.enviar_intento("C61.02", 13, lineas=lineas_del_caso(caso), db_path=base)
    S.enviar_intento("C61.02", 13, lineas=[{"cuenta": "Caja", "debe": 1.0},
                                           {"cuenta": "Ventas", "debe": 0.0, "haber": 1.0}],
                     db_path=base)
    resumen = S.resumen_intentos("C61.02", db_path=base)
    assert resumen["total"] == 2
    assert resumen["correctos"] == 1
    assert 0 <= resumen["promedio"] <= 100


# ============================================================================ Interfaz (rutas)
def test_listado_de_casos_para_el_estudiante(app_client, estudiante_client, db):
    respuesta = estudiante_client.get("/casos-libros")
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "C61.01" in cuerpo and "C61.19" in cuerpo
    assert "Casos prácticos de los libros" in cuerpo

    datos = estudiante_client.get("/casos-libros?formato=json").get_json()
    assert datos["success"] is True
    assert datos["total"] == 19
    assert datos["resumen"]["total"] == 19
    assert "iva_retenciones" in datos["advertencias"]
    # §62.5: en el JSON del estudiante no viaja la solución de los casos sin solución.
    sin_solucion = [c for c in datos["casos"] if c["codigo"] == "C61.12"][0]
    assert sin_solucion["solucion"] == [] and sin_solucion["asientos_esperados"] == []
    assert sin_solucion["cita_fuente"]


def test_ficha_de_un_caso_oculta_la_solucion_no_publicada(app_client, estudiante_client, db):
    ficha = estudiante_client.get("/casos-libros/C61.12")
    assert ficha.status_code == 200
    cuerpo = ficha.get_data(as_text=True)
    assert "C61.12" in cuerpo
    assert "sin solución visible" in cuerpo.lower() or "práctica sin solución" in cuerpo.lower()
    assert "4.570" in cuerpo or "4.570,00" in cuerpo          # los datos del enunciado sí se muestran

    datos = estudiante_client.get("/casos-libros/C61.12?formato=json").get_json()
    assert datos["caso"]["solucion"] == []
    assert datos["caso"]["solucion_visible"] is False

    # El docente sí puede ver el detalle de la ficha completa de un caso verificado.
    docente = cliente_docente()
    detalle = docente.get("/docente/casos-libros/C61.01?formato=json")
    assert detalle.status_code == 200
    assert detalle.get_json()["caso"]["solucion"]


def test_envio_de_intento_desde_el_formulario(app_client, estudiante_client, db):
    respuesta = estudiante_client.post("/casos-libros/C61.02/enviar", data={
        "cuenta_1": "Caja", "debe_1": "1725.00", "haber_1": "0",
        "cuenta_2": "41101", "debe_2": "0", "haber_2": "1500.00",
        "cuenta_3": "21301", "debe_3": "0", "haber_3": "225.00",
        "cuenta_4": "51301", "debe_4": "900.00", "haber_4": "0",
        "cuenta_5": "11402", "debe_5": "0", "haber_5": "900.00",
        "cuenta_6": "41101", "debe_6": "750.00", "haber_6": "0",
        "cuenta_7": "21301", "debe_7": "112.50", "haber_7": "0",
        "cuenta_8": "Caja", "debe_8": "0", "haber_8": "862.50",
        "cuenta_9": "11402", "debe_9": "450.00", "haber_9": "0",
        "cuenta_10": "51301", "debe_10": "0", "haber_10": "450.00",
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "CORRECTO" in cuerpo and "100" in cuerpo

    json_respuesta = estudiante_client.post("/casos-libros/C61.09/enviar?formato=json",
                                            json={"lineas": [{"cuenta": "Caja", "debe": 100.0,
                                                              "haber": 0.0},
                                                             {"cuenta": "Ventas", "debe": 0.0,
                                                              "haber": 100.0}]})
    assert json_respuesta.status_code == 200
    cuerpo_json = json_respuesta.get_json()
    assert cuerpo_json["success"] is True
    assert cuerpo_json["resultado"]["puntuacion"] < 100


def test_historial_de_intentos_del_estudiante(estudiante_client, db):
    estudiante_client.post("/casos-libros/C61.02/enviar?formato=json", json={
        "lineas": [{"cuenta": "Caja", "debe": 100.0}, {"cuenta": "Ventas", "debe": 0.0,
                                                      "haber": 100.0}]})
    historial = estudiante_client.get("/casos-libros/mis-intentos")
    assert historial.status_code == 200
    datos = estudiante_client.get("/casos-libros/mis-intentos?formato=json").get_json()
    assert datos["total"] >= 1
    assert datos["intentos"][0]["caso_codigo"] == "C61.02"


def test_panel_docente_del_banco_de_casos(app_client, db):
    app_client.post("/login", data={"username": "docente", "password": "docente123"},
                    follow_redirects=True)
    panel = app_client.get("/docente/casos-libros")
    assert panel.status_code == 200
    cuerpo = panel.get_data(as_text=True)
    assert "R62.1" in cuerpo and "R62.9" in cuerpo
    assert ETIQUETA_TASAS in cuerpo
    assert "Configuración académica" in cuerpo

    datos = app_client.get("/docente/casos-libros?formato=json").get_json()
    assert datos["success"] is True
    assert len(datos["casos"]) == 19
    assert len(datos["reglas"]) == 9
    assert len(datos["reglas_trazabilidad"]) == 8
    assert len(datos["erratas_catalogo"]) == 8
    assert len(datos["modos_catalogo"]) == 3
    assert len(datos["tasas"]) == len(TASAS_DEMOSTRATIVAS)
    assert datos["resumen"]["total"] == 19


def test_estudiante_no_accede_al_panel_docente(estudiante_client, db):
    respuesta = estudiante_client.get("/docente/casos-libros")
    assert respuesta.status_code == 403


def test_docente_edita_una_tarifa_demostrativa(app_client, db):
    app_client.post("/login", data={"username": "docente", "password": "docente123"},
                    follow_redirects=True)
    respuesta = app_client.post("/docente/casos-libros/tasas", data={"clave": "iva", "valor": "0.12"})
    assert respuesta.status_code in (200, 302)
    datos = app_client.get("/docente/casos-libros?formato=json").get_json()
    iva = [t for t in datos["tasas"] if t["clave"] == "iva"][0]
    assert iva["valor_vigente"] == 0.12 and iva["editada"] is True


def test_docente_activa_y_desactiva_un_caso(app_client, db):
    app_client.post("/login", data={"username": "docente", "password": "docente123"},
                    follow_redirects=True)
    respuesta = app_client.post("/docente/casos-libros/C61.02/activar", json={"activo": 0})
    assert respuesta.status_code == 200
    assert respuesta.get_json()["activo"] is False
    import sqlite3
    conexion = sqlite3.connect(db)
    try:
        activo = conexion.execute("SELECT activo FROM casos_libros WHERE codigo = 'C61.02'"
                                  ).fetchone()[0]
    finally:
        conexion.close()
    assert activo == 0
    # Un caso desactivado no admite intentos nuevos.
    with pytest.raises(S.CasoNoDisponible):
        S.iniciar_intento("C61.02", 14, db_path=db)
