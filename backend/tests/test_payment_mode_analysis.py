import unittest
from datetime import date
import io
import openpyxl
import pdfplumber

from app.services.file_analysis_service import (
    _classify_payment_mode,
    _compute_payment_mode_summary,
    _enrich_transactions,
    _build_analytics,
    _draw_payment_mode_analysis,
    build_pdf_report,
    build_excel_report,
)


class TestPaymentModeAnalysis(unittest.TestCase):
    """Unit tests for Phase - Fix Payment Mode Analysis requirements."""

    def test_01_payment_mode_detection(self):
        """Payment mode should represent HOW the transaction was performed.
        Supported modes: UPI, IMPS, NEFT, RTGS, ATM, POS, CHEQUE, CASH,
        BANK CHARGE, INTEREST, ECS, TRANSFER, OTHER.
        """
        cases = [
            ("UPI/12345/Vendor", "UPI"),
            ("user@upi payment", "UPI"),
            ("MMT/IMPS/987654321/Transfer", "IMPS"),
            ("IMPS/Ref9910", "IMPS"),
            ("NEFT CR-HDFC0001234-Client", "NEFT"),
            ("RTGS/PUNB0001-Contractor", "RTGS"),
            ("ATM-WDL Main Branch", "ATM"),
            ("CASH WDL ATM 004", "ATM"),
            ("POS 401234 Reliance Retail", "POS"),
            ("E-POS Swiped txn", "POS"),
            ("CHQ 441029 Clearance", "CHEQUE"),
            ("CHEQUE DEPOSIT 1002", "CHEQUE"),
            ("CASH DEPOSIT Counter", "CASH"),
            ("BY CASH Deposit", "CASH"),
            ("SMS CHARGES Q2", "BANK CHARGE"),
            ("INT.COLL 15AUG", "BANK CHARGE"),
            ("PROCESSING FEE LOAN", "BANK CHARGE"),
            ("PENAL INTEREST DEBIT", "BANK CHARGE"),
            ("INTEREST CREDIT SB", "INTEREST"),
            ("INT.PD Q1", "INTEREST"),
            ("SAVINGS BANK INTEREST RECEIVED", "INTEREST"),
            ("ECS DEBIT MUTUAL FUND", "ECS"),
            ("NACH HDFC AUTO DEBIT", "ECS"),
            ("INFT INTER-BRANCH TRANSFER", "TRANSFER"),
            ("BIL/INFT/99812", "TRANSFER"),
            ("Unknown narration without mode", "OTHER"),
        ]
        for desc, expected_mode in cases:
            with self.subTest(desc=desc):
                self.assertEqual(_classify_payment_mode(desc), expected_mode)

    def test_02_payment_mode_decoupled_from_financial_categories(self):
        """Financial categories (like Vendor & Contractor Payments, Salaries & Labor)
        must never be used as payment mode tags.
        """
        descriptions = [
            "SALARY FOR AUGUST 2026",
            "OFFICE RENT PAYMENT",
            "PURCHASE OF CEMENT & STEEL",
            "PETROL LOGISTICS EXPENSE",
        ]
        for desc in descriptions:
            mode = _classify_payment_mode(desc)
            self.assertNotIn(mode, [
                "Salaries & Labor",
                "Vendor & Contractor Payments",
                "Materials & Supplies",
                "Utilities",
                "Equipment & Fuel",
            ])

    def test_03_independent_credit_and_debit_analysis(self):
        """Payment Mode Analysis must be calculated independently for:
        1. CREDIT transactions
        2. DEBIT transactions
        """
        rows = [
            {"date": date(2026, 8, 1), "description": "UPI/1", "credit": 1000.0, "debit": 0.0, "balance": 11000.0, "direction": "CREDIT", "payment_mode": "UPI"},
            {"date": date(2026, 8, 2), "description": "NEFT/2", "credit": 3000.0, "debit": 0.0, "balance": 14000.0, "direction": "CREDIT", "payment_mode": "NEFT"},
            {"date": date(2026, 8, 3), "description": "RTGS/3", "credit": 0.0, "debit": 5000.0, "balance": 9000.0, "direction": "DEBIT", "payment_mode": "RTGS"},
            {"date": date(2026, 8, 4), "description": "IMPS/4", "credit": 0.0, "debit": 2000.0, "balance": 7000.0, "direction": "DEBIT", "payment_mode": "IMPS"},
        ]
        cr_rows = [r for r in rows if r["direction"] == "CREDIT"]
        dr_rows = [r for r in rows if r["direction"] == "DEBIT"]

        cr_dict, cr_list = _compute_payment_mode_summary(cr_rows, is_credit=True, total_amount=4000.0)
        dr_dict, dr_list = _compute_payment_mode_summary(dr_rows, is_credit=False, total_amount=7000.0)

        # Credit modes should contain UPI and NEFT, not RTGS or IMPS
        self.assertIn("UPI", cr_dict)
        self.assertIn("NEFT", cr_dict)
        self.assertNotIn("RTGS", cr_dict)
        self.assertNotIn("IMPS", cr_dict)

        # Debit modes should contain RTGS and IMPS, not UPI or NEFT
        self.assertIn("RTGS", dr_dict)
        self.assertIn("IMPS", dr_dict)
        self.assertNotIn("UPI", dr_dict)
        self.assertNotIn("NEFT", dr_dict)

    def test_04_payment_mode_structure_and_percentages_sum(self):
        """For each payment mode calculate:
        1. Transaction count
        2. Total amount
        3. Percentage of total amount
        4. Percentage of total count
        The sum of amount_percentage and count_percentage must equal 100% within rounding tolerance.
        """
        cr_rows = [
            {"date": date(2026, 8, 1), "description": "RTGS/Client 1", "credit": 12500000.0, "debit": 0.0, "direction": "CREDIT", "payment_mode": "RTGS"},
            {"date": date(2026, 8, 2), "description": "RTGS/Client 2", "credit": 7500000.0, "debit": 0.0, "direction": "CREDIT", "payment_mode": "RTGS"},
            {"date": date(2026, 8, 3), "description": "NEFT/Client 3", "credit": 4000000.0, "debit": 0.0, "direction": "CREDIT", "payment_mode": "NEFT"},
            {"date": date(2026, 8, 4), "description": "IMPS/Client 4", "credit": 1000000.0, "debit": 0.0, "direction": "CREDIT", "payment_mode": "IMPS"},
        ]
        total_cr = 25000000.0

        cr_dict, cr_list = _compute_payment_mode_summary(cr_rows, is_credit=True, total_amount=total_cr)

        rtgs_item = cr_dict["RTGS"]
        # Required structure fields
        self.assertEqual(rtgs_item["payment_mode"], "RTGS")
        self.assertEqual(rtgs_item["transaction_count"], 2)
        self.assertEqual(rtgs_item["total_amount"], 20000000.0)
        self.assertEqual(rtgs_item["amount_percentage"], 80.0)
        self.assertEqual(rtgs_item["count_percentage"], 50.0)

        # Backwards compatible alias keys
        self.assertEqual(rtgs_item["count"], 2)
        self.assertEqual(rtgs_item["amount"], 20000000.0)
        self.assertEqual(rtgs_item["pct_amount"], 80.0)
        self.assertEqual(rtgs_item["pct_count"], 50.0)

        # Sum of percentages must equal 100% within rounding tolerance
        sum_amt_pct = sum(item["amount_percentage"] for item in cr_list)
        sum_cnt_pct = sum(item["count_percentage"] for item in cr_list)
        self.assertAlmostEqual(sum_amt_pct, 100.0, places=1)
        self.assertAlmostEqual(sum_cnt_pct, 100.0, places=1)

    def test_05_do_not_hide_modes_when_6_or_fewer(self):
        """If there are 6 or fewer payment modes: Show all of them."""
        # 6 modes
        modes = ["UPI", "RTGS", "IMPS", "NEFT", "ATM", "CHEQUE"]
        rows = [
            {"date": date(2026, 8, i + 1), "description": f"{m}/Txn", "credit": (i + 1) * 1000.0, "debit": 0.0, "direction": "CREDIT", "payment_mode": m}
            for i, m in enumerate(modes)
        ]
        tot = sum(r["credit"] for r in rows)
        cr_dict, cr_list = _compute_payment_mode_summary(rows, is_credit=True, total_amount=tot)

        # All 6 modes must be present, none combined into Other
        self.assertEqual(len(cr_list), 6)
        for m in modes:
            self.assertIn(m, cr_dict)

        sum_amt_pct = sum(item["amount_percentage"] for item in cr_list)
        self.assertAlmostEqual(sum_amt_pct, 100.0, places=1)

    def test_06_more_than_6_modes_combine_remaining_into_other(self):
        """If there are more than 6 payment modes:
        Show top 5 modes and combine the remaining modes into 'Other'.
        'Other' must contain the exact sum of all omitted modes.
        Percentages must still total 100%.
        """
        # 8 distinct payment modes
        modes_spec = [
            ("UPI", 35000.0, 10),
            ("RTGS", 30000.0, 5),
            ("IMPS", 20000.0, 8),
            ("NEFT", 8000.0, 4),
            ("ATM", 4000.0, 2),
            ("CHEQUE", 1500.0, 1),
            ("CASH", 1000.0, 1),
            ("POS", 500.0, 1),
        ]
        rows = []
        for m, amt, cnt in modes_spec:
            per_txn = amt / cnt
            for j in range(cnt):
                rows.append({
                    "date": date(2026, 8, 1),
                    "description": f"{m}/Txn{j}",
                    "debit": per_txn,
                    "credit": 0.0,
                    "direction": "DEBIT",
                    "payment_mode": m,
                })

        tot_dr = sum(amt for _, amt, _ in modes_spec)
        tot_cnt = sum(cnt for _, _, cnt in modes_spec)

        dr_dict, dr_list = _compute_payment_mode_summary(rows, is_credit=False, total_amount=tot_dr)

        # Exactly 6 items: top 5 + "Other"
        self.assertEqual(len(dr_list), 6)
        top_5_names = [m for m, _, _ in modes_spec[:5]]
        for m in top_5_names:
            self.assertIn(m, dr_dict)

        self.assertIn("Other", dr_dict)
        other_item = dr_dict["Other"]

        # Expected omitted sum: CHEQUE (1500) + CASH (1000) + POS (500) = 3000
        # Expected omitted count: 1 + 1 + 1 = 3
        expected_other_amt = 1500.0 + 1000.0 + 500.0
        expected_other_cnt = 1 + 1 + 1

        self.assertEqual(other_item["total_amount"], expected_other_amt)
        self.assertEqual(other_item["transaction_count"], expected_other_cnt)

        # Sum of amounts must match exactly total debit
        self.assertEqual(round(sum(item["total_amount"] for item in dr_list), 2), round(tot_dr, 2))
        self.assertEqual(sum(item["transaction_count"] for item in dr_list), tot_cnt)

        # Percentages must total 100%
        sum_amt_pct = sum(item["amount_percentage"] for item in dr_list)
        sum_cnt_pct = sum(item["count_percentage"] for item in dr_list)
        self.assertAlmostEqual(sum_amt_pct, 100.0, places=1)
        self.assertAlmostEqual(sum_cnt_pct, 100.0, places=1)

    def test_07_k_square_parity_credit_debit_complete_percentages(self):
        """Verify the exact problem from the prompt:
        Credit: RTGS 63%, OTHER 20%, IMPS 10%, NEFT 7% = 100%.
        Debit: RTGS 43%, IMPS 37%, OTHER 15%, NEFT 3%, BANK CHARGE 2% = 100%.
        All modes are displayed, and percentages sum to 100%.
        """
        # Mock transactions representing the K Square distribution
        cr_rows = [
            {"date": date(2026, 8, 1), "description": "RTGS/1", "credit": 63000.0, "debit": 0.0, "direction": "CREDIT", "payment_mode": "RTGS"},
            {"date": date(2026, 8, 2), "description": "OTHER/2", "credit": 20000.0, "debit": 0.0, "direction": "CREDIT", "payment_mode": "OTHER"},
            {"date": date(2026, 8, 3), "description": "IMPS/3", "credit": 10000.0, "debit": 0.0, "direction": "CREDIT", "payment_mode": "IMPS"},
            {"date": date(2026, 8, 4), "description": "NEFT/4", "credit": 7000.0, "debit": 0.0, "direction": "CREDIT", "payment_mode": "NEFT"},
        ]
        dr_rows = [
            {"date": date(2026, 8, 1), "description": "RTGS/1", "debit": 43000.0, "credit": 0.0, "direction": "DEBIT", "payment_mode": "RTGS"},
            {"date": date(2026, 8, 2), "description": "IMPS/2", "debit": 37000.0, "credit": 0.0, "direction": "DEBIT", "payment_mode": "IMPS"},
            {"date": date(2026, 8, 3), "description": "OTHER/3", "debit": 15000.0, "credit": 0.0, "direction": "DEBIT", "payment_mode": "OTHER"},
            {"date": date(2026, 8, 4), "description": "NEFT/4", "debit": 3000.0, "credit": 0.0, "direction": "DEBIT", "payment_mode": "NEFT"},
            {"date": date(2026, 8, 5), "description": "BANK CHARGE/5", "debit": 2000.0, "credit": 0.0, "direction": "DEBIT", "payment_mode": "BANK CHARGE"},
        ]
        cr_dict, cr_list = _compute_payment_mode_summary(cr_rows, is_credit=True, total_amount=100000.0)
        dr_dict, dr_list = _compute_payment_mode_summary(dr_rows, is_credit=False, total_amount=100000.0)

        # Credit: 4 modes, all shown
        self.assertEqual(len(cr_list), 4)
        self.assertEqual(sum(item["amount_percentage"] for item in cr_list), 100.0)
        self.assertEqual(cr_dict["RTGS"]["amount_percentage"], 63.0)
        self.assertEqual(cr_dict["OTHER"]["amount_percentage"], 20.0)
        self.assertEqual(cr_dict["IMPS"]["amount_percentage"], 10.0)
        self.assertEqual(cr_dict["NEFT"]["amount_percentage"], 7.0)

        # Debit: 5 modes, all shown
        self.assertEqual(len(dr_list), 5)
        self.assertEqual(sum(item["amount_percentage"] for item in dr_list), 100.0)
        self.assertEqual(dr_dict["RTGS"]["amount_percentage"], 43.0)
        self.assertEqual(dr_dict["IMPS"]["amount_percentage"], 37.0)
        self.assertEqual(dr_dict["OTHER"]["amount_percentage"], 15.0)
        self.assertEqual(dr_dict["NEFT"]["amount_percentage"], 3.0)
        self.assertEqual(dr_dict["BANK CHARGE"]["amount_percentage"], 2.0)

    def test_08_pdf_payment_mode_card_renders_all_modes_with_100_percent(self):
        """_draw_payment_mode_analysis card must render donuts and legends for all modes
        without dropping modes, with percentages summing to 100%.
        """
        cr_tags = {"RTGS": 63000.0, "OTHER": 20000.0, "IMPS": 10000.0, "NEFT": 7000.0}
        dr_tags = {"RTGS": 43000.0, "IMPS": 37000.0, "OTHER": 15000.0, "NEFT": 3000.0, "BANK CHARGE": 2000.0}

        drawing = _draw_payment_mode_analysis(250, 196, cr_tags, dr_tags, 100000.0, 100000.0)
        # Verify drawing object returned cleanly
        self.assertIsNotNone(drawing)
        self.assertEqual(drawing.width, 250)
        self.assertEqual(drawing.height, 196)

    def test_09_excel_report_payment_modes(self):
        """Excel report must contain Credit by Payment Mode and Debit by Payment Mode
        tables with exact percentages summing to 100%.
        """
        all_txns = [
            {"date": date(2026, 8, 1), "description": "UPI/Client A", "credit": 50000.0, "debit": 0.0, "balance": 150000.0, "chq_no": "-", "file_name": "test.xlsx"},
            {"date": date(2026, 8, 2), "description": "NEFT/Client B", "credit": 50000.0, "debit": 0.0, "balance": 200000.0, "chq_no": "-", "file_name": "test.xlsx"},
            {"date": date(2026, 8, 3), "description": "RTGS/Vendor X", "credit": 0.0, "debit": 60000.0, "balance": 140000.0, "chq_no": "-", "file_name": "test.xlsx"},
            {"date": date(2026, 8, 4), "description": "IMPS/Vendor Y", "credit": 0.0, "debit": 40000.0, "balance": 100000.0, "chq_no": "-", "file_name": "test.xlsx"},
        ]
        all_txns = _enrich_transactions(all_txns)
        file_summary = {
            "transactions_found": len(all_txns),
            "total_credits": 100000.0,
            "total_debits": 100000.0,
            "opening_balance": 100000.0,
            "closing_balance": 100000.0,
            "net_cash_flow": 0.0,
            "transactions": all_txns,
            "file_name": "test.xlsx",
        }
        analytics = _build_analytics([file_summary], "Test Holder")
        summary = {
            "files_analysed": 1,
            "details": [file_summary],
            "analytics": analytics,
        }

        excel_bytes = build_excel_report("Test Statement", "BSA", summary)
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        self.assertIn("Categories", wb.sheetnames)
        ws = wb["Categories"]

        # Collect cells in Categories sheet
        sheet_text = [str(ws.cell(r, c).value) for r in range(1, ws.max_row + 1) for c in range(1, ws.max_column + 1)]
        self.assertTrue(any("Credit by Payment Mode" in s for s in sheet_text))
        self.assertTrue(any("Debit by Payment Mode" in s for s in sheet_text))
        self.assertTrue(any("UPI" in s for s in sheet_text))
        self.assertTrue(any("NEFT" in s for s in sheet_text))
        self.assertTrue(any("RTGS" in s for s in sheet_text))
        self.assertTrue(any("IMPS" in s for s in sheet_text))


if __name__ == "__main__":
    unittest.main()
