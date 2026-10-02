"""
Comprehensive test suite for Phase 4: Correct Income and Expense Classification
"""
from datetime import date
import unittest

from app.services.transaction_parser import (
    TransactionType,
    classify_transaction_direction,
    parse_table_transactions,
)
from app.services.file_analysis_service import analyse_bank_statement, _enrich_transactions


class TestIncomeExpenseClassification(unittest.TestCase):

    def test_01_unambiguous_credit_is_income(self):
        """Verify credit/deposit is classified strictly as INCOME."""
        t_type, dr, cr, is_unc, _ = classify_transaction_direction(debit=0.0, credit=15000.0)
        self.assertEqual(t_type, TransactionType.INCOME)
        self.assertEqual(cr, 15000.0)
        self.assertEqual(dr, 0.0)
        self.assertFalse(is_unc)

    def test_02_unambiguous_debit_is_expense(self):
        """Verify debit/withdrawal is classified strictly as EXPENSE."""
        t_type, dr, cr, is_unc, _ = classify_transaction_direction(debit=2400.0, credit=0.0)
        self.assertEqual(t_type, TransactionType.EXPENSE)
        self.assertEqual(dr, 2400.0)
        self.assertEqual(cr, 0.0)
        self.assertFalse(is_unc)

    def test_03_narration_keyword_independence(self):
        """
        Verify that narration keywords DO NOT determine direction.
        A 'Salary' payment in debit must be EXPENSE.
        A 'Payment Received' in credit must be INCOME.
        """
        table = [
            ["Date", "Description", "Debit", "Credit", "Balance"],
            # Debit with "Salary" narration -> EXPENSE!
            ["01/08/2026", "Salary to Staff Suresh", "25,000.00", "-", "75,000.00"],
            # Credit with "Payment" narration -> INCOME!
            ["02/08/2026", "Payment from Client ABC", "-", "50,000.00", "1,25,000.00"],
            # Debit with "UPI" narration -> EXPENSE!
            ["03/08/2026", "UPI Transfer to Vendor", "1,500.00", "-", "1,23,500.00"],
            # Credit with "UPI" narration -> INCOME!
            ["04/08/2026", "UPI Cashback Refund", "-", "200.00", "1,23,700.00"],
            # Debit with "Cash" narration -> EXPENSE!
            ["05/08/2026", "Cash Withdrawal ATM", "5,000.00", "-", "1,18,700.00"],
            # Credit with "Cash" narration -> INCOME!
            ["06/08/2026", "Cash Deposit CDM", "-", "10,000.00", "1,28,700.00"],
        ]
        txns = parse_table_transactions(table, page_num=1, file_name="keyword_test.pdf")
        self.assertEqual(len(txns), 6)

        # 1. Salary in Debit -> EXPENSE
        self.assertEqual(txns[0].transaction_type, TransactionType.EXPENSE)
        self.assertEqual(txns[0].debit, 25000.00)
        self.assertEqual(txns[0].credit, 0.0)

        # 2. Payment in Credit -> INCOME
        self.assertEqual(txns[1].transaction_type, TransactionType.INCOME)
        self.assertEqual(txns[1].credit, 50000.00)

        # 3. UPI in Debit -> EXPENSE
        self.assertEqual(txns[2].transaction_type, TransactionType.EXPENSE)

        # 4. UPI in Credit -> INCOME
        self.assertEqual(txns[3].transaction_type, TransactionType.INCOME)

        # 5. Cash in Debit -> EXPENSE
        self.assertEqual(txns[4].transaction_type, TransactionType.EXPENSE)

        # 6. Cash in Credit -> INCOME
        self.assertEqual(txns[5].transaction_type, TransactionType.INCOME)

    def test_04_cr_dr_single_amount_column(self):
        """Verify explicit CR / DR indicators determine INCOME / EXPENSE."""
        t_type1, dr1, cr1, _, _ = classify_transaction_direction(debit=0.0, credit=0.0, indicator="CR")
        # With amount in debit parameter
        t_type2, dr2, cr2, _, _ = classify_transaction_direction(debit=7500.0, credit=0.0, indicator="CR")
        self.assertEqual(t_type2, TransactionType.INCOME)
        self.assertEqual(cr2, 7500.0)
        self.assertEqual(dr2, 0.0)

        t_type3, dr3, cr3, _, _ = classify_transaction_direction(debit=0.0, credit=3200.0, indicator="DR")
        self.assertEqual(t_type3, TransactionType.EXPENSE)
        self.assertEqual(dr3, 3200.0)
        self.assertEqual(cr3, 0.0)

    def test_05_negative_amount_formats(self):
        """Verify negative numbers or parentheses resolve to EXPENSE."""
        table = [
            ["Date", "Particulars", "Amount", "Balance"],
            ["10/08/2026", "Office Supplies", "(1,250.00)", "48,750.00"],
            ["11/08/2026", "Consulting Fee", "10,000.00", "58,750.00"],
        ]
        txns = parse_table_transactions(table, page_num=1, file_name="neg_test.pdf")
        self.assertEqual(len(txns), 2)
        # (1,250.00) -> EXPENSE
        self.assertEqual(txns[0].transaction_type, TransactionType.EXPENSE)
        self.assertEqual(txns[0].debit, 1250.00)
        self.assertEqual(txns[0].credit, 0.0)

        # 10,000.00 -> INCOME
        self.assertEqual(txns[1].transaction_type, TransactionType.INCOME)
        self.assertEqual(txns[1].credit, 10000.00)

    def test_06_balance_delta_resolution(self):
        """Verify empty debit/credit rows are resolved via running balance delta."""
        # Balance increased from 50000 to 55000 -> INCOME of 5000
        t_type1, dr1, cr1, is_unc1, reason1 = classify_transaction_direction(
            debit=0.0, credit=0.0, current_balance=55000.0, previous_balance=50000.0
        )
        self.assertEqual(t_type1, TransactionType.INCOME)
        self.assertEqual(cr1, 5000.0)
        self.assertEqual(dr1, 0.0)
        self.assertFalse(is_unc1)

        # Balance decreased from 55000 to 52000 -> EXPENSE of 3000
        t_type2, dr2, cr2, is_unc2, reason2 = classify_transaction_direction(
            debit=0.0, credit=0.0, current_balance=52000.0, previous_balance=55000.0
        )
        self.assertEqual(t_type2, TransactionType.EXPENSE)
        self.assertEqual(dr2, 3000.0)
        self.assertEqual(cr2, 0.0)
        self.assertFalse(is_unc2)

    def test_07_unresolvable_is_marked_uncertain(self):
        """Verify unresolvable zero-amount transactions are flagged as UNCERTAIN without guessing."""
        t_type, dr, cr, is_unc, reason = classify_transaction_direction(
            debit=0.0, credit=0.0, current_balance=None, previous_balance=None
        )
        self.assertEqual(t_type, TransactionType.UNCERTAIN)
        self.assertTrue(is_unc)
        self.assertIn("Zero debit and credit", reason)

    def test_08_enrich_transactions_normalization(self):
        """Verify _enrich_transactions normalizes transaction_type across all rows."""
        rows = [
            {"date": date(2026, 8, 1), "description": "Salary", "debit": 0.0, "credit": 35000.0, "balance": 35000.0},
            {"date": date(2026, 8, 2), "description": "Rent", "debit": 12000.0, "credit": 0.0, "balance": 23000.0},
            {"date": date(2026, 8, 3), "description": "Note", "debit": 0.0, "credit": 0.0, "balance": 23000.0},
        ]
        enriched = _enrich_transactions(rows)
        self.assertEqual(enriched[0]["transaction_type"], "INCOME")
        self.assertEqual(enriched[1]["transaction_type"], "EXPENSE")
        self.assertEqual(enriched[2]["transaction_type"], "UNCERTAIN")


if __name__ == "__main__":
    unittest.main()
