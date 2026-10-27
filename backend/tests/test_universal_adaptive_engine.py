"""
Comprehensive automated test suite for the Universal Adaptive Bank Statement Extraction Engine.
Validates:
1. Universal date parsing with ambiguity resolution
2. Universal Decimal amount parsing (Indian/Western formats, currencies, parens, Dr/Cr)
3. Dynamic header and column detection past row 5 without templates
4. Multi-line narration reconstruction and footer bleed prevention
5. Mathematical balance equation solver and debit/credit assignment
6. Dynamic financial categorization and own-account inference
7. Transparent confidence scoring
8. End-to-end PDF extraction across diverse layouts
"""
from datetime import date
from decimal import Decimal
import os
import tempfile
import pytest

from app.services.adaptive_models import (
    ColumnRole,
    AmountMode,
    DetectedColumn,
    HeaderCandidate,
    NormalizedTransaction,
    ReconciliationStatus,
    ValidationStatus,
)
from app.services.financial_normalizer import (
    UniversalDateNormalizer,
    UniversalAmountNormalizer,
)
from app.services.adaptive_header_detector import (
    AdaptiveHeaderDetector,
    match_cell_role,
)
from app.services.narration_reconstructor import (
    NarrationReconstructor,
    is_noise_or_summary_line,
    clean_narration,
)
from app.services.balance_reconciliation_engine import BalanceReconciliationEngine
from app.services.financial_classifier import FinancialClassifier
from app.services.extraction_confidence import ExtractionConfidenceEvaluator
from app.services.bank_statement_pipeline import BankStatementPipeline
from tests.statement_generator import create_statement_pdf


# ==============================================================================
# 1. Date Normalization Tests
# ==============================================================================

def test_universal_date_normalization_formats():
    normalizer = UniversalDateNormalizer()

    # Standard formats
    assert normalizer.parse("15/08/2026")[0] == date(2026, 8, 15)
    assert normalizer.parse("15-08-2026")[0] == date(2026, 8, 15)
    assert normalizer.parse("15.08.2026")[0] == date(2026, 8, 15)
    assert normalizer.parse("2026-08-15")[0] == date(2026, 8, 15)

    # Text months
    assert normalizer.parse("15-Aug-2026")[0] == date(2026, 8, 15)
    assert normalizer.parse("15 Aug 2026")[0] == date(2026, 8, 15)
    assert normalizer.parse("August 15, 2026")[0] == date(2026, 8, 15)

    # 2-digit years
    assert normalizer.parse("15/08/26")[0] == date(2026, 8, 15)
    assert normalizer.parse("15-Aug-26")[0] == date(2026, 8, 15)


def test_date_ambiguity_resolution_using_document_context():
    # Ambiguous date: 03/04/2026 (could be April 3 or March 4)
    normalizer_dd_mm = UniversalDateNormalizer(prefer_day_first=True)
    normalizer_dd_mm.feed_evidence("25/07/2026")  # 25 > 12 -> proves DD/MM
    d1, is_ambig1, conf1 = normalizer_dd_mm.parse("03/04/2026")
    assert d1 == date(2026, 4, 3)
    assert is_ambig1 is True
    assert conf1 >= 0.85

    normalizer_mm_dd = UniversalDateNormalizer(prefer_day_first=False)
    normalizer_mm_dd.feed_evidence("07/25/2026")  # second token > 12 -> proves MM/DD
    d2, is_ambig2, conf2 = normalizer_mm_dd.parse("03/04/2026")
    assert d2 == date(2026, 3, 4)
    assert is_ambig2 is True


# ==============================================================================
# 2. Amount Normalization Tests
# ==============================================================================

