import sys
sys.path.insert(0, '.')
from app.services.file_analysis_service import _parse_pdf_transactions

rows = _parse_pdf_transactions('uploads/63cdbc6a-df7e-4240-a6d5-375850d7e1c5/Acct Statement_4115_01102026_14.55.03.pdf', 'hdfc.pdf')
print(f"Total rows: {len(rows)}")
for i, r in enumerate(rows):
    cr = float(r.get('credit') or 0)
    dr = float(r.get('debit') or 0)
    desc = r.get('description', '')
    print(f"{i:3d} | {str(r.get('date'))} | CR: {cr:10.2f} | DR: {dr:10.2f} | {desc}")
