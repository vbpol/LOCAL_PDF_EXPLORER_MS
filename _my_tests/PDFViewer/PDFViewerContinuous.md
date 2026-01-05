Here is a separate, continuous‑scroll multi‑page viewer.

- All pages are stacked vertically in one long scroll area (like a web page).
- Scroll wheel scrolls naturally through the whole document.
- Right dock: bookmark/outline tree; click any bookmark to jump to that page.
- Top toolbar: Open, Zoom +/–, Reset (1:1), Fit width.

Save this as e.g. `PDFContinuousViewer.py` and run:

```bash
python PDFContinuousViewer.py
```

You need:

```bash
pip install PyQt6 pymupdf
```

---

```python
#!/usr/bin/env python3
"""
Continuous multi-page PDF viewer (PyQt6 + PyMuPDF)

Features
--------
- Continuous vertical scrolling through all pages.
- Bookmark/outline dock on the right; clicking a bookmark scrolls to that page.
- Top toolbar:
    * Open PDF
    * Zoom in / Zoom out
    * Reset zoom (1:1)
    * Fit width

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
    QTreeWidget,
    QTreeWidgetItem,
    QDockWidget,
    QToolBar,
    QMessageBox,
)


class ContinuousPDFViewer(QMainWindow):
    """
    Continuous multi-page PDF viewer using PyMuPDF.

    Public methods
    --------------
    - load_pdf(path: str) -> bool
    - zoom_in(), zoom_out(), reset_zoom(), fit_width()
    - go_to_page(index: int)  # 0-based
    """

    errorOccurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._doc = None          # fitz.Document or None
        self._pdf_path: Optional[str] = None
        self._zoom: float = 1.0   # scale factor passed to MuPDF
        self._zoom_step: float = 1.25

        self.page_labels: List[QLabel] = []

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

        # Bookmark dock
        self.bookmark_tree = QTreeWidget()
        self.bookmark_tree.setHeaderHidden(True)
        self.bookmark_tree.itemActivated.connect(self._on_bookmark_activated)
        self.bookmark_tree.itemClicked.connect(self._on_bookmark_activated)

        self.bookmark_dock = QDockWidget("Bookmarks", self)
        self.bookmark_dock.setWidget(self.bookmark_tree)
        self.bookmark_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.bookmark_dock)

        # Toolbar
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

        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_zoom_reset)
        view_menu.addAction(self.act_fit_width)

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

        # Clear old page widgets
        self._clear_pages()

        # Create a QLabel for each page
        self.page_labels = []
        for _ in range(self.page_count):
            lbl = QLabel("Loading…")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("background-color: white;")
            self.pages_layout.addWidget(lbl)
            self.page_labels.append(lbl)

        self.pages_layout.addStretch(1)

        # Populate bookmarks
        self._load_bookmarks()

        # Render all pages at current zoom
        self._render_all_pages()

        return True

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

    # ---------------- Rendering ----------------

    def _render_all_pages(self):
        """Render all pages at the current zoom factor."""
        if self._doc is None:
            return

        try:
            import fitz
        except ImportError:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for i, label in enumerate(self.page_labels):
                try:
                    page = self._doc.load_page(i)
                    mat = fitz.Matrix(self._zoom, self._zoom)
                    pix = page.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")
                    qpix = QPixmap()
                    if qpix.loadFromData(img_bytes, "PNG"):
                        label.setPixmap(qpix)
                        label.setMinimumSize(qpix.size())
                        label.setText("")
                    else:
                        label.setText("Render error")
                except Exception as e:
                    label.setText(f"Error: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    # ---------------- Zoom operations ----------------

    def zoom_in(self):
        if self._doc is None:
            return
        self._zoom *= self._zoom_step
        self._render_all_pages()

    def zoom_out(self):
        if self._doc is None:
            return
        self._zoom /= self._zoom_step
        if self._zoom < 0.25:
            self._zoom = 0.25
        self._render_all_pages()

    def reset_zoom(self):
        if self._doc is None:
            return
        self._zoom = 1.0
        self._render_all_pages()

    def fit_width(self):
        """Zoom so that the first page fits the viewport width."""
        if self._doc is None or not self.page_labels:
            return

        first_label = self.page_labels[0]
        if first_label.pixmap() is None:
            # render at 1.0 to get size
            self._zoom = 1.0
            self._render_all_pages()

        pix = first_label.pixmap()
        if pix is None or pix.width() == 0:
            return

        view_w = self.scroll_area.viewport().width()
        if view_w <= 0:
            return

        factor = view_w / pix.width()
        self._zoom *= factor
        self._render_all_pages()

    # ---------------- Navigation ----------------

    def go_to_page(self, index: int):
        """Scroll to the given 0‑based page index."""
        if not (0 <= index < len(self.page_labels)):
            return
        label = self.page_labels[index]
        y = label.y()
        vbar = self.scroll_area.verticalScrollBar()
        vbar.setValue(max(0, y - 10))

    # ---------------- Bookmarks ----------------

    def _load_bookmarks(self):
        self.bookmark_tree.clear()

        if self._doc is None:
            return

        try:
            toc = self._doc.get_toc()  # [[level, title, page, ...], ...]
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
# Entry point
# ============================================================================


def main():
    app = QApplication(sys.argv)
    win = ContinuousPDFViewer()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

Notes and extensions you can add later:

- For very large PDFs, rendering all pages at once can be slow and memory‑intensive. Then you would implement “lazy rendering”: only render pages near the visible area when you scroll.
- If you want the same side toolbar (page number, zoom buttons, Adobe‑style menu) as in the other viewer, that can be added as a `QDockWidget` on the left and wired to `go_to_page`, `zoom_in/out`, `fit_width`, etc.