#!/usr/bin/env python3
"""
PDF bookmark viewer with:

- Single-page PDF viewer using PyMuPDF.
- Left navigation dock (page number, page up/down, zoom, 1:1).
- Right bookmark dock (QTreeWidget) driven by a reusable model:
    * PDFBookmarkModel  (logic: load/generate/save bookmarks)
    * PDFBookmarkDock   (UI: dockable panel + toolbar)

If a PDF has no bookmarks:
- Users can generate bookmarks automatically (font-size heuristic).
- Save them back to the same PDF or to "<name>_with_bookmarks.pdf".

Requirements:
    pip install PyQt6 pymupdf
"""

from __future__ import annotations

import os
import sys
from typing import Optional, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QDockWidget,
    QToolBar,
    QMessageBox,
    QToolButton,
    QSpinBox,
    QFrame,
    QMenuBar,
    QTreeWidget,
    QTreeWidgetItem,
    QHBoxLayout,
)

# ============================================================================
# Bookmark logic model (no UI)
# ============================================================================
from PDFBookmarkModelV6 import PDFBookmarkModel

# ============================================================================
# Bookmark dock (UI) using the model
# ============================================================================


class PDFBookmarkDock(QDockWidget):
    """
    Dockable bookmark panel with its own small toolbar.

    Reusable endpoints
    ------------------
    - set_model(model: PDFBookmarkModel)
    - refresh()      # reload tree from model.toc

    Signals
    -------
    - bookmarkActivated(page_index: int)  # 0-based
    """

    bookmarkActivated = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__("Bookmarks", parent)

        self.model: Optional[PDFBookmarkModel] = None

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemActivated.connect(self._on_item_activated)
        self.tree.itemClicked.connect(self._on_item_activated)

        # Toolbar inside the dock
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(self.toolbar.iconSize())
        self.toolbar.setMovable(False)

        self.act_generate = QAction("Generate", self)
        self.act_generate.setToolTip("Generate bookmarks automatically")
        self.act_generate.triggered.connect(self._generate_bookmarks)

        self.act_save_inplace = QAction("Save in PDF", self)
        self.act_save_inplace.setToolTip("Write bookmarks into this PDF")
        self.act_save_inplace.triggered.connect(self._save_inplace)

        self.act_save_copy = QAction("Save as _with_bookmarks", self)
        self.act_save_copy.setToolTip("Save a copy with bookmarks added")
        self.act_save_copy.triggered.connect(self._save_copy)

        self.act_reload = QAction("Reload", self)
        self.act_reload.setToolTip("Reload bookmarks from PDF")
        self.act_reload.triggered.connect(self.refresh)

        self.toolbar.addAction(self.act_generate)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_save_inplace)
        self.toolbar.addAction(self.act_save_copy)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_reload)

        # Layout inside dock
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self.toolbar)
        v.addWidget(self.tree)

        self.setWidget(container)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self._update_actions()

    # ----- public API -----

    def set_model(self, model: Optional[PDFBookmarkModel]):
        self.model = model
        self.refresh()

    def refresh(self):
        """Reload tree from model.toc."""
        self.tree.clear()

        if self.model is None or self.model.doc is None:
            self._update_actions()
            return

        toc = self.model.get_toc()
        if not toc:
            root = QTreeWidgetItem(["<No bookmarks> (use Generate)"])
            root.setDisabled(True)
            self.tree.addTopLevelItem(root)
            self._update_actions()
            return

        level_item_map: dict[int, QTreeWidgetItem] = {
            0: self.tree.invisibleRootItem()
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

            item = QTreeWidgetItem([title])
            # store 0-based page index
            item.setData(0, Qt.ItemDataRole.UserRole, page - 1)

            parent = level_item_map.get(level - 1, level_item_map[0])
            parent.addChild(item)
            level_item_map[level] = item

        self.tree.expandToDepth(1)
        self._update_actions()

    # ----- internal helpers -----

    def _update_actions(self):
        has_doc = self.model is not None and self.model.doc is not None
        has_bm = has_doc and self.model.has_bookmarks() if self.model else False
        modified = has_doc and self.model.modified if self.model else False

        self.act_generate.setEnabled(has_doc)
        self.act_save_inplace.setEnabled(has_doc and has_bm)
        self.act_save_copy.setEnabled(has_doc and has_bm)
        self.act_reload.setEnabled(has_doc)

    def _on_item_activated(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return
        try:
            page_index = int(data)
        except (TypeError, ValueError):
            return
        self.bookmarkActivated.emit(page_index)

    # ----- toolbar actions -----

    def _generate_bookmarks(self):
        if self.model is None or self.model.doc is None:
            return

        # simple dialog: ask for threshold? For now, fixed 16.0
        try:
            count = self.model.auto_generate_toc(font_threshold=16.0)
        except Exception as e:
            QMessageBox.critical(self, "Generate bookmarks", str(e))
            return

        if count == 0:
            QMessageBox.information(
                self,
                "Generate bookmarks",
                "No headings found with current heuristic.\n"
                "Try a lower font threshold in the code.",
            )
        else:
            QMessageBox.information(
                self,
                "Generate bookmarks",
                f"Generated {count} bookmark entries.\n"
                "You can now save them into the PDF or as a copy.",
            )
        self.refresh()

    def _save_inplace(self):
        if self.model is None:
            return
        try:
            self.model.save_inplace()
        except Exception as e:
            QMessageBox.critical(self, "Save bookmarks", str(e))
            return
        QMessageBox.information(
            self,
            "Save bookmarks",
            f"Bookmarks saved into:\n{self.model.pdf_path}",
        )
        self._update_actions()

    def _save_copy(self):
        if self.model is None:
            return
        try:
            out_path = self.model.save_copy()
        except Exception as e:
            QMessageBox.critical(self, "Save copy", str(e))
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Save copy with bookmarks")
        msg.setText(f"Bookmarks saved into:\n{out_path}\n\nOpen this file?")
        open_btn = msg.addButton("Open copy", QMessageBox.ButtonRole.AcceptRole)
        close_btn = msg.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() is open_btn:
            # ask main window (parent) to open it; simplest is emit a signal,
            # but for this example we just use QFileDialog-style call from parent
            parent = self.parent()
            if isinstance(parent, PDFBookmarkViewerMain):
                parent.load_pdf(out_path)
        self._update_actions()


# ============================================================================
# Navigation toolbar dock (simple)
# ============================================================================


class PDFViewerToolBar(QDockWidget):
    """
    Dockable navigation/zoom toolbar (simple version).

    Signals
    -------
    - pageRequested(page_index: int)   # 0-based
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

        self._total_pages = 0
        self._ignore_spin = bool(False)

        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(4)
        v.setAlignment(Qt.AlignmentFlag.AlignTop)

        # page spin
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setValue(1)
        self.page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_spin.setFixedWidth(50)
        self.page_spin.editingFinished.connect(self._on_page_spin_edited)
        v.addWidget(self.page_spin, 0, Qt.AlignmentFlag.AlignHCenter)

        # total pages label
        self.lbl_total = QLabel("0")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.lbl_total, 0, Qt.AlignmentFlag.AlignHCenter)

        # up/down
        self.btn_up = QToolButton()
        self.btn_up.setArrowType(Qt.ArrowType.UpArrow)
        self.btn_up.clicked.connect(self._on_prev_clicked)
        v.addWidget(self.btn_up, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_down = QToolButton()
        self.btn_down.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_down.clicked.connect(self._on_next_clicked)
        v.addWidget(self.btn_down, 0, Qt.AlignmentFlag.AlignHCenter)

        # separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        v.addWidget(sep)

        # 1:1
        self.btn_actual = QToolButton()
        self.btn_actual.setText("1:1")
        self.btn_actual.clicked.connect(self.actualSizeRequested)
        v.addWidget(self.btn_actual, 0, Qt.AlignmentFlag.AlignHCenter)

        # zoom +
        self.btn_zoom_in = QToolButton()
        self.btn_zoom_in.setText("+")
        self.btn_zoom_in.clicked.connect(self.zoomInRequested)
        v.addWidget(self.btn_zoom_in, 0, Qt.AlignmentFlag.AlignHCenter)

        # zoom -
        self.btn_zoom_out = QToolButton()
        self.btn_zoom_out.setText("-")
        self.btn_zoom_out.clicked.connect(self.zoomOutRequested)
        v.addWidget(self.btn_zoom_out, 0, Qt.AlignmentFlag.AlignHCenter)

        v.addStretch(1)

        self.setWidget(w)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self._set_enabled(False)

    # ----- public helpers -----

    def set_page_info(self, current_index: int, total_pages: int):
        self._total_pages = max(0, total_pages)
        self.lbl_total.setText(str(self._total_pages))
        self.page_spin.setMaximum(max(1, self._total_pages))
        self._ignore_spin = True
        self.page_spin.setValue(current_index + 1 if total_pages > 0 else 1)
        self._ignore_spin = False
        self._set_enabled(total_pages > 0)

    # ----- internals -----

    def _set_enabled(self, enabled: bool):
        for w in [
            self.page_spin,
            self.lbl_total,
            self.btn_up,
            self.btn_down,
            self.btn_actual,
            self.btn_zoom_in,
            self.btn_zoom_out,
        ]:
            w.setEnabled(enabled)

    def _on_prev_clicked(self):
        self.prevPageRequested.emit()

    def _on_next_clicked(self):
        self.nextPageRequested.emit()

    def _on_page_spin_edited(self):
        if self._ignore_spin or self._total_pages <= 0:
            return
        idx = self.page_spin.value() - 1
        idx = max(0, min(self._total_pages - 1, idx))
        self.pageRequested.emit(idx)


# ============================================================================
# Core single-page viewer (no menus/docks)
# ============================================================================


class PDFPageViewer(QMainWindow):
    """
    Simple single-page PDF viewer using PyMuPDF.

    Signals
    -------
    - pdfLoaded(path: str, page_count: int)
    - pdfClosed()
    - pageChanged(page_index: int)
    - errorOccurred(message: str)
    """

    pdfLoaded = pyqtSignal(str, int)
    pdfClosed = pyqtSignal()
    pageChanged = pyqtSignal(int)
    errorOccurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._doc = None           # type: ignore[assignment]
        self._pdf_path: Optional[str] = None
        self._current_page: int = 0
        self._zoom: float = 1.0
        self._min_zoom: float = 0.25
        self._max_zoom: float = 5.0

        self._init_ui()

    def _init_ui(self):
        self.page_label = QLabel("Open a PDF to begin")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("background-color: #808080; color: white;")

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.page_label)
        self.setCentralWidget(self.scroll_area)

    # ----- properties -----

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

    # ----- core API -----

    def load_pdf(self, path: str) -> bool:
        """Open a PDF file."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            self.errorOccurred.emit(
                "PyMuPDF (pymupdf) is required.\nInstall with: pip install pymupdf"
            )
            return False

        if not os.path.isfile(path):
            self.errorOccurred.emit(f"File not found:\n{path}")
            return False

        # close existing
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
        self._current_page = 0
        self._zoom = 1.0

        self._render_current_page()
        self.pdfLoaded.emit(path, self.page_count)
        return True

    def close_pdf(self):
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
        self.pdfClosed.emit()

    def go_to_page(self, index: int):
        if self._doc is None:
            return
        if index < 0 or index >= self.page_count:
            return
        self._current_page = index
        self._render_current_page()
        self.pageChanged.emit(index)

    def next_page(self):
        self.go_to_page(self._current_page + 1)

    def prev_page(self):
        self.go_to_page(self._current_page - 1)

    def set_zoom(self, factor: float):
        factor = max(self._min_zoom, min(self._max_zoom, factor))
        if abs(factor - self._zoom) < 1e-3:
            return
        self._zoom = factor
        self._render_current_page()

    def zoom_in(self):
        self.set_zoom(self._zoom * 1.25)

    def zoom_out(self):
        self.set_zoom(self._zoom / 1.25)

    def reset_zoom(self):
        self.set_zoom(1.0)

    # ----- rendering -----

    def _render_current_page(self):
        if self._doc is None:
            self.page_label.setText("No document loaded")
            self.page_label.setPixmap(QPixmap())
            return

        try:
            import fitz
        except ImportError:
            self.errorOccurred.emit(
                "PyMuPDF (pymupdf) is required.\nInstall with: pip install pymupdf"
            )
            return

        try:
            page = self._doc.load_page(self._current_page)
            mat = fitz.Matrix(self._zoom, self._zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            qpix = QPixmap()
            if not qpix.loadFromData(img_bytes, "PNG"):
                self.errorOccurred.emit("Failed to convert page image.")
                return
        except Exception as e:
            self.errorOccurred.emit(f"Error rendering page:\n{e}")
            return

        self.page_label.setPixmap(qpix)
        self.page_label.adjustSize()


# ============================================================================
# Main window: viewer + nav dock + bookmark dock
# ============================================================================


class PDFBookmarkViewerMain(PDFPageViewer):
    """
    Complete application window:

    - Central: single-page viewer (PDFPageViewer).
    - Left dock: PDFViewerToolBar.
    - Right dock: PDFBookmarkDock using PDFBookmarkModel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("PDF Bookmark Viewer")
        self.resize(1200, 800)

        # Bookmark model & dock
        self.bookmark_model = PDFBookmarkModel(self)
        self.bookmark_dock = PDFBookmarkDock(self)
        self.bookmark_dock.set_model(self.bookmark_model)
        self.bookmark_dock.bookmarkActivated.connect(self.go_to_page)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.bookmark_dock)

        # Navigation dock
        self.nav_dock = PDFViewerToolBar(self)
        self.nav_dock.pageRequested.connect(self.go_to_page)
        self.nav_dock.nextPageRequested.connect(self.next_page)
        self.nav_dock.prevPageRequested.connect(self.prev_page)
        self.nav_dock.zoomInRequested.connect(self.zoom_in)
        self.nav_dock.zoomOutRequested.connect(self.zoom_out)
        self.nav_dock.actualSizeRequested.connect(self.reset_zoom)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.nav_dock)

        # Menus & toolbar
        self._create_actions()
        self._create_menus()
        self._create_toolbar()

        # Signals from core viewer
        self.errorOccurred.connect(self._on_error)
        self.pdfLoaded.connect(self._on_pdf_loaded)
        self.pdfClosed.connect(self._on_pdf_closed)
        self.pageChanged.connect(self._on_page_changed)

    # ----- menus / toolbar -----

    def _create_actions(self):
        self.act_open = QAction("Open…", self)
        self.act_open.setShortcut("Ctrl+O")
        self.act_open.triggered.connect(self._open_file_dialog)

        self.act_close = QAction("Close PDF", self)
        self.act_close.triggered.connect(self.close_pdf)

        self.act_exit = QAction("Exit", self)
        self.act_exit.setShortcut("Ctrl+Q")
        self.act_exit.triggered.connect(self.close)

        self.act_prev = QAction("Previous page", self)
        self.act_prev.setShortcut("PgUp")
        self.act_prev.triggered.connect(self.prev_page)

        self.act_next = QAction("Next page", self)
        self.act_next.setShortcut("PgDown")
        self.act_next.triggered.connect(self.next_page)

        self.act_zoom_in = QAction("Zoom in", self)
        self.act_zoom_in.setShortcut("Ctrl++")
        self.act_zoom_in.triggered.connect(self.zoom_in)

        self.act_zoom_out = QAction("Zoom out", self)
        self.act_zoom_out.setShortcut("Ctrl+-")
        self.act_zoom_out.triggered.connect(self.zoom_out)

        self.act_zoom_reset = QAction("Actual size (1:1)", self)
        self.act_zoom_reset.setShortcut("Ctrl+0")
        self.act_zoom_reset.triggered.connect(self.reset_zoom)

        self.act_toggle_bm = self.bookmark_dock.toggleViewAction()
        self.act_toggle_bm.setText("Show bookmark panel")

        self.act_toggle_nav = self.nav_dock.toggleViewAction()
        self.act_toggle_nav.setText("Show navigation panel")

    def _create_menus(self):
        menubar: QMenuBar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.act_open)
        file_menu.addAction(self.act_close)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.act_prev)
        view_menu.addAction(self.act_next)
        view_menu.addSeparator()
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_zoom_reset)
        view_menu.addSeparator()
        view_menu.addAction(self.act_toggle_nav)
        view_menu.addAction(self.act_toggle_bm)

    def _create_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setMovable(True)
        self.addToolBar(tb)

        tb.addAction(self.act_open)
        tb.addAction(self.act_close)
        tb.addSeparator()
        tb.addAction(self.act_prev)
        tb.addAction(self.act_next)

    # ----- slots for viewer signals -----

    def _on_error(self, message: str):
        QMessageBox.critical(self, "Error", message)

    def _on_pdf_loaded(self, path: str, page_count: int):
        self.setWindowTitle(f"{os.path.basename(path)} - PDF Bookmark Viewer")
        # attach doc to bookmark model & refresh
        self.bookmark_model.set_document(self._doc, self._pdf_path)
        self.bookmark_dock.refresh()
        self.nav_dock.set_page_info(0, page_count)
        # if no bookmarks, we just show "<No bookmarks> (use Generate)"

    def _on_pdf_closed(self):
        self.setWindowTitle("PDF Bookmark Viewer")
        self.bookmark_model.clear()
        self.bookmark_dock.refresh()
        self.nav_dock.set_page_info(0, 0)

    def _on_page_changed(self, page_index: int):
        self.nav_dock.set_page_info(page_index, self.page_count)

    # ----- helpers -----

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


# ============================================================================
# Entry point
# ============================================================================


def main():
    app = QApplication(sys.argv)
    win = PDFBookmarkViewerMain()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()