def test_universal_amount_normalization():
    norm = UniversalAmountNormalizer

    # Indian comma notation: 12,34,567.89
    amt, dr_cr, valid, _ = norm.parse("12,34,567.89")
    assert amt == Decimal("1234567.89")
    assert valid is True

    # International comma notation: 1,234,567.89
    amt2, _, valid2, _ = norm.parse("1,234,567.89")
    assert amt2 == Decimal("1234567.89")
    assert valid2 is True

    # Currency symbols & non-breaking spaces
    amt3, _, _, _ = norm.parse("₹ 25,000.50\xa0")
    assert amt3 == Decimal("25000.50")

    amt4, _, _, _ = norm.parse("Rs. 1,500.00")
    assert amt4 == Decimal("1500.00")

    # Parentheses negatives & Dr/Cr markers
    amt5, dir5, _, _ = norm.parse("(500.00)")
    assert amt5 == Decimal("500.00")
    assert dir5 == "DR"

    amt6, dir6, _, _ = norm.parse("1,200.00 Dr")
    assert amt6 == Decimal("1200.00")
    assert dir6 == "DR"

    amt7, dir7, _, _ = norm.parse("3,450.00 Cr")
    assert amt7 == Decimal("3450.00")
    assert dir7 == "CR"

    # Genuine zero vs missing
    zero_amt, _, _, _ = norm.parse("0.00")
    assert zero_amt == Decimal("0.00")

    none_amt, _, _, _ = norm.parse("-")
    assert none_amt is None

    empty_amt, _, _, _ = norm.parse("")
    assert empty_amt is None


# ==============================================================================
# 3. Dynamic Header and Column Detection Tests
# ==============================================================================

def test_header_detection_past_row_5():
    detector = AdaptiveHeaderDetector()

    # Table where first 10 rows are metadata / branch details
    table = [
        ["STATE BANK OF INDIA", None, None, None, None],
        ["Branch: Connaught Place, New Delhi", None, None, None, None],
        ["IFSC: SBIN0000691", None, None, None, None],
        ["Account Holder: Alpha Traders Pvt Ltd", None, None, None, None],
        ["Account Number: 30918239102", None, None, None, None],
        ["Customer ID: 89123891", None, None, None, None],
        ["Nominee: Registered", None, None, None, None],
        ["Email: alpha@example.com", None, None, None, None],
        ["Statement Period: 01/04/2026 to 30/04/2026", None, None, None, None],
        [None, None, None, None, None],
        # The actual header is on Row 10!
        ["Txn Date", "Particulars", "Chq No", "Debit", "Credit", "Balance"],
        ["01/04/2026", "Opening Balance b/f", "", "", "", "1,50,000.00"],
    ]

    candidate = detector.detect_header_from_table(table, page_number=1)
    assert candidate is not None
    assert candidate.page_number == 1
    assert candidate.y_top == 10.0  # Found at index 10!
    assert candidate.has_date is True
    assert candidate.has_description is True
    assert candidate.has_amount is True
    assert candidate.has_balance is True
    assert candidate.amount_mode == AmountMode.SEPARATE_DR_CR


def test_header_detection_single_amount_with_dr_cr():
    detector = AdaptiveHeaderDetector()

    table = [
        ["Date", "Narration", "Reference", "Amount", "Dr/Cr", "Balance"],
        ["01/05/2026", "UPI/Zomato", "129031", "450.00", "Dr", "24,550.00"],
    ]

    candidate = detector.detect_header_from_table(table, page_number=1)
    assert candidate is not None
    assert candidate.amount_mode == AmountMode.SINGLE_AMOUNT_WITH_INDICATOR


# ==============================================================================
# 4. Narration Reconstruction & Noise Filtering Tests
# ==============================================================================

def test_narration_reconstruction_and_continuation():
    recon = NarrationReconstructor()

    # Start txn 1
    recon.start_transaction("UPI/3109281902/Swiggy Orders")
    assert recon.append_continuation("Bangalore KA IN") is True
    assert recon.append_continuation("Page 1 of 5") is False  # Noise must be filtered!
    assert recon.append_continuation("Ref: 98123019283") is True

    normalized, raw = recon.build_narrations()
    assert "Swiggy Orders Bangalore KA IN Ref: 98123019283" in normalized
    assert "Page 1 of 5" not in normalized


def test_noise_line_detection():
    assert is_noise_or_summary_line("Page 2 of 10") is True
    assert is_noise_or_summary_line("* END OF STATEMENT *") is True
    assert is_noise_or_summary_line("This is a system generated statement") is True
    assert is_noise_or_summary_line("-----------------------------") is True
    assert is_noise_or_summary_line("UPI/3091823/Vendor Payment") is False


# ==============================================================================
# 5. Balance Reconciliation Engine Tests
# ==============================================================================

