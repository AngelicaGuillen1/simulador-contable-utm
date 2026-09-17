# Treasury Routes: Cash, Arqueo, Banks and Reconciliation
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from routes.auth import login_required
from services.treasury_service import TreasuryService
from services.accounting_service import AccountingService
from services.audit_service import AuditService
from services.period_service import PeriodService
from models import get_db_connection

treasury_bp = Blueprint("treasury", __name__)


@treasury_bp.route("/caja/movimiento", methods=["POST"])
@login_required
def cash_movement():
    """Registra un movimiento de caja con su asiento contable (ingreso, egreso, depósito o retiro)."""
    caja_id = int(request.form.get("caja_id", 1))
    tipo = request.form.get("tipo_movimiento", "INGRESO")
    monto = float(request.form.get("monto", 0.0) or 0.0)
    concepto = request.form.get("concepto", "").strip()
    numero_comprobante = request.form.get("numero_comprobante", "").strip() or None
    banco_id = request.form.get("banco_id")
    fecha = request.form.get("fecha") or PeriodService.get_fecha_trabajo()

    try:
        if not concepto:
            raise ValueError("El concepto del movimiento de caja es obligatorio.")
        if monto <= 0:
            raise ValueError("El monto del movimiento de caja debe ser mayor a 0.")

        caja = None
        conn = get_db_connection()
        try:
            caja = conn.execute("SELECT * FROM cajas WHERE id = ?", (caja_id,)).fetchone()
        finally:
            conn.close()
        if not caja:
            raise ValueError("Caja no encontrada.")
        cuenta_caja = caja["cuenta_contable_id"]

        lineas = []
        origen = "CAJA"
        if tipo in ("INGRESO", "INGRESO_VENTA", "INGRESO_COBRO", "SOBRANTE_CAJA"):
            lineas.append({"cuenta_id": cuenta_caja, "debe": monto, "haber": 0.0, "referencia": concepto})
            lineas.append({"cuenta_id": 33, "debe": 0.0, "haber": monto,
                           "referencia": f"Ingreso en caja: {concepto}"})
        elif tipo in ("EGRESO", "EGRESO_COMPRA", "EGRESO_PAGO", "FALTANTE_CAJA"):
            lineas.append({"cuenta_id": 43, "debe": monto, "haber": 0.0,
                           "referencia": f"Egreso de caja: {concepto}"})
            lineas.append({"cuenta_id": cuenta_caja, "debe": 0.0, "haber": monto, "referencia": concepto})
        elif tipo in ("DEPOSITO_BANCO", "RETIRO"):
            if not banco_id:
                raise ValueError("Debe seleccionar la cuenta bancaria para depósitos y retiros.")
            banco = None
            conn = get_db_connection()
            try:
                banco = conn.execute("SELECT * FROM bancos WHERE id = ?", (int(banco_id),)).fetchone()
            finally:
                conn.close()
            if not banco:
                raise ValueError("Cuenta bancaria no encontrada.")
            if tipo == "DEPOSITO_BANCO":
                lineas.append({"cuenta_id": banco["cuenta_contable_id"], "debe": monto, "haber": 0.0,
                               "referencia": f"Depósito desde caja: {concepto}"})
                lineas.append({"cuenta_id": cuenta_caja, "debe": 0.0, "haber": monto, "referencia": concepto})
                origen = "BANCOS"
            else:
                lineas.append({"cuenta_id": cuenta_caja, "debe": monto, "haber": 0.0,
                               "referencia": f"Retiro de banco: {concepto}"})
                lineas.append({"cuenta_id": banco["cuenta_contable_id"], "debe": 0.0, "haber": monto, "referencia": concepto})
                origen = "BANCOS"
        else:
            raise ValueError(f"Tipo de movimiento de caja no soportado: '{tipo}'.")

        asiento_id, numero = AccountingService.create_journal_entry(
            1, fecha, f"Movimiento de caja - {concepto}", lineas,
            tipo_documento="COMPROBANTE_CAJA", numero_documento=numero_comprobante or f"MC-{fecha}",
            origen_modulo=origen, usuario_id=g.user["id"] if g.user else 1
        )
        TreasuryService.register_cash_movement(
            caja_id, tipo, monto, concepto, numero_comprobante=numero_comprobante,
            asiento_id=asiento_id, fecha=fecha
        )
        if tipo == "DEPOSITO_BANCO" and banco_id:
            TreasuryService.register_bank_movement(
                int(banco_id), "DEPOSITO", monto, f"Depósito desde caja: {concepto}",
                numero_referencia=numero_comprobante, asiento_id=asiento_id, fecha=fecha
            )
        elif tipo == "RETIRO" and banco_id:
            TreasuryService.register_bank_movement(
                int(banco_id), "TRANSFERENCIA_EMITIDA", monto, f"Retiro para caja: {concepto}",
                numero_referencia=numero_comprobante, asiento_id=asiento_id, fecha=fecha
            )
        AuditService.log(g.user["id"] if g.user else 1, g.user["username"] if g.user else "sistema",
                         "MOVIMIENTO_CAJA", "CAJA", caja_id, None,
                         {"tipo": tipo, "monto": monto, "asiento": numero})
        flash(f"Movimiento de caja registrado y contabilizado en el asiento #{numero} por ${monto:,.2f}.", "success")
    except Exception as e:
        flash(f"Error al registrar el movimiento de caja: {str(e)}", "danger")
    return redirect(url_for("treasury.cash"))


