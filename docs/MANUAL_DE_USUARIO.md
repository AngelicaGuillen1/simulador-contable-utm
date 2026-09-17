# Manual de Usuario
## Simulador Integral de Sistema Contable
### Servicios y Comercialización de Productos — *Comercial y Servicios Nueva Esperanza S.A.*

> Versión del sistema: 1.0 · Período de demostración: **Abril 2026** · Fecha de trabajo por defecto: **2026-04-30**
> Documento generado para uso académico. Todos los datos son de **demostración**.

---

## Índice

1. [¿Qué es este sistema?](#1-qué-es-este-sistema)
2. [Requisitos e instalación](#2-requisitos-e-instalación)
3. [Cómo ejecutar y detener el sistema](#3-cómo-ejecutar-y-detener-el-sistema)
4. [Usuarios, contraseñas y roles](#4-usuarios-contraseñas-y-roles)
5. [Recorrido guiado de 15 minutos](#5-recorrido-guiado-de-15-minutos)
6. [Mapa de navegación](#6-mapa-de-navegación)
7. [Módulos del sistema](#7-módulos-del-sistema)
   1. [Dashboard](#71-dashboard)
   2. [Plan de cuentas](#72-plan-de-cuentas)
   3. [Libro Diario](#73-libro-diario)
   4. [Libro Mayor](#74-libro-mayor)
   5. [Balance de Comprobación](#75-balance-de-comprobación)
   6. [Ajustes contables](#76-ajustes-contables)
   7. [Cierre contable](#77-cierre-contable)
   8. [Ventas](#78-ventas)
   9. [Servicios](#79-servicios)
   10. [Compras](#710-compras)
   11. [Productos](#711-productos)
   12. [Kardex](#712-kardex)
   13. [Existencias y alertas](#713-existencias-y-alertas)
   14. [Caja y arqueos](#714-caja-y-arqueos)
   15. [Bancos](#715-bancos)
   16. [Conciliación bancaria](#716-conciliación-bancaria)
   17. [Clientes](#717-clientes)
   18. [Cuentas por cobrar](#718-cuentas-por-cobrar)
   19. [Proveedores](#719-proveedores)
   20. [Cuentas por pagar](#720-cuentas-por-pagar)
   21. [Documentos fuente](#721-documentos-fuente)
   22. [Tributación](#722-tributación)
   23. [Estado de Resultados](#723-estado-de-resultados)
   24. [Estado de Situación Financiera](#724-estado-de-situación-financiera)
   25. [Estado de Flujo de Efectivo](#725-estado-de-flujo-de-efectivo)
   26. [Simulador de Casos](#726-simulador-de-casos)
   27. [Evaluaciones](#727-evaluaciones)
   28. [Panel de Analítica Docente](#728-panel-de-analítica-docente)
   29. [Tutor Contable IA](#729-tutor-contable-ia)
   30. [Centro de Reportes](#730-centro-de-reportes)
   31. [Administración](#731-administración)
8. [Reglas contables y validaciones](#8-reglas-contables-y-validaciones)
9. [Fecha de trabajo y períodos](#9-fecha-de-trabajo-y-períodos)
10. [Modo Examen y evaluación](#10-modo-examen-y-evaluación)
11. [Agentes de IA y API interna](#11-agentes-de-ia-y-api-interna)
12. [Datos de demostración](#12-datos-de-demostración)
13. [Solución de problemas](#13-solución-de-problemas)
14. [Preguntas frecuentes](#14-preguntas-frecuentes)
15. [Buenas prácticas](#15-buenas-prácticas)
16. [Glosario](#16-glosario)
17. [Anexos](#17-anexos)

---

## 1. ¿Qué es este sistema?

Es un **sistema contable educativo completo (tipo ERP académico)** que funciona en el navegador y
opera sobre una empresa simulada real: **Comercial y Servicios Nueva Esperanza S.A.**, dedicada a
dos actividades:

* **Comercial:** venta de productos de primera necesidad (arroz, azúcar, aceite, leche, harina,
  café, limpieza, higiene, bebidas y alimentos empacados).
* **Servicios:** entrega/distribución, transporte, asesoría, mantenimiento e instalación.

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
Kardex, el costo de ventas, la cartera del cliente, la caja o el banco, el IVA, los documentos
fuente, el libro diario, el libro mayor, el balance de comprobación y los estados financieros.

**¿Para quién es?** Estudiantes de Contabilidad, Auditoría, Administración, Finanzas y áreas
empresariales afines, y docentes que quieran asignar casos, evaluar automáticamente y ver analítica
del avance del curso.

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

Contenido de `requirements.txt`: Flask, Werkzeug, Jinja2, openpyxl (exportación a Excel) y pytest
(pruebas automáticas).

---

## 3. Cómo ejecutar y detener el sistema

**Ejecutar**

```bash
python app.py
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
* Comprobación de un despliegue publicado:

  ```bash
  python deploy/verificar_despliegue.py --url http://127.0.0.1:8080
  ```

**Regenerar los datos de demostración** (borra y reconstruye la base; útil para volver al estado
inicial después de una clase):

```bash
python database/seed_data.py
```

**Ejecutar las pruebas automáticas:**

```bash
python -m pytest tests -q
```

> La **fecha de trabajo** de la simulación no depende del reloj de tu computador: la controla el
> sistema desde el panel de Administración (ver [sección 9](#9-fecha-de-trabajo-y-períodos)).

---

## 4. Usuarios, contraseñas y roles

| Rol | Usuario | Contraseña | Nombre en el sistema |
|---|---|---|---|
| Administrador | `admin` | `admin123` | Ing. Marco Morales |
| Docente | `docente` | `docente123` | Dr. Carlos Mendoza |
| Estudiante | `estudiante` | `estudiante123` | Ana Lucía Morales |
| Auditor | `auditor` | `auditor123` | Lic. Roberto Vaca |

Las contraseñas se almacenan **con hash seguro** (nunca en texto plano).

### Matriz de permisos

| Módulo | Administrador | Docente | Estudiante | Auditor |
|---|:--:|:--:|:--:|:--:|
| Dashboard, libros, balance, estados financieros | ✅ | ✅ | ✅ | ✅ (solo lectura) |
| Documentos fuente y trazabilidad | ✅ | ✅ | ✅ | ✅ (solo lectura) |
| Registrar ventas, servicios, compras, cobros, pagos, tesorería, ajustes | ✅ | ✅ | ✅ | — |
| Simulador de casos y evaluaciones | ✅ | ✅ | ✅ | — |
| Panel de analítica docente | ✅ | ✅ | — | — |
| Cierre contable | ✅ | ✅ | — | — |
| Administración: usuarios, parámetros, impuestos, auditoría | ✅ | — | — | Solo auditoría (lectura) |

Si un usuario intenta entrar a un módulo sin permiso, recibe la página **403 – Acceso restringido**
con el mensaje del rol requerido y la lista de roles autorizados.

---

## 5. Recorrido guiado de 15 minutos

1. **Inicia sesión** con `estudiante / estudiante123`.
2. Entra a **Simulador de Casos** y pulsa *Iniciar* en **Nivel 1 — Básico**.
3. Lee el enunciado y el documento fuente del caso. En la tabla de líneas contables selecciona las
   cuentas, escribe los importes en **Debe** y **Haber** y añade líneas si necesitas más.
   *Si te trabas, pulsa **Pedir pista al Tutor IA** (cada pista resta 5 puntos).*
4. Pulsa **Enviar Asiento y Evaluar**. Verás tu puntuación sobre 100, la rúbrica desglosada y una
   retroalimentación concreta línea por línea.
5. Ve a **Contabilidad → Libro Diario** y localiza los asientos que generaste.
6. Ve a **Ventas → Nueva venta**, registra una venta a crédito por 20 unidades del producto que
   prefieras (forma de pago *Crédito*, 30 días) y guárdala.
7. Revisa en **Cuentas por Cobrar** que apareció el documento; registra un **cobro parcial**.
8. Revisa **Caja**, **Bancos** y **Documentos Fuente** para ver los movimientos y respaldos creados.
9. Abre **Estados Financieros → Situación Financiera**: debe aparecer el banner verde
   **“Activo = Pasivo + Patrimonio ✓”**.
10. Cierra con **Contabilidad → Balance de Comprobación**: los totales de débitos y créditos, y los
    saldos deudor y acreedor, deben coincidir.

---

## 6. Mapa de navegación

El menú lateral se organiza así:

| Sección | Módulos |
|---|---|
| **Dashboard General** | Indicadores, gráficos, alertas, actividad reciente |
| **Contabilidad Central** | Plan de Cuentas · Libro Diario · Libro Mayor · Balance de Comprobación · Ajustes Contables · Cierre de Período |
| **Operaciones Comerciales** | Ventas de Bienes · Servicios Prestados · Compras a Proveedores |
| **Inventario & Kardex** | Catálogo de Productos · Kardex (FIFO / Promedio) · Existencias & Alertas |
| **Tesorería & Cartera** | Caja & Arqueos · Cuentas Bancarias · Conciliación Bancaria · Clientes · Cuentas por Cobrar · Proveedores · Cuentas por Pagar · Documentos Fuente · Tributación |
| **Informes Financieros NIIF** | Estado de Resultados · Situación Financiera · Flujo de Efectivo |
| **Entorno Universitario & IA** | Simulador de Casos · Mis Evaluaciones · Panel Analítica Docente · Tutor Contable IA · Centro de Reportes |
| **Administración del Sistema** | Parámetros & Config · Gestión Usuarios · Parámetros Tributarios · Auditoría & Trazabilidad |

**Barra superior:** período contable activo, fecha de trabajo, buscador global (busca cuentas,
productos, clientes, asientos y simulaciones), acceso rápido al simulador y al Tutor IA, y menú del
usuario (ver resultados, ir al sistema contable, cerrar sesión).

---

## 7. Módulos del sistema

### 7.1 Dashboard

**Para qué sirve:** vista ejecutiva de la empresa simulada.

**Qué muestra**

* **Indicadores financieros:** saldo de caja, bancos, ventas de bienes, ingresos por servicios,
  inventario valorizado, cuentas por cobrar, cuentas por pagar y utilidad del período.
* **Gráficos:** evolución semanal de ventas, servicios, compras y gastos (con conmutador
  *Barras / Líneas*) y composición financiera (disponibilidad vs cartera vs inventario).
* **Alertas operativas:** stock bajo mínimo, cartera vencida (con monto), cuentas por pagar
  pendientes y **asientos descuadrados** (control permanente de la partida doble).
* **Actividad reciente:** últimos asientos contabilizados y últimos documentos fuente.
* **Inventario por categoría** (con filtro por categoría) y **cartera por estado**.
* **Resultados de simulación:** intentos, completados, promedio general y por nivel.
* **Accesos rápidos:** nueva venta, nueva compra, facturar servicio, caja, estado de resultados y
  Tutor IA.

> Todos los valores se calculan en vivo desde el libro mayor. No hay cifras decorativas.

---

### 7.2 Plan de cuentas

**Ruta:** Contabilidad → Plan de Cuentas

**Qué muestra:** las **43 cuentas** del plan contable con estructura jerárquica y clasificación en
seis grupos: **1 Activo · 2 Pasivo · 3 Patrimonio · 4 Ingresos · 5 Costos · 6 Gastos**.

Cada cuenta tiene código, nombre, **naturaleza** (deudora/acreedora), clasificación, cuenta padre,
nivel, si **acepta movimiento** y su **saldo actual calculado desde el libro mayor**.

**Cómo se usa**

* **Crear cuenta:** botón *Nueva cuenta* → código, nombre, naturaleza, clasificación, cuenta padre,
  nivel y si acepta movimiento. Ejemplo: `1.1.09 Anticipo a Proveedores`.
* **Editar cuenta:** botón de edición por fila (nombre, naturaleza, clasificación, estado activo).
* **Desactivar:** desde la edición (estado = inactivo); las cuentas inactivas no aparecen en los
  formularios de registro.
* **Buscar y filtrar:** por código, nombre, clasificación o naturaleza.

**Reglas:** el código debe ser único; una cuenta con movimientos no debería desactivarse para no
descuadrar informes históricos.

---

### 7.3 Libro Diario

**Ruta:** Contabilidad → Libro Diario

**Qué muestra:** todos los asientos con número, fecha, glosa, tipo y número de documento, módulo de
origen, usuario, y sus líneas con cuenta, **Debe**, **Haber** y referencia. Cada asiento indica su
total y si está cuadrado.

**Cómo se usa**

1. Pulsa **Nuevo asiento**.
2. Escribe **fecha** (dentro del período abierto), **glosa**, tipo y número de documento.
3. Agrega líneas: selecciona la cuenta y escribe el importe en **Debe** o en **Haber**. Usa
   *Agregar línea* para partidas con más de dos cuentas.
4. El sistema muestra en vivo los totales y la diferencia.
5. Guarda. **Si el asiento no cuadra, no se contabiliza** y recibirás un mensaje con la diferencia
   exacta (ver [sección 8](#8-reglas-contables-y-validaciones)).

**Anulación (reversión):** ningún asiento contabilizado se borra. El botón *Revertir* genera
automáticamente el **contra-asiento** con las líneas invertidas, marca el original como *REVERTIDO* y
conserva ambos en el diario para mantener la trazabilidad. El efecto contable neto de la pareja es
cero.

**Filtros:** por rango de fechas. El buscador global de la barra superior también localiza asientos
por número o glosa.

---

### 7.4 Libro Mayor

**Ruta:** Contabilidad → Libro Mayor

**Qué muestra:** para cada cuenta seleccionada (o todas las que tienen movimientos), el detalle
cronológico de fecha, número de asiento, concepto, **Debe**, **Haber** y **saldo acumulado**, más
los totales y el saldo final según la naturaleza de la cuenta.

**Cómo se usa:** selecciona la cuenta por **buscador**, por **código** o desde el filtro por
categoría, y opcionalmente acota el rango de fechas. Los saldos se recalculan en cada consulta,
por lo que siempre reflejan el estado real del diario.

---

### 7.5 Balance de Comprobación

**Ruta:** Contabilidad → Balance de Comprobación

**Qué muestra:** una línea por cuenta con movimiento: **saldo inicial**, **débitos**, **créditos**,
**saldo deudor** y **saldo acreedor**, con totales generales.

**Validación automática:** el módulo confirma dos igualdades:

* **Total Débitos = Total Créditos**
* **Total Saldo Deudor = Total Saldo Acreedor**

Si alguna no se cumple, se muestra como alerta con la diferencia exacta. Puedes filtrar por fecha de
corte.

---

### 7.6 Ajustes contables

**Ruta:** Contabilidad → Ajustes Contables

**Para qué sirve:** registrar al cierre del período las operaciones que no provienen de una
transacción comercial: **depreciación**, **amortización**, **provisiones**, **cuentas
incobrables**, **gastos e ingresos acumulados**, **gastos pagados por anticipado**, **ingresos
diferidos** y **ajuste de inventario**.

**Cómo se usa**

1. Pulsa *Nuevo ajuste* y elige el tipo (por ejemplo **Depreciación** o **Incobrables**).
2. Escribe la fecha (por defecto, la fecha de trabajo), la glosa y el monto.
3. El sistema construye el asiento con las cuentas correctas (gasto contra depreciación acumulada o
   provisión), lo contabiliza y genera su **comprobante de ajuste** en Documentos Fuente.

El listado muestra los ajustes del período. Puedes verificar el efecto en el mayor de las cuentas
`6.1.04`, `1.2.02`, `1.2.04`, `1.2.06`, `1.1.05` y `6.2.01`.

---

### 7.7 Cierre contable

**Ruta:** Contabilidad → Cierre de Período *(Administrador y Docente)*

**Proceso guiado**

```
Revisión de saldos → Ajustes → Balance ajustado → Cierre de ingresos →
Cierre de gastos → Resultado del período → Transferencia al patrimonio → Cierre del período
```

La pantalla muestra el estado de resultados y el balance antes de cerrar. Al pulsar **Ejecutar cierre**:

1. Se cancelan todas las cuentas de **ingresos** contra la cuenta de resultado `3.3.02`.
2. Se cancelan todas las cuentas de **costos y gastos** contra `3.3.02`.
3. El resultado queda reflejado en el **patrimonio**.
4. El **período se marca como CERRADO** y **no admite nuevas operaciones ordinarias**: cualquier
   intento de registrar una venta, compra, cobro o pago será rechazado con el mensaje
   *“El periodo contable esta CERRADO: no se pueden registrar nuevas operaciones.”*
5. Se genera el **comprobante de cierre** en Documentos Fuente.

> Recomendación académica: registra primero todos los ajustes (depreciación, provisión, IVA), revisa
> el balance de comprobación y **recién entonces** ejecuta el cierre.

---

### 7.8 Ventas

**Rutas:** Operaciones → Ventas de Bienes · **Nueva venta:** `/ventas/nueva`

Funciona como un **punto de venta profesional**.

**Cómo registrar una venta**

1. Elige el **cliente**.
2. Agrega líneas con **producto**, **cantidad**, **precio** y **descuento**. El sistema muestra el
   stock disponible y el subtotal por línea.
3. Elige la **forma de pago**: **Efectivo**, **Transferencia** (seleccionando el banco) o **Crédito**
   (con días de crédito).
4. Selecciona el **método de valoración del inventario** para el costo de ventas:
   **Promedio ponderado** o **FIFO**.
5. Pulsa *Registrar venta*.

**Cálculo automático:** subtotal, descuento, **IVA** (según la tabla de impuestos), total y **costo
de ventas** (según el método elegido).

**Al confirmar, el sistema actualiza simultáneamente**

| Elemento | Efecto |
|---|---|
| Inventario / Kardex | Disminuye el stock y registra el lote consumido |
| Costo de ventas | `5.1.01` al Debe contra `1.1.06` Inventario al Haber |
| Ingresos | `4.1.01` Ingresos por ventas al Haber |
| Impuestos | `2.1.02` IVA Ventas (débito fiscal) al Haber |
| Caja / Banco | Movimiento de ingreso en caja o transferencia recibida en el banco |
| Cartera | Si es a crédito, nace la **cuenta por cobrar** y sube el saldo del cliente |
| Libro Diario | Asiento de la venta + asiento del costo de ventas |
| Libro Mayor y Balance | Mayorización y saldos actualizados |
| Estados financieros | Ventas, costo de ventas y resultado del período |
| Documentos | Se emite la **factura** con su detalle |
| Auditoría | Registro de la operación con usuario, fecha y datos |

**Listado de ventas:** muestra factura, fecha, cliente, forma de pago, subtotal, IVA, total, costo de
ventas y estado.

**Validaciones:** no se permite vender sin stock suficiente ni a un cliente inválido; la cantidad
debe ser mayor que cero y el precio no negativo.

---

### 7.9 Servicios

**Ruta:** Operaciones → Servicios Prestados

**Cómo registrar un servicio**

1. Elige **cliente** y **servicio** (entrega, transporte, asesoría, mantenimiento, instalación…).
2. Indica **cantidad**, **tarifa** (viene sugerida), **descripción**, **impuestos**, **descuento**,
   **fecha** y **forma de pago**.

**Qué genera automáticamente**

* Ingreso en la cuenta **`4.1.02` Ingresos por Prestación de Servicios** (separado de la venta de
  bienes `4.1.01`).
* **Cuenta por cobrar** cuando la forma de pago es *Crédito*.
* **Movimiento de caja o bancos** cuando el cobro es inmediato.
* **Asiento contable** con IVA, **factura de servicio** y registro de auditoría.

> Los servicios no generan costo de mercaderías vendidas porque no implican salida de inventario:
> su margen es directo.

---

### 7.10 Compras

**Ruta:** Operaciones → Compras a Proveedores · **Nueva compra:** `/compras/nueva`

**Cómo registrar una compra**

1. Elige **proveedor**, escribe el **número de factura** del proveedor y elige la **forma de pago**
   (Efectivo, Transferencia o Crédito con días).
2. Agrega líneas con **producto**, **cantidad**, **costo unitario** y **descuento**.
3. Guarda.

**Al confirmar, el sistema**

* **Incrementa el inventario** y recalcula el **costo promedio ponderado** del producto, creando su
  lote para FIFO y su movimiento de Kardex (`ENTRADA_COMPRA`).
* Registra el **IVA Compras (crédito tributario)** en `1.1.07`.
* Genera la **cuenta por pagar** si la compra es a crédito (o el **egreso de caja/banco** si es de
  contado).
* Contabiliza el asiento (Inventario + IVA al Debe; Caja/Banco/CxP al Haber), emite el documento
  fuente de la factura de compra y registra la auditoría.

**Validaciones:** factura no duplicada, proveedor válido, cantidad mayor que cero y costo no
negativo.

---

### 7.11 Productos

**Ruta:** Inventario & Kardex → Catálogo de Productos

**Qué muestra:** los **20 productos** de primera necesidad con **código**, **categoría**,
**descripción**, **unidad**, **costo**, **precio de venta**, **existencias**, **stock mínimo**,
**stock máximo** y **proveedor principal**, además del valor total del inventario y el número de
alertas de stock.

**Filtros:** por categoría (Alimentos, Bebidas, Limpieza, Higiene).

> Los datos maestros de productos se administran desde el panel de Administración.

---

### 7.12 Kardex

**Ruta:** Inventario & Kardex → Kardex

**Qué muestra:** el kardex del producto seleccionado con **fecha**, **documento**,
**descripción**, **entradas**, **salidas**, **saldo**, **costo unitario** y **costo total** en cada
movimiento, más los totales de entradas/salidas, el stock final y el **valor total del inventario**.

**Métodos soportados**

* **Promedio ponderado:** el costo unitario se recalcula con cada entrada.
* **FIFO (primero entrado, primero salido):** cada salida consume los lotes más antiguos.

El método se elige por operación (al registrar la venta) y se puede analizar comparativamente
cambiando el selector del módulo.

**Regla de integridad verificada:** el saldo del Kardex coincide con las existencias del producto y
con el saldo de la cuenta contable `1.1.06 Inventario de Mercaderías`.

---

### 7.13 Existencias y alertas

**Ruta:** Inventario & Kardex → Existencias & Alertas

**Qué muestra:** el valorizado del inventario (unidades, valor al costo, valor a precio de venta y
**margen potencial**), un gráfico del valor por producto y la tabla de existencias con **semáforo**:

* 🔴 **Reponer:** existencias iguales o por debajo del **stock mínimo**.
* 🟡 **Exceso:** existencias por encima del **stock máximo**.
* 🟢 **Óptimo:** dentro del rango definido.

Cada fila enlaza al **Kardex** del producto.

---

### 7.14 Caja y arqueos

**Ruta:** Tesorería & Cartera → Caja & Arqueos

**Qué muestra:** el estado de la caja (responsable, saldo según sistema vs **saldo real del libro
mayor** y su diferencia), los movimientos de caja con signo contable y el historial de arqueos.

**Registrar un movimiento de caja**

1. Pulsa *Movimiento de caja*.
2. Elige el tipo: **Ingreso**, **Egreso**, **Depósito al banco** o **Retiro del banco**.
3. Escribe monto, concepto y comprobante (si es depósito o retiro, debes indicar la cuenta bancaria).

El sistema contabiliza el asiento correspondiente, registra el movimiento y **sincroniza el saldo de
la caja con el libro mayor**.

**Arqueo de caja**

1. Pulsa *Realizar arqueo* (o el botón de la fila de la caja).
2. El sistema muestra el **saldo contable** (libro mayor) y te pide el **saldo físico contado**.
3. Al guardar, el resultado se clasifica como **CUADRADO**, **SOBRANTE** o **FALTANTE** con la
   diferencia en valor absoluto.

**Regularizar la diferencia:** si el arqueo no cuadra, el historial ofrece el botón
**Regularizar**, que genera el asiento de ajuste y lo vincula al arqueo:

* **Faltante** → Debe `6.2.01` Gastos financieros y comisiones / Haber Caja.
* **Sobrante** → Debe Caja / Haber `4.2.01` Otros ingresos.

El arqueo queda marcado como *Regularizado* con el número de asiento, y el saldo de la caja vuelve a
coincidir con la realidad física.

---

### 7.15 Bancos

**Ruta:** Tesorería & Cartera → Cuentas Bancarias

**Qué muestra:** las **2 cuentas bancarias** (Banco Pichincha, cuenta corriente 2100874521 y Banco
Guayaquil, ahorros 10458932) con su saldo según el libro mayor, gráfico comparativo y el detalle de
movimientos con filtros por banco, estado (conciliado/pendiente) y texto.

**Registrar movimientos bancarios**

| Tipo | Efecto |
|---|---|
| **Depósito** | Aumenta el banco |
| **Transferencia recibida** | Aumenta el banco |
| **Nota de crédito** | Aumenta el banco (otros ingresos) |
| **Interés** | Aumenta el banco (otros ingresos) |
| **Transferencia emitida** | Disminuye el banco (pago) |
| **Cheque** | Disminuye el banco (pago) |
| **Nota de débito** | Disminuye el banco (gasto financiero) |
| **Comisión** | Disminuye el banco (gasto financiero) |

Cada movimiento genera su asiento, su referencia y queda disponible para la conciliación.

---

### 7.16 Conciliación bancaria

**Ruta:** Tesorería & Cartera → Conciliación Bancaria

**Cómo se usa**

1. Selecciona la **cuenta bancaria** (el sistema conoce su saldo según libros).
2. Escribe el **saldo según el extracto bancario** y, si existen, los conceptos pendientes:
   **depósitos en tránsito**, **cheques en tránsito**, **notas de débito** y **notas de crédito** no
   registradas, la **fecha de corte** y observaciones.
3. El panel de cálculo **en vivo** muestra:

```
Saldo extracto + Depósitos en tránsito − Cheques en tránsito = Saldo extracto ajustado
Saldo libros  + Notas de crédito − Notas de débito            = Saldo libros ajustado
Diferencia = |Saldo extracto ajustado − Saldo libros ajustado|
```

4. Si la diferencia es menor a 0,05 el resultado se marca **CONCILIADO** (verde); en caso contrario
   queda en **BORRADOR** (rojo) con la diferencia pendiente.
5. El historial conserva cada conciliación con su detalle aritmético y permite desplegarlo.

> Buena práctica: registra primero las notas bancarias reales en el módulo **Bancos**; recién después
> concilia, para que la diferencia llegue a cero.

---

### 7.17 Clientes

**Ruta:** Tesorería & Cartera → Clientes

**Qué muestra:** las **10 fichas** de clientes con identificación (RUC/cédula), nombre o razón
social, correo, teléfono, dirección, **límite de crédito**, días de crédito y **saldo pendiente**,
más indicadores de cartera total, cupo otorgado y cupos excedidos.

**Cómo se usa**

* **Nuevo cliente:** botón *Nuevo cliente* → identificación, nombre/razón social, correo, teléfono,
  dirección, límite y días de crédito.
* **Ficha / historial:** botón por fila que abre el historial del cliente con sus **compras**,
  **servicios**, **pagos (cobros)** y **cuentas por cobrar**, cada uno en su pestaña y con totales.
* **Filtros y orden:** búsqueda por RUC/nombre/correo/teléfono/dirección, filtro por estado, interruptor
  *solo con saldo* y orden por nombre, saldo o días de crédito.

---

### 7.18 Cuentas por cobrar

**Ruta:** Tesorería & Cartera → Cuentas por Cobrar

**Qué muestra:** cliente, documento, fecha de emisión, **vencimiento**, valor inicial, pagos, saldo y
**estado**: **PENDIENTE**, **PARCIAL**, **PAGADA** o **VENCIDA**, con semáforo de vencimientos,
banner que concilia el total del módulo y gráficos por estado y por cliente.

**Registrar un cobro**

1. Pulsa *Registrar cobro* en la fila del documento (o el botón general).
2. El importe aparece precargado con el saldo; puedes modificarlo para registrar un **abono parcial**.
3. Elige **medio de pago** (Efectivo, Transferencia, Cheque) y, si corresponde, el **banco** y el
   número de comprobante.

El sistema descuenta el saldo, actualiza el estado (PARCIAL o PAGADA), **reduce el saldo pendiente del
cliente**, genera el **comprobante de ingreso**, contabiliza el asiento (Debe Caja/Banco — Haber
`1.1.04` Cuentas por Cobrar) y registra el movimiento de tesorería.

**Validación:** no se puede cobrar un importe mayor al saldo pendiente.

---

### 7.19 Proveedores

**Ruta:** Tesorería & Cartera → Proveedores

**Qué muestra:** los **8 proveedores** con datos generales, plaza de pago y saldo pendiente, más el
historial por proveedor: **compras**, **facturas**, **pagos** y **saldo pendiente**.

**Cómo se usa:** *Nuevo proveedor* (identificación, razón social, contacto, dirección, días de
crédito) y **Ficha / historial** por fila con las pestañas de compras, pagos y obligaciones.

---

### 7.20 Cuentas por pagar

**Ruta:** Tesorería & Cartera → Cuentas por Pagar

**Qué muestra:** proveedor, factura, fecha de emisión, **vencimiento**, valor, saldo y **estado**,
con filtro de *solo vencidas*, banner de control y gráficos.

**Registrar un pago:** botón por fila (*Registrar pago*) → importe (total o **parcial**), medio de
pago, banco y número de comprobante. El sistema reduce la obligación, actualiza el estado, genera el
**comprobante de egreso**, contabiliza (Debe `2.1.01` Cuentas por Pagar — Haber Caja/Banco) y
registra el egreso en tesorería.

**Validación:** el pago no puede superar la deuda pendiente.

---

### 7.21 Documentos fuente

**Ruta:** Tesorería & Cartera → Documentos Fuente

**Qué muestra:** los documentos simulados que **respaldan cada operación**, filtrables por tipo y por
rango de fechas, con el asiento contable vinculado y su detalle estructurado.

**Tipos soportados:** factura de venta, factura de compra, factura de servicio, comprobante de
ingreso, comprobante de egreso, comprobante de caja, comprobante de cierre, nota de crédito, nota de
débito, papeleta de depósito, nota bancaria, arqueo de caja, rol de pagos, orden de compra,
comprobante de ajuste y documento interno.

El botón **Ver** abre el detalle del documento con sus datos estructurados y el asiento que generó:
es la evidencia que cierra la cadena *documento → transacción → asiento → diario → mayor → estados
financieros*.

---

### 7.22 Tributación

**Ruta:** Tesorería & Cartera → Tributación

**Qué muestra**

* La **configuración tributaria vigente**: código, nombre, porcentaje, tipo, cuenta contable y
  vigencia, con su estado activo/inactivo.
* La **determinación de IVA del período** calculada con el libro mayor: **IVA en ventas (débito
  fiscal)**, **IVA en compras (crédito tributario)**, **IVA por pagar** o **crédito a favor**, y las
  **retenciones** acumuladas.
* Las **cuentas contables** asociadas a cada impuesto.
* Una **calculadora tributaria** que ejecuta el cálculo real del sistema: base imponible + impuesto +
  total.

**Regla de oro:** el sistema **nunca inventa tasas**. Los porcentajes provienen exclusivamente de la
tabla de impuestos configurada por el Administrador. Si falta configuración para un tipo de
impuesto, la operación se rechaza con un mensaje explícito.

**Edición de tasas:** solo el rol **Administrador**, desde *Administración → Parámetros Tributarios*.

---

### 7.23 Estado de Resultados

**Ruta:** Informes Financieros NIIF → Estado de Resultados

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

---

### 7.24 Estado de Situación Financiera

**Ruta:** Informes Financieros NIIF → Situación Financiera

**Qué muestra:** **Activos corrientes y no corrientes**, **Pasivos corrientes y no corrientes** y
**Patrimonio**, en dos columnas que se apilan en móvil, con las cuentas de valuación
(depreciación acumulada y provisión de incobrables) presentadas restando.

**Validación:** en la parte superior aparece un banner que confirma la ecuación fundamental:

* **Verde:** `Activo = Pasivo + Patrimonio ✓`
* **Rojo:** alerta con la **diferencia** detectada y accesos directos a Ajustes y al Balance de
  Comprobación para localizar el problema.

Añade indicadores de apoyo: razón corriente, capital de trabajo, endeudamiento y autonomía.

> Mientras el período no se cierre, el resultado del ejercicio se incorpora automáticamente al
> patrimonio.

---

### 7.25 Estado de Flujo de Efectivo

**Ruta:** Informes Financieros NIIF → Flujo de Efectivo

**Qué muestra:** los movimientos de efectivo (caja y bancos) clasificados en **actividades de
operación**, **inversión** y **financiamiento**, con el total de cada actividad, el gráfico de
barras comparativo y la **variación neta del efectivo** del período.

---

### 7.26 Simulador de Casos

**Ruta:** Entorno Universitario & IA → Simulador de Casos

**Los cuatro niveles**

| Nivel | Nombre | Contenidos |
|---|---|---|
| **1** | Básico | Compras y ventas de contado, servicios, cobros y pagos |
| **2** | Intermedio | Crédito, inventarios, IVA, descuentos, devoluciones, bancos |
| **3** | Avanzado | Ajustes, conciliación, depreciación, provisiones, cierre, estados financieros |
| **4** | Caso Empresarial Integral | Gestión completa del período y asiento de cierre |

**Cómo resolver un caso**

1. Pulsa *Iniciar* en la simulación elegida (se crea tu **intento**).
2. Lee el **enunciado**: fecha, descripción, documento fuente, cantidades, precios, condiciones y
   forma de pago. **La solución no se muestra.**
3. Decide **qué ocurrió**, **qué cuentas intervienen**, **cuál va al Debe**, **cuál al Haber** y
   **qué monto** se registra.
4. Arma las líneas en la tabla (cuenta, Debe, Haber). Puedes agregar o quitar líneas.
5. Si necesitas ayuda, pulsa **Pedir pista al Tutor IA**: recibirás ayuda progresiva
   (orientación → pista → explicación conceptual) con **penalización de 5 puntos por pista**.
6. Pulsa **Enviar Asiento y Evaluar**.

**Puntuación (rúbrica)**

| Criterio | Puntos |
|---|---|
| Cuentas seleccionadas correctamente | 40 |
| Posición correcta en Debe/Haber | 30 |
| Importes correctos | 20 |
| Partida doble cuadrada | 10 |
| **Penalización** | **−5 por cada pista utilizada** |

**Resultado**

* **≥ 85 puntos:** CORRECTO
* **50 – 84,99:** PARCIALMENTE CORRECTO
* **< 50:** INCORRECTO

La retroalimentación es **específica**, por ejemplo:
*“La cuenta ‘Caja General’ está correctamente seleccionada, pero su movimiento debe registrarse en el
Debe porque aumenta un activo.”* Al final se muestra también el **fundamento teórico** del caso.
Quedan registrados el intento, las respuestas, los errores, las pistas, el tiempo y la puntuación.

**Casos disponibles:** los cuatro niveles suman **19 casos**. Los de Nivel 4 incluyen el asiento de
**cierre contable** del período. Cada caso se generó a partir de los **asientos reales** del sistema,
por lo que su solución esperada coincide exactamente con la contabilidad del período.

---

### 7.27 Evaluaciones

**Ruta:** Entorno Universitario & IA → Mis Evaluaciones

**Qué muestra:** todos tus intentos con simulación, fecha de inicio y fin, **puntuación**,
**tiempo utilizado** y estado; el **promedio** de los intentos completados, gráfico de evolución y el
botón para **reintentar** cada simulación. El semáforo de puntuación te indica de un vistazo tu nivel
de dominio.

El docente ve en esta misma pantalla los intentos de todos los estudiantes.

---

### 7.28 Panel de Analítica Docente

**Ruta:** Entorno Universitario & IA → Panel Analítica Docente *(Docente y Administrador)*

**Qué muestra**

* Estudiantes registrados, intentos totales y completados, **nota promedio** general.
* **Errores frecuentes** y su distribución (correcto / parcial / incorrecto).
* **Promedio por nivel** (gráfico de barras) para detectar en qué nivel se concentra la dificultad.
* **Progreso individual** por estudiante (intentos y promedio).
* Listado de **simulaciones del curso** con su nivel, duración y puntuación mínima.

Es la herramienta para decidir qué tema reforzar antes de avanzar al siguiente nivel.

---

### 7.29 Tutor Contable IA

**Ruta:** Entorno Universitario & IA → Tutor Contable IA

**Para qué sirve:** acompañar el razonamiento contable sin dar la respuesta de inmediato.

**Cómo se usa:** escribe tu pregunta (o usa las preguntas de ejemplo) y elige el **nivel de ayuda**:

1. **Orientación** — por dónde empezar a razonar.
2. **Pista** — un paso concreto hacia la solución.
3. **Explicación conceptual** — el fundamento contable (partida doble, costo de ventas, IVA,
   arqueo, depreciación…).
4. **Solución guiada** — disponible siempre que no estés en Modo Examen.

**Consultas que responde**

* “¿Por qué esta cuenta se debita?”
* “¿Qué tipo de cuenta debería revisar?”
* “¿Cómo afecta esta transacción al inventario?”
* “¿Por qué se genera costo de ventas?”
* “¿Qué significa este saldo?”
* Auditoría: *“auditar descuadres e inconsistencias”*.
* Tributaria: *“¿cuál es la tasa de IVA vigente?”* (responde con la configuración real).
* Inventarios: *“revisa el Kardex y el stock”*.
* Contable: *“dame el balance y el resultado del período”*.

**En Modo Examen** el Tutor **restringe pistas y soluciones** para preservar la validez de la
evaluación: la restricción se activa automáticamente cuando el caso pertenece a una simulación
marcada como examen.

El Tutor entiende las preguntas con o sin tildes y responde en español, citando los datos reales del
sistema.

---

### 7.30 Centro de Reportes

**Ruta:** Entorno Universitario & IA → Centro de Reportes

**16 informes**, cada uno en tres formatos (**CSV**, **Excel** y **versión imprimible para PDF**):

| Categoría | Informes |
|---|---|
| **Contabilidad** | Libro Diario · Libro Mayor · Balance de Comprobación |
| **Operaciones** | Ventas · Compras · Servicios |
| **Inventarios** | Inventario y existencias · Kardex consolidado |
| **Tesorería y Cartera** | Movimientos de caja · Movimientos bancarios · Cartera por cobrar · Cuentas por pagar |
| **Estados Financieros** | Estado de Resultados · Situación Financiera · Flujo de Efectivo |
| **Académico** | Resultados académicos de las simulaciones |

* **CSV:** se abre en Excel directamente (incluye BOM para acentos).
* **Excel (XLSX):** hoja con encabezado de empresa, período y fecha de trabajo, columnas ajustadas.
* **Versión imprimible:** página limpia lista para *Imprimir → Guardar como PDF*, con el balance de
  comprobación incluyendo el control de integridad (sumas y saldos).

---

### 7.31 Administración

**Ruta:** Administración del Sistema *(solo Administrador)*

**a) Parámetros & Configuración**

* Actualiza la **fecha de trabajo** de la simulación (debe estar dentro del período abierto) y los
  **datos de la empresa**: razón social, nombre comercial, RUC, dirección, teléfono, correo,
  actividades (comercial y de servicios) y **método de valoración por defecto** (Promedio o FIFO).
* Muestra los **períodos contables** con su estado (ABIERTO / CERRADO).
* Lista los **parámetros del sistema** vigentes.
* Expone los **últimos registros de auditoría**.

**b) Gestión de Usuarios:** crear usuarios indicando nombre de usuario, contraseña (se almacena con
hash), nombre completo, correo y **rol**; lista de usuarios con su rol y estado.

**c) Parámetros Tributarios:** edición de cada impuesto (nombre, porcentaje, tipo, cuenta contable y
estado). Aquí se ajustan las tasas cuando la cátedra lo requiera; el resto del sistema las toma
automáticamente.

**d) Auditoría & Trazabilidad:** registro **inmutable** de cada acción con usuario, módulo, acción,
registro afectado, **valor anterior** y **valor nuevo**, **dirección IP**, **agente** y **herramienta
ejecutada** (por ejemplo `AgenteContable` / `create_sale`). Filtrable por módulo. Es la evidencia de
control interno y de auditoría para el curso.

---

## 8. Reglas contables y validaciones

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
| **Operaciones atómicas** | Si algo falla, no queda ningún registro a medias |
| **Agentes sin acceso directo a la base** | Los agentes solo operan a través de herramientas estructuradas |

**Regla de oro de la partida doble (para consultar al Tutor IA):**

* Se **DEBITAN**: aumentos de Activo, aumentos de Gastos y Costos, disminuciones de Pasivo y
  Patrimonio.
* Se **ACREDITAN**: aumentos de Pasivo, aumentos de Patrimonio, aumentos de Ingresos, disminuciones
  de Activo.

---

## 9. Fecha de trabajo y períodos

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

## 10. Modo Examen y evaluación

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

---

## 11. Agentes de IA y API interna

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

**API interna (JSON)** — para integración con modelos de IA, scripts o frontends:

| Endpoint | Método | Para qué |
|---|---|---|
| `/api/health` | GET | Estado del sistema, período y fecha de trabajo |
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

Ejemplo: `GET /api/tools` devuelve `faltantes: []`, lo que confirma que las 37 herramientas
existen y son invocables.

---

## 12. Datos de demostración

La base se genera con `python database/seed_data.py` e incluye:

* Empresa **Comercial y Servicios Nueva Esperanza S.A.** (RUC 1792345678001) con sus dos actividades.
* **43 cuentas** contables jerárquicas, **6 impuestos** configurables, **1 caja** y **2 bancos**.
* **20 productos** de primera necesidad con stock, mínimos, máximos y proveedor principal.
* **10 clientes**, **8 proveedores** y **5 servicios**.
* Asiento de **apertura de saldos iniciales** + **cartera inicial** por cliente y proveedor.
* **30 operaciones del período Abril 2026** ejecutadas por los servicios reales del sistema: compras
  de contado y a crédito, ventas de contado, por transferencia y a crédito, servicios facturados,
  cobros de cartera, pagos a proveedores, gastos operacionales, depósito bancario, arqueo de caja con
  faltante, notas bancarias de débito y crédito, depreciación, provisión de incobrables y
  compensación del IVA.
* **37 asientos contabilizados**, **31 documentos fuente** y **~50 movimientos** de inventario.
* **4 simulaciones** y **19 casos** con solución verificada.

**Estado de integridad del período entregado:** total débitos = total créditos = **$92.778,50**;
total saldo deudor = total saldo acreedor = **$74.724,21**; **Activo $63.541,05 = Pasivo +
Patrimonio $63.541,05 (diferencia $0,00)**; utilidad del período **$750,67**; **0 asientos
descuadrados**.

> Recuerda: son datos **de demostración** con fines académicos; las tasas tributarias son
> configurables y no constituyen una afirmación sobre la normativa vigente.

---

## 13. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| No abre `http://127.0.0.1:5000` | El servidor no está corriendo | Ejecuta `python app.py` y espera el mensaje *“Servidor Flask disponible…”* |
| *“Address already in use”* | Ya hay otro servidor en el puerto 5000 | Cierra el proceso anterior (`taskkill /PID <pid> /F`) o cambia el puerto en `app.py` |
| *“ModuleNotFoundError: flask”* | Dependencias no instaladas | `pip install -r requirements.txt` (o activa el entorno virtual `.venv`) |
| *“no such table: …”* | Base de datos sin inicializar | `python database/seed_data.py` |
| *“El periodo contable esta CERRADO…”* | Se ejecutó el cierre del período | Regenera los datos en una base de práctica: `python database/seed_data.py` |
| *“La fecha … esta fuera del periodo abierto”* | La fecha usada no pertenece al período | Cambia la **fecha de trabajo** en Administración o usa una fecha dentro del período |
| *“El asiento no cuadra…”* | Debe ≠ Haber | Revisa la diferencia que indica el mensaje y corrige la línea con el error |
| *“Stock insuficiente…”* | No hay existencias suficientes | Registra primero una **compra** del producto |
| *“No existe configuración tributaria activa…”* | Falta el impuesto en la configuración | El Administrador debe crearlo/activarlo en *Parámetros Tributarios* |
| Página en blanco o sin estilos | El navegador bloqueó el CDN | Recarga con `Ctrl + F5`; el sistema funciona igual, con estilo base |
| El 403 aparece al entrar a Administración | Rol sin permisos | Ingresa con `admin` o usa un módulo permitido a tu rol |
| Quiero volver todo al estado inicial | Datos modificados por las prácticas | `python database/seed_data.py` (borra y regenera) |
| Quiero verificar que todo está bien | Control de integridad | `python -m pytest tests -q` (113 pruebas) y revisar el **Balance de Comprobación** |

---

## 14. Preguntas frecuentes

**¿Puedo usar mis propios productos, clientes y servicios?**
Sí: agrégalos desde Clientes, Proveedores y el panel de Administración; los productos se administran
en el catálogo (módulo Productos) y el catálogo de servicios desde la base de datos
(`catalogo_servicios`).

**¿Qué pasa si me equivoco en un asiento ya contabilizado?**
Registra una **reversión** desde el Libro Diario. El sistema crea el contra-asiento y conserva ambos
para la trazabilidad; nunca se borra información.

**¿Por qué mi venta no generó costo de ventas?**
Porque revise el método elegido: con **FIFO** el costo se toma de los lotes más antiguos y con
**Promedio** del costo promedio ponderado. Ambos generan el asiento `5.1.01` contra `1.1.06`.

**¿Por qué el estado de situación financiera muestra una diferencia?**
Solo puede ocurrir si existe un asiento descuadrado o una cuenta mal clasificada. Revisa el módulo
**Ajustes**, el **Balance de Comprobación** y el aviso de *asientos descuadrados* del Dashboard.

**¿El sistema guarda quién hizo cada cosa?**
Sí. El **Registro de Auditoría** guarda usuario, acción, módulo, registro, valor anterior, valor
nuevo, IP, agente y herramienta, además de fecha y hora.

**¿Cómo sé qué nivel de simulador me corresponde?**
Empieza por el Nivel 1 y avanza cuando obtengas 85 puntos o más. El **Panel de Analítica Docente**
del profesor muestra los promedios por nivel del curso.

**¿Puedo exportar los libros?**
Sí, desde el **Centro de Reportes** en CSV, Excel o versión imprimible/PDF.

**¿El Tutor IA me da la respuesta?**
Depende del nivel de ayuda que elijas y del modo: en **práctica** entrega explicación y solución
guiada; en **examen** solo orientación.

**¿Se pierde algo si cierro el navegador?**
No: todo se guarda en SQLite. Al volver a entrar, tus registros y resultados siguen ahí.

---

## 15. Buenas prácticas

**Para el docente**

1. Regenera la base antes de cada grupo para que todos trabajen sobre los mismos saldos iniciales.
2. Asigna el Nivel 1 y 2 como práctica guiada y el Nivel 4 como examen con puntuación mínima.
3. Revisa la **analítica docente** antes de avanzar de nivel: los errores frecuentes indican qué
   cuentas conviene reforzar.
4. Pide a los estudiantes que **justifiquen** cada débito y crédito usando el Tutor IA y que
   verifiquen siempre el **Balance de Comprobación**.
5. Usa el **registro de auditoría** para evidenciar el proceso de cada estudiante.

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

---

## 16. Glosario

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
| **NIIF** | Normas Internacionales de Información Financiera |
| **Fecha de trabajo** | Fecha simulada con la que se registran las operaciones |
| **Rúbrica** | Criterios y puntajes con que se evalúa un asiento |

---

## 17. Anexos

### A. Rutas de la aplicación (93)

**Interfaz**

```
/                            GET            Página de inicio pública
/login  /logout              GET/POST       Acceso y cierre de sesión
/dashboard                   GET            Dashboard general
/contabilidad/cuentas        GET/POST       Plan de cuentas (+ /cuentas/<id>/editar)
/contabilidad/diario         GET/POST       Libro diario (+ /diario/<id>/revertir)
/contabilidad/mayor          GET            Libro mayor
/contabilidad/balance        GET            Balance de comprobación
/contabilidad/ajustes        GET/POST       Ajustes contables
/contabilidad/cierre         GET/POST       Cierre de período (Admin/Docente)
/ventas  /ventas/nueva       GET/POST       Ventas y punto de venta
/servicios                   GET/POST       Prestación de servicios
/compras/  /compras/nueva    GET/POST       Compras y registro de facturas
/inventarios/  /productos    GET            Catálogo de productos
/inventarios/kardex[/<id>]   GET            Kardex (Promedio / FIFO)
/inventarios/stock           GET            Existencias y alertas
/caja  /caja/movimiento      GET/POST       Caja, arqueos y movimientos
/caja/regularizar/<id>       POST           Regularizar diferencia de arqueo
/bancos  /bancos/movimiento  GET/POST       Bancos y movimientos
/conciliacion                GET/POST       Conciliación bancaria
/clientes  /proveedores      GET/POST       Terceros
/cuentas-cobrar              GET/POST       Cartera y cobros
/cuentas-pagar               GET/POST       Obligaciones y pagos
/documentos/[/<id>]          GET            Documentos fuente
/impuestos/                  GET            Tributación (configuración + determinación)
/estados-financieros/resultados              GET   Estado de resultados
/estados-financieros/situacion-financiera    GET   Estado de situación financiera
/estados-financieros/flujo-efectivo          GET   Flujo de efectivo
/simulador [/<id>/iniciar|/jugar]  GET/POST  Simulador y evaluación
/evaluaciones  /docente/panel      GET       Resultados y analítica docente
/tutor/  /tutor/preguntar          GET/POST  Tutor Contable IA
/reportes/  /reportes/exportar/{csv,excel}/<tipo>  GET  Informes y exportaciones
/reportes/imprimible/<tipo>        GET       Versión imprimible / PDF
/admin/  /admin/usuarios  /admin/impuestos  /admin/auditoria   GET/POST
/manual                      GET            Este manual dentro del sistema
```

**API JSON:** 35 endpoints de `/api/*` (ver [sección 11](#11-agentes-de-ia-y-api-interna)).

### B. Herramientas de los agentes (37)

```
get_chart_of_accounts        get_account                  get_account_balance
validate_journal_entry       create_journal_entry         reverse_journal_entry
close_accounting_period      get_product                  get_inventory
register_inventory_entry     register_inventory_exit      calculate_weighted_average
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

### C. Modelo de datos (38 tablas)

**Seguridad y organización:** `roles`, `usuarios`, `empresas`, `periodos`, `parametros`,
`cursos`, `matriculas`.

**Contabilidad:** `cuentas`, `asientos`, `detalle_asientos`.

**Impuestos:** `impuestos`.

**Inventarios:** `productos`, `movimientos_inventario`, `kardex_lotes`.

**Terceros:** `clientes`, `proveedores`.

**Operaciones:** `ventas`, `detalle_ventas`, `compras`, `detalle_compras`,
`catalogo_servicios`, `transacciones_servicios`.

**Cartera y tesorería:** `cuentas_cobrar`, `cobros`, `cuentas_pagar`, `pagos`, `cajas`,
`movimientos_caja`, `arqueos_caja`, `bancos`, `movimientos_bancarios`, `conciliaciones_bancarias`.

**Documentos y trazabilidad:** `documentos_fuente`, `auditoria`.

**Simulación académica:** `simulaciones`, `casos_simulacion`, `intentos_estudiante`,
`detalle_intentos`.

### D. Verificación rápida del sistema

```bash
python -m pytest tests -q          # 113 pruebas automáticas
python database/seed_data.py       # regenerar datos de demostración
python deploy/verificar_despliegue.py --url http://127.0.0.1:8080   # verificar el despliegue
curl http://127.0.0.1:5000/api/health   # estado del sistema
```

---

*Manual de usuario del Simulador Integral de Sistema Contable · Servicios y Comercialización de
Productos · Comercial y Servicios Nueva Esperanza S.A. · Documento académico con datos de
demostración.*
