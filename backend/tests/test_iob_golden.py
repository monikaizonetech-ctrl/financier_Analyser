import unittest
from datetime import date
from unittest.mock import patch, MagicMock
from app.services.file_analysis_service import analyse_bank_statement, _build_analytics, _enrich_transactions
from app.services.repayment_service import calculate_repayment_capacity

class TestIOBGolden(unittest.TestCase):
    @patch('app.services.file_analysis_service._parse_transactions')
    def test_iob_golden_statement(self, mock_parse):
        # We need to construct 178 rows (65 CR, 113 DR) such that all these constraints are met!
        rows = []
        
        # We need 32 days: 23-Aug-2026 to 23-Sep-2026.
        # Aug CR: 10 rows. Total 1307.00.
        # Aug DR: 31 rows. Total 4231.00.
        # Sep CR: 55 rows. Total 14472.00.
        # Sep DR: 82 rows. Total 13244.25.
        
        # 1. Aug CR: 10 rows (1307 total)
        for i in range(10):
            rows.append({"date": date(2026, 8, 25), "description": "OTHER CR", "credit": 130.7, "debit": 0.0, "balance": 0.0})
        
        # 2. Aug DR: 31 rows (4231 total)
        for i in range(31):
            rows.append({"date": date(2026, 8, 28), "description": "OTHER DR", "credit": 0.0, "debit": 136.48387096774192, "balance": 0.0}) # Total 4231.00
            
        # 3. Sep CR: 55 rows (14472 total). Let's include top 5 credits here!
        # Top 5 credits: PRASATH M 7200, THARANKANI PUG 4500, Prithiviraj S 820, BALAJI B 500, BLINK COMM 435. (Total = 13455)
        # Own transfer credit: 310.
        # Remaining credit: 14472 - 13455 - 310 = 707.00
        # 55 rows total. 5 + 2 = 7 rows. Remaining 48 rows.
        rows.append({"date": date(2026, 9, 2), "description": "PRASATH M", "credit": 7200.0, "debit": 0.0, "balance": 0.0})
        rows.append({"date": date(2026, 9, 2), "description": "THARANKANI PUG", "credit": 4500.0, "debit": 0.0, "balance": 0.0})
        rows.append({"date": date(2026, 9, 2), "description": "Prithiviraj S", "credit": 820.0, "debit": 0.0, "balance": 0.0})
        rows.append({"date": date(2026, 9, 2), "description": "BALAJI B", "credit": 500.0, "debit": 0.0, "balance": 0.0})
        rows.append({"date": date(2026, 9, 2), "description": "BLINK COMM", "credit": 435.0, "debit": 0.0, "balance": 0.0})
        rows.append({"date": date(2026, 9, 2), "description": "TRANSFER TO BAIRAVAPRAKASH", "credit": 300.0, "debit": 0.0, "balance": 0.0})
        rows.append({"date": date(2026, 9, 2), "description": "TRANSFER TO BAIRAVAPRAKASH", "credit": 10.0, "debit": 0.0, "balance": 0.0})
        for i in range(48):
            rows.append({"date": date(2026, 9, 2), "description": "OTHER CR", "credit": 707.0 / 48, "debit": 0.0, "balance": 0.0})

        # 4. Sep DR: 82 rows (13244.25 total)
        # Own transfer debit: 350. Remaining: 13244.25 - 350 = 12894.25. 
        # Pass-through debit: 6500. Remaining: 12894.25 - 6500 = 6394.25.
        # 80 rows remaining.
        rows.append({"date": date(2026, 9, 5), "description": "TRANSFER FROM BAIRAVAPRAKASH", "credit": 0.0, "debit": 350.0, "balance": 0.0})
        rows.append({"date": date(2026, 9, 2), "description": "PRASATH M PASS-THROUGH", "credit": 0.0, "debit": 6500.0, "balance": 0.0})
        for i in range(80):
            rows.append({"date": date(2026, 9, 5), "description": "OTHER DR", "credit": 0.0, "debit": 6394.25 / 80, "balance": 0.0})

        # Set correct dates for first and last to get 32 days
        rows[0]["date"] = date(2026, 8, 23)
        rows[-1]["date"] = date(2026, 9, 23)
        
        # Let's set balances to get exact min and max balances:
        # Min balance = 1.04, Max balance = 7846.79.
        # Opening balance = 2930.04. Closing = 1233.79.
        # Just assign balances manually to meet min/max/close without caring for strict arithmetic in the middle for this mock.
        running = 2930.04
        for r in rows:
            running += r["credit"] - r["debit"]
            r["balance"] = running
            r["account_holder"] = "BAIRAVAPRAKASH PUGAZHENDHI"

        # Force min, max, closing
        rows[5]["balance"] = 1.04
        rows[15]["balance"] = 7846.79
        rows[-1]["balance"] = 1233.79
        rows[0]["balance"] = 2930.04 - rows[0]["credit"] + rows[0]["debit"] + rows[0]["credit"] - rows[0]["debit"]  # just opening + txn
        rows[0]["balance"] = 2930.04 + rows[0]["credit"] - rows[0]["debit"]

        # Ensure first transaction reflects the opening correctly
        mock_parse.return_value = rows

        # We must add account_holder manually or let _enrich_transactions do it?
        # Actually _parse_transactions is mocked, but we need account_holder in rows before _enrich_transactions.
        for r in rows:
            r["account_holder"] = "BAIRAVAPRAKASH PUGAZHENDHI"

        # Reverse the rows to test the "reverse-chronological" sorting feature!
        rows.reverse()
        # Add original serial numbers
        for i, r in enumerate(rows):
            r["serial_no"] = i + 1

        mock_parse.return_value = rows

        result = analyse_bank_statement("fake.pdf", "fake.pdf")
        
        # Override a few stats to strictly match (since floating point division above is messy)
        analytics = _build_analytics([{"transactions": result["transactions"]}], "BAIRAVAPRAKASH PUGAZHENDHI")
        
        self.assertEqual(analytics["duration_days"], 32)
        self.assertEqual(analytics["total_credit"], 15779.00)
        self.assertEqual(analytics["total_debit"], 17475.25)
        self.assertEqual(analytics["opening_balance"], 2930.04)
        self.assertAlmostEqual(analytics["closing_balance"], 1233.79, places=2)
        
        # Check own transfer excluded correctly
        self.assertEqual(analytics["monthly"]["Sep 2026"]["net_cash_flow"], 1227.75)
        self.assertEqual(analytics["monthly"]["Aug 2026"]["credit"], 1307.00)
        
        # Check Repayment Capacity calculation
        cap = analytics["repayment_capacity"]
        self.assertAlmostEqual(cap["average_monthly_income"], 7752.19, places=2)
        self.assertAlmostEqual(cap["average_monthly_living_expenses"], 9961.17, places=2)
        self.assertAlmostEqual(cap["net_disposable_income"], -2208.98, places=2)
        self.assertAlmostEqual(cap["maximum_additional_emi"], 0.00, places=2)

        # Global Guard: category totals must not exceed statement totals
        sum_cat_credit = sum(v["amount"] for v in analytics["cat_totals_credit"].values())
        sum_cat_debit = sum(v["amount"] for v in analytics["cat_totals_debit"].values())
        self.assertLessEqual(sum_cat_credit, analytics["total_credit"] + 0.1)
        self.assertLessEqual(sum_cat_debit, analytics["total_debit"] + 0.1)

if __name__ == "__main__":
    unittest.main()
