import os
import pytest
from app.services.file_analysis_service import _parse_transactions, _enrich_transactions, _build_analytics

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "iob_2026-08-23_2026-09-23.pdf")

@pytest.fixture(scope="module")
def analytics_result():
    if not os.path.exists(FIXTURE_PATH):
        pytest.skip(f"Fixture not found: {FIXTURE_PATH}")
    rows = _parse_transactions(FIXTURE_PATH, "iob_2026-08-23_2026-09-23.pdf")
    enriched = _enrich_transactions(rows)
    return _build_analytics([{"file_name": "iob_2026-08-23_2026-09-23.pdf", "transactions": enriched}], "BAIRAVAPRAKASH PUGAZHENDHI")

def test_account_holder(analytics_result):
    assert analytics_result["account_holder"] == "BAIRAVAPRAKASH PUGAZHENDHI"

def test_account_holder_raw():
    from app.services.pdf_extractor import extract_document_metadata, ExtractedDocument, ExtractedPage, ExtractedLine, ExtractedWord
    lines = [
        "Account No",
        "Account Holder Name",
        "Contact No",
        "Email ID",
        "IFS Code",
        ": 283101000009528",
        ": BAIRAVAPRAKASH",
        "PUGAZHENDHI",
        ": 919994719782"
    ]
    extracted_lines = []
    for i, t in enumerate(lines):
        words = []
        if i >= 5:
            # For the values, give them an x0 of 180 so they are picked up by the positional logic
            for w in t.split():
                words.append(ExtractedWord(text=w, x0=180, x1=200, top=0, bottom=0))
        extracted_lines.append(ExtractedLine(line_number=i, text=t, y_top=0, y_bottom=0, words=words))
    
    page = ExtractedPage(page_number=1, width=800, height=1000, lines=extracted_lines, raw_text="\n".join(lines), character_count=100)
    doc = ExtractedDocument(file_path="test.pdf", file_name="test.pdf", pages=[page])
    meta = extract_document_metadata(doc)
    assert meta["account_holder"] == "BAIRAVAPRAKASH PUGAZHENDHI"
    assert meta["account_no"] == "283101000009528"

def test_own_transfers(analytics_result):
    vm = analytics_result["repayment_capacity"]["validation_metrics"]
    assert vm["ignored_own_account_dr"] == 350.00
    assert vm["ignored_own_account_cr"] == 310.00

def test_pass_through(analytics_result):
    vm = analytics_result["repayment_capacity"]["validation_metrics"]
    assert vm["pass_through_excluded_cr"] == 7200.00
    assert vm["pass_through_excluded_dr"] == 6500.00

def test_income_and_expense_totals(analytics_result):
    rc = analytics_result["repayment_capacity"]
    assert rc["verified_income"] == 8269.00
    assert rc["income_label"] == "Estimated (52% classified)"
    assert rc["verified_living_expenses"] == 10625.25

def test_monthly_averages(analytics_result):
    rc = analytics_result["repayment_capacity"]
    assert round(rc["average_monthly_income"], 2) == 7752.19
    assert round(rc["average_monthly_living_expenses"], 2) == 9961.17
    assert round(rc["net_disposable_income"], 2) == -2208.98
    assert round(rc["maximum_additional_emi"], 2) == 0.00 # max_additional_EMI
    assert rc["status"]["title"] == "No Additional EMI Capacity"

def test_top_counterparties(analytics_result):
    top_cr = analytics_result.get("cp_credit", {})
    names = sorted(top_cr.keys(), key=lambda k: -top_cr[k]["amount"])[:5]
    assert names == ["THARANKANI PUG", "Prithiviraj S", "BALAJI B", "BLINK COMM", "PRASATH B"]
    b_comm = top_cr["BLINK COMM"]
    assert round(b_comm["amount"], 2) == 435.00

def test_recurring_debits(analytics_result):
    rec = analytics_result["recurring_debits"]
    names = [r["counterparty"] for r in rec]
    
    assert "Jio" in names
    assert next(r for r in rec if r["counterparty"] == "Jio")["count"] == 2
    
    assert "Kirubakar Tea" in names
    assert next(r for r in rec if r["counterparty"] == "Kirubakar Tea")["count"] == 9
    
    assert "Chai Factory" in names
    assert next(r for r in rec if r["counterparty"] == "Chai Factory")["count"] == 13
    
    assert "Joshas Pick N" in names
    assert "Narayanan Co" in names
    assert next(r for r in rec if r["counterparty"] == "Narayanan Co")["count"] == 6
    assert "Senthil Kumara" in names
    assert next(r for r in rec if r["counterparty"] == "Senthil Kumara")["count"] == 5
    assert "Prasath B" in names
    
    # Must NOT appear
    assert "ANANTHAM KUMAR" not in names
    assert "DR" not in names
    assert "CR" not in names

def test_categories(analytics_result):
    cats = analytics_result["cat_totals_debit"]
    assert "Medical" in cats
    med = cats["Medical"]
    assert round(med["amount"], 2) == 136.25

def test_risk_flags(analytics_result):
    flags = analytics_result.get("unusual_txns", [])
    types = [f["type"] for f in flags]
    assert "Pass-through" in types
    assert "Low balance" in types
    assert "Possible duplicate debits" in types
    assert "Own-account transfers" in types
    assert "High activity" in types
    # Ensure exact strings (rough check)
    pt = next(f for f in flags if f["type"] == "Pass-through")
    assert "22 Sep" in pt["description"]
    assert pt["severity"] == "High"
    ha = next(f for f in flags if f["type"] == "High activity")
    assert "18 transactions" in ha["description"]

def test_cashflow_decimals(analytics_result):
    # Just checking the raw totals have the right values to be formatted
    m_aug = analytics_result["monthly"]["Aug 2026"]
    assert round(m_aug["credit"], 2) == 1307.00
    assert round(m_aug["debit"], 2) == 4231.00
    m_sep = analytics_result["monthly"]["Sep 2026"]
    assert round(m_sep["credit"], 2) == 14472.00
    assert round(m_sep["debit"], 2) == 13244.25
    assert round(analytics_result["total_credit"], 2) == 15779.00
    assert round(analytics_result["total_debit"], 2) == 17475.25
