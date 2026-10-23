import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models.report import Report
from app.services.file_analysis_service import build_pdf_report

db = SessionLocal()
report = db.query(Report).filter(Report.id == '63cdbc6a-df7e-4240-a6d5-375850d7e1c5').first()
a = report.result_summary.get('analytics', {})

print('Verifying stored summary:')
print('  account_holder:', a.get('account_holder'))
print('  bank_name:', a.get('bank_name'))
print('  masked_account_no:', a.get('masked_account_no'))
print('  opening_balance:', a.get('opening_balance'))
print('  total_credit:', a.get('total_credit'))
print('  total_debit:', a.get('total_debit'))
print('  closing_balance:', a.get('closing_balance'))
print('  validation_status:', a.get('validation_status'))
print()
print('Generating PDF from stored summary...')
pdf_bytes = build_pdf_report('mohan', 'BSA', report.result_summary)
with open('test_final_output.pdf', 'wb') as f:
    f.write(pdf_bytes)
print(f'PDF: test_final_output.pdf ({len(pdf_bytes)} bytes)')
print('Done!')
