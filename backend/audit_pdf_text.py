import sys
sys.path.insert(0, '.')
import pymupdf

doc = pymupdf.open('test_mohan_v2.pdf')
full_text = ""
for page_num, page in enumerate(doc):
    text = page.get_text()
    full_text += f"\n--- PAGE {page_num + 1} ---\n" + text

prohibited = [
    "446",
    "437",
    "199,214",
    "7364831226",
    "A TO Z S",
    "Closing balance includes",
    "GSTN",
    "Registered Office",
]

print("=== PROHIBITED STRINGS AUDIT ===")
found_any = False
for p in prohibited:
    if p in full_text:
        print(f"FAILED: Found prohibited string {p!r}")
        found_any = True
    else:
        print(f"PASSED: {p!r} not found")

if not found_any:
    print("\nALL PROHIBITED STRING CHECKS PASSED CLEANLY!")
else:
    print("\nSOME PROHIBITED STRINGS WERE FOUND!")

# Let's check Authenticity text on Page 1 / Overview
print("\n=== PAGE 1 / OVERVIEW TEXT SAMPLE ===")
print(doc[0].get_text()[:600])

# Let's check Page 2 or Repayment Capacity page
for i, page in enumerate(doc):
    txt = page.get_text()
    if "Repayment Capacity" in txt or "SCENARIO" in txt:
        print(f"\n=== REPAYMENT CAPACITY PAGE (Page {i+1}) ===")
        print(txt)

doc.close()
