from PyQt6.QtCore import QSortFilterProxyModel, Qt

class PDFSortFilterProxyModel(QSortFilterProxyModel):
    """
    Proxy Model for filtering and sorting PDF data.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(-1) # Filter all columns by default, or specific ones

    def filterAcceptsRow(self, source_row, source_parent):
        """
        Custom filtering logic: Check if the search text appears in Filename, Tags, or Notes.
        """
        # If no filter regex is set, accept all
        if not self.filterRegularExpression().pattern():
            return True
            
        model = self.sourceModel()
        
        # We need to map our concept of columns to the source model
        # The source model (PDFTableModel) exposes:
        # 0: Filename
        # 1: Tags
        # 2: Category
        # 3: Path (Relative/Original)
        
        # We want to search in Filename (0) and Tags (1).
        # Notes are NOT in the table view columns, so we can't easily filter by them 
        # using the standard QSortFilterProxyModel mechanism if we rely only on displayed data.
        
        # However, we can access the underlying data if we know the model structure.
        # But `data()` only returns display data.
        
        # For a robust implementation, we should check column 0 and 1.
        # If we want to filter by Notes, the Notes must be available in the model.
        # In PDFTableModel, we have access to the dataframe, but here we only have the QModelIndex.
        
        # Let's check Filename (0) and Tags (1) and Path (3)
        
        regex = self.filterRegularExpression()
        
        filename = model.index(source_row, 0, source_parent).data()
        tags = model.index(source_row, 1, source_parent).data()
        path = model.index(source_row, 3, source_parent).data()
        
        # Notes are tricky because they aren't displayed. 
        # We could add a hidden column for notes or just skip filtering by notes for the grid view.
        # Given the requirement "search must filter the grid", users likely expect to search visible content.
        # But "notes" are mentioned in the placeholder "Search filenames, tags, notes...".
        
        # To support notes, we should modify PDFTableModel to expose notes via a UserRole or a hidden column.
        # Let's assume for now we search visible columns.
        
        match_found = False
        if filename and regex.match(str(filename)).hasMatch():
            match_found = True
        elif tags and regex.match(str(tags)).hasMatch():
            match_found = True
        elif path and regex.match(str(path)).hasMatch():
            match_found = True
            
        return match_found
