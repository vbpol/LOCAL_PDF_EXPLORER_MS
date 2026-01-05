import sys
import os
import fitz

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.services.pdf_renderer import PDFRenderer
from src.core.services.pdf_engine import PDFEngine

def main():
    print("Testing PDFRenderer & PDFEngine...")
    # Find a PDF to test
    root = os.path.dirname(os.path.abspath(__file__))
    # Walk to find a pdf
    target_pdf = None
    for r, d, f in os.walk(root):
        for file in f:
            if file.lower().endswith('.pdf'):
                target_pdf = os.path.join(r, file)
                break
        if target_pdf: break
    
    if not target_pdf:
        print("No PDF found for testing.")
        return

    print(f"Target: {target_pdf}")
    
    # Test ToC
    print("Extracting ToC...")
    toc = PDFEngine.extract_toc(target_pdf)
    print(f"ToC Items: {len(toc)}")
    if toc:
        print(f"Sample: {toc[0]}")

    # Test Render
    print("Rendering Page 1...")
    img = PDFRenderer.render_page(target_pdf, 1, zoom=0.5)
    print(f"Rendered Bytes: {len(img)}")
    assert len(img) > 0, "Render failed"
    print("PDFRenderer Test Passed.")

if __name__ == "__main__":
    main()
