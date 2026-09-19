# Manual de Usuario
## Simulador Integral de Sistema Contable
### Servicios y Comercialización de Productos — *Comercial y Servicios Nueva Esperanza S.A.*

> Versión del manual: **2.0** · Asignatura: **Contabilidad I (UTM)**
> Período de demostración: **Abril 2026** · Fecha de trabajo por defecto: **2026-04-30**
> Documento generado para uso académico. Todos los datos son de **demostración**.
>
> Esta versión documenta **los 44 módulos que existen hoy** en el sistema: **142 rutas** (107 de
> interfaz + 35 de API), **49 tablas**, **37 herramientas** de los agentes de IA y la suite completa
> de **pruebas automáticas**. Incluye además **guías paso a paso para el
> estudiante y para el docente**, con las pantallas descritas en texto (ver [sección 5](#5-cómo-leer-este-manual-y-sus-capturas-descritas)).
> Los conteos se verifican con los comandos de la [sección 21.E](#e-verificación-rápida-del-sistema).

---

## Índice

1. [¿Qué es este sistema?](#1-qué-es-este-sistema)
2. [Requisitos e instalación](#2-requisitos-e-instalación)
3. [Cómo ejecutar, detener y verificar el sistema](#3-cómo-ejecutar-detener-y-verificar-el-sistema)
4. [Usuarios, contraseñas y roles](#4-usuarios-contraseñas-y-roles)
5. [Cómo leer este manual y sus capturas descritas](#5-cómo-leer-este-manual-y-sus-capturas-descritas)
6. [Guía paso a paso del estudiante](#6-guía-paso-a-paso-del-estudiante)
7. [Guía paso a paso del docente](#7-guía-paso-a-paso-del-docente)
8. [Recorrido guiado de 15 minutos](#8-recorrido-guiado-de-15-minutos)
9. [Mapa de navegación](#9-mapa-de-navegación)
10. [Módulos del sistema](#10-módulos-del-sistema)
    1. [Dashboard](#101-dashboard)
    2. [Plan de Cuentas](#102-plan-de-cuentas)
    3. [Libro Diario](#103-libro-diario)
    4. [Libro Mayor](#104-libro-mayor)
    5. [Balance de Comprobación](#105-balance-de-comprobación)
    6. [Ajustes Contables](#106-ajustes-contables)
    7. [Cierre de Período](#107-cierre-de-período)
    8. [Ventas de Bienes](#108-ventas-de-bienes)
    9. [Servicios Prestados](#109-servicios-prestados)
    10. [Compras a Proveedores](#1010-compras-a-proveedores)
    11. [Catálogo de Productos](#1011-catálogo-de-productos)
    12. [Kardex](#1012-kardex)
    13. [Existencias y Alertas](#1013-existencias-y-alertas)
    14. [Caja y Arqueos](#1014-caja-y-arqueos)
    15. [Cuentas Bancarias](#1015-cuentas-bancarias)
    16. [Conciliación Bancaria](#1016-conciliación-bancaria)
    17. [Clientes](#1017-clientes)
    18. [Cuentas por Cobrar](#1018-cuentas-por-cobrar)
    19. [Proveedores](#1019-proveedores)
    20. [Cuentas por Pagar](#1020-cuentas-por-pagar)
    21. [Documentos Fuente](#1021-documentos-fuente)
    22. [Documentos del SRI: catálogo normativo](#1022-documentos-del-sri-catálogo-normativo)
    23. [Documentos del SRI: emitir un comprobante](#1023-documentos-del-sri-emitir-un-comprobante)
    24. [Documentos del SRI: ¿qué documento necesito?](#1024-documentos-del-sri-qué-documento-necesito)
    25. [Tributación: IVA y retenciones](#1025-tributación-iva-y-retenciones)
    26. [Estado de Resultados](#1026-estado-de-resultados)
    27. [Estado de Situación Financiera](#1027-estado-de-situación-financiera)
    28. [Estado de Flujo de Efectivo](#1028-estado-de-flujo-de-efectivo)
    29. [Simulador de Casos](#1029-simulador-de-casos)
    30. [Mis Evaluaciones](#1030-mis-evaluaciones)
    31. [Mis Actividades (syllabus)](#1031-mis-actividades-syllabus)
    32. [Mis Evidencias](#1032-mis-evidencias)
    33. [Actividades del Syllabus (docente)](#1033-actividades-del-syllabus-docente)
    34. [Evidencias de Estudiantes (docente)](#1034-evidencias-de-estudiantes-docente)
    35. [Verificar Código de Evidencia (docente)](#1035-verificar-código-de-evidencia-docente)
    36. [Seguimiento de Accesos (docente)](#1036-seguimiento-de-accesos-docente)
    37. [Mis Estudiantes: ficha y libros en solo lectura](#1037-mis-estudiantes-ficha-y-libros-en-solo-lectura)
    38. [Estudiantes sin ingresar](#1038-estudiantes-sin-ingresar)
    39. [Panel de Analítica Docente](#1039-panel-de-analítica-docente)
    40. [Tutor Contable IA](#1040-tutor-contable-ia)
    41. [Centro de Reportes](#1041-centro-de-reportes)
    42. [Administración del Sistema](#1042-administración-del-sistema)
    43. [Casos de los libros (§61)](#1043-casos-de-los-libros-61)
    44. [Banco de casos y trazabilidad (docente)](#1044-banco-de-casos-y-trazabilidad-docente)
11. [Un aula por estudiante: el aislamiento de los datos](#11-un-aula-por-estudiante-el-aislamiento-de-los-datos)
12. [Reglas contables y validaciones](#12-reglas-contables-y-validaciones)
13. [Fecha de trabajo y períodos](#13-fecha-de-trabajo-y-períodos)
14. [Modo Examen y evaluación](#14-modo-examen-y-evaluación)
15. [Agentes de IA y API interna](#15-agentes-de-ia-y-api-interna)
16. [Datos de demostración](#16-datos-de-demostración)
17. [Solución de problemas](#17-solución-de-problemas)
18. [Preguntas frecuentes](#18-preguntas-frecuentes)
19. [Buenas prácticas](#19-buenas-prácticas)
20. [Glosario](#20-glosario)
21. [Anexos](#21-anexos)

---

## 1. ¿Qué es este sistema?

Es un **sistema contable educativo completo (tipo ERP académico)** que funciona en el navegador y
opera sobre una empresa simulada real: **Comercial y Servicios Nueva Esperanza S.A.**, dedicada a
dos actividades:

* **Comercial:** venta de productos de primera necesidad (arroz, azúcar, aceite, leche, harina,
  café, limpieza, higiene, bebidas y alimentos empacados).
* **Servicios:** entrega/distribución, transporte, asesoría, mantenimiento e instalación.

El sistema tiene **dos caras que trabajan juntas**:

| Cara | Para quién | Qué resuelve |
|---|---|---|
| **Sistema contable** | Todos los roles | Registrar documentos, comprar, vender, cobrar, pagar, mayorizar, ajustar, cerrar y emitir estados financieros |
| **Plataforma del curso** | Estudiante y docente | Actividades del syllabus, evidencias verificables con huella SHA-256, seguimiento de accesos, libros de cada estudiante en solo lectura y analítica del avance |

**No es una página informativa ni un conjunto de ejercicios aislados.** Cada operación que registras
se propaga automáticamente a todo el sistema:

```
Documento fuente → Transacción → Asiento → Libro Diario → Libro Mayor → Balance → Estados financieros
```

y, cuando corresponde:

```
Compra → Inventario (Kardex) → Venta → Costo de ventas → Resultado del período
```

Una venta, por ejemplo, actualiza de forma simultánea: el registro de venta, el inventario y su
Kardex, el costo de ventas, la cartera del cliente, la caja o el banco, el IVA y sus retenciones,
los documentos fuente, el Libro Diario, el Libro Mayor, el Balance de Comprobación y los estados
financieros. Al mismo tiempo, el sistema anota el evento en la **línea de tiempo** del estudiante,
de modo que el docente puede reconstruir *qué hizo, cuándo y con qué resultado*.

**¿Para quién es?** Estudiantes de Contabilidad, Auditoría, Administración, Finanzas y áreas
empresariales afines, y docentes que quieran asignar actividades, evaluar automáticamente, recibir
evidencias verificables y ver analítica del avance del curso.

### Las tres piezas del entorno académico

```
base de CONTROL (compartida)          aula del estudiante (1 archivo por estudiante)
├── usuarios, roles, cursos           ├── su empresa, su plan de cuentas
├── actividades del syllabus          ├── sus asientos, diario, mayor, balance
├── asignaciones_actividad            ├── su inventario, cartera y tesorería
├── sesiones_usuario, eventos         ├── sus documentos y estados financieros
├── evidencias + versiones            └── sus períodos, impuestos y simulaciones
└── auditoría
```

El detalle está en [sección 11](#11-un-aula-por-estudiante-el-aislamiento-de-los-datos).

---

## 2. Requisitos e instalación

**Requisitos**

* Windows, macOS o Linux
* Python 3.11 o superior
* Navegador moderno (Chrome, Edge, Firefox)
* Opcional: conexión a Internet solo para los recursos visuales (Bootstrap, Chart.js desde CDN);
  el sistema funciona igual sin conexión, con estilos base.

**Instalación (una sola vez)**

```bash
cd "C:\Users\1161150\Desktop\Pagina web"
python -m venv .venv                     # crear entorno virtual (opcional pero recomendado)
.venv\Scripts\activate                   # en Windows (en Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

Contenido de `requirements.txt`: Flask, Werkzeug, Jinja2, waitress (servidor de producción),
openpyxl (exportación a Excel), markdown (generación de este manual) y pytest (pruebas automáticas).
**reportlab es opcional:** si está instalado, las evidencias se descargan en PDF; si no, se ofrece la
vista imprimible en HTML para *Imprimir → Guardar como PDF*.

---

## 3. Cómo ejecutar, detener y verificar el sistema

**Ejecutar**

```bash
.venv\Scripts\python.exe app.py
```

La aplicación queda disponible en: **http://127.0.0.1:5000**

Al arrancar verás en la consola:

```
 SIMULADOR INTEGRAL DE SISTEMA CONTABLE
 Servicios y Comercialización de Productos - Comercial Nueva Esperanza
 Servidor Flask disponible en: http://127.0.0.1:5000
 Usuarios demo: admin/admin123 - docente/docente123 - estudiante/estudiante123
```

**Detener:** `Ctrl + C` en la consola donde corre el servidor.

### Servicio continuo (24/7) y uso en red

Para dejar el sistema publicado de forma permanente se usa el servidor de producción incluido
(`waitress`), no el servidor de desarrollo:

```bash
python serve.py                                  # http://127.0.0.1:5000
HOST=0.0.0.0 PORT=8080 python serve.py           # accesible desde la red
```

* Si la base de datos no existe, `serve.py` la genera automáticamente en el primer arranque.
* **Este manual** está siempre disponible en **`/manual`** (y su fuente Markdown en `/manual/fuente`).
* En Windows, para que arranque solo y se reinicie si falla:

  ```powershell
  powershell -ExecutionPolicy Bypass -File deploy\windows\instalar_arranque_automatico.ps1 -Puerto 8080
  ```

* Para publicarlo en Internet (VPS con dominio y HTTPS, o plataforma gestionada) siga la guía
  `docs/DESPLIEGUE.md`, que incluye la **lista de verificación de seguridad** — entre otros puntos,
  cambiar las contraseñas de demostración con `python deploy/cambiar_credenciales.py`.
* **Hostinger VPS** (Ubuntu 22.04/24.04): el instalador automático configura servidor, Nginx,
  HTTPS, servicio systemd y respaldos en un solo comando:

  ```bash
  sudo bash deploy/hostinger/instalar_vps.sh --dominio contabilidad.midominio.com --correo docente@utm.edu.ec
  ```

  (Recuerde: en Hostinger solo los planes **VPS** pueden ejecutar una aplicación Flask; los planes
  de Web/Cloud hosting no lo permiten.)

### Verificación obligatoria después de cualquier cambio o despliegue

```bash
python -m pytest tests -q                                       # suite completa de pruebas automáticas
python database/seed_data.py                                    # regenerar los datos de demostración
python deploy/verificar_despliegue.py --url http://127.0.0.1:8080   # módulos, API, manual y seguridad
curl http://127.0.0.1:5000/api/health                           # estado del sistema
```

`deploy/verificar_despliegue.py` comprueba que los módulos respondan, que la API esté viva, que el
manual se sirva, que `database/`, `docs/` y `deploy/` **no** queden expuestos y que se cumpla la
ecuación `Activo = Pasivo + Patrimonio`. Un despliegue no está listo hasta que eso pase.

> La **fecha de trabajo** de la simulación no depende del reloj de tu computador: la controla el
> sistema desde el panel de Administración (ver [sección 13](#13-fecha-de-trabajo-y-períodos)).

---

## 4. Usuarios, contraseñas y roles

**Cuentas de demostración** (para mostrar el sistema en clase):

| Rol | Usuario | Contraseña | Nombre en el sistema |
|---|---|---|---|
| Administrador | `admin` | `admin123` | Ing. Marco Morales |
| Docente | `docente` | `docente123` | Ing. Angélica Victoria Guillén Pinargote, Mg. |
| Estudiante | `estudiante` | `estudiante123` | Ana Lucía Morales |
| Auditor | `auditor` | `auditor123` | Lic. Roberto Vaca |

**Estudiantes del curso:** cada estudiante tiene **su propio usuario** (por ejemplo `ealcivar4002`,
`javiles8757`), su **aula contable** (una base de datos propia) y una **contraseña inicial aleatoria**
que la docente entrega por el aula virtual; la contraseña inicial nunca es la cédula. El usuario del
estudiante se construye con la parte local de su correo institucional.

El ingreso acepta **usuario o correo electrónico** en el mismo campo. Las contraseñas se almacenan
**con hash seguro** (nunca en texto plano).

> **Antes de publicar el sistema en Internet:** cambie las contraseñas de demostración
> (`python deploy/cambiar_credenciales.py`) y defina una `SECRET_KEY` propia. Las cuentas
> `admin/admin123`, `docente/docente123`, etc. son públicas y solo sirven para la práctica.

### Matriz de permisos

| Módulo | Administrador | Docente | Estudiante | Auditor |
|---|:--:|:--:|:--:|:--:|
| Dashboard, libros, balance, estados financieros | ✅ | ✅ | ✅ | ✅ (solo lectura) |
| Documentos fuente, documentos del SRI, trazabilidad | ✅ | ✅ | ✅ | ✅ (solo lectura) |
| Registrar ventas, servicios, compras, cobros, pagos, tesorería, ajustes | ✅ | ✅ | ✅ | — |
| Simulador de casos y Mis Evaluaciones | ✅ | ✅ | ✅ | — |
| **Mis Actividades** y **Mis Evidencias** (syllabus) | ✅ | ✅ | ✅ | — |
| **Actividades del Syllabus** (crear, asignar, abrir/cerrar) | ✅ | ✅ | — | — |
| **Evidencias de Estudiantes** y **Verificar Código** | ✅ | ✅ | — | — |
| **Seguimiento de Accesos** y **Mis Estudiantes** (incluye libros ajenos) | ✅ | ✅ | — | — |
| Panel de Analítica Docente | ✅ | ✅ | — | — |
| Cierre contable | ✅ | ✅ | — | — |
| Administración: usuarios, parámetros, impuestos, auditoría | ✅ | — | — | Solo auditoría (lectura) |

Si un usuario intenta entrar a un módulo sin permiso, recibe la página **403 – Acceso restringido**
con el mensaje del rol requerido y la lista de roles autorizados. Si intenta abrir una evidencia o
una actividad **de otro compañero**, recibe **404/403**: el aislamiento no depende de que escriba
bien la URL (ver [sección 11](#11-un-aula-por-estudiante-el-aislamiento-de-los-datos)).

---

## 5. Cómo leer este manual y sus capturas descritas

Este documento no incluye imágenes: **cada pantalla se describe en texto**, con los rótulos,
columnas y botones **reales** del sistema, de modo que el manual se pueda leer en voz alta, imprimir
en blanco y negro o consultar desde un lector de pantalla.

La convención es siempre la misma:

```
📷 CAPTURA n · "Título que aparece en la pestaña"
Rol: Estudiante | Docente | Administrador      Ruta: /ruta/en/el/navegador
+----------------------------------------------------------------------+
|  <dibujo en texto de la pantalla: encabezado, filtros, columnas,      |
|   botones y datos de ejemplo>                                        |
+----------------------------------------------------------------------+
Qué mirar:   los datos que conviene revisar primero.
Qué hacer:   la acción concreta que se espera del usuario.
```

* Las **cajas** representan la distribución de la pantalla: primero el encabezado, luego la barra de
  filtros o el formulario, después la tabla o los indicadores y al final los botones.
* Los textos entre comillas son **literales del sistema** (rótulos, mensajes de error, títulos).
* Los montos son de ejemplo; los reales siempre salen de los libros del período.

Las dos guías de las secciones [6](#6-guía-paso-a-paso-del-estudiante) y
[7](#7-guía-paso-a-paso-del-docente) están pensadas para seguirse **de principio a fin el primer día
de clases**; en las secciones siguientes cada módulo se documenta por separado para consulta puntual.

---

## 6. Guía paso a paso del estudiante

Sigue estos doce pasos **en orden** la primera vez. Al final tendrás tu empresa con operaciones
registradas, tus libros cuadrados y **una evidencia verificable** con código y huella.

### Paso 1. Entrar al sistema

1. Abre el navegador en la dirección que te dio tu docente (en tu computador:
   `http://127.0.0.1:5000`; en el servidor del curso, el dominio que te indiquen).
2. Escribe tu **usuario** (por ejemplo `ealcivar4002`) o tu **correo** y tu **contraseña inicial**.
3. Pulsa **Iniciar Sesión**.

```
📷 CAPTURA 1 · "Iniciar Sesión"
Rol: cualquiera            Ruta: /login
+------------------------------------------------------------------------+
|  SIMULADOR INTEGRAL DE SISTEMA CONTABLE                                |
|  Servicios y Comercialización de Productos                             |
|                                                                        |
|   Usuario o correo   [ ealcivar4002                        ]           |
|   Contraseña         [ ************************            ]           |
|                                                                        |
|                        [    Iniciar Sesión    ]                        |
|                                                                        |
|  Período: Período Académico Abril 2026 · Fecha de trabajo: 2026-04-30  |
+------------------------------------------------------------------------+
Qué mirar:  el mensaje verde "¡Bienvenido(a) al Simulador Contable, <tu nombre>!"
Qué hacer:  si aparece en rojo "Credenciales incorrectas o usuario inactivo",
            revisa el usuario y la contraseña que entregó tu docente.
```

> Si no puedes entrar, **no pidas la contraseña a un compañero**: solicita al docente que restablezca
> tu cuenta. Cada estudiante tiene su propio usuario y su propia empresa.

### Paso 2. Reconocer el Dashboard

Al entrar llegas al **Dashboard General**: tu tablero de control. Revisa los indicadores y, sobre
todo, la zona de **alertas**.

```
📷 CAPTURA 2 · "Dashboard"
Rol: Estudiante            Ruta: /dashboard
+------------------------------------------------------------------------+
|  Menú lateral   |  Dashboard General          Período Abril 2026        |
|  - Dashboard    |  [ Caja ][ Bancos ][ Ventas ][ Servicios ][ CxC ]      |
|  - Contabilidad |  [ Inventario ][ CxP ][ Utilidad del período ]        |
|  - Operaciones  |  --------------------------------------------------- |
|  - Inventario   |  Gráficos: evolución semanal / barras o líneas        |
|  - Tesorería    |  Alertas: stock bajo · cartera vencida · CxP ·         |
|                 |           asientos descuadrados                      |
|  - Informes     |  Actividad reciente: últimos asientos y documentos    |
|  - Entorno Uni. |  Resultados de simulación: intentos y promedio        |
+------------------------------------------------------------------------+
Qué mirar:  el indicador "asientos descuadrados" debe estar en 0.
Qué hacer:  si hay alerta de stock bajo, registra primero una compra.
```

### Paso 3. Ver tus actividades del syllabus

En el menú lateral, sección **Entorno Universitario & IA → Mis Actividades**. Aquí aparecen las
actividades que tu docente te asignó con su puntaje, disponibilidad y estado.

```
📷 CAPTURA 3 · "Mis Actividades del Syllabus"
Rol: Estudiante            Ruta: /mis-actividades
+------------------------------------------------------------------------+
|  Mis Actividades del Syllabus            [ Ir a Mis Evidencias ] [JSON] |
|  Resumen: Total 6 · Pendientes 6 · En curso 0 · Entregadas 0            |
|  Puntaje total acumulado: 0.00                                         |
|  --------------------------------------------------------------------  |
|  Código   Actividad                        U  Componente Puntaje Estado|
|  U1-A1    Taller asistido: objeto, objeti  1  Docencia   10   Pendiente|
|  U2-A2    Práctica de laboratorio: clasif  2  Práctica   12   Pendiente|
|  U2-A3    Fichero autónomo de cuentas...   2  Autónomo   10   Pendiente|
|  U3-A4    Jornalización integral...        3  Docencia   10   Pendiente|
|  U3-A5    Portafolio autónomo de jornal... 3  Autónomo   10   Pendiente|
|  U4-A6    Trabajo autónomo integrador...   4  Autónomo   10   Pendiente|
|  Disponibilidad: "Disponible ahora" o "No disponible" (con el motivo)   |
|  Acciones: [ Ver detalle ]  [ Iniciar ]                                |
+------------------------------------------------------------------------+
Qué mirar:  la columna Disponibilidad — una actividad "No disponible" está
            fuera de su ventana de fechas (el motivo aparece al pasar el cursor).
Qué hacer:  abre la actividad y pulsa Iniciar para que el sistema marque el
            inicio: ese instante queda en tu línea de tiempo.
```

### Paso 4. Abrir la actividad y empezar a trabajar

El detalle de la actividad es tu hoja de ruta: instrucciones, evidencia solicitada, **tus eventos**
y las evidencias ya generadas para esa actividad.

```
📷 CAPTURA 4 · "U2-A2 - Práctica de laboratorio..."
Rol: Estudiante            Ruta: /mis-actividades/2
+------------------------------------------------------------------------+
|  [U2-A2]  Práctica de laboratorio: clasificación, naturaleza y          |
|           dinámica de las cuentas contables          [Disponible ahora] |
|  Instrucciones                                                         |
|    Componente PRACTICA · Puntaje: 12 puntos                            |
|    Fecha límite de entrega: ...                                        |
|    PROPÓSITO DE LA ACTIVIDAD: ...                                      |
|    CONTENIDOS DE LA UNIDAD: ...                                        |
|    CRITERIOS DE EVALUACIÓN: ...                                        |
|    USO DEL SIMULADOR: ...                                              |
|  Evidencia solicitada por el docente: PLAN_CUENTAS                     |
|  [ Iniciar actividad ]  [ Ver mis evidencias ]                         |
|  Eventos de esta actividad                                             |
|    Evento               Módulo      Detalle               Fecha y hora  |
|    INICIO_ACTIVIDAD     ACTIVIDADES Actividad iniciada    2026-04-30... |
|  Evidencias de esta actividad                                          |
|    Código                     Título              Estado    [Ver]       |
+------------------------------------------------------------------------+
Qué mirar:  la "Evidencia solicitada" te dice qué debes generar al terminar.
Qué hacer:  trabaja en los módulos contables (pasos 5 a 9) y vuelve aquí para
            registrar tu evidencia (paso 11).
```

### Paso 5. Tu plan de cuentas

**Contabilidad Central → Plan de Cuentas** (`/contabilidad/cuentas`). Muestra las **46 cuentas** con
código, nombre, **naturaleza** (deudora/acreedora), clasificación, cuenta padre, nivel, si acepta
movimiento y su **saldo actual calculado desde el libro mayor**.

* Para **agregar una cuenta**: formulario *Nueva cuenta* (código, nombre, naturaleza, clasificación,
  cuenta padre, acepta movimiento).
* Para **editar**: botón por fila (*Editar*); el cambio queda en la auditoría.

```
📷 CAPTURA 5 · "Plan de Cuentas"
Rol: Estudiante            Ruta: /contabilidad/cuentas
+------------------------------------------------------------------------+
|  Plan de Cuentas                                       [ Nueva cuenta ] |
|  Código   Nombre                          Naturaleza  Clasificación     |
|  1        ACTIVO                          DEUDORA     ACTIVO_CORRIENTE  |
|  1.1.01   Caja General                    DEUDORA     ACTIVO_CORRIENTE  |
|  1.1.02   Banco Pichincha                 DEUDORA     ACTIVO_CORRIENTE  |
|  1.1.06   Inventario de Mercaderías       DEUDORA     ACTIVO_CORRIENTE  |
|  2.1.01   Cuentas por Pagar               ACREEDORA   PASIVO_CORRIENTE  |
|  4.1.01   Ingresos por ventas de bienes   ACREEDORA   INGRESOS_OPER...  |
|  Saldo actual por cuenta, calculado con los movimientos del período     |
+------------------------------------------------------------------------+
Qué mirar:  que la cuenta donde vas a registrar ACEPTE MOVIMIENTO.
Qué hacer:  no borres cuentas: si te equivocas, usa una cuenta de ajuste.
```

### Paso 6. Registrar el asiento en el Libro Diario

**Contabilidad Central → Libro Diario** (`/contabilidad/diario`). Cada asiento tiene fecha, concepto,
documento de referencia y líneas en Debe y Haber.

1. Completa fecha, concepto y el **documento fuente** que respalda la operación.
2. Añade líneas: cuenta, Debe o Haber, importe. Puedes agregar o quitar líneas.
3. Pulsa **Guardar asiento**.
4. Si te equivocaste en un asiento ya contabilizado, usa **Revertir** (crea el contra-asiento) — los
   asientos **no se borran**.

```
📷 CAPTURA 6 · "Libro Diario"
Rol: Estudiante            Ruta: /contabilidad/diario
+------------------------------------------------------------------------+
|  Libro Diario                                                          |
|  Nuevo asiento:  Fecha [2026-04-30]  Concepto [Venta de mercaderías]    |
|  Documento [FACTURA_VENTA No. 001-001-000000123]                        |
|  Cuenta                     Debe        Haber                          |
|  [1.1.01 Caja General   ]   1130.00                                    |
|  [4.1.01 Ingresos ventas]                1000.00                       |
|  [2.1.02 IVA por pagar  ]                 130.00                       |
|  [ + Agregar línea ]        Total Debe 1130.00  Total Haber 1130.00    |
|  [ Guardar asiento ]                                                   |
|  Últimos asientos:  #  Fecha  Concepto  Documento  Debe  Haber [Revertir]|
+------------------------------------------------------------------------+
Qué mirar:  que los totales de Debe y Haber coincidan antes de guardar.
Qué hacer:  si aparece "El asiento no cuadra…", revisa la diferencia que
            indica el mensaje: la línea con el error está señalada.
```

### Paso 7. Mayorizar y revisar el Libro Mayor

**Contabilidad Central → Libro Mayor** (`/contabilidad/mayor`): los movimientos de cada cuenta con
su saldo acumulado. Aquí compruebas que un asiento llegó a la cuenta correcta.

```
📷 CAPTURA 7 · "Libro Mayor"
Rol: Estudiante            Ruta: /contabilidad/mayor
+------------------------------------------------------------------------+
|  Libro Mayor        Filtro de cuenta [ Todas / 1.1.01 Caja General ]    |
|  Cuenta 1.1.01 Caja General                     Saldo: $1.130,00        |
|  Fecha       Concepto              Debe      Haber     Saldo            |
|  2026-04-02  Aporte inicial      5000.00              5000.00           |
|  2026-04-30  Venta de mercaderías 1130.00              6130.00          |
+------------------------------------------------------------------------+
Qué mirar:  que el saldo acumulado tenga sentido con la naturaleza de la
            cuenta (la caja no puede quedar negativa por un error de lado).
```

### Paso 8. Comprobar el Balance de Comprobación

**Contabilidad Central → Balance de Comprobación** (`/contabilidad/balance`): la prueba de que el
mayor está cuadrado (sumas y saldos).

```
📷 CAPTURA 8 · "Balance de Comprobación"
Rol: Estudiante            Ruta: /contabilidad/balance
+------------------------------------------------------------------------+
|  Balance de Comprobación de Sumas y Saldos     [ Imprimir ] [ Excel ]   |
|  Código  Cuenta              Sumas Debe  Sumas Haber  Saldo Deudor ...  |
|  1.1.01  Caja General         6130.00                 6130.00           |
|  2.1.01  Cuentas por Pagar                 2400.00            2400.00    |
|  TOTALES                    92778.50     92778.50     74724.21  74724.21 |
|  ✔ Total Debe = Total Haber  ✔ Saldo deudor = Saldo acreedor            |
+------------------------------------------------------------------------+
Qué mirar:  las dos comparaciones finales deben coincidir exactamente.
Qué hacer:  si no cuadran, abre Ajustes Contables y busca el asiento
            descuadrado (el Dashboard también lo señala).
```

### Paso 9. Leer los estados financieros

**Informes Financieros NIIF** agrupa el **Estado de Resultados**, el **Estado de Situación
Financiera** y el **Estado de Flujo de Efectivo**. El de Situación Financiera trae el control de la
ecuación fundamental en un banner.

```
📷 CAPTURA 9 · "Estado de Situación Financiera"
Rol: Estudiante            Ruta: /estados-financieros/situacion-financiera
+------------------------------------------------------------------------+
|  Estado de Situación Financiera                                        |
|  ✔ Activo = Pasivo + Patrimonio   (diferencia $0,00)                    |
|  ACTIVO                        |  PASIVO + PATRIMONIO                    |
|  Corriente        12.345,67    |  Corriente          8.900,00           |
|  No corriente     10.000,00    |  No corriente      12.000,00           |
|  Depreciación     -2.500,00    |  Patrimonio        14.345,67           |
|  TOTAL ACTIVO     19.845,67    |  TOTAL P+P         19.845,67           |
|  Indicadores: razón corriente · capital de trabajo · endeudamiento      |
+------------------------------------------------------------------------+
Qué mirar:  el banner verde. Si está rojo, muestra la diferencia detectada.
```

### Paso 10. Emitir un comprobante del SRI

**Tesorería & Cartera → Documentos Fuente** abre el módulo de documentos. Ahí tienes tres vistas:
el **listado**, el **catálogo normativo** (`/documentos/catalogo`) y la **ayuda "¿Qué documento
necesito?"** (`/documentos/soporte`). Para emitir un comprobante se usa
**`/documentos/nuevo` → Emitir comprobante**.

```
📷 CAPTURA 10 · "Emitir comprobante" (Documentos del SRI)
Rol: Estudiante            Ruta: /documentos/nuevo
+------------------------------------------------------------------------+
|  Emitir comprobante       Tipo de documento [ FACTURA ▾ ]              |
|  Emisor [Comercial y Servicios Nueva Esperanza S.A.]                   |
|  RUC emisor [1792345678001]  Establecimiento [001]  Punto emisión [001] |
|  Tipo de emisión [NORMAL]     Fecha [2026-04-30]                       |
|  Adquirente: tipo [RUC] identificación [ ... ] razón social [ ... ]     |
|  Detalle: concepto | cantidad | precio | % IVA | subtotal              |
|  Forma de pago [EFECTIVO ▾]   Leyenda: DOCUMENTO PARA USO EDUCATIVO    |
|                            (SIN VALIDEZ COMERCIAL)                     |
|  [ Emitir comprobante ]   [ Limpiar formulario ]                       |
|  Validación: los puntos en rojo explican qué exige el reglamento       |
+------------------------------------------------------------------------+
Qué mirar:  la leyenda educativa y las validaciones (regla, severidad,
            "qué exige el reglamento") antes de emitir.
Qué hacer:  si el comprobante no se emite, el sistema explica el motivo;
            corrígelo y vuelve a intentar. El documento emitido queda en el
            listado de Documentos Fuente con su número completo.
```

### Paso 11. Generar tu evidencia verificable

**Entorno Universitario & IA → Mis Evidencias** (`/mis-evidencias`). Una evidencia es un **informe
con las cifras reales de tu empresa** (plan de cuentas, diario, mayor, balance o integral) más un
**código** y una **huella SHA-256** que permite al docente comprobar que no se alteró después.

1. Elige la **Actividad del syllabus** y el **tipo de evidencia** que pidió el docente.
2. Deja el título en blanco para que el sistema lo proponga, o escribe el tuyo.
3. Pulsa **Generar evidencia**. Si marcas *"Finalizar de inmediato y firmar con la huella SHA-256"*,
   la evidencia queda **FINAL** en el mismo paso.
4. En el detalle puedes **Finalizar evidencia**, **Registrar nueva versión** (con el motivo de la
   corrección) y abrir **Preparar captura** o **Imprimible / PDF**.

```
📷 CAPTURA 11 · "Mis Evidencias Verificables"
Rol: Estudiante            Ruta: /mis-evidencias
+------------------------------------------------------------------------+
|  Mis Evidencias Verificables        [ Mis Actividades ]        [ JSON ] |
|  Resumen: Total 1 · Finales 1 · Borradores 0 · Modificadas 0            |
|  Nueva evidencia                                                       |
|   Actividad del syllabus [ U2-A2 ▾ ]  Contenido [ PLAN_CUENTAS ▾ ]      |
|   Título (opcional) [                                   ]               |
|   [x] Finalizar de inmediato y firmar con la huella SHA-256             |
|   [ Generar evidencia ]                                                |
|  --------------------------------------------------------------------  |
|  Código                Título              Tipo    Estado  Integridad   |
|  CONT1-B-2026-4F7A9C21 Evidencia del plan  PLAN_.. FINAL   Sin cambios  |
|  Acciones: [ Ver ] [ Preparar captura ] [ Finalizar ]                  |
+------------------------------------------------------------------------+
Qué mirar:  la columna "Integridad": si dice "Modificada después", tu
            evidencia perdió la firma y el docente lo verá.
Qué hacer:  copia tu código CONT1-B-2026-________ y entrégalo en Moodle
            junto con el archivo o la captura.
```

> **El código es tu comprobante.** El docente puede verificar
> `CONT1-B-2026-XXXXXXXX` en **Verificar Código** y ver si el contenido cambió
> después de finalizar. No lo inventes ni lo compartas: es único por evidencia.

### Paso 12. Practicar con el simulador y cerrar sesión

* **Entorno Universitario & IA → Simulador de Casos**: elige un caso, pulsa *Iniciar*, arma las
  líneas (cuenta, Debe, Haber) y pulsa *Enviar Asiento y Evaluar*. Recibes puntuación sobre 100 y
  retroalimentación línea por línea. Si te trabas, **Pedir pista al Tutor IA** (resta 5 puntos).
* **Mis Evaluaciones**: tu historial de intentos, puntuaciones, tiempo y promedio.
* **Tutor Contable IA**: preguntas de razonamiento contable con cuatro niveles de ayuda
  (orientación, pista, explicación conceptual y solución guiada).
* Al terminar, cierra sesión desde el menú del usuario (**Cerrar Sesión**). El sistema guarda la
  duración de la sesión y anota tu último acceso: esos datos alimentan el seguimiento del docente.

### Resumen del recorrido del estudiante

| # | Pantalla | Ruta | Qué produce |
|---|---|---|---|
| 1 | Iniciar sesión | `/login` | Sesión registrada + evento `LOGIN` |
| 2 | Dashboard | `/dashboard` | Alertas y estado del período |
| 3 | Mis Actividades | `/mis-actividades` | Estado de las 6 actividades |
| 4 | Detalle de actividad | `/mis-actividades/<id>` | Evento `INICIO_ACTIVIDAD` |
| 5 | Plan de Cuentas | `/contabilidad/cuentas` | Cuentas creadas/editadas |
| 6 | Libro Diario | `/contabilidad/diario` | Asientos contabilizados |
| 7 | Libro Mayor | `/contabilidad/mayor` | Saldos por cuenta |
| 8 | Balance de Comprobación | `/contabilidad/balance` | Prueba de cuadre |
| 9 | Estados Financieros | `/estados-financieros/...` | Situación, resultados y efectivo |
| 10 | Documentos del SRI | `/documentos/nuevo` | Comprobante con validaciones |
| 11 | Mis Evidencias | `/mis-evidencias` | Código + huella SHA-256 |
| 12 | Simulador / Evaluaciones / Tutor | `/simulador`, `/evaluaciones`, `/tutor/` | Práctica y retroalimentación |

---

## 7. Guía paso a paso del docente

Esta guía reproduce la secuencia que usa la docente durante el período: **seguir el avance, revisar
los libros, gestionar las actividades del syllabus, calificar las evidencias y exportar el paquete
para Moodle**.

### Paso 1. Entrar y reconocer el panel del docente

Ingresa con tu usuario y contraseña. Al ser **Docente**, el menú lateral muestra la sección
**Entorno Universitario & IA** con los cinco módulos de gestión, que el estudiante no ve.

```
📷 CAPTURA 12 · "Menú lateral del docente"
Rol: Docente            Ruta: cualquier pantalla
+------------------------------------------------------------------------+
|  Menú lateral                                                          |
|  - Dashboard General                                                   |
|  - Contabilidad Central        (Plan de Cuentas, Diario, Mayor, ...)   |
|  - Operaciones Comerciales / Inventario / Tesorería / Informes         |
|  - Entorno Universitario & IA                                          |
|      Simulador de Casos                                                |
|      Mis Evaluaciones                                                  |
|      Mis Actividades                                                   |
|      Mis Evidencias                                                    |
|      Panel Analítica Docente          <-- docente                      |
|      Seguimiento de Accesos           <-- docente                      |
|      Mis Estudiantes                  <-- docente                      |
|      Actividades del Syllabus         <-- docente                      |
|      Evidencias de Estudiantes        <-- docente                      |
|      Verificar Código                 <-- docente                      |
|      Tutor Contable IA                                                 |
|      Centro de Reportes                                                |
+------------------------------------------------------------------------+
Qué mirar:  los cinco módulos marcados "<-- docente" son tus herramientas de
            gestión; el estudiante no los ve en su menú.
```

### Paso 2. Revisar el Dashboard de la empresa demostrativa

El Dashboard es el mismo para todos los roles, pero para el docente es el **estado de la empresa
demostrativa** que se usa en clase: período abierto, fecha de trabajo, alertas y resultados del
simulador del curso.

* **Accesos rápidos:** nueva venta, nueva compra, facturar servicio, caja, estado de resultados.
* **Resultados de simulación:** intentos, completados, promedio general y por nivel.

### Paso 3. Seguimiento de Accesos: quién trabaja y quién no

**Entorno Universitario & IA → Seguimiento de Accesos** (`/docente/accesos`). Es la vista que
responde la pregunta del primer día de clases: *¿quién ingresó?*

```
📷 CAPTURA 13 · "Panel de Accesos de Estudiantes"
Rol: Docente / Administrador            Ruta: /docente/accesos
+------------------------------------------------------------------------+
|  Seguimiento Académico        [ Exportar CSV ]      [ Estudiantes ]    |
|  KPI: Estudiantes · Con al menos una sesión · Eventos en total ·        |
|       Evidencias generadas · Tiempo de actividad                       |
|  --------------------------------------------------------------------  |
|  Filtros de seguimiento                                                |
|   Estudiante [ Todos ▾ ]  Desde [ ]  Hasta [ ]  Actividad [ Todas ▾ ]   |
|   Estado [ Todos los estados ▾ ]   Paralelo [ Todos ▾ ]                 |
|   Buscar [ nombre, usuario o correo ]                                   |
|   [ Aplicar filtros ]  [ Limpiar ]  [ Exportar CSV filtrado ]           |
|  --------------------------------------------------------------------  |
|  Resumen de accesos por estudiante                                     |
|  Estudiante   Paralelo Estado    Primer  Último  Sesiones Tiempo  Act.  |
|  Alcivar...    B       Activa    30/04   30/04   2        47 min  1/6   |
|  Aviles...     B       Activa    29/04   30/04   1        12 min  0/6   |
|  (si nunca entró, la fila muestra el aviso "Nunca ingresó")             |
|  Evidencias · Última acción · [ Ver ficha del estudiante ]              |
+------------------------------------------------------------------------+
Qué mirar:  "Primer acceso"/"Último acceso", "Sesiones", "Tiempo de actividad",
            "Actividades" (iniciadas/asignadas/completadas) y "Evidencias".
Qué hacer:  filtra por Paralelo y por fechas para cerrar una semana, y exporta
            el CSV como respaldo de asistencia y trabajo en el simulador.
```

Los filtros disponibles son: **estudiante**, **desde**, **hasta**, **actividad**, **estado de la
cuenta** (activa, inactiva, ya ingresó, nunca ingresó), **paralelo** y **búsqueda por nombre,
usuario o correo**.

### Paso 4. Exportar el CSV de accesos

El botón **Exportar CSV filtrado** descarga un archivo con separador `;` (se abre directo en Excel,
con BOM para los acentos) y estas columnas:

```
Estudiante ; Usuario ; Correo ; Paralelo ; Matrícula ; Estado de la cuenta ;
Primer acceso ; Último acceso ; Sesiones ; Tiempo de actividad ;
Actividades iniciadas ; Actividades asignadas ; Actividades completadas ;
Evidencias generadas ; Última acción
```

> La exportación respeta los filtros aplicados: filtra primero y exporta después; así el archivo
> contiene exactamente el grupo que quieres calificar.

### Paso 5. Ver la nómina completa y quién nunca ingresó

* **Mis Estudiantes** (`/docente/estudiantes`): la nómina con **Estudiante, Matrícula, Paralelo,
  Estado, Ingresó, Sesiones, Último acceso, Tiempo de actividad, Actividades, Evidencias** y el botón
  de **Acciones** para abrir la ficha.
* **Estudiantes sin ingresar** (`/docente/sin-ingresar`): la misma tabla, ya filtrada, con los
  estudiantes matriculados que nunca iniciaron sesión.

```
📷 CAPTURA 14 · "Estudiantes y Accesos"
Rol: Docente / Administrador            Ruta: /docente/estudiantes
+------------------------------------------------------------------------+
|  Estudiantes y Accesos                                                 |
|  Estudiante         Matrícula  Paralelo Estado  Ingresó  Sesiones       |
|  Alcivar Andrade...  1723456789  B       Activa  Sí       2           |
|  Aviles Mejia...     1709876543  B       Activa  Sí       1           |
|  ...                                                 No   "Nunca ingresó"|
|  Último acceso · Tiempo de actividad · Actividades · Evidencias         |
|  Acciones: [ Ver ficha ]                                               |
+------------------------------------------------------------------------+
Qué mirar:  cruza esta lista con la nómina del aula virtual: los "Nunca
            ingresó" son los que necesitan que les reenvíes sus credenciales.
```

### Paso 6. Abrir la ficha de un estudiante

Desde la ficha del estudiante (`/docente/estudiantes/<id>`) tienes **todo el expediente digital** en
una sola pantalla: datos, acceso, actividades, evidencias, intentos y un resumen de sus libros.

```
📷 CAPTURA 15 · "Ficha del Estudiante"
Rol: Docente / Administrador            Ruta: /docente/estudiantes/5
+------------------------------------------------------------------------+
|  [EA] Alcivar Andrade Emily Alejandra                                  |
|       ealcivar4002 | correo@utm.edu.ec | 1723456789 | Paralelo B        |
|       [Ya ingresó] o [Nunca ingresó]                                    |
|       [ Ver en el panel de accesos ]  [ JSON ]  [ Estudiantes ]         |
|  --------------------------------------------------------------------  |
|  Libros del estudiante (solo lectura)   [Solo lectura] [Balance]        |
|    56 cuentas · 12 aceptan movimiento · 37 asientos · 96 líneas de      |
|    detalle · Debe = Haber = 92778.50                                    |
|    [ Plan de cuentas ] [ Libro Diario ] [ Libro Mayor ] [ Balance ]     |
|    [ Estados financieros ]                                             |
|  Avance: 4 de 6 actividades entregadas                                  |
|  Indicadores: Ingresos registrados · Suma de sesiones · Actividades     |
|    asignadas · Entregadas o revisadas · Evidencias generadas · Última   |
|    acción                                                              |
|  Historial de accesos (sesiones)   # Inicio Fin Duración IP Estado      |
|  Línea de tiempo   [ JSON ]                                             |
|  Actividades del syllabus asignadas                                     |
|  Evidencias generadas                                                  |
|  Intentos de evaluación registrados                                    |
+------------------------------------------------------------------------+
Qué mirar:  el bloque de libros: si dice "El estudiante no tiene aula" o
            "Aún no registra asientos", el estudiante no ha empezado.
Qué hacer:  revisa la "Línea de tiempo" para reconstruir la clase paso a paso
            (qué abrió, qué registró, qué intentos fallidos tuvo).
```

### Paso 7. Ver los libros del estudiante en solo lectura

Cada pestaña abre **el archivo del estudiante** en modo lectura (`file:...?mode=ro`): nunca se puede
modificar su trabajo desde aquí. Las pestañas son **Ficha del estudiante · Plan de cuentas · Libro
Diario · Libro Mayor · Balance de comprobación · Estados financieros**.

```
📷 CAPTURA 16 · "Libro Diario de Alcivar Andrade Emily Alejandra"
Rol: Docente / Administrador            Ruta: /docente/estudiantes/5/diario
+------------------------------------------------------------------------+
|  [EA] Alcivar Andrade Emily Alejandra    [Solo lectura] [Balance cuadrado]|
|  ealcivar4002 | Paralelo B | ealcivar4002.db                            |
|  [Plan de cuentas] [Libro Diario] [Libro Mayor] [Balance] [Estados]     |
|  Filtro de fechas: Desde [ ] Hasta [ ]  [ Filtrar ]                     |
|  #  Fecha       Concepto            Cuentas            Debe     Haber    |
|  1  2026-09-21  Asiento de apertura  ...              5000.00            |
|  ...                                                                    |
+------------------------------------------------------------------------+
Qué mirar:  el aviso amarillo "No hay libros que mostrar" cuando el
            estudiante no tiene aula o su aula está vacía (no es un error).
Qué hacer:  compara el Diario con el Balance: si dice "Balance descuadrado",
            revisa sus asientos antes de la revisión oral.
```

### Paso 8. Crear o ajustar una actividad del syllabus

**Actividades del Syllabus** (`/docente/actividades`) trae las **6 actividades de Contabilidad I**
(una por resultado de aprendizaje) y el formulario para crear más.

```
📷 CAPTURA 17 · "Gestión de Actividades - Panel Docente"
Rol: Docente / Administrador            Ruta: /docente/actividades
+------------------------------------------------------------------------+
|  Gestión de Actividades                                                 |
|  [ Nueva actividad ]  [ Evidencias de estudiantes ]  [ Verificar código ]|
|  --- Panel "Nueva actividad" ---                                        |
|   Código [U1-A1]  Título [Taller asistido: ...]  Unidad [1]             |
|   Componente [DOCENCIA]  Puntaje [10]  Intentos [1]                     |
|   Tipo de evidencia [INTEGRAL]                                          |
|   Apertura [2026-10-05 00:00]  Cierre [2026-10-10 23:59]                |
|   Estado [ABIERTA]  [ ] Modo práctica (oculta ayudas)                    |
|   [ ] Permite Tutor IA                                                  |
|   Instrucciones para el estudiante [ ... ]                              |
|   Evidencia requerida [ ... ]                                           |
|   [ Guardar actividad ]                                                |
|  --- Filtros --- Unidad [4▾] Componente [Todas▾] Estado [Todas▾]        |
|                  Buscar [Código o título] [ Filtrar ] [ Limpiar ]       |
|  --- Tabla ---                                                         |
|  Código  Título              U  Comp.     Puntaje Asig Entr Curso Avance|
|  U1-A1   Taller asistido...  1  DOCENCIA  10      60   0    0    0 %    |
|  U2-A2   Práctica de lab...  2  PRACTICA  12      60   0    0    0 %    |
|  ...                                                                    |
|  Acciones: [asignar a todos] [abrir/cerrar] [ver asignaciones]          |
+------------------------------------------------------------------------+
Qué mirar:  las columnas Asignadas / Entregadas / En curso / Avance: es el
            pulso de la actividad en todo el paralelo.
Qué hacer:  publica la actividad "ABIERTA" el día que empieza y pásala a
            "CERRADA" cuando termine la ventana de entrega.
```

Campos que se guardan por actividad: **código, título, unidad, componente**
(DOCENCIA / PRACTICA / AUTONOMO), **puntaje, intentos máximos, tipo de evidencia**
(PLAN_CUENTAS, DIARIO, MAYOR, BALANCE, INTEGRAL), **fecha de apertura y cierre**, estado
(BORRADOR / ABIERTA / CERRADA), instrucciones, evidencia requerida, modo práctica y si permite
Tutor IA.

### Paso 9. Asignar la actividad al curso

Desde la fila de la actividad, el botón de **asignar a todos los estudiantes** crea una asignación
por estudiante (la operación es idempotente: repetirla no duplica ni borra el avance). Al abrir las
asignaciones de una actividad ves el detalle por estudiante.

```
📷 CAPTURA 18 · "Asignaciones de la actividad U2-A2"
Rol: Docente / Administrador            Ruta: /docente/actividades/2
+------------------------------------------------------------------------+
|  Estudiante      Paralelo Estado    Intentos Abierta en  Cerrada en     |
|  Alcivar Andrade  B      EN_CURSO  1        2026-10-06  -               |
|  Aviles Mejia     B      ENTREGADA 1        2026-10-05  2026-10-07      |
|  Nota  Evidencia                             [Modificada]               |
+------------------------------------------------------------------------+
Estados de la asignación: PENDIENTE · EN_CURSO · ENTREGADA · REVISADA
Qué mirar:  la etiqueta roja "Modificada" avisa que la evidencia del
            estudiante cambió después de finalizarla.
Qué hacer:  al calificar, escribe la nota y la observación en la asignación
            (o usa el código de evidencia para verificarla antes de calificar).
```

### Paso 10. Revisar las evidencias de los estudiantes

**Evidencias de Estudiantes** (`/docente/evidencias`) lista todas las evidencias del curso con
filtros por **estudiante, actividad, estado, búsqueda y "Solo modificadas"**.

```
📷 CAPTURA 19 · "Evidencias de Estudiantes - Panel Docente"
Rol: Docente / Administrador            Ruta: /docente/evidencias
+------------------------------------------------------------------------+
|  Evidencias de estudiantes     (Total · Finales · Modificadas)          |
|  Filtros: Buscar [ ] Actividad [Todas▾] Estudiante [Todos▾]            |
|           Estado [Todos▾]  [ ] Solo modificadas                        |
|  Código                Estudiante  Actividad Tipo   Estado Versiones     |
|  CONT1-B-2026-4F7A9C21 Alcivar...  U2-A2     PLAN_.. FINAL  2           |
|  CONT1-B-2026-9911AB02 Aviles...   U3-A4     DIARIO   BORRADOR 1        |
|  Generada · Integridad · Acciones [ Ver ]                               |
+------------------------------------------------------------------------+
Qué mirar:  "Versiones" y "Integridad": una evidencia FINAL con más de una
            versión cuenta la historia de una corrección (el motivo queda
            registrado).
Qué hacer:  abre el detalle para ver el contenido (cuentas, asientos, balance
            con las cifras reales del aula del estudiante) y califica.
```

### Paso 11. Verificar el código de una evidencia

**Verificar Código** (`/docente/evidencias/verificar`) comprueba que el código que el estudiante
entregó existe y que el contenido **no cambió después** de finalizarlo.

```
📷 CAPTURA 20 · "Verificar código de evidencia - Panel Docente"
Rol: Docente / Administrador            Ruta: /docente/evidencias/verificar
+------------------------------------------------------------------------+
|  Verificar código de evidencia            [ Todas las evidencias ]      |
|  Código de la evidencia [ CONT1-B-2026-4F7A9C21 ]                      |
|  [ Verificar ]                                                         |
|  --------------------------------------------------------------------  |
|  ✔ Evidencia encontrada: Emisión verificada                            |
|  Estudiante · Actividad · Tipo · Estado · Generada en · Huella SHA-256  |
|  Integridad: "Sin cambios" / "Contenido modificado después"            |
|  [ Ver la evidencia ]  [ Buscar en todas las evidencias ]              |
+------------------------------------------------------------------------+
Qué mirar:  la huella SHA-256 y la marca de integridad. Si el código no
            existe, el sistema responde "No existe una evidencia con ese
            código." (no inventa un resultado).
```

### Paso 12. Panel de Analítica Docente

**Panel Analítica Docente** (`/docente/panel`) es la analítica de las **simulaciones** del curso:
puntuaciones, errores frecuentes y promedios por nivel. Se complementa con el seguimiento de accesos
y las evidencias (que miden el trabajo en el sistema contable).

```
📷 CAPTURA 21 · "Panel Analítica Docente"
Rol: Docente / Administrador            Ruta: /docente/panel
+------------------------------------------------------------------------+
|  Panel de Analítica Docente                                            |
|  Estudiantes registrados · Intentos totales · Completados · Promedio    |
|  Errores frecuentes: distribución correcto / parcial / incorrecto       |
|  Promedio por nivel (gráfico de barras: Básico, Intermedio, Avanzado,   |
|  Caso Empresarial Integral)                                            |
|  Progreso individual: intentos y promedio por estudiante                |
|  Simulaciones del curso: nivel, duración y puntuación mínima            |
+------------------------------------------------------------------------+
Qué mirar:  el nivel con el promedio más bajo es el tema que conviene
            reforzar antes de avanzar al siguiente nivel.
```

### Paso 13. Armar el paquete de calificación

Tres fuentes, todas exportables sin pedir capturas al estudiante:

| Qué | Dónde | Resultado |
|---|---|---|
| Accesos y actividad | **Seguimiento de Accesos → Exportar CSV** | Asistencia, sesiones, tiempo, actividades y evidencias por estudiante |
| Evidencias (archivos) | **Mis Evidencias → Preparar captura / Imprimible / PDF** | Documento firmado con su huella SHA-256 |
| Indicadores contables de cada aula | `python deploy/multiaula/exportar_evidencias.py` | `evidencias_simulador.xlsx` (hojas `Resumen`, `Simulador`, `Revision`) y `evidencias_simulador.csv` |

```bash
# Paquete de evidencias del curso (una fila por estudiante)
python deploy/multiaula/exportar_evidencias.py --datos /var/datos/aulas --salida /root/evidencias
python deploy/multiaula/exportar_evidencias.py --min-asientos 20 --permitir-descuadres 0
```

El exportador calcula por estudiante: asientos, descuadres, ecuación patrimonial, utilidad,
caja/bancos/inventario/cartera, intentos y puntuación promedio, y un cumplimiento de 0 a 3; la hoja
`Revisión` lista lo que requiere tu atención. **Es el insumo para subir la evidencia a Moodle.**

### Paso 14. Mantenimiento del período y de las aulas

Comandos que la docente ejecuta entre clases (desde la carpeta del proyecto):

```bash
# 1. Preparar la nómina y las aulas de todo el paralelo (contraseñas aleatorias nuevas)
python database/importar_nomina.py --paralelo B --curso CONT1-AUD-ONLINE-P2-2026

# 2. Recrear el aula de un estudiante desde la plantilla (sin operaciones)
python database/crear_aula.py ealcivar4002 --paralelo B --plan completo

# 3. Reconstruir la plantilla con la que se clonan las aulas
python database/crear_aula.py --plantilla

# 4. Cargar/actualizar las 6 actividades del syllabus (idempotente)
python database/seed_actividades.py --todos

# 5. Actualizar los porcentajes tributarios en la base de control y en todas las aulas
python database/parametros_tributarios_sri.py --todas-las-aulas

# 6. Regenerar la empresa demostrativa (se usa en clase y en las pruebas)
python database/seed_data.py
```

> **Nunca sobreescribas un aula con trabajo.** Antes de clonar, cuenta `asientos`, `ventas` y
> `compras` del aula destino y detente si hay movimientos: el script se niega por defecto y exige
> una opción explícita para forzar. Reejecutar la importación de la nómina **no puede borrarle el
> avance a un estudiante**.

### Resumen del recorrido del docente

| # | Pantalla | Ruta | Qué obtiene |
|---|---|---|---|
| 1-2 | Menú y Dashboard | `/dashboard` | Estado del período y del curso |
| 3 | Seguimiento de Accesos | `/docente/accesos` | Quién ingresó, cuánto tiempo y qué hizo |
| 4 | Exportar CSV | `/docente/accesos/exportar.csv` | Respaldo de asistencia y trabajo |
| 5 | Mis Estudiantes / Sin ingresar | `/docente/estudiantes`, `/docente/sin-ingresar` | Nómina y ausencias |
| 6 | Ficha del estudiante | `/docente/estudiantes/<id>` | Expediente completo + línea de tiempo |
| 7 | Libros del estudiante | `/docente/estudiantes/<id>/{cuentas,diario,mayor,balance,estados}` | Su trabajo contable, en solo lectura |
| 8-9 | Actividades del Syllabus | `/docente/actividades` | Crear, asignar, abrir y cerrar actividades |
| 10 | Evidencias de Estudiantes | `/docente/evidencias` | Revisar y calificar evidencias |
| 11 | Verificar Código | `/docente/evidencias/verificar` | Comprobar el código y la huella |
| 12 | Panel Analítica Docente | `/docente/panel` | Analítica de las simulaciones |
| 13 | Paquete de calificación | CSV + XLSX del exportador | Insumo para Moodle |
| 14 | Mantenimiento | scripts de `database/` y `deploy/` | Nómina, aulas, actividades e impuestos |

---

## 8. Recorrido guiado de 15 minutos

Un primer recorrido para entender cómo se encadenan los módulos (rol **Estudiante**):

1. **Inicia sesión** con `estudiante / estudiante123`.
2. Entra a **Simulador de Casos** y pulsa *Iniciar* en **Nivel 1 — Básico**.
3. Lee el enunciado y el documento fuente del caso. En la tabla de líneas contables selecciona las
   cuentas, escribe los importes en **Debe** y **Haber** y añade líneas si necesitas más.
   *Si te trabas, pulsa **Pedir pista al Tutor IA** (cada pista resta 5 puntos).*
4. Pulsa **Enviar Asiento y Evaluar**. Verás tu puntuación sobre 100, la rúbrica desglosada y una
   retroalimentación concreta línea por línea.
5. Ve a **Contabilidad → Libro Diario** y localiza los asientos que generaste.
6. Ve a **Ventas → Nueva venta**, registra una venta a crédito por 20 unidades del producto que
   prefieras (forma de pago *Crédito*, 30 días) y guárdala. Si el cliente es **agente de retención**,
   marca la casilla y el sistema calcula las retenciones de Renta e IVA del desglose.
7. Revisa en **Cuentas por Cobrar** que apareció el documento; registra un **cobro parcial**.
8. Revisa **Caja**, **Bancos** y **Documentos Fuente** para ver los movimientos y respaldos creados.
9. Abre **Estados Financieros → Situación Financiera**: debe aparecer el banner verde
   **“Activo = Pasivo + Patrimonio ✓”**.
10. Cierra con **Contabilidad → Balance de Comprobación**: los totales de débitos y créditos, y los
    saldos deudor y acreedor, deben coincidir.
11. Entra a **Mis Actividades**, abre la actividad de la unidad en curso y pulsa *Iniciar*.
12. Genera tu **evidencia** en **Mis Evidencias** eligiendo esa actividad: obtendrás el código
    verificable que entregas al docente.

---

## 9. Mapa de navegación

El menú lateral se organiza así (las secciones marcadas **D** solo aparecen para Docente y
Administrador):

| Sección | Módulos |
|---|---|
| **Dashboard General** | Indicadores, gráficos, alertas, actividad reciente |
| **Contabilidad Central** | Plan de Cuentas · Libro Diario · Libro Mayor · Balance de Comprobación · Ajustes Contables · Cierre de Período |
| **Operaciones Comerciales** | Ventas de Bienes · Servicios Prestados · Compras a Proveedores |
| **Inventario & Kardex** | Catálogo de Productos · Kardex (FIFO / Promedio) · Existencias & Alertas |
| **Tesorería & Cartera** | Caja & Arqueos · Cuentas Bancarias · Conciliación Bancaria · Clientes · Cuentas por Cobrar · Proveedores · Cuentas por Pagar · Documentos Fuente · Tributación |
| **Informes Financieros NIIF** | Estado de Resultados · Situación Financiera · Flujo de Efectivo |
| **Entorno Universitario & IA** | Simulador de Casos · Mis Evaluaciones · **Mis Actividades** · **Mis Evidencias** · **Casos de los libros (§61)** |
| **Entorno Universitario & IA** *(D)* | Panel Analítica Docente · **Seguimiento de Accesos** · **Mis Estudiantes** · **Actividades del Syllabus** · **Evidencias de Estudiantes** · **Verificar Código** · **Banco de casos §61 y §62** |
| **Entorno Universitario & IA** *(todos)* | Tutor Contable IA · Centro de Reportes |
| **Administración del Sistema** *(solo Administrador)* | Parámetros & Config · Gestión Usuarios · Parámetros Tributarios · Auditoría & Trazabilidad |

**Barra superior:** período contable activo, fecha de trabajo, buscador global (busca cuentas,
productos, clientes, asientos y simulaciones), acceso rápido al simulador y al Tutor IA, y menú del
usuario (ver resultados, ir al sistema contable, cerrar sesión).

---

## 10. Módulos del sistema

Cada ficha indica el **rol** que puede entrar, la **ruta** en el navegador y qué muestra, cómo se usa
y qué datos deja registrados. Las pantallas ya descritas en las guías (secciones
[6](#6-guía-paso-a-paso-del-estudiante) y [7](#7-guía-paso-a-paso-del-docente)) se referencian para
no repetirlas.

### 10.1 Dashboard

**Rol:** todos · **Ruta:** `/dashboard`

Vista ejecutiva de la empresa simulada.

* **Indicadores financieros:** saldo de caja, bancos, ventas de bienes, ingresos por servicios,
  inventario valorizado, cuentas por cobrar, cuentas por pagar y utilidad del período.
* **Gráficos:** evolución semanal de ventas, servicios, compras y gastos (con conmutador
  *Barras / Líneas*) y composición financiera (disponibilidad vs cartera vs inventario).
* **Alertas operativas:** stock bajo mínimo, cartera vencida (con monto), cuentas por pagar
  pendientes y **asientos descuadrados** (control permanente de la partida doble).
* **Actividad reciente:** últimos asientos contabilizados y últimos documentos fuente.
* **Inventario por categoría** (con filtro) y **cartera por estado**.
* **Resultados de simulación:** intentos, completados, promedio general y por nivel.
* **Accesos rápidos:** nueva venta, nueva compra, facturar servicio, caja, estado de resultados y
  Tutor IA.

> Todos los valores se calculan en vivo desde los libros de quien está en sesión: para el estudiante
> son los de **su** empresa; para el docente, los de la empresa demostrativa.

### 10.2 Plan de Cuentas

**Rol:** todos · **Ruta:** `/contabilidad/cuentas` (+ `/contabilidad/cuentas/<id>/editar`)

Las **46 cuentas** del plan contable con estructura jerárquica y clasificación en seis grupos:
**1 Activo · 2 Pasivo · 3 Patrimonio · 4 Ingresos · 5 Costos · 6 Gastos**.

Cada cuenta tiene código, nombre, **naturaleza** (deudora/acreedora), clasificación, cuenta padre,
nivel, si **acepta movimiento** y su **saldo actual** calculado desde el libro mayor.

* **Nueva cuenta:** código, nombre, naturaleza, clasificación, cuenta padre y acepta movimiento.
* **Editar:** botón por fila; el cambio queda registrado en la **Auditoría** con el valor anterior y
  el nuevo.
* Cada cuenta creada o consultada genera un evento (`CREAR_CUENTA`, `CONSULTA_ACTIVIDAD`) en la
  línea de tiempo del estudiante.

Pantalla descrita en la 📷 CAPTURA 5.

### 10.3 Libro Diario

**Rol:** todos · **Ruta:** `/contabilidad/diario` (+ `POST /contabilidad/diario/<id>/revertir`)

Registro cronológico de **asientos**: fecha, concepto, documento fuente vinculado y líneas
(cuenta, Debe, Haber).

* **Registrar un asiento:** completa fecha, concepto y documento; añade líneas y guarda.
* **Validaciones:** partida doble obligatoria, mínimo dos líneas, importes mayores que cero y fecha
  dentro del período abierto (ver [sección 12](#12-reglas-contables-y-validaciones)).
* **Revertir:** genera el contra-asiento; el original se conserva y queda con estado `REVERTIDO`.
  **Nunca se borra un asiento contabilizado.**
* Filtros por fecha y por cuenta; los asientos se pueden exportar desde el Centro de Reportes.

Pantalla descrita en la 📷 CAPTURA 6.

### 10.4 Libro Mayor

**Rol:** todos · **Ruta:** `/contabilidad/mayor`

Movimientos de cada cuenta con su **saldo acumulado** (mayorización). Sirve para comprobar que un
asiento llegó a la cuenta correcta y con el lado correcto; alimenta el Balance y los estados
financieros. Pantalla descrita en la 📷 CAPTURA 7.

### 10.5 Balance de Comprobación

**Rol:** todos · **Ruta:** `/contabilidad/balance`

**Balance de comprobación de sumas y saldos**: sumas del Debe y del Haber por cuenta y saldos deudor
y acreedor, con totales y control de cuadre. Si exportas o imprimes desde el Centro de Reportes,
incluye el control de integridad (sumas y saldos). Pantalla descrita en la 📷 CAPTURA 8.

### 10.6 Ajustes Contables

**Rol:** todos · **Ruta:** `/contabilidad/ajustes`

Asientos de fin de período y corrección: **depreciación**, **provisión de incobrables**,
**compensación de IVA**, regularizaciones y cualquier ajuste que la cátedra pida. Funciona como el
Libro Diario (líneas Debe/Haber) pero con conceptos de ajuste predefinidos y su documento fuente
(*comprobante de ajuste*). Cada ajuste genera el evento `CORRECCION_ASIENTO` o
`CONSULTA_ACTIVIDAD` en la línea de tiempo del estudiante.

### 10.7 Cierre de Período

**Rol:** Administrador y Docente · **Ruta:** `/contabilidad/cierre`

Cierra el período contable: cancela ingresos, costos y gastos contra el resultado y deja el período
en estado **CERRADO** (queda registrado en el asiento de cierre). Después del cierre, el sistema
deja de aceptar operaciones ordinarias y lo informa con un mensaje explícito. Para volver a
practicar: `python database/seed_data.py` sobre una base de práctica.

### 10.8 Ventas de Bienes

**Rol:** todos · **Rutas:** `/ventas`, `/ventas/nueva`, `/ventas/<id>`, `POST /ventas/desglose`

Registro de ventas de mercadería con **inventario perpetuo**: cada venta genera el ingreso, el IVA,
la cartera o el efectivo **y** el asiento de **costo de ventas** contra inventario.

* **Cliente**, forma de pago (*Efectivo*, *Transferencia*, *Crédito* con días), días de crédito,
  caja o banco, y las líneas de producto (cantidad, precio, descuento).
* **IVA:** el porcentaje y la cuenta salen del catálogo tributario (nunca están escritos en el
  programa); el 15 % es la tarifa general configurada.
* **Retenciones de Renta y de IVA que el cliente agente de retención practica a la empresa:**
  se activan marcando *“El cliente es agente de retención (contribuyente especial)”* y eligiendo el
  **concepto** de la venta. La **retención de Renta** se calcula sobre el valor de la venta (subtotal,
  sin IVA) y la **retención de IVA** sobre el IVA de la factura; lo retenido queda **a favor de la
  empresa** y el asiento cuadra por el **neto a cobrar**.
* El botón de **vista previa** (`POST /ventas/desglose`) muestra subtotal, IVA, retenciones, total de
  la factura y neto **antes** de guardar: lo que se ve es lo que se contabiliza.
* Si no marcas la casilla del agente, la venta se cobra completa (comportamiento clásico, sin
  retenciones).

```
📷 CAPTURA 22 · "Nueva venta"
Rol: todos                 Ruta: /ventas/nueva
+------------------------------------------------------------------------+
|  Nueva venta                                                           |
|   Cliente [ CLIENTE 01 ▾ ]   Forma de pago [ CRÉDITO ▾ ]  Días [ 30 ]   |
|   [ ] El cliente es agente de retención (contribuyente especial):       |
|       la empresa SUFRE la retención de Renta e IVA                     |
|   Concepto de la venta (retenciones que aplica el cliente) [ BIENES ▾ ] |
|   Detalle: Producto | Cantidad | Precio | Descuento | Subtotal          |
|   Resumen:  Subtotal ..... 1.000,00   IVA 15 % ......... 150,00        |
|             Retención Renta 2 % .......... − 20,00                     |
|             Retención IVA 30 % ........... − 45,00                     |
|             Total retenciones ............ − 65,00                     |
|             NETO A COBRAR ....... 1.085,00                             |
|   [ Ver desglose previo ]   [ Guardar venta ]                          |
+------------------------------------------------------------------------+
Qué mirar:  que el "Neto a cobrar" sea el que se contabiliza en caja/banco o
            en la cartera del cliente.
```

### 10.9 Servicios Prestados

**Rol:** todos · **Ruta:** `/servicios` (GET/POST)

Facturación de servicios (entrega/distribución, transporte, asesoría, mantenimiento, instalación).
Usa el catálogo de servicios, la tarifa acordada y la forma de pago, y aplica exactamente el mismo
tratamiento tributario y de **retenciones por concepto** que las ventas de bienes (el cliente agente
de retención retiene Renta e IVA). El listado muestra las columnas **Retención Renta** y
**Retención IVA** con su porcentaje y código. Los servicios **no** mueven inventario.

### 10.10 Compras a Proveedores

**Rol:** todos · **Rutas:** `/compras/`, `/compras/nueva`, `/compras/<id>`, `POST /compras/desglose`

Registro de compras con actualización de inventario y Kardex, y control de factura duplicada por
proveedor. Incluye **retenciones de Renta y de IVA según los porcentajes del catálogo del SRI**:

* El **concepto de la compra** determina qué retenciones se aplican:
  `BIENES`, `SERVICIOS_MANO_OBRA`, `SERVICIOS_PROFESIONALES`, `SERVICIOS_SOCIEDADES`,
  `BIENES_AGRICOLAS_PRODUCTOR`, `RIMPE_EMPRENDEDOR`, `RIMPE_NEGOCIO_POPULAR`, `LIQUIDACION_COMPRA`
  y `SIN_RETENCION` (la opción por defecto, que conserva el comportamiento clásico).
* Si el proveedor es **contribuyente especial**, la retención de IVA se reduce (10 % en bienes,
  20 % en servicios) y la de Renta se mantiene.
* La **retención de Renta** se calcula sobre el valor del bien o servicio (sin IVA) y la de **IVA**
  sobre el IVA de la factura.
* La **cuenta por pagar y la deuda del proveedor es el NETO** (factura − retenciones): lo retenido se
  declara y paga al SRI, no al proveedor. En compras de contado se paga el neto, y el asiento cuadra.

```
📷 CAPTURA 23 · "Nueva compra"
Rol: todos                 Ruta: /compras/nueva
+------------------------------------------------------------------------+
|  Nueva compra                                                          |
|   Proveedor [ PROVEEDOR 03 ▾ ]  Nº factura [001-002-000004512]          |
|   Forma de pago [ CRÉDITO ▾ ] Días [30]  Fecha [2026-04-30]            |
|   [ ] El proveedor es contribuyente especial (retención de IVA menor)  |
|   Concepto de la compra (retenciones aplicables) [ BIENES ▾ ]          |
|   Detalle: Producto | Cantidad | Costo unitario | Subtotal              |
|   Resumen: Subtotal 500,00 · IVA 15 % 75,00 · Total factura 575,00      |
|            Retención Renta 2 % (−10,00) · Retención IVA 30 % (−22,50)   |
|            Total retenciones −32,50 · NETO A PAGAR 542,50               |
|   Tarifas vigentes en el catálogo del SRI (dato configurable)          |
|   [ Ver desglose previo ]   [ Guardar compra ]                         |
+------------------------------------------------------------------------+
Qué mirar:  "La retención de Renta se calcula sobre el valor del bien o
            servicio (subtotal, sin IVA) y la de IVA sobre el IVA de la
            factura" — es el aviso de la propia pantalla.
```

### 10.11 Catálogo de Productos

**Rol:** todos · **Ruta:** `/inventarios/` y `/inventarios/productos`

Los **20 productos** de primera necesidad con código, nombre, categoría, unidad, precio de venta,
costo, **stock actual**, stock mínimo y máximo, y proveedor principal. El stock se actualiza solo con
cada compra, venta y ajuste de inventario; no se edita a mano.

### 10.12 Kardex

**Rol:** todos · **Ruta:** `/inventarios/kardex` (+ `/inventarios/kardex/<producto_id>`)

Tarjeta **Kardex** por producto: entradas, salidas y saldo, con el **método de valoración**
(*Promedio ponderado* o *FIFO*) elegido en la empresa. Cada movimiento muestra su documento de
origen y su costo unitario; es la base del **costo de ventas** que se contabiliza en cada venta.

### 10.13 Existencias y Alertas

**Rol:** todos · **Ruta:** `/inventarios/stock`

Reporte de existencias valorizado con las **alertas de stock bajo mínimo** (cantidad, mínimo,
máximo y sugerencia de reposición). Las alertas se repiten en el Dashboard y en
`GET /api/inventory/alerts` para que los agentes de IA las puedan consultar.

### 10.14 Caja y Arqueos

**Rol:** todos · **Rutas:** `/caja`, `POST /caja/movimiento`, `POST /caja/regularizar/<arqueo_id>`

Saldos de la caja (**1.1.01 Caja General**), movimientos de ingreso y egreso, y **arqueos de caja**:
el conteo físico se compara contra el saldo contable y el sistema registra el **faltante o
sobrante**. El botón *Regularizar* contabiliza la diferencia con su documento de arqueo. Cada
movimiento y arqueo genera su comprobante en Documentos Fuente.

### 10.15 Cuentas Bancarias

**Rol:** todos · **Rutas:** `/bancos`, `POST /bancos/movimiento`

Las **2 cuentas bancarias** de la empresa (Banco Pichincha, Banco Guayaquil) con su saldo real,
depósitos, retiros, transferencias, **notas bancarias de débito y crédito** y cheques. Cada
movimiento deja su comprobante y su asiento (Debe/Haber de banco contra la contrapartida).

### 10.16 Conciliación Bancaria

**Rol:** todos · **Ruta:** `/conciliacion` (GET/POST)

Compara el **saldo del estado de cuenta** contra el **saldo contable** del banco y explica la
diferencia: partidas en tránsito, notas no contabilizadas, cheques no cobrados. Al cerrar la
conciliación se guarda el registro y el asiento de ajuste si corresponde.

### 10.17 Clientes

**Rol:** todos · **Ruta:** `/clientes` (GET/POST)

Catálogo de los **10 clientes** con identificación/RUC, razón social, contacto, dirección, cupo y
estado. Incluye el **historial de cada cliente** (compras, cobros y saldo) y su disponibilidad por
la API (`GET /api/customers`, `/api/customers/<id>/history`).

### 10.18 Cuentas por Cobrar

**Rol:** todos · **Ruta:** `/cuentas-cobrar` (GET/POST)

Cartera por cliente: documento, fecha de emisión, **vencimiento**, valor, saldo y estado, con filtro
de *solo vencidas*, banner de control y gráficos.

* **Cobro total o parcial:** medio de pago (efectivo, transferencia, cheque), banco y número de
  comprobante. El sistema reduce el saldo, actualiza el estado, genera el **comprobante de ingreso**,
  contabiliza (Debe Caja/Banco — Haber `1.1.04` Cuentas por Cobrar) y registra el ingreso en
  tesorería.
* **Validación:** el cobro no puede superar el saldo pendiente.
* Si la venta tuvo **retenciones**, el saldo a cobrar ya es el neto: lo retenido se cobra al SRI, no
  al cliente.

### 10.19 Proveedores

**Rol:** todos · **Ruta:** `/proveedores` (GET/POST)

Catálogo de los **8 proveedores** con RUC, razón social, contacto, **condición frente al IVA**
(contribuyente especial o no, RIMPE Emprendedor o Negocio Popular), días de crédito y estado. Incluye
historial y API (`GET /api/suppliers`, `/api/suppliers/<id>/history`). La **condición tributaria** del
proveedor es la que hace que la compra retenga 10 % o 20 % de IVA en lugar de 30 % o 70 %.

### 10.20 Cuentas por Pagar

**Rol:** todos · **Ruta:** `/cuentas-pagar` (GET/POST)

Obligaciones por proveedor: proveedor, factura, fecha de emisión, **vencimiento**, valor, saldo y
estado, con filtro de *solo vencidas*.

* **Registrar un pago:** botón por fila (*Registrar pago*) → importe (total o **parcial**), medio de
  pago, banco y número de comprobante. El sistema reduce la obligación, actualiza el estado, genera
  el **comprobante de egreso**, contabiliza (Debe `2.1.01` Cuentas por Pagar — Haber Caja/Banco) y
  registra el egreso en tesorería.
* La deuda registrada es el **neto de retenciones**: las retenciones se declaran al SRI por separado.

### 10.21 Documentos Fuente

**Rol:** todos · **Ruta:** `/documentos/` (+ `/documentos/<doc_id>`)

Los documentos simulados que **respaldan cada operación**, con filtros por **tipo, número, tercero,
estado y rango de fechas**, el resumen por tipo con su monto y la columna del **asiento contable**
vinculado. El botón **Detalle** abre el documento con sus datos estructurados, su desglose y el
asiento que generó: es la evidencia que cierra la cadena
*documento → transacción → asiento → diario → mayor → estados financieros*.

```
📷 CAPTURA 24 · "Documentos Fuente"
Rol: todos                 Ruta: /documentos/
+------------------------------------------------------------------------+
|  Documentos Fuente                                                     |
|  Filtros: Tipo [Todos▾] Número [ ] Tercero [ ] Estado [Todos▾]          |
|           Desde [ ] Hasta [ ]                                          |
|  Resumen por tipo (cantidad y monto) · Total del listado               |
|  --------------------------------------------------------------------  |
|  Tipo          Número             Fecha       Emisor    Tercero/Adquir. |
|  FACTURA_VENTA 001-001-000000123  2026-04-30  Nueva Es… CLIENTE 01      |
|  COMPROBANTE_… 001-001-000000045  2026-04-30  Nueva Es… PROVEEDOR 03    |
|  Estado · Monto · Asiento contable · [ Detalle ]                       |
+------------------------------------------------------------------------+
Qué mirar:  los tipos del simulador (factura de venta/compra/servicio,
            comprobante de ingreso/egreso/caja/cierre, notas de crédito y
            débito, papeleta de depósito, nota bancaria, estado de cuenta,
            arqueo de caja, rol de pagos, orden de compra, comprobante de
            ajuste, documentos por cobrar/pagar y documento interno).
Qué hacer:  usa "Detalle" para ver el asiento vinculado cuando un saldo no
            te cuadre: el documento dice de dónde salió el registro.
```

Los **documentos del SRI** (catálogo normativo, emisión de comprobantes y anulación) se documentan
en las tres fichas siguientes.

---

### 10.22 Documentos del SRI: catálogo normativo

**Rol:** todos · **Ruta:** `/documentos/catalogo`

El **catálogo de tipos de comprobante** con su ficha normativa: **14 tipos** agrupados en cuatro
categorías, más las **23 reglas** que el sistema valida al emitir.

| Categoría | Tipos |
|---|---|
| **Comprobantes de venta (8)** | Factura · Nota de venta (RISE) · Tiquete de máquina registradora · Liquidación de compra de bienes y servicios · Liquidación de compra de vehículos usados · Boletos o entradas a espectáculos públicos · Factura de servicios turísticos · Factura de transporte (excepto taxi y carga pesada) |
| **Documentos complementarios (3)** | Guía de remisión · Nota de crédito · Nota de débito |
| **Comprobantes de retención (1)** | Comprobante de retención |
| **Documentos de soporte (2)** | Acta de entrega-recepción de botellas plásticas no retornables (PET) · Acta de entrega-recepción de vehículos usados |

Cada regla se muestra con **Código**, **Título**, **Aplica a**, **Severidad**
(BLOQUEO / ADVERTENCIA / INFORMATIVA), **Validación automática** y **Qué exige el reglamento**. El
catálogo incluye también los **parámetros efectivos** del módulo (tope de consumidor final,
días hábiles para emitir la retención, longitudes de establecimiento/punto de emisión/secuencial y
la leyenda educativa).

```
📷 CAPTURA 25 · "Catálogo de documentos del SRI"
Rol: todos                 Ruta: /documentos/catalogo
+------------------------------------------------------------------------+
|  Catálogo de documentos del SRI          14 tipos · 23 reglas          |
|  Parámetros: tope consumidor final $200 · retención en 5 días hábiles   |
|              alerta desde el día 4 · baja de documentos 15 días         |
|              establecimiento 3 · punto de emisión 3 · secuencial 9      |
|              Leyenda: DOCUMENTO PARA USO EDUCATIVO (SIN VALIDEZ ...)    |
|  --------------------------------------------------------------------  |
|  Código        Título                        Aplica a  Severidad        |
|  R-57.2        Numeración de 15 dígitos       TODO      BLOQUEO         |
|  R-57.1        Emisión previa autorización    FACTURA   BLOQUEO         |
|  R-57.7        Identificación del adquirente  FACTURA…  BLOQUEO         |
|  R-57.12       Plazo del comprobante de ret.  RETENCION ADVERTENCIA     |
|  ...                                                                    |
|  Validación automática · Qué exige el reglamento                        |
+------------------------------------------------------------------------+
Qué mirar:  la severidad de cada regla decide si el sistema bloquea la
            emisión (BLOQUEO) o solo advierte (ADVERTENCIA/INFORMATIVA).
```

### 10.23 Documentos del SRI: emitir un comprobante

**Rol:** todos · **Rutas:** `/documentos/nuevo` (GET/POST), `/documentos/<id>`,
`POST /documentos/<id>/anular`

1. Elige el **tipo de documento**; el formulario se arma con los **campos preimpresos** y los
   **campos de llenado** del catálogo (emisor, RUC, establecimiento, punto de emisión, tipo de
   emisión, adquirente, detalle, forma de pago).
2. El sistema **valida** el comprobante con las reglas del catálogo y marca en rojo lo que falta,
   explicando en cada punto *qué exige el reglamento*.
3. Al **emitir**, el comprobante se guarda numerado y aparece en Documentos Fuente.
4. En el detalle puedes **anular** el comprobante indicando el **motivo** (la fila se conserva en el
   archivo: nunca se borra).

**Estados del documento:** `EMITIDO · ENTREGADO · ANULADO · DADO_DE_BAJA`.
Toda emisión y anulación queda en la **auditoría** y genera su evento de seguimiento.

Pantalla descrita en la 📷 CAPTURA 10.

### 10.24 Documentos del SRI: ¿qué documento necesito?

**Rol:** todos · **Ruta:** `/documentos/soporte`

Ayuda didáctica: dices **qué operación** vas a registrar y el sistema te dice **qué comprobante
corresponde**, con las reglas aplicables. Cubre **16 operaciones**: compra de bienes, compra de
servicios, compra a no obligado a llevar contabilidad, compra de vehículo usado, compra con tiquete,
venta de bienes, venta de servicios, venta de servicios turísticos, venta de transporte, venta a
consumidor final, venta RISE, venta de espectáculos, traslado de mercadería, retención, devolución o
descuento y cobro posterior.

Además acepta **banderas de contexto** (consumidor final, requiere traslado, ISD, turístico, RISE,
vehículo usado, proveedor con RUC, sin identificación) para afinar la sugerencia.

```
📷 CAPTURA 26 · "¿Qué documento necesito?"
Rol: todos                 Ruta: /documentos/soporte
+------------------------------------------------------------------------+
|  ¿Qué documento necesito?                                              |
|   Operación [ VENTA_BIENES ▾ ]                                         |
|   Detalles de la operación (opcional):                                 |
|    [ ] consumidor final   [ ] requiere traslado   [ ] es ISD            |
|    [ ] turístico  [ ] RISE  [ ] vehículo usado  [ ] proveedor con RUC   |
|  --------------------------------------------------------------------  |
|  Sugerencia: FACTURA — Factura                                          |
|  Reglas aplicables: Código · Título · Severidad                         |
+------------------------------------------------------------------------+
Qué mirar:  los nombres de las operaciones; cada una explica el comprobante
            y las reglas que se aplican al emitirlo.
```

### 10.25 Tributación: IVA y retenciones

**Rol:** todos · **Ruta:** `/impuestos/`

* **Configuración Tributaria:** la tabla de los **22 parámetros** vigentes con código, nombre,
  **porcentaje**, tipo, vigencia y estado activo/inactivo. Incluye:
  **IVA** general 15 % en ventas y en compras (crédito tributario), IVA 5 % en construcción y 8 % en
  servicios turísticos; **retenciones de IVA** (10 % bienes a contribuyente especial, 20 % servicios
  a contribuyente especial, 30 % transferencia de bienes, 70 % servicios/derechos/comisiones,
  100 % servicios profesionales, arrendamiento, importación de servicios y liquidaciones de compra);
  y **retenciones de Renta** (0 % RIMPE Negocio Popular y bancos, 1 % bienes agrícolas al productor y
  RIMPE Emprendedor, 1,75 % bienes agrícolas a comercializadores, 2 % bienes muebles, 3 % servicios de
  mano de obra, liquidaciones y regla residual, 5 % servicios profesionales de sociedades y
  10 % honorarios y arrendamientos).
* **Determinación de IVA del período** (calculada con el Libro Mayor): IVA en ventas (**débito
  fiscal**), IVA en compras (**crédito tributario**), **IVA por pagar** o **crédito a favor** y las
  **retenciones** acumuladas.
* **Calculadora tributaria del simulador:** base imponible + impuesto + total, ejecutando el cálculo
  real del sistema.
* **Cuentas contables utilizadas por la configuración tributaria:** impuesto, cuenta asignada y
  porcentaje.

**Regla de oro:** el sistema **nunca inventa tasas**. Los porcentajes provienen exclusivamente de la
tabla de impuestos; si falta configuración para un tipo de impuesto, la operación se rechaza con un
mensaje explícito. **Edición de tasas:** solo el rol **Administrador**, en
*Administración → Parámetros Tributarios*.

### 10.26 Estado de Resultados

**Rol:** todos · **Ruta:** `/estados-financieros/resultados`

**Estructura escalonada**

```
Ingresos por ventas de bienes (4.1.01)
+ Ingresos por prestación de servicios (4.1.02)
= Total ingresos operacionales
− Costo de mercaderías vendidas (5.1.01)
= Utilidad bruta en ventas
− Gastos administrativos (sueldos, arriendo, servicios básicos, depreciación, mantenimiento)
− Gastos de ventas (publicidad y marketing)
= Utilidad operacional
+ Otros ingresos (4.2.01: intereses ganados…)
− Gastos financieros y comisiones (6.2.01)
= Utilidad / (Pérdida) neta del período
```

Incluye análisis vertical (porcentaje sobre ventas), gráfico comparativo y filtro por rango de
fechas. **Todos los valores provienen de los movimientos contables**, no de estimaciones.

### 10.27 Estado de Situación Financiera

**Rol:** todos · **Ruta:** `/estados-financieros/situacion-financiera`

**Activos corrientes y no corrientes**, **Pasivos corrientes y no corrientes** y **Patrimonio**, en
dos columnas que se apilan en móvil, con las cuentas de valuación (depreciación acumulada y provisión
de incobrables) presentadas restando.

**Validación:** banner que confirma la ecuación fundamental:

* **Verde:** `Activo = Pasivo + Patrimonio ✓`
* **Rojo:** alerta con la **diferencia** detectada y accesos directos a Ajustes y al Balance de
  Comprobación para localizar el problema.

Añade indicadores de apoyo: razón corriente, capital de trabajo, endeudamiento y autonomía.

> Mientras el período no se cierre, el resultado del ejercicio se incorpora automáticamente al
> patrimonio.

Pantalla descrita en la 📷 CAPTURA 9.

### 10.28 Estado de Flujo de Efectivo

**Rol:** todos · **Ruta:** `/estados-financieros/flujo-efectivo`

Movimientos de efectivo (caja y bancos) clasificados en **actividades de operación**, **inversión** y
**financiamiento**, con el total de cada actividad, el gráfico de barras comparativo y la
**variación neta del efectivo** del período.

### 10.29 Simulador de Casos

**Rol:** todos · **Rutas:** `/simulador`, `/simulador/<id>/iniciar`,
`/simulador/<id>/jugar`, `POST /simulador/evaluar`

**Los cuatro niveles**

| Nivel | Nombre | Contenidos |
|---|---|---|
| **1** | Básico | Compras y ventas de contado, servicios, cobros y pagos |
| **2** | Intermedio | Crédito, inventarios, IVA, descuentos, devoluciones, bancos |
| **3** | Avanzado | Ajustes, conciliación, depreciación, provisiones, cierre, estados financieros |
| **4** | Caso Empresarial Integral | Gestión completa del período y asiento de cierre |

```
📷 CAPTURA 27 · "Simulador de Casos"
Rol: todos                 Ruta: /simulador/<id>/jugar
+------------------------------------------------------------------------+
|  Caso Nivel 1 · Básico            Tiempo: 00:03:12                     |
|  ENUNCIADO: fecha, descripción, documento fuente, cantidades, precios,  |
|  condiciones y forma de pago. (La solución NO se muestra.)              |
|  Líneas del asiento                                                    |
|   #  Cuenta                          Debe         Haber                |
|   1  [1.1.01 Caja General      ]     [ 1130.00 ]                       |
|   2  [4.1.01 Ingresos ventas   ]                 [ 1000.00 ]           |
|   [+ Agregar línea]  [- Quitar línea]                                  |
|  [ Pedir pista al Tutor IA (−5 puntos) ]  [ Enviar Asiento y Evaluar ]  |
+------------------------------------------------------------------------+
Qué mirar:  el documento fuente y la forma de pago del enunciado: definen
            las cuentas y si el registro es al contado o al crédito.
Qué hacer:  arma las líneas, verifica que Debe = Haber y envía a evaluar.
```

**Puntuación (rúbrica)**

| Criterio | Puntos |
|---|---|
| Cuentas seleccionadas correctamente | 40 |
| Posición correcta en Debe/Haber | 30 |
| Importes correctos | 20 |
| Partida doble cuadrada | 10 |
| **Penalización** | **−5 por cada pista utilizada** |

* **≥ 85 puntos:** CORRECTO · **50 – 84,99:** PARCIALMENTE CORRECTO · **< 50:** INCORRECTO.

La retroalimentación es **específica**, por ejemplo: *“La cuenta ‘Caja General’ está correctamente
seleccionada, pero su movimiento debe registrarse en el Debe porque aumenta un activo.”* Al final se
muestra también el **fundamento teórico** del caso. Quedan registrados el intento, las respuestas,
los errores, las pistas, el tiempo y la puntuación (y también el evento en la línea de tiempo del
estudiante).

**Casos disponibles:** los cuatro niveles suman **19 casos** con solución verificada, generados a
partir de los **asientos reales** del sistema.

### 10.30 Mis Evaluaciones

**Rol:** todos · **Ruta:** `/evaluaciones`

```
📷 CAPTURA 28 · "Mis Evaluaciones"
Rol: todos                 Ruta: /evaluaciones
+------------------------------------------------------------------------+
|  Mis Evaluaciones                                                      |
|  Promedio de intentos completados: 82.5                                |
|  #  Casos / Simulación     Inicio     Fin       Puntuación Tiempo Estado |
|  1  Nivel 1 · Básico       30/04 10:02 30/04 10:09   90.0    07:12 ✓    |
|  2  Nivel 2 · Intermedio   30/04 10:15 30/04 10:26   70.0    11:40 ~    |
|  [ Reintentar ]  Semáforo de puntuación por intento                     |
+------------------------------------------------------------------------+
Qué mirar:  el promedio y el semáforo te dicen si ya puedes pasar de nivel.
```

El docente ve en esta misma pantalla los intentos de todos los estudiantes.

### 10.31 Mis Actividades (syllabus)

**Rol:** todos · **Rutas:** `/mis-actividades`, `/mis-actividades/<id>`,
`POST /mis-actividades/<id>/iniciar`

Las actividades que el docente te asignó, con su **código** (`U1-A1` … `U4-A6`), unidad, componente
(DOCENCIA / PRACTICA / AUTONOMO), **puntaje**, **disponibilidad** (según la ventana de fechas) y
**estado de la asignación**: `PENDIENTE · EN_CURSO · ENTREGADA · REVISADA`.

* **Iniciar** una actividad marca el arranque y queda en tu línea de tiempo (`INICIO_ACTIVIDAD`).
* El detalle muestra **Instrucciones**, **Evidencia solicitada por el docente**, los **eventos** de
  esa actividad y las **evidencias** ya generadas (con accesos a *Ver* y *Preparar captura*).
* La pantalla ofrece también un botón *JSON* (`?formato=json`) para ver la misma información en
  formato de datos.

Pantallas descritas en las 📷 CAPTURAS 3 y 4.

### 10.32 Mis Evidencias

**Rol:** todos · **Rutas:** `/mis-evidencias`, `POST /mis-evidencias/nueva`,
`/mis-evidencias/<id>`, `POST /mis-evidencias/<id>/finalizar`,
`POST /mis-evidencias/<id>/version`, `/mis-evidencias/<id>/captura`,
`/mis-evidencias/<id>/imprimible`

El **módulo de evidencias verificables** convierte tu trabajo contable en un documento con:

* **Código único** con formato `CONT1-B-2026-XXXXXXXX` (`CONT1` curso, `B` paralelo, año y sufijo).
* **Contenido real de tu empresa**: plan de cuentas, asientos, mayor y balance (según el tipo:
  `PLAN_CUENTAS · DIARIO · MAYOR · BALANCE · INTEGRAL`).
* **Huella SHA-256** calculada al finalizar, que permite detectar cualquier cambio posterior.
* **Estados:** `BORRADOR · FINAL · INVALIDADA` y la marca **"Modificada después"** si el contenido
  cambió respecto de la huella.
* **Versiones:** cada corrección registra una versión nueva con su **motivo** (queda en la auditoría
  y en la línea de tiempo).
* **Vistas de entrega:** *Preparar captura* (vista limpia sin menú lateral, con botón
  *Imprimir o guardar*) e *Imprimible / PDF* (HTML listo para imprimir; PDF si el servidor tiene
  `reportlab` instalado).
* **Aislamiento:** la evidencia de otro compañero devuelve 404/403 aunque escribas su id en la URL.

Pantalla descrita en la 📷 CAPTURA 11.

### 10.33 Actividades del Syllabus (docente)

**Rol:** Docente y Administrador · **Rutas:** `/docente/actividades`,
`/docente/actividades/<id>`, `POST /docente/actividades/nueva`,
`POST /docente/actividades/<id>/asignar`, `POST /docente/actividades/<id>/estado`

Gestión completa de las actividades del syllabus: **crear**, **editar por código** (upsert),
**asignar** a todos o a estudiantes concretos, **abrir/cerrar** la ventana de disponibilidad y
**seguir el avance** del paralelo.

* Filtros por **unidad**, **componente**, **estado**, **estudiante** y **búsqueda por código o
  título**.
* Tabla con **Asignadas / Entregadas / En curso / Avance** por actividad y la etiqueta **Modificada**
  cuando la evidencia de un estudiante cambió después de finalizarla.
* Cada operación se registra en la auditoría (`CREAR_ACTIVIDAD`, `ASIGNAR_ACTIVIDAD`,
  `CAMBIAR_ESTADO_ACTIVIDAD`).

Pantallas descritas en las 📷 CAPTURAS 17 y 18. Las **6 actividades de Contabilidad I** del
seed son: `U1-A1` Taller asistido (DOCENCIA, 10 pts), `U2-A2` Práctica de laboratorio
(PRACTICA, 12 pts), `U2-A3` Fichero autónomo de cuentas (AUTONOMO, 10 pts), `U3-A4` Jornalización
integral (DOCENCIA, 10 pts), `U3-A5` Portafolio autónomo (AUTONOMO, 10 pts) y `U4-A6` Trabajo
autónomo integrador (AUTONOMO, 10 pts).

### 10.34 Evidencias de Estudiantes (docente)

**Rol:** Docente y Administrador · **Rutas:** `/docente/evidencias`,
`/docente/evidencias/<id>`

Listado de **todas las evidencias del curso** con filtros por **estudiante, actividad, estado,
búsqueda y "Solo modificadas"**, y las columnas **Código, Estudiante, Actividad, Tipo, Estado,
Versiones, Generada, Integridad**. El detalle abre el contenido real leído del aula del estudiante
(cuentas, asientos, mayor, balance) con el mismo formato que ve el estudiante, más la huella y el
histórico de versiones. Pantalla descrita en la 📷 CAPTURA 19.

### 10.35 Verificar Código de Evidencia (docente)

**Rol:** Docente y Administrador · **Ruta:** `/docente/evidencias/verificar?codigo=...`

Verificador por **código**: dice si la evidencia existe, de quién es, a qué actividad corresponde,
su huella SHA-256 y si el contenido **cambió después** de finalizarla. Si el código no existe,
responde *"No existe una evidencia con ese código."* Pantalla descrita en la 📷 CAPTURA 20.

### 10.36 Seguimiento de Accesos (docente)

**Rol:** Docente y Administrador · **Rutas:** `/docente/accesos`,
`/docente/accesos/exportar.csv`

Panel de seguimiento del trabajo del curso, con **KPIs** (estudiantes, con al menos una sesión,
eventos en total, evidencias generadas, tiempo de actividad), **filtros** por estudiante, fechas,
actividad, estado y paralelo, la tabla **Resumen de accesos por estudiante** y la **exportación a
CSV** con los filtros aplicados.

Los eventos que alimentan el panel y la línea de tiempo son:
`LOGIN`, `LOGOUT`, `INICIO_ACTIVIDAD`, `CREAR_CUENTA`, `MODIFICAR_CUENTA`, `CREAR_ASIENTO`,
`INTENTO_FALLIDO_ASIENTO`, `CONSULTA_DIARIO`, `CONSULTA_MAYOR`, `GENERACION_BALANCE`,
`CORRECCION_ASIENTO`, `GENERACION_ESTADO_FINANCIERO`, `CREACION_EVIDENCIA` y `CONSULTA_ACTIVIDAD`.
Cada sesión guarda **inicio, fin, duración, IP y navegador**.

Pantallas descritas en las 📷 CAPTURAS 13 y 14.

### 10.37 Mis Estudiantes: ficha y libros en solo lectura

**Rol:** Docente y Administrador · **Rutas:** `/docente/estudiantes`, `/docente/estudiantes/<id>`,
`/docente/estudiantes/<id>/linea-tiempo`, y las cinco vistas de libros:
`/cuentas`, `/diario`, `/mayor`, `/balance`, `/estados`.

La **ficha del estudiante** reúne: datos (nombre, usuario, correo, matrícula, paralelo, estado),
**historial de accesos** (sesiones con inicio, fin, duración, IP y estado), **línea de tiempo**,
**actividades asignadas**, **evidencias generadas**, **intentos de evaluación** y el **resumen de sus
libros** (cuentas, asientos, líneas de detalle, totales Debe/Haber, si cuadra, empresa y período).

Las vistas de libros abren **el archivo del estudiante en modo solo lectura**
(`file:...?mode=ro`): nunca se pueden modificar desde aquí. Todas muestran la etiqueta
**[Solo lectura]** y un distintivo de estado: **[Balance cuadrado]**, **[Balance descuadrado]**,
**[Sin movimientos todavía]** o **[Sin aula contable]**; si el aula está vacía, aparece un aviso
explicativo en lugar de un error. Pantallas descritas en las 📷 CAPTURAS 15 y 16.

### 10.38 Estudiantes sin ingresar

**Rol:** Docente y Administrador · **Ruta:** `/docente/sin-ingresar`

La nómina de estudiantes matriculados que **nunca iniciaron sesión**. Sirve para las dos primeras
semanas: son los estudiantes a los que hay que reenviarles las credenciales antes de que la
inactividad se vuelva un problema de calificación.

### 10.39 Panel de Analítica Docente

**Rol:** Docente y Administrador · **Ruta:** `/docente/panel`

* Estudiantes registrados, intentos totales y completados, **nota promedio** general.
* **Errores frecuentes** y su distribución (correcto / parcial / incorrecto).
* **Promedio por nivel** (gráfico de barras) para detectar en qué nivel se concentra la dificultad.
* **Progreso individual** por estudiante (intentos y promedio).
* Listado de **simulaciones del curso** con su nivel, duración y puntuación mínima.

Es la herramienta para decidir qué tema reforzar antes de avanzar al siguiente nivel. Pantalla
descrita en la 📷 CAPTURA 21.

### 10.40 Tutor Contable IA

**Rol:** todos · **Rutas:** `/tutor/`, `POST /tutor/preguntar`

Acompaña el razonamiento contable sin dar la respuesta de inmediato. Escribes tu pregunta (o usas las
de ejemplo) y eliges el **nivel de ayuda**:

1. **Orientación** — por dónde empezar a razonar.
2. **Pista** — un paso concreto hacia la solución.
3. **Explicación conceptual** — el fundamento contable (partida doble, costo de ventas, IVA,
   arqueo, depreciación…).
4. **Solución guiada** — disponible siempre que no estés en Modo Examen.

```
📷 CAPTURA 29 · "Tutor Contable IA"
Rol: todos                 Ruta: /tutor/
+------------------------------------------------------------------------+
|  Tutor Contable IA                                                     |
|  [ ¿Por qué esta cuenta se debita?                          ] [Enviar] |
|  Nivel de ayuda: ( ) Orientación  ( ) Pista  ( ) Explicación conceptual |
|                  ( ) Solución guiada                                    |
|  --------------------------------------------------------------------  |
|  TUTOR: En un asiento de venta al contado, Caja General aumenta un      |
|  activo, por eso va al DEBE...                                          |
|  Preguntas de ejemplo: ¿Qué significa este saldo? · ¿Cómo afecta esta   |
|  transacción al inventario? · auditar descuadres e inconsistencias      |
+------------------------------------------------------------------------+
Qué mirar:  el nivel de ayuda elegido: en Modo Examen las pistas y la
            solución quedan restringidas para preservar la evaluación.
```

El Tutor entiende las preguntas con o sin tildes y responde en español, citando los datos reales del
sistema (por ejemplo, la tasa de IVA vigente la lee de la configuración, no la inventa).

### 10.41 Centro de Reportes

**Rol:** todos · **Rutas:** `/reportes/`, `/reportes/exportar/csv/<tipo>`,
`/reportes/exportar/excel/<tipo>`, `/reportes/exportar/balance-csv`,
`/reportes/exportar/diario-csv`, `/reportes/exportar/inventario-csv`,
`/reportes/imprimible/<tipo>`

**16 informes**, cada uno en tres formatos (**CSV**, **Excel** y **versión imprimible para PDF**):

| Categoría | Informes |
|---|---|
| **Contabilidad** | Libro Diario · Libro Mayor · Balance de Comprobación |
| **Operaciones** | Registro de Ventas · Registro de Compras · Registro de Servicios Prestados |
| **Inventarios** | Inventario y Existencias · Kardex Consolidado |
| **Tesorería y Cartera** | Movimientos de Caja · Movimientos Bancarios · Cartera de Cuentas por Cobrar · Cuentas por Pagar a Proveedores |
| **Estados Financieros** | Estado de Resultados · Estado de Situación Financiera · Estado de Flujo de Efectivo |
| **Académico** | Resultados Académicos de Simulaciones |

```
📷 CAPTURA 30 · "Centro de Reportes"
Rol: todos                 Ruta: /reportes/
+------------------------------------------------------------------------+
|  Centro de Reportes                                                    |
|  Contabilidad          Libro Diario | Libro Mayor | Balance de Compr.   |
|  Operaciones           Ventas | Compras | Servicios                    |
|  Inventarios           Inventario y Existencias | Kardex consolidado    |
|  Tesorería y Cartera   Caja | Bancos | Cartera | Cuentas por pagar      |
|  Estados Financieros   Resultados | Situación | Flujo de efectivo       |
|  Académico             Resultados académicos de las simulaciones       |
|  Por cada informe: [ CSV ] [ Excel ] [ Versión imprimible / PDF ]        |
+------------------------------------------------------------------------+
Qué mirar:  el formato que necesitas: CSV para procesar, Excel para
            calificar y la versión imprimible para el anexo en PDF.
```

* **CSV:** se abre en Excel directamente (incluye BOM para acentos).
* **Excel (XLSX):** hoja con encabezado de empresa, período y fecha de trabajo, columnas ajustadas.
* **Versión imprimible:** página limpia lista para *Imprimir → Guardar como PDF*; el balance de
  comprobación incluye el control de integridad (sumas y saldos).

### 10.42 Administración del Sistema

**Rol:** solo Administrador · **Rutas:** `/admin/`, `/admin/usuarios`, `/admin/impuestos`,
`/admin/auditoria`

**a) Parámetros & Configuración:** actualiza la **fecha de trabajo** de la simulación (debe estar
dentro del período abierto) y los **datos de la empresa**: razón social, nombre comercial, RUC,
dirección, teléfono, correo, actividades (comercial y de servicios) y **método de valoración por
defecto** (Promedio o FIFO). Muestra los **períodos contables** con su estado (ABIERTO / CERRADO),
los **parámetros del sistema** vigentes y los últimos registros de auditoría.

**b) Gestión de Usuarios:** crear usuarios con nombre de usuario, contraseña (se almacena con hash),
nombre completo, correo, **rol** y paralelo; lista de usuarios con su rol y estado.

**c) Parámetros Tributarios:** edición de cada impuesto (nombre, porcentaje, tipo, cuenta contable y
estado). Aquí se ajustan las tasas cuando la cátedra lo requiera; el resto del sistema las toma
automáticamente, incluidas las retenciones de compras y ventas.

**d) Auditoría & Trazabilidad:** registro **inmutable** de cada acción con usuario, módulo, acción,
registro afectado, **valor anterior** y **valor nuevo**, **dirección IP**, **agente** y **herramienta
ejecutada** (por ejemplo `AgenteContable` / `create_sale`). Filtrable por módulo. Es la evidencia de
control interno y de auditoría para el curso.

```
📷 CAPTURA 31 · "Auditoría & Trazabilidad"
Rol: Administrador         Ruta: /admin/auditoria
+------------------------------------------------------------------------+
|  Auditoría & Trazabilidad        Filtro por módulo [ Todos ▾ ]          |
|  Fecha y hora  Usuario  Módulo  Acción  Registro  Valor anterior        |
|  Valor nuevo  IP  Agente  Herramienta                                   |
|  ...                                                                    |
|  (registro inmutable: no se edita ni se borra desde la interfaz)        |
+------------------------------------------------------------------------+
Qué mirar:  el par "valor anterior → valor nuevo" y la herramienta usada:
            es la prueba de control interno de cada operación.
```

---

### 10.43 Casos de los libros (§61)

**Rol:** todos · **Rutas:** `/casos-libros`, `/casos-libros/<codigo>`,
`POST /casos-libros/<codigo>/intentos`, `POST /casos-libros/<codigo>/enviar`,
`/casos-libros/mis-intentos`

El **banco de casos prácticos con las cifras de los libros de la asignatura**: **19 casos**
(`C61.01` … `C61.19`) cargados como **datos** en la base de control, no escritos en el código.

Cada caso tiene su **ficha obligatoria** antes de poder activarse: **fuente** (libro y edición),
**página con doble numeración** (impresa y PDF), **año**, **unidad** del syllabus, **dificultad**
(BÁSICO / INTERMEDIO / AVANZADO), **tipo de verificación** (ASIENTO / TOTALES / ECUACIÓN / MECÁNICA),
enunciado, datos entregados por la fuente, **asientos esperados**, saldos finales y las
**correcciones de erratas** con su razón.

* **Estados de validación del caso:** `VERIFICADO · VERIFICADO_CON_RESERVA · SIN_SOLUCION ·
  CON_ERRATA · PARCIAL_CON_ERRATA`. Los casos **SIN_SOLUCION** se cargan como *práctica sin solución
  visible*: se resuelven, pero el sistema no publica la respuesta.
* **Resolución:** el estudiante abre el caso, **inicia un intento** (con control de intentos
  máximos) y envía su respuesta como **líneas de asiento** (cuenta, Debe, Haber) o como
  **totales/ecuación**, según el tipo de verificación del caso.
* **Puntaje:** la misma rúbrica del simulador (cuentas 40 / posición 30 / importes 20 / cuadre 10),
  con umbrales de CORRECTO (85), PARCIALMENTE CORRECTO (50) y el aviso de que la verificación es
  **mecánica y no oficial** cuando la fuente no trae solución.
* **Mis intentos:** historial de intentos del estudiante con caso, número de intento, fecha,
  puntaje, resultado y tipo de verificación.
* **Avisos de fidelidad:** la lista y la ficha muestran las advertencias de trazabilidad (IVA y
  retenciones solo como cuenta/línea de cálculo, marco normativo de la fuente, páginas sin texto,
  datos reconstruidos y erratas corregidas) para que nadie confunda un ejemplo del libro con
  normativa vigente.

```
📷 CAPTURA 32 · "Casos prácticos de los libros · §61"
Rol: todos                 Ruta: /casos-libros
+------------------------------------------------------------------------+
|  Casos prácticos de los libros (§61)                                   |
|  Resumen del banco: total · activos · sin solución · con erratas        |
|  Filtros: Unidad [Todas▾] Validación [Todas▾] Fuente [Todas▾] Buscar    |
|  --------------------------------------------------------------------  |
|  Caso      Fuente  Unidad  Validación              Intentos  Acciones   |
|  C61.01    U2      2       VERIFICADO              0         [ Abrir ]  |
|  C61.05    U3      3       SIN_SOLUCION            0         [ Abrir ]  |
|  ...                                                                    |
|  Fuente · Edición / año · Correlación de páginas · Páginas sin texto     |
|  (§62.4)                                                              |
+------------------------------------------------------------------------+
Qué mirar:  el estado de validación: te dice si el caso trae solución en el
            libro, si se carga corregido o si es práctica sin solución.
Qué hacer:  abre la ficha, revisa la fuente y la página, inicia el intento y
            envía tu asiento. El sistema te dice qué criterio falló.
```

### 10.44 Banco de casos y trazabilidad (docente)

**Rol:** Docente y Administrador · **Rutas:** `/docente/casos-libros`,
`/docente/casos-libros/<codigo>`, `POST /docente/casos-libros/<codigo>/activar`,
`POST /docente/casos-libros/tasas`

Panel de administración del banco de casos y de las **reglas de trazabilidad §62**:

* **Banco completo** (también los casos no visibles para el estudiante) con fuente y páginas,
  estado de validación, **correcciones registradas** e intentos.
* **Activar / desactivar** un caso (un caso incompleto no se puede activar: la ficha es obligatoria
  antes de publicarlo).
* **Tarifas demostrativas editables (§62.2):** el IVA de los ejemplos, los aportes al IESS, la
  participación de trabajadores, el impuesto a la renta implícito y los porcentajes de depreciación
  (edificios, maquinaria, muebles, computación) se muestran con su valor vigente y se pueden fijar
  como **configuración académica** — nunca como afirmación de la fuente.
* **Reglas §62** (9 en total, 8 de trazabilidad de fuentes) y **erratas del catálogo semilla**, con
  su aviso correspondiente.
* **Intentos del curso:** caso, estudiante, número de intento, puntaje, resultado, si la verificación
  es **oficial** y la fecha.

```
📷 CAPTURA 33 · "Panel docente · Banco de casos §61 y trazabilidad §62"
Rol: Docente / Administrador            Ruta: /docente/casos-libros
+------------------------------------------------------------------------+
|  Banco de casos §61 y trazabilidad §62                                 |
|  Resumen del banco · Reglas §62 · Erratas del catálogo · Fuentes        |
|  Tarifas demostrativas (editables)                                     |
|   Tarifa            Fuente                 Valor        [ Fijar ]      |
|   IVA de los ejemplos (U4 2024)   ...      15 %                        |
|   Aporte personal al IESS         ...      9,45 %                      |
|   Depreciación de edificios       ...      5 %                         |
|  Banco completo                                                        |
|   Caso   Fuente y páginas   Estado   Correcciones   Activo   Intentos   |
|   C61.01 U2 imp. 140–142    VERIFIC. —             [x]      3           |
|  Intentos del curso                                                    |
|   Caso   Estudiante  Intento  Puntaje  Resultado  Oficial  Fecha        |
+------------------------------------------------------------------------+
Qué mirar:  la columna "Oficial": distingue una verificación contra la
            solución de la fuente de una verificación mecánica.
Qué hacer:  antes de activar un caso para el curso, revisa su ficha, su
            fuente y sus correcciones de erratas.
```

---

## 11. Un aula por estudiante: el aislamiento de los datos

El simulador nació como **una sola empresa compartida**. Con un curso completo escribiendo en la
misma empresa, el Libro Diario se mezcla y no hay forma de calificar. La solución aplicada es
**una base de datos SQLite por estudiante** (su **aula**) más una **base de control** compartida para
lo académico.

```
base de CONTROL (compartida)            aula del estudiante (1 archivo por estudiante)
├── usuarios, roles, cursos, matrículas ├── su empresa y su plan de cuentas
├── actividades, asignaciones           ├── sus asientos, diario, mayor y balance
├── sesiones_usuario, eventos           ├── su inventario, cartera y tesorería
├── evidencias, versiones, índice       ├── sus documentos y estados financieros
├── casos de los libros (§61) y reglas  └── sus períodos, impuestos y simulaciones
├── aulas_estudiante (qué aula es suya)
└── auditoría
```

**Qué se guarda en cada lado**

| Contenido | Base de control | Aula del estudiante |
|---|:--:|:--:|
| Usuarios, roles, cursos, matrículas | ✅ | — |
| Actividades del syllabus y asignaciones | ✅ | — |
| Evidencias, versiones, índice de evidencias | ✅ | — |
| Sesiones, eventos, auditoría | ✅ | — |
| Casos de los libros (§61) y reglas §62 | ✅ | — |
| Empresa, cuentas, asientos, libros, estados | — | ✅ |
| Inventario, cartera, tesorería, documentos, impuestos | — | ✅ |

**Cómo se resuelve la base según quien entra** (en `models.py`):

| Función | Devuelve |
|---|---|
| `get_db_control()` | La base de control: autenticación, administración y todo lo académico |
| `get_db_contable()` | El **aula del estudiante en sesión**; sin sesión de estudiante, la base de control |

Reglas de uso:

1. El **estudiante** ve y escribe únicamente en **su** aula contable; el aislamiento es por
   construcción: los datos de un compañero **no están en su archivo**.
2. **Docente, Administrador y Auditor** trabajan en la base de control y, para ver los libros de un
   estudiante, abren expresamente **su aula en modo solo lectura** (`file:...?mode=ro`).
3. Cualquier URL con el id de otro estudiante (actividad, evidencia, aula) devuelve **404/403**: el
   sistema no confía en que la URL esté bien escrita.
4. Las cuentas de **demostración** (`admin`, `docente`, `estudiante`, `auditor`) siguen operando sobre
   la empresa compartida: sirven para mostrar el sistema en clase y para las pruebas automáticas.

**Crear y mantener aulas**

```bash
python database/crear_aula.py --plantilla                  # (re)construye la plantilla
python database/crear_aula.py ealcivar4002 --paralelo B     # creación de una aula
python database/crear_aula.py --todas                       # creación para toda la nómina
python database/crear_aula.py ealcivar4002 --plan incompleto # plan de cuentas a completar
python database/importar_nomina.py --paralelo B --curso CONT1-AUD-ONLINE-P2-2026
```

Cada aula clonada de la plantilla llega **sin operaciones** (asientos, ventas y compras en cero) y
con las **6 actividades del syllabus** asignadas. La plantilla tiene 46 cuentas, 20 productos,
10 clientes, 8 proveedores, 22 parámetros tributarios y 1 período.

> **Nunca sobreescribas un aula con trabajo**: antes de clonar, el sistema cuenta
> `asientos`/`ventas`/`compras` del destino y se niega si hay movimientos (existe una opción
> explícita para forzarlo). Reejecutar la importación de la nómina no puede borrarle el avance a un
> estudiante. Detalle de diseño: `docs/DISENO_MULTIESTUDIANTE.md`.

---

## 12. Reglas contables y validaciones

El sistema aplica y comunica estas reglas; ninguna operación que las viole se contabiliza.

| Regla | Comportamiento |
|---|---|
| **Partida doble obligatoria** | Si Total Debe ≠ Total Haber se rechaza: *“El asiento no cuadra: Total Debe ($100.00) != Total Haber ($90.00). Diferencia: $10.00.”* |
| **Al menos dos cuentas por asiento** | Se exige un mínimo de dos líneas |
| **Importe mayor que cero** | No se admiten asientos por valor nulo |
| **Cantidad > 0 y precio/costo ≥ 0** | Validación en ventas y compras |
| **Stock suficiente** | *“Stock insuficiente para ‘Arroz Flor…’. Existencias: 40, solicitadas: 60.”* |
| **Período abierto** | *“El periodo contable esta CERRADO: no se pueden registrar nuevas operaciones.”* |
| **Fecha dentro del período** | *“La fecha 2026-08-01 esta fuera del periodo abierto ‘Período Académico Abril 2026’ (2026-04-01 a 2026-04-30).”* |
| **Factura no duplicada** | Control de documentos repetidos de proveedor |
| **Cuenta activa** | Las cuentas inactivas no se ofrecen en los formularios |
| **Cliente / proveedor válido** | *“Cliente no encontrado.”* / *“Proveedor no encontrado.”* |
| **Cobro/pago no mayor al saldo** | *“El monto a cobrar ($800.00) no puede ser mayor al saldo pendiente ($420.00).”* |
| **No se borran asientos contabilizados** | Solo **reversión** con contra-asiento |
| **Tasas tributarias configurables** | Si no hay configuración, el cálculo se rechaza (nunca se inventa un porcentaje) |
| **Dos bases distintas en las retenciones** | La **retención de Renta** se calcula sobre el valor del bien o servicio (sin IVA); la **retención de IVA** sobre el IVA de la factura |
| **La deuda del proveedor es el neto** | La cuenta por pagar (y el pago de contado) es **factura − retenciones**: lo retenido se declara y paga al SRI, no al proveedor |
| **La venta con retención se cobra por el neto** | Lo que el cliente agente de retención retiene queda **a favor de la empresa**; el asiento cuadra por el neto |
| **Concepto de retención válido** | Un concepto de retención desconocido se rechaza; solo se ofrecen los del catálogo del SRI |
| **Fidelidad de las fuentes (§62)** | Las erratas de los libros **no se replican**: se carga la versión corregida, con el valor del libro, el corregido y la razón |
| **Práctica sin solución visible (§62.5)** | Un caso cuya fuente no publica solución se resuelve, pero el sistema **no publica** la respuesta |
| **Operaciones atómicas** | Si algo falla, no queda ningún registro a medias |
| **Agentes sin acceso directo a la base** | Los agentes solo operan a través de herramientas estructuradas |

**Regla de oro de la partida doble (para consultar al Tutor IA):**

* Se **DEBITAN**: aumentos de Activo, aumentos de Gastos y Costos, disminuciones de Pasivo y
  Patrimonio.
* Se **ACREDITAN**: aumentos de Pasivo, aumentos de Patrimonio, aumentos de Ingresos, disminuciones
  de Activo.

---

## 13. Fecha de trabajo y períodos

El simulador **no usa el reloj de tu computador** para fechar las operaciones: usa la **fecha de
trabajo** de la simulación (por defecto **2026-04-30**), lo que permite reproducir un período
académico completo aunque estés practicando en otra fecha real.

* El **período activo** es *Período Académico Abril 2026* (2026-04-01 a 2026-04-30), en estado
  **ABIERTO**.
* La fecha de trabajo se cambia en *Administración → Parámetros & Config*, siempre **dentro del
  período abierto**; si escribes una fecha fuera de rango, el sistema lo informa y no la aplica.
* Si el período se **cierra** (módulo Cierre contable), el sistema deja de aceptar operaciones
  ordinarias y muestra el período como CERRADO.
* Para volver al estado inicial en cualquier momento: `python database/seed_data.py`.

---

## 14. Modo Examen y evaluación

**Modo Práctica (por defecto).** El estudiante recibe pistas progresivas, explicaciones y la solución
guiada del Tutor IA; la retroalimentación es inmediata y detallada.

**Modo Examen** (la simulación de Nivel 4 está configurada como examen). Durante un examen:

* La **solución inmediata queda desactivada**.
* Las **pistas quedan restringidas**: el Tutor responde con orientación general y no entrega la
  solución ni el paso clave.
* Se **registran los intentos**, el tiempo y los resultados para el docente.
* La puntuación se calcula con la misma rúbrica (40/30/20/10 − 5 por pista) y se exige la
  **puntuación mínima** definida en la simulación (70 puntos en Nivel 1, 75 en Nivel 2, 80 en Niveles
  3 y 4).

El docente configura duración, número de ejercicios, dificultad, intentos y puntuación mínima al
crear la simulación, y puede generar nuevos escenarios coherentes para su curso con el **Agente
Generador de Casos**.

**Actividades del syllabus y casos de los libros:** el docente también controla la **ventana de
disponibilidad** (fechas de apertura y cierre y estado ABIERTA/CERRADA) y el **modo práctica** por
actividad (que oculta las ayudas). En el banco de casos §61, la verificación es **mecánica y no
oficial** cuando el libro no publica la solución: la pantalla lo advierte antes de que el resultado
se use como calificación.

---

## 15. Agentes de IA y API interna

El sistema está preparado para trabajar con **agentes especializados** que operan exclusivamente a
través de herramientas estructuradas (nunca escriben en la base con texto libre).

| Agente | Responsabilidad |
|---|---|
| **Orquestador** | Analiza la solicitud e identifica la intención para enrutarla al agente correcto |
| **Contable** | Cuentas, débitos, créditos, partida doble, diario, mayor, estados financieros |
| **Inventarios** | Entradas, salidas, stock, Kardex, costo de ventas, FIFO y promedio |
| **Tributario** | Consulta la configuración tributaria real (nunca inventa porcentajes) |
| **Auditor** | Detecta descuadres, duplicidades, inconsistencias, fechas incorrectas y anomalías |
| **Tutor** | Explicaciones, pistas, preguntas y retroalimentación con andamiaje progresivo |
| **Evaluador** | Analiza intentos, errores, puntuaciones y nivel de dominio |
| **Generador de Casos** | Crea escenarios coherentes según los parámetros del docente |

**Cómo usarlos desde el sistema:** escribe tu consulta en el **Tutor Contable IA**; el Orquestador
decide qué agente responde.

**API interna (JSON)** — 35 endpoints, todos los módulos aceptan `?formato=json`:

| Endpoint | Método | Para qué |
|---|---|---|
| `/api/health` | GET | Estado del sistema, período, fecha de trabajo y número de tablas |
| `/api/dashboard` | GET | Indicadores y estado de resultados |
| `/api/accounts` · `/api/accounts/<id>/balance` | GET | Plan de cuentas y saldo de una cuenta |
| `/api/journal/validate` · `/api/journal/create` | POST | Validar y crear asientos |
| `/api/products` · `/api/inventory` · `/api/inventory/<id>` · `/api/inventory/alerts` | GET | Inventario y alertas |
| `/api/sales` · `/api/purchases` · `/api/services` | POST/GET | Registrar ventas, compras y servicios |
| `/api/customers` · `/api/customers/<id>/history` | GET | Clientes y su historial |
| `/api/suppliers` · `/api/suppliers/<id>/history` | GET | Proveedores y su historial |
| `/api/receivables` · `/api/payables` | GET | Cartera y obligaciones |
| `/api/collections` · `/api/payments` | POST | Cobros y pagos |
| `/api/treasury` | GET | Cajas y bancos con saldos reales |
| `/api/taxes` · `/api/taxes/calculate` | GET/POST | Configuración y cálculo tributario |
| `/api/statements?tipo=…` | GET | Estados financieros |
| `/api/documents` · `/api/documents/<id>` | GET | Documentos fuente |
| `/api/simulations` · `/api/simulations/<id>` · `/api/evaluate` | GET/POST | Casos y evaluación |
| `/api/progress/<estudiante_id>` | GET | Progreso del estudiante |
| `/api/periods` | GET | Períodos y fecha de trabajo |
| `/api/audit` | GET | Trazabilidad |
| `/api/search?q=…` | GET | Buscador global agrupado |
| `/api/tools` | GET | **37 herramientas** disponibles para los agentes |

Ejemplo: `GET /api/tools` devuelve `disponibles: 37, faltantes: []`, lo que confirma que las 37
herramientas existen y son invocables. Las rutas de gestión académica (actividades, evidencias,
accesos, estudiantes, casos §61, libros del estudiante) aceptan `?formato=json` o la cabecera
`Accept: application/json` para devolver su contenido como datos.

---

## 16. Datos de demostración

La base se genera con `python database/seed_data.py` e incluye:

* Empresa **Comercial y Servicios Nueva Esperanza S.A.** (RUC 1792345678001) con sus dos actividades.
* **46 cuentas** contables jerárquicas (25 deudoras y 21 acreedoras), **22 parámetros tributarios**,
  **1 caja** y **2 bancos**.
* **20 productos** de primera necesidad con stock, mínimos, máximos y proveedor principal.
* **10 clientes**, **8 proveedores** y **5 servicios**.
* Asiento de **apertura de saldos iniciales** + **cartera inicial** por cliente y proveedor.
* Operaciones del período **Abril 2026** ejecutadas por los servicios reales: compras de contado y a
  crédito (con sus retenciones), ventas de contado, por transferencia y a crédito, servicios
  facturados, cobros de cartera, pagos a proveedores, gastos operacionales, depósito bancario,
  arqueo de caja con faltante, notas bancarias de débito y crédito, depreciación, provisión de
  incobrables y compensación del IVA.
* **37 asientos contabilizados**, **31 documentos fuente**, **6 ventas**, **5 compras** y
  **49 movimientos** de inventario.
* **4 simulaciones** y **19 casos** del simulador con solución verificada.
* **6 actividades del syllabus** (`U1-A1` … `U4-A6`) y el **banco de 19 casos de los libros (§61)**
  con sus **9 reglas §62**.
* **14 tipos de comprobante del SRI** y **23 reglas** documentales.

**Estado de integridad del período entregado:** total débitos = total créditos = **$92.778,50**;
total saldo deudor = total saldo acreedor = **$74.724,21**; **Activo $63.541,05 = Pasivo +
Patrimonio $63.541,05 (diferencia $0,00)**; utilidad del período **$750,67**; **0 asientos
descuadrados**.

**Nómina de ejemplo:** la base de control incluye las cuentas de demostración más la nómina del
curso (60 estudiantes con paralelo B, cada uno con su aula). Los datos de la nómina y las
credenciales **no se versionan en el repositorio**: viven en la carpeta de la asignatura y en
`database/aulas/` (ignorada por Git).

> Recuerda: son datos **de demostración** con fines académicos; las tasas tributarias son
> configurables y no constituyen una afirmación sobre la normativa vigente.

---

## 17. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| No abre `http://127.0.0.1:5000` | El servidor no está corriendo | Ejecuta `python app.py` y espera el mensaje *“Servidor Flask disponible…”* |
| *“Address already in use”* | Ya hay otro servidor en el puerto 5000 | Cierra el proceso anterior (`taskkill /PID <pid> /F`) o cambia el puerto en `app.py` |
| *“ModuleNotFoundError: flask”* | Dependencias no instaladas | `pip install -r requirements.txt` (o activa el entorno virtual `.venv`) |
| *“no such table: …”* | Base de datos sin inicializar | `python database/seed_data.py` (y `python database/cargar_casos_libros.py` para el banco §61) |
| *“Credenciales incorrectas o usuario inactivo”* | Usuario o contraseña mal escritos, o cuenta inactiva | Verifica usuario/correo y contraseña; el docente restablece la contraseña con la importación de la nómina (`--reset-passwords`) |
| *“El periodo contable esta CERRADO…”* | Se ejecutó el cierre del período | Regenera los datos en una base de práctica: `python database/seed_data.py` |
| *“La fecha … esta fuera del periodo abierto”* | La fecha usada no pertenece al período | Cambia la **fecha de trabajo** en Administración o usa una fecha dentro del período |
| *“El asiento no cuadra…”* | Debe ≠ Haber | Revisa la diferencia que indica el mensaje y corrige la línea con el error |
| *“Stock insuficiente…”* | No hay existencias suficientes | Registra primero una **compra** del producto |
| *“No existe configuración tributaria activa…”* | Falta el impuesto en la configuración | El Administrador debe crearlo/activarlo en *Parámetros Tributarios* |
| La compra retiene un porcentaje que no esperabas | El **concepto de la compra** o la condición del proveedor (contribuyente especial / RIMPE) determina la retención | Revisa el concepto y la condición del proveedor; usa `SIN_RETENCION` si la operación no genera retención |
| *“El comprobante no se emitió: revisa los puntos marcados en rojo.”* | El documento incumple una regla del catálogo del SRI | Lee la regla y su severidad en el punto marcado (o consulta el catálogo en `/documentos/catalogo`) |
| Mi evidencia dice **“Modificada después”** | El trabajo contable cambió después de finalizar la evidencia | Genera una **nueva versión** (con el motivo) o una **evidencia nueva**; la huella anterior no se puede “reparar” |
| *“No existe una evidencia con ese código.”* | El código está mal escrito o no es de este curso | Copia el código completo con el formato `CONT1-B-2026-XXXXXXXX` |
| *“No hay libros que mostrar.”* | El estudiante todavía no tiene aula o su aula está vacía | Es un aviso, no un error: verifica que su aula se haya creado (`crear_aula.py`) y que haya registrado asientos |
| *“Nunca ingresó”* en el panel del docente | El estudiante no ha iniciado sesión | Reenvía las credenciales iniciales por el aula virtual |
| *404 / 403* al abrir una actividad o evidencia | La actividad/evidencia es de otro estudiante, o tu rol no la puede ver | Usa tus propios enlaces; si eres docente, entra desde *Mis Estudiantes* |
| Página en blanco o sin estilos | El navegador bloqueó el CDN | Recarga con `Ctrl + F5`; el sistema funciona igual, con estilo base |
| Quiero volver todo al estado inicial | Datos modificados por las prácticas | `python database/seed_data.py` (borra y regenera la base de control) |
| Quiero verificar que todo está bien | Control de integridad | `python -m pytest tests -q` y revisar el **Balance de Comprobación** |

---

## 18. Preguntas frecuentes

**¿Puedo usar mis propios productos, clientes y servicios?**
Sí: agrégalos desde Clientes, Proveedores y el panel de Administración; los productos se administran
en el catálogo (módulo Productos) y el catálogo de servicios desde la base de datos
(`catalogo_servicios`).

**¿Qué pasa si me equivoco en un asiento ya contabilizado?**
Registra una **reversión** desde el Libro Diario. El sistema crea el contra-asiento y conserva ambos
para la trazabilidad; nunca se borra información.

**¿Por qué mi venta no generó costo de ventas?**
Revisa el método elegido: con **FIFO** el costo se toma de los lotes más antiguos y con **Promedio**
del costo promedio ponderado. Ambos generan el asiento `5.1.01` contra `1.1.06`.

**¿Por qué el estado de situación financiera muestra una diferencia?**
Solo puede ocurrir si existe un asiento descuadrado o una cuenta mal clasificada. Revisa el módulo
**Ajustes**, el **Balance de Comprobación** y el aviso de *asientos descuadrados* del Dashboard.

**¿Por qué la venta no me depositó el total en la caja?**
Porque el cliente es **agente de retención** y la empresa **sufrió** la retención: entra el **neto** y
lo retenido queda a favor de la empresa (cuenta de retenciones). Si no querías retención, registra la
venta sin marcar la casilla del agente.

**¿El sistema guarda quién hizo cada cosa?**
Sí. La **Auditoría** guarda usuario, acción, módulo, registro, valor anterior, valor nuevo, IP, agente
y herramienta; y el **seguimiento de accesos** guarda sesiones, eventos, actividades y evidencias.

**¿Cómo sé qué nivel de simulador me corresponde?**
Empieza por el Nivel 1 y avanza cuando obtengas 85 puntos o más. El **Panel de Analítica Docente**
del profesor muestra los promedios por nivel del curso.

**¿Cuál es la diferencia entre una actividad del syllabus y un caso de los libros?**
La **actividad del syllabus** es el entregable de la asignatura: tiene fechas, puntaje y una
**evidencia** asociada a tu trabajo real en el simulador. Los **casos de los libros (§61)** son los
ejercicios con las cifras del libro de texto: se resuelven enviando el asiento, los totales o la
ecuación, y su solución puede no estar publicada.

**¿Puedo exportar los libros?**
Sí, desde el **Centro de Reportes** en CSV, Excel o versión imprimible/PDF.

**¿El Tutor IA me da la respuesta?**
Depende del nivel de ayuda que elijas y del modo: en **práctica** entrega explicación y solución
guiada; en **examen** solo orientación.

**¿Se pierde algo si cierro el navegador?**
No: todo se guarda en SQLite. Al volver a entrar, tus registros y resultados siguen ahí (tus libros en
tu aula, tus evidencias e intentos en la base de control).

---

## 19. Buenas prácticas

**Para el docente**

1. **Primer día:** verifica la nómina (`importar_nomina.py`), reparte las credenciales iniciales y
   confirma en **Seguimiento de Accesos** que todos ingresaron; usa **Estudiantes sin ingresar** para
   perseguir a los que faltan.
2. **Antes de abrir una actividad:** revisa su ficha (fechas, puntaje, evidencia requerida,
   intentos) y pásala a **ABIERTA**; ciérrala al cumplirse el plazo.
3. **Cada clase:** mira la **línea de tiempo** de dos o tres estudiantes (no de todos) para detectar
   errores repetidos: es más rápido que revisar capturas.
4. **Al calificar:** verifica el **código** de la evidencia y la marca de integridad **antes** de
   poner la nota; una evidencia “Modificada después” se califica con una nueva versión.
5. **Cierre de semana:** exporta el **CSV de accesos** filtrado por fechas y guárdalo con el paquete
   `exportar_evidencias.py` (XLSX + CSV) como evidencia de la semana.
6. **Antes de cada grupo nuevo:** regenera los datos de la empresa demostrativa y revisa que las
   aulas de los estudiantes estén **sin operaciones**.
7. **No reinicies el servidor de producción mientras se está editando el código:** se levanta con
   archivos a medio guardar. Reinicia cuando el cambio esté terminado y corre
   `deploy/verificar_despliegue.py`.
8. **Publicación:** cambia las contraseñas de demostración y define una `SECRET_KEY` propia antes de
   exponer el sistema en Internet.

**Para el estudiante**

1. Antes de registrar cualquier operación, pregunta: **¿qué cuentas intervienen, de qué naturaleza
   son, aumentan o disminuyen, y cuál va al Debe y cuál al Haber?**
2. No olvides el efecto del **inventario perpetuo**: en cada venta hay dos asientos (ingreso/cobro y
   costo de ventas).
3. Verifica cada tanto: **Balance de Comprobación** (sumas y saldos) y **Situación Financiera**
   (`Activo = Pasivo + Patrimonio`).
4. Registra la **cartera** y la **tesorería** en el mismo período: los cobros y pagos también deben
   quedar contabilizados.
5. Antes del cierre, completa los **ajustes** (depreciación, provisión, IVA) y recién entonces cierra
   el período.
6. **Inicia la actividad** el día que empiezas a trabajar y **genera la evidencia** cuando termines;
   no la dejes para el final del plazo: si algo falla, no te quedará tiempo de corregir.
7. **Guarda tu código de evidencia** (`CONT1-B-2026-XXXXXXXX`): es tu comprobante de entrega.

---

## 20. Glosario

| Término | Significado |
|---|---|
| **Asiento contable** | Registro de una operación con líneas en Debe y Haber |
| **Debe / Haber** | Columnas de la partida doble; deben sumar siempre lo mismo |
| **Partida doble** | Principio por el cual todo cargo tiene un abono de igual valor |
| **Mayorización** | Traslado de los movimientos del diario a cada cuenta del mayor |
| **Balance de comprobación** | Prueba de que las sumas y saldos del mayor cuadran |
| **Kardex** | Registro detallado de entradas, salidas y saldos de un producto |
| **Costo de ventas** | Costo de las mercaderías entregadas, reconocido en la venta |
| **Promedio ponderado** | Método de valoración con costo promedio recalculado por entrada |
| **FIFO** | Método de valoración: primero entrado, primero salido |
| **Cartera** | Cuentas por cobrar a clientes |
| **CxP** | Cuentas por pagar a proveedores |
| **Arqueo de caja** | Conteo físico del efectivo contra el saldo contable |
| **Conciliación bancaria** | Comparación del saldo bancario y el saldo contable |
| **Ajuste** | Asiento de fin de período (depreciación, provisión, acumulaciones) |
| **Cierre contable** | Cancelación de ingresos/gastos y determinación del resultado |
| **Débito fiscal / Crédito tributario** | IVA cobrado en ventas / IVA pagado en compras |
| **Retención** | Porcentaje retenido de un tributo y declarado al fisco |
| **Agente de retención** | Quien retiene el impuesto al pagar (contribuyente especial) |
| **Contribuyente especial** | Contribuyente con tarifas de retención reducidas (10 %/20 % de IVA) |
| **RIMPE** | Régimen Simplificado para Emprendedores y Negocios Populares |
| **NIIF** | Normas Internacionales de Información Financiera |
| **Fecha de trabajo** | Fecha simulada con la que se registran las operaciones |
| **Rúbrica** | Criterios y puntajes con que se evalúa un asiento |
| **Aula** | La base de datos contable propia de cada estudiante |
| **Actividad del syllabus** | Entregable de la asignatura con fechas, puntaje y evidencia requerida |
| **Asignación** | El vínculo entre una actividad y un estudiante (PENDIENTE · EN_CURSO · ENTREGADA · REVISADA) |
| **Evidencia** | Informe del trabajo contable del estudiante con código y huella SHA-256 |
| **Huella SHA-256** | Sello del contenido: si cambia, la evidencia queda marcada como modificada |
| **Línea de tiempo** | Secuencia de eventos del estudiante (accesos, asientos, intentos, evidencias) |
| **Intento** | Cada vez que se resuelve un caso del simulador o de los libros (§61) |
| **Caso de los libros (§61)** | Ejercicio con las cifras del libro de texto y su fuente citada |
| **Trazabilidad (§62)** | Reglas que garantizan que los ejemplos citen su fuente y corrijan sus erratas |
| **Modo Examen** | Configuración que restringe pistas y solución para preservar la evaluación |

---

## 21. Anexos

### A. Rutas de la aplicación

Todas las rutas del sistema, agrupadas por área. Los métodos `GET/POST` indican que la misma ruta
sirve la pantalla y procesa el formulario.

**Portada, sesión y manual**

| Ruta | Métodos |
|---|---|
| `/login` | GET,POST |
| `/logout` | GET |
| `/` | GET |
| `/manual` | GET |
| `/manual/fuente` | GET |

**Dashboard**

| Ruta | Métodos |
|---|---|
| `/dashboard` | GET |

**Contabilidad Central**

| Ruta | Métodos |
|---|---|
| `/contabilidad/cuentas` | GET,POST |
| `/contabilidad/ajustes` | GET,POST |
| `/contabilidad/cierre` | GET,POST |
| `/contabilidad/cuentas/<int:account_id>/editar` | POST |
| `/contabilidad/diario` | GET,POST |
| `/contabilidad/mayor` | GET |
| `/contabilidad/diario/<int:asiento_id>/revertir` | POST |
| `/contabilidad/balance` | GET |

**Operaciones Comerciales**

| Ruta | Métodos |
|---|---|
| `/compras/nueva` | GET,POST |
| `/compras/desglose` | POST |
| `/compras/` | GET |
| `/compras/<int:compra_id>` | GET |
| `/ventas/nueva` | GET,POST |
| `/ventas/desglose` | POST |
| `/ventas` | GET |
| `/ventas/<int:venta_id>` | GET |
| `/servicios` | GET,POST |

**Inventario & Kardex**

| Ruta | Métodos |
|---|---|
| `/inventarios/kardex` | GET |
| `/inventarios/kardex/<int:producto_id>` | GET |
| `/inventarios/` | GET |
| `/inventarios/productos` | GET |
| `/inventarios/stock` | GET |

**Tesorería & Cartera**

| Ruta | Métodos |
|---|---|
| `/documentos/<int:doc_id>/anular` | POST |
| `/documentos/catalogo` | GET |
| `/documentos/<int:doc_id>` | GET |
| `/documentos/` | GET |
| `/documentos/nuevo` | GET,POST |
| `/documentos/soporte` | GET |
| `/clientes` | GET,POST |
| `/cuentas-pagar` | GET,POST |
| `/cuentas-cobrar` | GET,POST |
| `/proveedores` | GET,POST |
| `/impuestos/` | GET |
| `/bancos/movimiento` | POST |
| `/bancos` | GET |
| `/caja` | GET,POST |
| `/caja/movimiento` | POST |
| `/conciliacion` | GET,POST |
| `/caja/regularizar/<int:arqueo_id>` | POST |

**Informes Financieros NIIF**

| Ruta | Métodos |
|---|---|
| `/estados-financieros/` | GET |
| `/estados-financieros/situacion-financiera` | GET |
| `/estados-financieros/flujo-efectivo` | GET |
| `/estados-financieros/resultados` | GET |

**Simulador y evaluaciones**

| Ruta | Métodos |
|---|---|
| `/evaluaciones` | GET |
| `/simulador` | GET |
| `/simulador/<int:simulacion_id>/jugar` | GET |
| `/simulador/<int:simulacion_id>/iniciar` | GET |
| `/simulador/evaluar` | POST |
| `/docente/panel` | GET |

**Actividades del syllabus (estudiante y docente)**

| Ruta | Métodos |
|---|---|
| `/docente/actividades/<int:actividad_id>/asignar` | POST |
| `/docente/actividades/<int:actividad_id>/estado` | POST |
| `/mis-actividades/<int:actividad_id>` | GET |
| `/docente/actividades` | GET |
| `/docente/actividades/<int:actividad_id>` | GET |
| `/mis-actividades/<int:actividad_id>/iniciar` | POST |
| `/mis-actividades` | GET |
| `/docente/actividades/nueva` | POST |

**Evidencias verificables (estudiante y docente)**

| Ruta | Métodos |
|---|---|
| `/mis-evidencias/<int:evidencia_id>/captura` | GET |
| `/mis-evidencias/<int:evidencia_id>` | GET |
| `/docente/evidencias/<int:evidencia_id>` | GET |
| `/docente/evidencias` | GET |
| `/mis-evidencias/<int:evidencia_id>/finalizar` | POST |
| `/mis-evidencias/<int:evidencia_id>/imprimible` | GET |
| `/mis-evidencias` | GET |
| `/mis-evidencias/nueva` | POST |
| `/mis-evidencias/<int:evidencia_id>/version` | POST |
| `/docente/evidencias/verificar` | GET |

**Panel docente: accesos, estudiantes y libros**

| Ruta | Métodos |
|---|---|
| `/docente/accesos` | GET |
| `/docente/accesos/exportar.csv` | GET |
| `/docente/estudiantes/<int:estudiante_id>/balance` | GET |
| `/docente/estudiantes/<int:estudiante_id>/cuentas` | GET |
| `/docente/estudiantes/<int:estudiante_id>` | GET |
| `/docente/estudiantes/<int:estudiante_id>/diario` | GET |
| `/docente/estudiantes/<int:estudiante_id>/estados` | GET |
| `/docente/estudiantes/<int:estudiante_id>/linea-tiempo` | GET |
| `/docente/estudiantes/<int:estudiante_id>/mayor` | GET |
| `/docente/estudiantes` | GET |
| `/docente/sin-ingresar` | GET |

**Tutor Contable IA**

| Ruta | Métodos |
|---|---|
| `/tutor/preguntar` | POST |
| `/tutor/` | GET |

**Centro de Reportes**

| Ruta | Métodos |
|---|---|
| `/reportes/exportar/csv/<tipo>` | GET |
| `/reportes/exportar/excel/<tipo>` | GET |
| `/reportes/exportar/inventario-csv` | GET |
| `/reportes/exportar/diario-csv` | GET |
| `/reportes/exportar/balance-csv` | GET |
| `/reportes/` | GET |
| `/reportes/imprimible/<tipo>` | GET |

**Administración del Sistema**

| Ruta | Métodos |
|---|---|
| `/admin/auditoria` | GET |
| `/admin/` | GET,POST |
| `/admin/impuestos` | GET,POST |
| `/admin/usuarios` | GET,POST |

**Otras rutas**

| Ruta | Métodos |
|---|---|
| `/casos-libros` | GET |
| `/casos-libros/<codigo>` | GET |
| `/casos-libros/<codigo>/enviar` | POST |
| `/casos-libros/<codigo>/intentos` | POST |
| `/casos-libros/mis-intentos` | GET |
| `/docente/casos-libros` | GET |
| `/docente/casos-libros/<codigo>` | GET |
| `/docente/casos-libros/<codigo>/activar` | POST |
| `/docente/casos-libros/tasas` | POST |

**Recursos estáticos**

| Ruta | Métodos |
|---|---|
| `/static/<path:filename>` | GET |

### B. Herramientas de los agentes (37)

```text
get_chart_of_accounts        get_account                  get_account_balance
validate_journal_entry       create_journal_entry         reverse_journal_entry
close_accounting_period      get_product                  get_inventory
register_inventory_entry     register_inventory_exit       calculate_weighted_average
calculate_fifo               calculate_cost_of_goods_sold create_sale
create_purchase              create_service_transaction   create_receivable
create_payable               register_collection          register_payment
get_customer_balance         get_supplier_balance         get_cash_balance
get_bank_balance             reconcile_bank               get_tax_configuration
calculate_tax                generate_trial_balance       generate_income_statement
generate_balance_sheet       generate_cash_flow           create_simulation_case
evaluate_student_attempt     generate_feedback            get_student_progress
audit_transaction
```

Se consultan en `GET /api/tools`, que debe devolver `faltantes: []`.

### C. Modelo de datos

**Seguridad y organización:** `roles`, `usuarios`, `empresas`, `periodos`, `parametros`,
`cursos`, `matriculas`, `aulas_estudiante`.

**Contabilidad:** `cuentas`, `asientos`, `detalle_asientos`.

**Impuestos:** `impuestos`.

**Inventarios:** `productos`, `movimientos_inventario`, `kardex_lotes`.

**Terceros:** `clientes`, `proveedores`.

**Operaciones:** `ventas`, `detalle_ventas`, `compras`, `detalle_compras`,
`catalogo_servicios`, `transacciones_servicios`.

**Cartera y tesorería:** `cuentas_cobrar`, `cobros`, `cuentas_pagar`, `pagos`, `cajas`,
`movimientos_caja`, `arqueos_caja`, `bancos`, `movimientos_bancarios`, `conciliaciones_bancarias`.

**Documentos y trazabilidad:** `documentos_fuente`, `auditoria`, `tipos_documento`,
`reglas_documento` (catálogo del SRI).

**Simulación académica:** `simulaciones`, `casos_simulacion`, `intentos_estudiante`,
`detalle_intentos`.

**Módulo educativo (base de control):** `actividades`, `asignaciones_actividad`,
`sesiones_usuario`, `eventos_estudiante`, `evidencias`, `versiones_evidencia`, `evidencias_indice`.

**Banco de casos de los libros (§61):** `casos_libros_fuentes`, `casos_libros`,
`casos_libros_trazabilidad`, `casos_libros_reglas`, `casos_libros_intentos` (se crean con
`python database/cargar_casos_libros.py`).

Son **48 tablas de negocio** en la base de control (más la tabla interna `sqlite_sequence`, que
`/api/health` cuenta: informa **49**). Cada **aula** de estudiante tiene las tablas contables y su
propio período; el detalle de dónde vive cada dato está en
[sección 11](#11-un-aula-por-estudiante-el-aislamiento-de-los-datos).

### D. Comandos del docente y del administrador

| Comando | Para qué |
|---|---|
| `python app.py` | Arrancar el sistema en modo desarrollo |
| `python serve.py` | Servir 24/7 (waitress); `HOST=0.0.0.0 PORT=8080` para red |
| `python database/seed_data.py` | Regenerar la empresa demostrativa |
| `python database/crear_aula.py --plantilla` | Reconstruir la plantilla de las aulas |
| `python database/crear_aula.py <usuario> --paralelo B` | Crear/repoblar el aula de un estudiante |
| `python database/crear_aula.py --todas` | Crear las aulas de toda la nómina |
| `python database/importar_nomina.py --paralelo B --curso <curso>` | Importar la nómina y crear usuarios, matrículas y aulas |
| `python database/importar_nomina.py ... --reset-passwords` | Restablecer contraseñas iniciales |
| `python database/seed_actividades.py --todos` | Cargar/actualizar las actividades del syllabus |
| `python database/cargar_casos_libros.py` | Cargar el banco de casos §61 y las reglas §62 |
| `python database/parametros_tributarios_sri.py --todas-las-aulas` | Actualizar los porcentajes tributarios |
| `python deploy/cambiar_credenciales.py` | Cambiar las contraseñas de demostración |
| `python deploy/multiaula/exportar_evidencias.py` | Paquete XLSX + CSV de evidencias del curso |
| `python deploy/verificar_despliegue.py --url <url>` | Verificar un despliegue (módulos, API, manual y seguridad) |
| `python docs/build_manual.py` | Regenerar este manual en HTML desde su fuente Markdown |

### E. Verificación rápida del sistema

```bash
python -m pytest tests -q                                            # suite de pruebas automáticas
python database/seed_data.py                                        # regenerar datos de demostración
python database/cargar_casos_libros.py --listar                      # estado del banco de casos §61
python deploy/verificar_despliegue.py --url http://127.0.0.1:8080    # verificación de despliegue
curl http://127.0.0.1:5000/api/health                                # estado del sistema
python docs/build_manual.py                                          # regenerar este manual
```

**Qué cubre la suite automática** (archivos de `tests/`):

| Archivo | Foco |
|---|---|
| `test_accounting_engine.py` | Partida doble, mayor, balance, estados |
| `test_operations.py` | Ventas, compras, servicios, tesorería y cartera |
| `test_statements_evaluation_api.py` | Estados financieros, evaluaciones y API |
| `test_rutas_y_flujos.py` | Rutas principales, login, manual y flujos de extremo a extremo |
| `test_documentos_sri.py` | Catálogo, emisión, validación y anulación de comprobantes |
| `test_retenciones_compras.py` | Retenciones de Renta e IVA en compras |
| `test_retenciones_ventas.py` | Retenciones que el cliente practica en ventas y servicios |
| `test_actividades_evidencias.py` | Actividades del syllabus, evidencias, huella y aislamiento |
| `test_accesos_docente.py` | Sesiones, eventos y panel de accesos |
| `test_docente_libros_estudiante.py` | Ficha y libros del estudiante en solo lectura |
| `test_aulas_aislamiento.py` | Aislamiento real entre dos estudiantes (acceso cruzado) |

Un cambio está listo cuando la suite pasa completa, el manual se regenera y
`deploy/verificar_despliegue.py` no reporta fallos.

**Este manual se sirve dentro del sistema:**

* Página: **`/manual`** (generada desde `docs/MANUAL_DE_USUARIO.md`).
* Fuente descargable: **`/manual/fuente`**.
* Para imprimir o guardar en PDF: botón *Imprimir / Guardar PDF* de la barra superior del manual.

---

*Manual de usuario del Simulador Integral de Sistema Contable · Servicios y Comercialización de
Productos · Comercial y Servicios Nueva Esperanza S.A. · Versión 2.0 · Documento académico con datos
de demostración.*
