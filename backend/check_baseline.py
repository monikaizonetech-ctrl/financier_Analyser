"""
Baseline check — run BEFORE any changes.
Tests A (IOB), C (HDFC), and prints actual vs expected.
"""
import sys, os
sys.path.insert(0, '.')

SEP = "=" * 60

def fmt(v, label=""):
    if v is None:
        return f"{label}: None"
    if isinstance(v, float):
        return f"{label}: {v:,.2f}"
    return f"{label}: {v}"

print(SEP)
print("BASELINE CHECK A — IOB statement")
print(SEP)

from app.services.file_analysis_service import _parse_pdf_transactions, analyse_bank_statement

iob_path = 'tests/fixtures/iob_2026-08-23_2026-09-23.pdf'
if not os.path.exists(iob_path):
    print("IOB file not found:", iob_path)
else:
    try:
        rows = _parse_pdf_transactions(iob_path, os.path.basename(iob_path))
        credits = [r for r in rows if (r.get('credit') or 0) > 0]
        debits  = [r for r in rows if (r.get('debit')  or 0) > 0]
        tc = sum(r.get('credit', 0) for r in credits)
        td = sum(r.get('debit', 0)  for r in debits)
        opening = rows[0].get('statement_opening_balance') if rows else None
        closing = rows[-1].get('balance') if rows else None
        holder  = rows[0].get('account_holder', 'N/A') if rows else 'N/A'
        print(f"Rows:    {len(rows)}   (expected 178)")
        print(f"Holder:  {holder}   (expected BAIRAVAPRAKASH PUGAZHENDHI)")
        print(fmt(opening, "Opening"))
        print("         expected  2,930.04")
        print(fmt(tc, "Credit"))
        print("         expected  15,779.00")
        print(fmt(td, "Debit"))
        print("         expected  17,475.25")
        print(fmt(closing, "Closing"))
        print("         expected  1,233.79")
    except Exception as e:
        import traceback; traceback.print_exc()

print()
print(SEP)
print("BASELINE CHECK C — HDFC statement")
print(SEP)

hdfc_path = 'uploads/63cdbc6a-df7e-4240-a6d5-375850d7e1c5/Acct Statement_4115_01102026_14.55.03.pdf'
if not os.path.exists(hdfc_path):
    print("HDFC file not found:", hdfc_path)
else:
    try:
        rows = _parse_pdf_transactions(hdfc_path, os.path.basename(hdfc_path))
        credits = [r for r in rows if (r.get('credit') or 0) > 0]
        debits  = [r for r in rows if (r.get('debit')  or 0) > 0]
        tc = sum(r.get('credit', 0) for r in credits)
        td = sum(r.get('debit', 0)  for r in debits)
        opening = rows[0].get('statement_opening_balance') if rows else None
        closing = rows[-1].get('balance') if rows else None
        holder  = rows[0].get('account_holder', 'N/A') if rows else 'N/A'
        print(f"Rows:    {len(rows)}   (expected 130)")
        print(f"Credits: {len(credits)}   (expected 29)")
        print(f"Debits:  {len(debits)}   (expected 101)")
        print(f"Holder:  {holder}   (expected MR. G MOHAN)")
        print(fmt(opening, "Opening"))
        print("         expected  57,598.70")
        print(fmt(tc, "Credit"))
        print("         expected  653,815.01")
        print(fmt(td, "Debit"))
        print("         expected  561,355.18")
        print(fmt(closing, "Closing"))
        print("         expected  150,058.53")

        # Check for narration contamination
        for r in rows:
            desc = r.get('description', '')
            if 'HDFC BANK LIMITED' in desc or '446 days' in desc or 'A TO Z S' in desc:
                print(f"  !! Narration contamination in row: {desc[:80]}")
        print("Narration contamination check done")
    except Exception as e:
        import traceback; traceback.print_exc()
