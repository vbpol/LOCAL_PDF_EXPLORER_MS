#!/usr/bin/env python3
"""
Simple PyQt6 GUI to check if a PDF has:
- Document outline / bookmarks (sidebar table of contents)
- Internal navigation links (GoTo/Dest)

Requirements:
    pip install PyQt6 pypdf
    # or, if pypdf is not available:
    pip install PyPDF2
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QTextEdit,
    QVBoxLayout, QFileDialog, QMessageBox
)


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

    # Older PyPDF2 method
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


def analyze_pdf(pdf_path: str) -> str:
    """Run the ToC / link analysis and return a human-readable report."""
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

    return "\n".join(lines)


class PdfTocChecker(QWidget):
    def __init__(self):
        super().__init__()

        self.pdf_path = None

        self.setWindowTitle("PDF ToC Checker")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        self.select_button = QPushButton("Select PDF…")
        self.select_button.clicked.connect(self.select_pdf)

        self.file_label = QLabel("No file selected.")
        self.file_label.setWordWrap(True)

        self.check_button = QPushButton("Run check")
        self.check_button.setEnabled(False)
        self.check_button.clicked.connect(self.run_check)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)

        layout.addWidget(self.select_button)
        layout.addWidget(self.file_label)
        layout.addWidget(self.check_button)
        layout.addWidget(self.result_text)

    def select_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF file",
            "",
            "PDF Files (*.pdf);;All Files (*)",
        )
        if file_path:
            self.pdf_path = file_path
            self.file_label.setText(f"Selected file:\n{file_path}")
            self.check_button.setEnabled(True)
            self.result_text.clear()

    def run_check(self):
        if not self.pdf_path:
            QMessageBox.warning(self, "No file", "Please select a PDF file first.")
            return

        try:
            self.result_text.setPlainText("Analyzing PDF, please wait...")
            QApplication.processEvents()  # update UI
            report = analyze_pdf(self.pdf_path)
            self.result_text.setPlainText(report)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


def main():
    app = QApplication(sys.argv)
    w = PdfTocChecker()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()