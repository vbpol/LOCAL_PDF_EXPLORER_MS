import sys
import os
import glob

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', 'src')
sys.path.append(src_path)

from core.services.pdf_engine import PDFEngine

def test_toc_check():
    # 1. Define specific test files
    base_dir = os.path.join(current_dir, '..', 'test_files')
    target_files = [
        os.path.join(base_dir, 'dummy_no_toc.pdf'),
        os.path.join(base_dir, 'dummy_with_toc.pdf'),
        os.path.join(base_dir, 'report.pdf') # The invalid one, to test error handling
    ]
    
    # Resolve absolute paths
    target_files = [os.path.abspath(f) for f in target_files]

    print(f"Testing ToC detection on {len(target_files)} files...\n")
    print(f"{'Filename':<40} | {'Has ToC?':<10} | {'Path'}")
    print("-" * 80)

    for f in target_files:
        has_toc = PDFEngine.has_toc(f)
        status = "YES" if has_toc else "NO"
        filename = os.path.basename(f)
        # Truncate filename if too long
        if len(filename) > 38:
            filename = filename[:35] + "..."
            
        print(f"{filename:<40} | {status:<10} | {f}")

if __name__ == "__main__":
    test_toc_check()
