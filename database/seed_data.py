"""
Datos de demostración del Simulador Integral de Sistema Contable
----------------------------------------------------------------
Genera una empresa simulada COMPLETA y COHERENTE:

  1. Datos maestros: roles, usuarios, empresa, período, curso, plan de cuentas (43 cuentas),
     impuestos configurables, caja, 2 bancos, catálogo de servicios, clientes, proveedores y
     20 productos de primera necesidad.
  2. Asiento de apertura de saldos iniciales + inventario inicial valorado (Kardex).
  3. Saldos iniciales de cartera (cuentas por cobrar y por pagar) por tercero.
  4. 30 operaciones del período Abril 2026 ejecutadas a través de los SERVICIOS reales del sistema
     (compras, ventas, servicios, cobros, pagos, gastos, tesorería y ajustes), de modo que cada
     operación actualiza de forma simultánea: documento fuente, transacción, inventario/Kardex,
     cartera, tesorería, libro diario, libro mayor y estados financieros.
  5. Simulaciones por niveles con casos generados a partir de los asientos REALES registrados.

Todos los datos son de DEMOSTRACIÓN con fines académicos.
"""
import os
import sys
import json
import sqlite3
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config
from database.db_init import init_db
from models import get_db_connection
from services.accounting_service import AccountingService
from services.inventory_service import InventoryService
from services.sales_service import SalesService
from services.purchase_service import PurchaseService
from services.treasury_service import TreasuryService
from services.document_service import DocumentService
from services.tax_service import TaxService
from services.period_service import PeriodService
from tools.financial_tools import create_receivable, create_payable

EMPRESA_ID = 1
PERIODO_ID = 1
PERIODO_INICIO = "2026-04-01"
PERIODO_FIN = "2026-04-30"
FECHA_TRABAJO = "2026-04-30"
USUARIO_ADMIN = 1

TABLAS = [
    "detalle_intentos", "intentos_estudiante", "casos_simulacion", "simulaciones",
    "matriculas", "cursos", "documentos_fuente", "conciliaciones_bancarias", "arqueos_caja",
    "movimientos_bancarios", "movimientos_caja", "bancos", "cajas", "pagos", "cobros",
    "cuentas_pagar", "cuentas_cobrar", "detalle_compras", "compras",
    "detalle_ventas", "ventas", "transacciones_servicios", "catalogo_servicios",
    "kardex_lotes", "movimientos_inventario", "productos", "proveedores", "clientes",
    "detalle_asientos", "asientos", "impuestos", "cuentas", "auditoria", "parametros",
    "empresas", "periodos", "usuarios", "roles",
]


