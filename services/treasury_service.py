# Treasury Service: Cash Boxes, Cash Count (Arqueo), Banks & Bank Reconciliation
import sqlite3
from datetime import datetime, date
from models import get_db_contable
from services.accounting_service import AccountingService
from services.audit_service import AuditService
from services.period_service import PeriodService
from services.document_service import DocumentService

class TreasuryService:
    @staticmethod
    def register_cash_movement(caja_id, tipo_movimiento, monto, concepto, numero_comprobante=None, asiento_id=None, fecha=None, db_path=None):
        """
        Registra un movimiento de caja (ingreso, egreso, apertura, depósito, retiro o cierre)
        y sincroniza el saldo de la caja con el saldo real del Libro Mayor.
        """
        if float(monto) <= 0:
            raise ValueError("El monto del movimiento de caja debe ser mayor a 0.")
        fecha_mov = fecha or PeriodService.get_fecha_trabajo(db_path=db_path)
        conn = get_db_contable(db_path)
        try:
            caja = conn.execute("SELECT * FROM cajas WHERE id = ?", (caja_id,)).fetchone()
            if not caja:
                raise ValueError("Caja no encontrada.")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO movimientos_caja (caja_id, fecha, tipo_movimiento, monto, concepto, numero_comprobante, asiento_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (caja_id, fecha_mov, tipo_movimiento, float(monto), concepto, numero_comprobante, asiento_id))
            movimiento_id = cursor.lastrowid
            conn.commit()
            TreasuryService.sync_cash_balance(caja_id, db_path=db_path)
            return movimiento_id
        finally:
            conn.close()

    @staticmethod
    def register_bank_movement(banco_id, tipo_movimiento, monto, concepto, numero_referencia=None, conciliado=0, asiento_id=None, fecha=None, db_path=None):
        """
        Registra un movimiento bancario (depósito, transferencia, cheque, nota de débito/crédito,
        comisión o interés) y sincroniza el saldo del banco con el Libro Mayor.
        """
        if float(monto) <= 0:
            raise ValueError("El monto del movimiento bancario debe ser mayor a 0.")
        fecha_mov = fecha or PeriodService.get_fecha_trabajo(db_path=db_path)
        conn = get_db_contable(db_path)
        try:
            banco = conn.execute("SELECT * FROM bancos WHERE id = ?", (banco_id,)).fetchone()
            if not banco:
                raise ValueError("Cuenta bancaria no encontrada.")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO movimientos_bancarios (banco_id, fecha, tipo_movimiento, monto, concepto, numero_referencia, conciliado, asiento_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (banco_id, fecha_mov, tipo_movimiento, float(monto), concepto, numero_referencia, int(conciliado), asiento_id))
            movimiento_id = cursor.lastrowid
            conn.commit()
            TreasuryService.sync_bank_balance(banco_id, db_path=db_path)
            return movimiento_id
        finally:
            conn.close()

    @staticmethod
    def sync_cash_balance(caja_id, db_path=None):
        conn = get_db_contable(db_path)
        try:
            caja = conn.execute("SELECT * FROM cajas WHERE id = ?", (caja_id,)).fetchone()
            if not caja:
                return None
            saldo = AccountingService.get_account_balance(caja["cuenta_contable_id"], db_path=db_path)
            conn.execute("UPDATE cajas SET saldo_actual = ? WHERE id = ?", (saldo, caja_id))
            conn.commit()
            return saldo
        finally:
            conn.close()

    @staticmethod
    def sync_bank_balance(banco_id, db_path=None):
        conn = get_db_contable(db_path)
        try:
            banco = conn.execute("SELECT * FROM bancos WHERE id = ?", (banco_id,)).fetchone()
            if not banco:
                return None
            saldo = AccountingService.get_account_balance(banco["cuenta_contable_id"], db_path=db_path)
            conn.execute("UPDATE bancos SET saldo_actual = ? WHERE id = ?", (saldo, banco_id))
            conn.commit()
            return saldo
        finally:
            conn.close()

    @staticmethod
    def get_cash_movements(caja_id=None, limit=100, db_path=None):
        conn = get_db_contable(db_path)
        try:
            query = """
                SELECT m.*, c.nombre as caja_nombre
                FROM movimientos_caja m
                JOIN cajas c ON m.caja_id = c.id
            """
            params = []
            if caja_id:
                query += " WHERE m.caja_id = ?"
                params.append(caja_id)
            query += " ORDER BY m.fecha DESC, m.id DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(query, params).fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_cash_boxes(db_path=None):
        conn = get_db_contable(db_path)
        try:
            cajas = conn.execute("SELECT * FROM cajas ORDER BY id ASC").fetchall()
            res = []
            for c in cajas:
                c_dict = dict(c)
                # Compute live accounting balance from journal ledger
                c_dict["saldo_contable_real"] = AccountingService.get_account_balance(c["cuenta_contable_id"], db_path=db_path)
                res.append(c_dict)
            return res
        finally:
            conn.close()

    @staticmethod
    def perform_cash_count(caja_id, saldo_fisico, observaciones="", usuario_id=1, fecha=None, db_path=None):
        """
        Executes Arqueo de Caja:
        Compares Saldo Contable (Libro Mayor) vs Saldo Físico Declarado.
        Calculates Difference: Físico - Contable.
        """
        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            caja = cursor.execute("SELECT * FROM cajas WHERE id = ?", (caja_id,)).fetchone()
            if not caja:
                raise ValueError("Caja no encontrada.")

            saldo_contable = AccountingService.get_account_balance(caja["cuenta_contable_id"], db_path=db_path)
            diferencia = round(float(saldo_fisico) - float(saldo_contable), 2)

            cursor.execute("""
                INSERT INTO arqueos_caja (caja_id, fecha, saldo_contable, saldo_fisico, diferencia, observaciones, usuario_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (caja_id, fecha or PeriodService.get_fecha_trabajo(db_path=db_path), saldo_contable, float(saldo_fisico), diferencia, observaciones, usuario_id))
            arqueo_id = cursor.lastrowid
            conn.commit()

            AuditService.log(usuario_id, "sistema", "ARQUEO_CAJA", "TESORERIA", arqueo_id, {
                "saldo_contable": saldo_contable
            }, {
                "saldo_fisico": float(saldo_fisico), "diferencia": diferencia
            }, db_path=db_path)

            return {
                "id": arqueo_id,
                "caja_id": caja_id,
                "saldo_contable": saldo_contable,
                "saldo_fisico": float(saldo_fisico),
                "diferencia": diferencia,
                "estado": "CUADRADO" if abs(diferencia) < 0.01 else ("SOBRANTE" if diferencia > 0 else "FALTANTE")
            }
        finally:
            conn.close()

    @staticmethod
    def regularize_cash_count(arqueo_id, usuario_id=1, db_path=None):
        """
        Regulariza contablemente la diferencia de un arqueo de caja:
        - Faltante: Debe 6.2.01 Gastos financieros y comisiones / Haber Caja.
        - Sobrante: Debe Caja / Haber 4.2.01 Otros ingresos.
        Vincula el asiento al arqueo (trazabilidad) y sincroniza el saldo de la caja.
        """
        conn = get_db_contable(db_path)
        try:
            arqueo = conn.execute("""
                SELECT a.*, c.nombre as caja_nombre, c.cuenta_contable_id
                FROM arqueos_caja a JOIN cajas c ON a.caja_id = c.id
                WHERE a.id = ?
            """, (arqueo_id,)).fetchone()
            if not arqueo:
                raise ValueError("Arqueo de caja no encontrado.")
            if arqueo["asiento_ajuste_id"]:
                raise ValueError("Este arqueo ya fue regularizado contablemente.")
            diferencia = round(float(arqueo["diferencia"]), 2)
            if abs(diferencia) < 0.01:
                raise ValueError("El arqueo está cuadrado: no existe diferencia que regularizar.")

            cuenta_caja = arqueo["cuenta_contable_id"]
            if diferencia < 0:
                # Faltante de caja: se reconoce un gasto
                lineas = [
                    {"cuenta_id": 43, "debe": abs(diferencia), "haber": 0.0,
                     "referencia": f"Faltante de caja del arqueo #{arqueo_id}"},
                    {"cuenta_id": cuenta_caja, "debe": 0.0, "haber": abs(diferencia),
                     "referencia": f"Regularización de caja arqueo #{arqueo_id}"},
                ]
                glosa = f"Regularización de faltante de caja determinado en el arqueo #{arqueo_id}"
            else:
                # Sobrante de caja: se reconoce un ingreso
                lineas = [
                    {"cuenta_id": cuenta_caja, "debe": diferencia, "haber": 0.0,
                     "referencia": f"Sobrante de caja del arqueo #{arqueo_id}"},
                    {"cuenta_id": 33, "debe": 0.0, "haber": diferencia,
                     "referencia": f"Regularización de caja arqueo #{arqueo_id}"},
                ]
                glosa = f"Regularización de sobrante de caja determinado en el arqueo #{arqueo_id}"
        finally:
            conn.close()

        fecha = PeriodService.get_fecha_trabajo(db_path=db_path)
        asiento_id, numero = AccountingService.create_journal_entry(
            1, fecha, glosa, lineas, tipo_documento="ARQUEO_CAJA",
            numero_documento=f"ARQ-REG-{arqueo_id}", origen_modulo="AJUSTES",
            usuario_id=usuario_id, db_path=db_path
        )

        conn = get_db_contable(db_path)
        try:
            conn.execute("UPDATE arqueos_caja SET asiento_ajuste_id = ? WHERE id = ?", (asiento_id, arqueo_id))
            conn.commit()
        finally:
            conn.close()

        DocumentService.register(
            "ARQUEO_CAJA", f"ARQ-REG-{arqueo_id}", fecha,
            "Comercial y Servicios Nueva Esperanza S.A.", "Caja", abs(diferencia),
            f"Asiento de regularización del arqueo #{arqueo_id} ({'faltante' if diferencia < 0 else 'sobrante'})",
            datos={"arqueo_id": arqueo_id, "diferencia": diferencia, "asiento": numero},
            asiento_id=asiento_id, db_path=db_path
        )
        TreasuryService.sync_cash_balance(arqueo["caja_id"], db_path=db_path)
        AuditService.log(usuario_id, "sistema", "REGULARIZAR_ARQUEO", "TESORERIA", arqueo_id, None,
                         {"diferencia": diferencia, "asiento_id": asiento_id}, db_path=db_path)
        return asiento_id, numero, diferencia

    @staticmethod
    def get_banks(db_path=None):
        conn = get_db_contable(db_path)
        try:
            bancos = conn.execute("SELECT * FROM bancos WHERE activo = 1 ORDER BY id ASC").fetchall()
            res = []
            for b in bancos:
                b_dict = dict(b)
                b_dict["saldo_contable_real"] = AccountingService.get_account_balance(b["cuenta_contable_id"], db_path=db_path)
                res.append(b_dict)
            return res
        finally:
            conn.close()

    @staticmethod
    def perform_bank_reconciliation(banco_id, periodo_id, fecha_corte, saldo_extracto, depositos_transito=0.0, cheques_transito=0.0, notas_debito=0.0, notas_credito=0.0, observaciones="", usuario_id=1, db_path=None):
        """
        Executes Bank Reconciliation:
        Saldo según Extracto Bancario
        + Depósitos en Tránsito
        - Cheques en Tránsito / No Cobrados
        + Notas de Crédito no registradas
        - Notas de Débito no registradas
        = Saldo Conciliado
        Compares against Saldo de Libros Contables.
        """
        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            banco = cursor.execute("SELECT * FROM bancos WHERE id = ?", (banco_id,)).fetchone()
            if not banco:
                raise ValueError("Banco no encontrado.")

            saldo_libros = AccountingService.get_account_balance(banco["cuenta_contable_id"], db_path=db_path)
            
            saldo_ext = float(saldo_extracto)
            dep_tran = float(depositos_transito)
            chq_tran = float(cheques_transito)
            nd_no_reg = float(notas_debito)
            nc_no_reg = float(notas_credito)

            saldo_extracto_ajustado = round(saldo_ext + dep_tran - chq_tran, 2)
            saldo_libros_ajustado = round(saldo_libros + nc_no_reg - nd_no_reg, 2)
            diferencia = round(abs(saldo_extracto_ajustado - saldo_libros_ajustado), 2)
            conciliado = diferencia < 0.05

            cursor.execute("""
                INSERT INTO conciliaciones_bancarias (
                    banco_id, periodo_id, fecha_corte, saldo_extracto_bancario, saldo_libro_bancos,
                    depositos_en_transito, cheques_en_transito, notas_debito_no_registradas,
                    notas_credito_no_registradas, diferencia, estado, usuario_id, observaciones
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (banco_id, periodo_id, fecha_corte, saldo_ext, saldo_libros, dep_tran, chq_tran,
                  nd_no_reg, nc_no_reg, diferencia, "CONCILIADO" if conciliado else "BORRADOR", usuario_id, observaciones))
            conc_id = cursor.lastrowid
            conn.commit()

            AuditService.log(usuario_id, "sistema", "CONCILIACION_BANCARIA", "TESORERIA", conc_id, None, {
                "banco": banco["nombre_banco"], "saldo_extracto": saldo_ext, "saldo_libros": saldo_libros, "diferencia": diferencia, "conciliado": conciliado
            }, db_path=db_path)

            return {
                "id": conc_id,
                "banco_id": banco_id,
                "nombre_banco": banco["nombre_banco"],
                "saldo_extracto": saldo_ext,
                "saldo_libros": saldo_libros,
                "saldo_extracto_ajustado": saldo_extracto_ajustado,
                "saldo_libros_ajustado": saldo_libros_ajustado,
                "diferencia": diferencia,
                "conciliado": conciliado
            }
        finally:
            conn.close()
