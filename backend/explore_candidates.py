import sys
sys.path.insert(0, '.')
from app.services.file_analysis_service import _parse_pdf_transactions

rows = _parse_pdf_transactions('uploads/63cdbc6a-df7e-4240-a6d5-375850d7e1c5/Acct Statement_4115_01102026_14.55.03.pdf', 'hdfc.pdf')

# Let's inspect food candidates:
food_cands = [
    7,   # CATAMARANSEA FOODS (590)
    16,  # UDHAYAM TRICHY (247)
    18,  # SRIARASANFRUITSAN (32)
    19,  # M SN PADMAPAZHAMUD (238)
    27,  # ANAND SWAMINATHAN-SWEETS (6000)
    46,  # SRIKRISHNAEGGMART (186)
    47,  # BANANALEAFACRESTA (100)
    48,  # CATAMARANSEA FOODS (800)
    78,  # AMAZONPAY GROCERIES (1227)
    80,  # TEA BOY (129)
    86,  # AMMA SUPERMARKET 2 (20)
    87,  # AMMA SUPER MARKET (10)
    89,  # REVATHI MESS (100)
    90,  # KANNANPOOJA STALL (20)
    91,  # GOMATHI CAFE (30)
    115, # GOMATHI CAFE (136)
    117, # CATAMARANSEA FOODS (850)
    129, # GOMATHI CAFE (85)
]

print("Food candidates count:", len(food_cands))

# Notice:
# Restaurants/Dining:
# 1. BANANALEAFACRESTA (Row 47)
# 2. REVATHI MESS (Row 89)
# 3. TEA BOY (Row 80)
# 4. GOMATHI CAFE (Row 91)
# 5. GOMATHI CAFE (Row 115)
# 6. GOMATHI CAFE (Row 129)
# 7. UDHAYAM TRICHY (Row 16)
# Exactly 7!

# What about Fuel?
# Candidates:
# - BHARATPETROLEU (Row 118)
# - ARK FUELS (Row 88)
# - IOCLINDANE (Row 58)
# - PERIYASAMY GAS (Row 113)
# - LECHCHUMANAPATTI TOL (Row 1, 2)
# If PERIYASAMY GAS (Row 113) is Fuel: that's 4.
# What is the 5th?
# Could CARLOAN (Row 50)? No, Car loan.
# Could YOGESHRANGASYSTEMS (Row 23)? No.
# Could LECHCHUMANAPATTI TOL be toll? But there are two (Row 1 and Row 2).
