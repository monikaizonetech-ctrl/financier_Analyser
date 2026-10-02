from datetime import date
from app.services.repayment_service import calculate_repayment_capacity
from app.services.file_analysis_service import _parse_pdf_transactions
import os

def test_iob_statement_credit_debit_mapping():
    # Load the actual transactions
    filepath = os.path.join("backend", "uploads", "938dd2e2-ad8e-4f87-947d-f67c83f3f76b", "Account Statement.pdf")
    if not os.path.exists(filepath):
        return # Skip if file not found locally in test runner
        
    txns = _parse_pdf_transactions(filepath, "Account Statement.pdf")
    
    extracted_credit_total = round(sum(float(t.get("credit") or 0.0) for t in txns), 2)
    extracted_debit_total = round(sum(float(t.get("debit") or 0.0) for t in txns), 2)
    
    # The source PDF mathematically sums to 15,779.00 for the Credit(Rs) column
    # and 17,475.25 for the Debit(Rs) column.
    # Therefore, when Debit(Rs) is mapped to canonical.debit, debit = 17475.25.
    
    assert extracted_credit_total == 15779.00
    assert extracted_debit_total == 17475.25
    
def test_living_expenses_cannot_exceed_statement_debits():
    filepath = os.path.join("backend", "uploads", "938dd2e2-ad8e-4f87-947d-f67c83f3f76b", "Account Statement.pdf")
    if not os.path.exists(filepath):
        return
        
    txns = _parse_pdf_transactions(filepath, "Account Statement.pdf")
    
    rc = calculate_repayment_capacity(
        all_rows=txns,
        start_date=date(2026, 8, 23),
        end_date=date(2026, 9, 23),
        is_integrity_verified=True
    )
    
    val = rc["validation_metrics"]
    assert val["total_living_expenses"] <= val["raw_total_debit"]

def test_income_cannot_exceed_statement_credits():
    filepath = os.path.join("backend", "uploads", "938dd2e2-ad8e-4f87-947d-f67c83f3f76b", "Account Statement.pdf")
    if not os.path.exists(filepath):
        return
        
    txns = _parse_pdf_transactions(filepath, "Account Statement.pdf")
    
    rc = calculate_repayment_capacity(
        all_rows=txns,
        start_date=date(2026, 8, 23),
        end_date=date(2026, 9, 23),
        is_integrity_verified=True
    )
    
    val = rc["validation_metrics"]
    assert val["total_verified_income"] <= val["raw_total_credit"]

def test_unknown_emi_is_not_zero():
    # Provide a mock dataset with NO EMI transactions
    mock_txns = [
        {"credit": 5000, "debit": 0, "description": "Salary"},
        {"credit": 0, "debit": 1000, "description": "Groceries"}
    ]
    
    rc = calculate_repayment_capacity(
        all_rows=mock_txns,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        is_integrity_verified=True
    )
    
    assert rc["existing_emi"] is None
    # Current FOIR should be None if there's no EMI, but the status logic should be respected.
    # The requirement states: EMI NOT_IDENTIFIED is not represented as ₹0.