def test_mathematical_balance_solver_reconciliation_pass():
    # Mathematically valid transactions
    # Opening: 10,000.00
    # Txn 1: +5,000.00 -> 15,000.00
    # Txn 2: -2,000.00 -> 13,000.00
    # Txn 3: -3,500.00 -> 9,500.00
    txns = [
        NormalizedTransaction(
            s_no=1,
            transaction_date=date(2026, 4, 1),
            description="Client Deposit",
            raw_description="Client Deposit",
            credit=Decimal("5000.00"),
            balance=Decimal("15000.00"),
        ),
        NormalizedTransaction(
            s_no=2,
            transaction_date=date(2026, 4, 2),
            description="Office Rent",
            raw_description="Office Rent",
            debit=Decimal("2000.00"),
            balance=Decimal("13000.00"),
        ),
        NormalizedTransaction(
            s_no=3,
            transaction_date=date(2026, 4, 3),
            description="Vendor Payment",
            raw_description="Vendor Payment",
            debit=Decimal("3500.00"),
            balance=Decimal("9500.00"),
        ),
    ]

    res = BalanceReconciliationEngine.reconcile(
        txns,
        statement_opening_balance=Decimal("10000.00"),
        statement_closing_balance=Decimal("9500.00"),
    )

    assert res.status == ReconciliationStatus.PASS
    assert res.opening_balance == Decimal("10000.00")
    assert res.total_credit == Decimal("5000.00")
    assert res.total_debit == Decimal("5500.00")
    assert res.net_cash_flow == Decimal("-500.00")
    assert res.computed_closing_balance == Decimal("9500.00")
    assert res.closing_difference == Decimal("0.00")
    assert res.verified_transactions == 3
    assert res.mismatched_transactions == 0


def test_mathematical_balance_solver_detects_mismatch():
    # Txn 2 balance jumps unaccountably (indicates missing transaction or arithmetic error)
    txns = [
        NormalizedTransaction(
            s_no=1,
            transaction_date=date(2026, 4, 1),
            description="Deposit",
            raw_description="Deposit",
            credit=Decimal("1000.00"),
            balance=Decimal("6000.00"),  # Opening 5000 + 1000 = 6000
        ),
        NormalizedTransaction(
            s_no=2,
            transaction_date=date(2026, 4, 2),
            description="Expense",
            raw_description="Expense",
            debit=Decimal("200.00"),
            balance=Decimal("4500.00"),  # Expected 5800, found 4500!
        ),
    ]

    res = BalanceReconciliationEngine.reconcile(
        txns,
        statement_opening_balance=Decimal("5000.00"),
        statement_closing_balance=Decimal("5800.00"),
    )

    assert res.status == ReconciliationStatus.FAIL
    assert res.mismatched_transactions == 1
    assert len(res.balance_mismatches) == 1
    assert res.balance_mismatches[0]["difference"] == 1300.00


def test_candidate_debit_credit_solver():
    # Test candidate column resolution when columns are ambiguous
    candidate_rows = [
        {"col_1": 0.0, "col_2": 5000.0, "balance": 15000.0},
        {"col_1": 2000.0, "col_2": 0.0, "balance": 13000.0},
        {"col_1": 1000.0, "col_2": 0.0, "balance": 12000.0},
    ]

    # If col_1 is Debit and col_2 is Credit:
    # 15000 - 2000 + 0 = 13000 (Matches!)
    # 13000 - 1000 + 0 = 12000 (Matches!)
    score_a = BalanceReconciliationEngine.test_debit_credit_assignment(
        candidate_rows, col_a_is_debit=True, col_a_key="col_1", col_b_key="col_2"
    )
    assert score_a == 1.0  # 100% match!

    # If inverted (col_1 is Credit, col_2 is Debit):
    score_b = BalanceReconciliationEngine.test_debit_credit_assignment(
        candidate_rows, col_a_is_debit=False, col_a_key="col_1", col_b_key="col_2"
    )
    assert score_b == 0.0  # 0% match!


# ==============================================================================
# 6. Financial Classifier & Dynamic Own Account Tests
# ==============================================================================

