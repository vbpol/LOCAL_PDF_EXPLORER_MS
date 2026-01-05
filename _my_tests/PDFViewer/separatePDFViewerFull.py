#!/usr/bin/env python3
"""
Continuous multi-page PDF viewer (PyQt6 + PyMuPDF) with:

- Continuous vertical scrolling through all pages.
- Lazy rendering: only pages near the visible area are rendered.
- Right dock: bookmark/outline tree.
- Left dock: Adobe-like vertical toolbar:
    * page number, page up/down
    * zoom +/-
    * 1:1 button with menu:
        - Single-page view / Two-page view (placeholders)
        - Enable scrolling
        - Actual size
        - Zoom to page level (fit current page)
        - Fit to width
        - Fit height
        - Fit visible content
        - Read mode
        - Full screen mode
        - Marquee zoom (one-shot)

Requirements:
    pip install PyQt6 pymupdf
"""

from __future__ import annotations

import os
import sys
from typing import Optional, List

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
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QTreeWidget,
    QTreeWidgetItem,
    QDockWidget,
    QToolBar,
    QMessageBox,
    QToolButton,
    QSpinBox,
    QFrame,
    QMenuBar,
    QMenu,
    QRubberBand,
)

# ============================================================================
# Continuous PDF viewer with lazy rendering
# ============================================================================


