# Prácticas y evaluación con 45 estudiantes
## Simulador Integral de Sistema Contable — guía para el docente

Esta guía resuelve una pregunta concreta: **cómo hacer que un curso de 45 estudiantes realice sus
prácticas contables en el simulador, con trabajo individual, y luego entregue la evidencia en
Moodle**.

---

## 1. La restricción que define todo

El simulador trabaja sobre **una empresa simulada con un solo juego de libros por base de datos**
(no hay `empresa_id` en las tablas de operaciones: `asientos`, `ventas`, `compras`, `cajas`…).

Consecuencia práctica:

| Escenario | Qué pasa |
|---|---|
| **45 estudiantes en una sola instancia** | Todos escriben sobre los mismos asientos, el mismo stock y la misma caja: se estorban, el inventario se agota, la cartera se mezcla y no se puede saber qué hizo cada uno. **No sirve para práctica individual** |
| **45 instancias aisladas** (una empresa por estudiante) | Cada uno registra sus propias operaciones, todos parten de los mismos saldos iniciales y la evidencia es verificable y comparable. **Es lo recomendable** |
| **Solo los casos del simulador** (puntajes) | Aquí sí funcionan varios usuarios en una misma instancia: los intentos son por usuario (`intentos_estudiante`) y el docente ve la tabla de calificaciones. Pero eso cubre solo la parte de casos, no la operación libre del sistema |

---

## 2. Opciones comparadas

| Opción | Aislamiento por estudiante | Costo | Requisitos del estudiante | Esfuerzo suyo | Veredicto |
|---|---|---|---|---|---|
| **VPS propio con 45 aulas** (`deploy/multiaula/`) | ✅ Total (una base de datos por aula) | ~US$ 8–13/mes (VPS 8 GB) | Ninguno: solo abrir una URL | Bajo (2 comandos) | **Recomendado** |
| **GitHub Codespaces** (`docs/GUIA_ESTUDIANTES.md`) | ✅ Total (instancia por estudiante) | Gratis (120 h-núcleo/mes por cuenta) | Cuenta de GitHub y verificación de correo | Medio (45 cuentas) | Buena alternativa sin presupuesto |
| Una sola instancia compartida | ❌ Ninguno | ~US$ 5/mes | Ninguno | Bajo | **No recomendado** para práctica individual |
| Cada estudiante en su PC (ZIP) | ✅ Total | Gratis | Instalar Python 3.11+ (45 instalaciones) | Alto (soporte en clase) | Último recurso |

**Recomendación:** VPS con **una aula por estudiante**. Motivos:

1. El estudiante solo necesita un enlace y una contraseña: 45 enlaces, cero instalaciones.
2. Todos parten de los **mismos saldos iniciales** (la base se genera igual para cada aula), así la
   comparación de resultados es legítima.
3. Usted obtiene **las evidencias desde el servidor**: un Excel con los indicadores de las 45 aulas,
   sin depender de capturas de pantalla ni de lo que el estudiante informe.
4. Cada aula tiene **contraseña única**, así que nadie puede entrar a la de un compañero aunque
   adivine el puerto.

---

## 3. Puesta en marcha (VPS Ubuntu 22.04/24.04)

```bash
# 1. En el VPS, con el proyecto subido (paquete o git):
sudo bash deploy/multiaula/gestionar_aulas.sh instalar \
     --dominio contabilidad.utm.edu.ec \
     --correo docente@utm.edu.ec \
     --aulas 45

# 2. Asignar los nombres reales (opcional pero recomendado):
#    archivo nombres.csv con una línea por aula:  aula01;Paredes Zambrano, María José
sudo bash deploy/multiaula/gestionar_aulas.sh crear --aulas 45 --nombres nombres.csv

# 3. Ver el estado de las 45 aulas:
sudo bash deploy/multiaula/gestionar_aulas.sh estado

# 4. Entregar a cada estudiante su fila de /root/credenciales_aulas.csv
sudo bash deploy/multiaula/gestionar_aulas.sh credenciales
```

Qué crea el instalador:

| Elemento | Detalle |
|---|---|
| Código compartido | `/opt/simulador` (una copia y un solo entorno virtual: 45 instancias lo reutilizan) |
| Datos por aula | `/var/datos/aulas/aulaNN/simulator.db` (aislada, con su empresa y su período Abril 2026) |
| Servicios | Plantilla `simulador-aula@NN` (se reinicia sola si falla) |
| Acceso | `https://<dominio>:9101` … `:9145`, un puerto por aula, con el mismo certificado HTTPS |
| Claves | `/etc/simulador/aulas/aulaNN.env` con `SECRET_KEY` propia y **cookie de sesión propia** (imprescindible: las cookies no distinguen puertos) |
| Contraseñas | Una por aula, en `/root/credenciales_aulas.csv` (permisos 600) |
| Respaldos | Copia diaria de todas las aulas a las 22:00 y **evidencias automáticas los lunes a las 07:00** |

