import sys
sys.path.insert(0, '.')
from app.services.file_analysis_service import _parse_pdf_transactions

rows = _parse_pdf_transactions('uploads/63cdbc6a-df7e-4240-a6d5-375850d7e1c5/Acct Statement_4115_01102026_14.55.03.pdf', 'hdfc.pdf')

print(f"Total rows: {len(rows)}")
for i, r in enumerate(rows):
    desc = r.get('description', '').upper()
    cr = r.get('credit') or 0
    dr = r.get('debit') or 0
    flow = f"CR {cr:,.2f}" if cr else f"DR {dr:,.2f}"
    print(f"[{i+1:3d}] {flow:14s} | {desc}")
