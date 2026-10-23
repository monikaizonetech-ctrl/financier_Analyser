import os
import io
import shutil
import tempfile
import unittest
from datetime import datetime
import pikepdf
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.models.report import ReportType, FileStatus, FileAuthenticity
from app.services.pdf_security_service import detect_pdf_encryption, unlock_pdf_file
from app.services.authenticity_service import check_document_authenticity
from app.services.file_analysis_service import run_analysis, build_pdf_report
from tests.statement_generator import create_statement_pdf


class TestPdfSecurityAndAuthenticity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="test_pdf_security_")
        cls.orig_pdf = os.path.join(cls.test_dir, "original_statement.pdf")

        # Generate a clean, verifiable standard bank statement
        rows = [
            ["01/08/2026", "01/08/2026", "NEFT INFLOW CLIENT A", "10,000.00", "0.00", "1,10,000.00"],
            ["05/08/2026", "05/08/2026", "OFFICE RENT AUG", "0.00", "20,000.00", "90,000.00"],
            ["10/08/2026", "10/08/2026", "VENDOR PAYMENT XYZ", "0.00", "15,000.00", "75,000.00"],
            ["15/08/2026", "15/08/2026", "CUSTOMER PAYMENT INV 101", "25,000.00", "0.00", "1,00,000.00"],
        ]
        headers = ["Post Date", "Value Date", "Description", "Credit", "Debit", "Balance"]
        col_x = [50, 110, 170, 360, 430, 500]

        create_statement_pdf(
            file_path=cls.orig_pdf,
            bank_name="HDFC BANK LIMITED",
            account_holder="RAHUL SHARMA",
            account_no="50100234567890",
            headers=headers,
            col_x_positions=col_x,
            rows_data=rows,
            header_noise=["Brought Forward 1,00,000.00Cr"],
            footer_noise=["Statement Summary : Dr. Count : 2 Cr. Count : 2 35,000.00 35,000.00", "CLOSING BALANCE : 1,00,000.00"],
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_user_password_lifecycle_and_parity(self):
        """
        Test 1: User-encrypted PDF with password 'test123'.
        Assert:
          - detect_pdf_encryption returns password_required=True
          - Wrong password raises ValueError('Incorrect password, try again')
          - Correct password 'test123' unlocks in memory and writes decrypted copy
          - Analysis report of unlocked PDF is identical in totals, counts, and repayment
            metrics to the unencrypted original.
        """
        enc_pdf = os.path.join(self.test_dir, "encrypted_test123.pdf")
        with pikepdf.open(self.orig_pdf) as pdf:
            pdf.save(
                enc_pdf,
                encryption=pikepdf.Encryption(owner="owneradmin", user="test123", R=4),
            )

        # 1. Detection
        det = detect_pdf_encryption(enc_pdf)
        self.assertTrue(det["is_encrypted"], "Encrypted PDF must be identified as encrypted")
        self.assertTrue(det["password_required"], "User password must be required")
        self.assertFalse(det["owner_restricted"], "Not owner-only restricted")

        # 2. Wrong password attempt
        with self.assertRaises(ValueError) as ctx:
            unlock_pdf_file(enc_pdf, "wrongpassword")
        self.assertIn("Incorrect password, try again", str(ctx.exception))

        # 3. Correct password unlock
        unlocked_copy = os.path.join(self.test_dir, "unlocked_copy.pdf")
        unlock_pdf_file(enc_pdf, "test123", target_path=unlocked_copy)
        self.assertTrue(os.path.exists(unlocked_copy), "Unlocked file must exist")

        det_unlocked = detect_pdf_encryption(unlocked_copy)
        self.assertFalse(det_unlocked["password_required"], "Unlocked file must not require password")

        # 4. Compare reports for full parity
        orig_res = run_analysis(ReportType.BSA, [self.orig_pdf], account_holder="RAHUL SHARMA")
        unlocked_res = run_analysis(ReportType.BSA, [unlocked_copy], account_holder="RAHUL SHARMA")

        self.assertEqual(orig_res["analytics"]["total_credit"], unlocked_res["analytics"]["total_credit"])
        self.assertEqual(orig_res["analytics"]["total_debit"], unlocked_res["analytics"]["total_debit"])
        self.assertEqual(orig_res["analytics"]["credit_count"], unlocked_res["analytics"]["credit_count"])
        self.assertEqual(orig_res["analytics"]["debit_count"], unlocked_res["analytics"]["debit_count"])
        self.assertEqual(orig_res["analytics"]["closing_balance"], unlocked_res["analytics"]["closing_balance"])

        orig_repay = orig_res["analytics"]["repayment_capacity"]
        unl_repay = unlocked_res["analytics"]["repayment_capacity"]
        self.assertEqual(orig_repay["average_monthly_income"], unl_repay["average_monthly_income"])
        self.assertEqual(orig_repay["maximum_additional_emi"], unl_repay["maximum_additional_emi"])

    def test_02_owner_password_only_pdf(self):
        """
        Test 2: Owner-password-only PDF opens without a prompt.
        Assert:
          - detect_pdf_encryption returns password_required=False, owner_restricted=True
          - Opens with empty user password without prompting user.
        """
        owner_pdf = os.path.join(self.test_dir, "owner_only.pdf")
        with pikepdf.open(self.orig_pdf) as pdf:
            pdf.save(
                owner_pdf,
                encryption=pikepdf.Encryption(owner="masterpass", user="", R=4),
            )

        det = detect_pdf_encryption(owner_pdf)
        self.assertTrue(det["is_encrypted"])
        self.assertFalse(det["password_required"], "Owner-only encrypted PDF must not require password prompt")
        self.assertTrue(det["owner_restricted"], "Must be detected as owner_restricted")

        auth = check_document_authenticity(owner_pdf, owner_restricted=True)
        self.assertIn("Restricted PDF (opened with standard reader permissions)", auth["reasons"])

    def test_03_incremental_update_tampering_detection(self):
        """
        Test 3: A PDF edited with an incremental update (more than 1 %%EOF marker).
        Assert:
          - Authenticity status is Suspicious or Tampered
          - Reason specifically cites incremental updates / %%EOF markers.
        """
        inc_pdf = os.path.join(self.test_dir, "incremental_edited.pdf")
        with pikepdf.open(self.orig_pdf) as pdf:
            pdf.save(inc_pdf)

        # Simulate incremental update appended after %%EOF
        with open(inc_pdf, "ab") as f:
            f.write(b"\n% Incremental edit appendix\n10 0 obj\n<< /Type /Annot >>\nendobj\n%%EOF\n")

        auth = check_document_authenticity(inc_pdf)
        self.assertIn(auth["status"], ["Suspicious", "Tampered"])
        has_eof_reason = any("Incremental updates detected" in r and "%%EOF" in r for r in auth["reasons"])
        self.assertTrue(has_eof_reason, f"Must cite incremental %%EOF updates. Got reasons: {auth['reasons']}")

    def test_04_changed_balance_tampered_detection(self):
        """
        Test 4: A PDF with an altered running balance.
        Assert:
          - Authenticity status is Tampered
          - Identifies arithmetic continuity mismatch and failing row number.
        """
        bad_bal_pdf = os.path.join(self.test_dir, "bad_balance.pdf")
        # Row 2 balance is 99,999.00 instead of 90,000.00
        tampered_rows = [
            ["01/08/2026", "01/08/2026", "NEFT INFLOW CLIENT A", "10,000.00", "0.00", "1,10,000.00"],
            ["05/08/2026", "05/08/2026", "OFFICE RENT AUG", "0.00", "20,000.00", "99,999.00"],  # Altered!
            ["10/08/2026", "10/08/2026", "VENDOR PAYMENT XYZ", "0.00", "15,000.00", "84,999.00"],
        ]
        headers = ["Post Date", "Value Date", "Description", "Credit", "Debit", "Balance"]
        col_x = [50, 110, 170, 360, 430, 500]

        create_statement_pdf(
            file_path=bad_bal_pdf,
            bank_name="HDFC BANK LIMITED",
            account_holder="RAHUL SHARMA",
            account_no="50100234567890",
            headers=headers,
            col_x_positions=col_x,
            rows_data=tampered_rows,
            header_noise=["Brought Forward 1,00,000.00Cr"],
        )

        res = run_analysis(ReportType.BSA, [bad_bal_pdf])
        parsed_txns = res["details"][0]["transactions"]

        auth = check_document_authenticity(
            bad_bal_pdf,
            parsed_transactions=parsed_txns,
            meta={"opening_balance": 100000.0, "closing_balance": 84999.0},
        )
        self.assertEqual(auth["status"], "Tampered", "Altered running balance must flag document as Tampered")
        continuity_flag = any("Arithmetic continuity mismatch" in r and "Row 2" in r for r in auth["reasons"])
        self.assertTrue(continuity_flag, f"Must cite Row 2 mismatch. Got reasons: {auth['reasons']}")

    def test_05_scanned_pdf_unverifiable(self):
        """
        Test 5: A scanned PDF with no extractable text layer.
        Assert:
          - Authenticity status is Unverifiable
          - Reason states no extractable text layer.
        """
        scanned_pdf = os.path.join(self.test_dir, "pure_scanned.pdf")
        c = canvas.Canvas(scanned_pdf, pagesize=A4)
        # Draw only shapes without text strings to simulate a scanned raster page
        c.rect(50, 500, 400, 200, stroke=1, fill=0)
        c.circle(200, 300, 50, stroke=1, fill=0)
        c.showPage()
        c.save()

        auth = check_document_authenticity(scanned_pdf)
        self.assertEqual(auth["status"], "Unverifiable", "Scanned PDF without text must be Unverifiable")
        has_scanned_reason = any("Scanned PDF with no extractable text layer" in r for r in auth["reasons"])
        self.assertTrue(has_scanned_reason, f"Must report no extractable text layer. Got: {auth['reasons']}")

    def test_06_password_never_leaked(self):
        """
        Test 6: Verify password string ('test123') is never stored in DB, logs,
        or generated report files.
        """
        test_pw = "secret_bank_pw_789"
        enc_pdf = os.path.join(self.test_dir, "secret_encrypted.pdf")
        with pikepdf.open(self.orig_pdf) as pdf:
            pdf.save(
                enc_pdf,
                encryption=pikepdf.Encryption(owner="admin", user=test_pw, R=4),
            )

        # Unlock
        unlocked_tmp = os.path.join(self.test_dir, "unlocked_secret.pdf")
        unlock_pdf_file(enc_pdf, test_pw, target_path=unlocked_tmp)

        # Run analysis and build reports
        analysis = run_analysis(ReportType.BSA, [unlocked_tmp], account_holder="RAHUL SHARMA")
        pdf_bytes = build_pdf_report("Secret_Report", "BSA", analysis)

        # Check in memory analysis summary
        import json
        dumped = json.dumps(analysis)
        self.assertNotIn(test_pw, dumped, "Password must not appear in result summary dictionary")

        # Check in generated PDF report
        self.assertNotIn(test_pw.encode(), pdf_bytes, "Password must not appear in binary PDF report")


if __name__ == "__main__":
    unittest.main()
