import fitz  # PyMuPDF
import os

class PDFEngine:
    """
    Scalable engine for PDF operations using PyMuPDF (fitz).
    """
    
    @staticmethod
    def has_toc(file_path: str) -> bool:
        """
        Check if the PDF at file_path has an embedded Table of Contents (Outline).
        
        Args:
            file_path (str): Absolute path to the PDF file.
            
        Returns:
            bool: True if ToC exists, False otherwise (or if error).
        """
        if not os.path.exists(file_path):
            return False
        
        if not file_path.lower().endswith('.pdf'):
            return False
            
        try:
            doc = fitz.open(file_path)
            # get_toc(simple=True) returns a list. If list is empty, no ToC.
            toc = doc.get_toc(simple=True)
            doc.close()
            return len(toc) > 0
        except Exception as e:
            # In production, use a logger instead of print
            print(f"Error checking ToC for {file_path}: {e}")
            return False

    @staticmethod
    def extract_toc(file_path: str):
        """
        Extract the Table of Contents from the PDF and return a nested dictionary structure.
        """
        if not os.path.exists(file_path):
            return []
            
        if not file_path.lower().endswith('.pdf'):
            return []
            
        try:
            doc = fitz.open(file_path)
            toc_raw = doc.get_toc(simple=False)
            doc.close()
            
            # Convert flat list to nested tree
            # PyMuPDF toc: [[lvl, title, page, ...], ...]
            # lvl is 1-based hierarchy level.
            
            toc_tree = []
            stack = [] # [(level, node_dict)]

            for item in toc_raw:
                lvl, title, page = item[0], item[1], item[2]
                dest = item[3] if len(item) > 3 else None
                
                # Extract Y coordinate if available in dest
                dest_y = 0
                if dest and isinstance(dest, dict) and 'to' in dest:
                    try:
                        # 'to' is usually a fitz.Point(x, y)
                        dest_y = dest['to'].y
                    except:
                        pass
                
                node = {
                    "title": title,
                    "page": page,
                    "dest_y": dest_y,
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
        except Exception as e:
            print(f"Error extracting ToC for {file_path}: {e}")
            return []
