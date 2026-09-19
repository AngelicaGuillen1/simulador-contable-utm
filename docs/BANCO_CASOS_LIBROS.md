# Banco de casos prácticos de los libros (§61) y trazabilidad de las fuentes (§62)

Implementación de las secciones **§61** (19 casos prácticos con cifras) y **§62** (advertencias
de fidelidad y calidad) del *Prompt Maestro v2* del Simulador Contable de Contabilidad I (UTM).

Todo se carga como **DATOS**: los casos, sus fichas y las reglas viven en la base de **control**
(`database/simulator.db`) y no en el código de la aplicación. La interfaz, la verificación de
intentos y las pruebas automáticas consumen esos datos.

## Archivos

| Archivo | Contenido |
|---|---|
| `database/banco_casos_libros.py` | Fuentes y su correlación de páginas, catálogo semilla §59, erratas §59.10, las 9 reglas §62, tarifas demostrativas §62.2, modos de catálogo §62.8 y utilidades de formato `es-EC`. |
| `database/casos_libros_61.py` | Los **19 casos** de §61 con enunciado, datos, asientos esperados, saldos, totales, solución, correcciones y etiquetas. |
| `database/esquema_casos_libros.py` | Esquema SQLite (5 tablas) y siembra idempotente (fuentes, reglas, casos y ficha de trazabilidad). |
| `database/cargar_casos_libros.py` | Cargador de línea de comandos (`--db`, `--listar`). |
| `services/casos_libros_service.py` | Lectura del banco, aplicación de las reglas §62, tarifas editables y **verificación de intentos**. |
| `routes/casos_libros.py` | Rutas de estudiante y de docente (HTML y JSON). |
| `templates/casos_libros/*.html` | Listado, ficha del caso, historial de intentos y panel docente. |
| `tests/test_casos_libros.py` | Pruebas automáticas de datos, carga, reglas, intentos e interfaz (38 pruebas). |

## Tablas (base de control)

* `casos_libros_fuentes` — fuente, edición, año, contexto normativo, correlación de páginas y
  páginas sin capa de texto.
* `casos_libros` — los 19 casos con su ficha obligatoria y su *payload* JSON (datos, asientos
  esperados, saldos, totales, solución, correcciones, etiquetas, advertencias).
* `casos_libros_trazabilidad` — una fila por ficha, corrección de errata, etiqueta de fidelidad,
  advertencia y regla aplicada (con valor del libro, valor aplicado y razón).
* `casos_libros_reglas` — las reglas `R62.1`–`R62.9` y las erratas `E59.1`–`E59.8`.
* `casos_libros_intentos` — cada intento del estudiante con su respuesta, verificación, puntaje,
  resultado y si el resultado puede ser oficial.

## Los 19 casos de §61

| Caso | Nombre | Fuente y páginas (impresa / PDF) | Estado |
|---|---|---|---|
| C61.01 | BrilloCar: ciclo contable integral | U2 imp. 134–172 (PDF 153–191) · 2023 | VERIFICADO |
| C61.02 | Ambato Cía. Ltda.: venta, costo y devolución | U4 imp. 102–103 · 2024 | VERIFICADO |
| C61.03 | Coral / Portal: interés implícito | U4 imp. 94–95 · 2024 | VERIFICADO |
| C61.04 | Smart Touch Learning: 12 hechos de abril | U3 imp. 75–82 (PDF 107–114) · 2010 | VERIFICADO |
| C61.05 | Harper Service Center: resumen capítulo 2 | U3 imp. 86–89 (PDF 118–121) · 2009 | VERIFICADO |
| C61.06 | Heat Miser: compras, descuentos y flete | U3 imp. 284–285 (PDF 316–317) · 2011 | VERIFICADO |
| C61.07 | Muebles el Cóndor: Mayor y Balances | SENA imp. 57–63 (PDF 59–65) · 1977 | VERIFICADO CON RESERVA |
| C61.08 | Autocontroles breves del SENA | SENA imp. 17–57 · 1977 | VERIFICADO |
| C61.09 | Ejercicios cortos resueltos de U4 | U4 imp. 42–97 · 2024 | VERIFICADO |
| C61.10 | Ejercicios cortos capítulo 5 de U3 | U3 imp. 300–301 (PDF 332–333) · 2011 | VERIFICADO (parcialmente calculado) |
| C61.11 | Limpia-Full: ecuación contable ampliada | U2 imp. 121 (PDF 140) · 2025 | SIN SOLUCIÓN |
| C61.12 | TechnoBoy: identificación de cuentas | U2 imp. 121–122 · 2023 | SIN SOLUCIÓN |
| C61.13 | Clean Solutions: cuenta y lado (Debe/Haber) | U2 imp. 123–124 · 2025 | SIN SOLUCIÓN |
| C61.14 | Ejercicios N°6, N°7, N°8 y N°10 de U2 | U2 imp. 124–129 · 2025 | SIN SOLUCIÓN |
| C61.15 | Servicios Unidos: estados financieros con ajustes | U4 imp. 124–127 · 2024 | SIN SOLUCIÓN |
| C61.16 | Guápulo Cía. Ltda.: ventas con costo | U4 imp. 92–93 · 2024 | CON ERRATA (corregida) |
| C61.17 | Servindustria: ingresos diferidos | U4 imp. 96–97 · 2024 | CON ERRATA (corregida) |
| C61.18 | Ejercicio N°1 y N°4 de ecuación contable | U2 imp. 120–123 · 2025 | PARCIAL / CON ERRATA |
| C61.19 | Préstamo bancario con contribución del 0,5 % | U4 imp. 82–83 · 2024 | SIN SOLUCIÓN |

