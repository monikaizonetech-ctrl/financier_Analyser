import sys
sys.path.insert(0, '.')
from app.services.file_analysis_service import _parse_pdf_transactions

rows = _parse_pdf_transactions('uploads/63cdbc6a-df7e-4240-a6d5-375850d7e1c5/Acct Statement_4115_01102026_14.55.03.pdf', 'hdfc.pdf')

# Known sets:
# 1. Credit card bill (1):
# 2. School fees (1):
# 3. Interest income (1):
# 4. Investment redemption (6):
# 5. ATM cash (3):
# 6. Dividend (12):
# 7. Investment (23):
# 8. Related party (11):

known = set()
for i, r in enumerate(rows):
    desc = r.get('description', '').upper()
    cr = float(r.get('credit') or 0)
    dr = float(r.get('debit') or 0)
    
    if 'IBBILLPAY' in desc:
        known.add(i)
    elif 'SCHOOL FEES' in desc:
        known.add(i)
    elif 'INTERESTPAIDTILL' in desc or 'INTEREST PAID' in desc:
        known.add(i)
    elif cr > 0 and ('TMFREDEMPTION' in desc or 'TATAMF' in desc):
        known.add(i)
    elif desc.startswith('ATW-'):
        known.add(i)
    elif cr > 0 and desc.startswith('ACH C-'):
        known.add(i)
    elif dr > 0 and any(k in desc for k in [
        'BSEMFA/C', 'KOTAKMF', 'HDFCMF', 'NIPPONINDMF', 'FTMF', 'BIRLAMF', 
        'NSECLEARING', 'SBISMSMFB', 'BNPPARIBASMF', 'UTIMFSMS', 'TATAMF', 
        'MIRAEMF', 'CAMSMUTUAL FUND', 'SBIMUTUAL FUND', 'WHITEOAKCAPITAL', 
        'BANDHAN28092026CAMS', 'FINNSECLEARINGLIM', 'HSLSECA/C'
    ]):
        known.add(i)
    elif any(k in desc for k in ['SSG', 'CREDITCARDBARROW', 'SOPHIADAISYRANI', 'SOPHIAMOHAN', 'MRSSOPHIADAISY']):
        known.add(i)

remaining = [(i, r) for i, r in enumerate(rows) if i not in known]
print(f"Remaining rows to categorize: {len(remaining)} (expected: 54 Person transfer + 7 Food + 5 Fuel + 3 Utilities + 3 Subscription = 72)")
print("=" * 80)
for idx, (i, r) in enumerate(remaining):
    flow = f"CR {r.get('credit', 0):,.2f}" if r.get('credit') else f"DR {r.get('debit', 0):,.2f}"
    print(f"[{i+1:3d}] {flow:14s} | {r.get('description')}")