def test_financial_classifier_and_counterparty_extraction():
    # UPI
    cat1, mode1, cp1, _, _ = FinancialClassifier.classify("UPI/3091823/SWIGGY/swiggy@icici", is_credit=False)
    assert mode1 == "UPI"
    assert "SWIGGY" in cp1.upper() or "3091823" in cp1

    # EMI
    cat2, mode2, _, is_own2, is_emi2 = FinancialClassifier.classify("ACH/HDB FINANCIAL SERVICES/EMI-39182", is_credit=False)
    assert is_emi2 is True
    assert "EMI" in cat2

    # Salary
    cat3, _, _, _, _ = FinancialClassifier.classify("NEFT-SBIN12345-PAYROLL SALARY APRIL 2026", is_credit=True)
    assert "Salary" in cat3

    # Dynamic Own Account inference from Document Account Holder (without hardcoding)
    holder_name = "RAMACHANDRAN VENKATARAMAN"
    cat4, _, _, is_own4, _ = FinancialClassifier.classify(
        "TRANSFER TO VENKATARAMAN", is_credit=False, account_holder=holder_name
    )
    assert is_own4 is True
    assert cat4 == "Internal Transfer"


# ==============================================================================
# 7. Confidence Scoring Tests
# ==============================================================================

def test_confidence_scoring_and_uncertainty_flags():
    # High confidence transaction
    txn_valid = NormalizedTransaction(
        s_no=1,
        transaction_date=date(2026, 4, 1),
        description="Electricity Bill Payment",
        raw_description="Electricity Bill Payment",
        debit=Decimal("1500.00"),
        balance=Decimal("20000.00"),
        validation_status=ValidationStatus.VALID,
    )
    score1 = ExtractionConfidenceEvaluator.evaluate_transaction(txn_valid)
    assert score1 >= 0.85
    assert txn_valid.confidence_score >= 0.85

    # Low confidence transaction (missing date, short description, warning status)
    txn_uncertain = NormalizedTransaction(
        s_no=2,
        transaction_date=None,  # missing date
        description="x",
        raw_description="x",
        debit=Decimal("100.00"),
        validation_status=ValidationStatus.WARNING,
    )
    score2 = ExtractionConfidenceEvaluator.evaluate_transaction(txn_uncertain)
    assert score2 < 0.70
    assert any("Low extraction confidence" in w for w in txn_uncertain.validation_warnings)


# ==============================================================================
# 8. End-to-End Synthetic PDF Pipeline Verification
# ==============================================================================

