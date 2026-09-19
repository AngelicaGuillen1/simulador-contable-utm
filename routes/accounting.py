# Accounting Routes: Plan de Cuentas, Diario, Mayor, Balance, Ajustes, Cierre
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g
from routes.auth import login_required, roles_required
from services.accounting_service import AccountingService
from services.document_service import DocumentService
from services.period_service import PeriodService
from models import get_db_contable

accounting_bp = Blueprint("accounting", __name__, url_prefix="/contabilidad")


def _cuenta_id(codigo, respaldo):
    """Resuelve el id de una cuenta por su código, con respaldo por id del plan de cuentas."""
    cuenta = AccountingService.get_account_by_code(codigo)
    return cuenta["id"] if cuenta else respaldo

@accounting_bp.route("/cuentas", methods=["GET", "POST"])
@login_required
def accounts():
    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()
        nombre = request.form.get("nombre", "").strip()
        naturaleza = request.form.get("naturaleza", "DEUDORA")
        clasificacion = request.form.get("clasificacion", "ACTIVO_CORRIENTE")
        cuenta_padre_id = request.form.get("cuenta_padre_id") or None
        nivel = int(request.form.get("nivel", 1))
        acepta_movimiento = int(request.form.get("acepta_movimiento", 1))

        try:
            AccountingService.create_account(codigo, nombre, naturaleza, clasificacion, cuenta_padre_id, nivel, acepta_movimiento)
            flash(f"Cuenta '{codigo} - {nombre}' creada exitosamente.", "success")
        except Exception as e:
            flash(f"Error al crear cuenta: {str(e)}", "danger")
        return redirect(url_for("accounting.accounts"))

    cuentas = AccountingService.get_accounts(active_only=False)
    # Add live balances
    for c in cuentas:
        c["saldo_actual"] = AccountingService.get_account_balance(c["id"]) if c["acepta_movimiento"] else 0.0

    return render_template("accounting/accounts.html", cuentas=cuentas)

@accounting_bp.route("/cuentas/<int:account_id>/editar", methods=["POST"])
@login_required
def edit_account(account_id):
    nombre = request.form.get("nombre", "").strip()
    naturaleza = request.form.get("naturaleza", "DEUDORA")
    clasificacion = request.form.get("clasificacion", "ACTIVO_CORRIENTE")
    activo = int(request.form.get("activo", 1))

    try:
        AccountingService.update_account(account_id, nombre, naturaleza, clasificacion, activo)
        flash("Cuenta contable actualizada correctamente.", "success")
    except Exception as e:
        flash(f"Error al actualizar cuenta: {str(e)}", "danger")
    return redirect(url_for("accounting.accounts"))

