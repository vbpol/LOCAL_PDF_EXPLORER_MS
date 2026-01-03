import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class PDFRenderer:
    """
    Core Service for rendering PDF pages and extracting content.
    Designed to be UI-agnostic (returns bytes/dicts, not QImages/Widgets).
    """
    
    @staticmethod
    def get_toc(file_path: str) -> List[Dict]:
        """
        Extracts the Table of Contents (Bookmarks) from a PDF.
        Returns a list of dictionaries with 'title', 'page', and 'children' (if flattened) or nested structure.
        PyMuPDF returns: [lvl, title, page, dest]
        We convert this to a nested JSON-friendly format.
        """
        doc = fitz.open(file_path)
        toc_raw = doc.get_toc()
        doc.close()
        
        # Convert flat list to nested tree
        # PyMuPDF toc: [[lvl, title, page, ...], ...]
        # lvl is 1-based hierarchy level.
        
        toc_tree = []
        stack = [] # [(level, node_dict)]

        for item in toc_raw:
            lvl, title, page = item[0], item[1], item[2]
            node = {
                "title": title,
                "page": page,
                "children": [],
                "user_note": "" # Placeholder for user data
            }
            
            if lvl == 1:
                toc_tree.append(node)
                stack = [(1, node)]
            else:
                # Find parent
                while stack and stack[-1][0] >= lvl:
                    stack.pop()
                
                if stack:
                    parent_node = stack[-1][1]
                    parent_node["children"].append(node)
                    stack.append((lvl, node))
                else:
                    # Fallback if hierarchy is broken, treat as root
                    toc_tree.append(node)
                    stack = [(lvl, node)]
                    
        return toc_tree

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