class ContinuousPDFViewer(QMainWindow):
    """
    Continuous multi-page PDF viewer using PyMuPDF and lazy rendering.

    Signals
    -------
    - errorOccurred(str)
    - pdfLoaded(path: str, page_count: int)
    - pdfClosed()
    - pageChanged(page_index: int)
    """

    errorOccurred = pyqtSignal(str)
    pdfLoaded = pyqtSignal(str, int)
    pdfClosed = pyqtSignal()
    pageChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._doc = None          # fitz.Document or None
        self._pdf_path: Optional[str] = None
        self._zoom: float = 1.0
        self._zoom_step: float = 1.25
        self._min_zoom: float = 0.25
        self._max_zoom: float = 5.0

        self._page_rects = []     # list of fitz.Rect (one per page)
        self.page_labels: List[QLabel] = []

        self._current_page: int = 0

        # Advanced modes
        self._read_mode = False
        self._full_screen = False
        self._marquee_zoom_enabled = False
        self._marquee_origin = None
        self._rubber_band: Optional[QRubberBand] = None

        self._init_ui()

    # ---------------- UI ----------------

    def _init_ui(self):
        self.setWindowTitle("Continuous PDF Viewer")
        self.resize(1200, 800)

        # Central scroll area with pages stacked vertically
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.pages_container = QWidget()
        self.pages_layout = QVBoxLayout(self.pages_container)
        self.pages_layout.setContentsMargins(10, 10, 10, 10)
        self.pages_layout.setSpacing(20)

        self.scroll_area.setWidget(self.pages_container)
        self.setCentralWidget(self.scroll_area)

        # Rubber band for marquee zoom
        self._rubber_band = QRubberBand(
            QRubberBand.Shape.Rectangle, self.scroll_area.viewport()
        )
        # For marquee zoom / lazy updates on scroll
        self.scroll_area.viewport().installEventFilter(self)
        self.scroll_area.verticalScrollBar().valueChanged.connect(
            self._on_scroll_changed
        )

        # Bookmark dock
        self.bookmark_tree = QTreeWidget()
        self.bookmark_tree.setHeaderHidden(True)
        self.bookmark_tree.itemActivated.connect(self._on_bookmark_activated)
        self.bookmark_tree.itemClicked.connect(self._on_bookmark_activated)

        self.bookmark_dock = QDockWidget("Bookmarks", self)
        self.bookmark_dock.setWidget(self.bookmark_tree)
        self.bookmark_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.bookmark_dock)

        # Top toolbar + menu
        self._create_actions()
        self._create_toolbar()
        self._create_menu()

        self.errorOccurred.connect(self._show_error)

    def _create_actions(self):
        self.act_open = QAction("Open…", self)
        self.act_open.setShortcut("Ctrl+O")
        self.act_open.triggered.connect(self._open_file_dialog)

        self.act_zoom_in = QAction("Zoom in", self)
        self.act_zoom_in.setShortcut("Ctrl++")
        self.act_zoom_in.triggered.connect(self.zoom_in)

        self.act_zoom_out = QAction("Zoom out", self)
        self.act_zoom_out.setShortcut("Ctrl+-")
        self.act_zoom_out.triggered.connect(self.zoom_out)

        self.act_zoom_reset = QAction("Reset (1:1)", self)
        self.act_zoom_reset.setShortcut("Ctrl+0")
        self.act_zoom_reset.triggered.connect(self.reset_zoom)

        self.act_fit_width = QAction("Fit width", self)
        self.act_fit_width.triggered.connect(self.fit_width)

    def _create_toolbar(self):
        tb = QToolBar("Main toolbar", self)
        tb.setMovable(True)
        self.addToolBar(tb)
        self.main_toolbar = tb

        tb.addAction(self.act_open)
        tb.addSeparator()
        tb.addAction(self.act_zoom_out)
        tb.addAction(self.act_zoom_in)
        tb.addAction(self.act_zoom_reset)
        tb.addAction(self.act_fit_width)

    def _create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.act_open)

        self.view_menu = menubar.addMenu("&View")
        self.view_menu.addAction(self.act_zoom_in)
        self.view_menu.addAction(self.act_zoom_out)
        self.view_menu.addAction(self.act_zoom_reset)
        self.view_menu.addAction(self.act_fit_width)

    # ---------------- PDF loading & layout ----------------

    def load_pdf(self, path: str) -> bool:
        """Load a PDF and build continuous view; return True on success."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            self.errorOccurred.emit(
                "PyMuPDF (pymupdf) is required.\nInstall it with:\n"
                "    pip install pymupdf"
            )
            return False

        if not os.path.isfile(path):
            self.errorOccurred.emit(f"File not found:\n{path}")
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
            self.errorOccurred.emit(f"Error opening PDF:\n{e}")
            return False

        self._doc = doc
        self._pdf_path = path
        self.setWindowTitle(f"{os.path.basename(path)} - Continuous PDF Viewer")

        self._zoom = 1.0
        self._current_page = 0
        self._page_rects = []

        # Clear old page widgets
        self._clear_pages()

        # Create labels (one per page), store base rects
        self.page_labels = []
        for i in range(self.page_count):
            page = self._doc.load_page(i)
            rect = page.rect
            self._page_rects.append(rect)

            lbl = QLabel("Loading…")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("background-color: white;")
            # Rough placeholder height so layout has space
            approx_h = max(80, int(rect.height * self._zoom / 1.0))
            lbl.setMinimumHeight(approx_h)

            self.pages_layout.addWidget(lbl)
            self.page_labels.append(lbl)

        self.pages_layout.addStretch(1)

        # Populate bookmarks
        self._load_bookmarks()

        # Let layout settle, then lazy-render visible pages
        QApplication.processEvents()
        self._update_visible_pages()

        self.pdfLoaded.emit(path, self.page_count)
        self.pageChanged.emit(0)
        return True

    def close_pdf(self):
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
        self._doc = None
        self._pdf_path = None
        self._clear_pages()
        self._page_rects = []
        self.page_labels = []
        self.pdfClosed.emit()

    def _clear_pages(self):
        while self.pages_layout.count():
            item = self.pages_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    @property
    def page_count(self) -> int:
        if self._doc is None:
            return 0
        return self._doc.page_count  # type: ignore[union-attr]

    # ---------------- Rendering (lazy) ----------------

    def _render_page(self, index: int):
        """Render a single page at current zoom into its label."""
        if self._doc is None:
            return
        if not (0 <= index < len(self.page_labels)):
            return

        try:
            import fitz
        except ImportError:
            return

        label = self.page_labels[index]
        try:
            page = self._doc.load_page(index)
            mat = fitz.Matrix(self._zoom, self._zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            qpix = QPixmap()
            if qpix.loadFromData(img_bytes, "PNG"):
                label.setPixmap(qpix)
                label.setMinimumSize(qpix.size())
                label.setText("")
                setattr(label, "_rendered_zoom", self._zoom)
            else:
                label.setPixmap(QPixmap())
                label.setText("Render error")
                setattr(label, "_rendered_zoom", None)
        except Exception as e:
            label.setPixmap(QPixmap())
            label.setText(f"Error: {e}")
            setattr(label, "_rendered_zoom", None)

    def _update_visible_pages(self):
        """Lazy rendering: only (re)render pages near the visible area."""
        if self._doc is None or not self.page_labels:
            return

        vbar = self.scroll_area.verticalScrollBar()
        y0 = vbar.value()
        view_h = self.scroll_area.viewport().height()
        if view_h <= 0:
            return
        y1 = y0 + view_h
        visible_rect = QRect(0, y0, self.pages_container.width(), view_h)

        margin = visible_rect.height()
        extended = visible_rect.adjusted(0, -margin, 0, margin)

        for i, label in enumerate(self.page_labels):
            page_geo = label.geometry()  # in container coords
            in_range = page_geo.intersects(extended)
            pix = label.pixmap()
            rendered_zoom = getattr(label, "_rendered_zoom", None)

            if in_range:
                if pix is None or rendered_zoom != self._zoom:
                    self._render_page(i)
            else:
                if pix is not None:
                    label.setPixmap(QPixmap())
                    label.setText("")
                    if i < len(self._page_rects):
                        rect = self._page_rects[i]
                        approx_h = max(80, int(rect.height * self._zoom / 1.0))
                        label.setMinimumHeight(approx_h)
                    setattr(label, "_rendered_zoom", None)

    def _rerender_for_new_zoom(self):
        """Clear existing pixmaps and re-render only visible pages."""
        if self._doc is None:
            return
        for i, label in enumerate(self.page_labels):
            label.setPixmap(QPixmap())
            setattr(label, "_rendered_zoom", None)
            if i < len(self._page_rects):
                rect = self._page_rects[i]
                approx_h = max(80, int(rect.height * self._zoom / 1.0))
                label.setMinimumHeight(approx_h)
        self._update_visible_pages()

    # ---------------- Zoom operations ----------------

    def zoom_in(self):
        if self._doc is None:
            return
        self._zoom = min(self._max_zoom, self._zoom * self._zoom_step)
        self._rerender_for_new_zoom()

    def zoom_out(self):
        if self._doc is None:
            return
        self._zoom = max(self._min_zoom, self._zoom / self._zoom_step)
        self._rerender_for_new_zoom()

    def reset_zoom(self):
        if self._doc is None:
            return
        self._zoom = 1.0
        self._rerender_for_new_zoom()

    def fit_width(self):
        """Zoom so that the current page fits the viewport width."""
        if self._doc is None or not self._page_rects:
            return

        rect = self._page_rects[self._current_page]
        if rect.width <= 0:
            return

        view_w = self.scroll_area.viewport().width()
        if view_w <= 0:
            return

        zoom = view_w / rect.width
        self._zoom = max(self._min_zoom, min(self._max_zoom, zoom))
        self._rerender_for_new_zoom()

    def fit_height(self):
        """Zoom so that the current page fits the viewport height."""
        if self._doc is None or not self._page_rects:
            return

        rect = self._page_rects[self._current_page]
        if rect.height <= 0:
            return

        view_h = self.scroll_area.viewport().height()
        if view_h <= 0:
            return

        zoom = view_h / rect.height
        self._zoom = max(self._min_zoom, min(self._max_zoom, zoom))
        self._rerender_for_new_zoom()

    def fit_page_level(self):
        """Fit current page completely into viewport (width & height)."""
        if self._doc is None or not self._page_rects:
            return

        rect = self._page_rects[self._current_page]
        if rect.width <= 0 or rect.height <= 0:
            return

        view_w = self.scroll_area.viewport().width()
        view_h = self.scroll_area.viewport().height()
        if view_w <= 0 or view_h <= 0:
            return

        zoom_w = view_w / rect.width
        zoom_h = view_h / rect.height
        zoom = min(zoom_w, zoom_h)

        self._zoom = max(self._min_zoom, min(self._max_zoom, zoom))
        self._rerender_for_new_zoom()

    def fit_visible_content(self):
        """Approximation: same as fit_width()."""
        self.fit_width()

    # ---------------- Navigation & scrolling ----------------

    def go_to_page(self, index: int):
        """Scroll so that the given 0‑based page index is near top."""
        if not (0 <= index < len(self.page_labels)):
            return
        label = self.page_labels[index]
        y = label.geometry().top()
        vbar = self.scroll_area.verticalScrollBar()
        vbar.setValue(max(0, y - 10))
        if index != self._current_page:
            self._current_page = index
            self.pageChanged.emit(index)
        self._update_visible_pages()

    def _on_scroll_changed(self, value: int):
        """Update current page based on scroll position + lazy render."""
        if not self.page_labels:
            return

        self._update_visible_pages()

        vbar = self.scroll_area.verticalScrollBar()
        vp_h = self.scroll_area.viewport().height()
        center_y = vbar.value() + vp_h // 2

        for i, label in enumerate(self.page_labels):
            g = label.geometry()
            if g.top() <= center_y <= g.bottom():
                if i != self._current_page:
                    self._current_page = i
                    self.pageChanged.emit(i)
                break

    def set_scrolling_enabled(self, enabled: bool):
        """Enable/disable scrollbars."""
        if enabled:
            pol = Qt.ScrollBarPolicy.ScrollBarAsNeeded
        else:
            pol = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        self.scroll_area.setVerticalScrollBarPolicy(pol)
        self.scroll_area.setHorizontalScrollBarPolicy(pol)

    # Dummy hook for view modes (single / two page) from toolbar.
    def set_view_mode(self, mode: str):
        # Continuous layout always used; ignore mode.
        pass

    # ---------------- Bookmarks ----------------

    def _load_bookmarks(self):
        self.bookmark_tree.clear()

        if self._doc is None:
            return

        try:
            toc = self._doc.get_toc()
        except Exception:
            toc = []

        if not toc:
            root = QTreeWidgetItem(["<No bookmarks>"])
            root.setDisabled(True)
            self.bookmark_tree.addTopLevelItem(root)
            return

        level_item_map: dict[int, QTreeWidgetItem] = {
            0: self.bookmark_tree.invisibleRootItem()
        }

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

        self.bookmark_tree.expandToDepth(1)

    def _on_bookmark_activated(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return
        try:
            page_index = int(data)
        except (TypeError, ValueError):
            return
        self.go_to_page(page_index)

    # ---------------- Advanced view modes ----------------

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

    def _apply_marquee_zoom(self, rect: QRect):
        if rect.width() < 10 or rect.height() < 10:
            return

        view_w = self.scroll_area.viewport().width()
        view_h = self.scroll_area.viewport().height()
        if view_w <= 0 or view_h <= 0:
            return

        factor = min(view_w / rect.width(), view_h / rect.height())
        old_zoom = self._zoom
        self._zoom = max(self._min_zoom, min(self._max_zoom, old_zoom * factor))
        self._rerender_for_new_zoom()

        # Roughly center on selection after zoom
        hbar = self.scroll_area.horizontalScrollBar()
        vbar = self.scroll_area.verticalScrollBar()
        center = rect.center()
        hbar.setValue(int(center.x() * factor - view_w / 2))
        vbar.setValue(int(center.y() * factor - view_h / 2))

    # ---------------- Event handling ----------------

    def eventFilter(self, obj, event):
        # Marquee zoom: handled here
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
                    and self._rubquee_valid()
                ):
                    # this branch never hit (typo safe-guard)
                    pass

        return super().eventFilter(obj, event)

    def _rubquee_valid(self):
        # helper for static analyzer; not used at runtime
        return False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_visible_pages()

    def keyPressEvent(self, event):
        # ESC to exit full-screen
        if event.key() == Qt.Key.Key_Escape and self._full_screen:
            self.nav_toolbar.act_full_screen.setChecked(False)
            self._set_full_screen(False)
        else:
            super().keyPressEvent(event)

    # ---------------- Helpers ----------------

    def _open_file_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            "",
            "PDF files (*.pdf);;All files (*)",
        )
        if not fname:
            return
        self.load_pdf(fname)

    def _show_error(self, msg: str):
        QMessageBox.critical(self, "Error", msg)


# ============================================================================
# Side toolbar (Adobe-like) reused for continuous viewer
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

        self._viewer: Optional[ContinuousPDFViewer] = None
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

        # Page up / down
        self.btn_up = QToolButton()
        self.btn_up.setArrowType(Qt.ArrowType.UpArrow)
        self.btn_up.clicked.connect(self._on_prev_clicked)
        layout.addWidget(self.btn_up, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_down = QToolButton()
        self.btn_down.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_down.clicked.connect(self._on_next_clicked)
        layout.addWidget(self.btn_down, 0, Qt.AlignmentFlag.AlignHCenter)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # 1:1 button with menu
        self.btn_actual = QToolButton()
        self.btn_actual.setText("1:1")
        layout.addWidget(self.btn_actual, 0, Qt.AlignmentFlag.AlignHCenter)

        self.view_menu = QMenu(self)

        # Page layout (placeholders)
        self.act_single_page = QAction("Single-page view", self, checkable=True)
        self.act_two_page = QAction("Two-page view", self, checkable=True)
        self.act_single_page.setChecked(True)
        self.view_mode_group = QActionGroup(self)
        self.view_mode_group.addAction(self.act_single_page)
        self.view_mode_group.addAction(self.act_two_page)
        self.view_mode_group.setExclusive(True)

        self.act_show_cover = QAction("Show cover page", self, checkable=True)
        self.act_show_cover.setEnabled(False)

        # Scrolling
        self.act_enable_scrolling = QAction("Enable scrolling", self, checkable=True)
        self.act_enable_scrolling.setChecked(True)

        # Zoom modes
        self.act_actual_size = QAction("Actual size", self, checkable=True)
        self.act_actual_size.setChecked(True)
        self.act_zoom_page = QAction("Zoom to page level", self)
        self.act_fit_width = QAction("Fit to width", self)
        self.act_fit_height = QAction("Fit height", self)
        self.act_fit_visible = QAction("Fit visible content", self)

        # Read/full-screen/marquee
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

    def attach_viewer(self, viewer: ContinuousPDFViewer) -> None:
        """Attach this toolbar to a ContinuousPDFViewer instance."""
        self._viewer = viewer

        viewer.pdfLoaded.connect(self.on_pdf_loaded)
        viewer.pdfClosed.connect(self.on_pdf_closed)
        viewer.pageChanged.connect(self.on_page_changed)

        # Middle mouse + wheel zoom on viewport
        viewer.scroll_area.viewport().installEventFilter(self)

        if viewer.page_count > 0:
            self.on_pdf_loaded(viewer._pdf_path or "", viewer.page_count)
            self.on_page_changed(0)
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
        if (
            self._viewer is not None
            and obj is self._viewer.scroll_area.viewport()
            and isinstance(event, QWheelEvent)
        ):
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
# Main window wiring viewer + toolbar
# ============================================================================


class ContinuousPDFMain(ContinuousPDFViewer):
    """
    ContinuousPDFViewer + side PDFViewerToolBar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Continuous PDF Viewer with Toolbar")

        # Create side toolbar and attach to this viewer
        self.nav_toolbar = PDFViewerToolBar(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.nav_toolbar)
        self.nav_toolbar.attach_viewer(self)

        # Add toggle for side toolbar to View menu
        self.view_menu.addAction(self.nav_toolbar.toggleViewAction())

        # Connect toolbar signals to viewer behavior
        self._connect_toolbar_signals()

    def _connect_toolbar_signals(self):
        self.nav_toolbar.pageRequested.connect(self.go_to_page)
        self.nav_toolbar.nextPageRequested.connect(
            lambda: self.go_to_page(min(self._current_page + 1, self.page_count - 1))
        )
        self.nav_toolbar.prevPageRequested.connect(
            lambda: self.go_to_page(max(self._current_page - 1, 0))
        )
        self.nav_toolbar.zoomInRequested.connect(self.zoom_in)
        self.nav_toolbar.zoomOutRequested.connect(self.zoom_out)
        self.nav_toolbar.actualSizeRequested.connect(self.reset_zoom)

        self.nav_toolbar.viewModeRequested.connect(self.set_view_mode)
        self.nav_toolbar.scrollingToggled.connect(self.set_scrolling_enabled)
        self.nav_toolbar.zoomPageLevelRequested.connect(self.fit_page_level)
        self.nav_toolbar.fitWidthRequested.connect(self.fit_width)
        self.nav_toolbar.fitHeightRequested.connect(self.fit_height)
        self.nav_toolbar.fitVisibleRequested.connect(self.fit_visible_content)

        self.nav_toolbar.readModeToggled.connect(self._set_read_mode)
        self.nav_toolbar.fullScreenToggled.connect(self._set_full_screen)
        self.nav_toolbar.marqueeZoomToggled.connect(self._set_marquee_zoom_mode)


# ============================================================================
# Entry point
# ============================================================================


def main():
    app = QApplication(sys.argv)
    win = ContinuousPDFMain()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()