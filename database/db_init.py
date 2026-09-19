import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config

SCHEMA_SQL = """
-- Tablas de Sistema y Seguridad
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nombre_completo TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    rol_id INTEGER NOT NULL,
    activo INTEGER DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rol_id) REFERENCES roles(id)
);

CREATE TABLE IF NOT EXISTS empresas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ruc TEXT UNIQUE NOT NULL,
    razon_social TEXT NOT NULL,
    nombre_comercial TEXT NOT NULL,
    direccion TEXT,
    telefono TEXT,
    email TEXT,
    actividad_comercial TEXT,
    actividad_servicios TEXT,
    metodo_kardex_defecto TEXT DEFAULT 'PROMEDIO', -- PROMEDIO o FIFO
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS periodos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado TEXT DEFAULT 'ABIERTO', -- ABIERTO, CERRADO
    cerrado_en TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

CREATE TABLE IF NOT EXISTS cursos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    codigo TEXT UNIQUE NOT NULL,
    docente_id INTEGER NOT NULL,
    periodo_academico TEXT,
    activo INTEGER DEFAULT 1,
    FOREIGN KEY (docente_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS matriculas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    curso_id INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (curso_id) REFERENCES cursos(id),
    FOREIGN KEY (estudiante_id) REFERENCES usuarios(id)
);

-- Plan de Cuentas Contables
CREATE TABLE IF NOT EXISTS cuentas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    naturaleza TEXT NOT NULL, -- DEUDORA, ACREEDORA
    clasificacion TEXT NOT NULL, -- ACTIVO_CORRIENTE, ACTIVO_NO_CORRIENTE, PASIVO_CORRIENTE, PASIVO_NO_CORRIENTE, PATRIMONIO, INGRESOS_OPERACIONALES, INGRESOS_NO_OPERACIONALES, COSTOS, GASTOS_ADMIN, GASTOS_VENTAS, GASTOS_FINANCIEROS
    cuenta_padre_id INTEGER,
    nivel INTEGER NOT NULL DEFAULT 1,
    acepta_movimiento INTEGER DEFAULT 1, -- 1=Detalle/Movimiento, 0=Agrupadora
    activo INTEGER DEFAULT 1,
    FOREIGN KEY (cuenta_padre_id) REFERENCES cuentas(id)
);

-- Libro Diario y Detalle de Asientos
CREATE TABLE IF NOT EXISTS asientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    periodo_id INTEGER,
    numero_asiento INTEGER NOT NULL,
    fecha DATE NOT NULL,
    glosa TEXT NOT NULL,
    tipo_documento TEXT,
    numero_documento TEXT,
    origen_modulo TEXT, -- MANUAL, VENTAS, SERVICIOS, COMPRAS, CAJA, BANCOS, AJUSTES, CIERRE
    estado TEXT DEFAULT 'CONTABILIZADO', -- CONTABILIZADO, ANULADO, REVERTIDO
    observacion TEXT,
    usuario_id INTEGER,
    asiento_reversion_id INTEGER,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    FOREIGN KEY (periodo_id) REFERENCES periodos(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS detalle_asientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asiento_id INTEGER NOT NULL,
    cuenta_id INTEGER NOT NULL,
    debe REAL NOT NULL DEFAULT 0.0,
    haber REAL NOT NULL DEFAULT 0.0,
    referencia TEXT,
    FOREIGN KEY (asiento_id) REFERENCES asientos(id) ON DELETE CASCADE,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
);

-- Configuración Tributaria
CREATE TABLE IF NOT EXISTS impuestos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    porcentaje REAL NOT NULL,
    tipo TEXT NOT NULL, -- IVA_VENTAS, IVA_COMPRAS, RET_RENTA_BIENES, RET_RENTA_SERVICIOS, RET_IVA_BIENES, RET_IVA_SERVICIOS
    cuenta_contable_id INTEGER,
    vigencia_desde DATE,
    activo INTEGER DEFAULT 1,
    FOREIGN KEY (cuenta_contable_id) REFERENCES cuentas(id)
);

-- Inventarios y Productos
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    categoria TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    unidad_medida TEXT DEFAULT 'UNIDAD',
    costo_unitario REAL NOT NULL DEFAULT 0.0,
    precio_venta REAL NOT NULL DEFAULT 0.0,
    stock_actual REAL NOT NULL DEFAULT 0.0,
    stock_minimo REAL NOT NULL DEFAULT 5.0,
    stock_maximo REAL NOT NULL DEFAULT 1000.0,
    aplica_iva INTEGER DEFAULT 1,
    proveedor_id INTEGER,
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    tipo_movimiento TEXT NOT NULL, -- ENTRADA_COMPRA, SALIDA_VENTA, AJUSTE_POSITIVO, AJUSTE_NEGATIVO, SALDO_INICIAL
    tipo_documento TEXT,
    numero_documento TEXT,
    cantidad REAL NOT NULL,
    costo_unitario REAL NOT NULL,
    costo_total REAL NOT NULL,
    saldo_cantidad REAL NOT NULL,
    saldo_costo_unitario REAL NOT NULL,
    saldo_costo_total REAL NOT NULL,
    asiento_id INTEGER,
    observaciones TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (asiento_id) REFERENCES asientos(id)
);

CREATE TABLE IF NOT EXISTS kardex_lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    documento_origen TEXT,
    cantidad_inicial REAL NOT NULL,
    cantidad_restante REAL NOT NULL,
    costo_unitario REAL NOT NULL,
    agotado INTEGER DEFAULT 0,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Terceros: Clientes y Proveedores
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identificacion TEXT UNIQUE NOT NULL,
    nombre_razon_social TEXT NOT NULL,
    email TEXT,
    telefono TEXT,
    direccion TEXT,
    limite_credito REAL DEFAULT 5000.0,
    dias_credito INTEGER DEFAULT 30,
    saldo_pendiente REAL DEFAULT 0.0,
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identificacion TEXT UNIQUE NOT NULL,
    razon_social TEXT NOT NULL,
    email TEXT,
    telefono TEXT,
    direccion TEXT,
    dias_credito INTEGER DEFAULT 30,
    saldo_pendiente REAL DEFAULT 0.0,
    activo INTEGER DEFAULT 1
);

-- Ventas y Detalle de Ventas
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    cliente_id INTEGER NOT NULL,
    numero_factura TEXT UNIQUE NOT NULL,
    fecha DATE NOT NULL,
    forma_pago TEXT NOT NULL, -- EFECTIVO, TRANSFERENCIA, CREDITO
    dias_credito INTEGER DEFAULT 0,
    fecha_vencimiento DATE,
    subtotal REAL NOT NULL DEFAULT 0.0,
    descuento REAL NOT NULL DEFAULT 0.0,
    base_imponible REAL NOT NULL DEFAULT 0.0,
    iva_porcentaje REAL NOT NULL DEFAULT 15.0,
    iva_valor REAL NOT NULL DEFAULT 0.0,
    total REAL NOT NULL DEFAULT 0.0,
    costo_ventas_total REAL NOT NULL DEFAULT 0.0,
    asiento_id INTEGER,
    asiento_costo_id INTEGER,
    estado TEXT DEFAULT 'EMITIDA', -- EMITIDA, ANULADA, COBRADA
    usuario_id INTEGER,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (asiento_id) REFERENCES asientos(id)
);

CREATE TABLE IF NOT EXISTS detalle_ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad REAL NOT NULL,
    precio_unitario REAL NOT NULL,
    descuento REAL DEFAULT 0.0,
    subtotal REAL NOT NULL,
    costo_unitario_venta REAL NOT NULL,
    costo_total_venta REAL NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Servicios
CREATE TABLE IF NOT EXISTS catalogo_servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    tarifa_sugerida REAL NOT NULL DEFAULT 0.0,
    aplica_iva INTEGER DEFAULT 1,
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS transacciones_servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    cliente_id INTEGER NOT NULL,
    servicio_id INTEGER NOT NULL,
    numero_factura TEXT UNIQUE NOT NULL,
    fecha DATE NOT NULL,
    descripcion TEXT,
    cantidad REAL NOT NULL DEFAULT 1.0,
    tarifa REAL NOT NULL,
    descuento REAL DEFAULT 0.0,
    subtotal REAL NOT NULL,
    iva_porcentaje REAL DEFAULT 15.0,
    iva_valor REAL NOT NULL,
    total REAL NOT NULL,
    forma_pago TEXT NOT NULL, -- EFECTIVO, TRANSFERENCIA, CREDITO
    dias_credito INTEGER DEFAULT 0,
    asiento_id INTEGER,
    estado TEXT DEFAULT 'EMITIDA',
    usuario_id INTEGER,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (servicio_id) REFERENCES catalogo_servicios(id),
    FOREIGN KEY (asiento_id) REFERENCES asientos(id)
);

-- Compras y Detalle de Compras
CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    proveedor_id INTEGER NOT NULL,
    numero_factura TEXT NOT NULL,
    fecha DATE NOT NULL,
    forma_pago TEXT NOT NULL, -- EFECTIVO, TRANSFERENCIA, CREDITO
    dias_credito INTEGER DEFAULT 0,
    fecha_vencimiento DATE,
    subtotal REAL NOT NULL DEFAULT 0.0,
    descuento REAL NOT NULL DEFAULT 0.0,
    iva_porcentaje REAL NOT NULL DEFAULT 15.0,
    iva_valor REAL NOT NULL DEFAULT 0.0,
    total REAL NOT NULL DEFAULT 0.0,
    asiento_id INTEGER,
    estado TEXT DEFAULT 'REGISTRADA',
    usuario_id INTEGER,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
    FOREIGN KEY (asiento_id) REFERENCES asientos(id)
);

CREATE TABLE IF NOT EXISTS detalle_compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compra_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad REAL NOT NULL,
    costo_unitario REAL NOT NULL,
    descuento REAL DEFAULT 0.0,
    subtotal REAL NOT NULL,
    FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Cuentas por Cobrar y Cobros
CREATE TABLE IF NOT EXISTS cuentas_cobrar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    tipo_origen TEXT NOT NULL, -- VENTA_PRODUCTOS, SERVICIO
    origen_id INTEGER NOT NULL,
    numero_documento TEXT NOT NULL,
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    monto_original REAL NOT NULL,
    saldo_actual REAL NOT NULL,
    estado TEXT DEFAULT 'PENDIENTE', -- PENDIENTE, PARCIAL, PAGADA, VENCIDA
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE TABLE IF NOT EXISTS cobros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_cobrar_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    monto REAL NOT NULL,
    medio_pago TEXT NOT NULL, -- EFECTIVO, TRANSFERENCIA, CHEQUE
    caja_id INTEGER,
    banco_id INTEGER,
    numero_comprobante TEXT,
    asiento_id INTEGER,
    observacion TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cuenta_cobrar_id) REFERENCES cuentas_cobrar(id),
    FOREIGN KEY (asiento_id) REFERENCES asientos(id)
);

-- Cuentas por Pagar y Pagos
CREATE TABLE IF NOT EXISTS cuentas_pagar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id INTEGER NOT NULL,
    compra_id INTEGER, -- NULL cuando la obligación proviene de un saldo inicial (apertura)
    numero_factura TEXT NOT NULL,
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    monto_original REAL NOT NULL,
    saldo_actual REAL NOT NULL,
    estado TEXT DEFAULT 'PENDIENTE', -- PENDIENTE, PARCIAL, PAGADA, VENCIDA
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
    FOREIGN KEY (compra_id) REFERENCES compras(id)
);

CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_pagar_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    monto REAL NOT NULL,
    medio_pago TEXT NOT NULL, -- EFECTIVO, TRANSFERENCIA, CHEQUE
    caja_id INTEGER,
    banco_id INTEGER,
    numero_comprobante TEXT,
    asiento_id INTEGER,
    observacion TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cuenta_pagar_id) REFERENCES cuentas_pagar(id),
    FOREIGN KEY (asiento_id) REFERENCES asientos(id)
);

-- Tesorería: Cajas y Bancos
CREATE TABLE IF NOT EXISTS cajas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    responsable TEXT,
    cuenta_contable_id INTEGER NOT NULL,
    saldo_actual REAL DEFAULT 0.0,
    estado TEXT DEFAULT 'ABIERTA', -- ABIERTA, CERRADA
    FOREIGN KEY (cuenta_contable_id) REFERENCES cuentas(id)
);

CREATE TABLE IF NOT EXISTS movimientos_caja (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caja_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    tipo_movimiento TEXT NOT NULL, -- APERTURA, INGRESO_VENTA, INGRESO_COBRO, EGRESO_COMPRA, EGRESO_PAGO, DEPOSITO_BANCO, RETIRO, CIERRE
    monto REAL NOT NULL,
    concepto TEXT NOT NULL,
    numero_comprobante TEXT,
    asiento_id INTEGER,
    FOREIGN KEY (caja_id) REFERENCES cajas(id),
    FOREIGN KEY (asiento_id) REFERENCES asientos(id)
);

CREATE TABLE IF NOT EXISTS arqueos_caja (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caja_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    saldo_contable REAL NOT NULL,
    saldo_fisico REAL NOT NULL,
    diferencia REAL NOT NULL, -- Fisico - Contable: Positivo = Sobrante, Negativo = Faltante
    observaciones TEXT,
    usuario_id INTEGER NOT NULL,
    asiento_ajuste_id INTEGER,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (caja_id) REFERENCES cajas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS bancos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_banco TEXT NOT NULL,
    numero_cuenta TEXT UNIQUE NOT NULL,
    tipo_cuenta TEXT NOT NULL, -- CORRIENTE, AHORROS
    cuenta_contable_id INTEGER NOT NULL,
    saldo_actual REAL DEFAULT 0.0,
    activo INTEGER DEFAULT 1,
    FOREIGN KEY (cuenta_contable_id) REFERENCES cuentas(id)
);

CREATE TABLE IF NOT EXISTS movimientos_bancarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    banco_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    tipo_movimiento TEXT NOT NULL, -- DEPOSITO, TRANSFERENCIA_RECIBIDA, TRANSFERENCIA_EMITIDA, CHEQUE, NOTA_DEBITO, NOTA_CREDITO, COMISION, INTERES
    monto REAL NOT NULL,
    concepto TEXT NOT NULL,
    numero_referencia TEXT,
    conciliado INTEGER DEFAULT 0,
    asiento_id INTEGER,
    FOREIGN KEY (banco_id) REFERENCES bancos(id),
    FOREIGN KEY (asiento_id) REFERENCES asientos(id)
);

CREATE TABLE IF NOT EXISTS conciliaciones_bancarias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    banco_id INTEGER NOT NULL,
    periodo_id INTEGER NOT NULL,
    fecha_corte DATE NOT NULL,
    saldo_extracto_bancario REAL NOT NULL,
    saldo_libro_bancos REAL NOT NULL,
    depositos_en_transito REAL DEFAULT 0.0,
    cheques_en_transito REAL DEFAULT 0.0,
    notas_debito_no_registradas REAL DEFAULT 0.0,
    notas_credito_no_registradas REAL DEFAULT 0.0,
    diferencia REAL DEFAULT 0.0,
    estado TEXT DEFAULT 'BORRADOR', -- BORRADOR, CONCILIADO
    usuario_id INTEGER,
    observaciones TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (banco_id) REFERENCES bancos(id),
    FOREIGN KEY (periodo_id) REFERENCES periodos(id)
);

-- Documentos Fuente Simulados
CREATE TABLE IF NOT EXISTS documentos_fuente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL, -- FACTURA_VENTA, FACTURA_COMPRA, COMPROBANTE_INGRESO, COMPROBANTE_EGRESO, NOTA_CREDITO, NOTA_DEBITO, ESTADO_CUENTA_BANCARIO, ORDEN_COMPRA, ROL_PAGOS
    numero TEXT NOT NULL,
    fecha DATE NOT NULL,
    emisor TEXT NOT NULL,
    receptor TEXT NOT NULL,
    monto_total REAL NOT NULL,
    descripcion TEXT,
    datos_json TEXT, -- JSON estructurado con detalles
    asiento_id INTEGER,
    simulacion_caso_id INTEGER
);

-- Simulaciones, Casos y Evaluación
CREATE TABLE IF NOT EXISTS simulaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    nivel INTEGER NOT NULL DEFAULT 1, -- 1=Basico, 2=Intermedio, 3=Avanzado, 4=Integral
    modo_examen INTEGER DEFAULT 0, -- 0=Practica/Guiado, 1=Examen
    duracion_minutos INTEGER DEFAULT 60,
    puntuacion_minima REAL DEFAULT 70.0,
    docente_id INTEGER,
    curso_id INTEGER,
    activo INTEGER DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (docente_id) REFERENCES usuarios(id),
    FOREIGN KEY (curso_id) REFERENCES cursos(id)
);

CREATE TABLE IF NOT EXISTS casos_simulacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulacion_id INTEGER NOT NULL,
    orden INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    fecha_transaccion DATE NOT NULL,
    enunciado TEXT NOT NULL,
    documento_fuente_tipo TEXT,
    documento_fuente_numero TEXT,
    datos_transaccion_json TEXT NOT NULL, -- JSON con detalles de la operación
    solucion_esperada_json TEXT NOT NULL, -- JSON con las cuentas esperadas y montos Debe/Haber
    pistas_json TEXT, -- Array de pistas progresivas: nivel 1, 2, 3
    explicacion_pedagogica TEXT,
    FOREIGN KEY (simulacion_id) REFERENCES simulaciones(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS intentos_estudiante (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulacion_id INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL,
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_fin TIMESTAMP,
    puntuacion_total REAL DEFAULT 0.0,
    estado TEXT DEFAULT 'EN_PROGRESO', -- EN_PROGRESO, COMPLETADO, ABANDONADO
    tiempo_segundos INTEGER DEFAULT 0,
    FOREIGN KEY (simulacion_id) REFERENCES simulaciones(id),
    FOREIGN KEY (estudiante_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS detalle_intentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intento_id INTEGER NOT NULL,
    caso_id INTEGER NOT NULL,
    respuestas_json TEXT NOT NULL, -- Lo que el estudiante ingresó (cuentas, debe, haber, impuestos)
    puntuacion REAL NOT NULL,
    resultado TEXT NOT NULL, -- CORRECTO, PARCIALMENTE_CORRECTO, INCORRECTO
    numero_intento_caso INTEGER DEFAULT 1,
    pistas_utilizadas INTEGER DEFAULT 0,
    retroalimentacion_especifica TEXT,
    tiempo_segundos INTEGER DEFAULT 0,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intento_id) REFERENCES intentos_estudiante(id) ON DELETE CASCADE,
    FOREIGN KEY (caso_id) REFERENCES casos_simulacion(id)
);

-- Trazabilidad y Auditoría
CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    username TEXT,
    accion TEXT NOT NULL, -- CREAR, MODIFICAR, ANULAR, REVERTIR, CONSULTAR, LOGIN, SIMULACION_ENVIO
    modulo TEXT NOT NULL, -- ASIENTOS, VENTAS, COMPRAS, SERVICIOS, INVENTARIO, CAJA, BANCOS, PLAN_CUENTAS, ADMIN
    registro_id TEXT,
    valor_anterior TEXT,
    valor_nuevo TEXT,
    ip_origen TEXT,
    agente_utilizado TEXT,
    herramienta_ejecutada TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Parámetros del sistema (fecha de trabajo de la simulación, tolerancias, etc.)
CREATE TABLE IF NOT EXISTS parametros (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    descripcion TEXT,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices de rendimiento
CREATE INDEX IF NOT EXISTS idx_detalle_asiento ON detalle_asientos(asiento_id);
CREATE INDEX IF NOT EXISTS idx_detalle_cuenta ON detalle_asientos(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_asientos_fecha ON asientos(fecha);
CREATE INDEX IF NOT EXISTS idx_mov_inv_producto ON movimientos_inventario(producto_id);
CREATE INDEX IF NOT EXISTS idx_cxc_cliente ON cuentas_cobrar(cliente_id);
CREATE INDEX IF NOT EXISTS idx_cxp_proveedor ON cuentas_pagar(proveedor_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_modulo ON auditoria(modulo);
"""

