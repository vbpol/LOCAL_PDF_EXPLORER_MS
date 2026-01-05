from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox,
    QDockWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
import json

from src.core.services.pdf_engine import PDFEngine
from src.apps.pdf_ms.views.reader.components import (
    PDFToolbar, PDFViewerPanel, ToCPanel, MetadataPanel
)

class ReaderWindow(QMainWindow):
    """
    Modular Reader Window (Reader V2).
    Orchestrates ToC, Viewer, and Metadata panels using Dock Widgets.
    """
    
    def __init__(self, file_path, core_app, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.core_app = core_app
        
        self.setWindowTitle(f"Reader: {file_path}")
        self.resize(1200, 800)
        
        self._init_ui()
        self._connect_signals()
        self._load_data()
        
    def _init_ui(self):
        # 1. Center Panel (Viewer)
        self.viewer = PDFViewerPanel()
        self.setCentralWidget(self.viewer)
        
        # 2. Toolbar (Native QMainWindow Toolbar)
        self.toolbar = PDFToolbar()
        # Enable dockable/floatable features
        self.toolbar.setMovable(True)
        self.toolbar.setFloatable(True)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        # 3. Left Panel (ToC)
        self.dock_toc = QDockWidget("Table of Contents", self)
        self.toc_panel = ToCPanel()
        self.dock_toc.setWidget(self.toc_panel)
        self.dock_toc.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_toc)
        
        # 4. Right Panel (Metadata)
        self.dock_meta = QDockWidget("Metadata", self)
        self.metadata_panel = MetadataPanel()
        self.dock_meta.setWidget(self.metadata_panel)
        self.dock_meta.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_meta)
        
        # 5. Add Toggle Actions to Toolbar
        self.toolbar.addSeparator()
        
        # ToC Toggle
        act_toc = self.dock_toc.toggleViewAction()
        act_toc.setText("ToC")
        act_toc.setToolTip("Show/Hide Table of Contents Panel")
        self.toolbar.addAction(act_toc)
        
        # Metadata Toggle
        act_meta = self.dock_meta.toggleViewAction()
        act_meta.setText("Info")
        act_meta.setToolTip("Show/Hide Metadata Panel")
        self.toolbar.addAction(act_meta)

    def _connect_signals(self):
        # Toolbar -> Viewer
        self.toolbar.zoom_in_requested.connect(self.viewer.zoom_in)
        self.toolbar.zoom_out_requested.connect(self.viewer.zoom_out)
        self.toolbar.prev_page_requested.connect(self.viewer.prev_page)
        self.toolbar.next_page_requested.connect(self.viewer.next_page)
        
        self.toolbar.fit_width_requested.connect(lambda: self.viewer.set_view_mode("width"))
        self.toolbar.fit_height_requested.connect(lambda: self.viewer.set_view_mode("height"))
        self.toolbar.fit_page_requested.connect(lambda: self.viewer.set_view_mode("page"))
        self.toolbar.fit_content_requested.connect(lambda: self.viewer.set_view_mode("content"))
        self.toolbar.full_mode_requested.connect(self._toggle_full_screen)
        
        # Viewer -> Toolbar
        self.viewer.page_changed.connect(self._on_page_changed)
        
        # ToC -> Viewer
        self.toc_panel.toc_navigation_requested.connect(self._on_toc_navigation)
        
        # ToC -> App (Save)
        self.toc_panel.save_toc_requested.connect(self._save_toc_to_db)
        
        # Metadata -> App (Save)
        self.metadata_panel.save_requested.connect(self._save_file_metadata)

    def _load_data(self):
        # Load PDF in Viewer
        self.viewer.load_document(self.file_path)
        # Update initial toolbar state
        self.toolbar.update_page_info(self.viewer.current_page, self.viewer.total_pages)
        
        # Load ToC
        self._load_toc()
        
        # Load Metadata
        self._load_metadata()

    def _load_toc(self):
        # 1. Try Load from DB
        db_meta = self.core_app.pdf_manager.get_metadata(self.file_path)
        bookmarks_json = db_meta.get('bookmarks', '')
        
        toc_data = []
        if bookmarks_json:
            try:
                toc_data = json.loads(bookmarks_json)
            except:
                toc_data = []
        
        # 2. If DB empty, Extract
        if not toc_data:
            toc_data = PDFEngine.extract_toc(self.file_path)
            
        self.toc_panel.load_toc(toc_data)

    def _load_metadata(self):
        meta = self.core_app.pdf_manager.get_metadata(self.file_path)
        self.metadata_panel.set_data(self.file_path, meta.get('tags', ''), meta.get('notes', ''))

    def _on_page_changed(self, page):
        self.toolbar.update_page_info(page, self.viewer.total_pages)
        # Optional: Sync ToC selection if possible? (Complex, skip for now)

    def _on_toc_navigation(self, page, y_offset):
        # "activate it when users navigate by TOC item"
        # Switch to Fit Content mode if not in a width-based mode for better readability
        if self.viewer.view_mode not in ["width", "content"]:
            self.viewer.set_view_mode("content")
            self.toolbar.set_mode_checked("content")
            
        self.viewer.go_to_page(page, y_offset)

    def _save_toc_to_db(self, toc_data):
        try:
            toc_json = json.dumps(toc_data)
            self.core_app.update_file_custom(self.file_path, bookmarks=toc_json)
            QMessageBox.information(self, "Success", "Chapter Notes Saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save ToC: {str(e)}")

    def _save_file_metadata(self, file_path, tags, notes):
        try:
            self.core_app.update_file_metadata(file_path, tags, notes)
            QMessageBox.information(self, "Success", "File Metadata Saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _toggle_full_screen(self):
        if self.isFullScreen():
            self.showNormal()
            self.toolbar.act_full_mode.setChecked(False)
        else:
            self.showFullScreen()
            self.toolbar.act_full_mode.setChecked(True)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle ESC key to exit full screen."""
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self._toggle_full_screen()
        else:
            super().keyPressEvent(event)
