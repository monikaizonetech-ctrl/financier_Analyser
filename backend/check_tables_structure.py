import pdfplumber
import re

file_path = r'uploads\c84379c7-9ffd-47e8-83b5-1a71b44cb6ea\GSTR-1-2018-2019.pdf'

all_pages_data = []
with pdfplumber.open(file_path) as pdf:
    for page_idx, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for tbl in (tables or []):
            if not tbl or len(tbl) < 2:
                continue
            all_pages_data.append((page_idx, tbl))

print(f"Total tables collected: {len(all_pages_data)}")
for p_idx, tbl in all_pages_data:
    print(f"Page {p_idx+1}: header: {tbl[0][:5]}")
