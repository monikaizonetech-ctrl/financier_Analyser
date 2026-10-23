"""
Unit tests for parse_indian_bank_text_transactions.

These tests run against the actual Indian Bank statement PDF and verify:
  1.  03/06/25 credit 373,623.00  -> narration == '7364831226 /BRANCH : NILAGIRI'
  2.  12/11/25 debit  49,000.00   -> narration must NOT contain 'OWN DELINK'
  3.  11/06/25 credit 170,133.12  -> narration must NOT contain 'Deposit by SELF'
                                    and MUST contain 'ONE 97 COM'
  4.  Every row whose narration contains 'Txn Amt. X Charges. Y'
      must satisfy debit == X + Y  (or credit == X + Y for credit rows).
  5.  Zero-amount rows are not present in the output (OWN DELINK ... 0.00 dropped).
  6.  Total row count == 3268  (matches standalone stream-parser result).
"""

import os, re, sys
import pytest

# Allow running from repo root  (python -m pytest backend/tests/...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.pdf_extractor import extract_pdf_document, extract_document_metadata
from app.services.transaction_parser import parse_indian_bank_text_transactions

PDF_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "uploads",
    "7927a5ce-3d3c-4f45-a232-cb0a11dccc33",
    "7364831226.pdf",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def transactions():
    """Parse the real Indian Bank PDF once for all tests in this module."""
    if not os.path.exists(PDF_PATH):
        pytest.skip(f"PDF not found at {PDF_PATH}")
    doc = extract_pdf_document(PDF_PATH, max_pages=None)
    meta = extract_document_metadata(doc)
    # Force bank name so the dedicated parser is exercised even if extraction
    # fails to detect it from header lines during testing
    meta["bank_name"] = "INDIAN BANK"
    txns = parse_indian_bank_text_transactions(doc, "7364831226.pdf", meta)
    return txns


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _find(txns, *, amt, narr_contains=None):
    """Return all transactions matching a given amount (credit or debit)."""
    results = []
    for t in txns:
        cr = float(t.get("credit") or 0.0)
        dr = float(t.get("debit") or 0.0)
        if abs(max(cr, dr) - amt) < 0.01:
            if narr_contains is None or narr_contains in (t.get("description") or ""):
                results.append(t)
    return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIndianBankParser:

    def test_total_count(self, transactions):
        """Total valid transactions must equal 3268 (zero-amount rows dropped)."""
        assert len(transactions) == 3268, (
            f"Expected 3268 transactions, got {len(transactions)}"
        )

    def test_no_zero_amount_rows(self, transactions):
        """No transaction should have both credit and debit equal to 0."""
        zero_rows = [
            t for t in transactions
            if float(t.get("credit") or 0.0) == 0.0 and float(t.get("debit") or 0.0) == 0.0
        ]
        assert zero_rows == [], (
            f"Found {len(zero_rows)} zero-amount rows that should have been dropped"
        )

    def test_03jun25_narration_exact(self, transactions):
        """
        03/06/25 credit 373,623.00 -> narration must be exactly
        '7364831226 /BRANCH : NILAGIRI'
        """
        matches = _find(transactions, amt=373623.0)
        assert matches, "Transaction with credit=373,623.00 not found"
        desc = matches[0].get("description", "")
        assert desc == "7364831226 /BRANCH : NILAGIRI", (
            f"Expected exact narration '7364831226 /BRANCH : NILAGIRI', got {desc!r}"
        )

    def test_12nov25_no_own_delink(self, transactions):
        """
        12/11/25 debit 49,000.00 (INW_CLG...JAYA, ChqNo:416206)
        narration must NOT mention OWN DELINK.
        """
        matches = _find(transactions, amt=49000.0, narr_contains="416206")
        assert matches, "Transaction with debit=49,000.00 and ChqNo:416206 not found"
        desc = matches[0].get("description", "")
        assert "OWN DELINK" not in desc, (
            f"Narration must not contain 'OWN DELINK', got {desc!r}"
        )

    def test_11jun25_no_deposit_by_self_and_has_one97(self, transactions):
        """
        11/06/25 credit 170,133.12 (NEFT/YESB ... ONE 97 COM)
        narration must NOT contain 'Deposit by SELF'
        and MUST contain 'ONE 97 COM'.
        """
        matches = _find(transactions, amt=170133.12)
        assert matches, "Transaction with credit=170,133.12 not found"
        desc = matches[0].get("description", "")
        assert "Deposit by SELF" not in desc, (
            f"Narration must not contain 'Deposit by SELF', got {desc!r}"
        )
        assert "ONE 97 COM" in desc, (
            f"Narration must contain 'ONE 97 COM', got {desc!r}"
        )

    def test_txn_amt_charges_debit_equality(self, transactions):
        """
        Every row whose narration contains 'Txn Amt. X Charges. Y'
        must have debit (or credit) == X + Y.
        """
        pattern = re.compile(
            r"Txn\s*Amt\.?\s*([\d,]+\.\d{2})\s*Charges\.?\s*([\d,]+\.\d{2})",
            re.I,
        )
        failures = []
        checked = 0
        for t in transactions:
            desc = t.get("description") or ""
            m = pattern.search(desc)
            if not m:
                continue
            checked += 1
            x = float(m.group(1).replace(",", ""))
            y = float(m.group(2).replace(",", ""))
            expected = round(x + y, 2)
            actual = float(t.get("debit") or t.get("credit") or 0.0)
            if abs(actual - expected) > 0.02:
                failures.append(
                    f"amt={actual} expected={expected} ({x}+{y}) desc={desc[:80]}"
                )

        assert checked > 0, "No 'Txn Amt. ... Charges. ...' rows found -- pattern may have changed"
        assert failures == [], (
            f"{len(failures)} Txn-Amt+Charges rows failed equality:\n"
            + "\n".join(failures[:10])
        )

    def test_opening_and_closing_balance(self, transactions):
        """Opening balance must be 10,751,825.08 and closing balance must be 62,464.75."""
        stmt_opening = transactions[0].get("statement_opening_balance")
        assert stmt_opening is not None, "statement_opening_balance is missing on first transaction"
        assert round(stmt_opening, 2) == 10751825.08, (
            f"Expected Opening Balance 10,751,825.08, got {stmt_opening}"
        )
        last_bal = transactions[-1].get("balance")
        assert round(last_bal, 2) == 62464.75, (
            f"Expected Closing Balance 62,464.75, got {last_bal}"
        )

    def test_financial_summary_totals(self, transactions):
        """Total credit 160,981,757.49 (528 txns), total debit 171,671,117.82 (2,740 txns)."""
        cr_rows = [t for t in transactions if float(t.get("credit") or 0.0) > 0]
        dr_rows = [t for t in transactions if float(t.get("debit") or 0.0) > 0]
        total_cr = round(sum(float(t.get("credit") or 0.0) for t in cr_rows), 2)
        total_dr = round(sum(float(t.get("debit") or 0.0) for t in dr_rows), 2)
        net_cf = round(total_cr - total_dr, 2)
        balances = [t["balance"] for t in transactions if t.get("balance") is not None]

        assert len(cr_rows) == 528, f"Expected 528 credit transactions, got {len(cr_rows)}"
        assert len(dr_rows) == 2740, f"Expected 2740 debit transactions, got {len(dr_rows)}"
        assert total_cr == 160981757.49, f"Expected Total Credit 160,981,757.49, got {total_cr}"
        assert total_dr == 171671117.82, f"Expected Total Debit 171,671,117.82, got {total_dr}"
        assert net_cf == -10689360.33, f"Expected Net Cash Flow -10,689,360.33, got {net_cf}"
        assert round(min(balances), 2) == 60843.75, f"Expected Min Balance 60,843.75, got {min(balances)}"
        assert round(max(balances), 2) == 12052774.63, f"Expected Max Balance 12,052,774.63, got {max(balances)}"

    def test_first_transaction_credit_classification(self, transactions):
        """First transaction (01/06/25, RTGS from ONE 97, 485,054.99) must be classified as CREDIT with balance 11,236,880.07."""
        t0 = transactions[0]
        assert float(t0.get("credit") or 0.0) == 485054.99, (
            f"Expected first transaction credit 485,054.99, got {t0.get('credit')}"
        )
        assert t0.get("debit") is None or float(t0.get("debit") or 0.0) == 0.0, (
            f"First transaction must not be debit, got {t0.get('debit')}"
        )
        assert round(t0["balance"], 2) == 11236880.07, (
            f"Expected first transaction balance 11,236,880.07, got {t0['balance']}"
        )
        assert "ONE 97" in (t0.get("description") or ""), (
            f"First transaction narration must mention ONE 97, got {t0.get('description')}"
        )

    def test_june_2025_monthly_cashflow(self, transactions):
        """Jun 2025: credit 27,134,905.20 (84 txns), debit 34,110,217.63 (290 txns)."""
        jun_txns = [
            t for t in transactions
            if (t.get("date") and str(t["date"]).startswith("2025-06"))
            or (t.get("date") and getattr(t["date"], "month", None) == 6 and getattr(t["date"], "year", None) == 2025)
        ]
        jun_cr = [t for t in jun_txns if float(t.get("credit") or 0.0) > 0]
        jun_dr = [t for t in jun_txns if float(t.get("debit") or 0.0) > 0]
        jun_cr_total = round(sum(float(t.get("credit") or 0.0) for t in jun_cr), 2)
        jun_dr_total = round(sum(float(t.get("debit") or 0.0) for t in jun_dr), 2)

        assert len(jun_cr) == 84, f"Expected 84 credit txns in Jun 2025, got {len(jun_cr)}"
        assert jun_cr_total == 27134905.20, f"Expected Jun 2025 credit 27,134,905.20, got {jun_cr_total}"
        assert len(jun_dr) == 290, f"Expected 290 debit txns in Jun 2025, got {len(jun_dr)}"
        assert jun_dr_total == 34110217.63, f"Expected Jun 2025 debit 34,110,217.63, got {jun_dr_total}"

    def test_top_transactions(self, transactions):
        """Top debits: 3,581,015.00 (26-Feb-2026), 2,672,068.00 (30-Jul-2025). Top credit: 2,656,261.00 (30-Oct-2025)."""
        debits = sorted(
            [t for t in transactions if float(t.get("debit") or 0.0) > 0],
            key=lambda t: -float(t.get("debit") or 0.0)
        )
        credits = sorted(
            [t for t in transactions if float(t.get("credit") or 0.0) > 0],
            key=lambda t: -float(t.get("credit") or 0.0)
        )
        assert round(float(debits[0]["debit"]), 2) == 3581015.00, f"Top debit 1 mismatch: {debits[0]}"
        assert str(debits[0]["date"]) == "2026-02-26"
        assert round(float(debits[1]["debit"]), 2) == 2672068.00, f"Top debit 2 mismatch: {debits[1]}"
        assert str(debits[1]["date"]) == "2025-07-30"

        assert round(float(credits[0]["credit"]), 2) == 2656261.00, f"Top credit 1 mismatch: {credits[0]}"
        assert str(credits[0]["date"]) == "2025-10-30"

    def test_validation_gate_all_checks_pass(self, transactions):
        """All 7 validation gate checks (a through g) must PASS."""
        from app.services.file_analysis_service import _build_analytics
        analytics = _build_analytics(
            [{
                "transactions": transactions,
                "opening_balance": 10751825.08,
                "closing_balance": 62464.75,
                "statement_summary": {
                    "total_credit": 160981757.49,
                    "total_debit": 171671117.82,
                    "cr_count": 528,
                    "dr_count": 2740,
                },
                "statement_period": "01-06-2025 to 20-08-2026",
            }],
            account_holder="TEST HOLDER",
        )
        assert analytics["is_integrity_verified"] is True
        assert analytics["validation_status"] == "VALID"
        assert len(analytics["validation_reasons"]) == 0
        for chk in analytics["reconciliation_checks"]:
            assert chk["status"] == "PASS", f"Check failed: {chk}"

