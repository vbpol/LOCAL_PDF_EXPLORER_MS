
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.apps.pdf_ms.controllers.main_controller import MainController
from src.apps.pdf_ms.views.main_window import MainWindow

class TestStartup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance if it doesn't exist
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_app_initialization(self):
        """Test that the application initializes without errors."""
        try:
            controller = MainController()
            self.assertIsInstance(controller.main_window, MainWindow)
            self.assertTrue(controller.main_window.isVisible() == False) # Should be hidden initially until show() is called
            
            # Check if critical components are present
            self.assertTrue(hasattr(controller.main_window, 'table_view'))
            self.assertTrue(hasattr(controller.main_window, 'metadata_container'))
            
            # Check initial state
            self.assertTrue(controller.main_window.metadata_container.isHidden())
            
            # Check Toggle Button
            self.assertTrue(hasattr(controller.main_window, 'act_toggle_info'))
            self.assertFalse(controller.main_window.act_toggle_info.isChecked())
            
            # Test Toggle
            controller.main_window.act_toggle_info.trigger() # Toggle ON
            self.assertFalse(controller.main_window.metadata_container.isHidden())
            self.assertTrue(controller.main_window.act_toggle_info.isChecked())
            
            controller.main_window.act_toggle_info.trigger() # Toggle OFF
            self.assertTrue(controller.main_window.metadata_container.isHidden())
            
        except Exception as e:
            self.fail(f"Application initialization failed: {e}")

if __name__ == '__main__':
    unittest.main()
