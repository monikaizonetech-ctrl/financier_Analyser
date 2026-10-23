import sys
sys.path.insert(0, '.')
from app.services.file_analysis_service import _parse_pdf_transactions
from datetime import date

rows = _parse_pdf_transactions('uploads/63cdbc6a-df7e-4240-a6d5-375850d7e1c5/Acct Statement_4115_01102026_14.55.03.pdf', 'hdfc.pdf')

# Let's inspect the exact classification:
# Credits (29 rows, total 653,815.01)
# 1. Own-name token (Row 9): 4,130.00
# 2. Investment redemption (6 rows): 158,666.71
# 3. Related party credits (3 rows: SSG 100k, SSG 150k, Sophia 100k): 350,000.00
# 4. Borrowing credits (1 row: CREDITCARDBARROW): 100,000.00
# 5. Dividend credits (12 rows): 2,967.45
# 6. Interest income (1 row): 545.00
# 7. Other credits (6 rows):
#    - Row 10: 217.85 (BAJAJ FINANCIAL)
#    - Row 33: 20,000.00 (PRAVEEN KUMAR)
#    - Row 41: 688.00 (CONNECTORPAYOUT GURUMOORTHY MOHAN)
#    - Row 75: 1,000.00 (MRSSOPHIADAISY RAN)
#    - Row 85: 15,600.00 (WINWAY COMPUTERS)
#    Wait! 2,967.45 + 545.00 + 217.85 + 20,000.00 + 688.00 + 1,000.00 + 15,600.00 = 41,018.30!
# EXACTLY 41,018.30!
#
# Debits (101 rows, total 561,355.18):
# - Investment debits (23 rows): 221,158.83
# - Living expenses (78 rows): 340,196.35
# Sum = 221,158.83 + 340,196.35 = 561,355.18!

cr_total = sum(float(r.get('credit') or 0) for r in rows)
dr_total = sum(float(r.get('debit') or 0) for r in rows)

print(f"Credit total: {cr_total:,.2f}")
print(f"Debit total:  {dr_total:,.2f}")

income_a = cr_total - 4130.00
exp_a = dr_total - 221158.83
net_a = income_a - exp_a
foir_cap_a = income_a * 0.50
max_emi_a = min(foir_cap_a, net_a)

print("\n--- Scenario (a) ---")
print(f"Income:   {income_a:,.2f}  (expected: 649,685.01)")
print(f"Expenses: {exp_a:,.2f}  (expected: 340,196.35)")
print(f"Net:      {net_a:,.2f}  (expected: 309,488.66)")
print(f"FOIR Cap: {foir_cap_a:,.2f}  (expected: 324,842.50)")
print(f"Max EMI:  {max_emi_a:,.2f}  (expected: 309,488.66)")

income_b = 41018.30
exp_b = exp_a
net_b = income_b - exp_b
foir_cap_b = income_b * 0.50
max_emi_b = 0.00

print("\n--- Scenario (b) ---")
print(f"Income:   {income_b:,.2f}  (expected: 41,018.30)")
print(f"Expenses: {exp_b:,.2f}  (expected: 340,196.35)")
print(f"Net:      {net_b:,.2f}  (expected: -299,178.05)")
print(f"FOIR Cap: {foir_cap_b:,.2f}  (expected: 20,509.15)")
print(f"Max EMI:  {max_emi_b:,.2f}  (expected: 0.00)")
