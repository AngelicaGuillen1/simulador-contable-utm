# Guía para estudiantes
## Simulador Integral de Sistema Contable

Bienvenido(a). Este repositorio contiene el **Simulador Integral de Sistema Contable**
(Comercial y Servicios Nueva Esperanza S.A.): un sistema contable completo con inventarios,
tesorería, cartera, impuestos, estados financieros y un simulador de casos con evaluación automática.

Hay **dos formas de abrirlo**: elija la que le resulte más cómoda.

---

## 1. Qué necesita

| Opción | Requisitos |
|---|---|
| **A. Abrir en el navegador (Codespaces)** | Solo una cuenta de GitHub. No instala nada |
| **B. Ejecutar en su computador** | Python **3.11 o superior** ([descargar](https://www.python.org/downloads/)); en Windows marque *“Add Python to PATH”* |

---

## 2. Opción A — Abrir el sistema en el navegador (sin instalar nada)

GitHub crea para usted un entorno en la nube con el simulador ya instalado.

1. Entre a **https://codespaces.new/AngelicaGuillen1/simulador-contable-utm**
   (o en el repositorio: botón verde **`Code` → pestaña `Codespaces` → `Create codespace on main`**).
2. Espere **1–3 minutos**: se instalan las dependencias, se genera la empresa simulada y se ejecuta
   la suite completa de pruebas (los mensajes aparecen en la terminal, archivo `.devcontainer/instalar.sh`).
3. En unos segundos se abre sola una **pestaña de vista previa** con el simulador.
   Si no aparece: abra el panel **`PUERTOS` / `PORTS`**, busque el puerto **5000**, pulse el icono del
   globo (*Abrir en el navegador*) y use la dirección
   `https://<nombre-del-codespace>-5000.app.github.dev`.
4. Inicie sesión con su **correo institucional** y la clave que le entregó la docente.

**Al terminar la clase:** detenga el entorno para no consumir su cuota → en GitHub:
*Codespaces → (los tres puntos del entorno) → `Stop codespace`*. Sus datos quedan guardados y al
volver a iniciarlo todo sigue igual.

> **Límites honestos de esta opción:** es un entorno **individual** — cada estudiante tiene su propia
> copia y su propia base de datos; no es una URL compartida para todo el curso. La cuenta personal
> gratuita de GitHub incluye **120 horas-núcleo al mes**; un entorno de 2 núcleos consume 2 por cada
> hora encendido, es decir unas **60 horas al mes**, suficiente para el semestre si lo detiene al
> terminar. GitHub puede pedirle una verificación de cuenta la primera vez.

---

## 3. Opción B — Ejecutar el sistema en su propio computador

**Paso 1. Descargar**

* **Descarga directa:** en el repositorio, botón verde **`Code` → `Download ZIP`**, y descomprima en
  una carpeta, por ejemplo `Documentos\SimuladorContable`.
* **Con Git:**
  ```bash
  git clone https://github.com/AngelicaGuillen1/simulador-contable-utm.git
  cd simulador-contable-utm
  ```

**Paso 2. Instalar y ejecutar** (la instalación se hace una sola vez)

*Windows (PowerShell o CMD)*
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python serve.py
```

*macOS / Linux*
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python serve.py
```

**Paso 3. Abrir en el navegador:** `http://127.0.0.1:5000`
(la primera vez tarda alrededor de un minuto porque genera los datos de demostración).

**Las siguientes veces** solo necesita activar el entorno y arrancar:
```bat
.venv\Scripts\activate
python serve.py
```
Para terminar, cierre la ventana de la terminal o pulse `Ctrl + C`.

---

## 4. Usuarios para entrar

| Rol | Usuario | Contraseña |
|---|---|---|

> Trabaje con el usuario **estudiante**. Los otros perfiles existen para que pueda ver los módulos de
> administración, de docencia y de auditoría.

---

## 5. Primer recorrido (15 minutos)

1. **Inicio de sesión** con `estudiante`.
2. **Simulador de Casos → Nivel 1 → Iniciar.** Lea el enunciado, arme el asiento (cuenta, Debe,
   Haber) y pulse **Enviar Asiento y Evaluar**. Verá su puntuación sobre 100, la rúbrica y la
   retroalimentación. Si se traba, use **Pedir pista al Tutor IA** (cada pista resta 5 puntos).
3. **Contabilidad → Libro Diario**: encuentre los asientos que acaba de generar.
4. **Ventas → Nueva venta**: registre una venta a crédito (20 unidades, 30 días) y véala reflejada en
   **Cuentas por Cobrar**, **Caja/Bancos**, **Kardex** y **Documentos Fuente**.
5. **Estados Financieros → Situación Financiera**: debe aparecer el banner verde
   **“Activo = Pasivo + Patrimonio ✓”**.
6. **Contabilidad → Balance de Comprobación**: compruebe que las sumas y los saldos cuadran.

El **manual de usuario completo** está disponible en:

* dentro del sistema: `http://127.0.0.1:5000/manual` (o el puerto que use en Codespaces);
* en el repositorio: `docs/MANUAL_DE_USUARIO.md`;
* publicado sin ejecutar nada: **https://angelicaguillen1.github.io/simulador-contable-utm/MANUAL_DE_USUARIO.html**

---

## 6. Volver a los datos iniciales

Cada vez que quiera empezar de cero (por ejemplo, antes de una práctica evaluada):

```bash
python database/seed_data.py
```

Esto **borra** sus registros y vuelve a crear la empresa simulada con el período Abril 2026 y las 30
operaciones de demostración. No afecta a los archivos del repositorio.

---

## 7. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| En Codespaces no aparece la vista previa | Abra el panel **PUERTOS**, ubique el 5000 y pulse *Abrir en el navegador*; si el puerto no aparece, ejecute en la terminal `bash .devcontainer/arrancar.sh` |
| En Codespaces dice que no tengo cuota | Detenga los entornos que no use (*Codespaces → Stop*) o use la Opción B en su computador |
| `python: command not found` (o *no se reconoce como un comando*) | Python no está instalado o no está en el PATH. Reinstálelo marcando *“Add Python to PATH”*; en macOS/Linux use `python3` |
| `ModuleNotFoundError: No module named 'flask'` | No activó el entorno virtual o no instaló las dependencias: repita el paso 2 de la Opción B |
| `Address already in use` | Ya hay un servidor abierto en ese puerto: cierre la otra terminal o use otro puerto: `PORT=8081 python serve.py` (Windows: `set PORT=8081` antes) |
| `no such table: ...` | Falta generar la base: `python database/seed_data.py` |
| El navegador no abre nada | Copie y pegue usted mismo la dirección (`http://127.0.0.1:5000`) |
| La página se ve sin colores | Recargue con `Ctrl + F5`. El sistema funciona igual sin conexión |
| `error: externally-managed-environment` (Linux nuevo) | Use el entorno virtual del paso 2, o instale con `python3 -m pip install --user -r requirements.txt` |

---

## 8. Cómo entregar las evidencias de una práctica

El sistema guarda todo lo que usted hace. Para respaldar su trabajo puede:

1. **Generar la evidencia de la actividad** en *Entorno Universitario & IA → Mis Evidencias*: elija la
   **actividad del syllabus** y el **tipo de evidencia**, y el sistema arma el informe con las cifras
   reales de su empresa, un **código** (`CONT1-B-2026-XXXXXXXX`) y una **huella SHA-256** que comprueba
   que no se alteró después. Desde el detalle puede abrir **Preparar captura** (vista limpia para
   pantallazo) o **Imprimible / PDF**. Entregue el **código** junto con el archivo o la captura.
   El paso a paso completo está en el *Manual de Usuario*, sección **6. Guía paso a paso del estudiante**.
2. **Exportar los libros** desde *Centro de Reportes* en **CSV**, **Excel** o **versión imprimible**
   (esta última: *Imprimir → Guardar como PDF*).
3. **Descargar sus calificaciones** desde *Mis Evaluaciones* (puntuación, tiempo y estado de cada
   intento).
4. **Mostrar la trazabilidad** en *Administración → Auditoría* (usuario, acción, valor anterior y
   valor nuevo de cada operación).

Envíe esos archivos según lo indique el docente (campus virtual o correo del curso).

---

## 9. Reglas del curso

* Cada estudiante trabaja en **su propia copia** del sistema: sus datos no se mezclan con los de
  nadie.
* El simulador **no inventa datos**: las tasas de impuestos provienen de la configuración del sistema
  y todos los estados financieros se calculan desde el libro mayor.
* **No se borran asientos contabilizados**: para corregir un error se usa la **reversión**, que crea el
  contra-asiento y conserva la trazabilidad (igual que en la práctica profesional).
* Puede consultar el **Tutor Contable IA** siempre; en modo examen solo dará orientación.
* Antes de una práctica calificada, ejecute `python database/seed_data.py` para partir de los mismos
  saldos iniciales que sus compañeros.

---

## 10. Para el docente

* **Abrir el sistema en el navegador sin servidor propio:** GitHub Codespaces (sección 2 de esta guía)
  o una **URL pública gratuita** con PythonAnywhere (ver `docs/DESPLIEGUE.md`, opción C1).
* **Publicar una URL única para todo el curso:** `docs/DESPLIEGUE.md` (VPS con Hostinger u otro
  proveedor, Docker o plataforma gestionada).
* **Manual de usuario:** `docs/MANUAL_DE_USUARIO.md`. Su **guía paso a paso del docente** (sección 7)
  cubre el seguimiento de accesos, las actividades del syllabus, las evidencias de los estudiantes y
  el paquete de calificación (CSV + XLSX).
* **Verificación automática:** cada `push` ejecuta la suite completa de pruebas y un arranque real del servidor
  en Linux mediante GitHub Actions.

> Nota: GitHub Pages (la portada del curso) **no puede ejecutar el simulador**: solo publica páginas
> estáticas. El sistema se ejecuta en Codespaces o en un servidor propio.

---

*Simulador Integral de Sistema Contable · Servicios y Comercialización de Productos ·
Comercial y Servicios Nueva Esperanza S.A. · Uso académico con datos de demostración.*