def init_db(db_path=None):
    if db_path is None:
        db_path = Config.DATABASE_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"Database initialized successfully at {db_path} with 33 core tables!")

    # Módulo educativo (actividades, asignaciones, sesiones, eventos, evidencias).
    from database.esquema_educativo import aplicar as _aplicar_educativo
    _aplicar_educativo(db_path)

    # Catálogo de documentos del SRI (tipos, reglas y columnas del comprobante).
    from database.esquema_documentos_sri import aplicar as _aplicar_sri, sembrar as _sembrar_sri
    _aplicar_sri(db_path, verboso=False)
    _sembrar_sri(db_path, verboso=False)

    # Porcentajes oficiales del SRI (IVA y retenciones), y cuentas asociadas.
    from database.parametros_tributarios_sri import aplicar as _aplicar_tributario
    _aplicar_tributario(db_path, verboso=False)
    print("   Catálogo del SRI y parámetros tributarios aplicados.")

    # Banco de casos prácticos de los libros (§61) y reglas de trazabilidad de las fuentes (§62).
    from database.esquema_casos_libros import aplicar as _aplicar_casos, sembrar as _sembrar_casos
    _aplicar_casos(db_path, verboso=False)
    _sembrar_casos(db_path, verboso=False)
    print("   Banco de casos prácticos de los libros (§61) y reglas §62 aplicados.")

if __name__ == "__main__":
    init_db()
