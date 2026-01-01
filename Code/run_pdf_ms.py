import sys
from PyQt6.QtWidgets import QApplication
from src.apps.pdf_ms.controllers.main_controller import MainController

def main():
    app = QApplication(sys.argv)
    
    # MVC Entry Point: Instantiate Controller
    controller = MainController()
    controller.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
