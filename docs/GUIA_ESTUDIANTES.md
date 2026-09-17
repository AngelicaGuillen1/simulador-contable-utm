# Guía para estudiantes
## Simulador Integral de Sistema Contable

Bienvenido(a). Este repositorio contiene el **Simulador Integral de Sistema Contable**
(Comercial y Servicios Nueva Esperanza S.A.) que usaremos en el curso: un sistema contable
completo, con inventarios, tesorería, cartera, impuestos, estados financieros y un simulador de
casos con evaluación automática.

Aquí no hay que programar nada: usted **descarga el sistema, lo ejecuta en su computador y trabaja
con él en el navegador**.

---

## 1. Qué necesita

| Requisito | Detalle |
|---|---|
| Sistema operativo | Windows, macOS o Linux |
| Python | **3.11 o superior** ([descargar](https://www.python.org/downloads/)) — en Windows marque *“Add Python to PATH”* al instalar |
| Espacio libre | ~60 MB |
| Navegador | Chrome, Edge, Firefox o Safari |

---

## 2. Descargar el sistema

**Opción A — Descarga directa (la más simple)**

1. En esta página de GitHub pulse el botón verde **`Code` → `Download ZIP`**.
2. Descomprima el archivo en una carpeta, por ejemplo `Documentos\SimuladorContable`.
3. Abra una terminal **dentro de esa carpeta**.

**Opción B — Con Git**

```bash
git clone https://github.com/<USUARIO-DEL-DOCENTE>/<NOMBRE-DEL-REPOSITORIO>.git
cd <NOMBRE-DEL-REPOSITORIO>
```

---

## 3. Instalar y ejecutar (una sola vez la instalación)

### Windows (PowerShell o CMD)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python serve.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python serve.py
```

Cuando vea el mensaje **“Servidor de producción (waitress) escuchando en http://127.0.0.1:5000”**
(la primera vez tarda un minuto porque genera los datos de demostración), abra el navegador en:

```
http://127.0.0.1:5000
```

**Las siguientes veces** solo necesita:

```bash
# Windows
.venv\Scripts\activate
python serve.py
```

Para terminar, cierre la ventana de la terminal o pulse `Ctrl + C`.

---

## 4. Usuarios para entrar

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `admin123` |
| Docente | `docente` | `docente123` |
| Estudiante | `estudiante` | `estudiante123` |
| Auditor | `auditor` | `auditor123` |

> Trabaje con el usuario **estudiante**. Los otros perfiles existen para que pueda ver los módulos
> de administración y de docencia.

---

## 5. Primer recorrido (15 minutos)

1. **Inicio de sesión** con `estudiante`.
2. **Simulador de Casos → Nivel 1 → Iniciar.** Lea el enunciado, arme el asiento (cuenta, Debe,
   Haber) y pulse **Enviar Asiento y Evaluar**. Verá su puntuación sobre 100, la rúbrica y la
   retroalimentación. Si se traba, use **Pedir pista al Tutor IA** (cada pista resta 5 puntos).
3. **Contabilidad → Libro Diario**: encuentre los asientos que acaba de generar.
4. **Ventas → Nueva venta**: registre una venta a crédito (20 unidades, 30 días) y véala reflejada
   en **Cuentas por Cobrar**, **Caja/Bancos**, **Kardex** y **Documentos Fuente**.
5. **Estados Financieros → Situación Financiera**: debe aparecer el banner verde
   **“Activo = Pasivo + Patrimonio ✓”**.
6. **Contabilidad → Balance de Comprobación**: compruebe que las sumas y los saldos cuadran.

El **manual de usuario completo** está en:

* dentro del sistema: `http://127.0.0.1:5000/manual`
* en el repositorio: `docs/MANUAL_DE_USUARIO.md`

---

## 6. Volver a los datos iniciales

Cada vez que quiera empezar de cero (por ejemplo, antes de una práctica evaluada):

```bash
python database/seed_data.py
```

Esto **borra** sus registros y vuelve a crear la empresa simulada con el período Abril 2026 y las
30 operaciones de demostración. No afecta a los archivos del repositorio.

---

## 7. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `python: command not found` (o *no se reconoce como un comando*) | Python no está instalado o no está en el PATH. Reinstálelo marcando *“Add Python to PATH”*; en macOS/Linux use `python3` |
| `ModuleNotFoundError: No module named 'flask'` | No activó el entorno virtual o no instaló las dependencias: repita el paso 3 |
| `Address already in use` | Ya hay un servidor abierto en ese puerto: cierre la otra ventana de terminal o cambie el puerto: `PORT=8081 python serve.py` (Windows: `set PORT=8081` antes) |
| `no such table: ...` | Falta generar la base: `python database/seed_data.py` |
| El navegador no abre nada | Copie y pegue usted mismo `http://127.0.0.1:5000` en la barra de direcciones |
| La página se ve sin colores | Recargue con `Ctrl + F5`. El sistema funciona igual sin conexión |
| `error: externally-managed-environment` (Linux nuevo) | Use el entorno virtual del paso 3, o instale con `python3 -m pip install --user -r requirements.txt` |

---

## 8. Cómo entregar las evidencias de una práctica

El sistema guarda todo lo que usted hace. Para respaldar su trabajo puede:

1. **Exportar los libros** desde *Centro de Reportes* en **CSV**, **Excel** o **versión imprimible**
   (esta última: *Imprimir → Guardar como PDF*).
2. **Imprimir sus calificaciones** desde *Mis Evaluaciones* (puntuación, tiempo y estado de cada
   intento).
3. **Mostrar la trazabilidad** en *Administración → Auditoría* (usuario, acción, valor anterior y
   valor nuevo de cada operación).

Envíe esos archivos según lo indique el docente (campus virtual o correo del curso).

---

## 9. Reglas del curso

* Cada estudiante trabaja en **su propia copia** del sistema: sus datos no se mezclan con los de
  nadie.
* El simulador **no inventa datos**: las tasas de impuestos provienen de la configuración del
  sistema y todos los estados financieros se calculan desde el libro mayor.
* **No se borran asientos contabilizados**: para corregir un error se usa la **reversión**, que crea
  el contra-asiento y conserva la trazabilidad (igual que en la práctica profesional).
* Puede consultar el **Tutor Contable IA** siempre; en modo examen solo dará orientación.
* Antes de una práctica calificada, ejecute `python database/seed_data.py` para partir de los
  mismos saldos iniciales que sus compañeros.

---

## 10. Para el docente

* Publicación del sistema en Internet (VPS, Docker o plataforma gestionada): `docs/DESPLIEGUE.md`.
* Manual de usuario y plan de clases por módulo: `docs/MANUAL_DE_USUARIO.md`.
* Verificación automática del código: cada `push` ejecuta las **113 pruebas** de la suite
  (`pytest`) en GitHub Actions.

---

*Simulador Integral de Sistema Contable · Servicios y Comercialización de Productos ·
Comercial y Servicios Nueva Esperanza S.A. · Uso académico con datos de demostración.*
