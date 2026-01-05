from PyQt6.QtWidgets import QToolBar, QLabel, QWidget, QSizePolicy
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import pyqtSignal, Qt

class PDFToolbar(QToolBar):
    """
    Modular Toolbar for PDF Viewer.
    Scalable, self-contained.
    """
    
    # Signals
    zoom_in_requested = pyqtSignal()
    zoom_out_requested = pyqtSignal()
    fit_page_requested = pyqtSignal()
    fit_width_requested = pyqtSignal()
    fit_height_requested = pyqtSignal()
    fit_content_requested = pyqtSignal()
    full_mode_requested = pyqtSignal()
    prev_page_requested = pyqtSignal()
    next_page_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # self.setMovable(False) # Allow moving by default for dockable experience
        # self.setFloatable(False) 
        self._init_actions()

    def _init_actions(self):
        # Navigation
        self.act_prev = QAction("<", self)
        self.act_prev.setToolTip("Previous Page")
        self.act_prev.triggered.connect(self.prev_page_requested.emit)
        self.addAction(self.act_prev)
        
        self.lbl_page_info = QLabel(" 0 / 0 ")
        self.addWidget(self.lbl_page_info)
        
        self.act_next = QAction(">", self)
        self.act_next.setToolTip("Next Page")
        self.act_next.triggered.connect(self.next_page_requested.emit)
        self.addAction(self.act_next)
        
        self.addSeparator()
        
        # Zoom
        self.act_zoom_out = QAction("-", self)
        self.act_zoom_out.setToolTip("Zoom Out")
        self.act_zoom_out.triggered.connect(self.zoom_out_requested.emit)
        self.addAction(self.act_zoom_out)
        
        self.act_zoom_in = QAction("+", self)
        self.act_zoom_in.setToolTip("Zoom In")
        self.act_zoom_in.triggered.connect(self.zoom_in_requested.emit)
        self.addAction(self.act_zoom_in)
        
        self.addSeparator()
        
        # View Modes
        self.act_fit_width = QAction("Fit Width", self)
        self.act_fit_width.setCheckable(True)
        self.act_fit_width.triggered.connect(lambda: self._handle_mode_change(self.act_fit_width, self.fit_width_requested))
        self.addAction(self.act_fit_width)

        self.act_fit_content = QAction("Fit Content", self)
        self.act_fit_content.setCheckable(True)
        self.act_fit_content.setToolTip("Fit to visible content (ignore margins)")
        self.act_fit_content.triggered.connect(lambda: self._handle_mode_change(self.act_fit_content, self.fit_content_requested))
        self.addAction(self.act_fit_content)
        
        self.act_fit_height = QAction("Fit Height", self)
        self.act_fit_height.setCheckable(True)
        self.act_fit_height.triggered.connect(lambda: self._handle_mode_change(self.act_fit_height, self.fit_height_requested))
        self.addAction(self.act_fit_height)

        self.act_fit_page = QAction("Fit Page", self)
        self.act_fit_page.setCheckable(True)
        self.act_fit_page.triggered.connect(lambda: self._handle_mode_change(self.act_fit_page, self.fit_page_requested))
        self.addAction(self.act_fit_page)
        
        self.addSeparator()
        
        self.act_full_mode = QAction("Full Screen", self)
        self.act_full_mode.setCheckable(True)
        self.act_full_mode.triggered.connect(self.full_mode_requested.emit)
        self.addAction(self.act_full_mode)
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

    def _handle_mode_change(self, action, signal):
        # Uncheck others
        for act in [self.act_fit_width, self.act_fit_height, self.act_fit_page, self.act_fit_content]:
            if act != action:
                act.setChecked(False)
        signal.emit()

    def update_page_info(self, current, total):
        self.lbl_page_info.setText(f" {current} / {total} ")

    def set_mode_checked(self, mode):
        # Helper to set check state programmatically
        self.act_fit_width.setChecked(mode == "width")
        self.act_fit_height.setChecked(mode == "height")
        self.act_fit_page.setChecked(mode == "page")
        self.act_fit_content.setChecked(mode == "content")
