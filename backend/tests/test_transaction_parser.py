"""
Comprehensive test suite for Phase 3: Intelligent Transaction Extraction
"""
from datetime import date
import unittest

from app.services.transaction_parser import (
    ColumnRole,
    CanonicalTransaction,
    identify_column_roles,
    parse_date,
    clean_amount_str,
    parse_table_transactions,
    parse_spatial_line_transactions,
)
from app.services.pdf_extractor import (
    ExtractedPage,
    ExtractedLine,
    ExtractedWord,
    LineType,
)


class TestIntelligentTransactionParser(unittest.TestCase):

    def test_01_date_parsing_variations(self):
        """Verify parsing of multiple date formats."""
        self.assertEqual(parse_date("01/08/2026"), date(2026, 8, 1))
        self.assertEqual(parse_date("01-08-2026"), date(2026, 8, 1))
        self.assertEqual(parse_date("01.08.2026"), date(2026, 8, 1))
        self.assertEqual(parse_date("2026-08-01"), date(2026, 8, 1))
        self.assertEqual(parse_date("01-Aug-2026"), date(2026, 8, 1))
        self.assertEqual(parse_date("01 Aug 2026"), date(2026, 8, 1))
        self.assertEqual(parse_date("01-Aug-26"), date(2026, 8, 1))
        self.assertIsNone(parse_date("Not A Date"))
        self.assertIsNone(parse_date("-"))

    def test_02_amount_cleaning_and_disambiguation(self):
        """Verify amounts are cleaned while avoiding phone numbers and account numbers."""
        # Standard decimal amounts
        amt, ind = clean_amount_str("25,000.00")
        self.assertEqual(amt, 25000.00)
        self.assertIsNone(ind)

        # Currency symbols
        amt, ind = clean_amount_str("₹ 1,250.50")
        self.assertEqual(amt, 1250.50)

        # Dr / Cr indicators
        amt, ind = clean_amount_str("5,000.00 Dr")
        self.assertEqual(amt, 5000.00)
        self.assertEqual(ind, "DR")

        amt, ind = clean_amount_str("12,300.00 Cr")
        self.assertEqual(amt, 12300.00)
        self.assertEqual(ind, "CR")

        # Accounting negative parentheses
        amt, ind = clean_amount_str("(450.00)")
        self.assertEqual(amt, 450.00)
        self.assertEqual(ind, "DR")

        # Disambiguate: Long phone or account number (10+ digits without decimal)
        amt, ind = clean_amount_str("9876543210")
        self.assertEqual(amt, 0.0)

    def test_03_column_order_identification(self):
        """Verify column roles can be identified regardless of column ordering."""
        # Standard: Date, Description, Debit, Credit, Balance
        h1 = ["Date", "Narration", "Chq No", "Debit", "Credit", "Balance"]
        roles1 = identify_column_roles(h1)
        self.assertEqual(roles1[ColumnRole.DATE], 0)
        self.assertEqual(roles1[ColumnRole.DESCRIPTION], 1)
        self.assertEqual(roles1[ColumnRole.REFERENCE], 2)
        self.assertEqual(roles1[ColumnRole.DEBIT], 3)
        self.assertEqual(roles1[ColumnRole.CREDIT], 4)
        self.assertEqual(roles1[ColumnRole.BALANCE], 5)

        # Reversed order: Deposit before Withdrawal
        h2 = ["Txn Date", "Particulars", "Deposits", "Withdrawals", "Closing Balance"]
        roles2 = identify_column_roles(h2)
        self.assertEqual(roles2[ColumnRole.DATE], 0)
        self.assertEqual(roles2[ColumnRole.DESCRIPTION], 1)
        self.assertEqual(roles2[ColumnRole.CREDIT], 2)
        self.assertEqual(roles2[ColumnRole.DEBIT], 3)
        self.assertEqual(roles2[ColumnRole.BALANCE], 4)

        # Single Amount column with Dr/Cr type
        h3 = ["Transaction Date", "Details", "Amount", "Type", "Available Balance"]
        roles3 = identify_column_roles(h3)
        self.assertEqual(roles3[ColumnRole.DATE], 0)
        self.assertEqual(roles3[ColumnRole.DESCRIPTION], 1)
        self.assertEqual(roles3[ColumnRole.AMOUNT], 2)
        self.assertEqual(roles3[ColumnRole.TXN_TYPE], 3)
        self.assertEqual(roles3[ColumnRole.BALANCE], 4)

    def test_04_multi_line_transaction_stitching(self):
        """Verify that multi-line transaction rows are stitched without creating duplicates."""
        # Simulated table where row 1 has date + description part 1
        # row 2 has description part 2 + delayed amounts
        # row 3 is another transaction
        table = [
            ["Date", "Description", "Ref No", "Debit", "Credit", "Balance"],
            ["01/08/2026", "NEFT/ABC COMPANY PVT LTD", "", "", "", ""],
            ["", "INVOICE #98725 MUMBAI", "NEFT-7841", "25,000.00", "", "85,000.00"],
            ["02/08/2026", "Salary Credit", "SAL-01", "", "40,000.00", "1,25,000.00"],
        ]
        txns = parse_table_transactions(table, page_num=1, file_name="test.pdf")

        # Exactly 2 transactions should be produced, NOT 3
        self.assertEqual(len(txns), 2)

        # First transaction should contain stitched narration and correct amounts
        t1 = txns[0]
        self.assertEqual(t1.date, date(2026, 8, 1))
        self.assertIn("NEFT/ABC COMPANY PVT LTD", t1.description)
        self.assertIn("INVOICE #98725 MUMBAI", t1.description)
        self.assertEqual(t1.reference, "NEFT-7841")
        self.assertEqual(t1.debit, 25000.00)
        self.assertEqual(t1.credit, 0.0)
        self.assertEqual(t1.balance, 85000.00)

        # Second transaction
        t2 = txns[1]
        self.assertEqual(t2.date, date(2026, 8, 2))
        self.assertEqual(t2.credit, 40000.00)
        self.assertEqual(t2.balance, 125000.00)

    def test_05_single_amount_column_with_drcr(self):
        """Verify handling of single Amount column with Dr/Cr indicator."""
        table = [
            ["Date", "Particulars", "Amount", "Type", "Balance"],
            ["10-08-2026", "Vendor Payment", "15,000.00", "DR", "70,000.00"],
            ["12-08-2026", "Customer Deposit", "20,000.00", "CR", "90,000.00"],
        ]
        txns = parse_table_transactions(table, page_num=1, file_name="single_amt.pdf")
        self.assertEqual(len(txns), 2)

        self.assertEqual(txns[0].debit, 15000.00)
        self.assertEqual(txns[0].credit, 0.0)

        self.assertEqual(txns[1].debit, 0.0)
        self.assertEqual(txns[1].credit, 20000.00)

    def test_06_filter_summary_and_noise_rows(self):
        """Verify sub-totals, brought forward, and carried forward are not treated as transactions."""
        table = [
            ["Date", "Particulars", "Debit", "Credit", "Balance"],
            ["", "B/F", "-", "-", "50,000.00"],
            ["15-08-2026", "UPI Transfer", "500.00", "-", "49,500.00"],
            ["", "Total", "500.00", "-", "49,500.00"],
            ["", "End of Statement", "", "", ""],
        ]
        txns = parse_table_transactions(table, page_num=1, file_name="summary.pdf")
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].description, "UPI Transfer")
        self.assertEqual(txns[0].debit, 500.00)

    def test_07_spatial_line_borderless_extraction(self):
        """Verify borderless line extraction with multi-line narration and amounts."""
        page = ExtractedPage(
            page_number=1,
            width=595.0,
            height=842.0,
            raw_text="Borderless test",
            character_count=50,
            header_lines=[
                ExtractedLine(
                    line_number=1,
                    text="Date Description Debit Credit Balance",
                    y_top=50.0,
                    y_bottom=60.0,
                    line_type=LineType.COLUMN_HEADER,
                )
            ],
            transaction_lines=[
                ExtractedLine(
                    line_number=2,
                    text="01/08/2026 NEFT/XYZ ENTERPRISES",
                    y_top=100.0,
                    y_bottom=110.0,
                    line_type=LineType.TRANSACTION_CANDIDATE,
                ),
                ExtractedLine(
                    line_number=3,
                    text="INVOICE 123 25,000.00 75,000.00",
                    y_top=112.0,
                    y_bottom=122.0,
                    line_type=LineType.TRANSACTION_CANDIDATE,
                ),
                ExtractedLine(
                    line_number=4,
                    text="05/08/2026 ATM Cash Withdrawal 5,000.00 70,000.00",
                    y_top=140.0,
                    y_bottom=150.0,
                    line_type=LineType.TRANSACTION_CANDIDATE,
                ),
            ],
        )
        txns = parse_spatial_line_transactions(page, file_name="borderless.pdf")
        self.assertEqual(len(txns), 2)

        # First txn stitched across lines 2 and 3
        t1 = txns[0]
        self.assertEqual(t1.date, date(2026, 8, 1))
        self.assertIn("NEFT/XYZ ENTERPRISES", t1.description)
        self.assertIn("INVOICE 123", t1.description)
        self.assertEqual(t1.debit, 25000.00)
        self.assertEqual(t1.balance, 75000.00)

        # Second txn
        t2 = txns[1]
        self.assertEqual(t2.date, date(2026, 8, 5))
        self.assertEqual(t2.debit, 5000.00)
        self.assertEqual(t2.balance, 70000.00)


if __name__ == "__main__":
    unittest.main()
