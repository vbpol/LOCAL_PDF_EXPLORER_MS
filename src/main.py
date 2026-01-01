import sys
import os

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from src.apps.pdf_ms.controllers.main_controller import MainController

def main():
    app = QApplication(sys.argv)
    controller = MainController()
    controller.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
