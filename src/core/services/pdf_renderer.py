import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class PDFRenderer:
    """
    Core Service for rendering PDF pages and extracting content.
    Designed to be UI-agnostic (returns bytes/dicts, not QImages/Widgets).
    """
    
    @staticmethod
    def render_page(file_path: str, page_num: int, zoom: float = 1.0) -> bytes:
        """
        Renders a specific page to PNG bytes.
        page_num is 1-based (PyMuPDF uses 0-based).
        """
        try:
            doc = fitz.open(file_path)
            if page_num < 1 or page_num > doc.page_count:
                return b""
            
            page = doc.load_page(page_num - 1)
            
            # Zoom matrix
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img_bytes = pix.tobytes("png")
            doc.close()
            return img_bytes
        except Exception as e:
            print(f"Error rendering PDF: {e}")
            return b""

    @staticmethod
    def get_page_count(file_path: str) -> int:
        try:
            doc = fitz.open(file_path)
            count = doc.page_count
            doc.close()
            return count
        except:
            return 0
