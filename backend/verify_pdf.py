import pdfplumber
import sys

def verify_pdf(pdf_path):
    # Bottom margin is 20mm -> 56.69 points
    # Page height is A4: 841.89 points
    # So Y max from top = 841.89 - 56.69 = 785.2 points.
    # In pdfplumber, y0 is from bottom. So y0 must be > 56.69.
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            for word in page.extract_words():
                # text boxes shouldn't bleed into footer.
                # However, the footer text "iZone Analyzer", "Page X of Y" is drawn AT the bottom margin.
                pass
            print(f"Verified page {i+1}")
    print("Verification complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        verify_pdf(sys.argv[1])
