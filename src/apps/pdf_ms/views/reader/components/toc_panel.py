from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QTextEdit, QLabel, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

class ToCPanel(QWidget):
    """
    Modular Left Panel for PDF Reader.
    Displays Table of Contents and handles Chapter Notes.
    """
    
    # Signals
    page_navigation_requested = pyqtSignal(int)
    save_toc_requested = pyqtSignal(list) # Emits the full ToC data structure with notes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.toc_data = []
        self.current_toc_item = None
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # ToC Tree
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("Table of Contents")
        self.toc_tree.setToolTip("Navigate the document structure")
        self.toc_tree.itemClicked.connect(self._on_toc_clicked)
        layout.addWidget(self.toc_tree, stretch=2)
        
        # Chapter Notes
        layout.addWidget(QLabel("Chapter Notes:"))
        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Select a chapter to add notes...")
        self.note_editor.setToolTip("Write notes specific to the selected chapter")
        self.note_editor.textChanged.connect(self._on_chapter_note_changed)
        layout.addWidget(self.note_editor, stretch=1)
        
        # Save Button
        self.btn_save_toc = QPushButton("Save Chapter Notes")
        self.btn_save_toc.setToolTip("Save all chapter notes to the database")
        self.btn_save_toc.clicked.connect(self._on_save_clicked)
        layout.addWidget(self.btn_save_toc)

    def load_toc(self, toc_data: list):
        """
        Load ToC data structure into the tree.
        toc_data: List of dicts with keys: title, page, children, user_note
        """
        self.toc_data = toc_data # Keep reference
        self.toc_tree.clear()
        self.note_editor.clear()
        self.current_toc_item = None
        
        def add_node(parent_menu, data):
            item = QTreeWidgetItem(parent_menu)
            item.setText(0, data.get('title', 'Untitled'))
            # Store reference to the mutable dict in the item
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            for child in data.get('children', []):
                add_node(item, child)
                
        for node in self.toc_data:
            add_node(self.toc_tree, node)
            
        self.toc_tree.expandAll()

    def _on_toc_clicked(self, item, column):
        self.current_toc_item = item
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data:
            # 1. Navigate
            page = data.get('page', 1)
            self.page_navigation_requested.emit(page)
            
            # 2. Load Note
            self.note_editor.blockSignals(True)
            self.note_editor.setText(data.get('user_note', ''))
            self.note_editor.blockSignals(False)

    def _on_chapter_note_changed(self):
        if self.current_toc_item:
            data = self.current_toc_item.data(0, Qt.ItemDataRole.UserRole)
            if data:
                # Update the in-memory data structure
                data['user_note'] = self.note_editor.toPlainText()
                # Re-set data just in case, though dict is mutable and passed by ref
                self.current_toc_item.setData(0, Qt.ItemDataRole.UserRole, data)

    def _on_save_clicked(self):
        if self.toc_data:
            self.save_toc_requested.emit(self.toc_data)
        else:
            # Maybe show warning if no ToC?
            pass