Correcciones de erratas registradas en la ficha del caso (§62.1):

* **C61.02** — fecha del asiento de devolución: libro 20-may → enunciado 22-may.
* **C61.04** — saldo final de Cuentas por pagar: 500,00 (ficha §61.4) → **300,00**, porque con
  500,00 la balanza publicada 38.800,00 = 38.800,00 no cuadra.
* **C61.16** — Caja del asiento del 25-jun: 4.000,00 (descuadrado) → **4.600,00**.
* **C61.17** — reconocimiento mensual: 500,00 → **600,00** (7.200,00 ÷ 12 meses).
* **C61.18** — quinta fila del Ejercicio N°1 (patrimonio negativo de −150.000,00) **excluida**.

Auditoría realizada al cargar los datos (comprobaciones aritméticas automáticas):
los asientos esperados de todos los casos cuadran partida doble; los saldos finales suman igual
en Debe y Haber; las sumas y saldos del balance de comprobación cuadran; y todos los códigos de
cuenta citados existen en el catálogo semilla §59.

## Las reglas de trazabilidad de las fuentes (§62)

§62 numera **nueve** reglas: **ocho** regulan la trazabilidad de las fuentes y una (§62.8) el
catálogo semilla de cuentas. La interfaz muestra las nueve y marca cuáles son de trazabilidad.

| Regla | Título | Dónde se aplica |
|---|---|---|
| R62.1 | No replicar erratas; registrar toda corrección | `correcciones` por caso + tabla de trazabilidad |
| R62.2 | Las tarifas de las fuentes son datos históricos o demostrativos | `TASAS_DEMOSTRATIVAS` + tabla `parametros` (editables) |
| R62.3 | Las fuentes no explican el IVA ni las retenciones como normativa | aviso fijo en toda ficha y en el panel docente |
| R62.4 | Constancia de las páginas que eran imágenes sin texto | `fuentes.paginas_sin_texto` + etiqueta «dato reconstruido» |
| R62.5 | Ningún ejercicio sin solución se presenta como resuelto | `solucion_visible = 0` + verificación mecánica no oficial |
| R62.6 | Advertir el marco extranjero o histórico y normalizar el formato | `contexto_normativo` + filtros `num_ec` / `money_ec` |
| R62.7 | Citar siempre la doble numeración de páginas | `cita_fuente()` en todas las fichas |
| R62.8 | El catálogo semilla es un punto de partida (3 modos) | `MODOS_CATALOGO` + aviso en el panel docente |
| R62.9 | Ficha obligatoria antes de publicar un caso | `ficha_incompleta()` y `activar_caso()` |

## Verificación de intentos

* `iniciar_intento` / `enviar_intento` controlan los **intentos máximos** de cada caso y registran
  en `casos_libros_intentos` la respuesta, la verificación y el puntaje.
* Puntaje por tipo de verificación:
  * `ASIENTO` (fuente con solución): cuentas 40 · posición Debe/Haber 30 · importes 20 · partida
    doble 10. `CORRECTO` ≥ 85, `PARCIALMENTE_CORRECTO` ≥ 50.
  * `MECANICA` (fuente sin solución, §62.5): asiento cuadrado 40 · cuentas válidas 20 · posición
    Debe/Haber 30 · balance cuadrado 10.
  * `TOTALES` (saldos y totales publicados): coincidencia con los totales comprobados del caso.
  * `ECUACION` (ecuación contable ampliada): elementos + identidad Activo = Pasivo + Capital +
    Ingresos − Gastos.
* Un intento es **oficial** solo si la solución está publicada por la fuente y es verificable. Los
  casos sin solución o con «solución calculada» quedan marcados como **no oficiales** y requieren
  revisión del docente (§62.4 y §62.5).
* Si el estudiante envía la cifra impresa que la fuente trae errada, la retroalimentación cita la
  errata, el valor corregido y la razón registrada (§62.1).

## Uso

```bash
# Cargar (idempotente) el banco en la base de control
.venv/Scripts/python.exe database/cargar_casos_libros.py
.venv/Scripts/python.exe database/cargar_casos_libros.py --listar

# Pruebas automáticas del módulo
.venv/Scripts/python.exe -m pytest tests/test_casos_libros.py -q
```

Interfaz:

* Estudiante: **Casos de los libros (§61)** → `/casos-libros`, ficha `/casos-libros/<codigo>`,
  historial `/casos-libros/mis-intentos`.
* Docente: **Banco de casos §61 y §62** → `/docente/casos-libros` (fichas, trazabilidad, reglas,
  erratas del plan de cuentas, tarifas demostrativas editables e intentos).

Todas las vistas aceptan `?formato=json` para su representación en JSON.

## Ficha de cada caso (§62.9)

Cada caso se activa solo si su ficha está completa por escrito: **fuente completa, página (con
doble numeración), año, si la solución está o no en la fuente y si hubo corrección de erratas**.
`activar_caso()` rechaza con `FICHA_INCOMPLETA` cualquier caso sin esos datos, y las pruebas
verifican esa negativa.
