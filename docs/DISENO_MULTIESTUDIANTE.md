# Diseño: un aula por estudiante (aislamiento real)

## Problema

El simulador nació como **una sola empresa compartida**: casi todas las tablas contables
(`cuentas`, `productos`, `clientes`, `proveedores`, `documentos_fuente`, `cajas`, `bancos`…) no
tienen columna de empresa, y solo 8 tablas la tienen. Con 59 estudiantes escribiendo en la misma
empresa, el Libro Diario se mezcla, el plan de cuentas se duplica y no hay forma de calificar.

Agregar `empresa_id` a 45 tablas obligaría a revisar ~388 sentencias SQL. Es un refactor amplio y
de alto riesgo.

## Decisión

**Una base de datos SQLite por estudiante** (equivalente a darle a cada uno su propia instancia del
sistema) para el trabajo contable, más una **base de control** compartida para lo académico.

```
database/
├── simulator.db                     BD de CONTROL (compartida) — lo académico
│   ├── usuarios, roles, cursos, matriculas
│   ├── actividades, asignaciones_actividad
│   ├── sesiones_usuario, eventos_estudiante
│   ├── evidencias, versiones_evidencia
│   ├── aulas_estudiante            (qué aula corresponde a cada estudiante)
│   └── auditoria
├── aulas/
│   └── B/
│       ├── ealcivar4002.db          aula contable de Emily Alcívar
│       └── javiles8757.db           aula contable de Jordano Avilés
└── plantilla/
    └── aula_base.db                 plantilla para clonar (esquema + datos demostrativos)
```

Cada aula contiene **lo contable del estudiante**: su empresa, plan de cuentas, asientos, Libro Diario
y Mayor, balance, estados financieros, inventario, cartera, tesorería, documentos, períodos, impuestos
y las simulaciones.

Ventaja de este reparto: el docente ve **en un solo lugar** quién ingresó, qué actividades entregó y
qué evidencias generó (base de control), mientras los libros de cada estudiante quedan aislados. La
evidencia de un estudiante se arma leyendo **su** aula y se guarda en la base de control, de modo que
verificar un código es una sola consulta.

## Por qué así

- **Aislamiento por construcción:** el estudiante A no puede ver los datos de B porque *no están en
  su archivo*; cualquier URL con un id ajeno devuelve su propio registro, no el del compañero. No hay
  que confiar en filtros añadidos a mano en cada consulta.
- **Cero cambios en las 388 consultas** de negocio: siguen funcionando igual, contra otra ruta de archivo.
- **Respaldo y borrado simple:** copiar el archivo de un estudiante, o reponer su aula desde la plantilla.
- **Rendimiento:** cada estudiante escribe en su propio archivo; no hay contención de escritura entre 59.

## Resolución de la base según el usuario

En `models.py`:

| Función | Devuelve |
|---|---|
| `get_db_connection(db_path=None)` | La base de **control** (compatibilidad total con el código actual). |
| `get_db_control()` | Igual que la anterior, con nombre explícito para autenticación y administración. |
| `get_db_contable(db_path=None)` | El **aula del estudiante** en sesión; si no hay sesión de estudiante, la base de control (modo demostración). |

Reglas:

1. Si la aplicación corre en modo un solo curso (`SIMULADOR_MULTIESTUDIANTE` desactivado) todo se
   comporta como antes: una sola base. Nada se rompe.
2. Si el usuario en sesión es **Estudiante** y existe su aula, `get_db_contable()` apunta a su archivo.
3. **Docente, Administrador y Auditor** trabajan contra la base de control; para ver los libros de un
   estudiante abren expresamente su aula (`ruta_aula(username, paralelo)`), en modo lectura.
4. `auth.py` siempre usa `get_db_control()`: la tabla `usuarios` vive en la base de control.

## Índice de evidencias

Las evidencias viven en la **base de control**, junto con las actividades y las asignaciones: el
docente las revisa y verifica en un solo lugar, sin abrir 59 archivos. Lo que sí se lee del aula del
estudiante es el **contenido** de la evidencia (sus cuentas, sus asientos, su balance), para que el
resumen muestre cifras reales y no inventadas. La huella SHA-256 y la marca de «modificada después»
siguen guardándose con la evidencia.

## Panel docente

El resumen de accesos, las actividades entregadas y las evidencias se leen de la base de control. Para
**ver los libros de un estudiante** (Libro Diario, Libro Mayor, balance de comprobación y estados
financieros) el panel abre expresamente el aula de ese estudiante y la consulta en **modo solo
lectura** (`file:...?mode=ro`), sin poder modificarla.

Rutas disponibles para el docente y el administrador, desde la ficha del estudiante:

| Ruta | Muestra |
|---|---|
| `/docente/estudiantes/<id>` | Ficha: accesos, sesiones, línea de tiempo, avance de actividades y resumen de sus libros |
| `/docente/estudiantes/<id>/diario` | Libro Diario del estudiante |
| `/docente/estudiantes/<id>/mayor` | Libro Mayor con saldos acumulados |
| `/docente/estudiantes/<id>/balance` | Balance de comprobación y si cuadra |
| `/docente/estudiantes/<id>/cuentas` | Plan de cuentas que construyó |
| `/docente/estudiantes/<id>/estados` | Estados financieros básicos |

Todas aceptan `?formato=json` para consumo de la API interna. Si el estudiante aún no tiene aula o su
aula está vacía, la vista lo dice con un aviso claro en lugar de mostrar un error.

## Nómina e ingreso de los estudiantes

1. `Listado de estudiantes_B.pdf` → `datos/nomina_paralelo_B.csv` (usuario, nombre, cédula, correo).
2. `database/importar_nomina.py` crea, para cada estudiante: usuario en la base de control (rol
   Estudiante, paralelo B, matrícula = cédula), su aula clonada desde la plantilla, y le asigna las
   seis actividades del syllabus.
3. La **contraseña inicial es aleatoria** (nunca la cédula) y se entrega a la docente en un archivo
   de credenciales **fuera del repositorio**, para que lo distribuya por el aula virtual.
4. El estudiante puede cambiar su contraseña en su primer ingreso.

## Modo demostración

La empresa compartida (**Comercial y Servicios Nueva Esperanza S.A.**) sigue disponible para las
cuentas `admin`, `docente`, `estudiante` y `auditor`, de modo que la docente pueda mostrar el sistema
en clase y las pruebas automáticas sigan corriendo sin depender de las aulas.
