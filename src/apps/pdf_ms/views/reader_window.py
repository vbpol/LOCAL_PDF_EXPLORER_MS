from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QTreeWidget, QTreeWidgetItem, QTextEdit, QLabel, QScrollArea,
    QToolBar, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
import json

from src.core.services.pdf_renderer import PDFRenderer
from src.core.services.pdf_engine import PDFEngine
from src.apps.pdf_ms.views.metadata_view import MetadataView

class ReaderWindow(QMainWindow):
    """
    Integrated PDF Reader Window (Pro Version).
    Left: ToC and Notes using QTreeWidget.
    Center: PDF Page View.
    Right: File Metadata (Tags/Notes).
    """
    
    def __init__(self, file_path, core_app, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.core_app = core_app # Inject CoreApp for persistence
        
        self.setWindowTitle(f"Reader: {file_path}")
        self.resize(1200, 800)
        
        self.current_page = 1
        self.total_pages = PDFRenderer.get_page_count(file_path)
        self.zoom_level = 1.0
        self.toc_data = [] # Store current ToC state in memory
        self.current_toc_item = None # Currently selected QTreeWidgetItem
        
        self.init_ui()
        self.load_toc()
        self.load_metadata()
        self.render_current_page()

    def init_ui(self):
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # --- LEFT PANEL (ToC & Chapter Notes) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("Table of Contents")
        self.toc_tree.setToolTip("Navigate the document structure")
        self.toc_tree.itemClicked.connect(self.on_toc_clicked)
        left_layout.addWidget(self.toc_tree, stretch=2)
        
        left_layout.addWidget(QLabel("Chapter Notes:"))
        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Select a chapter to add notes...")
        self.note_editor.setToolTip("Write notes specific to the selected chapter")
        self.note_editor.textChanged.connect(self.on_chapter_note_changed)
        left_layout.addWidget(self.note_editor, stretch=1)
        
        # Save ToC Button
        self.btn_save_toc = QPushButton("Save Chapter Notes")
        self.btn_save_toc.setToolTip("Save all chapter notes to the database")
        self.btn_save_toc.clicked.connect(self.save_toc_to_db)
        # self.btn_save_toc.setEnabled(False) # Enable only on change? strictly simpler to always enable
        left_layout.addWidget(self.btn_save_toc)
        
        splitter.addWidget(left_panel)
        
        # --- CENTER PANEL (Reader) ---
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_prev = QPushButton("<")
        self.btn_prev.setToolTip("Previous Page (Left Arrow)")
        self.btn_prev.clicked.connect(self.prev_page)
        self.lbl_page = QLabel(f"Page {self.current_page} / {self.total_pages}")
        self.btn_next = QPushButton(">")
        self.btn_next.setToolTip("Next Page (Right Arrow)")
        self.btn_next.clicked.connect(self.next_page)
        
        toolbar.addWidget(self.btn_prev)
        toolbar.addWidget(self.lbl_page)
        toolbar.addWidget(self.btn_next)
        toolbar.addStretch()
        
        center_layout.addLayout(toolbar)
        
        # Scroll Area for Image
        self.scroll_area = QScrollArea()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        center_layout.addWidget(self.scroll_area)
        
        splitter.addWidget(center_panel)
        
        # --- RIGHT PANEL (File Metadata) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.metadata_view = MetadataView()
        self.metadata_view.save_requested.connect(self.save_file_metadata)
        right_layout.addWidget(self.metadata_view)
        
        splitter.addWidget(right_panel)
        
        # Set Sizes (Left, Center, Right)
        splitter.setSizes([250, 600, 250])

    def load_toc(self):
        # 1. Try Load from DB first (Persistence)
        db_meta = self.core_app.pdf_manager.get_metadata(self.file_path)
        bookmarks_json = db_meta.get('bookmarks', '')
        
        if bookmarks_json:
            try:
                self.toc_data = json.loads(bookmarks_json)
            except:
                self.toc_data = []
        
        # 2. If DB empty, Extract from PDF
        if not self.toc_data:
            self.toc_data = PDFEngine.extract_toc(self.file_path)
            # Auto-save initial extraction to DB? No, wait for user to save notes or explicit action.
            # But spec said "Check DB... If empty extract".
            # For now, we just use extracted.
        
        self.toc_tree.clear()
        
        def add_node(parent_menu, data):
            item = QTreeWidgetItem(parent_menu)
            item.setText(0, data['title'])
            item.setData(0, Qt.ItemDataRole.UserRole, data) # Store full node data reference
            
            for child in data.get('children', []):
                add_node(item, child)
                
        for node in self.toc_data:
            add_node(self.toc_tree, node)
            
        self.toc_tree.expandAll()

    def load_metadata(self):
        meta = self.core_app.pdf_manager.get_metadata(self.file_path)
        self.metadata_view.set_data(self.file_path, meta['tags'], meta['notes'])

    def on_toc_clicked(self, item, column):
        self.current_toc_item = item
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            page = data.get('page', 1)
            self.go_to_page(page)
            
            # Load note
            self.note_editor.blockSignals(True)
            self.note_editor.setText(data.get('user_note', ''))
            self.note_editor.blockSignals(False)

    def on_chapter_note_changed(self):
        if self.current_toc_item:
            data = self.current_toc_item.data(0, Qt.ItemDataRole.UserRole)
            if data:
                # Update the Dictionary in memory (mutable)
                data['user_note'] = self.note_editor.toPlainText()
                # Update item data just in case Qt copies it (it usually copies)
                # But since it's a dict, if it's referenced, it might be fine.
                # Safer to set it back
                self.current_toc_item.setData(0, Qt.ItemDataRole.UserRole, data)

    def save_toc_to_db(self):
        """Persist the current ToC tree (with notes) to the DB."""
        try:
            # Serialise self.toc_data
            toc_json = json.dumps(self.toc_data)
            
            # We need a method in Core to update ONLY bookmarks, or generally update metadata.
            # current 'update_file_metadata' updates tags/notes.
            # We need 'update_any_metadata' or add bookmarks arg.
            # Let's check CoreApp/PDFManager interface.
            # Assuming we can use SQL directly via Storage or add method to PDFManager.
            # Cleanest: Add update_bookmarks to PDFManager/CoreApp.
            
            # Accessing storage directly via core_app (Not ideal but pragmatic for now)
            # self.core_app.storage.update_metadata(self.file_path, bookmarks=toc_json)
            # Wait, storage.update_metadata signature needs checking.
            
            self.core_app.update_file_custom(self.file_path, bookmarks=toc_json)
            QMessageBox.information(self, "Success", "Chapter Notes Saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save ToC: {str(e)}")

    def save_file_metadata(self, file_path, tags, notes):
        try:
            self.core_app.update_file_metadata(file_path, tags, notes)
            QMessageBox.information(self, "Success", "File Metadata Saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def go_to_page(self, page_num):
        if 1 <= page_num <= self.total_pages:
            self.current_page = page_num
            self.render_current_page()
            
    def prev_page(self):
        self.go_to_page(self.current_page - 1)
        
    def next_page(self):
        self.go_to_page(self.current_page + 1)
        
    def render_current_page(self):
        img_bytes = PDFRenderer.render_page(self.file_path, self.current_page, self.zoom_level)
        if img_bytes:
            image = QImage.fromData(img_bytes)
            pixmap = QPixmap.fromImage(image)
            self.image_label.setPixmap(pixmap)
            self.lbl_page.setText(f"Page {self.current_page} / {self.total_pages}")