# ----------------------------------------------------------------------------
# Utilidades internas
# ----------------------------------------------------------------------------
def _reset_tables(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    for tabla in TABLAS:
        try:
            conn.execute(f"DELETE FROM {tabla}")
        except sqlite3.OperationalError:
            pass
    try:
        conn.execute("DELETE FROM sqlite_sequence")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def _insert_many(db_path, sql, filas):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executemany(sql, filas)
    conn.commit()
    conn.close()


def _documento(tipo, numero, fecha, emisor, receptor, monto, descripcion, datos=None, asiento_id=None):
    return DocumentService.register(tipo, numero, fecha, emisor, receptor, monto, descripcion,
                                    datos=datos, asiento_id=asiento_id)


def _asiento(fecha, glosa, lineas, tipo_documento, numero_documento, origen_modulo, observacion=None):
    """Crea un asiento contable validado y devuelve (asiento_id, numero_asiento)."""
    return AccountingService.create_journal_entry(
        EMPRESA_ID, fecha, glosa, lineas, tipo_documento=tipo_documento,
        numero_documento=numero_documento, origen_modulo=origen_modulo,
        usuario_id=USUARIO_ADMIN, periodo_id=PERIODO_ID, observacion=observacion
    )


def _lineas_de_asiento(asiento_id, db_path=None):
    """Devuelve las líneas contables reales de un asiento con código y nombre de cuenta."""
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute("""
            SELECT c.codigo, c.nombre, c.naturaleza, d.debe, d.haber, d.referencia
            FROM detalle_asientos d
            JOIN cuentas c ON d.cuenta_id = c.id
            WHERE d.asiento_id = ?
            ORDER BY d.debe DESC, d.haber ASC
        """, (asiento_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# 1. Datos maestros
# ----------------------------------------------------------------------------
def _seed_maestros(db_path):
    roles = [
        (1, "Administrador", "Acceso total a configuración, usuarios, parámetros y auditoría"),
        (2, "Docente", "Creación de simulaciones, casos, rúbricas y analítica de desempeño"),
        (3, "Estudiante", "Ejecución de simulaciones, registros contables y autoevaluación"),
        (4, "Auditor", "Acceso de solo lectura a movimientos, libros, estados y trazabilidad"),
    ]
    _insert_many(db_path, "INSERT INTO roles (id, nombre, descripcion) VALUES (?, ?, ?)", roles)

    users = [
        (1, "admin", generate_password_hash("admin123"), "Ing. Marco Morales - Administrador", "admin@nuevaesperanza.edu.ec", 1, 1),
        (2, "docente", generate_password_hash("docente123"), "Dr. Carlos Mendoza - Catedrático Contable", "cmendoza@universidad.edu.ec", 2, 1),
        (3, "estudiante", generate_password_hash("estudiante123"), "Ana Lucía Morales - Estudiante", "amorales@estudiantes.edu.ec", 3, 1),
        (4, "auditor", generate_password_hash("auditor123"), "Lic. Roberto Vaca - Auditor Externo", "rvaca@auditoria.com.ec", 4, 1),
    ]
    _insert_many(db_path, """
        INSERT INTO usuarios (id, username, password_hash, nombre_completo, email, rol_id, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, users)

    _insert_many(db_path, """
        INSERT INTO empresas (id, ruc, razon_social, nombre_comercial, direccion, telefono, email,
                              actividad_comercial, actividad_servicios, metodo_kardex_defecto, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(
        1, Config.COMPANY_RUC, "Comercial y Servicios Nueva Esperanza S.A.",
        Config.COMPANY_NAME,
        "Av. Amazonas N34-120 y Naciones Unidas, Edificio Platinum, Quito", "02-2987-654",
        "info@nuevaesperanza.com.ec",
        "Comercialización de productos de primera necesidad al por mayor y menor",
        "Prestación de servicios de logística, asesoría y mantenimiento integral",
        "PROMEDIO", 1
    )])

    _insert_many(db_path, """
        INSERT INTO periodos (id, empresa_id, nombre, fecha_inicio, fecha_fin, estado)
        VALUES (?, ?, ?, ?, ?, 'ABIERTO')
    """, [(PERIODO_ID, EMPRESA_ID, "Período Académico Abril 2026", PERIODO_INICIO, PERIODO_FIN)])

    _insert_many(db_path, """
        INSERT INTO cursos (id, nombre, codigo, docente_id, periodo_academico, activo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [(1, "Contabilidad General y de Costos I", "CONT-101-2026", 2, "2026-1", 1)])
    _insert_many(db_path, "INSERT INTO matriculas (id, curso_id, estudiante_id) VALUES (?, ?, ?)",
                 [(1, 1, 3)])

    # Plan de cuentas (43 cuentas jerárquicas NIIF)
    cuentas = [
        (1, "1", "ACTIVO", "DEUDORA", "ACTIVO_CORRIENTE", None, 1, 0),
        (2, "1.1", "ACTIVO CORRIENTE", "DEUDORA", "ACTIVO_CORRIENTE", 1, 2, 0),
        (3, "1.1.01", "Caja General", "DEUDORA", "ACTIVO_CORRIENTE", 2, 3, 1),
        (4, "1.1.02", "Banco Pichincha Cta Cte 2100874521", "DEUDORA", "ACTIVO_CORRIENTE", 2, 3, 1),
        (5, "1.1.03", "Banco Guayaquil Cta Ahorros 10458932", "DEUDORA", "ACTIVO_CORRIENTE", 2, 3, 1),
        (6, "1.1.04", "Cuentas por Cobrar Clientes", "DEUDORA", "ACTIVO_CORRIENTE", 2, 3, 1),
        (7, "1.1.05", "Provisión Cuentas Incobrables", "ACREEDORA", "ACTIVO_CORRIENTE", 2, 3, 1),
        (8, "1.1.06", "Inventario de Mercaderías", "DEUDORA", "ACTIVO_CORRIENTE", 2, 3, 1),
        (9, "1.1.07", "IVA Compras (Crédito Tributario)", "DEUDORA", "ACTIVO_CORRIENTE", 2, 3, 1),
        (10, "1.1.08", "Anticipo a Proveedores", "DEUDORA", "ACTIVO_CORRIENTE", 2, 3, 1),
        (11, "1.2", "ACTIVO NO CORRIENTE", "DEUDORA", "ACTIVO_NO_CORRIENTE", 1, 2, 0),
        (12, "1.2.01", "Muebles y Enseres de Oficina", "DEUDORA", "ACTIVO_NO_CORRIENTE", 11, 3, 1),
        (13, "1.2.02", "Depreciación Acumulada Muebles y Enseres", "ACREEDORA", "ACTIVO_NO_CORRIENTE", 11, 3, 1),
        (14, "1.2.03", "Equipo de Cómputo y Software", "DEUDORA", "ACTIVO_NO_CORRIENTE", 11, 3, 1),
        (15, "1.2.04", "Depreciación Acumulada Equipo de Cómputo", "ACREEDORA", "ACTIVO_NO_CORRIENTE", 11, 3, 1),
        (16, "1.2.05", "Vehículo de Reparto", "DEUDORA", "ACTIVO_NO_CORRIENTE", 11, 3, 1),
        (17, "1.2.06", "Depreciación Acumulada Vehículo", "ACREEDORA", "ACTIVO_NO_CORRIENTE", 11, 3, 1),
        (18, "2", "PASIVO", "ACREEDORA", "PASIVO_CORRIENTE", None, 1, 0),
        (19, "2.1", "PASIVO CORRIENTE", "ACREEDORA", "PASIVO_CORRIENTE", 18, 2, 0),
        (20, "2.1.01", "Cuentas por Pagar Proveedores", "ACREEDORA", "PASIVO_CORRIENTE", 19, 3, 1),
        (21, "2.1.02", "IVA Ventas (Débito Fiscal)", "ACREEDORA", "PASIVO_CORRIENTE", 19, 3, 1),
        (22, "2.1.03", "Retenciones en la Fuente por Pagar", "ACREEDORA", "PASIVO_CORRIENTE", 19, 3, 1),
        (23, "2.1.04", "Sueldos y Beneficios Sociales por Pagar", "ACREEDORA", "PASIVO_CORRIENTE", 19, 3, 1),
        (24, "2.1.05", "Préstamo Bancario por Pagar CP", "ACREEDORA", "PASIVO_CORRIENTE", 19, 3, 1),
        (25, "3", "PATRIMONIO", "ACREEDORA", "PATRIMONIO", None, 1, 0),
        (26, "3.1.01", "Capital Social Suscrito y Pagado", "ACREEDORA", "PATRIMONIO", 25, 2, 1),
        (27, "3.2.01", "Reserva Legal", "ACREEDORA", "PATRIMONIO", 25, 2, 1),
        (28, "3.3.01", "Utilidades Acumuladas Ejercicios Anteriores", "ACREEDORA", "PATRIMONIO", 25, 2, 1),
        (29, "3.3.02", "Utilidad del Ejercicio Actual", "ACREEDORA", "PATRIMONIO", 25, 2, 1),
        (30, "4", "INGRESOS", "ACREEDORA", "INGRESOS_OPERACIONALES", None, 1, 0),
        (31, "4.1.01", "Ingresos por Ventas de Bienes", "ACREEDORA", "INGRESOS_OPERACIONALES", 30, 2, 1),
        (32, "4.1.02", "Ingresos por Prestación de Servicios", "ACREEDORA", "INGRESOS_OPERACIONALES", 30, 2, 1),
        (33, "4.2.01", "Otros Ingresos Operacionales / Financieros", "ACREEDORA", "INGRESOS_NO_OPERACIONALES", 30, 2, 1),
        (34, "5", "COSTOS", "DEUDORA", "COSTOS", None, 1, 0),
        (35, "5.1.01", "Costo de Mercaderías Vendidas", "DEUDORA", "COSTOS", 34, 2, 1),
        (36, "6", "GASTOS", "DEUDORA", "GASTOS_ADMIN", None, 1, 0),
        (37, "6.1.01", "Gasto Sueldos y Salarios", "DEUDORA", "GASTOS_ADMIN", 36, 2, 1),
        (38, "6.1.02", "Gasto Arriendo de Local", "DEUDORA", "GASTOS_ADMIN", 36, 2, 1),
        (39, "6.1.03", "Gasto Servicios Básicos y Conectividad", "DEUDORA", "GASTOS_ADMIN", 36, 2, 1),
        (40, "6.1.04", "Gasto Depreciación de Activos Fijos", "DEUDORA", "GASTOS_ADMIN", 36, 2, 1),
        (41, "6.1.05", "Gasto Publicidad, Marketing y Ventas", "DEUDORA", "GASTOS_VENTAS", 36, 2, 1),
        (42, "6.1.06", "Gasto Mantenimiento y Reparaciones", "DEUDORA", "GASTOS_ADMIN", 36, 2, 1),
        (43, "6.2.01", "Gastos Financieros y Comisiones Bancarias", "DEUDORA", "GASTOS_FINANCIEROS", 36, 2, 1),
    ]
    _insert_many(db_path, """
        INSERT INTO cuentas (id, codigo, nombre, naturaleza, clasificacion, cuenta_padre_id, nivel, acepta_movimiento, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, cuentas)

    # Configuración tributaria (tasas configurables por el administrador - NO fijas en el código)
    impuestos = [
        (1, "IVA-15-VTA", "IVA 15% en Ventas", 15.0, "IVA_VENTAS", 21, "2024-04-01", 1),
        (2, "IVA-15-COM", "IVA 15% en Compras", 15.0, "IVA_COMPRAS", 9, "2024-04-01", 1),
        (3, "RET-FTE-BIE", "Retención Fuente Renta Bienes 1.75%", 1.75, "RET_RENTA_BIENES", 22, "2024-01-01", 1),
        (4, "RET-FTE-SRV", "Retención Fuente Renta Servicios 2.75%", 2.75, "RET_RENTA_SERVICIOS", 22, "2024-01-01", 1),
        (5, "RET-IVA-BIE", "Retención IVA Bienes 30%", 30.0, "RET_IVA_BIENES", 22, "2024-01-01", 1),
        (6, "RET-IVA-SRV", "Retención IVA Servicios 70%", 70.0, "RET_IVA_SERVICIOS", 22, "2024-01-01", 1),
    ]
    _insert_many(db_path, """
        INSERT INTO impuestos (id, codigo, nombre, porcentaje, tipo, cuenta_contable_id, vigencia_desde, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, impuestos)

    _insert_many(db_path, """
        INSERT INTO cajas (id, nombre, responsable, cuenta_contable_id, saldo_actual, estado)
        VALUES (?, ?, ?, ?, 0.0, 'ABIERTA')
    """, [(1, "Caja Principal Ventas", "Lic. Gabriela Santos", 3)])
    _insert_many(db_path, """
        INSERT INTO bancos (id, nombre_banco, numero_cuenta, tipo_cuenta, cuenta_contable_id, saldo_actual, activo)
        VALUES (?, ?, ?, ?, ?, 0.0, 1)
    """, [
        (1, "Banco Pichincha", "2100874521", "CORRIENTE", 4),
        (2, "Banco Guayaquil", "10458932", "AHORROS", 5),
    ])

    _insert_many(db_path, """
        INSERT INTO catalogo_servicios (id, codigo, nombre, descripcion, tarifa_sugerida, aplica_iva, activo)
        VALUES (?, ?, ?, ?, ?, 1, 1)
    """, [
        (1, "SRV-LOG-01", "Servicio de Entrega y Distribución Logística Express", "Transporte puerta a puerta", 45.00),
        (2, "SRV-ADM-02", "Asesoría Administrativa y de Gestión Contable", "Consultoría integral", 150.00),
        (3, "SRV-MNT-03", "Mantenimiento Preventivo y Limpieza de Instalaciones", "Saneamiento y mantenimiento", 80.00),
        (4, "SRV-TRN-04", "Transporte Especializado de Carga Pesada", "Traslado interprovincial", 120.00),
        (5, "SRV-INS-05", "Instalación y Configuración de Equipos Comerciales", "Montaje comercial", 65.00),
    ])

    # Clientes (saldo_pendiente se genera con los documentos por cobrar iniciales)
    clientes = [
        (1, "1718293847001", "Distribuidora El Ahorro Cía. Ltda.", "contacto@elahorro.com.ec", "02-2451-890", "Av. América y Colón, Quito", 8000.0, 30),
        (2, "1791827364001", "Supermercado San José S.A.", "compras@sanjose.ec", "02-3104-500", "Calle 10 de Agosto N45-12, Quito", 12000.0, 45),
        (3, "1719283746", "Carlos Alberto Paredes Peña", "cparedes@gmail.com", "0998123456", "Villa Flora, Pasaje C N12, Quito", 1500.0, 15),
        (4, "1792348712001", "Comercial La Pradera Cía. Ltda.", "info@lapradera.ec", "02-2345-678", "Av. Prensa y Florida, Quito", 6000.0, 30),
        (5, "1720394857", "María Elena Morales Tapia", "mmorales@yahoo.es", "0987654321", "La Floresta, Guipuzcoa E12, Quito", 2000.0, 15),
        (6, "1793458921001", "Restaurante y Catering Tradición Andina", "gerencia@tradicionandina.ec", "02-2876-543", "Cumbayá, Plaza Central, Quito", 4500.0, 30),
        (7, "1715674892", "Jorge Luis Benítez Salazar", "jbenitez@hotmail.com", "0995432109", "Carcelén, Manzana 4 Villa 8, Quito", 1000.0, 15),
        (8, "1792456789001", "MiniMarket La Esquina Popular", "ventas@laesquina.ec", "02-2765-432", "Guamaní, Av. Maldonado S56, Quito", 3500.0, 20),
        (9, "1716789054", "Patricia del Rocío Gómez Alarcón", "pgomez@outlook.com", "0984321098", "El Batán, Gaspar de Villarroel E3, Quito", 1500.0, 15),
        (10, "1792876543001", "Bodega Central Mayorista del Norte", "bodega@elnorte.ec", "02-2543-210", "Calderón, Panamericana Norte Km 11, Quito", 10000.0, 30),
    ]
    _insert_many(db_path, """
        INSERT INTO clientes (id, identificacion, nombre_razon_social, email, telefono, direccion,
                              limite_credito, dias_credito, saldo_pendiente, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 1)
    """, clientes)

    proveedores = [
        (1, "1790012345001", "Pronaca Alimentos Procesados S.A.", "pedidos@pronaca.com.ec", "02-3987-000", "Durán - Tambo Km 4.5", 45),
        (2, "0990023456001", "La Fabril S.A. - Grasas y Aceites", "ventas@lafabril.com.ec", "05-2678-900", "Manta, Vía Interbarrial", 30),
        (3, "1790034567001", "Unilever Andina Ecuador S.A.", "distribucion@unilever.com", "04-2890-123", "Guayaquil, Vía a Daule Km 8.5", 30),
        (4, "1790045678001", "Colgate Palmolive del Ecuador C.A.", "ecuador@colpal.com", "02-2432-100", "Quito, Av. República y Eloy Alfaro", 30),
        (5, "1790056789001", "Nestlé Ecuador S.A.", "serviciocliente@nestle.com.ec", "02-2990-500", "Quito, Av. Naciones Unidas y Núñez de Vela", 45),
        (6, "1790067890001", "Molinos Champion S.A.", "molinos@champion.com.ec", "02-2678-432", "Quito, Panamericana Sur Km 9", 30),
        (7, "1790078901001", "Industrial Papelera Ecuatoriana S.A.", "pedidos@inpaec.com.ec", "02-2456-789", "Latacunga, Parque Industrial", 30),
        (8, "1790089012001", "Distribuidora Nacional de Lácteos ReyLeche", "ventas@reyleche.ec", "02-2890-543", "Machachi, Av. Pablo Guarderas", 20),
    ]
    _insert_many(db_path, """
        INSERT INTO proveedores (id, identificacion, razon_social, email, telefono, direccion,
                                 dias_credito, saldo_pendiente, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, 1)
    """, proveedores)

    productos = [
        (1, "PROD-001", "Alimentos", "Arroz Flor Especial Grano Largo 5kg", "Fardo/Saco", 3.80, 5.20, 120.0, 20.0, 500.0, 1, 6),
        (2, "PROD-002", "Alimentos", "Azúcar Blanca Refinada 2kg", "Bolsa", 1.40, 2.10, 100.0, 15.0, 400.0, 1, 6),
        (3, "PROD-003", "Alimentos", "Aceite Vegetal Palma Real 1 Litro", "Botella", 1.90, 2.85, 80.0, 15.0, 300.0, 1, 2),
        (4, "PROD-004", "Alimentos", "Leche Entera UHT Pasteurizada 1L", "TetraPak", 0.75, 1.10, 150.0, 30.0, 600.0, 1, 8),
        (5, "PROD-005", "Alimentos", "Harina de Trigo Especial Fortificada 1kg", "Funda", 0.85, 1.30, 90.0, 20.0, 350.0, 1, 6),
        (6, "PROD-006", "Bebidas", "Café Soluble Tradicional Instantáneo 200g", "Frasco", 2.60, 3.90, 60.0, 10.0, 250.0, 1, 5),
        (7, "PROD-007", "Limpieza", "Detergente en Polvo Floral Multiacción 1kg", "Funda", 1.80, 2.70, 75.0, 15.0, 300.0, 1, 3),
        (8, "PROD-008", "Higiene", "Jabón Líquido Antibacterial Manos 500ml", "Dispensador", 1.20, 1.95, 85.0, 15.0, 300.0, 1, 4),
        (9, "PROD-009", "Limpieza", "Desinfectante Multiusos Lavanda 1 Litro", "Galón/Bot", 1.10, 1.75, 70.0, 15.0, 250.0, 1, 3),
        (10, "PROD-010", "Higiene", "Papel Higiénico Doble Hoja Suave Pack x4", "Paquete", 1.30, 2.00, 110.0, 25.0, 450.0, 1, 7),
        (11, "PROD-011", "Higiene", "Pasta Dental Protección Anticaries 100ml", "Tubo", 1.15, 1.80, 95.0, 20.0, 350.0, 1, 4),
        (12, "PROD-012", "Higiene", "Champú Anticaspa Nutrición Profunda 400ml", "Botella", 2.80, 4.20, 50.0, 10.0, 200.0, 1, 3),
        (13, "PROD-013", "Alimentos", "Atún en Aceite Vegetal Lomitos 170g", "Lata", 1.10, 1.65, 130.0, 25.0, 500.0, 1, 1),
        (14, "PROD-014", "Alimentos", "Fideo Tallarín Supremo Clásico 400g", "Paquete", 0.60, 0.95, 140.0, 30.0, 500.0, 1, 6),
        (15, "PROD-015", "Alimentos", "Lenteja Seleccionada de Grano Seco 500g", "Funda", 0.70, 1.15, 80.0, 15.0, 300.0, 1, 1),
        (16, "PROD-016", "Alimentos", "Avena Molida Fortificada con Vitaminas 500g", "Funda", 0.65, 1.05, 90.0, 20.0, 350.0, 1, 5),
        (17, "PROD-017", "Limpieza", "Cloro Desinfectante Concentrado 1 Litro", "Botella", 0.80, 1.35, 100.0, 20.0, 400.0, 1, 3),
        (18, "PROD-018", "Limpieza", "Esponja Abrasiva Multiuso Pack x3 Unidades", "Pack", 0.90, 1.50, 120.0, 25.0, 450.0, 1, 3),
        (19, "PROD-019", "Bebidas", "Agua Purificada Mineral sin Gas 5 Litros", "Bidón", 1.10, 1.80, 65.0, 15.0, 250.0, 1, 5),
        (20, "PROD-020", "Alimentos", "Galletas de Sal Familiares Crackers Pack", "Paquete", 0.95, 1.50, 110.0, 20.0, 400.0, 1, 5),
    ]
    # La empresa simulada mantiene una cobertura aproximada de tres meses de stock por línea de
    # producto (comportamiento típico de una distribuidora mayorista de primera necesidad).
    productos = [(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7] * 3, p[8] * 3, p[9] * 3, p[10], p[11])
                 for p in productos]
    _insert_many(db_path, """
        INSERT INTO productos (id, codigo, categoria, descripcion, unidad_medida, costo_unitario,
                               precio_venta, stock_actual, stock_minimo, stock_maximo, aplica_iva, proveedor_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?)
    """, [(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[8], p[9], p[10], p[11]) for p in productos])

    PeriodService.set_param("origen_datos", "DEMOSTRACION",
                            "Los datos del sistema son de demostración con fines académicos.", db_path=db_path)
    return productos


# ----------------------------------------------------------------------------
# 2. Apertura: saldos iniciales, inventario inicial y cartera inicial
# ----------------------------------------------------------------------------
def _seed_apertura(db_path, productos):
    # Tuple de producto: (id, codigo, categoria, descripcion, unidad, costo_unitario, precio_venta,
    #                     stock_actual, stock_minimo, stock_maximo, aplica_iva, proveedor_id)
    inventario_inicial = round(sum(p[7] * p[5] for p in productos), 2)

    caja = 2450.00
    banco_pichincha = 18500.00
    banco_guayaquil = 8200.00
    cxc_inicial = 6590.00
    muebles, dep_muebles = 4500.00, 450.00
    computo, dep_computo = 3800.00, 760.00
    vehiculo, dep_vehiculo = 15000.00, 3000.00
    cxp_inicial = 13730.00
    prestamo = 5000.00
    capital = 25000.00
    reserva = 2500.00

    activos = (caja + banco_pichincha + banco_guayaquil + cxc_inicial + inventario_inicial
               + muebles - dep_muebles + computo - dep_computo + vehiculo - dep_vehiculo)
    pasivos_patrimonio_sin_utilidad = cxp_inicial + prestamo + capital + reserva
    utilidades_acumuladas = round(activos - pasivos_patrimonio_sin_utilidad, 2)

    lineas = [
        {"cuenta_id": 3, "debe": caja, "haber": 0.0, "referencia": "Saldo inicial Caja General"},
        {"cuenta_id": 4, "debe": banco_pichincha, "haber": 0.0, "referencia": "Saldo inicial Banco Pichincha"},
        {"cuenta_id": 5, "debe": banco_guayaquil, "haber": 0.0, "referencia": "Saldo inicial Banco Guayaquil"},
        {"cuenta_id": 6, "debe": cxc_inicial, "haber": 0.0, "referencia": "Cartera inicial de clientes"},
        {"cuenta_id": 8, "debe": inventario_inicial, "haber": 0.0, "referencia": "Inventario inicial de 20 productos"},
        {"cuenta_id": 12, "debe": muebles, "haber": 0.0, "referencia": "Muebles y enseres de oficina"},
        {"cuenta_id": 13, "debe": 0.0, "haber": dep_muebles, "referencia": "Depreciación acumulada muebles"},
        {"cuenta_id": 14, "debe": computo, "haber": 0.0, "referencia": "Equipo de cómputo y software"},
        {"cuenta_id": 15, "debe": 0.0, "haber": dep_computo, "referencia": "Depreciación acumulada cómputo"},
        {"cuenta_id": 16, "debe": vehiculo, "haber": 0.0, "referencia": "Vehículo de reparto"},
        {"cuenta_id": 17, "debe": 0.0, "haber": dep_vehiculo, "referencia": "Depreciación acumulada vehículo"},
        {"cuenta_id": 20, "debe": 0.0, "haber": cxp_inicial, "referencia": "Obligaciones iniciales con proveedores"},
        {"cuenta_id": 24, "debe": 0.0, "haber": prestamo, "referencia": "Préstamo bancario por pagar CP"},
        {"cuenta_id": 26, "debe": 0.0, "haber": capital, "referencia": "Capital social suscrito y pagado"},
        {"cuenta_id": 27, "debe": 0.0, "haber": reserva, "referencia": "Reserva legal"},
        {"cuenta_id": 28, "debe": 0.0, "haber": utilidades_acumuladas, "referencia": "Utilidades acumuladas de ejercicios anteriores"},
    ]
    asiento_id, numero = _asiento(
        PERIODO_INICIO, "Asiento de Apertura de Saldos Iniciales Período Abril 2026", lineas,
        "BALANCE_INICIAL", "BAL-INI-2026-01", "MANUAL"
    )
    _documento("COMPROBANTE_AJUSTE", "BAL-INI-2026-01", PERIODO_INICIO,
               "Comercial y Servicios Nueva Esperanza S.A.", "Contabilidad",
               round(activos, 2),
               "Comprobante del asiento de apertura de saldos iniciales del período Abril 2026",
               datos={"activos": round(activos, 2), "inventario_inicial": inventario_inicial,
                      "utilidades_acumuladas": utilidades_acumuladas},
               asiento_id=asiento_id)

    # Inventario inicial valorado con Kardex y lote FIFO por producto
    for p in productos:
        p_id, _cod, _cat, _desc, _und, costo, _pv, stock = p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]
        InventoryService.register_entry(
            p_id, stock, costo, tipo_movimiento="SALDO_INICIAL", tipo_documento="INVENTARIO_FISICO",
            numero_documento="INV-INI-2026-01", observaciones="Inventario inicial valorado al costo",
            asiento_id=asiento_id, fecha=PERIODO_INICIO, db_path=None
        )

    # Cartera inicial por cliente (documentos por cobrar) - suma 6.590,00
    cartera_inicial = [(1, 1250.00, "2026-04-15"), (2, 2300.00, "2026-05-15"), (4, 850.00, "2026-04-30"),
                       (5, 420.00, "2026-04-20"), (8, 680.00, "2026-04-25"), (10, 1090.00, "2026-05-10")]
    for cliente_id, monto, vencimiento in cartera_inicial:
        create_receivable(cliente_id, monto, f"FAC-INI-{cliente_id:04d}", "2026-03-31", vencimiento,
                          tipo_origen="SALDO_INICIAL")

    # Obligaciones iniciales con proveedores (suma 13.730,00)
    obligaciones_iniciales = [(1, 3400.00, "2026-05-10"), (2, 2150.00, "2026-04-30"), (3, 1820.00, "2026-04-30"),
                              (4, 940.00, "2026-04-25"), (5, 2780.00, "2026-05-15"), (6, 1100.00, "2026-04-28"),
                              (7, 650.00, "2026-04-27"), (8, 890.00, "2026-04-22")]
    for proveedor_id, monto, vencimiento in obligaciones_iniciales:
        create_payable(proveedor_id, monto, f"FAC-INI-PR{proveedor_id:03d}", "2026-03-31", vencimiento)

    TreasuryService.sync_cash_balance(1)
    TreasuryService.sync_bank_balance(1)
    TreasuryService.sync_bank_balance(2)
    return asiento_id, numero


# ----------------------------------------------------------------------------
# 3. Las 30 operaciones del período (transacciones relacionadas entre sí)
# ----------------------------------------------------------------------------
def _ids_asiento(db_path, tabla, registro_id, columnas):
    """Devuelve la lista de ids de asiento asociados a un registro operativo."""
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(f"SELECT {', '.join(columnas)} FROM {tabla} WHERE id = ?", (registro_id,)).fetchone()
        if not row:
            return []
        return [row[c] for c in columnas if row[c] is not None]
    finally:
        conn.close()


def _resolver_asientos(db_path, resultado):
    """Obtiene los asientos generados por una operación a partir de su registro operativo."""
    if "venta_id" in resultado:
        return _ids_asiento(db_path, "ventas", resultado["venta_id"], ("asiento_id", "asiento_costo_id"))
    if "servicio_tx_id" in resultado:
        return _ids_asiento(db_path, "transacciones_servicios", resultado["servicio_tx_id"], ("asiento_id",))
    if "cobro_id" in resultado:
        return _ids_asiento(db_path, "cobros", resultado["cobro_id"], ("asiento_id",))
    if "pago_id" in resultado:
        return _ids_asiento(db_path, "pagos", resultado["pago_id"], ("asiento_id",))
    if "compra_id" in resultado:
        return _ids_asiento(db_path, "compras", resultado["compra_id"], ("asiento_id",))
    return []


def _seed_operaciones(db_path):
    """Ejecuta las 30 operaciones del período a través de los servicios del sistema."""
    operaciones = []

    def reg(tipo, titulo, fecha, doc_tipo, doc_numero, resultado, asiento_ids, datos=None):
        if asiento_ids is None:
            asiento_ids = _resolver_asientos(db_path, resultado)
        operaciones.append({
            "tipo": tipo, "titulo": titulo, "fecha": fecha, "doc_tipo": doc_tipo,
            "doc_numero": doc_numero, "resultado": resultado, "asiento_ids": asiento_ids,
            "datos": datos or {},
        })

    # -------- O1: Venta de contado en efectivo
    venta_id, fac, total = SalesService.create_sale(
        EMPRESA_ID, 7,
        [{"producto_id": 1, "cantidad": 60, "precio_unitario": 5.20},
         {"producto_id": 3, "cantidad": 60, "precio_unitario": 2.85}],
        forma_pago="EFECTIVO", caja_id=1, usuario_id=USUARIO_ADMIN, fecha="2026-04-02"
    )
    reg("VENTA_CONTADO", "Venta de contado en efectivo (60 arroz + 60 aceite)",
        "2026-04-02", "FACTURA_VENTA", fac, {"venta_id": venta_id, "total": total}, None,
        {"cliente": "Jorge Luis Benítez Salazar", "forma_pago": "EFECTIVO"})

    # -------- O2: Prestación de servicio logístico cobrado por transferencia
    srv_id, fac_srv, total_srv = SalesService.create_service_transaction(
        EMPRESA_ID, 6, 1, cantidad=8, tarifa=45.0,
        descripcion="Distribución logística de víveres del período",
        forma_pago="TRANSFERENCIA", banco_id=1, usuario_id=USUARIO_ADMIN, fecha="2026-04-03"
    )
    reg("SERVICIO", "Servicio de entrega y distribución cobrado por transferencia",
        "2026-04-03", "FACTURA_SERVICIO", fac_srv, {"servicio_tx_id": srv_id, "total": total_srv}, None,
        {"cliente": "Restaurante y Catering Tradición Andina", "forma_pago": "TRANSFERENCIA"})

    # -------- O3: Compra de mercaderías pagada por transferencia
    compra_id, fac_com, total_com = PurchaseService.create_purchase(
        EMPRESA_ID, 1, "FAC-002-005-001890",
        [{"producto_id": 1, "cantidad": 400, "costo_unitario": 3.80},
         {"producto_id": 13, "cantidad": 300, "costo_unitario": 1.10},
         {"producto_id": 15, "cantidad": 200, "costo_unitario": 0.70}],
        forma_pago="TRANSFERENCIA", banco_id=1, usuario_id=USUARIO_ADMIN, fecha="2026-04-05"
    )
    reg("COMPRA_CONTADO", "Compra de arroz, atún y lenteja pagada por transferencia",
        "2026-04-05", "FACTURA_COMPRA", "FAC-002-005-001890", {"compra_id": compra_id}, None,
        {"proveedor": "Pronaca Alimentos Procesados S.A.", "total": total_com})

    # -------- O4: Compra de harina y fideo pagada en efectivo
    compra_id, fac_com, total_com = PurchaseService.create_purchase(
        EMPRESA_ID, 6, "FAC-006-002-004512",
        [{"producto_id": 5, "cantidad": 300, "costo_unitario": 0.85},
         {"producto_id": 14, "cantidad": 250, "costo_unitario": 0.60},
         {"producto_id": 2, "cantidad": 250, "costo_unitario": 1.40}],
        forma_pago="EFECTIVO", usuario_id=USUARIO_ADMIN, fecha="2026-04-06"
    )
    reg("COMPRA_CONTADO", "Compra de harina, fideo y azúcar pagada en efectivo",
        "2026-04-06", "FACTURA_COMPRA", "FAC-006-002-004512", {"compra_id": compra_id}, None,
        {"proveedor": "Molinos Champion S.A.", "total": total_com})

    # -------- O5: Venta a crédito 30 días a distribuidora
    venta_id, fac, total = SalesService.create_sale(
        EMPRESA_ID, 1,
        [{"producto_id": 1, "cantidad": 200, "precio_unitario": 5.20},
         {"producto_id": 10, "cantidad": 150, "precio_unitario": 2.00}],
        forma_pago="CREDITO", dias_credito=30, usuario_id=USUARIO_ADMIN, fecha="2026-04-07"
    )
    reg("VENTA_CREDITO", "Venta a crédito 30 días a Distribuidora El Ahorro",
        "2026-04-07", "FACTURA_VENTA", fac, {"venta_id": venta_id, "total": total}, None,
        {"cliente": "Distribuidora El Ahorro Cía. Ltda.", "forma_pago": "CRÉDITO 30 DÍAS"})

    # -------- O6: Venta de contado con cobro en cuenta de ahorros
    venta_id, fac, total = SalesService.create_sale(
        EMPRESA_ID, 5,
        [{"producto_id": 4, "cantidad": 150, "precio_unitario": 1.10},
         {"producto_id": 20, "cantidad": 100, "precio_unitario": 1.50},
         {"producto_id": 6, "cantidad": 60, "precio_unitario": 3.90}],
        forma_pago="TRANSFERENCIA", banco_id=2, usuario_id=USUARIO_ADMIN, fecha="2026-04-08"
    )
    reg("VENTA_CONTADO", "Venta de contado cobrada en cuenta de ahorros",
        "2026-04-08", "FACTURA_VENTA", fac, {"venta_id": venta_id, "total": total}, None,
        {"cliente": "María Elena Morales Tapia", "forma_pago": "TRANSFERENCIA"})

    # -------- O7: Compra a crédito 30 días de aceite
    compra_id, fac_com, total_com = PurchaseService.create_purchase(
        EMPRESA_ID, 2, "FAC-007-001-003421",
        [{"producto_id": 3, "cantidad": 250, "costo_unitario": 1.90}],
        forma_pago="CREDITO", dias_credito=30, usuario_id=USUARIO_ADMIN, fecha="2026-04-09"
    )
    reg("COMPRA_CREDITO", "Compra a crédito 30 días de aceite vegetal",
        "2026-04-09", "FACTURA_COMPRA", "FAC-007-001-003421", {"compra_id": compra_id}, None,
        {"proveedor": "La Fabril S.A. - Grasas y Aceites", "total": total_com})

    # -------- O8: Pago total de la compra anterior
    cxp = _ultima_cuenta_pagar(db_path, "FAC-007-001-003421")
    pago_id, nuevo_saldo, estado = PurchaseService.register_payment(
        cxp["id"], cxp["saldo_actual"], medio_pago="TRANSFERENCIA", banco_id=1,
        numero_comprobante="CE-2026-0031", usuario_id=USUARIO_ADMIN, fecha="2026-04-12"
    )
    reg("PAGO_PROVEEDOR", "Pago por transferencia de la compra de aceite (La Fabril)",
        "2026-04-12", "COMPROBANTE_EGRESO", "CE-2026-0031", {"pago_id": pago_id}, None,
        {"proveedor": "La Fabril S.A.", "monto": cxp["saldo_actual"], "estado": estado})

    # -------- O9: Compra a crédito 45 días (lácteos, café y avena)
    compra_id, fac_com, total_com = PurchaseService.create_purchase(
        EMPRESA_ID, 5, "FAC-005-003-009122",
        [{"producto_id": 4, "cantidad": 250, "costo_unitario": 0.75},
         {"producto_id": 16, "cantidad": 200, "costo_unitario": 0.65},
         {"producto_id": 6, "cantidad": 120, "costo_unitario": 2.60}],
        forma_pago="CREDITO", dias_credito=45, usuario_id=USUARIO_ADMIN, fecha="2026-04-13"
    )
    reg("COMPRA_CREDITO", "Compra a crédito 45 días de lácteos, avena y café",
        "2026-04-13", "FACTURA_COMPRA", "FAC-005-003-009122", {"compra_id": compra_id}, None,
        {"proveedor": "Nestlé Ecuador S.A.", "total": total_com})

    # -------- O10: Venta de contado en efectivo (consumidor final)
    venta_id, fac, total = SalesService.create_sale(
        EMPRESA_ID, 3,
        [{"producto_id": 1, "cantidad": 100, "precio_unitario": 5.20},
         {"producto_id": 14, "cantidad": 150, "precio_unitario": 0.95},
         {"producto_id": 2, "cantidad": 80, "precio_unitario": 2.10}],
        forma_pago="EFECTIVO", caja_id=1, usuario_id=USUARIO_ADMIN, fecha="2026-04-14"
    )
    reg("VENTA_CONTADO", "Venta de contado en efectivo a cliente final",
        "2026-04-14", "FACTURA_VENTA", fac, {"venta_id": venta_id, "total": total}, None,
        {"cliente": "Carlos Alberto Paredes Peña", "forma_pago": "EFECTIVO"})

    # -------- O11: Servicio de asesoría a crédito 30 días
    srv_id, fac_srv, total_srv = SalesService.create_service_transaction(
        EMPRESA_ID, 10, 2, cantidad=3, tarifa=150.0,
        descripcion="Asesoría administrativa y de gestión contable",
        forma_pago="CREDITO", dias_credito=30, usuario_id=USUARIO_ADMIN, fecha="2026-04-15"
    )
    reg("SERVICIO", "Servicio de asesoría administrativa a crédito 30 días",
        "2026-04-15", "FACTURA_SERVICIO", fac_srv, {"servicio_tx_id": srv_id, "total": total_srv}, None,
        {"cliente": "Bodega Central Mayorista del Norte", "forma_pago": "CRÉDITO 30 DÍAS"})

    # -------- O12: Compra de productos de limpieza por transferencia
    compra_id, fac_com, total_com = PurchaseService.create_purchase(
        EMPRESA_ID, 3, "FAC-003-002-007810",
        [{"producto_id": 7, "cantidad": 150, "costo_unitario": 1.80},
         {"producto_id": 9, "cantidad": 150, "costo_unitario": 1.10},
         {"producto_id": 17, "cantidad": 120, "costo_unitario": 0.80}],
        forma_pago="TRANSFERENCIA", banco_id=1, usuario_id=USUARIO_ADMIN, fecha="2026-04-16"
    )
    reg("COMPRA_CONTADO", "Compra de productos de limpieza pagada por transferencia",
        "2026-04-16", "FACTURA_COMPRA", "FAC-003-002-007810", {"compra_id": compra_id}, None,
        {"proveedor": "Unilever Andina Ecuador S.A.", "total": total_com})

    # -------- O13: Venta a crédito 30 días a supermercado
    venta_id, fac, total = SalesService.create_sale(
        EMPRESA_ID, 2,
        [{"producto_id": 1, "cantidad": 300, "precio_unitario": 5.20},
         {"producto_id": 2, "cantidad": 200, "precio_unitario": 2.10},
         {"producto_id": 5, "cantidad": 150, "precio_unitario": 1.30}],
        forma_pago="CREDITO", dias_credito=30, usuario_id=USUARIO_ADMIN, fecha="2026-04-17"
    )
    reg("VENTA_CREDITO", "Venta a crédito 30 días a Supermercado San José",
        "2026-04-17", "FACTURA_VENTA", fac, {"venta_id": venta_id, "total": total}, None,
        {"cliente": "Supermercado San José S.A.", "forma_pago": "CRÉDITO 30 DÍAS"})

    # -------- O14: Arriendo del local (gasto con IVA, pago por transferencia)
    asiento_id, numero = _asiento(
        "2026-04-18", "Pago del arriendo del local comercial correspondiente a Abril 2026",
        [{"cuenta_id": 38, "debe": 400.00, "haber": 0.0, "referencia": "Arriendo de local comercial"},
         {"cuenta_id": 9, "debe": 60.00, "haber": 0.0, "referencia": "IVA 15% en compras"},
         {"cuenta_id": 4, "debe": 0.0, "haber": 460.00, "referencia": "Transferencia Banco Pichincha"}],
        "FACTURA_COMPRA", "FAC-000112", "COMPRAS"
    )
    TreasuryService.register_bank_movement(1, "TRANSFERENCIA_EMITIDA", 460.00,
                                           "Arriendo local comercial abril 2026",
                                           numero_referencia="FAC-000112", asiento_id=asiento_id,
                                           fecha="2026-04-18")
    _documento("FACTURA_COMPRA", "FAC-000112", "2026-04-18", "Inmobiliaria Los Andes",
               "Comercial y Servicios Nueva Esperanza S.A.", 460.00,
               "Arriendo del local comercial del mes de abril 2026 (incluye IVA)",
               datos={"subtotal": 400.00, "iva": 60.00, "total": 460.00}, asiento_id=asiento_id)
    reg("GASTO", "Pago del arriendo del local comercial (gasto administrativo)",
        "2026-04-18", "FACTURA_COMPRA", "FAC-000112", {"asiento": numero}, [asiento_id],
        {"concepto": "Arriendo de local", "monto": 460.00})

    # -------- O15: Servicios básicos pagados en efectivo
    asiento_id, numero = _asiento(
        "2026-04-19", "Pago de servicios básicos (energía eléctrica, agua e internet) del período",
        [{"cuenta_id": 39, "debe": 135.00, "haber": 0.0, "referencia": "Servicios básicos"},
         {"cuenta_id": 9, "debe": 20.25, "haber": 0.0, "referencia": "IVA 15% en compras"},
         {"cuenta_id": 3, "debe": 0.0, "haber": 155.25, "referencia": "Pago en efectivo de caja"}],
        "FACTURA_COMPRA", "FAC-009871", "COMPRAS"
    )
    TreasuryService.register_cash_movement(1, "EGRESO", 155.25,
                                           "Servicios básicos abril 2026",
                                           numero_comprobante="FAC-009871", asiento_id=asiento_id,
                                           fecha="2026-04-19")
    _documento("FACTURA_COMPRA", "FAC-009871", "2026-04-19", "Empresa Eléctrica Quito / EPMAPS / CNT",
               "Comercial y Servicios Nueva Esperanza S.A.", 155.25,
               "Servicios básicos del período (energía, agua e internet)",
               datos={"subtotal": 135.00, "iva": 20.25, "total": 155.25}, asiento_id=asiento_id)
    reg("GASTO", "Pago de servicios básicos en efectivo",
        "2026-04-19", "FACTURA_COMPRA", "FAC-009871", {"asiento": numero}, [asiento_id],
        {"concepto": "Servicios básicos", "monto": 155.25})

    # -------- O16: Cobro de cartera inicial del Supermercado San José
    cxc = _cuenta_cobrar_de_cliente(db_path, cliente_id=2, documento="FAC-INI-0002")
    cobro_id, nuevo_saldo, estado = SalesService.register_collection(
        cxc["id"], 1500.00, medio_pago="TRANSFERENCIA", banco_id=2,
        numero_comprobante="CI-2026-0045", usuario_id=USUARIO_ADMIN, fecha="2026-04-20"
    )
    reg("COBRO_CARTERA", "Cobro por transferencia de cartera inicial (Supermercado San José)",
        "2026-04-20", "COMPROBANTE_INGRESO", "CI-2026-0045", {"cobro_id": cobro_id}, None,
        {"cliente": "Supermercado San José S.A.", "monto": 1500.00, "estado": estado})

    # -------- O17: Depósito de la recaudación en efectivo al banco
    asiento_id, numero = _asiento(
        "2026-04-21", "Depósito de la recaudación en efectivo a la cuenta corriente del Banco Pichincha",
        [{"cuenta_id": 4, "debe": 1800.00, "haber": 0.0, "referencia": "Depósito en Banco Pichincha"},
         {"cuenta_id": 3, "debe": 0.0, "haber": 1800.00, "referencia": "Salida de Caja General"}],
        "PAPELETA_DEPOSITO", "DEP-00874", "CAJA"
    )
    TreasuryService.register_cash_movement(1, "DEPOSITO_BANCO", 1800.00,
                                           "Depósito de recaudación al Banco Pichincha",
                                           numero_comprobante="DEP-00874", asiento_id=asiento_id,
                                           fecha="2026-04-21")
    TreasuryService.register_bank_movement(1, "DEPOSITO", 1800.00,
                                           "Depósito de recaudación en efectivo",
                                           numero_referencia="DEP-00874", asiento_id=asiento_id,
                                           fecha="2026-04-21")
    _documento("PAPELETA_DEPOSITO", "DEP-00874", "2026-04-21",
               "Comercial y Servicios Nueva Esperanza S.A.", "Banco Pichincha", 1800.00,
               "Papeleta de depósito de la recaudación en efectivo del período",
               datos={"banco": "Banco Pichincha", "cuenta": "2100874521", "monto": 1800.00},
               asiento_id=asiento_id)
    reg("DEPOSITO_BANCO", "Depósito de recaudación en efectivo al banco",
        "2026-04-21", "PAPELETA_DEPOSITO", "DEP-00874", {"asiento": numero}, [asiento_id],
        {"monto": 1800.00})

    # -------- O18: Venta de contado cobrada por transferencia (minimarket)
    venta_id, fac, total = SalesService.create_sale(
        EMPRESA_ID, 8,
        [{"producto_id": 11, "cantidad": 120, "precio_unitario": 1.80},
         {"producto_id": 8, "cantidad": 100, "precio_unitario": 1.95},
         {"producto_id": 18, "cantidad": 150, "precio_unitario": 1.50}],
        forma_pago="TRANSFERENCIA", banco_id=1, usuario_id=USUARIO_ADMIN, fecha="2026-04-22"
    )
    reg("VENTA_CONTADO", "Venta de contado cobrada por transferencia (MiniMarket)",
        "2026-04-22", "FACTURA_VENTA", fac, {"venta_id": venta_id, "total": total}, None,
        {"cliente": "MiniMarket La Esquina Popular", "forma_pago": "TRANSFERENCIA"})

    # -------- O19: Servicio de mantenimiento cobrado por transferencia
    srv_id, fac_srv, total_srv = SalesService.create_service_transaction(
        EMPRESA_ID, 4, 3, cantidad=6, tarifa=80.0,
        descripcion="Mantenimiento preventivo y limpieza de instalaciones",
        forma_pago="TRANSFERENCIA", banco_id=1, usuario_id=USUARIO_ADMIN, fecha="2026-04-23"
    )
    reg("SERVICIO", "Servicio de mantenimiento preventivo cobrado por transferencia",
        "2026-04-23", "FACTURA_SERVICIO", fac_srv, {"servicio_tx_id": srv_id, "total": total_srv}, None,
        {"cliente": "Comercial La Pradera Cía. Ltda.", "forma_pago": "TRANSFERENCIA"})

    # -------- O20: Cobro en efectivo de cartera inicial
    cxc = _cuenta_cobrar_de_cliente(db_path, cliente_id=4, documento="FAC-INI-0004")
    cobro_id, nuevo_saldo, estado = SalesService.register_collection(
        cxc["id"], 850.00, medio_pago="EFECTIVO", caja_id=1,
        numero_comprobante="CI-2026-0046", usuario_id=USUARIO_ADMIN, fecha="2026-04-24"
    )
    reg("COBRO_CARTERA", "Cobro en efectivo de cartera inicial (Comercial La Pradera)",
        "2026-04-24", "COMPROBANTE_INGRESO", "CI-2026-0046", {"cobro_id": cobro_id}, None,
        {"cliente": "Comercial La Pradera Cía. Ltda.", "monto": 850.00, "estado": estado})

    # -------- O21: Publicidad digital (gasto de ventas)
    asiento_id, numero = _asiento(
        "2026-04-25", "Campaña publicitaria digital del mes de abril 2026",
        [{"cuenta_id": 41, "debe": 150.00, "haber": 0.0, "referencia": "Gasto publicidad y marketing"},
         {"cuenta_id": 9, "debe": 22.50, "haber": 0.0, "referencia": "IVA 15% en compras"},
         {"cuenta_id": 5, "debe": 0.0, "haber": 172.50, "referencia": "Transferencia Banco Guayaquil"}],
        "FACTURA_COMPRA", "FAC-000541", "COMPRAS"
    )
    TreasuryService.register_bank_movement(2, "TRANSFERENCIA_EMITIDA", 172.50,
                                           "Campaña publicitaria digital abril 2026",
                                           numero_referencia="FAC-000541", asiento_id=asiento_id,
                                           fecha="2026-04-25")
    _documento("FACTURA_COMPRA", "FAC-000541", "2026-04-25", "Agencia Digital Andina",
               "Comercial y Servicios Nueva Esperanza S.A.", 172.50,
               "Campaña publicitaria digital del período (incluye IVA)",
               datos={"subtotal": 150.00, "iva": 22.50, "total": 172.50}, asiento_id=asiento_id)
    reg("GASTO", "Gasto de publicidad y marketing pagado por transferencia",
        "2026-04-25", "FACTURA_COMPRA", "FAC-000541", {"asiento": numero}, [asiento_id],
        {"concepto": "Publicidad y marketing", "monto": 172.50})

    # -------- O22: Mantenimiento del vehículo de reparto
    asiento_id, numero = _asiento(
        "2026-04-26", "Mantenimiento preventivo del vehículo de reparto",
        [{"cuenta_id": 42, "debe": 90.00, "haber": 0.0, "referencia": "Mantenimiento de vehículo"},
         {"cuenta_id": 9, "debe": 13.50, "haber": 0.0, "referencia": "IVA 15% en compras"},
         {"cuenta_id": 4, "debe": 0.0, "haber": 103.50, "referencia": "Cheque Banco Pichincha"}],
        "FACTURA_COMPRA", "FAC-000089", "COMPRAS"
    )
    TreasuryService.register_bank_movement(1, "CHEQUE", 103.50,
                                           "Mantenimiento vehículo de reparto",
                                           numero_referencia="FAC-000089", asiento_id=asiento_id,
                                           fecha="2026-04-26")
    _documento("FACTURA_COMPRA", "FAC-000089", "2026-04-26", "Taller Automotriz Central",
               "Comercial y Servicios Nueva Esperanza S.A.", 103.50,
               "Mantenimiento preventivo del vehículo de reparto (incluye IVA)",
               datos={"subtotal": 90.00, "iva": 13.50, "total": 103.50}, asiento_id=asiento_id)
    reg("GASTO", "Mantenimiento del vehículo de reparto pagado con cheque",
        "2026-04-26", "FACTURA_COMPRA", "FAC-000089", {"asiento": numero}, [asiento_id],
        {"concepto": "Mantenimiento de vehículo", "monto": 103.50})

    # -------- O23: Pago del rol de sueldos del personal
    asiento_id, numero = _asiento(
        "2026-04-27", "Pago del rol de sueldos del personal administrativo Abril 2026",
        [{"cuenta_id": 37, "debe": 1200.00, "haber": 0.0, "referencia": "Sueldos y salarios del período"},
         {"cuenta_id": 4, "debe": 0.0, "haber": 1200.00, "referencia": "Transferencia de nómina Banco Pichincha"}],
        "ROL_PAGOS", "ROL-2026-04", "MANUAL"
    )
    TreasuryService.register_bank_movement(1, "TRANSFERENCIA_EMITIDA", 1200.00,
                                           "Pago de rol de sueldos Abril 2026",
                                           numero_referencia="ROL-2026-04", asiento_id=asiento_id,
                                           fecha="2026-04-27")
    _documento("ROL_PAGOS", "ROL-2026-04", "2026-04-27",
               "Comercial y Servicios Nueva Esperanza S.A.", "Personal administrativo", 1200.00,
               "Rol de pagos del personal administrativo del mes de abril 2026",
               datos={"total_rol": 1200.00, "empleados": 4, "periodo": "Abril 2026"}, asiento_id=asiento_id)
    reg("GASTO", "Pago del rol de sueldos del personal",
        "2026-04-27", "ROL_PAGOS", "ROL-2026-04", {"asiento": numero}, [asiento_id],
        {"concepto": "Sueldos y salarios", "monto": 1200.00})

    # -------- O24: Pago parcial a proveedor Colgate Palmolive
    cxp = _cuenta_pagar_de_proveedor(db_path, proveedor_id=4, factura="FAC-INI-PR004")
    pago_id, nuevo_saldo, estado = PurchaseService.register_payment(
        cxp["id"], 600.00, medio_pago="TRANSFERENCIA", banco_id=1,
        numero_comprobante="CE-2026-0034", usuario_id=USUARIO_ADMIN, fecha="2026-04-27"
    )
    reg("PAGO_PROVEEDOR", "Pago parcial de obligación inicial (Colgate Palmolive)",
        "2026-04-27", "COMPROBANTE_EGRESO", "CE-2026-0034", {"pago_id": pago_id}, None,
        {"proveedor": "Colgate Palmolive del Ecuador C.A.", "monto": 600.00, "estado": estado})

    # -------- O25: Arqueo de caja con faltante y su regularización
    saldo_contable_caja = AccountingService.get_account_balance(3)
    arqueo = TreasuryService.perform_cash_count(
        1, round(saldo_contable_caja - 5.00, 2),
        observaciones="Arqueo de caja del período con faltante menor no imputable a terceros",
        usuario_id=USUARIO_ADMIN, fecha="2026-04-28"
    )
    asiento_id, numero = _asiento(
        "2026-04-28", "Regularización de faltante de caja determinado en arqueo",
        [{"cuenta_id": 43, "debe": 5.00, "haber": 0.0, "referencia": "Faltante de caja en arqueo"},
         {"cuenta_id": 3, "debe": 0.0, "haber": 5.00, "referencia": "Ajuste Caja General"}],
        "ARQUEO_CAJA", "ARQ-2026-04-28", "AJUSTES"
    )
    _documento("ARQUEO_CAJA", "ARQ-2026-04-28", "2026-04-28",
               "Comercial y Servicios Nueva Esperanza S.A.", "Caja Principal Ventas", 5.00,
               "Acta de arqueo de caja con faltante de $5,00 regularizado contra gastos financieros",
               datos={"saldo_contable": arqueo["saldo_contable"], "saldo_fisico": arqueo["saldo_fisico"],
                      "diferencia": arqueo["diferencia"]}, asiento_id=asiento_id)
    reg("ARQUEO_CAJA", "Arqueo de caja con faltante y regularización contable",
        "2026-04-28", "ARQUEO_CAJA", "ARQ-2026-04-28", {"arqueo_id": arqueo["id"], "asiento": numero},
        [asiento_id], {"saldo_contable": arqueo["saldo_contable"], "diferencia": arqueo["diferencia"]})

    # -------- O26: Nota de débito bancaria por comisiones
    asiento_id, numero = _asiento(
        "2026-04-29", "Nota de débito del Banco Pichincha por comisiones y mantenimiento de cuenta",
        [{"cuenta_id": 43, "debe": 18.50, "haber": 0.0, "referencia": "Comisiones bancarias"},
         {"cuenta_id": 4, "debe": 0.0, "haber": 18.50, "referencia": "Débito Banco Pichincha"}],
        "NOTA_DEBITO_BCO", "ND-99812", "BANCOS"
    )
    TreasuryService.register_bank_movement(1, "NOTA_DEBITO", 18.50,
                                           "Comisiones y mantenimiento de cuenta",
                                           numero_referencia="ND-99812", asiento_id=asiento_id,
                                           fecha="2026-04-29")
    _documento("NOTA_DEBITO_BCO", "ND-99812", "2026-04-29", "Banco Pichincha",
               "Comercial y Servicios Nueva Esperanza S.A.", 18.50,
               "Nota de débito por comisiones y mantenimiento de cuenta corriente",
               datos={"banco": "Banco Pichincha", "cuenta": "2100874521", "concepto": "Comisiones bancarias"},
               asiento_id=asiento_id)
    reg("NOTA_BANCARIA", "Nota de débito bancaria por comisiones",
        "2026-04-29", "NOTA_DEBITO_BCO", "ND-99812", {"asiento": numero}, [asiento_id],
        {"monto": 18.50})

    # -------- O27: Ajuste de depreciación de activos fijos
    asiento_id, numero = _asiento(
        "2026-04-30", "Ajuste mensual de depreciación de activos fijos por línea recta (Abril 2026)",
        [{"cuenta_id": 40, "debe": 350.83, "haber": 0.0, "referencia": "Gasto depreciación del mes"},
         {"cuenta_id": 13, "debe": 0.0, "haber": 37.50, "referencia": "Depreciación acumulada muebles"},
         {"cuenta_id": 15, "debe": 0.0, "haber": 63.33, "referencia": "Depreciación acumulada cómputo"},
         {"cuenta_id": 17, "debe": 0.0, "haber": 250.00, "referencia": "Depreciación acumulada vehículo"}],
        "COMPROBANTE_AJUSTE", "AJU-DEP-2026-04", "AJUSTES"
    )
    _documento("COMPROBANTE_AJUSTE", "AJU-DEP-2026-04", "2026-04-30",
               "Comercial y Servicios Nueva Esperanza S.A.", "Contabilidad", 350.83,
               "Comprobante de ajuste por depreciación mensual de activos fijos",
               datos={"muebles": 37.50, "computo": 63.33, "vehiculo": 250.00, "total": 350.83},
               asiento_id=asiento_id)
    reg("AJUSTE_DEPRECIACION", "Ajuste mensual de depreciación de activos fijos",
        "2026-04-30", "COMPROBANTE_AJUSTE", "AJU-DEP-2026-04", {"asiento": numero}, [asiento_id],
        {"total_depreciacion": 350.83})

    # -------- O28: Ajuste de provisión de cuentas incobrables
    asiento_id, numero = _asiento(
        "2026-04-30", "Ajuste de provisión de cuentas incobrables (1% sobre cartera vigente)",
        [{"cuenta_id": 43, "debe": 45.00, "haber": 0.0, "referencia": "Gasto provisión incobrables"},
         {"cuenta_id": 7, "debe": 0.0, "haber": 45.00, "referencia": "Provisión cuentas incobrables"}],
        "COMPROBANTE_AJUSTE", "AJU-INC-2026-04", "AJUSTES"
    )
    _documento("COMPROBANTE_AJUSTE", "AJU-INC-2026-04", "2026-04-30",
               "Comercial y Servicios Nueva Esperanza S.A.", "Contabilidad", 45.00,
               "Comprobante de ajuste por provisión de cuentas incobrables del período",
               datos={"porcentaje": 1.0, "monto": 45.00}, asiento_id=asiento_id)
    reg("AJUSTE_PROVISION", "Ajuste de provisión de cuentas incobrables",
        "2026-04-30", "COMPROBANTE_AJUSTE", "AJU-INC-2026-04", {"asiento": numero}, [asiento_id],
        {"monto": 45.00})

    # -------- O29: Nota de crédito bancaria por intereses ganados
    asiento_id, numero = _asiento(
        "2026-04-30", "Nota de crédito del Banco Guayaquil por intereses ganados en cuenta de ahorros",
        [{"cuenta_id": 5, "debe": 24.50, "haber": 0.0, "referencia": "Acreditación de intereses"},
         {"cuenta_id": 33, "debe": 0.0, "haber": 24.50, "referencia": "Intereses ganados"}],
        "NOTA_CREDITO_BCO", "NC-10458", "BANCOS"
    )
    TreasuryService.register_bank_movement(2, "NOTA_CREDITO", 24.50,
                                           "Intereses ganados en cuenta de ahorros",
                                           numero_referencia="NC-10458", asiento_id=asiento_id,
                                           fecha="2026-04-30")
    _documento("NOTA_CREDITO_BCO", "NC-10458", "2026-04-30", "Banco Guayaquil",
               "Comercial y Servicios Nueva Esperanza S.A.", 24.50,
               "Nota de crédito por intereses ganados en la cuenta de ahorros",
               datos={"banco": "Banco Guayaquil", "cuenta": "10458932", "concepto": "Intereses ganados"},
               asiento_id=asiento_id)
    reg("NOTA_BANCARIA", "Nota de crédito bancaria por intereses ganados",
        "2026-04-30", "NOTA_CREDITO_BCO", "NC-10458", {"asiento": numero}, [asiento_id],
        {"monto": 24.50})

    # -------- O30: Compensación del IVA del período (débito fiscal vs crédito tributario)
    iva_ventas = AccountingService.get_account_balance(21)
    iva_compras = AccountingService.get_account_balance(9)
    monto_compensacion = round(min(iva_ventas, iva_compras), 2)
    if monto_compensacion > 0:
        asiento_id, numero = _asiento(
            "2026-04-30", "Compensación del IVA del período: débito fiscal contra crédito tributario",
            [{"cuenta_id": 21, "debe": monto_compensacion, "haber": 0.0, "referencia": "Débito fiscal compensado"},
             {"cuenta_id": 9, "debe": 0.0, "haber": monto_compensacion, "referencia": "Crédito tributario aplicado"}],
            "COMPROBANTE_AJUSTE", "AJU-IVA-2026-04", "AJUSTES"
        )
        _documento("COMPROBANTE_AJUSTE", "AJU-IVA-2026-04", "2026-04-30",
                   "Comercial y Servicios Nueva Esperanza S.A.", "SRI (referencial académico)",
                   monto_compensacion,
                   "Comprobante de compensación del IVA en ventas contra el IVA en compras del período",
                   datos={"iva_ventas": iva_ventas, "iva_compras": iva_compras,
                          "compensado": monto_compensacion,
                          "saldo_iva_por_pagar": round(iva_ventas - monto_compensacion, 2)},
                   asiento_id=asiento_id)
        reg("AJUSTE_IMPUESTOS", "Compensación del IVA del período",
            "2026-04-30", "COMPROBANTE_AJUSTE", "AJU-IVA-2026-04", {"asiento": numero}, [asiento_id],
            {"compensado": monto_compensacion})

    # Sincronización final de saldos de tesorería con el Libro Mayor
    TreasuryService.sync_cash_balance(1)
    TreasuryService.sync_bank_balance(1)
    TreasuryService.sync_bank_balance(2)
    return operaciones


def _ultima_cuenta_pagar(db_path, numero_factura):
    conn = get_db_connection(db_path)
    try:
        row = conn.execute("""
            SELECT * FROM cuentas_pagar WHERE numero_factura = ? ORDER BY id DESC LIMIT 1
        """, (numero_factura,)).fetchone()
        if not row:
            raise ValueError(f"No existe cuenta por pagar para la factura {numero_factura}.")
        return dict(row)
    finally:
        conn.close()


def _cuenta_cobrar_de_cliente(db_path, cliente_id, documento=None):
    conn = get_db_connection(db_path)
    try:
        if documento:
            row = conn.execute("""
                SELECT * FROM cuentas_cobrar WHERE cliente_id = ? AND numero_documento = ?
                ORDER BY id DESC LIMIT 1
            """, (cliente_id, documento)).fetchone()
        else:
            row = conn.execute("""
                SELECT * FROM cuentas_cobrar WHERE cliente_id = ? AND estado != 'PAGADA'
                ORDER BY id DESC LIMIT 1
            """, (cliente_id,)).fetchone()
        if not row:
            raise ValueError(f"No existe cuenta por cobrar pendiente para el cliente {cliente_id}.")
        return dict(row)
    finally:
        conn.close()


def _cuenta_pagar_de_proveedor(db_path, proveedor_id, factura=None):
    conn = get_db_connection(db_path)
    try:
        if factura:
            row = conn.execute("""
                SELECT * FROM cuentas_pagar WHERE proveedor_id = ? AND numero_factura = ?
                ORDER BY id DESC LIMIT 1
            """, (proveedor_id, factura)).fetchone()
        else:
            row = conn.execute("""
                SELECT * FROM cuentas_pagar WHERE proveedor_id = ? AND estado != 'PAGADA'
                ORDER BY id DESC LIMIT 1
            """, (proveedor_id,)).fetchone()
        if not row:
            raise ValueError(f"No existe obligación pendiente para el proveedor {proveedor_id}.")
        return dict(row)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# 4. Simulaciones y casos generados desde los asientos reales
# ----------------------------------------------------------------------------
PISTAS_POR_TIPO = {
    "VENTA_CONTADO": [
        "El dinero ingresa a la empresa: piensa qué cuenta de Activo aumenta (Caja o Banco).",
        "El ingreso por venta de bienes se acredita y el IVA cobrado al cliente constituye un pasivo con el fisco.",
        "En inventario perpetuo, la venta genera un segundo asiento: Costo de Mercaderías Vendidas (Debe) contra Inventario (Haber).",
    ],
    "VENTA_CREDITO": [
        "No hay entrada de efectivo: nace un derecho de cobro (Activo).",
        "Acredita el ingreso por ventas y el IVA Ventas (débito fiscal) por el valor total de la factura.",
        "Recuerda registrar también la salida de inventario contra Costo de Mercaderías Vendidas.",
    ],
    "SERVICIO": [
        "Los servicios prestados se registran en una cuenta de ingreso diferente a la de venta de bienes.",
        "Identifica si el cobro fue en efectivo, por transferencia o a crédito para elegir la cuenta deudora.",
        "El IVA generado se acredita en IVA Ventas (débito fiscal).",
    ],
    "COMPRA_CONTADO": [
        "La compra de mercaderías incrementa el activo Inventario de Mercaderías.",
        "El IVA pagado al proveedor es crédito tributario (Activo) y no un gasto.",
        "La salida de efectivo o banco se acredita por el total de la factura.",
    ],
    "COMPRA_CREDITO": [
        "Al no pagar de inmediato, nace una obligación: Cuentas por Pagar Proveedores.",
        "Debita el Inventario de Mercaderías y el IVA Compras por el valor correspondiente.",
        "Acredita Cuentas por Pagar Proveedores por el total de la factura.",
    ],
    "COBRO_CARTERA": [
        "El cobro extingue parcial o totalmente el derecho de cobro del cliente.",
        "El dinero puede ingresar a Caja (efectivo) o a Bancos (transferencia).",
        "Acredita Cuentas por Cobrar Clientes por el valor recaudado.",
    ],
    "PAGO_PROVEEDOR": [
        "El pago reduce la obligación con el proveedor.",
        "Debita Cuentas por Pagar Proveedores.",
        "Acredita la cuenta de Caja o Banco que entrega los fondos.",
    ],
    "DEPOSITO_BANCO": [
        "Es una transferencia entre cuentas: aumenta Bancos y disminuye Caja.",
        "No genera ingresos ni gastos.",
        "Debita la cuenta bancaria y acredita Caja General.",
    ],
    "GASTO": [
        "Identifica qué gasto específico se está reconociendo (sueldos, arriendo, servicios, publicidad, mantenimiento).",
        "Si la factura incluye IVA acreditable, regístralo como crédito tributario.",
        "Acredita la cuenta de Caja o Banco que realizó el pago.",
    ],
    "NOTA_BANCARIA": [
        "Revisa si la nota aumenta o disminuye el disponible bancario.",
        "Una comisión bancaria es un gasto financiero; los intereses ganados son otro ingreso.",
        "Debita o acredita la cuenta bancaria según corresponda.",
    ],
    "AJUSTE_DEPRECIACION": [
        "La depreciación es un gasto que no significa salida de efectivo.",
        "Debita la cuenta de gasto depreciación.",
        "Acredita cada cuenta de Depreciación Acumulada (cuenta complementaria de activo) por el valor de cada activo.",
    ],
    "AJUSTE_PROVISION": [
        "La provisión anticipa una posible pérdida de cartera.",
        "Debita la cuenta de gasto correspondiente.",
        "Acredita la Provisión de Cuentas Incobrables (cuenta de valuación del activo).",
    ],
    "ARQUEO_CAJA": [
        "Compara el saldo contable de Caja con el conteo físico del dinero.",
        "Si existe faltante, el gasto se debita y Caja se acredita por la diferencia.",
        "Un sobrante implicaría el registro inverso (débito a Caja).",
    ],
    "AJUSTE_IMPUESTOS": [
        "El IVA en ventas (débito fiscal) se compensa con el IVA en compras (crédito tributario).",
        "Se debita IVA Ventas y se acredita IVA Compras por el valor compensado.",
        "La diferencia residual representa el IVA por pagar o el crédito a favor.",
    ],
}

EXPLICACION_POR_TIPO = {
    "VENTA_CONTADO": "En una venta de contado con inventario perpetuo se registran dos asientos: (1) Debe Caja o Banco por el total facturado, Haber Ingresos por Ventas por el subtotal y Haber IVA Ventas por el impuesto; (2) Debe Costo de Mercaderías Vendidas y Haber Inventario de Mercaderías por el costo de las unidades entregadas.",
    "VENTA_CREDITO": "En una venta a crédito el activo que aumenta es Cuentas por Cobrar Clientes (no Caja), por el total de la factura. El ingreso se reconoce en el momento de la venta por el principio de devengo, y el inventario sale contra Costo de Mercaderías Vendidas.",
    "SERVICIO": "Los ingresos por prestación de servicios se registran en la cuenta 4.1.02, separada de la venta de bienes (4.1.01). No generan costo de mercaderías vendidas porque no implican salida de inventario; el IVA cobrado es débito fiscal.",
    "COMPRA_CONTADO": "Toda compra de mercaderías con inventario perpetuo se debita directamente a Inventario de Mercaderías. El IVA pagado al proveedor es crédito tributario (activo) y se compensa con el débito fiscal del mismo período.",
    "COMPRA_CREDITO": "En una compra a crédito se reconoce la obligación en Cuentas por Pagar Proveedores por el total de la factura, manteniendo el gasto financiero cero hasta el pago. El inventario y el crédito tributario de IVA aumentan en el Debe.",
    "COBRO_CARTERA": "La recaudación de cartera es una permuta de activos: se extingue el derecho de cobro (Haber Cuentas por Cobrar) y aumenta la disponibilidad en Caja o Bancos (Debe). No genera un nuevo ingreso.",
    "PAGO_PROVEEDOR": "El pago a proveedores extingue la obligación registrada: Debe Cuentas por Pagar Proveedores y Haber Caja o Bancos. Si existiera descuento financiero, se reconocería como ingreso financiero.",
    "DEPOSITO_BANCO": "El depósito de la recaudación es una transferencia interna entre cuentas del activo: aumenta Bancos y disminuye Caja. No afecta el resultado del período.",
    "GASTO": "Los gastos operacionales se reconocen en el período en que se incurren (devengo), clasificándose en administrativos, de ventas o financieros según su naturaleza, con el IVA acreditable separado.",
    "NOTA_BANCARIA": "Las notas bancarias ajustan el disponible: las comisiones y notas de débito se registran como gasto financiero, mientras que los intereses ganados y notas de crédito constituyen otro ingreso operacional/financiero.",
    "AJUSTE_DEPRECIACION": "La depreciación distribuye el costo histórico de los activos fijos a lo largo de su vida útil por línea recta. Se debita el gasto del período y se acredita la cuenta complementaria de activo (Depreciación Acumulada).",
    "AJUSTE_PROVISION": "La provisión de cuentas incobrables reconoce anticipadamente la pérdida probable de la cartera, debitando el gasto y acreditando la cuenta de valuación 1.1.05 que se presenta disminuyendo las Cuentas por Cobrar.",
    "ARQUEO_CAJA": "El arqueo de caja compara el saldo del Libro Mayor con el conteo físico. Un faltante no imputable a terceros se ajusta contra gastos del período para que el saldo contable coincida con la realidad física.",
    "AJUSTE_IMPUESTOS": "La compensación del IVA es un ajuste técnico: el débito fiscal acumulado en ventas se disminuye contra el crédito tributario de compras. El remanente determina el IVA por pagar o el crédito a favor del contribuyente.",
}


def _solucion_desde_asiento(asiento_id, db_path=None):
    lineas = _lineas_de_asiento(asiento_id, db_path=db_path)
    return [
        {"cuenta": l["codigo"], "nombre": l["nombre"], "debe": round(l["debe"], 2), "haber": round(l["haber"], 2)}
        for l in lineas
    ]


def _seed_simulaciones(db_path, operaciones):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    simulaciones = [
        (1, "Nivel 1 — Básico: Ciclo Operativo Inicial",
         "Compras y ventas de contado, prestación de servicios, cobros y pagos con asientos simples de partida doble.", 1, 0, 45, 70.0),
        (2, "Nivel 2 — Intermedio: Crédito, Inventarios y Tributación",
         "Ventas y compras a crédito, control de Kardex por promedio ponderado y FIFO, IVA y documentos por cobrar/pagar.", 2, 0, 60, 75.0),
        (3, "Nivel 3 — Avanzado: Ajustes, Tesorería y Cierre",
         "Depreciación, provisiones, arqueo de caja, notas bancarias, compensación de IVA y cierre del período.", 3, 0, 75, 80.0),
        (4, "Nivel 4 — Caso Empresarial Integral: Gestión Completa de la Empresa",
         "Administración integral de Comercial y Servicios Nueva Esperanza durante un mes completo con 30 transacciones interconectadas.", 4, 1, 90, 80.0),
    ]
    c.executemany("""
        INSERT INTO simulaciones (id, titulo, descripcion, nivel, modo_examen, duracion_minutos,
                                  puntuacion_minima, docente_id, curso_id, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, 2, 1, 1)
    """, simulaciones)

    # Selección de operaciones por nivel (usando las transacciones REALES del período)
    por_tipo = {}
    for op in operaciones:
        por_tipo.setdefault(op["tipo"], []).append(op)

    casos_por_nivel = {
        1: (
            [("VENTA_CONTADO", 0, "Venta de contado de productos de primera necesidad"),
             ("SERVICIO", 0, "Prestación de servicio logístico con cobro por transferencia"),
             ("COMPRA_CONTADO", 1, "Compra de mercaderías pagada en efectivo"),
             ("COBRO_CARTERA", 1, "Cobro en efectivo de cartera de un cliente")],
        ),
        2: (
            [("VENTA_CREDITO", 0, "Venta de mercaderías a crédito a 30 días"),
             ("COMPRA_CREDITO", 1, "Compra de mercaderías a crédito a 45 días"),
             ("COBRO_CARTERA", 0, "Cobro por transferencia de cartera inicial"),
             ("PAGO_PROVEEDOR", 0, "Pago por transferencia de una obligación con proveedor")],
        ),
        3: (
            [("AJUSTE_DEPRECIACION", 0, "Ajuste mensual por depreciación de activos fijos"),
             ("AJUSTE_PROVISION", 0, "Ajuste por provisión de cuentas incobrables"),
             ("ARQUEO_CAJA", 0, "Arqueo de caja con faltante y su regularización"),
             ("NOTA_BANCARIA", 0, "Nota de débito bancaria por comisiones"),
             ("AJUSTE_IMPUESTOS", 0, "Compensación del IVA del período")],
        ),
        4: (
            [("VENTA_CONTADO", 1, "Venta de contado en cuenta de ahorros (caso integral)"),
             ("GASTO", 0, "Pago del arriendo del local comercial"),
             ("DEPOSITO_BANCO", 0, "Depósito de la recaudación en el banco"),
             ("NOTA_BANCARIA", 1, "Nota de crédito bancaria por intereses ganados"),
             ("AJUSTE_IMPUESTOS", 0, "Cierre técnico de la posición de IVA del período")],
        ),
    }

    caso_id = 1
    orden_global = 0
    for simulacion_id, seleccion in casos_por_nivel.items():
        if isinstance(seleccion, tuple):  # permite declarar la selección como lista o tupla de listas
            seleccion = seleccion[0]
        orden = 0
        for tipo, idx, titulo in seleccion:
            lista = por_tipo.get(tipo, [])
            if len(lista) <= idx:
                continue
            op = lista[idx]
            asiento_principal = (op["asiento_ids"] or [None])[0]
            if not asiento_principal:
                continue

            if op["tipo"].startswith("VENTA") and len(op["asiento_ids"]) >= 2:
                solucion = {
                    "asiento_venta": _solucion_desde_asiento(op["asiento_ids"][0], db_path=db_path),
                    "asiento_costo": _solucion_desde_asiento(op["asiento_ids"][1], db_path=db_path),
                }
            else:
                solucion = {"asiento": _solucion_desde_asiento(asiento_principal, db_path=db_path)}
            pistas = PISTAS_POR_TIPO.get(tipo, ["Analiza el hecho económico y aplica la partida doble."])
            explicacion = EXPLICACION_POR_TIPO.get(tipo, "")

            conn_op = get_db_connection(db_path)
            try:
                asiento_row = conn_op.execute("SELECT * FROM asientos WHERE id = ?", (asiento_principal,)).fetchone()
                doc_tipo = asiento_row["tipo_documento"] if asiento_row else op["doc_tipo"]
                doc_numero = asiento_row["numero_documento"] if asiento_row else op["doc_numero"]
            finally:
                conn_op.close()

            orden += 1
            orden_global += 1
            enunciado = (
                f"{op['titulo']}. Transacción del {op['fecha']} con documento fuente "
                f"{doc_tipo} {doc_numero}. Registre el asiento contable completo aplicando la partida doble."
            )
            c.execute("""
                INSERT INTO casos_simulacion (id, simulacion_id, orden, titulo, fecha_transaccion, enunciado,
                    documento_fuente_tipo, documento_fuente_numero, datos_transaccion_json,
                    solucion_esperada_json, pistas_json, explicacion_pedagogica)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                caso_id, simulacion_id, orden, titulo, op["fecha"], enunciado,
                doc_tipo, doc_numero,
                json.dumps({**op["resultado"], **op["datos"]}, ensure_ascii=False, default=str),
                json.dumps(solucion, ensure_ascii=False),
                json.dumps(pistas, ensure_ascii=False),
                explicacion
            ))
            caso_id += 1

    # Caso integrador final del Nivel 4: asiento de cierre del período
    income = AccountingService.get_income_statement(db_path=db_path)
    lineas_cierre = []
    for codigo, valor, cta_id in [("4.1.01", income["ventas_bienes"], 31),
                                  ("4.1.02", income["ingresos_servicios"], 32),
                                  ("4.2.01", income["otros_ingresos"], 33)]:
        if valor > 0:
            lineas_cierre.append({"cuenta": codigo, "nombre": f"Cancelación de la cuenta {codigo}",
                                  "debe": round(valor, 2), "haber": 0.0})
    total_ingresos = round(income["ventas_bienes"] + income["ingresos_servicios"] + income["otros_ingresos"], 2)
    if total_ingresos > 0:
        lineas_cierre.append({"cuenta": "3.3.02", "nombre": "Utilidad del Ejercicio Actual",
                              "debe": 0.0, "haber": total_ingresos})

    total_costos_gastos = round(income["costo_ventas"] + income["total_gastos_operacionales"] + income["gastos_financieros"], 2)
    if total_costos_gastos > 0:
        lineas_cierre.append({"cuenta": "3.3.02", "nombre": "Utilidad del Ejercicio Actual",
                              "debe": total_costos_gastos, "haber": 0.0})
    for codigo, valor in [("5.1.01", income["costo_ventas"]),
                          ("6.1.01", income["gastos_administrativos"]["sueldos"]),
                          ("6.1.02", income["gastos_administrativos"]["arriendo"]),
                          ("6.1.03", income["gastos_administrativos"]["servicios_basicos"]),
                          ("6.1.04", income["gastos_administrativos"]["depreciacion"]),
                          ("6.1.05", income["gastos_ventas"]["publicidad"]),
                          ("6.1.06", income["gastos_administrativos"]["mantenimiento"]),
                          ("6.2.01", income["gastos_financieros"])]:
        if valor > 0:
            lineas_cierre.append({"cuenta": codigo, "nombre": f"Cancelación de la cuenta {codigo}",
                                  "debe": 0.0, "haber": round(valor, 2)})

    c.execute("""
        INSERT INTO casos_simulacion (id, simulacion_id, orden, titulo, fecha_transaccion, enunciado,
            documento_fuente_tipo, documento_fuente_numero, datos_transaccion_json,
            solucion_esperada_json, pistas_json, explicacion_pedagogica)
        VALUES (?, 4, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        caso_id, orden + 1,
        "Cierre contable del período: cancelación de ingresos, costos y gastos",
        PERIODO_FIN,
        ("Con los saldos finales del período Abril 2026, registre el asiento de cierre contable: cancele las "
         "cuentas de ingresos (4.1.01, 4.1.02 y 4.2.01) y las cuentas de costos y gastos (5.1.01 y 6.1.01 a 6.2.01) "
         "contra la cuenta de resultado 3.3.02 Utilidad del Ejercicio Actual. Verifique que el asiento cuadre."),
        "COMPROBANTE_CIERRE", "CIE-2026-04",
        json.dumps({
            "ventas_bienes": income["ventas_bienes"],
            "ingresos_servicios": income["ingresos_servicios"],
            "otros_ingresos": income["otros_ingresos"],
            "costo_ventas": income["costo_ventas"],
            "gastos_operacionales": income["total_gastos_operacionales"],
            "gastos_financieros": income["gastos_financieros"],
            "utilidad_neta": income["utilidad_neta"],
        }, ensure_ascii=False),
        json.dumps({"asiento": lineas_cierre}, ensure_ascii=False),
        json.dumps([
            "Primero cancele los ingresos: se debitan las cuentas de ingreso y se acredita la cuenta de resultado.",
            "Luego cancele costos y gastos: se debita la cuenta de resultado y se acreditan las cuentas de costo y gasto.",
            "La diferencia entre ingresos y costos/gastos es la utilidad neta que se transfiere al patrimonio.",
        ], ensure_ascii=False),
        ("El cierre contable traslada los saldos de las cuentas de resultado (ingresos, costos y gastos) a la cuenta "
         "de resultado del ejercicio y luego al patrimonio, dejando las cuentas temporales en cero para iniciar el "
         "siguiente período. Activo = Pasivo + Patrimonio se mantiene después del cierre.")
    ))
    caso_id += 1

    conn.commit()
    conn.close()
    return caso_id - 1


# ----------------------------------------------------------------------------
# 5. Orquestación
# ----------------------------------------------------------------------------
def _seed_all_interno(db_path=None, reset=True, verbose=True):
    """Implementación interna: asume que Config.DATABASE_PATH ya apunta a db_path."""
    if db_path is None:
        db_path = Config.DATABASE_PATH

    if reset:
        # Se elimina el archivo para garantizar un esquema limpio y datos 100% reproducibles
        for sufijo in ("", "-wal", "-shm"):
            try:
                os.remove(db_path + sufijo)
            except OSError:
                pass

    init_db(db_path)
    if reset:
        _reset_tables(db_path)

    productos = _seed_maestros(db_path)
    asiento_apertura, numero_apertura = _seed_apertura(db_path, productos)
    operaciones = _seed_operaciones(db_path)
    total_casos = _seed_simulaciones(db_path, operaciones)

    # La fecha de trabajo queda al cierre del período para operar sobre el mes completo
    PeriodService.set_param("fecha_trabajo", FECHA_TRABAJO,
                            "Fecha de trabajo de la simulación (AAAA-MM-DD) dentro del período abierto.",
                            db_path=db_path)
    PeriodService.set_param("origen_datos", "DEMOSTRACION",
                            "Los datos del sistema son de demostración con fines académicos.",
                            db_path=db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            INSERT INTO auditoria (usuario_id, username, accion, modulo, registro_id, valor_anterior,
                                   valor_nuevo, ip_origen, agente_utilizado, herramienta_ejecutada)
            VALUES (1, 'admin', 'INICIALIZAR_SISTEMA', 'ADMIN', 'SEED-2026', NULL,
                    'Carga de datos demostrativos completos de Comercial y Servicios Nueva Esperanza',
                    '127.0.0.1', 'AgenteOrquestador', 'seed_all')
        """)
        conn.commit()
    finally:
        conn.close()

    if verbose:
        trial = AccountingService.get_trial_balance(db_path=db_path)
        bs = AccountingService.get_balance_sheet(db_path=db_path)
        income = AccountingService.get_income_statement(db_path=db_path)
        print("=" * 78)
        print(" DATOS DE DEMOSTRACIÓN GENERADOS CORRECTAMENTE")
        print("=" * 78)
        print(f" Período: {PeriodService.get_active_period(db_path=db_path)['nombre']}")
        print(f" Fecha de trabajo: {FECHA_TRABAJO}")
        print(f" Asiento de apertura: #{numero_apertura}")
        print(f" Operaciones integradas ejecutadas: {len(operaciones)}")
        print(f" Casos de simulación creados: {total_casos}")
        print(f" Asientos contabilizados: {len(AccountingService.get_journal_entries(db_path=db_path))}")
        print("-" * 78)
        print(f" Total débitos : {trial['total_debitos']:,.2f}   Total créditos: {trial['total_creditos']:,.2f}"
              f"   Cuadra sumas: {trial['cuadrado_sumas']}")
        print(f" Saldo deudor : {trial['total_saldo_deudor']:,.2f}   Saldo acreedor: {trial['total_saldo_acreedor']:,.2f}"
              f"   Cuadra saldos: {trial['cuadrado_saldos']}")
        print(f" Activo: {bs['total_activo']:,.2f}  =  Pasivo + Patrimonio: {bs['total_pasivo_y_patrimonio']:,.2f}"
              f"   Balanceado: {bs['balanceado']} (diferencia {bs['diferencia']})")
        print(f" Utilidad neta del período: {income['utilidad_neta']:,.2f}")
        print("=" * 78)

    return {
        "operaciones": len(operaciones),
        "casos": total_casos,
        "asiento_apertura": asiento_apertura,
    }


def seed_all(db_path=None, reset=True, verbose=True):
    """
    Genera los datos de demostración completos.

    Todas las operaciones se ejecutan a través de los SERVICIOS reales del sistema, por lo que
    Config.DATABASE_PATH se fija temporalmente a la ruta solicitada para que cualquier servicio
    que no reciba db_path de forma explícita escriba en la base de datos correcta.
    """
    if db_path is None:
        db_path = Config.DATABASE_PATH

    ruta_original = Config.DATABASE_PATH
    Config.DATABASE_PATH = db_path
    try:
        return _seed_all_interno(db_path=db_path, reset=reset, verbose=verbose)
    finally:
        Config.DATABASE_PATH = ruta_original


if __name__ == "__main__":
    seed_all()
