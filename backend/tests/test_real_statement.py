"""
Test case verifying end-to-end extraction, reconciliation, and report generation
for the real Indian Bank statement (AccountStatement_22-09-2026 17_48_55.pdf).
"""
import io
import os
import unittest
import pdfplumber
import openpyxl

from app.services.file_analysis_service import (
    ReportType,
    run_analysis,
    build_pdf_report,
    build_excel_report,
    analyse_bank_statement,
)
from app.services.reconciliation_service import (
    reconcile_transactions,
    ValidationStatus,
)


class TestRealIndianBankStatement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_pdf_path = r"C:\Users\IZONE 181\Downloads\AccountStatement_22-09-2026 17_48_55.pdf"

    def test_real_statement_extraction_and_reconciliation(self):
        if not os.path.exists(self.real_pdf_path):
            self.skipTest("Real statement PDF not found on system")

        res = analyse_bank_statement(self.real_pdf_path)

        # 1. Verify counts and key figures
        self.assertEqual(res["transactions_found"], 30, "Must extract all 30 transactions")
        self.assertEqual(res["total_credits"], 592.00, "Total credits must equal 592.00")
        self.assertEqual(res["total_debits"], 5603.00, "Total debits must equal 5603.00")
        self.assertEqual(res["opening_balance"], 5381.60, "Opening balance must equal 5381.60")
        self.assertEqual(res["closing_balance"], 370.60, "Closing balance must equal 370.60")
        self.assertEqual(res["net_cash_flow"], -5011.00, "Net cash flow must equal -5011.00")

        # 2. Verify reconciliation integrity
        rec = reconcile_transactions(
            rows=res["transactions"],
            opening_balance=res["opening_balance"],
            extracted_closing_balance=res["closing_balance"],
        )
        self.assertEqual(rec.status, ValidationStatus.VALID)
        self.assertEqual(rec.discrepancy_count, 0)
        self.assertEqual(rec.expected_closing_balance, 370.60)

        # 3. Verify end-to-end report generation
        analysis = run_analysis(ReportType.BSA, [self.real_pdf_path])
        self.assertEqual(analysis["analytics"]["bank_name"], "INDIAN BANK")
        self.assertEqual(analysis["analytics"]["account_holder"], "Suguna Subramanian")

        pdf_bytes = build_pdf_report("Indian_Bank_Report", "BSA", analysis)
        self.assertGreater(len(pdf_bytes), 1000)
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            p1_text = pdf.pages[0].extract_text()
            self.assertIn("INDIAN BANK", p1_text)
            self.assertIn("Suguna Subramanian", p1_text)
            self.assertIn("5,603.00", p1_text)
            self.assertIn("592.00", p1_text)
            self.assertIn("370.60", p1_text)

        excel_bytes = build_excel_report("Indian_Bank_Report", "BSA", analysis)
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        self.assertEqual(len(wb.sheetnames), 28)


if __name__ == "__main__":
    unittest.main()
