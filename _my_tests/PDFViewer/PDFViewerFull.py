#!/usr/bin/env python3
"""
PDFBMViewer with dockable PDFViewerToolBar and Adobe-like view/zoom menu.

Requirements:
    pip install PyQt6 pymupdf
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QRect
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QPixmap,
    QWheelEvent,
    QPainter,
    QMouseEvent,
)
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
    QMenu,
    QRubberBand,
)


# ============================================================================
# Core viewer class (PDF + bookmarks)
# ============================================================================


class clsPDFBMViewer(QMainWindow):
    """
    Reusable PDF viewer with a dockable bookmark panel.
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

        self._view_mode: str = "single"      # "single" or "two"
        self._scrolling_enabled: bool = True

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
        self.bookmark_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
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
        self._view_mode = "single"

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
        """Actual size (1:1)."""
        self.set_zoom(1.0)

    def set_view_mode(self, mode: str) -> None:
        """'single' or 'two' page view."""
        if mode not in ("single", "two"):
            return
        if mode == self._view_mode:
            return
        self._view_mode = mode
        self._render_current_page()

    def set_scrolling_enabled(self, enabled: bool) -> None:
        """Enable/disable scrollbars."""
        self._scrolling_enabled = enabled
        if enabled:
            pol = Qt.ScrollBarPolicy.ScrollBarAsNeeded
        else:
            pol = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        self.scroll_area.setVerticalScrollBarPolicy(pol)
        self.scroll_area.setHorizontalScrollBarPolicy(pol)

    def fit_to_width(self) -> None:
        """Zoom so page (or pages) fit width of viewport."""
        if self._doc is None:
            return
        pw, ph = self._get_layout_page_size()
        if pw is None or pw <= 0:
            return
        view_w = self.scroll_area.viewport().width()
        if view_w <= 0:
            return
        zoom = view_w / pw
        self.set_zoom(zoom)

    def fit_to_height(self) -> None:
        """Zoom so page (or pages) fit height of viewport."""
        if self._doc is None:
            return
        pw, ph = self._get_layout_page_size()
        if ph is None or ph <= 0:
            return
        view_h = self.scroll_area.viewport().height()
        if view_h <= 0:
            return
        zoom = view_h / ph
        self.set_zoom(zoom)

    def fit_to_page(self) -> None:
        """Zoom so entire page (or pages) fit in viewport."""
        if self._doc is None:
            return
        pw, ph = self._get_layout_page_size()
        if not pw or not ph:
            return
        view_w = self.scroll_area.viewport().width()
        view_h = self.scroll_area.viewport().height()
        if view_w <= 0 or view_h <= 0:
            return
        zoom = min(view_w / pw, view_h / ph)
        self.set_zoom(zoom)

    def fit_visible_content(self) -> None:
        """Approximation: same as fit_to_width."""
        self.fit_to_width()

    def toggle_bookmark_panel(self, visible: bool) -> None:
        """Show/hide the bookmark dock."""
        self.bookmark_dock.setVisible(visible)

    # ------------------------ Internal helpers ------------------------

    def _emit_error(self, message: str) -> None:
        self.errorOccurred.emit(message)

    def _get_layout_page_size(self):
        """Return (width, height) in 'page units' for current layout."""
        if self._doc is None:
            return None, None
        try:
            page = self._doc.load_page(self._current_page)
        except Exception:
            return None, None
        rect = page.rect
        if self._view_mode == "single":
            width = rect.width
        else:
            width = rect.width * 2.0
        height = rect.height
        return float(width), float(height)

    def _render_current_page(self) -> None:
        """Render the current page(s) into the central QLabel."""
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
            mat = fitz.Matrix(self._zoom, self._zoom)

            if self._view_mode == "single" or self.page_count == 1:
                page = self._doc.load_page(self._current_page)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                qpix = QPixmap()
                if not qpix.loadFromData(img_bytes, "PNG"):
                    self._emit_error("Failed to convert page image.")
                    return
            else:
                # Two-page view: current page + next page side by side
                page1 = self._doc.load_page(self._current_page)
                page2_idx = min(self._current_page + 1, self.page_count - 1)
                page2 = self._doc.load_page(page2_idx)

                pix1 = page1.get_pixmap(matrix=mat)
                pix2 = page2.get_pixmap(matrix=mat)

                q1 = QPixmap()
                q1.loadFromData(pix1.tobytes("png"), "PNG")
                q2 = QPixmap()
                q2.loadFromData(pix2.tobytes("png"), "PNG")

                combo_w = q1.width() + q2.width()
                combo_h = max(q1.height(), q2.height())
                qpix = QPixmap(combo_w, combo_h)
                qpix.fill(Qt.GlobalColor.white)

                painter = QPainter(qpix)
                painter.drawPixmap(0, 0, q1)
                painter.drawPixmap(q1.width(), 0, q2)
                painter.end()

        except Exception as e:
            self._emit_error(f"Error rendering page:\n{e}")
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
            toc = self._doc.get_toc()
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

        for level, title, page in (entry[:3] for entry in toc if len(entry) >= 3):
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
# Dockable toolbar with Adobe-like view menu
# ============================================================================


