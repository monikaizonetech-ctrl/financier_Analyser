import pdfplumber
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python render_images.py <pdf_path>")
        return
    pdf_path = sys.argv[1]
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            img = page.to_image(resolution=150)
            img.save(f"page_{i+1}.png")
            print(f"Saved page_{i+1}.png")

if __name__ == "__main__":
    main()
