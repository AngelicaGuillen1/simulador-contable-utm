# Structured Agent Tools - Accounting & Journal
from services.accounting_service import AccountingService

def get_chart_of_accounts(active_only=True, db_path=None):
    """Retrieves full chart of accounts (Plan de Cuentas)."""
    return AccountingService.get_accounts(active_only=active_only, db_path=db_path)

def get_account(account_id_or_code, db_path=None):
    """Retrieves specific account by ID or code."""
    if isinstance(account_id_or_code, int) or (isinstance(account_id_or_code, str) and account_id_or_code.isdigit()):
        return AccountingService.get_account_by_id(int(account_id_or_code), db_path=db_path)
    return AccountingService.get_account_by_code(str(account_id_or_code), db_path=db_path)

def get_account_balance(account_id, db_path=None):
    """Calculates live balance for an account from the General Ledger."""
    return AccountingService.get_account_balance(int(account_id), db_path=db_path)

def validate_journal_entry(lines):
    """Validates double-entry balance: sum(Debits) == sum(Credits)."""
    is_valid, msg = AccountingService.validate_journal_entry(lines)
    return {"valid": is_valid, "message": msg}

def create_journal_entry(empresa_id, fecha, glosa, lineas, tipo_documento="MANUAL", numero_documento=None, origen_modulo="MANUAL", usuario_id=1, periodo_id=1, db_path=None):
    """Creates a validated, atomic double-entry journal entry."""
    asiento_id, num = AccountingService.create_journal_entry(
        empresa_id, fecha, glosa, lineas, tipo_documento=tipo_documento,
        numero_documento=numero_documento, origen_modulo=origen_modulo,
        usuario_id=usuario_id, periodo_id=periodo_id, db_path=db_path
    )
    return {"asiento_id": asiento_id, "numero_asiento": num, "status": "CONTABILIZADO"}

def reverse_journal_entry(asiento_id, motivo="Reversión contable", usuario_id=1, db_path=None):
    """Reverses an existing journal entry with inverse debit/credit lines."""
    rev_id, rev_num = AccountingService.reverse_journal_entry(asiento_id, motivo=motivo, usuario_id=usuario_id, db_path=db_path)
    return {"reversion_id": rev_id, "numero_reversion": rev_num, "status": "REVERTIDO"}

def close_accounting_period(empresa_id=1, periodo_id=1, usuario_id=1, db_path=None):
    """Executes closing entries for revenue and expense accounts and locks the period."""
    success, msg = AccountingService.execute_period_closing(empresa_id, periodo_id, usuario_id=usuario_id, db_path=db_path)
    return {"success": success, "message": msg}