class PDFViewerToolBar(QDockWidget):
    """
    Dockable vertical/horizontal PDF navigation/zoom toolbar.
    """

    pageRequested = pyqtSignal(int)
    nextPageRequested = pyqtSignal()
    prevPageRequested = pyqtSignal()
    zoomInRequested = pyqtSignal()
    zoomOutRequested = pyqtSignal()
    actualSizeRequested = pyqtSignal()
    viewModeRequested = pyqtSignal(str)
    scrollingToggled = pyqtSignal(bool)
    zoomPageLevelRequested = pyqtSignal()
    fitWidthRequested = pyqtSignal()
    fitHeightRequested = pyqtSignal()
    fitVisibleRequested = pyqtSignal()
    readModeToggled = pyqtSignal(bool)
    fullScreenToggled = pyqtSignal(bool)
    marqueeZoomToggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("Navigation", parent)

        self._viewer: Optional[clsPDFBMViewer] = None
        self._total_pages: int = 0
        self._ignore_spin_change: bool = False

        self._init_ui()
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)

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

        # '1:1' exact size button with menu
        self.btn_actual = QToolButton()
        self.btn_actual.setText("1:1")
        layout.addWidget(self.btn_actual, 0, Qt.AlignmentFlag.AlignHCenter)

        # Adobe-like view menu
        self.view_menu = QMenu(self)

        self.act_single_page = QAction("Single-page view", self, checkable=True)
        self.act_two_page = QAction("Two-page view", self, checkable=True)
        self.act_single_page.setChecked(True)
        self.view_mode_group = QActionGroup(self)
        self.view_mode_group.addAction(self.act_single_page)
        self.view_mode_group.addAction(self.act_two_page)
        self.view_mode_group.setExclusive(True)

        self.act_show_cover = QAction("Show cover page", self, checkable=True)
        self.act_show_cover.setEnabled(False)  # placeholder only

        self.act_enable_scrolling = QAction("Enable scrolling", self, checkable=True)
        self.act_enable_scrolling.setChecked(True)

        self.act_actual_size = QAction("Actual size", self, checkable=True)
        self.act_actual_size.setChecked(True)
        self.act_zoom_page = QAction("Zoom to page level", self)
        self.act_fit_width = QAction("Fit to width", self)
        self.act_fit_height = QAction("Fit height", self)
        self.act_fit_visible = QAction("Fit visible content", self)

        self.act_read_mode = QAction("Read mode", self, checkable=True)
        self.act_full_screen = QAction("Full screen mode", self, checkable=True)
        self.act_marquee_zoom = QAction("Marquee zoom", self, checkable=True)

        self.view_menu.addAction(self.act_single_page)
        self.view_menu.addAction(self.act_two_page)
        self.view_menu.addAction(self.act_show_cover)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.act_enable_scrolling)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.act_actual_size)
        self.view_menu.addAction(self.act_zoom_page)
        self.view_menu.addAction(self.act_fit_width)
        self.view_menu.addAction(self.act_fit_height)
        self.view_menu.addAction(self.act_fit_visible)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.act_read_mode)
        self.view_menu.addAction(self.act_full_screen)
        self.view_menu.addSeparator()
        self.view_menu.addSection("Other tools")
        self.view_menu.addAction(self.act_marquee_zoom)

        self.btn_actual.setMenu(self.view_menu)
        self.btn_actual.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.btn_actual.clicked.connect(self._on_actual_clicked)

        # Menu actions -> signals
        self.act_single_page.triggered.connect(
            lambda checked: self._on_view_mode("single", checked)
        )
        self.act_two_page.triggered.connect(
            lambda checked: self._on_view_mode("two", checked)
        )
        self.act_enable_scrolling.toggled.connect(self.scrollingToggled)
        self.act_actual_size.triggered.connect(self._on_actual_from_menu)
        self.act_zoom_page.triggered.connect(self.zoomPageLevelRequested)
        self.act_fit_width.triggered.connect(self.fitWidthRequested)
        self.act_fit_height.triggered.connect(self.fitHeightRequested)
        self.act_fit_visible.triggered.connect(self.fitVisibleRequested)
        self.act_read_mode.toggled.connect(self.readModeToggled)
        self.act_full_screen.toggled.connect(self.fullScreenToggled)
        self.act_marquee_zoom.toggled.connect(self.marqueeZoomToggled)

        # Zoom buttons
        self.btn_zoom_in = QToolButton()
        self.btn_zoom_in.setText("+")
        self.btn_zoom_in.clicked.connect(self.zoomInRequested)
        layout.addWidget(self.btn_zoom_in, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_zoom_out = QToolButton()
        self.btn_zoom_out.setText("-")
        self.btn_zoom_out.clicked.connect(self.zoomOutRequested)
        layout.addWidget(self.btn_zoom_out, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch(1)

        self.setWidget(w)
        self.setMinimumWidth(80)
        self._set_enabled(False)

    # ---------- Public API ----------

    def attach_viewer(self, viewer: clsPDFBMViewer) -> None:
        self._viewer = viewer
        viewer.pdfLoaded.connect(self.on_pdf_loaded)
        viewer.pdfClosed.connect(self.on_pdf_closed)
        viewer.pageChanged.connect(self.on_page_changed)
        viewer.scroll_area.viewport().installEventFilter(self)

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

        self.act_single_page.setChecked(True)
        self.act_two_page.setChecked(False)
        self.act_enable_scrolling.setChecked(True)
        self.act_actual_size.setChecked(True)
        self.act_read_mode.setChecked(False)
        self.act_full_screen.setChecked(False)
        self.act_marquee_zoom.setChecked(False)

    def on_pdf_closed(self) -> None:
        self._total_pages = 0
        self.total_label.setText("0")
        self.page_spin.setMaximum(1)
        self.page_spin.setValue(1)
        self._set_enabled(False)

    def on_page_changed(self, page_index: int) -> None:
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
        if self._ignore_spin_change or self._total_pages <= 0:
            return
        page_1_based = self.page_spin.value()
        page_index = max(0, min(self._total_pages - 1, page_1_based - 1))
        self.pageRequested.emit(page_index)

    def _on_actual_clicked(self):
        self.actualSizeRequested.emit()
        self.act_actual_size.setChecked(True)

    def _on_actual_from_menu(self):
        self.actualSizeRequested.emit()
        self.act_actual_size.setChecked(True)

    def _on_view_mode(self, mode: str, checked: bool):
        if not checked:
            return
        self.viewModeRequested.emit(mode)

    # ---------- Middle-mouse zoom filter ----------

def eventFilter(self, obj, event):
    # --- Marquee zoom on viewport ---
    if obj is self.scroll_area.viewport():
        if self._marquee_zoom_enabled:
            if isinstance(event, QMouseEvent):
                t = event.type()
                if (
                    t == QEvent.Type.MouseButtonPress
                    and event.button() == Qt.MouseButton.LeftButton
                ):
                    self._marquee_origin = event.position().toPoint()
                    self._rubber_band.setGeometry(
                        QRect(self._marquee_origin, self._marquee_origin)
                    )
                    self._rubber_band.show()
                    return True
                elif (
                    t == QEvent.Type.MouseMove
                    and self._rubber_band.isVisible()
                    and self._marquee_origin is not None
                ):
                    rect = QRect(
                        self._marquee_origin, event.position().toPoint()
                    ).normalized()
                    self._rubber_band.setGeometry(rect)
                    return True
                elif (
                    t == QEvent.Type.MouseButtonRelease
                    and event.button() == Qt.MouseButton.LeftButton
                    and self._rubber_band.isVisible()
                    and self._marquee_origin is not None
                ):
                    self._rubber_band.hide()
                    rect = QRect(
                        self._marquee_origin, event.position().toPoint()
                    ).normalized()
                    self._apply_marquee_zoom(rect)
                    self._marquee_origin = None
                    self._marquee_zoom_enabled = False
                    self.nav_toolbar.act_marquee_zoom.setChecked(False)
                    return True

        # --- Wheel scroll to change pages when not in marquee mode ---
        if isinstance(event, QWheelEvent) and not self._marquee_zoom_enabled:
            vbar = self.scroll_area.verticalScrollBar()
            delta = event.angleDelta().y()

            # Scroll down at bottom -> next page
            if (
                delta < 0
                and vbar.value() == vbar.maximum()
                and self.current_page_index < self.page_count - 1
            ):
                self.next_page()
                return True

            # Scroll up at top -> previous page
            if (
                delta > 0
                and vbar.value() == vbar.minimum()
                and self.current_page_index > 0
            ):
                self.prev_page()
                return True

    return super().eventFilter(obj, event)


# ============================================================================
# Example main window using clsPDFBMViewer + PDFViewerToolBar
# ============================================================================


class PDFBMViewer(clsPDFBMViewer):
    """
    Example application on top of clsPDFBMViewer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("PDF Bookmark Viewer")
        self.resize(1200, 800)

        self._read_mode = False
        self._full_screen = False
        self._marquee_zoom_enabled = False
        self._marquee_origin = None
        self._rubber_band = QRubberBand(
            QRubberBand.Shape.Rectangle, self.scroll_area.viewport()
        )
        self.scroll_area.viewport().installEventFilter(self)

        self._create_actions()
        self._create_menus()
        self._create_top_toolbar()

        self.nav_toolbar = PDFViewerToolBar(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.nav_toolbar)
        self.nav_toolbar.attach_viewer(self)

        self.view_menu.addAction(self.nav_toolbar.toggleViewAction())
        self._connect_signals()

    # ---------- UI chrome ----------

    def _create_actions(self):
        self.act_open = QAction("Open…", self)
        self.act_open.setShortcut("Ctrl+O")
        self.act_open.triggered.connect(self._open_file_dialog)

        self.act_close = QAction("Close PDF", self)
        self.act_close.triggered.connect(self.close_pdf)

        self.act_exit = QAction("Exit", self)
        self.act_exit.setShortcut("Ctrl+Q")
        self.act_exit.triggered.connect(self.close)

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
        tb = QToolBar("Main Toolbar", self)
        tb.setMovable(True)
        self.addToolBar(tb)
        self.main_toolbar = tb

        tb.addAction(self.act_open)
        tb.addAction(self.act_close)
        tb.addSeparator()
        tb.addAction(self.act_prev)
        tb.addAction(self.act_next)

    def _connect_signals(self):
        self.errorOccurred.connect(self._on_error)
        self.pdfLoaded.connect(self._on_pdf_loaded)

        self.nav_toolbar.pageRequested.connect(self.go_to_page)
        self.nav_toolbar.nextPageRequested.connect(self.next_page)
        self.nav_toolbar.prevPageRequested.connect(self.prev_page)
        self.nav_toolbar.zoomInRequested.connect(self.zoom_in)
        self.nav_toolbar.zoomOutRequested.connect(self.zoom_out)
        self.nav_toolbar.actualSizeRequested.connect(self.reset_zoom)

        self.nav_toolbar.viewModeRequested.connect(self.set_view_mode)
        self.nav_toolbar.scrollingToggled.connect(self.set_scrolling_enabled)
        self.nav_toolbar.zoomPageLevelRequested.connect(self.fit_to_page)
        self.nav_toolbar.fitWidthRequested.connect(self.fit_to_width)
        self.nav_toolbar.fitHeightRequested.connect(self.fit_to_height)
        self.nav_toolbar.fitVisibleRequested.connect(self.fit_visible_content)

        self.nav_toolbar.readModeToggled.connect(self._set_read_mode)
        self.nav_toolbar.fullScreenToggled.connect(self._set_full_screen)
        self.nav_toolbar.marqueeZoomToggled.connect(self._set_marquee_zoom_mode)

    # ---------- Advanced modes ----------

    def _set_read_mode(self, enabled: bool):
        self._read_mode = enabled
        self.menuBar().setVisible(not enabled)
        self.main_toolbar.setVisible(not enabled)
        self.nav_toolbar.setVisible(not enabled)
        self.bookmark_dock.setVisible(not enabled)

    def _set_full_screen(self, enabled: bool):
        self._full_screen = enabled
        if enabled:
            self.showFullScreen()
        else:
            self.showNormal()

    def _set_marquee_zoom_mode(self, enabled: bool):
        self._marquee_zoom_enabled = enabled

    # ---------- Marquee zoom on viewport ----------

    def eventFilter(self, obj, event):
        if obj is self.scroll_area.viewport() and self._marquee_zoom_enabled:
            if isinstance(event, QMouseEvent):
                t = event.type()
                if (
                    t == QEvent.Type.MouseButtonPress
                    and event.button() == Qt.MouseButton.LeftButton
                ):
                    self._marquee_origin = event.position().toPoint()
                    self._rubber_band.setGeometry(
                        QRect(self._marquee_origin, self._marquee_origin)
                    )
                    self._rubber_band.show()
                    return True
                elif (
                    t == QEvent.Type.MouseMove
                    and self._rubber_band.isVisible()
                    and self._marquee_origin is not None
                ):
                    rect = QRect(
                        self._marquee_origin, event.position().toPoint()
                    ).normalized()
                    self._rubber_band.setGeometry(rect)
                    return True
                elif (
                    t == QEvent.Type.MouseButtonRelease
                    and event.button() == Qt.MouseButton.LeftButton
                    and self._rubber_band.isVisible()
                    and self._marquee_origin is not None
                ):
                    self._rubber_band.hide()
                    rect = QRect(
                        self._marquee_origin, event.position().toPoint()
                    ).normalized()
                    self._apply_marquee_zoom(rect)
                    self._marquee_origin = None
                    self._marquee_zoom_enabled = False
                    self.nav_toolbar.act_marquee_zoom.setChecked(False)
                    return True

        return super().eventFilter(obj, event)

    def _apply_marquee_zoom(self, rect: QRect):
        if rect.width() < 10 or rect.height() < 10:
            return
        view_w = self.scroll_area.viewport().width()
        view_h = self.scroll_area.viewport().height()
        if view_w <= 0 or view_h <= 0:
            return

        factor = min(view_w / rect.width(), view_h / rect.height())
        old_zoom = self.zoom_factor
        self.set_zoom(old_zoom * factor)

        hbar = self.scroll_area.horizontalScrollBar()
        vbar = self.scroll_area.verticalScrollBar()
        center = rect.center()
        hbar.setValue(int(center.x() * factor - view_w / 2))
        vbar.setValue(int(center.y() * factor - view_h / 2))

    # ---------- Other overrides ----------

    def keyPressEvent(self, event):
        # ESC to exit full-screen (PyQt6: Qt.Key.Key_Escape)
        if event.key() == Qt.Key.Key_Escape and self._full_screen:
            self.nav_toolbar.act_full_screen.setChecked(False)
            self._set_full_screen(False)
        else:
            super().keyPressEvent(event)

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