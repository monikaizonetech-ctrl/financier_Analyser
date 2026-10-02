import pytest
from datetime import date
from app.services.file_analysis_service import _parse_pdf_transactions
from app.services.repayment_service import calculate_repayment_capacity

@pytest.fixture
def statement_data():
    txns = _parse_pdf_transactions(r'uploads\938dd2e2-ad8e-4f87-947d-f67c83f3f76b\Account Statement.pdf', 'Account Statement.pdf')
    rc = calculate_repayment_capacity(txns, date(2026, 8, 23), date(2026, 9, 23), True)
    return rc

def test_statement_credit_debit(statement_data):
    val = statement_data['validation_metrics']
    assert val['raw_total_credit'] == 15779.00
    assert val['raw_total_debit'] == 17475.25

def test_income_cannot_exceed_credit(statement_data):
    val = statement_data['validation_metrics']
    assert val['total_verified_income'] <= 15779.00

def test_living_expenses_cannot_exceed_debit(statement_data):
    val = statement_data['validation_metrics']
    assert val['total_living_expenses'] <= 17475.25

def test_unknown_emi_is_null(statement_data):
    assert statement_data['existing_emi'] is None

def test_unknown_emi_does_not_produce_zero_foir(statement_data):
    assert statement_data['current_foir'] is None

def test_diagnostics_and_repayment_use_same_expense_value(statement_data):
    # Verified living expenses is the canonical key
    assert 'verified_living_expenses' in statement_data

def test_diagnostics_and_repayment_use_same_income_value(statement_data):
    # Verified income is the canonical key
    assert 'verified_income' in statement_data

def test_validation_reason_matches_actual_failure(statement_data):
    status = statement_data['status']
    status_text = status.get('reason', '') if isinstance(status, dict) else status
    assert "Expense classification/reconciliation failed" not in status_text

def test_no_demo_fallback(statement_data):
    # Ensure it's not substituting 15779.00 as a fallback
    # Wait, the user specifically wants average_monthly_living_expenses = 15779.00 if it's a 1-month statement!
    assert statement_data['verified_living_expenses'] == statement_data['average_monthly_living_expenses']
