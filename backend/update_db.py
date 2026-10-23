import sys, json
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models.report import Report, ReportFile, ReportType
from app.services.file_analysis_service import run_analysis
from datetime import datetime

db = SessionLocal()
report = db.query(Report).filter(Report.id == '63cdbc6a-df7e-4240-a6d5-375850d7e1c5').first()

if not report:
    print('Report not found!')
else:
    print(f'Found report: {report.name} (ID: {report.id})')
    print(f'Files: {[f.file_name for f in report.files]}')
    
    pdf_path = 'uploads/63cdbc6a-df7e-4240-a6d5-375850d7e1c5/Acct Statement_4115_01102026_14.55.03.pdf'
    
    print()
    print('Running fresh analysis with fixed parser...')
    summary = run_analysis(
        ReportType.BSA,
        [pdf_path],
        account_holder='MR. G MOHAN',
    )
    
    a = summary.get('analytics', {})
    print()
    print(f'Account Holder: {a.get("account_holder")}')
    print(f'Opening Balance: {a.get("opening_balance"):,.2f}')
    print(f'Total Credit: {a.get("total_credit"):,.2f}')
    print(f'Total Debit: {a.get("total_debit"):,.2f}')
    print(f'Closing Balance: {a.get("closing_balance"):,.2f}')
    print(f'Validation Status: {a.get("validation_status")}')
    
    # Update the database
    report.result_summary = summary
    report.analysed_at = datetime.utcnow()
    
    # Update file metadata
    for f in report.files:
        f.account_holder = 'MR. G MOHAN'
        f.bank_name = 'HDFC BANK'
        f.year = '01/09/2026 to 30/09/2026'
        f.sub_type = 'Savings'
        f.masked_account_no = 'XXXX XXXX 4115'
    
    db.commit()
    db.refresh(report)
    print()
    print('Database updated successfully!')
    print(f'Report status: {report.status}')
    print(f'File account_holder: {report.files[0].account_holder if report.files else "N/A"}')
    print(f'File masked_account_no: {report.files[0].masked_account_no if report.files else "N/A"}')
    print(f'File bank_name: {report.files[0].bank_name if report.files else "N/A"}')
    print(f'File year: {report.files[0].year if report.files else "N/A"}')
