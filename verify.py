import sys
import os
sys.path.insert(0, os.path.abspath('backend'))

from app.services.file_analysis_service import run_analysis
import json

file_path = 'backend/uploads/0ed351e5-ad00-47f2-94d7-ed81f139e0c6/Account Statement.pdf'
from app.models import ReportType
result = run_analysis(ReportType.BSA, [file_path], 'BAIRAVAPRAKASH PUGAZHENDHI')

a = result['analytics']

print('HOLDER NAME:', a.get('account_holder'))

print('RECURRING DEBITS:')
for r in a.get('recurring_debits', []):
    print(f"- {r['counterparty']} (x{r['count']})")

dr_cat = a.get('cat_totals_debit', {})
med = dr_cat.get('Medical', {}).get('amount', 0.0)
print('MEDICAL CATEGORY AMOUNT:', med)

flags = a.get('unusual_txns', [])
for f in flags:
    print(f"FLAG: {f.get('type')} - {f.get('severity')} - {f.get('description')}")

cf = a.get('monthly', {})
for month, c in cf.items():
    print(f"MONTHLY AVG {month}: credit={c.get('total_credit', 0)}, debit={c.get('total_debit', 0)}, net={c.get('net_cash_flow', 0)}, avg_bal={c.get('avg_balance', 0)}")

rep = a.get('repayment_capacity', {})
print('MAX ADDITIONAL EMI:', rep.get('max_additional_emi', 0))

# Print Cashflow average decimals logic!
dur = a.get("duration_days", 30) or 30
cr_avg = (a.get('total_credit', 0) / dur) * 30
dr_avg = (a.get('total_debit', 0) / dur) * 30
net_avg = (a.get('net_cash_flow', 0) / dur) * 30
avg_bal = a.get('avg_balance', 0)
print(f"CASHFLOW MONTHLY AVG ROW: credit {cr_avg:,.2f}, debit {dr_avg:,.2f}, net {net_avg:,.2f}, avg balance {avg_bal:,.2f}")

# Print expected expense by category total
sum_exp = sum(v["amount"] for k, v in dr_cat.items()) - 350.0 - 6500.0
print("EXPENSE CATEGORY TOTAL (-own -pt):", sum_exp)

