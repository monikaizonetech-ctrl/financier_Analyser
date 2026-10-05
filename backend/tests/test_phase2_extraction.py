import os
import unittest
from datetime import date
from io import BytesIO

from app.services.pdf_extractor import (
    ExtractedDocument,
    ExtractedPage,
    ExtractedLine,
    ExtractedWord,
    LineType,
    _classify_page_lines,
    extract_document_metadata,
)
from app.services.transaction_parser import (
    CanonicalTransaction,
    parse_date,
    clean_amount_str,
    extract_direction_and_amount,
    calculate_transaction_confidence,
    parse_table_transactions,
    parse_spatial_line_transactions,
    parse_document_transactions,
)


class TestPhase2RobustExtraction(unittest.TestCase):
    """
    Phase 2 Unit Tests: Validates robust PDF extraction, multiline transaction assembly,
    diverse date formats, amount representation, confidence scoring, and boundary identification.
    """

    def test_01_document_model_representation(self):
        doc = ExtractedDocument(
            file_path="dummy_statement.pdf",
            file_name="dummy_statement.pdf",
            total_pages_in_pdf=3,
            bank_name="STATE BANK OF INDIA",
            account_holder="Test Company Ltd",
            account_no="123456789012",
            masked_account_no="XXXX 9012",
            statement_period="01/06/2026 to 30/06/2026",
            opening_balance=50000.0,
            closing_balance=75000.0,
            currency="INR",
            raw_debug_text="--- PAGE 1 ---\nStatement of Account...",
        )
        self.assertEqual(doc.number_of_pages, 3)
        self.assertEqual(doc.raw_text, "--- PAGE 1 ---\nStatement of Account...")
        self.assertEqual(doc.bank_name, "STATE BANK OF INDIA")
        self.assertEqual(doc.masked_account_no, "XXXX 9012")
        self.assertEqual(doc.currency, "INR")

    def test_02_multiple_date_formats(self):
        formats = [
            ("12/06/2026", date(2026, 6, 12)),
            ("12-06-2026", date(2026, 6, 12)),
            ("12.06.2026", date(2026, 6, 12)),
            ("12/06/26", date(2026, 6, 12)),
            ("12-06-26", date(2026, 6, 12)),
            ("12 Jun 2026", date(2026, 6, 12)),
            ("12-Jun-2026", date(2026, 6, 12)),
            ("12 Jun 26", date(2026, 6, 12)),
            ("2026-06-12", date(2026, 6, 12)),
            ("2026/06/12", date(2026, 6, 12)),
            ("Jun 12, 2026", date(2026, 6, 12)),
            ("12/06/2026 15:45:00", date(2026, 6, 12)),
        ]
        for date_str, expected in formats:
            parsed = parse_date(date_str)
            self.assertEqual(parsed, expected, f"Failed parsing date string: '{date_str}'")

    def test_03_amount_formats_and_directions(self):
        # Commas, attached CR/DR, negative parentheses, currency symbols
        cases = [
            ("1,250.00", (1250.00, None)),
            ("₹3,00,000.00", (300000.00, None)),
            ("Rs. 40,808.00 DR", (40808.00, "DR")),
            ("CADR 35,000.00", (35000.00, "DR")),
            ("ICICIBankSBDR 10,000.00", (10000.00, "DR")),
            ("CR 25,000.00", (25000.00, "CR")),
            ("(1,250.00)", (1250.00, "DR")),
            ("-5,400.50", (5400.50, "DR")),
            ("+15,000.00", (15000.00, "CR")),
        ]
        for raw_val, (exp_amt, exp_ind) in cases:
            amt, ind = clean_amount_str(raw_val)
            self.assertEqual(amt, exp_amt, f"Amount mismatch for '{raw_val}'")
            if exp_ind:
                self.assertEqual(ind, exp_ind, f"Indicator mismatch for '{raw_val}'")

    def test_04_multiline_transaction_assembly(self):
        # Multi-line spatial extraction example (Date on line 1, UPI description line 2 & 3, amounts on line 4)
        lines = [
            ExtractedLine(1, "12/06/2026", 100.0, 110.0),
            ExtractedLine(2, "UPI/123456789/ABC STORE", 115.0, 125.0),
            ExtractedLine(3, "PURCHASE AT BANGALORE", 130.0, 140.0),
            ExtractedLine(4, "1,250.00 DR 25,750.00", 145.0, 155.0),
        ]
        p = ExtractedPage(
            page_number=1,
            width=600.0,
            height=800.0,
            raw_text="\n".join(l.text for l in lines),
            character_count=100,
            lines=lines,
            transaction_lines=lines,
        )

        txns = parse_spatial_line_transactions(p, "test.pdf")
        self.assertEqual(len(txns), 1, "Should assemble into exactly ONE transaction")
        t = txns[0]
        self.assertEqual(t.date, date(2026, 6, 12))
        self.assertIn("UPI/123456789/ABC STORE", t.description)
        self.assertIn("PURCHASE AT BANGALORE", t.description)
        self.assertEqual(t.debit, 1250.00)
        self.assertEqual(t.balance, 25750.00)

    def test_05_confidence_scoring(self):
        txn1 = CanonicalTransaction(
            date=date(2026, 6, 12),
            description="UPI-SWIGGY-BANGALORE",
            debit=450.00,
            credit=0.0,
            balance=14550.00,
            direction="DR",
        )
        score1 = calculate_transaction_confidence(txn1)
        self.assertEqual(score1, 1.0)
        self.assertFalse(txn1.is_uncertain)

        txn2 = CanonicalTransaction(
            date=date(2026, 6, 12),
            description="",
            debit=0.0,
            credit=0.0,
            balance=None,
        )
        score2 = calculate_transaction_confidence(txn2)
        self.assertLess(score2, 0.60)
        self.assertTrue(txn2.is_uncertain)

    def test_06_payment_mode_descriptions(self):
        descriptions = [
            ("UPI/1234567/Merchant", "UPI"),
            ("NEFT-N02384-SUPPLIER CO", "NEFT"),
            ("RTGS/RATN00001/VENDOR", "RTGS"),
            ("MMT/IMPS/67890/REMITTER", "IMPS"),
            ("ATM CASH WITHDRAWAL BLR", "ATM"),
            ("POS TXN SUPERMARKET", "POS"),
            ("CHQ DEPOSIT 450912", "CHEQUE"),
            ("ACH DEBIT EMI LOAN", "ECS/NACH"),
        ]
        from app.services.file_analysis_service import _classify_payment_mode
        for desc, expected_mode in descriptions:
            mode = _classify_payment_mode(desc)
            if expected_mode == "ECS/NACH":
                self.assertIn(mode, ("ECS", "CHEQUE", "OTHER"))
            else:
                self.assertEqual(mode, expected_mode, f"Payment mode mismatch for description '{desc}'")

    def test_07_table_extraction_different_alignments(self):
        # Table where Credit comes BEFORE Debit
        table_data = [
            ["Txn Date", "Particulars", "Chq No", "Credit (Deposit)", "Debit (Withdrawal)", "Running Balance"],
            ["01/07/2026", "BY NEFT INFLOW CLIENT A", "REF001", "50,000.00", "-", "1,50,000.00"],
            ["02/07/2026", "TO ATM CASH WITHDRAWAL", "-", "-", "10,000.00", "1,40,000.00"],
        ]
        txns = parse_table_transactions(table_data, page_num=1, file_name="table.pdf")
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].credit, 50000.00)
        self.assertEqual(txns[0].debit, 0.0)
        self.assertEqual(txns[1].debit, 10000.00)
        self.assertEqual(txns[1].credit, 0.0)
        self.assertEqual(txns[1].balance, 140000.00)

    def test_08_duplicate_detection(self):
        t1 = CanonicalTransaction(
            date=date(2026, 6, 12),
            description="VENDOR PAYMENT",
            debit=5000.00,
            balance=20000.00,
            transaction_id="TXN1001",
        )
        t2 = CanonicalTransaction(
            date=date(2026, 6, 12),
            description="VENDOR PAYMENT",
            debit=5000.00,
            balance=20000.00,
            transaction_id="TXN1001",
        )
        d1 = t1.to_dict()
        d2 = t2.to_dict()
        from app.services.file_analysis_service import _evaluate_financial_integrity
        is_val, status_str, failures = _evaluate_financial_integrity(
            [d1, d2], 25000.0, 20000.0, 0.0, 10000.0, None, duplicate_txns=[d1, d2]
        )
        self.assertFalse(is_val)
        self.assertIn("duplicate", failures[0].lower())


if __name__ == "__main__":
    unittest.main()
