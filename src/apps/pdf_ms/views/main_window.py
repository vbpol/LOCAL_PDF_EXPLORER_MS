from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter, QFileDialog, QHeaderView, QToolBar, QLineEdit, QSizePolicy, QComboBox, QApplication, QStyle
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from src.apps.pdf_ms.views.components.pdf_table_view import PDFTableView

class MainWindow(QMainWindow):
    """
    MVC View: The main application window.
    Composes other views (PDFListView, MetadataView).
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Management System")
        self.resize(1000, 600)
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)
        
        # Open Folder Action (Defined but added later)
        self.act_open_folder = QAction(self)
        self.act_open_folder.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.act_open_folder.setToolTip("Open Folder")
        # Text is removed as requested ("use icon like a loop instead of text") - assuming Icon Only
        
        # Restart App Action
        self.act_restart = QAction("Restart App", self)
        self.toolbar.addAction(self.act_restart)

        # Toggle Info Panel Action
        self.act_toggle_info = QAction("Info Panel", self)
        self.act_toggle_info.setCheckable(True)
        self.act_toggle_info.setChecked(False)
        self.act_toggle_info.triggered.connect(self.toggle_info_panel)
        self.toolbar.addAction(self.act_toggle_info)

        # Settings Action
        self.act_settings = QAction("Settings", self)
        self.act_settings.setToolTip("Configure application settings")
        self.toolbar.addAction(self.act_settings)

        # History Combo Box
        self.combo_history = QComboBox()
        self.combo_history.setPlaceholderText("Select Root Folder...")
        self.combo_history.setFixedWidth(300)
        self.combo_history.setToolTip("Select from previously opened root folders")
        self.toolbar.addWidget(self.combo_history)

        # Add Open Folder Action AFTER Combo Box
        self.toolbar.addAction(self.act_open_folder)

        # Search Bar in Toolbar (or separate layout)
        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(empty)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search filenames, tags, notes...")
        self.search_input.setToolTip("Filter files by name, tags, or notes")
        self.search_input.setFixedWidth(200)
        self.toolbar.addWidget(self.search_input)

        # Splitter for List | Details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Enhanced Table View
        self.table_view = PDFTableView()
        splitter.addWidget(self.table_view)

        # Metadata Panel (will be injected by controller or instantiated here)
        # We'll leave a placeholder or let the controller attach the specific view
        # For simplicity, we can create a container here
        self.metadata_container = QWidget()
        self.metadata_layout = QVBoxLayout(self.metadata_container)
        self.metadata_layout.setContentsMargins(0,0,0,0)
        splitter.addWidget(self.metadata_container)
        
        # Hide Metadata Panel Initially
        self.metadata_container.hide()
        
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def add_metadata_view(self, view_widget):
        self.metadata_layout.addWidget(view_widget)

    def toggle_info_panel(self, checked):
        self.metadata_container.setVisible(checked)
