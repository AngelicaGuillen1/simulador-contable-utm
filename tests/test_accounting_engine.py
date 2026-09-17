"""Pruebas del motor contable: partida doble, mayor, balance y ecuación patrimonial."""
import pytest

from services.accounting_service import AccountingService
from models import get_db_connection
from services.period_service import PeriodService


# ---------------------------------------------------------------- Partida doble
def test_asiento_descuadrado_es_rechazado_con_mensaje_explicito():
    lineas = [
        {"cuenta_id": 3, "debe": 1250.00, "haber": 0.0},
        {"cuenta_id": 31, "debe": 0.0, "haber": 1150.00},
    ]
    valido, mensaje = AccountingService.validate_journal_entry(lineas)
    assert valido is False
    assert "1,250.00" in mensaje and "1,150.00" in mensaje and "100.00" in mensaje


def test_asiento_balanceado_es_aceptado():
    lineas = [
        {"cuenta_id": 3, "debe": 115.00, "haber": 0.0},
        {"cuenta_id": 31, "debe": 0.0, "haber": 100.00},
        {"cuenta_id": 21, "debe": 0.0, "haber": 15.00},
    ]
    valido, mensaje = AccountingService.validate_journal_entry(lineas)
    assert valido is True


def test_no_se_permite_contabilizar_asiento_descuadrado(db):
    lineas = [
        {"cuenta_id": 3, "debe": 500.00, "haber": 0.0},
        {"cuenta_id": 31, "debe": 0.0, "haber": 400.00},
    ]
    with pytest.raises(ValueError, match="no cuadra"):
        AccountingService.create_journal_entry(
            1, "2026-04-20", "Intento de asiento descuadrado", lineas, db_path=db
        )


def test_todos_los_asientos_del_sistema_cuadran(db):
    conn = get_db_connection(db)
    try:
        descuadres = conn.execute("""
            SELECT a.id, a.numero_asiento, SUM(d.debe) as debe, SUM(d.haber) as haber
            FROM asientos a JOIN detalle_asientos d ON d.asiento_id = a.id
            WHERE a.estado = 'CONTABILIZADO'
            GROUP BY a.id
            HAVING ABS(SUM(d.debe) - SUM(d.haber)) > 0.01
        """).fetchall()
    finally:
        conn.close()
    assert descuadres == [], f"Asientos descuadrados encontrados: {[dict(r) for r in descuadres]}"


def test_todos_los_asientos_tienen_al_menos_dos_lineas(db):
    conn = get_db_connection(db)
    try:
        malos = conn.execute("""
            SELECT a.id, a.numero_asiento, COUNT(d.id) as lineas
            FROM asientos a LEFT JOIN detalle_asientos d ON d.asiento_id = a.id
            WHERE a.estado = 'CONTABILIZADO'
            GROUP BY a.id HAVING COUNT(d.id) < 2
        """).fetchall()
    finally:
        conn.close()
    assert malos == []


# ---------------------------------------------------------------- Balance y mayor
def test_balance_de_comprobacion_cuadra(db):
    trial = AccountingService.get_trial_balance(db_path=db)
    assert trial["cuadrado_sumas"] is True
    assert trial["cuadrado_saldos"] is True
    assert trial["total_debitos"] == trial["total_creditos"]
    assert trial["total_saldo_deudor"] == trial["total_saldo_acreedor"]
    assert trial["total_debitos"] > 0


def test_mayor_coincide_con_el_diario(db):
    """La suma de los movimientos del mayor debe coincidir con la del libro diario."""
    conn = get_db_connection(db)
    try:
        diario = conn.execute("""
            SELECT COALESCE(SUM(d.debe), 0) as debe, COALESCE(SUM(d.haber), 0) as haber
            FROM detalle_asientos d JOIN asientos a ON d.asiento_id = a.id
            WHERE a.estado = 'CONTABILIZADO'
        """).fetchone()
    finally:
        conn.close()

    total_debe = total_haber = 0.0
    for cuenta in AccountingService.get_ledger(db_path=db):
        total_debe += cuenta["total_debe"]
        total_haber += cuenta["total_haber"]

    assert round(total_debe, 2) == round(diario["debe"], 2)
    assert round(total_haber, 2) == round(diario["haber"], 2)


def test_activo_es_igual_a_pasivo_mas_patrimonio(db):
    bs = AccountingService.get_balance_sheet(db_path=db)
    assert bs["balanceado"] is True, f"Diferencia detectada: {bs['diferencia']}"
    assert bs["diferencia"] == 0.0
    assert round(bs["total_activo"], 2) == round(bs["total_pasivo_y_patrimonio"], 2)