@accounting_bp.route("/diario", methods=["GET", "POST"])
@login_required
def journal():
    if request.method == "POST":
        fecha = request.form.get("fecha")
        glosa = request.form.get("glosa", "").strip()
        tipo_doc = request.form.get("tipo_documento", "MANUAL")
        num_doc = request.form.get("numero_documento", "").strip()

        cuentas_ids = request.form.getlist("cuenta_id[]")
        debes = request.form.getlist("debe[]")
        haberes = request.form.getlist("haber[]")
        referencias = request.form.getlist("referencia[]")

        lineas = []
        for i in range(len(cuentas_ids)):
            if cuentas_ids[i]:
                d = float(debes[i] or 0.0)
                h = float(haberes[i] or 0.0)
                if d > 0 or h > 0:
                    lineas.append({
                        "cuenta_id": int(cuentas_ids[i]),
                        "debe": d,
                        "haber": h,
                        "referencia": referencias[i] if i < len(referencias) else ""
                    })

        try:
            asiento_id, num = AccountingService.create_journal_entry(
                1, fecha, glosa, lineas, tipo_documento=tipo_doc,
                numero_documento=num_doc, origen_modulo="MANUAL",
                usuario_id=g.user["id"] if g.user else 1
            )
            DocumentService.register(
                tipo_doc or "DOCUMENTO_INTERNO", num_doc or f"ASI-{num}", fecha,
                "Comercial y Servicios Nueva Esperanza S.A.", "Contabilidad",
                round(sum(l["debe"] for l in lineas), 2),
                f"Asiento manual de libro diario #{num}: {glosa}",
                datos={"lineas": len(lineas), "origen": "REGISTRO_MANUAL"}, asiento_id=asiento_id
            )
            flash(f"Asiento Contable #{num} registrado exitosamente con partida doble.", "success")
        except ValueError as ve:
            flash(f"Error de validación contable: {str(ve)}", "danger")
        except Exception as e:
            flash(f"Error inesperado al guardar asiento: {str(e)}", "danger")
        return redirect(url_for("accounting.journal"))

    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    asientos = AccountingService.get_journal_entries(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    cuentas = AccountingService.get_accounts(active_only=True)

    return render_template("accounting/journal.html", asientos=asientos, cuentas=cuentas)

@accounting_bp.route("/diario/<int:asiento_id>/revertir", methods=["POST"])
@login_required
def reverse_journal(asiento_id):
    motivo = request.form.get("motivo", "Reversión contable solicitada por usuario")
    try:
        rev_id, rev_num = AccountingService.reverse_journal_entry(asiento_id, motivo=motivo, usuario_id=g.user["id"] if g.user else 1)
        flash(f"Asiento #{asiento_id} revertido con éxito mediante nuevo Asiento de Reversión #{rev_num}.", "info")
    except Exception as e:
        flash(f"Error al revertir asiento: {str(e)}", "danger")
    return redirect(url_for("accounting.journal"))

@accounting_bp.route("/mayor")
@login_required
def ledger():
    cuenta_id = request.args.get("cuenta_id", type=int)
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")

    cuentas = AccountingService.get_accounts(active_only=True)
    ledger_data = AccountingService.get_ledger(cuenta_id=cuenta_id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

    return render_template("accounting/ledger.html", ledger_data=ledger_data, cuentas=cuentas, selected_cuenta_id=cuenta_id)

@accounting_bp.route("/balance")
@login_required
def trial_balance():
    fecha_corte = request.args.get("fecha_corte")
    trial_data = AccountingService.get_trial_balance(fecha_corte=fecha_corte)
    return render_template("accounting/trial_balance.html", trial=trial_data, fecha_corte=fecha_corte)

@accounting_bp.route("/ajustes", methods=["GET", "POST"])
@login_required
def adjustments():
    if request.method == "POST":
        tipo_ajuste = request.form.get("tipo_ajuste")
        glosa = request.form.get("glosa", "Ajuste contable periódico")
        monto = float(request.form.get("monto", 0.0))

        try:
            cta_dep = _cuenta_id("6.1.04", 40)
            cta_muebles = _cuenta_id("1.2.02", 13)
            cta_computo = _cuenta_id("1.2.04", 15)
            cta_vehiculo = _cuenta_id("1.2.06", 17)
            cta_incobrables = _cuenta_id("1.1.05", 7)
            cta_gasto_fin = _cuenta_id("6.2.01", 43)

            if tipo_ajuste == "DEPRECIACION":
                dep_muebles = round(monto * 0.15, 2)
                dep_computo = round(monto * 0.25, 2)
                dep_vehiculo = round(monto - dep_muebles - dep_computo, 2)
                lineas = [
                    {"cuenta_id": cta_dep, "debe": monto, "haber": 0.0, "referencia": "Gasto depreciación activos fijos"},
                    {"cuenta_id": cta_muebles, "debe": 0.0, "haber": dep_muebles, "referencia": "Deprec. Acum Muebles"},
                    {"cuenta_id": cta_computo, "debe": 0.0, "haber": dep_computo, "referencia": "Deprec. Acum Cómputo"},
                    {"cuenta_id": cta_vehiculo, "debe": 0.0, "haber": dep_vehiculo, "referencia": "Deprec. Acum Vehículo"}
                ]
            elif tipo_ajuste == "INCOBRABLES":
                lineas = [
                    {"cuenta_id": cta_gasto_fin, "debe": monto, "haber": 0.0, "referencia": "Gasto provisión cuentas incobrables"},
                    {"cuenta_id": cta_incobrables, "debe": 0.0, "haber": monto, "referencia": "Provisión acumulada cartera"}
                ]
            else:
                flash("Tipo de ajuste no reconocido.", "warning")
                return redirect(url_for("accounting.adjustments"))

            fecha_ajuste = request.form.get("fecha") or PeriodService.get_fecha_trabajo()
            numero_ajuste = f"AJU-{tipo_ajuste[:3]}-{fecha_ajuste}"
            asiento_id, num = AccountingService.create_journal_entry(
                1, fecha_ajuste, glosa, lineas,
                tipo_documento="COMPROBANTE_AJUSTE", numero_documento=numero_ajuste,
                origen_modulo="AJUSTES", usuario_id=g.user["id"] if g.user else 1
            )
            DocumentService.register(
                "COMPROBANTE_AJUSTE", numero_ajuste, fecha_ajuste,
                "Comercial y Servicios Nueva Esperanza S.A.", "Contabilidad", monto,
                f"Comprobante del ajuste contable #{num} ({tipo_ajuste})",
                datos={"tipo_ajuste": tipo_ajuste, "monto": monto, "lineas": lineas},
                asiento_id=asiento_id
            )
            flash(f"Ajuste contable #{num} registrado y mayorizado exitosamente.", "success")
        except Exception as e:
            flash(f"Error al registrar ajuste: {str(e)}", "danger")
        return redirect(url_for("accounting.adjustments"))

    # Summary of adjustments
    asientos_ajuste = AccountingService.get_journal_entries()
    ajustes_list = [a for a in asientos_ajuste if a["origen_modulo"] == "AJUSTES"]
    return render_template("accounting/adjustments.html", ajustes=ajustes_list)

@accounting_bp.route("/cierre", methods=["GET", "POST"])
@login_required
@roles_required("Administrador", "Docente")
def closing():
    income_stmt = AccountingService.get_income_statement()
    trial = AccountingService.get_trial_balance()

    if request.method == "POST":
        try:
            success, msg = AccountingService.execute_period_closing(1, 1, usuario_id=g.user["id"] if g.user else 1)
            DocumentService.register(
                "COMPROBANTE_CIERRE", "CIE-2026-04", PeriodService.get_fecha_trabajo(),
                "Comercial y Servicios Nueva Esperanza S.A.", "Contabilidad",
                round(sum(c["saldo_deudor"] for c in trial["cuentas"]), 2),
                "Comprobante del cierre contable del período (cancelación de ingresos, costos y gastos)",
                datos={"utilidad_neta": income_stmt["utilidad_neta"], "resultado": msg}
            )
            flash(msg, "success" if success else "danger")
        except Exception as e:
            flash(f"Error al ejecutar el cierre contable: {str(e)}", "danger")
        return redirect(url_for("accounting.closing"))

    conn = get_db_contable()
    periodo = conn.execute("SELECT * FROM periodos WHERE id = 1").fetchone()
    conn.close()

    return render_template("accounting/closing.html", income=income_stmt, trial=trial, periodo=dict(periodo) if periodo else {})
