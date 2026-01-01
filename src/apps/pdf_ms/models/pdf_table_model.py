from PyQt6.QtCore import QAbstractTableModel, Qt, pyqtSignal

class PDFTableModel(QAbstractTableModel):
    """
    MVC Model: Wraps the Pandas DataFrame for the View.
    Follows Single Responsibility: Only handles data presentation logic.
    """
    
    def __init__(self, data=None):
        super().__init__()
        self._data = data
        self._headers = ["Filename", "Type", "Tags", "Category", "Path", "Actions"] # Added Type column

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
            # Headers: ["Filename", "Type", "Tags", "Category", "Path", "Actions"]
            
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
                if 'relative_path' in self._data.columns:
                    return str(self._data.iloc[row]['relative_path'])
                return str(self._data.iloc[row]['original_path'])
            elif col == 5:
                return "Action" # Placeholder text, will be painted by delegate
        
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