Comandos de operación diaria:

```bash
sudo bash deploy/multiaula/gestionar_aulas.sh reiniciar --aula 07        # un aula
sudo bash deploy/multiaula/gestionar_aulas.sh reestablecer --aula 07     # vuelve a los saldos iniciales
sudo bash deploy/multiaula/gestionar_aulas.sh exportar --salida /root/evidencias --min-asientos 20
```

> **Requisitos de recursos (honesto):** cada aula es un proceso independiente que ocupa ~40–50 MB.
> 45 aulas ≈ 2 GB de RAM, así que el VPS debe tener **8 GB** (Hostinger KVM 2 o equivalente) para
> trabajar con holgura; con 4 GB funciona, pero sin margen. SQLite no es un problema aquí porque
> cada aula escribe en su propio archivo.

---

## 4. Flujo de trabajo con Moodle

**En clase (2 h por práctica)**

1. El estudiante abre **su** enlace (`https://dominio:91NN`), entra con su usuario y su contraseña.
2. Resuelve la práctica: registra las operaciones indicadas y verifica el **Balance de Comprobación**
   y la **Situación Financiera** (el banner verde *Activo = Pasivo + Patrimonio ✓*).
3. Resuelve el caso del **Simulador** del nivel correspondiente (queda puntuado automáticamente).
4. Exporta su evidencia y la sube a la **tarea de Moodle**.

**Evidencia a solicitar (una sola entrega, tres archivos)**

| # | Archivo | De dónde | Qué demuestra |
|---|---|---|---|
| 1 | **Balance de comprobación** en CSV o Excel | *Centro de Reportes → Contabilidad → Balance de Comprobación* | Que sus asientos cuadran (sumas y saldos) |
| 2 | **Situación Financiera** y **Estado de Resultados** en versión imprimible (PDF) | *Centro de Reportes → Estados Financieros* → *Imprimir → Guardar como PDF* | El resultado final y la ecuación patrimonial |
| 3 | **Captura de *Mis Evaluaciones*** con el puntaje del caso | *Simulador → Mis Evaluaciones* | El caso resuelto y su calificación del sistema |

> Pídales además, cuando la práctica lo requiera, la captura del **Kardex** o del **Libro Diario
> filtrado por fecha**: es la prueba de que registraron las operaciones indicadas y no otras.

**Lo que usted hace para calificar (5 minutos por práctica, no 45 revisiones manuales)**

```bash
sudo bash deploy/multiaula/gestionar_aulas.sh exportar --salida /root/evidencias --min-asientos 20
```

Se generan dos archivos:

* `evidencias_simulador.xlsx` — hoja **Resumen** con una fila por estudiante: asientos registrados,
  asientos descuadrados, cuentas con movimiento, totales de débitos y créditos, Activo, Pasivo +
  Patrimonio, **diferencia patrimonial**, utilidad neta, caja, bancos, inventario, cartera, cuentas
  por pagar, productos bajo mínimo, intentos, **puntuación promedio**, mejor puntuación, pistas
  utilizadas, casos incorrectos y un **cumplimiento 0–3** con los umbrales que usted defina.
* `evidencias_simulador.csv` — el mismo resumen para subir a Moodle como **calificación** o para
  cruzar con la entrega de cada estudiante.

La hoja **Revision** lista automáticamente lo que requiere su atención: asientos descuadrados,
ecuación patrimonial rota, aulas sin actividad o sin base de datos.

**Ventaja de fondo:** el docente no depende de lo que el estudiante diga. Los números salen del motor
contable, no de una captura que se puede editar. La captura de Moodle es la entrega formal; el Excel
del servidor es la verificación.

---

## 5. Reprogramar, reiniciar y devolver

| Necesidad | Comando |
|---|---|
| El estudiante dañó sus datos y quiere empezar de nuevo | `gestionar_aulas.sh reestablecer --aula 07` (vuelve a los saldos iniciales y conserva su contraseña) |
| Alguien se quedó con un aula abierta o el servidor se reinició | `gestionar_aulas.sh reiniciar --aula 07` |
| Ver quién trabajó y quién no | `gestionar_aulas.sh estado` (muestra HTTP y número de asientos por aula) |
| Fin del semestre | `exportar` final + copia de `/var/datos/aulas` con `rsync` a su equipo |

