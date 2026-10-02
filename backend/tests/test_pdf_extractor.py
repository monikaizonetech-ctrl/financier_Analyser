"""
Test suite for Phase 2: Robust PDF Extraction Layer
"""
import os
import unittest
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.services.pdf_extractor import (
    LineType,
    ExtractedWord,
    ExtractedLine,
    ExtractedPage,
    ExtractedDocument,
    extract_pdf_document,
    extract_document_metadata,
    _reconstruct_lines_from_words,
    _is_column_header_line,
    _is_footer_line,
    _starts_with_date,
)
from app.services.file_analysis_service import analyse_bank_statement


class TestRobustPDFExtractor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo_pdf_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "uploads",
            "09dd73df-f2e1-4cec-9b00-7babdf6b8a54",
            "demo_bank_statement.pdf",
        )
        cls.test_artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(cls.test_artifacts_dir, exist_ok=True)

    def test_01_nonexistent_and_invalid_file(self):
        """Verify handling of missing or corrupted files."""
        doc = extract_pdf_document("nonexistent_statement.pdf")
        self.assertFalse(doc.is_valid)
        self.assertIn("File not found", doc.error_message)

    def test_02_demo_statement_extraction(self):
        """Verify extraction on existing demo bank statement PDF."""
        self.assertTrue(os.path.exists(self.demo_pdf_path), "Demo PDF should exist in uploads directory")
        doc = extract_pdf_document(self.demo_pdf_path, max_pages=5)

        # 1. Validation & page count
        self.assertTrue(doc.is_valid)
        self.assertEqual(doc.total_pages_in_pdf, 1)
        self.assertEqual(doc.pages_processed, 1)
        self.assertFalse(doc.is_scanned)

        # 2. Page information
        page = doc.pages[0]
        self.assertEqual(page.page_number, 1)
        self.assertGreater(page.width, 0)
        self.assertGreater(page.height, 0)
        self.assertGreater(page.character_count, 100)
        self.assertGreater(len(page.raw_text), 100)

        # 3. Line reconstruction
        self.assertGreater(len(page.lines), 15)
        for line in page.lines:
            self.assertIsInstance(line, ExtractedLine)
            self.assertGreater(len(line.text), 0)
            self.assertGreaterEqual(line.y_bottom, line.y_top)

        # 4. Headers & Footers classification
        self.assertGreater(len(page.header_lines), 0)
        col_headers = [l for l in page.header_lines if l.line_type == LineType.COLUMN_HEADER]
        self.assertEqual(len(col_headers), 1)
        self.assertIn("Date", col_headers[0].text)
        self.assertIn("Balance", col_headers[0].text)

        # 5. Transaction candidate isolation
        self.assertGreater(len(page.transaction_lines), 10)
        # Verify first transaction candidate line
        first_txn = page.transaction_lines[0]
        self.assertIn("Opening Balance", first_txn.text)

        # 6. Raw debug text presence
        self.assertIn("--- PAGE 1 ---", doc.raw_debug_text)
        self.assertIn("DEMO NATIONAL BANK", doc.raw_debug_text)

    def test_03_metadata_extraction(self):
        """Verify bank name, account holder, and account number extraction."""
        doc = extract_pdf_document(self.demo_pdf_path)
        meta = extract_document_metadata(doc)
        self.assertIn("DEMO NATIONAL BANK", meta["bank_name"])
        self.assertEqual(meta["account_holder"], "Monika L")
        self.assertIn("4821", meta["account_no"])
        self.assertEqual(meta["account_type"], "Savings")

    def test_04_line_reconstruction_with_tolerance(self):
        """Verify words on the same horizontal band are clustered into a single line."""
        words = [
            {"text": "01-08-2026", "x0": 50, "x1": 110, "top": 200.0, "bottom": 210.0},
            {"text": "Salary", "x0": 130, "x1": 180, "top": 201.0, "bottom": 211.0},
            {"text": "Credit", "x0": 190, "x1": 230, "top": 200.5, "bottom": 210.5},
            {"text": "50,000.00", "x0": 450, "x1": 500, "top": 199.8, "bottom": 209.8},
            # Second line lower on page
            {"text": "02-08-2026", "x0": 50, "x1": 110, "top": 225.0, "bottom": 235.0},
            {"text": "ATM", "x0": 130, "x1": 160, "top": 225.5, "bottom": 235.5},
            {"text": "Withdrawal", "x0": 170, "x1": 240, "top": 224.8, "bottom": 234.8},
        ]
        reconstructed = _reconstruct_lines_from_words(words, page_height=800.0, y_tolerance=3.0)
        self.assertEqual(len(reconstructed), 2)
        self.assertEqual(reconstructed[0].text, "01-08-2026 Salary Credit 50,000.00")
        self.assertEqual(reconstructed[1].text, "02-08-2026 ATM Withdrawal")

    def test_05_column_header_and_footer_detection(self):
        """Verify column header and footer identification helpers."""
        # Valid column headers
        self.assertTrue(_is_column_header_line("Date Particulars Chq No Debit Credit Balance"))
        self.assertTrue(_is_column_header_line("Txn Date Description Value Date Withdrawal Deposit Running Balance"))

        # Non-column headers (e.g. transactions or metadata)
        self.assertFalse(_is_column_header_line("01-07-2026 Opening Balance 50,000.00"))
        self.assertFalse(_is_column_header_line("Account Statement for Monika L"))

        # Footers
        page_height = 842.0
        self.assertTrue(_is_footer_line("Page 1 of 3", y_top=800.0, page_height=page_height))
        self.assertTrue(_is_footer_line("This is a computer-generated statement", y_top=790.0, page_height=page_height))
        self.assertTrue(_is_footer_line("Continued on next page", y_top=750.0, page_height=page_height))
        self.assertFalse(_is_footer_line("01-07-2026 Electricity Bill 2,340.00", y_top=500.0, page_height=page_height))

    def test_06_date_detection(self):
        """Verify flexible date detection regex."""
        self.assertTrue(_starts_with_date("01-07-2026"))
        self.assertTrue(_starts_with_date("15/12/2025"))
        self.assertTrue(_starts_with_date("05.04.2024"))
        self.assertTrue(_starts_with_date("01-Jul-2026"))
        self.assertTrue(_starts_with_date("2026-08-15"))
        self.assertFalse(_starts_with_date("Date Particulars Debit Credit"))
        self.assertFalse(_starts_with_date("HDFC BANK STATEMENT"))

    def test_07_page_limit_enforcement(self):
        """Verify that PDFs exceeding max_pages are processed up to the configured limit with warnings."""
        multi_page_pdf = os.path.join(self.test_artifacts_dir, "multi_page_test.pdf")
        c = canvas.Canvas(multi_page_pdf, pagesize=A4)
        for p in range(1, 8):  # 7 pages
            c.drawString(100, 750, f"Statement of Account Page {p}")
            c.drawString(100, 700, "Date Description Debit Credit Balance")
            c.drawString(100, 650, f"0{p}-01-2026 Test Txn {p} 100.00 - 1000.00")
            c.drawString(100, 50, f"Page {p} of 7")
            c.showPage()
        c.save()

        doc = extract_pdf_document(multi_page_pdf, max_pages=5)
        self.assertTrue(doc.is_valid)
        self.assertEqual(doc.total_pages_in_pdf, 7)
        self.assertEqual(doc.pages_processed, 5)
        self.assertTrue(any("Processing the first 5 pages" in w for w in doc.warning_messages))

    def test_08_scanned_pdf_detection(self):
        """Verify that PDFs with sparse/no selectable text are detected as scanned/image documents."""
        scanned_sim_pdf = os.path.join(self.test_artifacts_dir, "scanned_sim.pdf")
        c = canvas.Canvas(scanned_sim_pdf, pagesize=A4)
        # Draw only shapes/empty canvas (no text drawn)
        c.rect(50, 50, 500, 700)
        c.showPage()
        c.save()

        doc = extract_pdf_document(scanned_sim_pdf)
        self.assertTrue(doc.is_valid)
        self.assertTrue(doc.is_scanned)
        self.assertTrue(any("insufficient selectable text" in w for w in doc.warning_messages))

        # Check that analyse_bank_statement passes this notice through cleanly
        res = analyse_bank_statement(scanned_sim_pdf)
        self.assertEqual(res["transactions_found"], 0)
        self.assertIn("insufficient selectable text", res["note"])

    def test_09_end_to_end_parity(self):
        """Verify analyse_bank_statement parity on demo statement."""
        res = analyse_bank_statement(self.demo_pdf_path)
        self.assertEqual(res["transactions_found"], 13)
        self.assertEqual(res["total_credits"], 48945.0)
        self.assertEqual(res["total_debits"], 16388.0)
        self.assertEqual(res["closing_balance"], 82557.0)
        self.assertEqual(res["net_cash_flow"], 32557.0)


if __name__ == "__main__":
    unittest.main()
