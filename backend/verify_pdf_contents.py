import pdfplumber
import sys

with pdfplumber.open('test_gstr3b_verified.pdf') as pdf:
    full_text = ''
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ''
        full_text += f'\n--- PAGE {i+1} ---\n' + text
        if '328,817' in text:
            print(f'ERROR: Found 328,817 on page {i+1}')
        if 'Utilization Rate: 0.0%' in text or ('Utilization Rate' in text and '0.0%' in text):
            print(f'ERROR: Found Utilization Rate 0.0% on page {i+1}')

print('Forbidden string search finished.')

checks = [
    '328,826.00',
    '81,941.55',
    '246,884.45',
    'drawn from opening credit ledger',
    'Cannot assess repayment capacity',
    '69.35%',
    '24.92%',
    '328,825.34'
]

for c in checks:
    found = c.lower() in full_text.lower()
    print(f'Check "{c}": {"FOUND" if found else "NOT FOUND"}')
