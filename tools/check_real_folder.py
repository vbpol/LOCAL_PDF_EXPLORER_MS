import sys
import os
import glob

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', 'src')
sys.path.append(src_path)

from core.services.pdf_engine import PDFEngine

def check_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"Error: Folder not found: {folder_path}")
        return

    # Recursive search for PDFs
    # Note: glob with recursive=True requires ** pattern
    pdf_pattern = os.path.join(folder_path, "**", "*.pdf")
    pdf_files = glob.glob(pdf_pattern, recursive=True)
    
    if not pdf_files:
        print(f"No PDF files found in {folder_path}")
        return

    print(f"Scanning {len(pdf_files)} PDF files in: {folder_path}\n")
    print(f"{'Filename':<60} | {'Has ToC?':<10}")
    print("-" * 80)

    count_yes = 0
    count_no = 0

    for f in pdf_files:
        try:
            has_toc = PDFEngine.has_toc(f)
            status = "YES" if has_toc else "NO"
            
            if has_toc:
                count_yes += 1
            else:
                count_no += 1
                
            filename = os.path.basename(f)
            # Truncate filename if too long
            if len(filename) > 58:
                filename = filename[:55] + "..."
                
            print(f"{filename:<60} | {status:<10}")
        except Exception as e:
            print(f"Error processing {os.path.basename(f)}: {e}")

    print("-" * 80)
    print(f"Total: {len(pdf_files)} | With ToC: {count_yes} | Without ToC: {count_no}")

if __name__ == "__main__":
    target_folder = r"E:\AVEVA-TM docs\1D ENGINEERING"
    check_folder(target_folder)
