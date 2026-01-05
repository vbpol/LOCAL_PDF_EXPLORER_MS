#!/usr/bin/env python3
"""
PDFBMViewer with dockable PDFViewerToolBar

Requirements:
    pip install PyQt6 pymupdf
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap, QWheelEvent
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDockWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QScrollArea,
    QLabel,
    QFileDialog,
    QMessageBox,
    QToolBar,
    QWidget,
    QVBoxLayout,
    QToolButton,
    QSpinBox,
    QFrame,
    QMenuBar,
)


# ============================================================================
# Core viewer class
# ============================================================================

class clsPDFBMViewer(QMainWindow):
    """
    Reusable PDF viewer with a dockable bookmark panel.

    Public API
    ----------
    - load_pdf(path: str) -> bool
    - close_pdf() -> None
    - go_to_page(index: int) -> None          # 0-based
    - next_page() / prev_page()
    - set_zoom(factor: float)
    - zoom_in() / zoom_out() / reset_zoom()
    - toggle_bookmark_panel(visible: bool)

    Signals
    -------
    - pdfLoaded(path: str, page_count: int)
    - pdfClosed()
    - pageChanged(page_index: int)
    - bookmarksLoaded(count: int)
    - errorOccurred(message: str)
    """

    pdfLoaded = pyqtSignal(str, int)
    pdfClosed = pyqtSignal()
    pageChanged = pyqtSignal(int)
    bookmarksLoaded = pyqtSignal(int)
    errorOccurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._doc = None          # type: ignore[assignment]
        self._pdf_path: Optional[str] = None
        self._current_page: int = 0
        self._zoom: float = 1.0
        self._min_zoom: float = 0.25
        self._max_zoom: float = 5.0

        self._init_ui()

    # ------------------------ UI setup ------------------------

    def _init_ui(self):
        # Central page viewer
        self.page_label = QLabel("Open a PDF to begin")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("background-color: #808080; color: white;")

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.page_label)
        self.setCentralWidget(self.scroll_area)

        # Bookmark tree inside a dock widget
        self.bookmark_tree = QTreeWidget()
        self.bookmark_tree.setHeaderHidden(True)
        self.bookmark_tree.itemActivated.connect(self._on_bookmark_activated)
        self.bookmark_tree.itemClicked.connect(self._on_bookmark_activated)

        self.bookmark_dock = QDockWidget("Bookmarks", self)
        self.bookmark_dock.setWidget(self.bookmark_tree)
        self.bookmark_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.bookmark_dock)

    # ------------------------ Public properties ------------------------

    @property
    def pdf_path(self) -> Optional[str]:
        return self._pdf_path

    @property
    def page_count(self) -> int:
        if self._doc is None:
            return 0
        return self._doc.page_count  # type: ignore[union-attr]

    @property
    def current_page_index(self) -> int:
        return self._current_page

    @property
    def zoom_factor(self) -> float:
        return self._zoom

    # ------------------------ Public API ------------------------

    def load_pdf(self, path: str) -> bool:
        """Load a PDF file; return True on success."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            self._emit_error(
                "PyMuPDF (pymupdf) is required.\nInstall it with:\n"
                "    pip install pymupdf"
            )
            return False

        if not os.path.isfile(path):
            self._emit_error(f"File not found:\n{path}")
            return False

        # Close previous document
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None

        try:
            doc = fitz.open(path)
        except Exception as e:
            self._emit_error(f"Error opening PDF:\n{e}")
            return False

        self._doc = doc
        self._pdf_path = path
        self._current_page = 0
        self._zoom = 1.0

        self._render_current_page()
        self._load_bookmarks()

        self.pdfLoaded.emit(path, self.page_count)
        return True

    def close_pdf(self) -> None:
        """Close the current PDF and clear the viewer."""
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
        self._doc = None
        self._pdf_path = None
        self._current_page = 0
        self.page_label.setText("No document loaded")
        self.page_label.setPixmap(QPixmap())
        self.bookmark_tree.clear()
        self.pdfClosed.emit()

    def go_to_page(self, index: int) -> None:
        """Navigate to the given 0‑based page index."""
        if self._doc is None:
            return
        if index < 0 or index >= self.page_count:
            return
        if index == self._current_page:
            return

        self._current_page = index
        self._render_current_page()
        self.pageChanged.emit(self._current_page)

    def next_page(self) -> None:
        self.go_to_page(self._current_page + 1)

    def prev_page(self) -> None:
        self.go_to_page(self._current_page - 1)

    def set_zoom(self, factor: float) -> None:
        """Set zoom factor and re-render the current page."""
        factor = max(self._min_zoom, min(self._max_zoom, factor))
        if abs(factor - self._zoom) < 1e-3:
            return
        self._zoom = factor
        self._render_current_page()

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom * 1.25)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom / 1.25)

    def reset_zoom(self) -> None:
        self.set_zoom(1.0)

    def toggle_bookmark_panel(self, visible: bool) -> None:
        """Show/hide the bookmark dock."""
        self.bookmark_dock.setVisible(visible)

    # ------------------------ Internal helpers ------------------------

    def _emit_error(self, message: str) -> None:
        self.errorOccurred.emit(message)

    def _render_current_page(self) -> None:
        """Render the current page into the central QLabel."""
        if self._doc is None:
            self.page_label.setText("No document loaded")
            self.page_label.setPixmap(QPixmap())
            return

        try:
            import fitz  # ensure present
        except ImportError:
            self._emit_error(
                "PyMuPDF (pymupdf) is required.\nInstall it with:\n"
                "    pip install pymupdf"
            )
            return

        try:
            page = self._doc.load_page(self._current_page)
            mat = fitz.Matrix(self._zoom, self._zoom)
            pix = page.get_pixmap(matrix=mat)
        except Exception as e:
            self._emit_error(f"Error rendering page:\n{e}")
            return

        img_bytes = pix.tobytes("png")
        qpix = QPixmap()
        if not qpix.loadFromData(img_bytes, "PNG"):
            self._emit_error("Failed to convert page image.")
            return

        self.page_label.setPixmap(qpix)
        self.page_label.adjustSize()

    def _load_bookmarks(self) -> None:
        """Populate the bookmark tree from the PDF outline."""
        self.bookmark_tree.clear()

        if self._doc is None:
            self.bookmarksLoaded.emit(0)
            return

        try:
            toc = self._doc.get_toc()  # [[level, title, page, ...], ...]
        except Exception as e:
            self._emit_error(f"Error reading bookmarks:\n{e}")
            self.bookmarksLoaded.emit(0)
            return

        if not toc:
            root = QTreeWidgetItem(["<No bookmarks>"])
            root.setDisabled(True)
            self.bookmark_tree.addTopLevelItem(root)
            self.bookmarksLoaded.emit(0)
            return

        level_item_map: dict[int, QTreeWidgetItem] = {
            0: self.bookmark_tree.invisibleRootItem()
        }
        count = 0

        for entry in toc:
            if len(entry) < 3:
                continue
            level, title, page = entry[0], entry[1], entry[2]

            try:
                level = int(level)
                page = int(page)
            except ValueError:
                continue

            if level < 1:
                level = 1
            if page < 1:
                page = 1
            if page > self.page_count:
                page = self.page_count

            item = QTreeWidgetItem([title])
            item.setData(0, Qt.ItemDataRole.UserRole, page - 1)

            parent = level_item_map.get(level - 1, level_item_map[0])
            parent.addChild(item)
            level_item_map[level] = item
            count += 1

        self.bookmark_tree.expandToDepth(1)
        self.bookmarksLoaded.emit(count)

    def _on_bookmark_activated(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return
        try:
            page_idx = int(data)
        except (TypeError, ValueError):
            return
        self.go_to_page(page_idx)


# ============================================================================
# Dockable side toolbar (Adobe-like)
# ============================================================================

class PDFViewerToolBar(QDockWidget):
    """
    Dockable vertical PDF navigation/zoom toolbar.

    UI elements (top -> bottom)
    ---------------------------
    - Current page (QSpinBox, 1-based, editable)
    - Total pages label
    - Page up (previous page)
    - Page down (next page)
    - Separator
    - '1:1' button -> actual size zoom
    - Zoom + button
    - Zoom - button

    Features
    --------
    - Middle mouse + wheel over the viewer's page area = zoom in/out.
    - Emits signals so it can be reused with any viewer class.

    Signals
    -------
    - pageRequested(page_index: int)      # 0-based
    - nextPageRequested()
    - prevPageRequested()
    - zoomInRequested()
    - zoomOutRequested()
    - actualSizeRequested()
    """

    pageRequested = pyqtSignal(int)
    nextPageRequested = pyqtSignal()
    prevPageRequested = pyqtSignal()
    zoomInRequested = pyqtSignal()
    zoomOutRequested = pyqtSignal()
    actualSizeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Navigation", parent)

        self._viewer: Optional[clsPDFBMViewer] = None
        self._total_pages: int = 0
        self._ignore_spin_change: bool = False

        self._init_ui()

        # By default the dock can be moved/closed/floated.
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )

    def _init_ui(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Current page spinbox
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setValue(1)
        self.page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_spin.setFixedWidth(50)
        self.page_spin.editingFinished.connect(self._on_page_spin_edited)
        layout.addWidget(self.page_spin, 0, Qt.AlignmentFlag.AlignHCenter)

        # Total pages label
        self.total_label = QLabel("0")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.total_label, 0, Qt.AlignmentFlag.AlignHCenter)

        # Page up / down buttons
        self.btn_up = QToolButton()
        self.btn_up.setArrowType(Qt.ArrowType.UpArrow)
        self.btn_up.clicked.connect(self._on_prev_clicked)
        layout.addWidget(self.btn_up, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_down = QToolButton()
        self.btn_down.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_down.clicked.connect(self._on_next_clicked)
        layout.addWidget(self.btn_down, 0, Qt.AlignmentFlag.AlignHCenter)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # '1:1' exact size button
        self.btn_actual = QToolButton()
        self.btn_actual.setText("1:1")
        self.btn_actual.clicked.connect(self.actualSizeRequested)
        layout.addWidget(self.btn_actual, 0, Qt.AlignmentFlag.AlignHCenter)

        # Zoom in
        self.btn_zoom_in = QToolButton()
        self.btn_zoom_in.setText("+")
        self.btn_zoom_in.clicked.connect(self.zoomInRequested)
        layout.addWidget(self.btn_zoom_in, 0, Qt.AlignmentFlag.AlignHCenter)

        # Zoom out
        self.btn_zoom_out = QToolButton()
        self.btn_zoom_out.setText("-")
        self.btn_zoom_out.clicked.connect(self.zoomOutRequested)
        layout.addWidget(self.btn_zoom_out, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch(1)

        self.setWidget(w)
        self.setMinimumWidth(70)
        self._set_enabled(False)

    # ---------- Public API ----------

    def attach_viewer(self, viewer: clsPDFBMViewer) -> None:
        """
        Attach this toolbar to a clsPDFBMViewer instance.
        Connects signals and installs wheel-zoom filter.
        """
        self._viewer = viewer

        viewer.pdfLoaded.connect(self.on_pdf_loaded)
        viewer.pdfClosed.connect(self.on_pdf_closed)
        viewer.pageChanged.connect(self.on_page_changed)

        # Zoom with middle mouse + wheel over the page viewport
        viewer.scroll_area.viewport().installEventFilter(self)

        # Initialize state if a document is already open
        if viewer.page_count > 0:
            self.on_pdf_loaded(viewer.pdf_path or "", viewer.page_count)
            self.on_page_changed(viewer.current_page_index)
        else:
            self.on_pdf_closed()

    # ---------- Slots for viewer events ----------

    def on_pdf_loaded(self, path: str, page_count: int) -> None:
        self._total_pages = page_count
        self.total_label.setText(str(page_count if page_count > 0 else 0))
        self.page_spin.setMaximum(max(1, page_count))
        self.page_spin.setValue(1)
        self._set_enabled(page_count > 0)

    def on_pdf_closed(self) -> None:
        self._total_pages = 0
        self.total_label.setText("0")
        self.page_spin.setMaximum(1)
        self.page_spin.setValue(1)
        self._set_enabled(False)

    def on_page_changed(self, page_index: int) -> None:
        # Update spinbox without triggering navigation again
        self._ignore_spin_change = True
        self.page_spin.setValue(page_index + 1)
        self._ignore_spin_change = False

    # ---------- Internal helpers ----------

    def _set_enabled(self, enabled: bool) -> None:
        self.page_spin.setEnabled(enabled)
        self.total_label.setEnabled(enabled)
        self.btn_up.setEnabled(enabled)
        self.btn_down.setEnabled(enabled)
        self.btn_actual.setEnabled(enabled)
        self.btn_zoom_in.setEnabled(enabled)
        self.btn_zoom_out.setEnabled(enabled)

    def _on_prev_clicked(self):
        self.prevPageRequested.emit()

    def _on_next_clicked(self):
        self.nextPageRequested.emit()

    def _on_page_spin_edited(self):
        if self._ignore_spin_change:
            return
        if self._total_pages <= 0:
            return
        page_1_based = self.page_spin.value()
        page_index = max(0, min(self._total_pages - 1, page_1_based - 1))
        self.pageRequested.emit(page_index)

    # ---------- Middle-mouse zoom filter ----------

    def eventFilter(self, obj, event):
        if self._viewer is not None and obj is self._viewer.scroll_area.viewport():
            if isinstance(event, QWheelEvent):
                # Zoom only when middle mouse button is held while scrolling
                if event.buttons() & Qt.MouseButton.MiddleButton:
                    delta = event.angleDelta().y()
                    if delta > 0:
                        self.zoomInRequested.emit()
                    elif delta < 0:
                        self.zoomOutRequested.emit()
                    return True
        return super().eventFilter(obj, event)


# ============================================================================
# Example main window using clsPDFBMViewer + PDFViewerToolBar
# ============================================================================

class PDFBMViewer(clsPDFBMViewer):
    """
    Example application on top of clsPDFBMViewer.

    - Menus for file and view actions.
    - Top toolbar (for file / basic nav).
    - Left dock: PDFViewerToolBar (page + zoom controls).
    - Right dock: bookmarks tree (from base class).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("PDF Bookmark Viewer")
        self.resize(1200, 800)

        self._create_actions()
        self._create_menus()
        self._create_top_toolbar()
        self._connect_signals()

        # Dockable side PDF toolbar
        self.nav_toolbar = PDFViewerToolBar(self)
        self.nav_toolbar.attach_viewer(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.nav_toolbar)

        # Add toggle action to View menu
        self.view_menu.addAction(self.nav_toolbar.toggleViewAction())

    # ---------- UI chrome (menus / toolbar) ----------

    def _create_actions(self):
        # File actions
        self.act_open = QAction("Open…", self)
        self.act_open.setShortcut("Ctrl+O")
        self.act_open.triggered.connect(self._open_file_dialog)

        self.act_close = QAction("Close PDF", self)
        self.act_close.triggered.connect(self.close_pdf)

        self.act_exit = QAction("Exit", self)
        self.act_exit.setShortcut("Ctrl+Q")
        self.act_exit.triggered.connect(self.close)

        # View / navigation actions (still available from menu)
        self.act_next = QAction("Next page", self)
        self.act_next.setShortcut("PgDown")
        self.act_next.triggered.connect(self.next_page)

        self.act_prev = QAction("Previous page", self)
        self.act_prev.setShortcut("PgUp")
        self.act_prev.triggered.connect(self.prev_page)

        self.act_zoom_in = QAction("Zoom in", self)
        self.act_zoom_in.setShortcut("Ctrl++")
        self.act_zoom_in.triggered.connect(self.zoom_in)

        self.act_zoom_out = QAction("Zoom out", self)
        self.act_zoom_out.setShortcut("Ctrl+-")
        self.act_zoom_out.triggered.connect(self.zoom_out)

        self.act_zoom_reset = QAction("Actual size (1:1)", self)
        self.act_zoom_reset.setShortcut("Ctrl+0")
        self.act_zoom_reset.triggered.connect(self.reset_zoom)

        self.act_toggle_bookmarks = self.bookmark_dock.toggleViewAction()
        self.act_toggle_bookmarks.setText("Show bookmarks panel")

    def _create_menus(self):
        menubar: QMenuBar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.act_open)
        file_menu.addAction(self.act_close)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        self.view_menu = menubar.addMenu("&View")
        self.view_menu.addAction(self.act_next)
        self.view_menu.addAction(self.act_prev)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.act_zoom_in)
        self.view_menu.addAction(self.act_zoom_out)
        self.view_menu.addAction(self.act_zoom_reset)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.act_toggle_bookmarks)

    def _create_top_toolbar(self):
        # A simple top toolbar mostly for file actions
        tb = QToolBar("Main Toolbar", self)
        tb.setMovable(True)
        self.addToolBar(tb)

        tb.addAction(self.act_open)
        tb.addAction(self.act_close)
        tb.addSeparator()
        tb.addAction(self.act_prev)
        tb.addAction(self.act_next)

    def _connect_signals(self):
        self.errorOccurred.connect(self._on_error)
        self.pdfLoaded.connect(self._on_pdf_loaded)

        # Connect navigation toolbar signals to viewer methods
        self.nav_toolbar.pageRequested.connect(self.go_to_page)
        self.nav_toolbar.nextPageRequested.connect(self.next_page)
        self.nav_toolbar.prevPageRequested.connect(self.prev_page)
        self.nav_toolbar.zoomInRequested.connect(self.zoom_in)
        self.nav_toolbar.zoomOutRequested.connect(self.zoom_out)
        self.nav_toolbar.actualSizeRequested.connect(self.reset_zoom)

    # ---------- Slots ----------

    def _on_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)

    def _on_pdf_loaded(self, path: str, page_count: int) -> None:
        self.setWindowTitle(f"{os.path.basename(path)} - PDF Bookmark Viewer")

    def _open_file_dialog(self) -> None:
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            "",
            "PDF files (*.pdf);;All files (*)",
        )
        if not fname:
            return
        self.load_pdf(fname)


# ============================================================================
# Entry point
# ============================================================================

def main():
    app = QApplication(sys.argv)
    win = PDFBMViewer()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()