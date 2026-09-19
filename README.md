# Simulador Integral de Sistema Contable
### Servicios y Comercialización de Productos

Aplicación web profesional desarrollada con **Python + Flask + SQLite** que funciona como un
sistema contable educativo completo (ERP académico). El estudiante administra una empresa simulada
—**Comercial y Servicios Nueva Esperanza S.A.**— ejecutando el ciclo contable íntegro: desde el
documento fuente hasta los estados financieros, con evaluación automática e inteligencia artificial.

> “Aprende contabilidad gestionando una empresa en un entorno de simulación.”

---

## 1. Objetivo

Servir de entorno práctico para estudiantes de **Contabilidad, Auditoría, Administración y Finanzas**,
permitiendo operar una empresa real simulada con operaciones **relacionadas entre sí**: compras,
ventas, servicios, cobros, pagos, inventarios, cartera, tesorería, impuestos, ajustes, cierre y
estados financieros. No es un conjunto de ejercicios aislados: cada operación actualiza de forma
automática y simultánea el inventario, la cartera, la tesorería, los impuestos, el libro diario,
el libro mayor, el balance de comprobación y los estados financieros.

## 2. Tecnologías

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.11+, Flask 3, Jinja2 |
| Persistencia | SQLite (38 tablas, claves primarias/foráneas, índices) |
| Frontend | HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, JavaScript (Chart.js) |
| Exportación | CSV nativo, Excel (openpyxl), versión imprimible para PDF |
| Pruebas | pytest (113 pruebas automáticas) |
| IA / Agentes | Agentes especializados en Python + API JSON interna + herramientas estructuradas |

## 3. Arquitectura

```
Interfaz (Jinja2 + Bootstrap)
        │  (nunca contiene lógica contable crítica)
Rutas Flask (routes/)
        │
Servicios de negocio y contabilidad (services/)   ← única vía de escritura
        │
Herramientas estructuradas (tools/)  ← superficie que consumen los agentes
        │
Agentes especializados (agents/)
        │
SQLite (database/simulator.db)
```

Principios aplicados:

* **Separación estricta** entre interfaz, lógica empresarial, lógica contable, persistencia,
  agentes y herramientas.
* **Partida doble obligatoria**: ningún asiento descuadrado puede contabilizarse
  (`AccountingService.validate_journal_entry`).
* **Integridad contable**: una venta afecta simultáneamente venta, inventario/Kardex, costo de
  ventas, cartera, caja/banco, impuestos, diario, mayor, balance y estados financieros.
* **Trazabilidad total**: registro de auditoría con usuario, acción, módulo, valor anterior, valor
  nuevo, IP, agente y herramienta ejecutada.
* **Nada se borra**: los asientos contabilizados se anulan mediante **reversión** con contra-asiento.
* **Las tasas tributarias nunca se inventan**: provienen de la tabla `impuestos`; si no existe
  configuración, la operación se rechaza con un mensaje explícito.

## 4. Estructura del proyecto

