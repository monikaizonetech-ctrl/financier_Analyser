import sys
sys.path.insert(0, '.')
from app.services.file_analysis_service import _parse_pdf_transactions

rows = _parse_pdf_transactions('uploads/63cdbc6a-df7e-4240-a6d5-375850d7e1c5/Acct Statement_4115_01102026_14.55.03.pdf', 'hdfc.pdf')

for i, r in enumerate(rows):
    desc = r.get('description', '').upper()
    if 'HELAN' in desc or 'KVBL0001262' in desc:
        d = r.get('debit') or r.get('credit')
        print(f"Row {i+1:3d}: {d:10.2f} | {desc}")
