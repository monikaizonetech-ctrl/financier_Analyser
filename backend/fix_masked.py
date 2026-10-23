import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models.report import Report
import re

def _mask_account_no(acc_no):
    if not acc_no: return 'XXXX XXXX XXXX'
    clean = str(acc_no).strip()
    if not clean: return 'XXXX XXXX XXXX'
    if 'X' in clean.upper(): return clean
    digits = re.sub(r'\D', '', clean)
    if len(digits) <= 4: return f'XXXX {digits}' if digits else 'XXXX XXXX XXXX'
    masked_raw = 'X' * (len(digits) - 4) + digits[-4:]
    pad = (4 - len(masked_raw) % 4) % 4
    masked_raw = 'X' * pad + masked_raw
    chunks = [masked_raw[i:i+4] for i in range(0, len(masked_raw), 4)]
    return ' '.join(chunks)

db = SessionLocal()
report = db.query(Report).filter(Report.id == '63cdbc6a-df7e-4240-a6d5-375850d7e1c5').first()

if report and report.result_summary:
    a = report.result_summary.get('analytics', {})
    # Update masked account number in analytics
    old_masked = a.get('masked_account_no')
    new_masked = _mask_account_no(a.get('account_no', ''))
    print(f'Old masked: {old_masked}')
    print(f'New masked: {new_masked}')
    
    a['masked_account_no'] = new_masked
    
    # Also update account_holder if still wrong
    if a.get('account_holder') == 'MR. GMOHAN':
        a['account_holder'] = 'MR. G MOHAN'
    
    # Need to set the full dict back (JSON column requires full replacement)
    import copy
    new_summary = copy.deepcopy(report.result_summary)
    new_summary['analytics']['masked_account_no'] = new_masked
    new_summary['analytics']['account_holder'] = a['account_holder']
    
    report.result_summary = new_summary
    db.commit()
    print(f'Updated! New masked_account_no: {new_summary["analytics"]["masked_account_no"]}')
    print(f'Updated! account_holder: {new_summary["analytics"]["account_holder"]}')
    
    # Also update file record
    for f in report.files:
        f.masked_account_no = 'XXXX XXXX XXXX 4115'
        f.account_holder = 'MR. G MOHAN'
    db.commit()
    print('File record updated too.')
else:
    print('Report not found or no summary!')