@treasury_bp.route("/caja/regularizar/<int:arqueo_id>", methods=["POST"])
@login_required
def regularize_cash_count(arqueo_id):
    """Genera el asiento de ajuste por la diferencia (faltante o sobrante) de un arqueo de caja."""
    try:
        asiento_id, numero, diferencia = TreasuryService.regularize_cash_count(
            arqueo_id, usuario_id=g.user["id"] if g.user else 1
        )
        tipo = "faltante" if diferencia < 0 else "sobrante"
        flash(f"Diferencia de ${abs(diferencia):,.2f} ({tipo}) del arqueo #{arqueo_id} "
              f"regularizada mediante el asiento contable #{numero}.", "success")
    except Exception as e:
        flash(f"No se pudo regularizar el arqueo: {str(e)}", "danger")
    return redirect(url_for("treasury.cash"))


@treasury_bp.route("/bancos/movimiento", methods=["POST"])
@login_required
def bank_movement():
    """Registra un movimiento bancario con su asiento contable."""
    banco_id = int(request.form.get("banco_id", 1))
    tipo = request.form.get("tipo_movimiento", "DEPOSITO")
    monto = float(request.form.get("monto", 0.0) or 0.0)
    concepto = request.form.get("concepto", "").strip()
    referencia = request.form.get("numero_referencia", "").strip() or None
    fecha = request.form.get("fecha") or PeriodService.get_fecha_trabajo()

    try:
        if not concepto:
            raise ValueError("El concepto del movimiento bancario es obligatorio.")
        if monto <= 0:
            raise ValueError("El monto del movimiento bancario debe ser mayor a 0.")
        conn = get_db_connection()
        try:
            banco = conn.execute("SELECT * FROM bancos WHERE id = ?", (banco_id,)).fetchone()
        finally:
            conn.close()
        if not banco:
            raise ValueError("Cuenta bancaria no encontrada.")
        cuenta_banco = banco["cuenta_contable_id"]

        # Tipos que incrementan el disponible bancario frente a los que lo disminuyen
        incrementa = {"DEPOSITO", "TRANSFERENCIA_RECIBIDA", "NOTA_CREDITO", "INTERES"}
        if tipo in incrementa:
            contrapartida = 33 if tipo in ("NOTA_CREDITO", "INTERES") else 6
            lineas = [
                {"cuenta_id": cuenta_banco, "debe": monto, "haber": 0.0, "referencia": concepto},
                {"cuenta_id": contrapartida, "debe": 0.0, "haber": monto,
                 "referencia": f"Acreditación bancaria: {concepto}"}
            ]
        elif tipo in ("TRANSFERENCIA_EMITIDA", "CHEQUE", "NOTA_DEBITO", "COMISION"):
            contrapartida = 43 if tipo in ("NOTA_DEBITO", "COMISION") else 20
            lineas = [
                {"cuenta_id": contrapartida, "debe": monto, "haber": 0.0,
                 "referencia": f"Débito bancario: {concepto}"},
                {"cuenta_id": cuenta_banco, "debe": 0.0, "haber": monto, "referencia": concepto}
            ]
        else:
            raise ValueError(f"Tipo de movimiento bancario no soportado: '{tipo}'.")

        asiento_id, numero = AccountingService.create_journal_entry(
            1, fecha, f"Movimiento bancario {banco['nombre_banco']} - {concepto}", lineas,
            tipo_documento="NOTA_BANCARIA", numero_documento=referencia or f"MB-{fecha}",
            origen_modulo="BANCOS", usuario_id=g.user["id"] if g.user else 1
        )
        TreasuryService.register_bank_movement(
            banco_id, tipo, monto, concepto, numero_referencia=referencia,
            asiento_id=asiento_id, fecha=fecha
        )
        AuditService.log(g.user["id"] if g.user else 1, g.user["username"] if g.user else "sistema",
                         "MOVIMIENTO_BANCARIO", "BANCOS", banco_id, None,
                         {"tipo": tipo, "monto": monto, "asiento": numero})
        flash(f"Movimiento bancario registrado y contabilizado en el asiento #{numero} por ${monto:,.2f}.", "success")
    except Exception as e:
        flash(f"Error al registrar el movimiento bancario: {str(e)}", "danger")
    return redirect(url_for("treasury.banks"))