```
app.py                      # Punto de entrada Flask (factory + manejo de errores 403/404/500)
config.py                   # Configuración (nombre, RUC, ruta de la base)
models.py                   # Conexión SQLite (WAL, foreign keys) y utilidades
requirements.txt            # Dependencias
README.md                   # Este documento

services/                   # Lógica de negocio y contabilidad (única vía de escritura)
├── accounting_service.py   # Motor de partida doble, mayor, balance y estados financieros
├── inventory_service.py    # Inventarios, Kardex, promedio ponderado y FIFO
├── sales_service.py        # Ventas de bienes, servicios y cobros de cartera
├── purchase_service.py     # Compras y pagos a proveedores
├── treasury_service.py     # Caja, arqueos, bancos, movimientos y conciliación
├── tax_service.py          # Configuración tributaria y cálculo de impuestos
├── document_service.py     # Documentos fuente (facturas, comprobantes, notas, arqueos…)
├── period_service.py       # Períodos contables y fecha de trabajo de la simulación
├── simulation_service.py   # Simulaciones, niveles, casos, intentos y analítica
├── evaluation_service.py   # Evaluación con rúbrica y retroalimentación específica
└── audit_service.py        # Registro de auditoría y trazabilidad

agents/                     # Arquitectura agéntica
├── orchestrator.py         # Agente Orquestador (clasifica la intención y enruta)
├── accounting_agent.py     # Agente Contable
├── inventory_agent.py      # Agente de Inventarios
├── tax_agent.py            # Agente Tributario  (solo consulta configuración real)
├── audit_agent.py          # Agente Auditor    (descuadres, duplicidades, anomalías)
├── tutor_agent.py          # Agente Tutor      (andamiaje pedagógico progresivo)
├── evaluator_agent.py      # Agente Evaluador  (intentos, errores, dominio)
└── case_generator_agent.py # Agente Generador de Casos

tools/                      # 37+ herramientas estructuradas expuestas a los agentes
├── accounting_tools.py     # get_chart_of_accounts, get_account, validate_journal_entry, …
├── inventory_tools.py      # get_product, get_inventory, register_inventory_entry/exit, FIFO…
├── financial_tools.py      # create_sale, create_purchase, create_receivable, calculate_tax, …
└── simulation_tools.py     # create_simulation_case, evaluate_student_attempt, audit_transaction…

routes/                     # Blueprints HTTP + API JSON
├── auth.py dashboard.py home.py accounting.py sales.py purchases.py
├── inventory.py treasury.py partners.py documents.py taxes.py
├── financial_statements.py simulations.py tutor.py reports.py admin.py api.py

templates/                  # 46 plantillas Jinja2 (base.html evita duplicar header/sidebar/footer)
static/css/custom.css       # Tema ERP (sidebar, KPI cards, tablas, banners de validación)
static/js/                  # app.js (buscador global), journal.js, simulation.js, tutor.js
database/
├── db_init.py              # Esquema de 38 tablas + índices
├── seed_data.py            # Datos de demostración (30 operaciones reales del período)
├── banco_casos_libros.py   # §62: fuentes, reglas de trazabilidad, tarifas demostrativas, catálogo §59
├── casos_libros_61.py      # §61: los 19 casos prácticos con cifras (datos puros)
├── esquema_casos_libros.py # Tablas y siembra del banco de casos y de las reglas §62
├── cargar_casos_libros.py  # Cargador del banco de casos (§61) por línea de comandos
└── simulator.db            # Base de datos SQLite
tests/                      # Pruebas automáticas (pytest)

serve.py                    # Servidor de producción (waitress) para servicio 24/7
wsgi.py                     # Punto de entrada WSGI (waitress/gunicorn/Docker)
docs/
├── MANUAL_DE_USUARIO.md    # Manual de usuario (fuente única, se sirve en /manual)
├── MANUAL_DE_USUARIO.html   # Manual en HTML (generado por docs/build_manual.py)
├── DESPLIEGUE.md           # Guía de despliegue 24/7 (Windows, VPS, PaaS, Docker)
└── build_manual.py         # Generador del manual en HTML
deploy/
├── windows/                # Arranque automático del servicio en Windows
├── hostinger/              # Instalador para VPS Ubuntu (un solo comando)
├── pythonanywhere/wsgi.py  # URL pública gratuita con PythonAnywhere
├── systemd/ nginx/         # Servicio y proxy inverso para VPS
├── backup_db.py            # Respaldo en caliente de la base SQLite
├── cambiar_credenciales.py # Cambio de contraseñas antes de publicar
└── verificar_despliegue.py # Verificación del despliegue publicado
.devcontainer/              # Abrir el sistema en el navegador con GitHub Codespaces
.github/workflows/          # Integración continua: pruebas + arranque real en Linux
Procfile · Dockerfile · render.yaml   # Artefactos para plataformas gestionadas
```

## 4.b Cómo abrir el sistema desde GitHub

| Vía | Sirve para | Requisitos |
|---|---|---|
| **GitHub Codespaces** (`.devcontainer/`) | Abrir el simulador en el navegador, sin instalar nada; una instancia por estudiante | Cuenta de GitHub (plan gratuito: 120 horas-núcleo/mes) |
| **Descarga del repositorio** (`Code → Download ZIP`) | Ejecutarlo en el propio computador | Python 3.11+ |
| **PythonAnywhere** (`deploy/pythonanywhere/wsgi.py`) | **Una URL pública para todo el curso**, gratis | Cuenta gratuita en pythonanywhere.com |
| **GitHub Pages** (`docs/`) | Portada del curso, manual y guía en línea | — |

