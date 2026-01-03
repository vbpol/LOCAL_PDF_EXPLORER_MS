import sys
import os
import pytest
import fitz
from PyQt6.QtWidgets import QApplication

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.apps.pdf_ms.views.reader_window import ReaderWindow

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

@pytest.fixture
def dummy_pdf(tmp_path):
    """Creates a temporary PDF for the test."""
    p = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "UI Test PDF")
    doc.save(str(p))
    doc.close()
    return str(p)

@pytest.fixture
def mock_core_app():
    class MockManager:
        def get_metadata(self, path):
            return {'tags': '', 'notes': '', 'bookmarks': ''}
    class MockCore:
        pdf_manager = MockManager()
    return MockCore()

def test_reader_window_launch(qapp, dummy_pdf, mock_core_app):
    """
    Test that ReaderWindow initializes and loads a PDF.
    """
    try:
        window = ReaderWindow(dummy_pdf, mock_core_app)
        
        # Check title
        assert "test.pdf" in window.windowTitle()
        
        # Check widgets exist
        assert window.toc_tree is not None
        assert window.image_label is not None
        
        # Check initial state
        assert window.current_page == 1
        
        # Determine if image was loaded (pixmap should be set)
        assert window.image_label.pixmap() is not None
        
        window.close()
        print("ReaderWindow Launch Test Passed")
        
    except Exception as e:
        pytest.fail(f"ReaderWindow Test Failed: {e}")