@treasury_bp.route("/caja", methods=["GET", "POST"])
@login_required
def cash():
    conn = get_db_connection()
    try:
        if request.method == "POST":
            caja_id = int(request.form.get("caja_id", 1))
            saldo_fisico = float(request.form.get("saldo_fisico", 0.0))
            obs = request.form.get("observaciones", "")

            try:
                res = TreasuryService.perform_cash_count(caja_id, saldo_fisico, observaciones=obs, usuario_id=g.user["id"] if g.user else 1)
                if res["estado"] == "CUADRADO":
                    flash(f"Arqueo de Caja exitoso: Saldo Físico (${res['saldo_fisico']:,.2f}) coincide exactamente con el Saldo Contable (${res['saldo_contable']:,.2f}).", "success")
                elif res["estado"] == "SOBRANTE":
                    flash(f"Arqueo de Caja completado con SOBRANTE de ${res['diferencia']:,.2f}. Saldo Físico: ${res['saldo_fisico']:,.2f} vs Contable: ${res['saldo_contable']:,.2f}.", "info")
                else:
                    flash(f"Arqueo de Caja completado con FALTANTE de ${abs(res['diferencia']):,.2f}. Saldo Físico: ${res['saldo_fisico']:,.2f} vs Contable: ${res['saldo_contable']:,.2f}.", "warning")
            except Exception as e:
                flash(f"Error al procesar arqueo de caja: {str(e)}", "danger")
            return redirect(url_for("treasury.cash"))

        cajas = TreasuryService.get_cash_boxes()
        arqueos = conn.execute("""
            SELECT a.*, c.nombre as caja_nombre, u.nombre_completo as usuario_nombre
            FROM arqueos_caja a
            JOIN cajas c ON a.caja_id = c.id
            JOIN usuarios u ON a.usuario_id = u.id
            ORDER BY a.id DESC LIMIT 20
        """).fetchall()

        return render_template("treasury/cash.html", cajas=cajas, arqueos=[dict(a) for a in arqueos],
                               movimientos=TreasuryService.get_cash_movements(limit=40),
                               hoy=PeriodService.get_fecha_trabajo())
    finally:
        conn.close()

@treasury_bp.route("/bancos")
@login_required
def banks():
    conn = get_db_connection()
    try:
        bancos = TreasuryService.get_banks()
        movimientos = conn.execute("""
            SELECT m.*, b.nombre_banco, b.numero_cuenta
            FROM movimientos_bancarios m
            JOIN bancos b ON m.banco_id = b.id
            ORDER BY m.fecha DESC, m.id DESC LIMIT 50
        """).fetchall()

        return render_template("treasury/banks.html", bancos=bancos, movimientos=[dict(m) for m in movimientos],
                               hoy=PeriodService.get_fecha_trabajo())
    finally:
        conn.close()

@treasury_bp.route("/conciliacion", methods=["GET", "POST"])
@login_required
def reconciliation():
    conn = get_db_connection()
    try:
        if request.method == "POST":
            banco_id = int(request.form.get("banco_id"))
            periodo_id = int(request.form.get("periodo_id", 1))
            fecha_corte = request.form.get("fecha_corte", "2026-04-30")
            saldo_ext = float(request.form.get("saldo_extracto", 0.0))
            dep_tran = float(request.form.get("depositos_transito", 0.0))
            chq_tran = float(request.form.get("cheques_transito", 0.0))
            nd_no_reg = float(request.form.get("notas_debito", 0.0))
            nc_no_reg = float(request.form.get("notas_credito", 0.0))
            obs = request.form.get("observaciones", "")

            try:
                res = TreasuryService.perform_bank_reconciliation(
                    banco_id, periodo_id, fecha_corte, saldo_ext,
                    depositos_transito=dep_tran, cheques_transito=chq_tran,
                    notas_debito=nd_no_reg, notas_credito=nc_no_reg,
                    observaciones=obs, usuario_id=g.user["id"] if g.user else 1
                )
                if res["conciliado"]:
                    flash(f"Conciliación bancaria de {res['nombre_banco']} completada exitosamente sin diferencias.", "success")
                else:
                    flash(f"Conciliación bancaria guardada en borrador con diferencia de ${res['diferencia']:,.2f}.", "warning")
            except Exception as e:
                flash(f"Error al procesar conciliación: {str(e)}", "danger")
            return redirect(url_for("treasury.reconciliation"))

        bancos = TreasuryService.get_banks()
        conciliaciones = conn.execute("""
            SELECT c.*, b.nombre_banco, b.numero_cuenta, u.nombre_completo as usuario_nombre
            FROM conciliaciones_bancarias c
            JOIN bancos b ON c.banco_id = b.id
            LEFT JOIN usuarios u ON c.usuario_id = u.id
            ORDER BY c.id DESC
        """).fetchall()

        return render_template("treasury/reconciliation.html", bancos=bancos,
                               conciliaciones=[dict(c) for c in conciliaciones],
                               hoy=PeriodService.get_fecha_trabajo())
    finally:
        conn.close()
