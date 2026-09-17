# Export all structured tools for agent consumption
from tools.accounting_tools import (
    get_chart_of_accounts,
    get_account,
    get_account_balance,
    validate_journal_entry,
    create_journal_entry,
    reverse_journal_entry,
    close_accounting_period
)
from tools.inventory_tools import (
    get_product,
    get_inventory,
    register_inventory_entry,
    register_inventory_exit,
    calculate_weighted_average,
    calculate_fifo,
    calculate_cost_of_goods_sold
)
from tools.financial_tools import (
    create_sale,
    create_purchase,
    create_service_transaction,
    create_receivable,
    create_payable,
    register_collection,
    register_payment,
    get_customer_balance,
    get_supplier_balance,
    get_cash_balance,
    get_bank_balance,
    reconcile_bank,
    get_tax_configuration,
    calculate_tax,
    generate_trial_balance,
    generate_income_statement,
    generate_balance_sheet,
    generate_cash_flow
)
from tools.simulation_tools import (
    create_simulation_case,
    evaluate_student_attempt,
    generate_feedback,
    get_student_progress,
    audit_transaction
)
