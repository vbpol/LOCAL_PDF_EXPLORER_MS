import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.apps.pdf_ms.views.reader import ReaderWindow
from src.apps.pdf_ms.views.reader.components import PDFToolbar, PDFViewerPanel, ToCPanel, MetadataPanel
from src.core.services.pdf_renderer import PDFRenderer

# Mock CoreApp
class MockCoreApp:
    def __init__(self):
        self.pdf_manager = MockPDFManager()
        
    def update_file_custom(self, path, bookmarks=None):
        pass
        
    def update_file_metadata(self, path, tags, notes):
        pass

class MockPDFManager:
    def get_metadata(self, path):
        return {'tags': '', 'notes': '', 'bookmarks': ''}

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_reader_window_initialization(qapp, monkeypatch):
    """
    Test that ReaderWindow initializes correctly with all modular components.
    """
    # Patch PDFRenderer to avoid file errors
    monkeypatch.setattr(PDFRenderer, "get_page_count", lambda f: 10)
    monkeypatch.setattr(PDFRenderer, "render_page", lambda f, p, z: b'')
    
    core_app = MockCoreApp()
    # Use a dummy file path
    file_path = "test.pdf"
    
    # Instantiate
    window = ReaderWindow(file_path, core_app)
    
    # Check components existence
    assert isinstance(window.toolbar, PDFToolbar)
    assert isinstance(window.viewer, PDFViewerPanel)
    assert isinstance(window.toc_panel, ToCPanel)
    assert isinstance(window.metadata_panel, MetadataPanel)
    
    # Check Dock Widgets
    assert window.dock_toc is not None
    assert window.dock_meta is not None
    assert window.centralWidget() == window.viewer
    
    # Check Toolbar Actions
    actions = window.toolbar.actions()
    assert len(actions) > 8 # Updated count
    
    # Verify Toggle Actions exist
    action_texts = [a.text() for a in actions]
    assert "ToC" in action_texts
    assert "Info" in action_texts
    assert "Fit Content" in action_texts
    
    # Clean up
    window.close()

def test_pdf_toolbar_signals(qapp):
    toolbar = PDFToolbar()
    # Just verify attributes exist
    assert hasattr(toolbar, 'zoom_in_requested')
    assert hasattr(toolbar, 'fit_width_requested')
    assert hasattr(toolbar, 'fit_content_requested')

def test_toc_panel_structure(qapp):
    panel = ToCPanel()
    assert panel.toc_tree is not None
    assert panel.note_editor is not None
    assert panel.btn_save_toc is not None

def test_toc_navigation_triggers_mode(qapp, monkeypatch):
    # Patch PDFRenderer
    monkeypatch.setattr(PDFRenderer, "get_page_count", lambda f: 10)
    monkeypatch.setattr(PDFRenderer, "render_page", lambda f, p, z: b'')
    
    core_app = MockCoreApp()
    window = ReaderWindow("test.pdf", core_app)
    
    # Mock _calculate_fit_zoom to avoid fitz.open error
    window.viewer._calculate_fit_zoom = lambda: None
    
    # Force initial mode to 'page'
    window.viewer.view_mode = "page"
    
    # Simulate ToC navigation signal
    # We emit signal with page 5, y=100.0
    window.toc_panel.toc_navigation_requested.emit(5, 100.0)
    
    # Check if mode switched to 'content' (as per requirement)
    assert window.viewer.view_mode == "content"
    
    # Check if page was updated
    assert window.viewer.current_page == 5
    
    window.close()
