import fitz
import sys
import re

def verify_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        
        # 3. Extract PDF text. Fail if a header contains a file name or an ISO timestamp
        if re.search(r'\.pdf|\\.csv|\\.xlsx', text, re.IGNORECASE):
            print(f"FAIL: Page {page_num + 1} contains a file name!")
            sys.exit(1)
        if re.search(r'\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}', text):
            print(f"FAIL: Page {page_num + 1} contains an ISO timestamp!")
            sys.exit(1)
            
        # Fail if a number matches /-?\\d{6,}\\.\\d{2}/ without separators
        if re.search(r'-?\\d{6,}\\.\\d{2}', text):
            print(f"FAIL: Page {page_num + 1} contains raw unformatted float (e.g. 123456.00)!")
            sys.exit(1)
            
        # Fail if any page has fewer than 5 body lines (except the last)
        lines = [line.strip() for line in text.split('\\n') if line.strip()]
        if page_num < len(doc) - 1 and len(lines) < 5:
            print(f"FAIL: Page {page_num + 1} is nearly empty ({len(lines)} lines)!")
            sys.exit(1)
            
    print("Verification passed text checks!")
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_pdf.py <pdf_path>")
        sys.exit(1)
    verify_pdf(sys.argv[1])
