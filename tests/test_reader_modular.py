import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.apps.pdf_ms.views.reader import ReaderWindow
from src.apps.pdf_ms.views.reader.components import PDFToolbar, PDFViewerPanel, ToCPanel, MetadataPanel

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

def test_reader_window_initialization(qapp):
    """
    Test that ReaderWindow initializes correctly with all modular components.
    """
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
    assert len(actions) > 7 # Nav(3) + Zoom(2) + Fit(3) + Full(1) + Toggle(2) + Separators
    
    # Verify Toggle Actions exist
    action_texts = [a.text() for a in actions]
    assert "ToC" in action_texts
    assert "Info" in action_texts
    
    # Clean up
    window.close()

def test_pdf_toolbar_signals(qapp):
    toolbar = PDFToolbar()
    # Just verify attributes exist
    assert hasattr(toolbar, 'zoom_in_requested')
    assert hasattr(toolbar, 'fit_width_requested')

def test_toc_panel_structure(qapp):
    panel = ToCPanel()
    assert panel.toc_tree is not None
    assert panel.note_editor is not None
    assert panel.btn_save_toc is not None
