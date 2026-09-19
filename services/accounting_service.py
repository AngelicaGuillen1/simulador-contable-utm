# Core Double-Entry Accounting Engine & Financial Statements Service
import sqlite3
from datetime import datetime, date
from models import get_db_contable
from services.audit_service import AuditService

class AccountingService:
    @staticmethod
    def get_accounts(active_only=True, db_path=None):
        conn = get_db_contable(db_path)
        try:
            query = "SELECT * FROM cuentas"
            if active_only:
                query += " WHERE activo = 1"
            query += " ORDER BY codigo ASC"
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_account_by_id(account_id, db_path=None):
        conn = get_db_contable(db_path)
        try:
            row = conn.execute("SELECT * FROM cuentas WHERE id = ?", (account_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_account_by_code(code, db_path=None):
        conn = get_db_contable(db_path)
        try:
            row = conn.execute("SELECT * FROM cuentas WHERE codigo = ?", (code,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def create_account(codigo, nombre, naturaleza, clasificacion, cuenta_padre_id=None, nivel=1, acepta_movimiento=1, db_path=None):
        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cuentas (codigo, nombre, naturaleza, clasificacion, cuenta_padre_id, nivel, acepta_movimiento, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (codigo, nombre, naturaleza, clasificacion, cuenta_padre_id, nivel, acepta_movimiento))
            new_id = cursor.lastrowid
            conn.commit()
            return new_id
        finally:
            conn.close()

    @staticmethod
    def update_account(account_id, nombre, naturaleza, clasificacion, activo=1, db_path=None):
        conn = get_db_contable(db_path)
        try:
            conn.execute("""
                UPDATE cuentas
                SET nombre = ?, naturaleza = ?, clasificacion = ?, activo = ?
                WHERE id = ?
            """, (nombre, naturaleza, clasificacion, int(activo), account_id))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def validate_journal_entry(lineas):
        """
        Validates that total debits == total credits with strict floating point tolerance (0.01).
        lineas format: [{'cuenta_id': 1, 'debe': 100.0, 'haber': 0.0}, ...]
        """
        if not lineas or len(lineas) < 2:
            return False, "Un asiento contable debe contener al menos 2 cuentas (partida doble)."
        
        total_debe = round(sum(float(l.get("debe", 0.0)) for l in lineas), 2)
        total_haber = round(sum(float(l.get("haber", 0.0)) for l in lineas), 2)
        diferencia = round(abs(total_debe - total_haber), 2)

        if diferencia > 0.01:
            return False, f"El asiento no cuadra: Total Debe (${total_debe:,.2f}) != Total Haber (${total_haber:,.2f}). Diferencia: ${diferencia:,.2f}."
        
        if total_debe <= 0:
            return False, "El importe del asiento debe ser mayor a 0."

        return True, "Asiento balanceado correctamente."

    @staticmethod
    def create_journal_entry(empresa_id, fecha, glosa, lineas, tipo_documento="MANUAL", numero_documento=None, origen_modulo="MANUAL", usuario_id=1, periodo_id=1, observacion=None, db_path=None):
        is_valid, msg = AccountingService.validate_journal_entry(lineas)
        if not is_valid:
            raise ValueError(msg)

        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            
            # Check period state
            per = conn.execute("SELECT estado FROM periodos WHERE id = ?", (periodo_id,)).fetchone()
            if per and per["estado"] == "CERRADO":
                raise ValueError("No se pueden registrar operaciones en un período contable CERRADO.")

            # Next sequential number for empresa
            row = cursor.execute("SELECT MAX(numero_asiento) as max_num FROM asientos WHERE empresa_id = ?", (empresa_id,)).fetchone()
            next_num = (row["max_num"] or 0) + 1

            cursor.execute("""
                INSERT INTO asientos (empresa_id, periodo_id, numero_asiento, fecha, glosa, tipo_documento, numero_documento, origen_modulo, estado, observacion, usuario_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'CONTABILIZADO', ?, ?)
            """, (empresa_id, periodo_id, next_num, fecha, glosa, tipo_documento, numero_documento, origen_modulo, observacion, usuario_id))
            asiento_id = cursor.lastrowid

            for l in lineas:
                cta_id = l["cuenta_id"]
                debe = float(l.get("debe", 0.0))
                haber = float(l.get("haber", 0.0))
                ref = l.get("referencia", "")
                
                cursor.execute("""
                    INSERT INTO detalle_asientos (asiento_id, cuenta_id, debe, haber, referencia)
                    VALUES (?, ?, ?, ?, ?)
                """, (asiento_id, cta_id, debe, haber, ref))

            conn.commit()

            AuditService.log(usuario_id, "sistema", "CREAR_ASIENTO", "ASIENTOS", asiento_id, None, {
                "numero": next_num, "fecha": fecha, "glosa": glosa, "lineas_count": len(lineas)
            }, db_path=db_path)

            return asiento_id, next_num
        finally:
            conn.close()

    @staticmethod
    def get_journal_entries(empresa_id=1, fecha_inicio=None, fecha_fin=None, estado=None, db_path=None):
        conn = get_db_contable(db_path)
        try:
            query = """
                SELECT a.*, u.nombre_completo as usuario_nombre
                FROM asientos a
                LEFT JOIN usuarios u ON a.usuario_id = u.id
                WHERE a.empresa_id = ?
            """
            params = [empresa_id]
            if estado:
                query += " AND a.estado = ?"
                params.append(estado)
            else:
                # Por defecto se muestran los asientos contabilizados y los revertidos
                # (estos últimos con su contra-asiento, para conservar la trazabilidad).
                query += " AND a.estado IN ('CONTABILIZADO', 'REVERTIDO')" 
            if fecha_inicio:
                query += " AND a.fecha >= ?"
                params.append(fecha_inicio)
            if fecha_fin:
                query += " AND a.fecha <= ?"
                params.append(fecha_fin)
            query += " ORDER BY a.numero_asiento ASC"

            asientos_rows = conn.execute(query, params).fetchall()
            asientos = []
            for a in asientos_rows:
                a_dict = dict(a)
                detalles = conn.execute("""
                    SELECT d.*, c.codigo as cuenta_codigo, c.nombre as cuenta_nombre, c.naturaleza
                    FROM detalle_asientos d
                    JOIN cuentas c ON d.cuenta_id = c.id
                    WHERE d.asiento_id = ?
                    ORDER BY d.debe DESC, d.haber ASC
                """, (a["id"],)).fetchall()
                a_dict["detalles"] = [dict(d) for d in detalles]
                a_dict["total_debe"] = sum(d["debe"] for d in detalles)
                a_dict["total_haber"] = sum(d["haber"] for d in detalles)
                asientos.append(a_dict)
            return asientos
        finally:
            conn.close()

    @staticmethod
    def reverse_journal_entry(asiento_id, motivo="Reversión por anulación contable", usuario_id=1, db_path=None):
        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            asiento = conn.execute("SELECT * FROM asientos WHERE id = ?", (asiento_id,)).fetchone()
            if not asiento:
                raise ValueError("Asiento no encontrado.")
            if asiento["estado"] != "CONTABILIZADO":
                raise ValueError("Solo se pueden revertir asientos en estado CONTABILIZADO.")

            detalles = conn.execute("SELECT * FROM detalle_asientos WHERE asiento_id = ?", (asiento_id,)).fetchall()
            
            # Invert debits and credits for reversing entry
            reversed_lines = []
            for d in detalles:
                reversed_lines.append({
                    "cuenta_id": d["cuenta_id"],
                    "debe": d["haber"],
                    "haber": d["debe"],
                    "referencia": f"Reversión Asiento #{asiento['numero_asiento']}"
                })

            # La reversión se registra con la fecha de trabajo de la simulación, que siempre
            # se encuentra dentro del período abierto.
            from services.period_service import PeriodService
            today_str = PeriodService.get_fecha_trabajo(db_path=db_path)
            glosa_rev = f"Reversión del Asiento #{asiento['numero_asiento']}: {motivo}"
            
            rev_id, rev_num = AccountingService.create_journal_entry(
                asiento["empresa_id"], today_str, glosa_rev, reversed_lines,
                tipo_documento="REVERSION", numero_documento=f"REV-{asiento['numero_asiento']}",
                origen_modulo="MANUAL", usuario_id=usuario_id, periodo_id=asiento["periodo_id"],
                observacion=f"Reversión originada del asiento {asiento_id}", db_path=db_path
            )

            cursor.execute("UPDATE asientos SET estado = 'REVERTIDO', asiento_reversion_id = ? WHERE id = ?", (rev_id, asiento_id))
            conn.commit()

            AuditService.log(usuario_id, "sistema", "REVERTIR_ASIENTO", "ASIENTOS", asiento_id, {"estado": "CONTABILIZADO"}, {"estado": "REVERTIDO", "asiento_reversion_id": rev_id}, db_path=db_path)
            return rev_id, rev_num
        finally:
            conn.close()

    @staticmethod
    def get_ledger(cuenta_id=None, codigo_cuenta=None, fecha_inicio=None, fecha_fin=None, db_path=None):
        conn = get_db_contable(db_path)
        try:
            if not cuenta_id and codigo_cuenta:
                cta = conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (codigo_cuenta,)).fetchone()
                if cta:
                    cuenta_id = cta["id"]
            
            if cuenta_id:
                cuentas = conn.execute("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,)).fetchall()
            else:
                cuentas = conn.execute("SELECT * FROM cuentas WHERE acepta_movimiento = 1 ORDER BY codigo ASC").fetchall()

            ledger_data = []
            for c in cuentas:
                c_dict = dict(c)
                naturaleza = c["naturaleza"]

                query = """
                    SELECT d.debe, d.haber, d.referencia, a.fecha, a.numero_asiento, a.glosa, a.tipo_documento, a.numero_documento
                    FROM detalle_asientos d
                    JOIN asientos a ON d.asiento_id = a.id
                    WHERE d.cuenta_id = ? AND a.estado IN ('CONTABILIZADO', 'REVERTIDO')
                """
                params = [c["id"]]
                if fecha_inicio:
                    query += " AND a.fecha >= ?"
                    params.append(fecha_inicio)
                if fecha_fin:
                    query += " AND a.fecha <= ?"
                    params.append(fecha_fin)
                query += " ORDER BY a.fecha ASC, a.numero_asiento ASC"

                movs = conn.execute(query, params).fetchall()
                movimientos = []
                saldo_acumulado = 0.0

                for m in movs:
                    debe = float(m["debe"])
                    haber = float(m["haber"])
                    if naturaleza == "DEUDORA":
                        saldo_acumulado += (debe - haber)
                    else:
                        saldo_acumulado += (haber - debe)

                    m_dict = dict(m)
                    m_dict["saldo"] = round(saldo_acumulado, 2)
                    movimientos.append(m_dict)

                total_debe = sum(m["debe"] for m in movimientos)
                total_haber = sum(m["haber"] for m in movimientos)

                c_dict["movimientos"] = movimientos
                c_dict["total_debe"] = round(total_debe, 2)
                c_dict["total_haber"] = round(total_haber, 2)
                c_dict["saldo_final"] = round(saldo_acumulado, 2)

                # Include only accounts with movements or when explicitly queried
                if movimientos or cuenta_id:
                    ledger_data.append(c_dict)

            return ledger_data
        finally:
            conn.close()

    @staticmethod
    def get_account_balance(cuenta_id, db_path=None):
        conn = get_db_contable(db_path)
        try:
            cta = conn.execute("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,)).fetchone()
            if not cta:
                return 0.0
            row = conn.execute("""
                SELECT SUM(d.debe) as total_debe, SUM(d.haber) as total_haber
                FROM detalle_asientos d
                JOIN asientos a ON d.asiento_id = a.id
                WHERE d.cuenta_id = ? AND a.estado IN ('CONTABILIZADO', 'REVERTIDO')
            """, (cuenta_id,)).fetchone()
            
            debe = float(row["total_debe"] or 0.0)
            haber = float(row["total_haber"] or 0.0)

            if cta["naturaleza"] == "DEUDORA":
                return round(debe - haber, 2)
            else:
                return round(haber - debe, 2)
        finally:
            conn.close()

    @staticmethod
    def get_trial_balance(fecha_corte=None, db_path=None):
        """
        Generates Trial Balance (Balance de Comprobación) with 4 key balance columns:
        Sumas Débitos, Sumas Créditos, Saldo Deudor, Saldo Acreedor.
        Validates: Sum(Debits) == Sum(Credits) and Sum(Saldo Deudor) == Sum(Saldo Acreedor).
        """
        conn = get_db_contable(db_path)
        try:
            cuentas = conn.execute("SELECT * FROM cuentas WHERE acepta_movimiento = 1 ORDER BY codigo ASC").fetchall()
            
            rows = []
            total_debitos = 0.0
            total_creditos = 0.0
            total_saldo_deudor = 0.0
            total_saldo_acreedor = 0.0

            for c in cuentas:
                query = """
                    SELECT SUM(d.debe) as debitos, SUM(d.haber) as creditos
                    FROM detalle_asientos d
                    JOIN asientos a ON d.asiento_id = a.id
                    WHERE d.cuenta_id = ? AND a.estado IN ('CONTABILIZADO', 'REVERTIDO')
                """
                params = [c["id"]]
                if fecha_corte:
                    query += " AND a.fecha <= ?"
                    params.append(fecha_corte)
                
                res = conn.execute(query, params).fetchone()
                debitos = float(res["debitos"] or 0.0)
                creditos = float(res["creditos"] or 0.0)

                if debitos == 0.0 and creditos == 0.0:
                    continue

                saldo_deudor = 0.0
                saldo_acreedor = 0.0

                if c["naturaleza"] == "DEUDORA":
                    diff = debitos - creditos
                    if diff >= 0:
                        saldo_deudor = diff
                    else:
                        saldo_acreedor = abs(diff)
                else:
                    diff = creditos - debitos
                    if diff >= 0:
                        saldo_acreedor = diff
                    else:
                        saldo_deudor = abs(diff)

                total_debitos += debitos
                total_creditos += creditos
                total_saldo_deudor += saldo_deudor
                total_saldo_acreedor += saldo_acreedor

                rows.append({
                    "id": c["id"],
                    "codigo": c["codigo"],
                    "nombre": c["nombre"],
                    "clasificacion": c["clasificacion"],
                    "naturaleza": c["naturaleza"],
                    "debitos": round(debitos, 2),
                    "creditos": round(creditos, 2),
                    "saldo_deudor": round(saldo_deudor, 2),
                    "saldo_acreedor": round(saldo_acreedor, 2)
                })

            cuadrado_sumas = abs(round(total_debitos - total_creditos, 2)) < 0.02
            cuadrado_saldos = abs(round(total_saldo_deudor - total_saldo_acreedor, 2)) < 0.02

            return {
                "cuentas": rows,
                "total_debitos": round(total_debitos, 2),
                "total_creditos": round(total_creditos, 2),
                "total_saldo_deudor": round(total_saldo_deudor, 2),
                "total_saldo_acreedor": round(total_saldo_acreedor, 2),
                "cuadrado_sumas": cuadrado_sumas,
                "cuadrado_saldos": cuadrado_saldos,
                "diferencia_sumas": round(abs(total_debitos - total_creditos), 2),
                "diferencia_saldos": round(abs(total_saldo_deudor - total_saldo_acreedor), 2)
            }
        finally:
            conn.close()

    @staticmethod
    def get_income_statement(fecha_inicio=None, fecha_fin=None, db_path=None):
        """
        Generates Estado de Resultados (Income Statement):
        + Ventas de Bienes (4.1.01)
        + Prestación de Servicios (4.1.02)
        = Total Ingresos Operacionales
        - Costo de Ventas (5.1.01)
        = Utilidad Bruta en Ventas
        - Gastos Administrativos (6.1.01, 6.1.02, 6.1.03, 6.1.04, 6.1.06)
        - Gastos de Ventas (6.1.05)
        = Utilidad Operacional
        + Otros Ingresos / Ganancias (4.2.01)
        - Gastos Financieros (6.2.01)
        = Utilidad / (Pérdida) Neta del Período
        """
        conn = get_db_contable(db_path)
        try:
            # Helper to calculate net balance for accounts
            def get_account_sum(account_code):
                row = conn.execute("""
                    SELECT SUM(d.haber) - SUM(d.debe) as total
                    FROM detalle_asientos d
                    JOIN asientos a ON d.asiento_id = a.id
                    JOIN cuentas c ON d.cuenta_id = c.id
                    WHERE c.codigo = ? AND a.estado IN ('CONTABILIZADO', 'REVERTIDO')
                """, (account_code,)).fetchone()
                return float(row["total"] or 0.0)

            def get_expense_sum(account_code):
                row = conn.execute("""
                    SELECT SUM(d.debe) - SUM(d.haber) as total
                    FROM detalle_asientos d
                    JOIN asientos a ON d.asiento_id = a.id
                    JOIN cuentas c ON d.cuenta_id = c.id
                    WHERE c.codigo = ? AND a.estado IN ('CONTABILIZADO', 'REVERTIDO')
                """, (account_code,)).fetchone()
                return float(row["total"] or 0.0)

            ventas_bienes = get_account_sum("4.1.01")
            servicios = get_account_sum("4.1.02")
            total_ingresos_op = ventas_bienes + servicios

            costo_ventas = get_expense_sum("5.1.01")
            utilidad_bruta = total_ingresos_op - costo_ventas

            gasto_sueldos = get_expense_sum("6.1.01")
            gasto_arriendo = get_expense_sum("6.1.02")
            gasto_servicios_basicos = get_expense_sum("6.1.03")
            gasto_depreciacion = get_expense_sum("6.1.04")
            gasto_publicidad = get_expense_sum("6.1.05")
            gasto_mantenimiento = get_expense_sum("6.1.06")

            gastos_admin = gasto_sueldos + gasto_arriendo + gasto_servicios_basicos + gasto_depreciacion + gasto_mantenimiento
            gastos_ventas = gasto_publicidad
            total_gastos_op = gastos_admin + gastos_ventas

            utilidad_operacional = utilidad_bruta - total_gastos_op

            otros_ingresos = get_account_sum("4.2.01")
            gastos_financieros = get_expense_sum("6.2.01")

            utilidad_neta = utilidad_operacional + otros_ingresos - gastos_financieros

            return {
                "ventas_bienes": round(ventas_bienes, 2),
                "ingresos_servicios": round(servicios, 2),
                "total_ingresos_operacionales": round(total_ingresos_op, 2),
                "costo_ventas": round(costo_ventas, 2),
                "utilidad_bruta": round(utilidad_bruta, 2),
                "gastos_administrativos": {
                    "sueldos": round(gasto_sueldos, 2),
                    "arriendo": round(gasto_arriendo, 2),
                    "servicios_basicos": round(gasto_servicios_basicos, 2),
                    "depreciacion": round(gasto_depreciacion, 2),
                    "mantenimiento": round(gasto_mantenimiento, 2),
                    "total": round(gastos_admin, 2)
                },
                "gastos_ventas": {
                    "publicidad": round(gasto_publicidad, 2),
                    "total": round(gastos_ventas, 2)
                },
                "total_gastos_operacionales": round(total_gastos_op, 2),
                "utilidad_operacional": round(utilidad_operacional, 2),
                "otros_ingresos": round(otros_ingresos, 2),
                "gastos_financieros": round(gastos_financieros, 2),
                "utilidad_neta": round(utilidad_neta, 2)
            }
        finally:
            conn.close()

    @staticmethod
    def get_balance_sheet(fecha_corte=None, db_path=None):
        """
        Generates Estado de Situación Financiera (Balance Sheet):
        Activos = Pasivos + Patrimonio
        Validates the fundamental accounting equation dynamically with net profit inclusion.
        """
        conn = get_db_contable(db_path)
        try:
            trial = AccountingService.get_trial_balance(fecha_corte, db_path=db_path)
            income_stmt = AccountingService.get_income_statement(db_path=db_path)
            utilidad_neta = income_stmt["utilidad_neta"]

            activos_corrientes = []
            activos_no_corrientes = []
            pasivos_corrientes = []
            pasivos_no_corrientes = []
            patrimonio = []

            for c in trial["cuentas"]:
                clas = c["clasificacion"]
                # Contribución al grupo: en los grupos de ACTIVO las cuentas de naturaleza
                # ACREEDORA restan (depreciación acumulada, provisión de incobrables) y en los
                # grupos de PASIVO/PATRIMONIO las cuentas DEUDORAS restan (pérdidas).
                if clas in ("ACTIVO_CORRIENTE", "ACTIVO_NO_CORRIENTE"):
                    contribucion = c["saldo_deudor"] - c["saldo_acreedor"]
                else:
                    contribucion = c["saldo_acreedor"] - c["saldo_deudor"]

                item = {"codigo": c["codigo"], "nombre": c["nombre"],
                        "valor": round(contribucion, 2), "signo": 1}

                if clas == "ACTIVO_CORRIENTE":
                    activos_corrientes.append(item)
                elif clas == "ACTIVO_NO_CORRIENTE":
                    activos_no_corrientes.append(item)
                elif clas == "PASIVO_CORRIENTE":
                    pasivos_corrientes.append(item)
                elif clas == "PASIVO_NO_CORRIENTE":
                    pasivos_no_corrientes.append(item)
                elif clas == "PATRIMONIO":
                    patrimonio.append(item)

            # Se incorpora el resultado del ejercicio (pérdida o ganancia) al patrimonio
            # mientras el período no haya sido cerrado contablemente.
            patrimonio.append({
                "codigo": "3.3.02",
                "nombre": "Resultado / Utilidad del Ejercicio Actual (Calculado)",
                "valor": round(utilidad_neta, 2),
                "signo": 1
            })

            total_act_corr = sum(i["valor"] * i["signo"] for i in activos_corrientes)
            total_act_nocorr = sum(i["valor"] * i["signo"] for i in activos_no_corrientes)
            total_activo = total_act_corr + total_act_nocorr

            total_pas_corr = sum(i["valor"] * i["signo"] for i in pasivos_corrientes)
            total_pas_nocorr = sum(i["valor"] * i["signo"] for i in pasivos_no_corrientes)
            total_pasivo = total_pas_corr + total_pas_nocorr

            total_patrimonio = sum(i["valor"] * i["signo"] for i in patrimonio)
            total_pasivo_patrimonio = total_pasivo + total_patrimonio

            diferencia = round(abs(total_activo - total_pasivo_patrimonio), 2)
            balanceado = diferencia < 0.05

            return {
                "activos_corrientes": activos_corrientes,
                "total_activo_corriente": round(total_act_corr, 2),
                "activos_no_corrientes": activos_no_corrientes,
                "total_activo_no_corriente": round(total_act_nocorr, 2),
                "total_activo": round(total_activo, 2),
                "pasivos_corrientes": pasivos_corrientes,
                "total_pasivo_corriente": round(total_pas_corr, 2),
                "pasivos_no_corrientes": pasivos_no_corrientes,
                "total_pasivo_no_corriente": round(total_pas_nocorr, 2),
                "total_pasivo": round(total_pasivo, 2),
                "patrimonio": patrimonio,
                "total_patrimonio": round(total_patrimonio, 2),
                "total_pasivo_y_patrimonio": round(total_pasivo_patrimonio, 2),
                "balanceado": balanceado,
                "diferencia": diferencia
            }
        finally:
            conn.close()

    @staticmethod
    def get_cash_flow_statement(db_path=None):
        """
        Generates Estado de Flujo de Efectivo (Cash Flow Statement - Direct method simulation):
        Actividades de Operación, Actividades de Inversión, Actividades de Financiamiento.
        """
        conn = get_db_contable(db_path)
        try:
            # Query cash and bank movements
            caja_bancos_ids = [3, 4, 5] # Caja, Pichincha, Guayaquil
            
            detalles = conn.execute("""
                SELECT d.debe, d.haber, d.cuenta_id, a.fecha, a.glosa, a.origen_modulo, a.tipo_documento
                FROM detalle_asientos d
                JOIN asientos a ON d.asiento_id = a.id
                WHERE d.cuenta_id IN (3, 4, 5) AND a.estado IN ('CONTABILIZADO', 'REVERTIDO')
                ORDER BY a.fecha ASC
            """).fetchall()

            flujo_operacion = []
            flujo_inversion = []
            flujo_financiamiento = []

            for d in detalles:
                neto = float(d["debe"]) - float(d["haber"])
                origen = d["origen_modulo"]
                glosa = d["glosa"]

                item = {"fecha": d["fecha"], "concepto": glosa, "monto": round(neto, 2)}

                if "Activos Fijos" in glosa or "Vehículo" in glosa or "Cómputo" in glosa or origen == "INVERSION":
                    flujo_inversion.append(item)
                elif "Préstamo" in glosa or "Capital" in glosa or origen == "FINANCIAMIENTO":
                    flujo_financiamiento.append(item)
                else:
                    flujo_operacion.append(item)

            total_op = sum(i["monto"] for i in flujo_operacion)
            total_inv = sum(i["monto"] for i in flujo_inversion)
            total_fin = sum(i["monto"] for i in flujo_financiamiento)
            variacion_neta = total_op + total_inv + total_fin

            return {
                "flujo_operacion": flujo_operacion,
                "total_operacion": round(total_op, 2),
                "flujo_inversion": flujo_inversion,
                "total_inversion": round(total_inv, 2),
                "flujo_financiamiento": flujo_financiamiento,
                "total_financiamiento": round(total_fin, 2),
                "variacion_neta_efectivo": round(variacion_neta, 2)
            }
        finally:
            conn.close()

    @staticmethod
    def execute_period_closing(empresa_id=1, periodo_id=1, usuario_id=1, db_path=None):
        """
        Executes guided accounting close:
        1. Cancels all Revenue accounts against Summary of Income and Expense (3.3.02 / Pérdidas y Ganancias)
        2. Cancels all Expense & Cost accounts against 3.3.02
        3. Transfers net income to Retained Earnings (3.3.01)
        4. Locks period (estado = 'CERRADO')
        """
        conn = get_db_contable(db_path)
        try:
            income_stmt = AccountingService.get_income_statement(db_path=db_path)
            utilidad_neta = income_stmt["utilidad_neta"]

            # 1. Close Revenue accounts (Debit Revenue, Credit Utilidad del Ejercicio 3.3.02)
            ventas = income_stmt["ventas_bienes"]
            servicios = income_stmt["ingresos_servicios"]
            otros_ing = income_stmt["otros_ingresos"]
            total_ing = ventas + servicios + otros_ing

            lineas_ing = []
            if ventas > 0:
                lineas_ing.append({"cuenta_id": 31, "debe": ventas, "haber": 0.0, "referencia": "Cancelación cuenta de ingresos"})
            if servicios > 0:
                lineas_ing.append({"cuenta_id": 32, "debe": servicios, "haber": 0.0, "referencia": "Cancelación cuenta de servicios"})
            if otros_ing > 0:
                lineas_ing.append({"cuenta_id": 33, "debe": otros_ing, "haber": 0.0, "referencia": "Cancelación otros ingresos"})
            if total_ing > 0:
                lineas_ing.append({"cuenta_id": 29, "debe": 0.0, "haber": total_ing, "referencia": "Traspaso de ingresos a resultado"})
                AccountingService.create_journal_entry(
                    empresa_id, date.today().isoformat(), "Cierre de cuentas de ingresos del período",
                    lineas_ing, tipo_documento="CIERRE_INGRESOS", numero_documento="CIE-ING-01",
                    origen_modulo="CIERRE", usuario_id=usuario_id, periodo_id=periodo_id, db_path=db_path
                )

            # 2. Close Expense accounts (Credit Expenses & Cost, Debit Utilidad del Ejercicio 29)
            costo = income_stmt["costo_ventas"]
            gastos = income_stmt["total_gastos_operacionales"] + income_stmt["gastos_financieros"]
            total_egr = costo + gastos

            lineas_egr = [{"cuenta_id": 29, "debe": total_egr, "haber": 0.0, "referencia": "Traspaso de costos y gastos"}]
            if costo > 0:
                lineas_egr.append({"cuenta_id": 35, "debe": 0.0, "haber": costo, "referencia": "Cancelación costo de ventas"})
            for k, val in income_stmt["gastos_administrativos"].items():
                if k != "total" and val > 0:
                    cta_code_map = {"sueldos": 37, "arriendo": 38, "servicios_basicos": 39, "depreciacion": 40, "mantenimiento": 42}
                    if k in cta_code_map:
                        lineas_egr.append({"cuenta_id": cta_code_map[k], "debe": 0.0, "haber": val, "referencia": f"Cancelación gasto {k}"})
            if income_stmt["gastos_ventas"]["publicidad"] > 0:
                lineas_egr.append({"cuenta_id": 41, "debe": 0.0, "haber": income_stmt["gastos_ventas"]["publicidad"], "referencia": "Cancelación gasto publicidad"})
            if income_stmt["gastos_financieros"] > 0:
                lineas_egr.append({"cuenta_id": 43, "debe": 0.0, "haber": income_stmt["gastos_financieros"], "referencia": "Cancelación gastos financieros"})

            if total_egr > 0:
                AccountingService.create_journal_entry(
                    empresa_id, date.today().isoformat(), "Cierre de cuentas de costos y gastos del período",
                    lineas_egr, tipo_documento="CIERRE_GASTOS", numero_documento="CIE-GAS-01",
                    origen_modulo="CIERRE", usuario_id=usuario_id, periodo_id=periodo_id, db_path=db_path
                )

            # 3. Lock period
            conn.execute("UPDATE periodos SET estado = 'CERRADO', cerrado_en = CURRENT_TIMESTAMP WHERE id = ?", (periodo_id,))
            conn.commit()

            AuditService.log(usuario_id, "sistema", "CIERRE_PERIODO", "CONTABILIDAD", periodo_id, {"estado": "ABIERTO"}, {"estado": "CERRADO", "utilidad_neta": utilidad_neta}, db_path=db_path)
            return True, f"Cierre contable ejecutado con éxito. Utilidad del período: ${utilidad_neta:,.2f}."
        finally:
            conn.close()
