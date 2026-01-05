import fitz

def create_pdfs():
    # 1. Create PDF with NO ToC
    doc1 = fitz.open()
    page = doc1.new_page()
    page.insert_text((50, 50), "This is a dummy PDF with NO Table of Contents.")
    doc1.save("test_files/dummy_no_toc.pdf")
    doc1.close()
    print("Created test_files/dummy_no_toc.pdf")

    # 2. Create PDF WITH ToC
    doc2 = fitz.open()
    # Page 1
    page1 = doc2.new_page()
    page1.insert_text((50, 50), "Chapter 1")
    # Page 2
    page2 = doc2.new_page()
    page2.insert_text((50, 50), "Chapter 2")
    
    # Add ToC
    # Format: [level, title, page_number]
    toc = [
        [1, "Chapter 1", 1],
        [1, "Chapter 2", 2]
    ]
    doc2.set_toc(toc)
    doc2.save("test_files/dummy_with_toc.pdf")
    doc2.close()
    print("Created test_files/dummy_with_toc.pdf")

if __name__ == "__main__":
    create_pdfs()
