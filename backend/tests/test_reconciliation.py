"""
Comprehensive test suite for Phase 5: Financial Validation and Reconciliation
"""
from datetime import date
import unittest

from app.services.reconciliation_service import (
    ValidationStatus,
    DiscrepancyType,
    reconcile_transactions,
)


class TestFinancialReconciliation(unittest.TestCase):

    def test_01_valid_clean_statement(self):
        """Verify that a mathematically consistent statement produces VALID status."""
        rows = [
            {"date": date(2026, 8, 1), "description": "Opening Balance", "debit": 0.0, "credit": 0.0, "balance": 50000.0},
            {"date": date(2026, 8, 2), "description": "Salary Credit", "debit": 0.0, "credit": 30000.0, "balance": 80000.0},
            {"date": date(2026, 8, 3), "description": "Rent Payment", "debit": 15000.0, "credit": 0.0, "balance": 65000.0},
            {"date": date(2026, 8, 4), "description": "Grocery Store", "debit": 5000.0, "credit": 0.0, "balance": 60000.0},
        ]
        report = reconcile_transactions(rows, opening_balance=50000.0, extracted_closing_balance=60000.0)

        self.assertEqual(report.status, ValidationStatus.VALID)
        self.assertEqual(report.opening_balance, 50000.0)
        self.assertEqual(report.total_income, 30000.0)
        self.assertEqual(report.total_expense, 20000.0)
        self.assertEqual(report.net_cash_flow, 10000.0)
        self.assertEqual(report.expected_closing_balance, 60000.0)
        self.assertEqual(report.extracted_closing_balance, 60000.0)
        self.assertEqual(report.discrepancy_count, 0)

    def test_02_missing_transaction_detection(self):
        """
        Verify that an unaccounted gap between running balances
        is detected as POSSIBLE_MISSING_TRANSACTION.
        """
        rows = [
            {"date": date(2026, 8, 1), "description": "Opening Balance", "debit": 0.0, "credit": 0.0, "balance": 50000.0},
            {"date": date(2026, 8, 2), "description": "Salary Credit", "debit": 0.0, "credit": 20000.0, "balance": 70000.0},
            # Gap: A 10,000 withdrawal is missing here, so next row starts with balance 58000 instead of 68000
            {"date": date(2026, 8, 5), "description": "Electricity Bill", "debit": 2000.0, "credit": 0.0, "balance": 58000.0, "source_page": 2, "raw_text": "05/08/2026 Electricity Bill 2000.00 58000.00"},
        ]
        report = reconcile_transactions(rows, opening_balance=50000.0, extracted_closing_balance=58000.0)

        self.assertIn(report.status, (ValidationStatus.SUSPICIOUS, ValidationStatus.ERROR))
        types = [d.type for d in report.discrepancies]
        self.assertIn(DiscrepancyType.POSSIBLE_MISSING_TRANSACTION, types)

        # Verify source information was preserved for auditing
        missing_disc = next(d for d in report.discrepancies if d.type == DiscrepancyType.POSSIBLE_MISSING_TRANSACTION)
        self.assertEqual(missing_disc.source_page, 2)
        self.assertIn("Electricity Bill", missing_disc.raw_text)
        self.assertEqual(missing_disc.difference, -10000.0)

    def test_03_inverted_debit_credit_detection(self):
        """
        Verify that when a debit transaction was misclassified as credit
        (or vice versa), the engine diagnoses POSSIBLE_INVERTED_DEBIT_CREDIT.
        """
        rows = [
            {"date": date(2026, 8, 1), "description": "Opening", "debit": 0.0, "credit": 0.0, "balance": 50000.0},
            # ATM Withdrawal was mistakenly placed in Credit column!
            # Math: 50,000 - 5,000 = 45,000. But row has Credit=5,000, Balance=45,000
            {"date": date(2026, 8, 2), "description": "ATM Withdrawal", "debit": 0.0, "credit": 5000.0, "balance": 45000.0, "source_page": 1, "raw_text": "02/08/2026 ATM Withdrawal - 5000.00 45000.00"},
        ]
        report = reconcile_transactions(rows, opening_balance=50000.0)

        types = [d.type for d in report.discrepancies]
        self.assertIn(DiscrepancyType.POSSIBLE_INVERTED_DEBIT_CREDIT, types)
        disc = next(d for d in report.discrepancies if d.type == DiscrepancyType.POSSIBLE_INVERTED_DEBIT_CREDIT)
        self.assertEqual(disc.severity, ValidationStatus.SUSPICIOUS)
        self.assertIn("inverted debit/credit", disc.message.lower())

    def test_04_duplicate_transaction_detection(self):
        """
        Verify that identical repeated rows without running balance movement
        are flagged as POSSIBLE_DUPLICATE_TRANSACTION.
        """
        rows = [
            {"date": date(2026, 8, 1), "description": "Vendor Payment", "debit": 2500.0, "credit": 0.0, "balance": 47500.0, "source_page": 1, "raw_text": "Row 1"},
            # Duplicate row: identical date, description, amount, and same balance (did not change)
            {"date": date(2026, 8, 1), "description": "Vendor Payment", "debit": 2500.0, "credit": 0.0, "balance": 47500.0, "source_page": 1, "raw_text": "Row 2 duplicate"},
        ]
        report = reconcile_transactions(rows, opening_balance=50000.0)

        types = [d.type for d in report.discrepancies]
        self.assertIn(DiscrepancyType.POSSIBLE_DUPLICATE_TRANSACTION, types)
        disc = next(d for d in report.discrepancies if d.type == DiscrepancyType.POSSIBLE_DUPLICATE_TRANSACTION)
        self.assertEqual(disc.severity, ValidationStatus.WARNING)
        self.assertIn("duplicate", disc.message.lower())

    def test_05_header_footer_leak_detection(self):
        """Verify that summary phrases ('Page Total', 'B/F') parsed as transactions are flagged."""
        rows = [
            {"date": date(2026, 8, 1), "description": "Page Total", "debit": 0.0, "credit": 0.0, "balance": 50000.0, "source_page": 1, "raw_text": "Page Total 50,000.00"},
            {"date": date(2026, 8, 2), "description": "Salary", "debit": 0.0, "credit": 20000.0, "balance": 70000.0, "source_page": 1, "raw_text": "Salary 20000.00 70000.00"},
        ]
        report = reconcile_transactions(rows, opening_balance=50000.0, extracted_closing_balance=70000.0)

        types = [d.type for d in report.discrepancies]
        self.assertIn(DiscrepancyType.SUSPICIOUS_HEADER_FOOTER_ENTRY, types)

    def test_06_closing_balance_mismatch_detection(self):
        """
        Verify that when Expected Closing != Extracted Closing,
        CLOSING_BALANCE_MISMATCH is flagged with ERROR severity.
        """
        rows = [
            {"date": date(2026, 8, 1), "description": "Salary", "debit": 0.0, "credit": 10000.0, "balance": 60000.0},
        ]
        # Statement claimed closing balance was 95,000 instead of expected 60,000
        report = reconcile_transactions(rows, opening_balance=50000.0, extracted_closing_balance=95000.0)

        self.assertEqual(report.status, ValidationStatus.ERROR)
        types = [d.type for d in report.discrepancies]
        self.assertIn(DiscrepancyType.CLOSING_BALANCE_MISMATCH, types)
        disc = next(d for d in report.discrepancies if d.type == DiscrepancyType.CLOSING_BALANCE_MISMATCH)
        self.assertEqual(disc.difference, 35000.0)


if __name__ == "__main__":
    unittest.main()