> **GitHub Pages no puede ejecutar la aplicación:** solo publica contenido estático. El simulador
> necesita un proceso Python y una base de datos, por lo que se ejecuta en Codespaces, en
> PythonAnywhere o en un servidor (ver `docs/DESPLIEGUE.md`).

## 5. Instalación

```bash
# 1. Requisitos previos: Python 3.11 o superior
python --version

# 2. Instalar dependencias
pip install -r requirements.txt
```

## 6. Ejecución

```bash
# 1. (Opcional) Regenerar los datos de demostración
python database/seed_data.py

# 2a. Desarrollo local (servidor de Flask, recarga automática)
python app.py
```

La aplicación queda disponible en: **http://127.0.0.1:5000** y el manual de usuario en
**http://127.0.0.1:5000/manual**.

**Puesta en producción y servicio 24/7** (servidor `waitress`, no el de desarrollo):

```bash
python serve.py                      # http://127.0.0.1:5000 (HOST/PORT del entorno)
HOST=0.0.0.0 PORT=8080 python serve.py
```

En Windows, para dejarlo arrancando solo y reiniciándose si falla:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\windows\instalar_arranque_automatico.ps1 -Puerto 8080
```

Verificación de un despliegue ya publicado:

```bash
python deploy/verificar_despliegue.py --url http://127.0.0.1:8080
```

Guía completa (VPS con dominio y HTTPS, plataformas gestionadas, Docker, respaldos y lista de
seguridad): **`docs/DESPLIEGUE.md`**.

## 7. Base de datos

SQLite en `database/simulator.db` con **38 tablas**, entre ellas:
`roles, usuarios, empresas, periodos, parametros, cuentas, asientos, detalle_asientos, impuestos,
productos, movimientos_inventario, kardex_lotes, clientes, proveedores, ventas, detalle_ventas,
compras, detalle_compras, catalogo_servicios, transacciones_servicios, cuentas_cobrar, cobros,
cuentas_pagar, pagos, cajas, movimientos_caja, arqueos_caja, bancos, movimientos_bancarios,
conciliaciones_bancarias, documentos_fuente, simulaciones, casos_simulacion, intentos_estudiante,
detalle_intentos, cursos, matriculas, auditoria`.

Se definen claves primarias, claves foráneas, restricciones y **índices** de rendimiento sobre los
detalles de asiento, movimientos de inventario, cartera, cuentas por pagar y auditoría.

**Fecha de trabajo de la simulación.** El sistema no depende del reloj real: la tabla `parametros`
guarda la *fecha de trabajo* (por defecto `2026-04-30`) con la que se registran todas las operaciones.
El Administrador puede cambiarla dentro del período abierto en `/admin`.

## 8. Credenciales de demostración

| Rol | Usuario | Contraseña | Alcance |
|-----|---------|-----------|---------|
| Administrador | `admin` | `admin123` | Configuración, usuarios, parámetros, auditoría |
| Docente | `docente` | `docente123` | Simulaciones, casos, rúbricas, analítica |
| Estudiante | `estudiante` | `estudiante123` | Casos, registros, libros, estados, puntuaciones |
| Auditor | `auditor` | `auditor123` | Solo lectura: movimientos, libros, estados, trazabilidad |

Las contraseñas se almacenan **con hash** (`pbkdf2:sha256` de Werkzeug); nunca en texto plano.

## 9. Roles y permisos

* **Administrador**: usuarios, parámetros tributarios, cuentas, empresas, períodos, auditoría.
* **Docente**: crea simulaciones y casos, define dificultad/rúbricas, revisa desempeño grupal.
* **Estudiante**: desarrolla casos, registra operaciones, consulta libros y estados, se autoevalúa.
* **Auditor**: acceso de solo lectura a movimientos, libros, estados y trazabilidad.

El control se implementa con sesiones Flask y los decoradores `@login_required` / `@roles_required`
(por ejemplo, `/admin/*` responde **403 con mensaje explicativo** a cualquier otro rol).

## 10. Módulos disponibles

Dashboard · Planeación de cuentas · Libro Diario · Libro Mayor · Balance de Comprobación ·
Ajustes · Cierre contable · Ventas · Servicios · Compras · Productos · Kardex (Promedio y FIFO) ·
Existencias y alertas · Caja y arqueos · Bancos y movimientos · Conciliación bancaria · Clientes ·
Cuentas por cobrar · Proveedores · Cuentas por pagar · Documentos fuente · Tributación ·
Estado de Resultados · Estado de Situación Financiera · Flujo de Efectivo · Simulador de casos ·
Evaluaciones · Panel de analítica docente · Tutor Contable IA · Centro de Reportes ·
Administración del sistema.

## 11. Funcionamiento de la simulación

1. El estudiante ingresa a **Simulador de Casos** y elige uno de los cuatro niveles:
   * **Nivel 1 — Básico**: compras y ventas de contado, servicios, cobros y pagos.
   * **Nivel 2 — Intermedio**: crédito, inventarios, Kardex, IVA y descuentos.
   * **Nivel 3 — Avanzado**: ajustes, arqueo, depreciación, provisiones, conciliación e impuestos.
   * **Nivel 4 — Integral**: gestión completa del período + asiento de cierre.
2. Cada caso presenta fecha, enunciado, documento fuente, datos de la transacción y condiciones de
   pago, **sin revelar la solución**.
3. El estudiante propone las cuentas, decide Debe/Haber e ingresa los importes; el sistema valida la
   partida doble antes de enviar.
4. El **Agente Evaluador** califica de 0 a 100 con rúbrica: 40 % cuentas, 30 % posición Debe/Haber,
   20 % importes, 10 % partida doble, menos 5 puntos por pista utilizada.
5. La retroalimentación es **específica**, por ejemplo:
   *“La cuenta ‘Caja General’ está correctamente seleccionada, pero su movimiento debe registrarse
   en el Debe porque aumenta un activo.”*
6. Quedan registrados intentos, respuestas, errores, pistas, tiempo y puntuación; el docente accede
   a la analítica grupal e individual.

Los casos de demostración se generan a partir de los **asientos reales** registrados en la base, de
modo que la solución esperada coincide exactamente con la contabilidad del período.

## 11.b Banco de casos prácticos de los libros (§61) y trazabilidad de las fuentes (§62)

Además de los casos generados por el sistema, el simulador carga como **DATOS** el banco de los
**19 casos prácticos de los libros** descritos en la sección §61 del Prompt Maestro v2 y aplica las
reglas de trazabilidad de las fuentes de §62. Todo vive en la base de **control** (contenido
académico compartido) y se puede recargar en cualquier momento:

```bash
python database/cargar_casos_libros.py            # carga idempotente del banco (§61 y §62)
python database/cargar_casos_libros.py --listar   # informe del estado del banco
```

* **Ficha obligatoria por caso (§62.9):** fuente completa, página con **doble numeración** (impresa
  y del PDF, §62.7), año, si la solución está o no en la fuente y si hubo corrección de erratas.
  `activar_caso()` rechaza cualquier caso con ficha incompleta.
* **Erratas corregidas y registradas (§62.1):** C61.02 (fecha), C61.04 (Cuentas por pagar 300,00 en
  lugar de 500,00), C61.16 (Caja 4.600,00 en lugar de 4.000,00), C61.17 (reconocimiento mensual
  600,00 en lugar de 500,00) y C61.18 (fila de patrimonio negativo excluida).
* **Casos sin solución (§62.5):** C61.11 a C61.19 se cargan como enunciado de práctica **sin
  solución visible** y se verifican con reglas mecánicas (asiento cuadrado, cuentas válidas,
  posición Debe/Haber y balance cuadrado); el resultado queda marcado como **no oficial**.
* **Fidelidad de las fuentes (§62.2, §62.3, §62.4 y §62.6):** las tarifas de los libros quedan
  etiquetadas como *Configuración académica / demostrativa* y se editan desde el panel docente
  (`/docente/casos-libros`); toda ficha advierte que las fuentes no explican el IVA ni las
  retenciones como normativa, y las páginas que eran imagen sin texto se muestran con la etiqueta
  «dato reconstruido — pendiente de validación con el facsímil».
* **Interfaz:** *Casos de los libros (§61)* para el estudiante (`/casos-libros`, ficha por caso,
  historial de intentos) y *Banco de casos §61 y §62* para el docente (`/docente/casos-libros`, con
  reglas, erratas del plan de cuentas, tarifas demostrativas editables e intentos). Todas las vistas
  responden también en JSON con `?formato=json`, y las cifras se muestran en formato `es-EC`
  (1.234,56) sin alterar ningún valor.

Detalle completo en `docs/BANCO_CASOS_LIBROS.md`.

## 12. Arquitectura agéntica

| Agente | Responsabilidad |
|--------|-----------------|
| **Orquestador** | Analiza la solicitud, identifica la intención y enruta al agente correcto |
| **Contable** | Cuentas, débitos, créditos, partida doble, diario, mayor, estados financieros |
| **Inventarios** | Entradas, salidas, stock, Kardex, costo de ventas, FIFO y promedio ponderado |
| **Tributario** | Consulta los parámetros tributarios; **nunca** inventa porcentajes |
| **Auditor** | Detecta descuadres, duplicidades, inconsistencias, fechas inválidas y anomalías |
| **Tutor** | Explicaciones, pistas y preguntas con andamiaje progresivo |
| **Evaluador** | Analiza intentos, errores, puntuaciones y nivel de dominio |
| **Generador de Casos** | Crea escenarios coherentes según parámetros del docente |

Ningún agente modifica la base de datos con texto libre: toda escritura pasa por las herramientas
estructuradas o por la API interna.

## 13. Herramientas de los agentes (37)

`get_chart_of_accounts, get_account, get_account_balance, validate_journal_entry,
create_journal_entry, reverse_journal_entry, close_accounting_period, get_product, get_inventory,
register_inventory_entry, register_inventory_exit, calculate_weighted_average, calculate_fifo,
calculate_cost_of_goods_sold, create_sale, create_purchase, create_service_transaction,
create_receivable, create_payable, register_collection, register_payment, get_customer_balance,
get_supplier_balance, get_cash_balance, get_bank_balance, reconcile_bank, get_tax_configuration,
calculate_tax, generate_trial_balance, generate_income_statement, generate_balance_sheet,
generate_cash_flow, create_simulation_case, evaluate_student_attempt, generate_feedback,
get_student_progress, audit_transaction`

Verificación en caliente: `GET /api/tools` devuelve `faltantes: []`.

## 14. API interna (JSON)

`/api/health` · `/api/dashboard` · `/api/accounts` · `/api/accounts/<id>/balance` ·
`/api/journal/validate` · `/api/journal/create` · `/api/products` · `/api/inventory` ·
`/api/inventory/<id>` · `/api/inventory/alerts` · `/api/sales` · `/api/purchases` · `/api/services` ·
`/api/customers` · `/api/customers/<id>/history` · `/api/suppliers` · `/api/suppliers/<id>/history` ·
`/api/receivables` · `/api/payables` · `/api/collections` · `/api/payments` · `/api/treasury` ·
`/api/taxes` · `/api/taxes/calculate` · `/api/statements` · `/api/documents` · `/api/documents/<id>` ·
`/api/periods` · `/api/simulations` · `/api/simulations/<id>` · `/api/evaluate` ·
`/api/progress/<id>` · `/api/audit` · `/api/search` · `/api/tools`

## 15. Pruebas automáticas

```bash
python -m pytest tests -q
```

**275 pruebas** cubren: partida doble, asientos descuadrados, mayor vs. diario, balance de
comprobación, ecuación **Activo = Pasivo + Patrimonio**, reversión de asientos, períodos y fechas,
inventarios (entradas, salidas, stock, Kardex, promedio ponderado y FIFO), costo de ventas, ventas
de contado y crédito, servicios, compras, cuentas por cobrar y por pagar, cobros y pagos, caja y
arqueos (con regularización contable), conciliación bancaria, impuestos, estados financieros, cierre
contable, evaluación del estudiante con rúbrica, navegación por los 40 módulos de la interfaz,
flujos completos de operaciones por formulario, exportaciones CSV/Excel/impresión, API interna,
manual de usuario, control de roles, documentos fuente, trazabilidad y auditoría, y el **banco de
casos prácticos de los libros (§61) con las reglas de trazabilidad de las fuentes (§62)**:
ficha obligatoria por caso, erratas corregidas y registradas, doble numeración de páginas,
tarifas demostrativas editables, casos sin solución con verificación mecánica no oficial y
control de intentos (`tests/test_casos_libros.py`).

Resultado verificado: **275 passed** (suite completa en ~6 min).

Además se verificó el sistema en ejecución real con peticiones HTTP, tanto con el servidor de
desarrollo (`python app.py`) como con el de producción (`python serve.py`): los 40 módulos responden
**200**, las operaciones registradas por formulario actualizan los saldos del Libro Mayor, la
ecuación patrimonial se mantiene con diferencia **0.00** y una evaluación enviada al simulador
obtuvo **100/100 (CORRECTO)** con su rúbrica y retroalimentación específica.

El despliegue publicado se comprueba de una sola vez con
`python deploy/verificar_despliegue.py --url <dirección>` (módulos, API, manual, archivos internos
no expuestos e integridad contable).

## 16. Datos de demostración

`database/seed_data.py` construye una base reproducible con:

* Empresa **Comercial y Servicios Nueva Esperanza S.A.** (RUC 1792345678001) con dos actividades:
  comercialización de productos de primera necesidad y prestación de servicios.
* **43 cuentas** contables jerárquicas (6 grupos: Activo, Pasivo, Patrimonio, Ingresos, Costos, Gastos).
* **20 productos** de primera necesidad (alimentos, bebidas, limpieza, higiene) con stock, mínimos,
  máximos y proveedor principal; inventario inicial valorizado con lotes de Kardex.
* **10 clientes**, **8 proveedores**, **5 servicios configurables**, caja y **2 cuentas bancarias**.
* **6 parámetros tributarios** configurables (IVA 15 % ventas/compras y 4 retenciones).
* Asiento de apertura con saldos iniciales reales (activo, pasivo, patrimonio) y cartera inicial.
* **30 operaciones del período Abril 2026** ejecutadas por los servicios reales del sistema:
  compras de contado y a crédito, ventas de contado, por transferencia y a crédito, servicios
  facturados, cobros de cartera, pagos a proveedores, gastos operacionales, depósito bancario,
  arqueo de caja con faltante, notas bancarias de débito y crédito, depreciación, provisión de
  incobrables y compensación del IVA del período.
* **19 casos de simulación** en los cuatro niveles, con pistas progresivas y explicación pedagógica
  generadas a partir de los asientos reales.
* **Documentos fuente** de todos los tipos: facturas de venta y compra, facturas de servicio,
  comprobantes de ingreso y egreso, papeletas de depósito, notas bancarias de débito y crédito,
  acta de arqueo, rol de pagos y comprobantes de ajuste.

**Todos los datos son de DEMOSTRACIÓN y tienen fines exclusivamente académicos.** Las tasas
tributarias son configurables y no constituyen una afirmación sobre la normativa vigente.

## 17. Verificación de integridad (resultado real del sembrado)

```
Período: Período Académico Abril 2026
Fecha de trabajo: 2026-04-30
Operaciones integradas ejecutadas: 30
Casos de simulación creados: 19
Asientos contabilizados: 37
Total débitos : 92,778.50   Total créditos: 92,778.50   Cuadra sumas: True
Saldo deudor : 74,724.21   Saldo acreedor: 74,724.21   Cuadra saldos: True
Activo: 63,541.05  =  Pasivo + Patrimonio: 63,541.05   Balanceado: True (diferencia 0.0)
Utilidad neta del período: 750.67
```

Composición de la base demostrativa entregada: 43 cuentas, 20 productos, 10 clientes, 8 proveedores,
5 servicios, 6 impuestos configurables, 1 caja, 2 bancos, 6 ventas, 5 compras, 3 servicios
facturados, 19 documentos por cobrar/pagar entre saldos iniciales y operaciones, 24 movimientos de
tesorería, 49 movimientos de inventario, 33 lotes de Kardex, **37 asientos contabilizados**,
**31 documentos fuente**, 4 simulaciones y **19 casos** con solución verificada, 88 registros de
auditoría. **Asientos descuadrados: 0**.

## 18. Mejoras futuras

* Integración con un modelo de lenguaje real para el Tutor IA (el orquestador ya expone la interfaz).
* Exportación a PDF directa en servidor (hoy se resuelve con la versión imprimible del navegador).
* Autenticación de dos factores y bitácora firmada para el rol Auditor.
* Conciliación bancaria automática importando extractos CSV del banco.
* Motor de retenciones por proveedor y generación de comprobantes de retención.
* Modo multiusuario concurrente con PostgreSQL para grupos grandes.
* Editor visual de casos para el docente (hoy se generan por script y por el agente generador).