---

## 6. Programa sugerido de prácticas

| # | Tema | Módulos que usan | Caso del simulador | Evidencia extra |
|---|---|---|---|---|
| 1 | Compra y venta de contado, costo de ventas | Compras, Ventas, Kardex, Caja | Nivel 1 | Captura del **Kardex** del producto vendido |
| 2 | Venta a crédito, cobro parcial y cartera | Ventas, Cuentas por Cobrar, Clientes, Bancos | Nivel 2 | Captura del **Libro Diario** de la venta y del cobro |
| 3 | IVA, retenciones y conciliación bancaria | Tributación, Bancos, Conciliación | Nivel 2 | Captura de la **determinación de IVA** del período |
| 4 | Ajustes: depreciación, provisión, arqueo con faltante | Ajustes, Caja y arqueos | Nivel 3 | Captura del **asiento de ajuste** y del arqueo |
| 5 | Cierre del período y estados financieros | Cierre, Estado de Resultados, Situación Financiera, Flujo de Efectivo | Nivel 4 (**modo examen**) | Los tres estados en PDF |

Rúbrica sugerida (10 puntos por práctica):

| Criterio | Puntos | Cómo se comprueba |
|---|---|---|
| Operaciones registradas correctamente | 4 | Cumplimiento del Excel: asientos ≥ mínimo y **0 descuadres** |
| Coherencia contable final | 3 | Ecuación patrimonial con diferencia **0** y utilidad coherente en la hoja Resumen |
| Caso del simulador resuelto | 2 | Puntuación del intento en *Mis Evaluaciones* (y en el Excel) |
| Evidencia entregada en Moodle en plazo | 1 | Los PDF/CSV subidos a la tarea |

Ajuste los umbrales con `--min-asientos` y `--permitir-descuadres`: el sistema no impone criterios
propios, usted los define.

---

## 7. Si no hay presupuesto para el VPS

Use **GitHub Codespaces**: cada estudiante abre
`https://codespaces.new/AngelicaGuillen1/simulador-contable-utm` y tiene su propio simulador en el
navegador, igualmente aislado (los pasos están en `docs/GUIA_ESTUDIANTES.md`). Costo cero, pero:

* cada estudiante necesita una **cuenta de GitHub** verificada (es el único trabajo previo real);
* la cuota gratuita es de **120 horas-núcleo al mes** por cuenta (≈60 h reales) y conviene que
  detengan el entorno al terminar cada clase;
* las evidencias son las mismas (exportaciones del Centro de Reportes), pero **usted no tiene acceso
  al servidor**: la verificación se apoya en los archivos que cada estudiante sube a Moodle. Como
  control, pídales el CSV del balance de comprobación: si sus asientos no cuadran, se nota en el
  propio archivo.

---

## 8. Lo que no recomiendo (y por qué)

* **Que los 45 entren a una sola instancia** con usuarios distintos: los libros son compartidos y la
  práctica individual se vuelve imposible de evaluar. Esto incluye "solo para la práctica libre":
  el stock se agota para todos y las cifras dejan de ser comparables.
* **Pedir capturas de pantalla como única evidencia**: no dicen si los asientos cuadran ni permiten
  comparar. Son útiles como entrega formal, no como control.
* **Instalar el sistema en 45 computadores de laboratorio**: es viable después de la primera clase,
  pero la instalación y el soporte de Python consumen la sesión completa.

---

## 9. Verificación de esta guía

Las piezas de esta guía fueron probadas de forma real en el proyecto:

* **Exportador de evidencias** (`deploy/multiaula/exportar_evidencias.py`): ejecutado sobre 3 aulas de
  prueba (2 sembradas con datos reales + 1 sin base de datos) → Excel y CSV generados, con los
  valores correctos de cada aula (37 asientos, 108 líneas, 0 descuadres, **Activo 63.541,05 =
  Pasivo + Patrimonio 63.541,05**, utilidad 750,67), la asignación de nombres por aula, los intentos
  (promedio 74,75), y el aula sin datos marcada en la hoja *Revision*.
* **Aislamiento entre aulas**: dos instancias en puertos distintos con la misma cookie de sesión
  enviada de una a otra → **rechazada (302 al login)**, gracias a `SESSION_COOKIE_NAME` por aula.
* **Gestor de aulas** (`deploy/multiaula/gestionar_aulas.sh`): sintaxis validada y plantillas
  (servicio systemd, bloques de Nginx, cron de respaldos) revisadas con valores reales.
* Suite del sistema: **113 pruebas** y **CI en verde** en GitHub.
