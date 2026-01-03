from PyQt6.QtWidgets import QTableView, QHeaderView, QAbstractItemView, QMenu, QInputDialog, QMessageBox, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor
from src.apps.pdf_ms.views.components.action_delegate import ActionDelegate

class PDFTableView(QTableView):
    """
    Enhanced Table View for PDF Management.
    Features:
    - Sortable columns
    - Alternating row colors
    - Context menu
    - Selection handling
    """
    
    # Signals
    file_open_requested = pyqtSignal(object) # Emits index
    folder_open_requested = pyqtSignal(object) # Emits index
    metadata_edit_requested = pyqtSignal(object) # Emits index
    file_rename_requested = pyqtSignal(object, str) # Emits index, new_name
    toc_action_requested = pyqtSignal(object) # Emits index (For Red/Green button)
    batch_toc_requested = pyqtSignal(list) # Emits list of indexes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        # Basic Appearance
        self.setAlternatingRowColors(True)
        self.setShowGrid(False) # Cleaner look
        self.setSortingEnabled(True)
        self.setMouseTracking(True) # Enable mouse tracking for hover effects in delegate
        
        # Selection Mode
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Headers
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        self.verticalHeader().setVisible(False) # Hide row numbers for cleaner look
        
    def setModel(self, model):
        """
        Override setModel to configure columns after model is loaded.
        """
        super().setModel(model)
        self.configure_columns()

    def configure_columns(self):
        """
        Configure column resize modes and widths.
        """
        header = self.horizontalHeader()
        # 0: Filename, 1: Type, 2: Tags, 3: Category, 4: Path, 5: Actions
        
        # Default behavior
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Specifics
        # Filename: Interactive/Stretch. 
        # User wants to resize, but usually filename should take available space.
        # If we set to Interactive, it won't auto-fill.
        # Let's keep it Interactive as requested "allow users to resize column width"
        # But we can set a large initial width.
        self.setColumnWidth(0, 300) 
        
        # Type: Resize to contents, but hidden by default
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.setColumnHidden(1, True) # Hidden by default
        
        # Tags & Category: Interactive
        self.setColumnWidth(2, 150)
        self.setColumnWidth(3, 100)
        
        # Bookmarks: Fixed small
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(4, 80)
        
        # Path: Interactive. Default width
        self.setColumnWidth(5, 300) # Default width for path
        
        # Actions: Fixed larger for 3 buttons
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(6, 120)
        
        # Context Menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Header Context Menu for Column Toggling
        self.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.show_header_menu)

        # Action Delegate
        self.action_delegate = ActionDelegate(self)
        self.setItemDelegateForColumn(6, self.action_delegate)
        self.action_delegate.action_requested.connect(self.on_action_requested)
        
        # Styling (CSS-like)
        self.setStyleSheet("""
            QTableView {
                background-color: #ffffff;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
                gridline-color: #e0e0e0;
            }
            QTableView::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: none;
                border-right: 1px solid #d0d0d0;
                border-bottom: 1px solid #d0d0d0;
            }
        """)

    def show_header_menu(self, position):
        """
        Show context menu for toggling column visibility.
        """
        menu = QMenu(self)
        
        model = self.model()
        if not model:
            return
            
        # Iterate over columns
        # Note: If using ProxyModel, we check columnCount of the view's model (which is proxy)
        column_count = model.columnCount()
        
        for col in range(column_count):
            header_text = model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            if not header_text:
                header_text = f"Column {col}"
                
            action = QAction(str(header_text), self)
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(col))
            action.setData(col) # Store column index
            action.triggered.connect(self.toggle_column)
            menu.addAction(action)
            
        menu.exec(self.horizontalHeader().mapToGlobal(position))

    def toggle_column(self):
        action = self.sender()
        if action:
            col = action.data()
            is_visible = action.isChecked()
            if is_visible:
                self.showColumn(col)
            else:
                self.hideColumn(col)

    def on_action_requested(self, row, action_type):
        """
        Handle clicks from Action Delegate.
        """
        model = self.model()
        index = model.index(row, 0)
        
        if action_type == 'open_file':
            self.file_open_requested.emit(index)
        elif action_type == 'open_folder':
            self.folder_open_requested.emit(index)
        elif action_type == 'toc_action':
            self.toc_action_requested.emit(index)

    def show_context_menu(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return
            
        menu = QMenu()
        
        # Open File
        act_open = QAction("Open File", self)
        act_open.triggered.connect(lambda: self.file_open_requested.emit(index))
        act_open.setToolTip("Open this file")
        menu.addAction(act_open)
        
        # Open Folder
        act_open_folder = QAction("Open Containing Folder", self)
        act_open_folder.triggered.connect(lambda: self.folder_open_requested.emit(index))
        act_open_folder.setToolTip("Open the folder containing this file")
        menu.addAction(act_open_folder)
        
        # Edit Metadata
        act_edit = QAction("Edit Metadata", self)
        act_edit.triggered.connect(lambda: self.metadata_edit_requested.emit(index))
        act_edit.setToolTip("Edit tags and notes for this file")
        menu.addAction(act_edit)
        
        # Rename File
        act_rename = QAction("Rename File", self)
        act_rename.triggered.connect(lambda: self.rename_file_dialog(index))
        act_rename.setToolTip("Rename the file")
        menu.addAction(act_rename)
        
        menu.addSeparator()
        
        # Batch ToC Generation (if multiple selected)
        selected_indexes = self.selectionModel().selectedRows()
        if len(selected_indexes) > 1:
            act_batch_toc = QAction(f"Generate ToC for {len(selected_indexes)} Selected Files", self)
            act_batch_toc.triggered.connect(lambda: self.batch_toc_requested.emit(selected_indexes))
            act_batch_toc.setToolTip("Generate Table of Contents for all selected PDFs")
            menu.addAction(act_batch_toc)
            menu.addSeparator()

        # Set Column Width
        col_index = index.column()
        current_width = self.columnWidth(col_index)
        act_col_width = QAction(f"Set Column Width (Current: {current_width})", self)
        act_col_width.triggered.connect(lambda: self.set_column_width_dialog(col_index))
        act_col_width.setToolTip("Manually set the width of this column")
        menu.addAction(act_col_width)
        
        menu.exec(self.viewport().mapToGlobal(position))

    def rename_file_dialog(self, index):
        """
        Show dialog to rename file.
        """
        # Get current filename from the view (which is filename_no_ext)
        current_name = index.sibling(index.row(), 0).data()
        if not current_name:
            current_name = ""
            
        new_name, ok = QInputDialog.getText(self, "Rename File", 
                                          "Enter new filename (without extension):",
                                          QLineEdit.EchoMode.Normal,
                                          current_name)
        if ok and new_name and new_name != current_name:
            self.file_rename_requested.emit(index, new_name)

    def set_column_width_dialog(self, col_index):
        """
        Show dialog to set column width.
        """
        current_width = self.columnWidth(col_index)
        new_width, ok = QInputDialog.getInt(self, "Set Column Width", 
                                            f"Enter width for column {col_index}:", 
                                            value=current_width, min=10, max=2000)
        if ok:
            self.setColumnWidth(col_index, new_width)