def test_cuentas_de_activo_no_quedan_negativas(db):
    """Ninguna cuenta de activo debe presentar saldo contrario (sobre-giro)."""
    trial = AccountingService.get_trial_balance(db_path=db)
    negativas = []
    for c in trial["cuentas"]:
        if c["clasificacion"] in ("ACTIVO_CORRIENTE", "ACTIVO_NO_CORRIENTE") and c["saldo_acreedor"] > 0:
            if c["codigo"] not in ("1.1.05", "1.2.02", "1.2.04", "1.2.06"):  # contra-cuentas válidas
                negativas.append((c["codigo"], c["nombre"], c["saldo_acreedor"]))
    assert negativas == [], f"Cuentas de activo con saldo acreedor inesperado: {negativas}"


def test_reversion_de_asiento_genera_contra_asiento(db):
    conn = get_db_connection(db)
    try:
        asiento = conn.execute("""
            SELECT id, numero_asiento FROM asientos
            WHERE estado = 'CONTABILIZADO' AND origen_modulo = 'VENTAS'
            ORDER BY id ASC LIMIT 1
        """).fetchone()
    finally:
        conn.close()
    assert asiento is not None

    saldo_antes = AccountingService.get_account_balance(3, db_path=db)

    conn = get_db_connection(db)
    try:
        efecto_original = conn.execute("""
            SELECT COALESCE(SUM(debe - haber), 0) as efecto FROM detalle_asientos
            WHERE asiento_id = ? AND cuenta_id = 3
        """, (asiento["id"],)).fetchone()["efecto"]
        lineas_originales = {(r["cuenta_id"], round(r["debe"], 2), round(r["haber"], 2)) for r in conn.execute(
            "SELECT cuenta_id, debe, haber FROM detalle_asientos WHERE asiento_id = ?", (asiento["id"],))}
    finally:
        conn.close()

    rev_id, rev_numero = AccountingService.reverse_journal_entry(asiento["id"], usuario_id=1, db_path=db)
    assert rev_id > 0 and rev_numero > asiento["numero_asiento"]

    conn = get_db_connection(db)
    try:
        original = conn.execute("SELECT estado, asiento_reversion_id FROM asientos WHERE id = ?",
                                (asiento["id"],)).fetchone()
        lineas_rev = conn.execute("SELECT cuenta_id, debe, haber FROM detalle_asientos WHERE asiento_id = ?",
                                  (rev_id,)).fetchall()
    finally:
        conn.close()

    assert original["estado"] == "REVERTIDO"
    assert original["asiento_reversion_id"] == rev_id
    assert len(lineas_rev) == len(lineas_originales)

    # El contra-asiento debe invertir exactamente cada línea del original
    lineas_invertidas = {(l["cuenta_id"], round(l["haber"], 2), round(l["debe"], 2)) for l in lineas_rev}
    assert lineas_invertidas == lineas_originales

    # El par original + reversión se anula: el saldo vuelve al estado previo a la operación anulada
    assert AccountingService.get_account_balance(3, db_path=db) == pytest.approx(
        saldo_antes - float(efecto_original), abs=0.01)


# ---------------------------------------------------------------- Períodos
def test_fecha_de_trabajo_dentro_del_periodo_abierto(db):
    periodo = PeriodService.get_active_period(db_path=db)
    fecha = PeriodService.get_fecha_trabajo(db_path=db)
    assert periodo is not None
    assert periodo["estado"] == "ABIERTO"
    assert periodo["fecha_inicio"] <= fecha <= periodo["fecha_fin"]


def test_fecha_fuera_del_periodo_es_rechazada(db):
    with pytest.raises(ValueError):
        PeriodService.set_fecha_trabajo("2026-07-15", db_path=db)


def test_operacion_con_fecha_fuera_del_periodo_es_rechazada(db):
    from services.sales_service import SalesService
    with pytest.raises(ValueError, match="fuera del periodo|fuera del período"):
        SalesService.create_sale(
            1, 3, [{"producto_id": 1, "cantidad": 1, "precio_unitario": 5.20}],
            forma_pago="EFECTIVO", fecha="2026-08-01", db_path=db
        )


def test_plan_de_cuentas_jerarquico_y_clasificado(db):
    cuentas = AccountingService.get_accounts(db_path=db)
    assert len(cuentas) >= 40
    codigos = {c["codigo"] for c in cuentas}
    for obligatoria in ["1.1.01", "1.1.04", "1.1.06", "2.1.01", "2.1.02", "3.1.01", "4.1.01",
                        "4.1.02", "5.1.01", "6.1.01", "6.2.01"]:
        assert obligatoria in codigos
    for c in cuentas:
        assert c["naturaleza"] in ("DEUDORA", "ACREEDORA")
        if c["cuenta_padre_id"]:
            assert str(c["nivel"]) not in ("", "None")