def test_end_to_end_bordered_pdf_pipeline():
    """Generates a bordered PDF bank statement with ReportLab and processes it through the pipeline."""
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "test_bordered_statement.pdf")

    headers = ["Date", "Description", "Chq No", "Debit", "Credit", "Balance"]
    col_x = [50, 110, 260, 320, 390, 460]
    rows = [
        ["01/06/2026", "Opening Balance b/f", "", "", "", "50,000.00"],
        ["05/06/2026", "Client Inward NEFT", "981230", "", "25,000.00", "75,000.00"],
        ["12/06/2026", "Office Stationery Store", "4412", "3,500.00", "", "71,500.00"],
        ["20/06/2026", "Broadband Internet Bill", "", "1,200.00", "", "70,300.00"],
        ["28/06/2026", "Consulting Fee Receipt", "1109", "", "15,000.00", "85,300.00"],
    ]

    create_statement_pdf(
        file_path=pdf_path,
        bank_name="HDFC BANK",
        account_holder="Zenith Technologies Ltd",
        account_no="5010029318239",
        headers=headers,
        col_x_positions=col_x,
        rows_data=rows,
        table_bordered=True,
    )

    pipeline = BankStatementPipeline()
    result = pipeline.process_document(pdf_path, "test_bordered_statement.pdf")

    assert result["has_data"] is True
    assert result["transactions_found"] >= 4
    assert result["total_credits"] == 40000.00
    assert result["total_debits"] == 4700.00
    assert result["net_cash_flow"] == 35300.00
    assert result["closing_balance"] == 85300.00
    assert result["reconciliation"]["is_verified"] is True
    assert result["extraction_quality_score"] >= 80.0

    # Cleanup
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_end_to_end_descending_dates_normalized_to_ascending():
    """Validates that statements provided in descending date order are normalized to ascending."""
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "test_descending_statement.pdf")

    headers = ["Date", "Particulars", "Chq No", "Debit", "Credit", "Balance"]
    col_x = [50, 110, 260, 320, 390, 460]
    # Reverse chronological order
    rows = [
        ["28/06/2026", "Consulting Fee Receipt", "1109", "", "15,000.00", "85,300.00"],
        ["20/06/2026", "Broadband Internet Bill", "", "1,200.00", "", "70,300.00"],
        ["12/06/2026", "Office Stationery Store", "4412", "3,500.00", "", "71,500.00"],
        ["05/06/2026", "Client Inward NEFT", "981230", "", "25,000.00", "75,000.00"],
        ["01/06/2026", "Opening Balance b/f", "", "", "", "50,000.00"],
    ]

    create_statement_pdf(
        file_path=pdf_path,
        bank_name="AXIS BANK",
        account_holder="Sigma Enterprise",
        account_no="9120100293182",
        headers=headers,
        col_x_positions=col_x,
        rows_data=rows,
        table_bordered=True,
    )

    pipeline = BankStatementPipeline()
    result = pipeline.process_document(pdf_path, "test_descending_statement.pdf")

    assert result["has_data"] is True
    # Verify chronological ascending normalization
    txns = result["transactions"]
    assert txns[0]["date"] <= txns[-1]["date"]
    assert txns[0]["date"] == date(2026, 6, 5)
    assert txns[-1]["date"] == date(2026, 6, 28)

    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_end_to_end_multiline_narration_assembly():
    """Validates that multiline descriptions are properly merged across row breaks."""
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "test_multiline_statement.pdf")

    headers = ["Date", "Narration", "Ref", "Amount", "Type", "Balance"]
    col_x = [50, 110, 260, 330, 400, 460]
    # Narration with \n line breaks
    rows = [
        ["02/08/2026", "UPI/391028391/Merchant Payment\nFood Delivery Services\nBangalore KA", "REF501", "850.00", "Dr", "49,150.00"],
        ["08/08/2026", "NEFT Inward From Alpha\nInvoice 2026-081\nServices Rendered", "REF502", "12,000.00", "Cr", "61,150.00"],
    ]

    create_statement_pdf(
        file_path=pdf_path,
        bank_name="ICICI BANK",
        account_holder="Pinnacle Tech",
        account_no="00120102931",
        headers=headers,
        col_x_positions=col_x,
        rows_data=rows,
        table_bordered=False,
    )

    pipeline = BankStatementPipeline()
    result = pipeline.process_document(pdf_path, "test_multiline_statement.pdf")

    assert result["has_data"] is True
    assert result["transactions_found"] == 2
    desc1 = result["transactions"][0]["description"]
    assert "Food Delivery Services" in desc1
    assert "Bangalore KA" in desc1

    desc2 = result["transactions"][1]["description"]
    assert "Invoice 2026-081" in desc2

    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_ocr_service_availability_and_preprocessing():
    """Validates that AdaptiveOCRService reports availability and executes OpenCV preprocessing."""
    from app.services.adaptive_ocr_service import AdaptiveOCRService
    import numpy as np

    assert AdaptiveOCRService.is_available() is True

    # Test OpenCV preprocessing on a synthetic test image
    dummy_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    # Draw some text-like dark pixels
    dummy_img[40:60, 20:80] = 0

    processed = AdaptiveOCRService.preprocess_image(dummy_img)
    assert processed is not None
    assert processed.shape[0] == 100
    assert processed.shape[1] == 100



