Here’s an updated version of `pdf_toc_checker_gui.py` with all requested features:

- Remembers previously used PDF paths via a combo box (and across runs using `QSettings`).
- “Check” button turns **green** if bookmarks exist, **red** if not.
- New **“Generate BM”** button:
  - Automatically generates bookmarks (using a simple font-size heuristic with PyMuPDF).
  - Saves output as `<original_name>_with_bookmarks.pdf` in the same folder.
  - Shows a popup asking whether to open the new PDF or open its folder.

```python
#!/usr/bin/env python3
"""
PyQt6 GUI to:
- Check if a PDF has bookmarks / internal links.
- Automatically generate bookmarks (heuristic) and save a new PDF.

Features:
- Remembers recently used PDF paths in a combo box (persists across runs).
- "Check" button turns green if bookmarks exist, red if not.
- "Generate BM" button creates a new PDF with bookmarks:
    <original_name>_with_bookmarks.pdf
  and offers to open the PDF or its folder.

Requirements:
    pip install PyQt6 pypdf pymupdf
    # or PyPDF2 instead of pypdf if you prefer:
    pip install PyQt6 PyPDF2 pymupdf
"""

import os
import sys
from typing import Tuple

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
    QComboBox,
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl, QSettings

# ---------------------
# PDF analysis (read)
# ---------------------

def get_pdf_reader_class():
    """Try to import PdfReader from pypdf or PyPDF2."""
    try:
        from pypdf import PdfReader  # type: ignore
        return PdfReader, "pypdf"
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
            return PdfReader, "PyPDF2"
        except ImportError:
            return None, None


def count_outline_items(outline_obj) -> int:
    """Recursively count entries in the outline/bookmarks structure."""
    if not outline_obj:
        return 0

    count = 0

    def _walk(item):
        nonlocal count
        if isinstance(item, list):
            for sub in item:
                _walk(sub)
        else:
            count += 1

    _walk(outline_obj)
    return count


def get_outline_count(reader) -> int:
    """Return total count of outline entries (bookmarks)."""
    outline = None

    # Newer pypdf / PyPDF2 properties
    for attr_name in ("outline", "outlines"):
        o = getattr(reader, attr_name, None)
        if o is not None:
            outline = o
            break

    # Older PyPDF2 method (if present)
    if outline is None:
        get_outlines = getattr(reader, "getOutlines", None)
        if callable(get_outlines):
            try:
                outline = get_outlines()
            except Exception:
                outline = None

    return count_outline_items(outline)


def find_internal_links(reader):
    """
    Find internal navigation links (GoTo / Dest) in annotations.

    Returns:
        links: list of (page_number, link_type)
        links_per_page: dict {page_number: count}
    """
    links = []
    links_per_page = {}

    for page_index, page in enumerate(reader.pages):
        annots = page.get("/Annots", [])
        if not annots:
            continue

        for annot in annots:
            try:
                if hasattr(annot, "get_object"):
                    obj = annot.get_object()
                else:
                    obj = annot.getObject()
            except Exception:
                continue

            if obj.get("/Subtype") != "/Link":
                continue

            dest = obj.get("/Dest")
            action = obj.get("/A")

            link_type = None
            if dest is not None:
                link_type = "Dest"
            elif action is not None and action.get("/S") == "/GoTo":
                link_type = "GoTo"

            if link_type:
                page_num = page_index + 1  # 1-based
                links.append((page_num, link_type))
                links_per_page[page_num] = links_per_page.get(page_num, 0) + 1

    return links, links_per_page


def analyze_pdf(pdf_path: str) -> Tuple[str, int, int]:
    """
    Analyze a PDF and return (report_text, outline_count, total_internal_links).
    """
    PdfReader, lib_name = get_pdf_reader_class()
    if PdfReader is None:
        raise RuntimeError(
            "No PDF library found.\n"
            "Please install one of:\n"
            "    pip install pypdf\n"
            "or:\n"
            "    pip install PyPDF2"
        )

    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        raise RuntimeError(f"Error opening PDF:\n{e}") from e

    if getattr(reader, "is_encrypted", False):
        # Try blank password
        try:
            reader.decrypt("")
        except Exception:
            raise RuntimeError(
                "The PDF is encrypted and could not be decrypted without a password."
            )

    # Outline / bookmarks
    try:
        outline_count = get_outline_count(reader)
    except Exception:
        outline_count = 0

    # Internal links
    try:
        links, links_per_page = find_internal_links(reader)
        total_links = len(links)
    except Exception:
        links, links_per_page = [], {}
        total_links = 0

    lines = []
    lines.append(f"PDF: {pdf_path}")
    lines.append("-" * 60)
    lines.append(f"Using library: {lib_name}")
    lines.append("")
    lines.append(f"Outline / bookmarks entries: {outline_count}")
    if outline_count > 0:
        lines.append("  -> This PDF has a document outline (sidebar ToC).")
    else:
        lines.append("  -> No document outline/bookmarks found.")
    lines.append("")
    lines.append(f"Internal navigation links (GoTo/Dest): {total_links}")
    if total_links > 0:
        lines.append("  -> Internal clickable links found on these pages:")
        for page_num in sorted(links_per_page):
            lines.append(f"     - Page {page_num}: {links_per_page[page_num]} link(s)")
    else:
        lines.append("  -> No internal navigation links found.")
    lines.append("-" * 60)
    if outline_count > 0 or total_links > 0:
        lines.append(
            "Conclusion: This PDF has some form of navigable structure "
            "(bookmarks and/or internal links)."
        )
    else:
        lines.append(
            "Conclusion: No navigable ToC/bookmarks or internal navigation links detected."
        )

    return "\n".join(lines), outline_count, total_links


# ---------------------
# Bookmark generation (write) using PyMuPDF
# ---------------------

FONT_THRESHOLD = 16.0  # heuristic: treat spans with size >= this as headings


def generate_bookmarks_for_pdf(pdf_path: str) -> Tuple[str, int]:
    """
    Generate bookmarks for pdf_path using a simple font-size heuristic.

    Returns:
        (output_pdf_path, number_of_bookmarks_created)

    Raises:
        RuntimeError on problems (missing library, no headings detected, etc.).
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise RuntimeError(
            "PyMuPDF (pymupdf) is required for bookmark generation.\n"
            "Install it with:\n"
            "    pip install pymupdf"
        ) from e

    if not os.path.isfile(pdf_path):
        raise RuntimeError(f"File not found:\n{pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise RuntimeError(f"Error opening PDF with PyMuPDF:\n{e}") from e

    toc = []  # list of [level, title, page_number]
    seen = set()

    for page_index, page in enumerate(doc):
        page_num = page_index + 1  # 1-based

        try:
            text_dict = page.get_text("dict")
        except Exception:
            continue

        blocks = text_dict.get("blocks", [])
        for block in blocks:
            lines = block.get("lines", [])
            for line in lines:
                for span in line.get("spans", []):
                    size = span.get("size", 0)
                    text = span.get("text", "").strip()
                    if not text:
                        continue

                    # Simple heuristic: large text, contains any letter.
                    if size >= FONT_THRESHOLD and any(c.isalpha() for c in text):
                        key = (page_num, text)
                        if key in seen:
                            continue
                        seen.add(key)
                        toc.append([1, text, page_num])
                # (optional: you could break after first heading per line/page)

    if not toc:
        doc.close()
        raise RuntimeError(
            "No headings detected with the current heuristic; no bookmarks created.\n"
            f"Try adjusting FONT_THRESHOLD (currently {FONT_THRESHOLD}) "
            "or using a different document."
        )

    base, ext = os.path.splitext(pdf_path)
    if not ext:
        ext = ".pdf"
    output_path = base + "_with_bookmarks" + ext

    try:
        doc.set_toc(toc)
        doc.save(output_path)
    except Exception as e:
        doc.close()
        raise RuntimeError(f"Error saving PDF with bookmarks:\n{e}") from e

    doc.close()
    return output_path, len(toc)


# ---------------------
# GUI
# ---------------------

class PdfTocChecker(QWidget):
    def __init__(self):
        super().__init__()

        self.pdf_path = None
        self.settings = QSettings("PdfTools", "PdfTocCheckerGUI")

        self.setWindowTitle("PDF ToC Checker")
        self.resize(800, 600)

        main_layout = QVBoxLayout(self)

        # Row 1: PDF selection (label + combo + browse button)
        file_layout = QHBoxLayout()
        file_label = QLabel("PDF file:")
        self.pdf_combo = QComboBox()
        self.pdf_combo.setEditable(False)
        self.pdf_combo.currentIndexChanged.connect(self.on_combo_changed)

        self.browse_button = QPushButton("Browse…")
        self.browse_button.clicked.connect(self.browse_pdf)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self.pdf_combo, 1)
        file_layout.addWidget(self.browse_button)

        # Row 2: Action buttons
        btn_layout = QHBoxLayout()
        self.check_button = QPushButton("Check")
        self.check_button.setEnabled(False)
        self.check_button.clicked.connect(self.run_check)

        self.generate_button = QPushButton("Generate BM")
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self.run_generate_bookmarks)

        btn_layout.addWidget(self.check_button)
        btn_layout.addWidget(self.generate_button)

        # Row 3: Results
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)

        main_layout.addLayout(file_layout)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.result_text)

        # Load recent files into combo box
        self.load_recent_files()

    # ----- Recent files handling -----

    def load_recent_files(self):
        paths = self.settings.value("recent_files", [], type=list)
        if not isinstance(paths, list):
            paths = []
        for p in paths:
            if isinstance(p, str) and os.path.isfile(p):
                self.pdf_combo.addItem(p)

        if self.pdf_combo.count() > 0:
            self.pdf_combo.setCurrentIndex(0)
            self.set_current_pdf(self.pdf_combo.currentText())

    def save_recent_files(self):
        paths = [self.pdf_combo.itemText(i) for i in range(self.pdf_combo.count())]
        self.settings.setValue("recent_files", paths)

    def add_recent_file(self, path: str):
        if not path:
            return
        existing = [self.pdf_combo.itemText(i) for i in range(self.pdf_combo.count())]
        if path in existing:
            idx = existing.index(path)
            self.pdf_combo.setCurrentIndex(idx)
        else:
            self.pdf_combo.insertItem(0, path)
            self.pdf_combo.setCurrentIndex(0)
        self.save_recent_files()

    # ----- File selection -----

    def browse_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF file",
            "",
            "PDF Files (*.pdf);;All Files (*)",
        )
        if file_path:
            self.add_recent_file(file_path)
            self.set_current_pdf(file_path)

    def on_combo_changed(self, index: int):
        if index < 0:
            self.set_current_pdf(None)
            return
        path = self.pdf_combo.itemText(index)
        self.set_current_pdf(path)

    def set_current_pdf(self, path: str | None):
        if path and os.path.isfile(path):
            self.pdf_path = path
            self.check_button.setEnabled(True)
            self.generate_button.setEnabled(True)
            self.check_button.setStyleSheet("")  # reset color
            self.result_text.clear()
        else:
            self.pdf_path = None
            self.check_button.setEnabled(False)
            self.generate_button.setEnabled(False)
            self.check_button.setStyleSheet("")
            if path and not os.path.isfile(path):
                QMessageBox.warning(
                    self,
                    "File not found",
                    f"The file does not exist:\n{path}",
                )

    # ----- Actions -----

    def run_check(self):
        if not self.pdf_path:
            QMessageBox.warning(self, "No file", "Please select a PDF file first.")
            return

        try:
            self.result_text.setPlainText("Analyzing PDF, please wait...")
            QApplication.processEvents()  # update UI
            report, outline_count, total_links = analyze_pdf(self.pdf_path)
            self.result_text.setPlainText(report)

            # Color the "Check" button: green if bookmarks exist, red otherwise.
            if outline_count > 0:
                self.check_button.setStyleSheet("background-color: green; color: white;")
            else:
                self.check_button.setStyleSheet("background-color: red; color: white;")

        except Exception as e:
            self.check_button.setStyleSheet("")
            QMessageBox.critical(self, "Error", str(e))

    def run_generate_bookmarks(self):
        if not self.pdf_path:
            QMessageBox.warning(self, "No file", "Please select a PDF file first.")
            return

        try:
            self.result_text.setPlainText("Generating bookmarks, please wait...")
            QApplication.processEvents()

            output_path, count = generate_bookmarks_for_pdf(self.pdf_path)
            self.result_text.append(
                f"\nGenerated {count} bookmarks.\nSaved as:\n{output_path}"
            )

            # Add output file to recent list as well
            self.add_recent_file(output_path)

            # Ask user what to do next
            msg = QMessageBox(self)
            msg.setWindowTitle("Bookmarks generated")
            msg.setText(
                f"Bookmarks generated: {count}\n\n"
                f"Output file:\n{output_path}\n\n"
                "What would you like to do?"
            )
            open_pdf_btn = msg.addButton("Open PDF", QMessageBox.ButtonRole.AcceptRole)
            open_folder_btn = msg.addButton(
                "Open Folder", QMessageBox.ButtonRole.ActionRole
            )
            close_btn = msg.addButton("Close", QMessageBox.ButtonRole.RejectRole)

            msg.exec()

            clicked = msg.clickedButton()
            if clicked == open_pdf_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))
            elif clicked == open_folder_btn:
                folder = os.path.dirname(output_path) or "."
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            else:
                # Close: do nothing extra
                pass

        except Exception as e:
            QMessageBox.critical(self, "Error generating bookmarks", str(e))

    # ----- Close event -----

    def closeEvent(self, event):
        self.save_recent_files()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    w = PdfTocChecker()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

Usage:

```bash
pip install PyQt6 pypdf pymupdf
# or:
pip install PyQt6 PyPDF2 pymupdf

python pdf_toc_checker_gui.py
```

- Use the combo box + “Browse…” to select PDFs (recent files are remembered).
- Click **Check**: button turns green/red depending on bookmark presence.
- Click **Generate BM**: creates `<name>_with_bookmarks.pdf` and offers to open the file or its folder.