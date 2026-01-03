from PyQt6.QtCore import QAbstractTableModel, Qt, pyqtSignal
import pandas as pd

class PDFTableModel(QAbstractTableModel):
    """
    MVC Model: Wraps the Pandas DataFrame for the View.
    Follows Single Responsibility: Only handles data presentation logic.
    """
    
    def __init__(self, data=None):
        super().__init__()
        self._data = data
        self._headers = ["Filename", "Type", "Tags", "Category", "Fav", "Bookmarks", "Path", "Actions"]

    def set_data(self, df):
        self.beginResetModel()
        self._data = df
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._data) if self._data is not None else 0

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or self._data is None:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            
            # Map column index to DataFrame column
            # Headers: ["Filename", "Type", "Tags", "Category", "Bookmarks", "Path", "Actions"]
            
            if col == 0:
                if 'filename_no_ext' in self._data.columns:
                    return str(self._data.iloc[row]['filename_no_ext'])
                return str(self._data.iloc[row]['filename'])
            elif col == 1:
                if 'file_type' in self._data.columns:
                    return str(self._data.iloc[row]['file_type'])
                return "PDF File"
            elif col == 2:
                tags = self._data.iloc[row]['tags']
                return tags if tags else ""
            elif col == 3:
                return str(self._data.iloc[row]['category'])
            elif col == 4:
                # Fav / User Bookmark
                if 'is_bookmarked' in self._data.columns:
                    val = self._data.iloc[row]['is_bookmarked']
                    return "★" if val else "☆"
                return "☆"
            elif col == 5:
                # Bookmarks Status
                if 'has_toc' in self._data.columns:
                    val = self._data.iloc[row]['has_toc']
                    has_toc = True if (val and val is not pd.NA) else False
                    return "✓ Yes" if has_toc else "✗ No"
                return "?"
            elif col == 6:
                if 'relative_path' in self._data.columns:
                    return str(self._data.iloc[row]['relative_path'])
                return str(self._data.iloc[row]['original_path'])
            elif col == 7:
                # Delegate handles painting, but we can return text for accessibility if needed
                return "" 
        
        elif role == Qt.ItemDataRole.UserRole:
            # Return enriched data for delegates
            row = index.row()
            has_toc = False
            if 'has_toc' in self._data.columns:
                val = self._data.iloc[row]['has_toc']
                has_toc = True if (val and val is not pd.NA) else False
            
            is_bookmarked = False
            if 'is_bookmarked' in self._data.columns:
                is_bookmarked = bool(self._data.iloc[row]['is_bookmarked'])
                
            return {
                'has_toc': has_toc,
                'is_bookmarked': is_bookmarked,
                'path': str(self._data.iloc[row]['original_path'])
            }
        
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._headers[section]
            else:
                return str(section + 1)
        return None

    def get_file_path_at(self, row):
        if self._data is not None and 0 <= row < len(self._data):
            return str(self._data.iloc[row]['original_path'])
        return None
