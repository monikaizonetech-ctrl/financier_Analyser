import sys; sys.path.insert(0, r'c:\Users\IZONE 194\Downloads\Financier\backend')
from app.services.file_analysis_service import _parse_pdf_transactions
from app.services.repayment_service import calculate_repayment_capacity
from datetime import date
import json

txns = _parse_pdf_transactions(r'backend\uploads\938dd2e2-ad8e-4f87-947d-f67c83f3f76b\Account Statement.pdf', 'Account Statement.pdf')
rc = calculate_repayment_capacity(txns, date(2026, 8, 23), date(2026, 9, 23), True)

print("Date        Description                                     Credit       Classification")
print("-" * 80)
for t in txns:
    cr = float(t.get('credit') or 0.0)
    if cr > 0:
        desc = (t.get('description') or '')[:40].ljust(40)
        c_class = "INCOME"
        d = desc.lower()
        if "reversal" in d or "refund" in d or "bounce" in d or "return" in d or "dishonour" in d:
            c_class = "REFUND/REVERSAL"
        elif "internal" in d or "own account" in d or "transfer to own" in d or "self" in d:
            c_class = "OWN ACCOUNT TRANSFER"
        elif "loan" in d and not any(k in d for k in ("emi", "installment")):
            c_class = "LOAN DISBURSEMENT"
            
        print(f"{t['date']}  {desc}  ₹{cr:<10,.2f} {c_class}")
