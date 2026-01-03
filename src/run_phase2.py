import sys
import os
import fitz # pymupdf

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.services.pdf_renderer import PDFRenderer

def create_dummy_pdf(path):
    """Creates a simple 1-page PDF for testing WITH a ToC."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Chapter 1 Content")
    
    # Add ToC: [level, title, page_num]
    # page_num is 1-based in fitz.set_toc? No, usually handles mapping. 
    # fitz.set_toc expects list of [lvl, title, page]
    toc = [
        [1, "Chapter 1", 1],
        [2, "Section 1.1", 1]
    ]
    doc.set_toc(toc)
    doc.save(path)
    doc.close()
    return path

def main():
    print("=== Phase 2 Validation: PDF Core Services ===")
    
    # Setup Test Artifact
    test_pdf = os.path.join(os.path.dirname(__file__), "phase2_test.pdf")
    create_dummy_pdf(test_pdf)
    print(f"[OK] Created dummy PDF: {test_pdf}")

    try:
        # 1. Test Page Count
        count = PDFRenderer.get_page_count(test_pdf)
        print(f"Page Count: {count}")
        assert count == 1, "Page count mismatch"
        print("[OK] Page Count Verified")

        # 2. Test Rendering
        img_data = PDFRenderer.render_page(test_pdf, 1)
        assert len(img_data) > 0, "Render produced empty bytes"
        print(f"[OK] Page Rendering Verified ({len(img_data)} bytes)")

        toc = PDFRenderer.get_toc(test_pdf)
        print(f"Extracted ToC: {toc}")
        assert isinstance(toc, list), "ToC should be a list"
        
        # Verify Key fields
        assert len(toc) == 1, f"Expected 1 Root Item (Nested), got {len(toc)}"
        root_item = toc[0]
        assert root_item['title'] == "Chapter 1", "Root title mismatch"
        assert len(root_item['children']) == 1, "Root should have 1 child"
        assert root_item['children'][0]['title'] == "Section 1.1", "Child title mismatch"
        
        print(f"[OK] ToC Extraction & Nesting Verified")

    except Exception as e:
        print(f"[FAIL] Validation Failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if os.path.exists(test_pdf):
            os.remove(test_pdf)
            print("[OK] Cleanup Complete")

    print("=== Phase 2 Validation Complete ===")

if __name__ == "__main__":
    main()
