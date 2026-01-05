Below is a reusable, “scalable” viewer class `clsPDFBMViewer` plus a simple application `PDFBMViewer` that uses it.

- `clsPDFBMViewer` is a `QMainWindow` with:
  - Central PDF page viewer (rendered via PyMuPDF / `fitz`).
  - Dockable **right** bookmark panel (`QDockWidget` + `QTreeWidget`).
  - Clear public API (“endpoints”) like `load_pdf()`, `go_to_page()`, `zoom_in()`, etc.
  - Signals: `pdfLoaded`, `pageChanged`, `bookmarksLoaded`, `errorOccurred`.

- `PDFBMViewer` is a small GUI around `clsPDFBMViewer` with:
  - File → Open / Close / Exit
  - View → Zoom in/out/reset, toggle bookmark panel
  - Toolbar buttons for common actions

---

### Requirements

```bash
pip install PyQt6 pymupdf
```

---

### Code: `pdfbm_viewer.py`

```python
#!/usr/bin/env python3
"""
PDFBMViewer
===========

Core class: clsPDFBMViewer
- QMainWindow with:
    * Central PDF page viewer
    * Dockable bookmark (outline) panel on the right
- Uses PyMuPDF (fitz) for PDF loading, rendering, and TOC/bookmarks.

Example GUI: PDFBMViewer
- Subclass of clsPDFBMViewer adding menus/toolbars and file open dialog.

Dependencies:
    pip install PyQt6 pymupdf
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap
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
)


# ---------------------------------------------------------------------------
# Core viewer class
# ---------------------------------------------------------------------------

class clsPDFBMViewer(QMainWindow):
    """
    Reusable PDF viewer with a dockable bookmark panel.

    Public API (endpoints)
    ----------------------
    - load_pdf(path: str) -> bool
    - close_pdf() -> None
    - go_to_page(index: int) -> None        # 0-based
    - next_page() / prev_page()
    - set_zoom(factor: float)
    - zoom_in() / zoom_out() / reset_zoom()
    - toggle_bookmark_panel(visible: bool)  # or via dock's toggleViewAction()

    Properties
    ----------
    - pdf_path: Optional[str]
    - page_count: int
    - current_page_index: int
    - zoom_factor: float

    Signals
    -------
    - pdfLoaded(path: str, page_count: int)
    - pageChanged(page_index: int)
    - bookmarksLoaded(count: int)
    - errorOccurred(message: str)
    """

    pdfLoaded = pyqtSignal(str, int)
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

    # ------------------------ Public API / endpoints ------------------------

    def load_pdf(self, path: str) -> bool:
        """
        Load a PDF file.

        Returns True on success, False on failure (and emits errorOccurred).
        """
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

        # Convert PyMuPDF pixmap -> QPixmap via PNG bytes (safe & simple)
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

            # Normalize
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
            # Store 0-based page index in UserRole
            item.setData(0, Qt.ItemDataRole.UserRole, page - 1)

            parent = level_item_map.get(level - 1, level_item_map[0])
            parent.addChild(item)
            level_item_map[level] = item
            count += 1

        self.bookmark_tree.expandToDepth(1)
        self.bookmarksLoaded.emit(count)

    def _on_bookmark_activated(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle click/double-click on a bookmark item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return
        try:
            page_idx = int(data)
        except (TypeError, ValueError):
            return
        self.go_to_page(page_idx)


# ---------------------------------------------------------------------------
# Example GUI application using clsPDFBMViewer
# ---------------------------------------------------------------------------

class PDFBMViewer(clsPDFBMViewer):
    """
    Example application built on top of clsPDFBMViewer.
    Adds menus, toolbar, and basic actions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("PDF Bookmark Viewer")
        self.resize(1200, 800)

        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._connect_signals()

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

        # View / navigation actions
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

        self.act_zoom_reset = QAction("Reset zoom", self)
        self.act_zoom_reset.setShortcut("Ctrl+0")
        self.act_zoom_reset.triggered.connect(self.reset_zoom)

        self.act_toggle_bookmarks = self.bookmark_dock.toggleViewAction()
        self.act_toggle_bookmarks.setText("Show bookmarks panel")

    def _create_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.act_open)
        file_menu.addAction(self.act_close)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.act_next)
        view_menu.addAction(self.act_prev)
        view_menu.addSeparator()
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_zoom_reset)
        view_menu.addSeparator()
        view_menu.addAction(self.act_toggle_bookmarks)

    def _create_toolbar(self):
        tb = QToolBar("Main Toolbar", self)
        tb.setMovable(True)
        self.addToolBar(tb)

        tb.addAction(self.act_open)
        tb.addSeparator()
        tb.addAction(self.act_prev)
        tb.addAction(self.act_next)
        tb.addSeparator()
        tb.addAction(self.act_zoom_out)
        tb.addAction(self.act_zoom_in)
        tb.addAction(self.act_zoom_reset)
        tb.addSeparator()
        tb.addAction(self.act_toggle_bookmarks)

    def _connect_signals(self):
        self.errorOccurred.connect(self._on_error)
        self.pdfLoaded.connect(self._on_pdf_loaded)
        
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    win = PDFBMViewer()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

---

This gives you:

- A reusable `clsPDFBMViewer` component (with clear methods and signals) that you can embed or subclass in other apps.
- A working `PDFBMViewer` application demonstrating how to use the class, with a dockable right‑side bookmarks panel for navigation similar to your screenshot.