def test_end_to_end_single_amount_dr_cr_pipeline():
    """Generates a statement with a single Amount column + Dr/Cr flag."""
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "test_single_amount_statement.pdf")

    headers = ["Date", "Narration", "Ref", "Amount", "Type", "Balance"]
    col_x = [50, 110, 260, 330, 400, 460]
    rows = [
        ["10/07/2026", "Customer Payment", "REF101", "10,000.00", "Cr", "60,000.00"],
        ["15/07/2026", "Vendor Payment", "REF102", "4,000.00", "Dr", "56,000.00"],
        ["22/07/2026", "Electricity Bill", "REF103", "1,500.00", "Dr", "54,500.00"],
    ]

    create_statement_pdf(
        file_path=pdf_path,
        bank_name="KOTAK MAHINDRA BANK",
        account_holder="Nexus Solutions",
        account_no="99120391203",
        headers=headers,
        col_x_positions=col_x,
        rows_data=rows,
        table_bordered=False,
    )

    pipeline = BankStatementPipeline()
    result = pipeline.process_document(pdf_path, "test_single_amount_statement.pdf")

    assert result["has_data"] is True
    assert result["transactions_found"] == 3
    assert result["total_credits"] == 10000.00
    assert result["total_debits"] == 5500.00
    assert result["closing_balance"] == 54500.00
    assert result["reconciliation"]["is_verified"] is True

    # Cleanup
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_end_to_end_descending_dates_normalized_to_ascending():
    """Validates that statements provided in descending date order are normalized to ascending."""
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "test_descending_statement.pdf")

    headers = ["Date", "Particulars", "Chq No", "Debit", "Credit", "Balance"]
    col_x = [50, 110, 260, 320, 390, 460]
    # Reverse chronological order
    rows = [
        ["28/06/2026", "Consulting Fee Receipt", "1109", "", "15,000.00", "85,300.00"],
        ["20/06/2026", "Broadband Internet Bill", "", "1,200.00", "", "70,300.00"],
        ["12/06/2026", "Office Stationery Store", "4412", "3,500.00", "", "71,500.00"],
        ["05/06/2026", "Client Inward NEFT", "981230", "", "25,000.00", "75,000.00"],
        ["01/06/2026", "Opening Balance b/f", "", "", "", "50,000.00"],
    ]

    create_statement_pdf(
        file_path=pdf_path,
        bank_name="AXIS BANK",
        account_holder="Sigma Enterprise",
        account_no="9120100293182",
        headers=headers,
        col_x_positions=col_x,
        rows_data=rows,
        table_bordered=True,
    )

    pipeline = BankStatementPipeline()
    result = pipeline.process_document(pdf_path, "test_descending_statement.pdf")

    assert result["has_data"] is True
    # Verify chronological ascending normalization
    txns = result["transactions"]
    assert txns[0]["date"] <= txns[-1]["date"]
    assert txns[0]["date"] == date(2026, 6, 5)
    assert txns[-1]["date"] == date(2026, 6, 28)

    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_end_to_end_multiline_narration_assembly():
    """Validates that multiline descriptions are properly merged across row breaks."""
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "test_multiline_statement.pdf")

    headers = ["Date", "Narration", "Ref", "Amount", "Type", "Balance"]
    col_x = [50, 110, 260, 330, 400, 460]
    # Narration with \n line breaks
    rows = [
        ["02/08/2026", "UPI/391028391/Merchant Payment\nFood Delivery Services\nBangalore KA", "REF501", "850.00", "Dr", "49,150.00"],
        ["08/08/2026", "NEFT Inward From Alpha\nInvoice 2026-081\nServices Rendered", "REF502", "12,000.00", "Cr", "61,150.00"],
    ]

    create_statement_pdf(
        file_path=pdf_path,
        bank_name="ICICI BANK",
        account_holder="Pinnacle Tech",
        account_no="00120102931",
        headers=headers,
        col_x_positions=col_x,
        rows_data=rows,
        table_bordered=False,
    )

    pipeline = BankStatementPipeline()
    result = pipeline.process_document(pdf_path, "test_multiline_statement.pdf")

    assert result["has_data"] is True
    assert result["transactions_found"] == 2
    desc1 = result["transactions"][0]["description"]
    assert "Food Delivery Services" in desc1
    assert "Bangalore KA" in desc1

    desc2 = result["transactions"][1]["description"]
    assert "Invoice 2026-081" in desc2

    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_ocr_service_availability_and_preprocessing():
    """Validates that AdaptiveOCRService reports availability and executes OpenCV preprocessing."""
    from app.services.adaptive_ocr_service import AdaptiveOCRService
    import numpy as np

    assert AdaptiveOCRService.is_available() is True

    # Test OpenCV preprocessing on a synthetic test image
    dummy_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    # Draw some text-like dark pixels
    dummy_img[40:60, 20:80] = 0

    processed = AdaptiveOCRService.preprocess_image(dummy_img)
    assert processed is not None
    assert processed.shape[0] == 100
    assert processed.shape[1] == 100

