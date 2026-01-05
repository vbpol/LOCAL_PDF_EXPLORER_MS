from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor
from src.core.services.pdf_renderer import PDFRenderer

class PDFViewerPanel(QWidget):
    """
    Self-contained PDF Viewer Panel.
    Handles Rendering, Zooming, Fit Modes, and Mouse Interaction.
    """
    
    # Signals
    page_changed = pyqtSignal(int) # new_page
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.current_page = 1
        self.total_pages = 0
        self.zoom_level = 1.0
        self.view_mode = "custom" # "custom", "width", "height", "page"
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) # Important for Fit modes
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #505050;") # Dark gray background
        
        # Install event filter for Ctrl+Scroll Zoom
        self.scroll_area.viewport().installEventFilter(self)
        self.image_label.installEventFilter(self)
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)

    def load_document(self, file_path):
        self.file_path = file_path
        self.total_pages = PDFRenderer.get_page_count(file_path)
        self.current_page = 1
        self.render_page()

    def render_page(self):
        if not self.file_path:
            return

        # Calculate Zoom based on Mode
        if self.view_mode != "custom":
             self._calculate_fit_zoom()

        # Render
        img_bytes = PDFRenderer.render_page(self.file_path, self.current_page, self.zoom_level)
        if img_bytes:
            image = QImage.fromData(img_bytes)
            pixmap = QPixmap.fromImage(image)
            self.image_label.setPixmap(pixmap)
            # Ensure label size matches pixmap if not resizable, but ScrollArea handles it
        
        self.page_changed.emit(self.current_page)

    def _calculate_fit_zoom(self):
        """Calculate zoom level based on current viewport size and PDF page size."""
        # We need page dimensions without rendering fully first? 
        # fitz.open(path).load_page(n).rect gives size.
        # This is expensive to open every time.
        # Optimization: Store doc or dimensions. For now, open briefly.
        import fitz
        try:
            doc = fitz.open(self.file_path)
            page = doc.load_page(self.current_page - 1)
            rect = page.rect
            doc.close()
            
            page_w, page_h = rect.width, rect.height
            view_w = self.scroll_area.viewport().width() - 20 # Scrollbar buffer
            view_h = self.scroll_area.viewport().height() - 20
            
            if self.view_mode == "width":
                self.zoom_level = view_w / page_w
            elif self.view_mode == "height":
                self.zoom_level = view_h / page_h
            elif self.view_mode == "page":
                # Fit entire page (min of width/height ratios)
                ratio_w = view_w / page_w
                ratio_h = view_h / page_h
                self.zoom_level = min(ratio_w, ratio_h)
                
        except Exception as e:
            print(f"Error calculating zoom: {e}")

    def go_to_page(self, page):
        if 1 <= page <= self.total_pages:
            self.current_page = page
            self.render_page()

    def next_page(self):
        self.go_to_page(self.current_page + 1)

    def prev_page(self):
        self.go_to_page(self.current_page - 1)

    def zoom_in(self):
        self.view_mode = "custom"
        self.zoom_level *= 1.2
        self.render_page()

    def zoom_out(self):
        self.view_mode = "custom"
        self.zoom_level /= 1.2
        self.render_page()

    def set_view_mode(self, mode):
        """Set fit mode: 'width', 'height', 'page', 'custom'"""
        self.view_mode = mode
        self.render_page()

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.Wheel:
            modifiers = event.modifiers()
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                # Zoom
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return True
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        # Re-render if in a Fit mode
        if self.view_mode != "custom":
            self.render_page()
        super().resizeEvent(event)
