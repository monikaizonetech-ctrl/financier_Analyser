"""
Phase 7: Real-World Testing & Hardening Test Suite.
Validates the complete end-to-end pipeline across 20 diverse bank statement structures.
For every test case, verifies:
1. Correct number of transactions
2. Correct dates
3. Correct descriptions
4. Correct debit amounts
5. Correct credit amounts
6. Correct balances
7. Correct income classification
8. Correct expense classification
9. Correct totals
10. Correct opening balance
11. Correct closing balance
12. Correct charts
13. Correct PDF (4 pages)
14. Correct Excel (28 sheets)
"""
from datetime import date
import io
import os
import unittest
import openpyxl
import pdfplumber

from app.services.file_analysis_service import (
    ReportType,
    run_analysis,
    build_pdf_report,
    build_excel_report,
)
from tests.statement_generator import create_statement_pdf


class TestRealWorldHardening(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fixtures_dir = os.path.join(
            os.path.dirname(__file__),
            "artifacts",
            "phase7_fixtures",
        )
        os.makedirs(cls.fixtures_dir, exist_ok=True)

    def _verify_common_report_outputs(self, analysis_result, report_name="Test_Report"):
        """Helper to verify PDF and Excel generation and metric parity."""
        pdf_bytes = build_pdf_report(report_name, "BSA", analysis_result)
        excel_bytes = build_excel_report(report_name, "BSA", analysis_result)

        # PDF validation
        self.assertGreater(len(pdf_bytes), 1000)
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            self.assertEqual(len(pdf.pages), 4, "PDF report must have exactly 4 pages")
            p1_text = pdf.pages[0].extract_text()
            self.assertIn("Overview of the Input Statement", p1_text)
            self.assertIn("Financial Summary & Key Indicators", p1_text)

            p2_text = pdf.pages[1].extract_text()
            self.assertIn("Visual Analytics", p2_text)
            self.assertIn("Transaction Visualizations", p2_text)

            p3_text = pdf.pages[2].extract_text()
            self.assertIn("Additional Financial Analysis", p3_text)
            self.assertIn("Cashflow Summary", p3_text)

            p4_text = pdf.pages[3].extract_text()
            self.assertIn("Transaction Summary", p4_text)

        # Excel validation
        self.assertGreater(len(excel_bytes), 5000)
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        self.assertEqual(len(wb.sheetnames), 28, "Excel report must have exactly 28 sheets")

        return pdf_bytes, excel_bytes

    # ----------------------------------------------------------------------
    # 1. Existing demo statement
    # ----------------------------------------------------------------------
    def test_01_existing_demo_statement(self):
        demo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "uploads",
            "09dd73df-f2e1-4cec-9b00-7babdf6b8a54",
            "demo_bank_statement.pdf",
        )
        r = run_analysis(ReportType.BSA, [demo_path], account_holder="Monika L")
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 13)
        self.assertEqual(a["opening_balance"], 50000.0)
        self.assertEqual(a["closing_balance"], 82557.0)
        self.assertEqual(a["total_credit"], 48945.0)
        self.assertEqual(a["total_debit"], 16388.0)
        self.assertEqual(a["net_cash_flow"], 32557.0)
        self.assertEqual(a["validation_status"], "VALID")

        self._verify_common_report_outputs(r, "Demo_Test")

    # ----------------------------------------------------------------------
    # 2. Different column alignment
    # ----------------------------------------------------------------------
    def test_02_different_column_alignment(self):
        pdf_path = os.path.join(self.fixtures_dir, "case02_diff_align.pdf")
        headers = ["Date", "Narration", "Withdrawal (Dr)", "Deposit (Cr)", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Initial Balance", "-", "-", "45,000.00"],
            ["05/08/2026", "Consulting Income", "-", "15,000.00", "60,000.00"],
            ["12/08/2026", "Office Supplies", "3,500.00", "-", "56,500.00"],
            ["20/08/2026", "Software Subscription", "4,500.00", "-", "52,000.00"],
            ["28/08/2026", "Client Payment", "-", "20,000.00", "72,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "APEX CO-OPERATIVE BANK", "John Doe", "XXXX 8821",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 5)
        self.assertEqual(a["opening_balance"], 45000.0)
        self.assertEqual(a["closing_balance"], 72000.0)
        self.assertEqual(a["total_credit"], 35000.0)
        self.assertEqual(a["total_debit"], 8000.0)
        self.assertEqual(a["net_cash_flow"], 27000.0)
        self.assertEqual(a["validation_status"], "VALID")

        self._verify_common_report_outputs(r, "Case02_Align")

    # ----------------------------------------------------------------------
    # 3. Different column order (Credit before Debit)
    # ----------------------------------------------------------------------
    def test_03_different_column_order(self):
        pdf_path = os.path.join(self.fixtures_dir, "case03_diff_order.pdf")
        headers = ["Txn Date", "Description", "Credit", "Debit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "20,000.00"],
            ["04/08/2026", "Deposit / Client A", "10,000.00", "-", "30,000.00"],
            ["10/08/2026", "Withdrawal / Rent", "-", "8,000.00", "22,000.00"],
            ["15/08/2026", "Deposit / Salary", "25,000.00", "-", "47,000.00"],
            ["22/08/2026", "Withdrawal / Utilities", "-", "2,000.00", "45,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "HERITAGE BANK CORP", "Sarah Connor", "XXXX 1290",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 5)
        self.assertEqual(a["opening_balance"], 20000.0)
        self.assertEqual(a["closing_balance"], 45000.0)
        self.assertEqual(a["total_credit"], 35000.0)
        self.assertEqual(a["total_debit"], 10000.0)
        self.assertEqual(a["net_cash_flow"], 25000.0)
        self.assertEqual(a["validation_status"], "VALID")

        self._verify_common_report_outputs(r, "Case03_Order")

    # ----------------------------------------------------------------------
    # 4. Multi-line narration
    # ----------------------------------------------------------------------
    def test_04_multi_line_narration(self):
        pdf_path = os.path.join(self.fixtures_dir, "case04_multiline.pdf")
        headers = ["Date", "Particulars", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "50,000.00"],
            ["03/08/2026", "NEFT/TRANSFER FROM ABC CORP\nINVOICE 10928/REF 8812\nFOR TECH SERVICES", "-", "40,000.00", "90,000.00"],
            ["10/08/2026", "UPI/PAYMENT TO VENDOR XYZ\nSTORE PURCHASE BILL 4402", "5,000.00", "-", "85,000.00"],
            ["18/08/2026", "IMPS/SALARY DISBURSEMENT\nEMPLOYEE REIMBURSEMENT", "-", "15,000.00", "100,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "NATIONAL COMMERCIAL BANK", "Tech Studio", "XXXX 4499",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 4)
        self.assertEqual(a["opening_balance"], 50000.0)
        self.assertEqual(a["closing_balance"], 100000.0)
        self.assertEqual(a["total_credit"], 55000.0)
        self.assertEqual(a["total_debit"], 5000.0)
        self.assertEqual(a["net_cash_flow"], 50000.0)

        # Verify multi-line narration was stitched cleanly
        second_txn = a["all_rows"][1]
        self.assertIn("NEFT/TRANSFER FROM ABC CORP", second_txn["description"])
        self.assertIn("INVOICE 10928/REF 8812", second_txn["description"])

        self._verify_common_report_outputs(r, "Case04_Multiline")

    # ----------------------------------------------------------------------
    # 5. Multi-page statement
    # ----------------------------------------------------------------------
    def test_05_multi_page_statement(self):
        pdf_path = os.path.join(self.fixtures_dir, "case05_multipage.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "30,000.00"],
            ["03/08/2026", "Deposit A", "-", "10,000.00", "40,000.00"],
            ["06/08/2026", "Expense A", "4,000.00", "-", "36,000.00"],
            ["10/08/2026", "Expense B", "6,000.00", "-", "30,000.00"],
            # Pagebreak occurs after row 4
            ["15/08/2026", "Deposit B", "-", "20,000.00", "50,000.00"],
            ["20/08/2026", "Expense C", "5,000.00", "-", "45,000.00"],
            ["25/08/2026", "Deposit C", "-", "15,000.00", "60,000.00"],
            ["30/08/2026", "Expense D", "2,000.00", "-", "58,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "METROPOLITAN BANK", "Alice Walker", "XXXX 7701",
            headers, col_x, rows,
            page_break_after_rows=[4],
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 8)
        self.assertEqual(a["opening_balance"], 30000.0)
        self.assertEqual(a["closing_balance"], 58000.0)
        self.assertEqual(a["total_credit"], 45000.0)
        self.assertEqual(a["total_debit"], 17000.0)
        self.assertEqual(a["net_cash_flow"], 28000.0)
        self.assertEqual(a["validation_status"], "VALID")

        self._verify_common_report_outputs(r, "Case05_Multipage")

    # ----------------------------------------------------------------------
    # 6. Repeated table headers across pages
    # ----------------------------------------------------------------------
    def test_06_repeated_table_headers(self):
        pdf_path = os.path.join(self.fixtures_dir, "case06_repeated_headers.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "25,000.00"],
            ["05/08/2026", "Income Txn 1", "-", "15,000.00", "40,000.00"],
            ["10/08/2026", "Expense Txn 1", "5,000.00", "-", "35,000.00"],
            # Page break here with repeated header drawn on page 2
            ["15/08/2026", "Income Txn 2", "-", "20,000.00", "55,000.00"],
            ["25/08/2026", "Expense Txn 2", "10,000.00", "-", "45,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "REPUBLIC SAVINGS BANK", "Robert Green", "XXXX 3302",
            headers, col_x, rows,
            page_break_after_rows=[3],
            repeat_headers=True,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        # Repeated header should not be parsed as a transaction row
        self.assertEqual(len(a["all_rows"]), 5)
        self.assertEqual(a["opening_balance"], 25000.0)
        self.assertEqual(a["closing_balance"], 45000.0)
        self.assertEqual(a["total_credit"], 35000.0)
        self.assertEqual(a["total_debit"], 15000.0)
        self.assertEqual(a["validation_status"], "VALID")

        self._verify_common_report_outputs(r, "Case06_RepeatHdr")

    # ----------------------------------------------------------------------
    # 7. Different date formats (YYYY-MM-DD)
    # ----------------------------------------------------------------------
    def test_07_different_date_formats(self):
        pdf_path = os.path.join(self.fixtures_dir, "case07_iso_dates.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["2026-08-01", "Opening Balance", "-", "-", "50,000.00"],
            ["2026-08-05", "Client Transfer", "-", "25,000.00", "75,000.00"],
            ["2026-08-15", "Equipment Lease", "10,000.00", "-", "65,000.00"],
            ["2026-08-25", "Interest Earned", "-", "500.00", "65,500.00"],
        ]
        create_statement_pdf(
            pdf_path, "GLOBAL TRUST BANK", "Nexus Corp", "XXXX 9912",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 4)
        self.assertEqual(a["opening_balance"], 50000.0)
        self.assertEqual(a["closing_balance"], 65500.0)
        self.assertEqual(str(a["all_rows"][0]["date"]), "2026-08-01")
        self.assertEqual(str(a["all_rows"][1]["date"]), "2026-08-05")

        self._verify_common_report_outputs(r, "Case07_Dates")

    # ----------------------------------------------------------------------
    # 8. Different amount formats (Indian Lakh/Crore notation)
    # ----------------------------------------------------------------------
    def test_08_different_amount_formats(self):
        pdf_path = os.path.join(self.fixtures_dir, "case08_indian_amounts.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "1,50,000.00"],
            ["05/08/2026", "Contractor Inflow", "-", "2,25,000.50", "3,75,000.50"],
            ["15/08/2026", "Machinery Purchase", "1,15,000.00", "-", "2,60,000.50"],
        ]
        create_statement_pdf(
            pdf_path, "STATE FINANCIAL BANK", "Industrial Ltd", "XXXX 5510",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 3)
        self.assertEqual(a["opening_balance"], 150000.0)
        self.assertEqual(a["total_credit"], 225000.5)
        self.assertEqual(a["total_debit"], 115000.0)
        self.assertEqual(a["closing_balance"], 260000.5)

        self._verify_common_report_outputs(r, "Case08_Amounts")

    # ----------------------------------------------------------------------
    # 9. Debit / Credit Columns (explicit distinction)
    # ----------------------------------------------------------------------
    def test_09_debit_credit_columns(self):
        pdf_path = os.path.join(self.fixtures_dir, "case09_explicit_dr_cr.pdf")
        headers = ["Date", "Particulars", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "0.00", "0.00", "10,000.00"],
            ["03/08/2026", "Salary Deposit", "0.00", "50,000.00", "60,000.00"],
            ["08/08/2026", "Rent Withdrawal", "15,000.00", "0.00", "45,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "STANDARD COMMERCIAL BANK", "David Brown", "XXXX 4400",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 3)
        self.assertEqual(a["all_rows"][1]["transaction_type"], "INCOME")
        self.assertEqual(a["all_rows"][2]["transaction_type"], "EXPENSE")

        self._verify_common_report_outputs(r, "Case09_ExplicitCols")

    # ----------------------------------------------------------------------
    # 10. CR / DR Representation (Single Amount column with suffix)
    # ----------------------------------------------------------------------
    def test_10_cr_dr_representation(self):
        pdf_path = os.path.join(self.fixtures_dir, "case10_cr_dr_suffix.pdf")
        headers = ["Date", "Description", "Amount", "Balance"]
        col_x = [50, 150, 350, 470]
        rows = [
            ["01/08/2026", "Opening Balance", "0.00", "50,000.00"],
            ["04/08/2026", "Project Milestone", "30,000.00 CR", "80,000.00"],
            ["11/08/2026", "Office Rent", "12,000.00 DR", "68,000.00"],
            ["19/08/2026", "Client Bonus", "5,000.00 CR", "73,000.00"],
            ["26/08/2026", "Utility Bill", "3,000.00 DR", "70,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "CITIZENS UNION BANK", "Creative Agency", "XXXX 8192",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 5)
        self.assertEqual(a["opening_balance"], 50000.0)
        self.assertEqual(a["closing_balance"], 70000.0)
        self.assertEqual(a["total_credit"], 35000.0)
        self.assertEqual(a["total_debit"], 15000.0)
        self.assertEqual(a["net_cash_flow"], 20000.0)
        self.assertEqual(a["validation_status"], "VALID")

        self._verify_common_report_outputs(r, "Case10_CrDr")

    # ----------------------------------------------------------------------
    # 11. Negative Amount Representation (- for Expense, unsigned for Income)
    # ----------------------------------------------------------------------
    def test_11_negative_amount_representation(self):
        pdf_path = os.path.join(self.fixtures_dir, "case11_negative_amounts.pdf")
        headers = ["Date", "Description", "Amount", "Balance"]
        col_x = [50, 150, 350, 470]
        rows = [
            ["01/08/2026", "Opening Balance", "0.00", "40,000.00"],
            ["05/08/2026", "Consulting Fee", "20,000.00", "60,000.00"],
            ["12/08/2026", "Hardware Purchase", "-8,000.00", "52,000.00"],
            ["20/08/2026", "Cloud Hosting", "-2,000.00", "50,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "ALLIANCE BANK", "Dev Ops Ltd", "XXXX 1029",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 4)
        self.assertEqual(a["opening_balance"], 40000.0)
        self.assertEqual(a["closing_balance"], 50000.0)
        self.assertEqual(a["total_credit"], 20000.0)
        self.assertEqual(a["total_debit"], 10000.0)

        self._verify_common_report_outputs(r, "Case11_NegativeAmounts")

    # ----------------------------------------------------------------------
    # 12. Missing optional fields (No Cheque / Ref number)
    # ----------------------------------------------------------------------
    def test_12_missing_optional_fields(self):
        pdf_path = os.path.join(self.fixtures_dir, "case12_missing_optional.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 150, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "15,000.00"],
            ["05/08/2026", "Stripe Payout", "-", "25,000.00", "40,000.00"],
            ["15/08/2026", "Domain Renewal", "1,500.00", "-", "38,500.00"],
        ]
        create_statement_pdf(
            pdf_path, "MODERN DIGITAL BANK", "SaaS Startup", "XXXX 9001",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 3)
        self.assertEqual(a["opening_balance"], 15000.0)
        self.assertEqual(a["closing_balance"], 38500.0)

        self._verify_common_report_outputs(r, "Case12_MissingOptional")

    # ----------------------------------------------------------------------
    # 13. Long transaction descriptions (>100 characters)
    # ----------------------------------------------------------------------
    def test_13_long_transaction_descriptions(self):
        pdf_path = os.path.join(self.fixtures_dir, "case13_long_desc.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 130, 340, 415, 490]
        long_desc_1 = "NEFT-AXIS000123-MICROSOFT CORP INDIA PVT LTD-MONTHLY ENTERPRISE SUBSCRIPTION CLOUD SERVICES REF 9901828"
        long_desc_2 = "RTGS-HDFC000456-ALTIUS TECH SOLUTIONS PRIVATE LIMITED-PROFESSIONAL CONSULTING RETAINER FEE FOR AUGUST"
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "100,000.00"],
            ["05/08/2026", long_desc_1, "25,000.00", "-", "75,000.00"],
            ["15/08/2026", long_desc_2, "-", "50,000.00", "125,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "CONTINENTAL BANK", "Enterprise Co", "XXXX 6677",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 3)
        self.assertIn("MICROSOFT CORP", a["all_rows"][1]["description"])
        self.assertIn("ALTIUS TECH SOLUTIONS", a["all_rows"][2]["description"])

        self._verify_common_report_outputs(r, "Case13_LongDesc")

    # ----------------------------------------------------------------------
    # 14. Header / footer noise exclusion
    # ----------------------------------------------------------------------
    def test_14_header_footer_noise(self):
        pdf_path = os.path.join(self.fixtures_dir, "case14_noise.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        header_noise = [
            "Branch: Fort Mumbai | IFSC Code: SBIN0001234 | GSTIN: 27AAACS1234F1Z1",
            "Customer Support: 1800-425-3800 | Email: support@bank.com",
        ]
        footer_noise = [
            "CONFIDENTIAL: This document is strictly intended for the designated recipient. Computer-generated without physical signature.",
        ]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "60,000.00"],
            ["05/08/2026", "Dividend Payout", "-", "12,000.00", "72,000.00"],
            ["12/08/2026", "Maintenance Charge", "2,000.00", "-", "70,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "STATE BANK OF COMMERCE", "Noise Test User", "XXXX 4411",
            headers, col_x, rows,
            header_noise=header_noise,
            footer_noise=footer_noise,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        # Only real transaction lines should be extracted
        self.assertEqual(len(a["all_rows"]), 3)
        self.assertEqual(a["opening_balance"], 60000.0)
        self.assertEqual(a["closing_balance"], 70000.0)

        self._verify_common_report_outputs(r, "Case14_Noise")

    # ----------------------------------------------------------------------
    # 15. Duplicate-like transactions
    # ----------------------------------------------------------------------
    def test_15_duplicate_like_transactions(self):
        pdf_path = os.path.join(self.fixtures_dir, "case15_duplicates.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "50,000.00"],
            ["10/08/2026", "ATM Cash Withdrawal", "5,000.00", "-", "45,000.00"],
            ["10/08/2026", "ATM Cash Withdrawal", "5,000.00", "-", "40,000.00"],
            ["20/08/2026", "Salary Deposit", "-", "30,000.00", "70,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "PREMIER BANK", "Daniel Craig", "XXXX 5599",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        # Both ATM withdrawals are legitimate and preserved
        self.assertEqual(len(a["all_rows"]), 4)
        self.assertEqual(a["total_debit"], 10000.0)
        self.assertEqual(a["total_credit"], 30000.0)
        self.assertEqual(a["closing_balance"], 70000.0)

        self._verify_common_report_outputs(r, "Case15_Duplicates")

    # ----------------------------------------------------------------------
    # 16. Balance reconciliation
    # ----------------------------------------------------------------------
    def test_16_balance_reconciliation(self):
        pdf_path = os.path.join(self.fixtures_dir, "case16_reconciliation.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "80,000.00"],
            ["05/08/2026", "Consulting Income", "-", "25,000.00", "105,000.00"],
            ["15/08/2026", "Office Rent", "20,000.00", "-", "85,000.00"],
            ["25/08/2026", "Equipment Purchase", "15,000.00", "-", "70,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "FIDELITY BANK", "Reconciliation Test", "XXXX 0019",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        rec = a["reconciliation"]
        self.assertEqual(rec["status"], "VALID")
        self.assertEqual(rec["opening_balance"], 80000.0)
        self.assertEqual(rec["total_income"], 25000.0)
        self.assertEqual(rec["total_expense"], 35000.0)
        self.assertEqual(rec["net_cash_flow"], -10000.0)
        self.assertEqual(rec["expected_closing_balance"], 70000.0)
        self.assertEqual(rec["extracted_closing_balance"], 70000.0)
        self.assertEqual(len(rec["discrepancies"]), 0)

        self._verify_common_report_outputs(r, "Case16_Reconciled")

    # ----------------------------------------------------------------------
    # 17. Statement with income and expenses (Mixed)
    # ----------------------------------------------------------------------
    def test_17_statement_with_income_and_expenses(self):
        pdf_path = os.path.join(self.fixtures_dir, "case17_mixed.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "25,000.00"],
            ["02/08/2026", "Salary Inflow", "-", "50,000.00", "75,000.00"],
            ["05/08/2026", "Grocery Store", "3,500.00", "-", "71,500.00"],
            ["10/08/2026", "Freelance Project", "-", "15,000.00", "86,500.00"],
            ["15/08/2026", "Electricity Bill", "2,500.00", "-", "84,000.00"],
            ["22/08/2026", "Dinner with Friends", "1,800.00", "-", "82,200.00"],
            ["28/08/2026", "Stock Dividend", "-", "4,000.00", "86,200.00"],
        ]
        create_statement_pdf(
            pdf_path, "UNION BANK OF INDIA", "Mixed User", "XXXX 7711",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 7)
        self.assertEqual(a["total_credit"], 69000.0)
        self.assertEqual(a["total_debit"], 7800.0)
        self.assertEqual(a["net_cash_flow"], 61200.0)
        self.assertEqual(a["closing_balance"], 86200.0)

        self._verify_common_report_outputs(r, "Case17_Mixed")

    # ----------------------------------------------------------------------
    # 18. Statement with only expenses (Outflow only)
    # ----------------------------------------------------------------------
    def test_18_statement_with_only_expenses(self):
        pdf_path = os.path.join(self.fixtures_dir, "case18_expenses_only.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "50,000.00"],
            ["05/08/2026", "Office Rent", "20,000.00", "-", "30,000.00"],
            ["15/08/2026", "Vendor Payment", "10,000.00", "-", "20,000.00"],
            ["25/08/2026", "Utility Bill", "5,000.00", "-", "15,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "TREASURY SAVINGS BANK", "Expense Only Account", "XXXX 2219",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 4)
        self.assertEqual(a["total_credit"], 0.0)
        self.assertEqual(a["total_debit"], 35000.0)
        self.assertEqual(a["net_cash_flow"], -35000.0)
        self.assertEqual(a["closing_balance"], 15000.0)
        self.assertEqual(a["validation_status"], "VALID")

        self._verify_common_report_outputs(r, "Case18_ExpensesOnly")

    # ----------------------------------------------------------------------
    # 19. Statement with only income (Inflow only)
    # ----------------------------------------------------------------------
    def test_19_statement_with_only_income(self):
        pdf_path = os.path.join(self.fixtures_dir, "case19_income_only.pdf")
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        col_x = [50, 140, 310, 400, 490]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "10,000.00"],
            ["05/08/2026", "Salary Deposit", "-", "40,000.00", "50,000.00"],
            ["15/08/2026", "Bonus Credit", "-", "15,000.00", "65,000.00"],
            ["25/08/2026", "Interest Payout", "-", "1,000.00", "66,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "ACCUMULATOR BANK", "Income Only Account", "XXXX 8820",
            headers, col_x, rows,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 4)
        self.assertEqual(a["total_credit"], 56000.0)
        self.assertEqual(a["total_debit"], 0.0)
        self.assertEqual(a["net_cash_flow"], 56000.0)
        self.assertEqual(a["closing_balance"], 66000.0)
        self.assertEqual(a["validation_status"], "VALID")

        self._verify_common_report_outputs(r, "Case19_IncomeOnly")

    # ----------------------------------------------------------------------
    # 20. Statement with irregular spacing
    # ----------------------------------------------------------------------
    def test_20_statement_with_irregular_spacing(self):
        pdf_path = os.path.join(self.fixtures_dir, "case20_irregular_spacing.pdf")
        headers = ["Date", "Particulars", "Withdrawal", "Deposit", "Balance"]
        col_x = [48, 138, 305, 395, 485]
        rows = [
            ["01/08/2026", "Opening Balance", "-", "-", "25,000.00"],
            ["06/08/2026", "Client Advance", "-", "18,000.00", "43,000.00"],
            ["14/08/2026", "Supplies Store", "4,200.00", "-", "38,800.00"],
            ["22/08/2026", "Software Tool", "2,800.00", "-", "36,000.00"],
        ]
        create_statement_pdf(
            pdf_path, "COMMERCE BANK OF INDIA", "Freelance Studio", "XXXX 5092",
            headers, col_x, rows,
            irregular_spacing=True,
        )

        r = run_analysis(ReportType.BSA, [pdf_path])
        a = r["analytics"]

        self.assertEqual(len(a["all_rows"]), 4)
        self.assertEqual(a["opening_balance"], 25000.0)
        self.assertEqual(a["closing_balance"], 36000.0)
        self.assertEqual(a["total_credit"], 18000.0)
        self.assertEqual(a["total_debit"], 7000.0)
        self.assertEqual(a["net_cash_flow"], 11000.0)

        self._verify_common_report_outputs(r, "Case20_IrregularSpacing")


if __name__ == "__main__":
    unittest.main()
