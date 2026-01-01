import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.apps.pdf_ms.controllers.main_controller import MainController

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_ui_startup(qapp):
    """
    Smoke test: Ensure MainController initializes MainWindow without error.
    """
    try:
        controller = MainController()
        assert controller.main_window is not None
        assert controller.main_window.isVisible() is False
        
        # Optional: check if core initialized
        assert controller.app_core is not None
        print("UI Startup Test Passed")
    except Exception as e:
        pytest.fail(f"UI Startup Failed: {e}")
