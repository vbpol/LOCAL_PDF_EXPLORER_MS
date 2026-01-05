from __future__ import annotations

import os
import sys
from typing import Optional, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QWidget,
)


class PDFBookmarkModel(QWidget):
    """
    Non-UI model for managing PDF bookmarks (outline).

    Uses PyMuPDF (fitz).

    Main endpoints
    --------------
    - set_document(doc, pdf_path: str | None)
    - clear()

    - has_bookmarks() -> bool
    - get_toc() -> list[list[int, str, int]]

    - auto_generate_toc(font_threshold: float = 14.0,
                        max_levels: int = 3,
                        force_page_heading: bool = True) -> int
         -> generates a hierarchical TOC based on font size + color.

    - save_inplace() -> None
    - save_copy(suffix: str = "_with_bookmarks") -> str
         -> returns output path
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc = None           # type: ignore[assignment]
        self.pdf_path: Optional[str] = None
        self.toc: list[list] = []
        self.generated: bool = False
        self.modified: bool = False

    # ----- basic state -----

    def set_document(self, doc, pdf_path: Optional[str]):
        """Attach an existing PyMuPDF Document and load its TOC."""
        self.doc = doc
        self.pdf_path = pdf_path
        try:
            self.toc = doc.get_toc()
        except Exception:
            self.toc = []
        self.generated = False
        self.modified = False

    def clear(self):
        self.doc = None
        self.pdf_path = None
        self.toc = []
        self.generated = False
        self.modified = False

    def has_bookmarks(self) -> bool:
        return bool(self.toc)

    def get_toc(self):
        return list(self.toc)

    # ------------------------------------------------------------------
    # Enhanced automatic TOC generation: size + color + per-page fallback
    # ------------------------------------------------------------------

    def auto_generate_toc(
        self,
        font_threshold: float = 14.0,
        max_levels: int = 3,
        force_page_heading: bool = True,
    ) -> int:
        """
        Generate a hierarchical TOC from text based on font sizes and color.

        Heuristics:
        -----------
        1) Find the median font size across all text = "body" size.
        2) Determine distinct heading sizes (rounded to 0.5pt) above both
           body_size and font_threshold. Largest N -> levels 1..N.
        3) For each page:
           - Track current_title/current_level across ALL blocks
             (so wrapped headings like "Integration with ... Products"
              become a single bookmark).
           - A line is considered a heading if:
             * Its font size maps to a heading size, OR
             * Its color differs from the dominant body text color AND
               its font size is close to or above body size.
           - Consecutive heading lines with the same level are concatenated
             into a single title.
        4) If a page had no headings at all and force_page_heading is True,
           the largest text line on that page is used as a fallback heading.

        Returns:
            Number of TOC entries generated.
        """
        if self.doc is None:
            raise RuntimeError("No document attached to PDFBookmarkModel.")

        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise RuntimeError(
                "PyMuPDF (pymupdf) is required for auto bookmark generation.\n"
                "Install it with: pip install pymupdf"
            ) from e

        # ---------------- Pass 1: collect font sizes ----------------
        all_sizes: list[float] = []

        for page in self.doc:
            try:
                text_dict = page.get_text("dict")
            except Exception:
                continue

            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        txt = span.get("text", "").strip()
                        if not txt or not any(c.isalpha() for c in txt):
                            continue
                        size = float(span.get("size", 0.0))
                        if size > 0:
                            all_sizes.append(size)

        if not all_sizes:
            self.toc = []
            self.generated = True
            self.modified = True
            return 0

        # Median body font size
        all_sizes_sorted = sorted(all_sizes)
        mid = len(all_sizes_sorted) // 2
        if len(all_sizes_sorted) % 2 == 0:
            body_size = 0.5 * (
                all_sizes_sorted[mid - 1] + all_sizes_sorted[mid]
            )
        else:
            body_size = all_sizes_sorted[mid]

        # Round sizes to nearest 0.5 to reduce noise
        def round05(x: float) -> float:
            return round(x * 2.0) / 2.0

        unique_sizes = sorted(set(round05(s) for s in all_sizes))

        # Heading candidates are sizes above both body_size and font_threshold
        threshold = max(body_size, font_threshold)
        heading_sizes = [s for s in unique_sizes if s > threshold]
        if not heading_sizes:
            # Fallback: take largest few sizes
            heading_sizes = unique_sizes[-max_levels:]

        # Use at most max_levels distinct heading sizes for levels 1..N
        heading_sizes = sorted(heading_sizes, reverse=True)[:max_levels]

        # Map rounded size -> level (larger size -> smaller level number).
        size_to_level: dict[float, int] = {}
        for idx, s in enumerate(heading_sizes):
            size_to_level[s] = idx + 1  # 1..max_levels

        # ---------------- Pass 1b: estimate body text color -----------
        #   Most frequent color among spans with near-body font size.
        body_color_counts: dict[str, int] = {}

        for page in self.doc:
            try:
                text_dict = page.get_text("dict")
            except Exception:
                continue

            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        txt = span.get("text", "").strip()
                        if not txt or not any(c.isalpha() for c in txt):
                            continue
                        size = float(span.get("size", 0.0))
                        if abs(size - body_size) <= 1.0:
                            col_key = repr(span.get("color", None))
                            body_color_counts[col_key] = (
                                body_color_counts.get(col_key, 0) + 1
                            )

        body_color_key = None
        if body_color_counts:
            body_color_key = max(body_color_counts, key=body_color_counts.get)

        # ---------------- Pass 2: detect headings & build TOC --------
        toc: list[list] = []
        seen = set()  # (page_num, level, title)

        for page_index, page in enumerate(self.doc):
            page_num = page_index + 1
            try:
                text_dict = page.get_text("dict")
            except Exception:
                continue

            # Per-page fallback candidate
            page_best_size = 0.0
            page_best_text: Optional[str] = None
            page_best_color: Optional[str] = None

            page_had_heading = False

            # current_title / current_level span the *whole page*,
            # not just a single block – this merges headings split
            # across blocks, e.g. "Integration with ... Products".
            current_title: Optional[str] = None
            current_level: Optional[int] = None

            def flush_current():
                nonlocal current_title, current_level
                if current_title and current_level is not None:
                    key = (page_num, current_level, current_title)
                    if key not in seen:
                        toc.append([current_level, current_title, page_num])
                        seen.add(key)
                current_title = None
                current_level = None

            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue

                    # Combine span texts
                    line_text_parts = []
                    sizes_this_line = []
                    color_counts_line: dict[str, int] = {}

                    for span in spans:
                        txt = span.get("text", "")
                        if not txt:
                            continue
                        line_text_parts.append(txt)
                        size = float(span.get("size", 0.0))
                        sizes_this_line.append(size)
                        col_key = repr(span.get("color", None))
                        color_counts_line[col_key] = (
                            color_counts_line.get(col_key, 0) + 1
                        )

                    line_text = " ".join(line_text_parts).strip()
                    if not line_text or not any(c.isalpha() for c in line_text):
                        # blank / non-text line: end of heading run
                        flush_current()
                        continue

                    max_size = max(sizes_this_line) if sizes_this_line else 0.0
                    s_rounded = round05(max_size)

                    # Dominant color of this line
                    if color_counts_line:
                        line_color_key = max(
                            color_counts_line, key=color_counts_line.get
                        )
                    else:
                        line_color_key = None

                    # Track best line on this page for fallback
                    if max_size > page_best_size:
                        page_best_size = max_size
                        page_best_text = line_text
                        page_best_color = line_color_key

                    # --- heading by size ---
                    heading_level = None
                    for hs in heading_sizes:
                        if s_rounded >= hs:
                            heading_level = size_to_level[hs]
                            break

                    # --- additional heading by color (highlight) ---
                    if heading_level is None:
                        is_color_heading = (
                            body_color_key is not None
                            and line_color_key is not None
                            and line_color_key != body_color_key
                        )
                        if is_color_heading and max_size >= body_size * 0.9:
                            # assign level close to its size or deepest level
                            if heading_sizes:
                                heading_level = len(heading_sizes)
                                for hs in heading_sizes:
                                    if max_size >= hs * 0.9:
                                        heading_level = size_to_level[hs]
                                        break
                            else:
                                heading_level = 1

                    if heading_level is None:
                        # Non-heading line: close any pending heading
                        flush_current()
                        continue

                    page_had_heading = True

                    # Merge consecutive lines with the same heading level
                    if current_title and current_level == heading_level:
                        current_title += " " + line_text
                    else:
                        flush_current()
                        current_title = line_text
                        current_level = heading_level

            # End of page: flush any current heading
            flush_current()

            # If no heading detected on this page, but we have a strong text
            # candidate, add it as a fallback heading (e.g. first big title).
            if (
                force_page_heading
                and not page_had_heading
                and page_best_text
                and page_best_size > 0
            ):
                s_rounded = round05(page_best_size)
                heading_level = None
                for hs in heading_sizes:
                    if s_rounded >= hs:
                        heading_level = size_to_level[hs]
                        break
                if heading_level is None:
                    heading_level = len(heading_sizes) if heading_sizes else 1

                key = (page_num, heading_level, page_best_text)
                if key not in seen:
                    toc.append([heading_level, page_best_text, page_num])
                    seen.add(key)

        self.toc = toc
        self.generated = True
        self.modified = True
        return len(toc)

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def _ensure_doc(self):
        if self.doc is None or self.pdf_path is None:
            raise RuntimeError("No document or path set in PDFBookmarkModel.")

    def save_inplace(self) -> None:
        """Write current TOC back into the same PDF file."""
        self._ensure_doc()
        self.doc.set_toc(self.toc)
        self.doc.save(self.pdf_path, incremental=False)
        self.modified = False
        self.generated = False

    def save_copy(self, suffix: str = "_with_bookmarks") -> str:
        """
        Save current TOC into a new PDF file:
            <original_name><suffix>.pdf

        Returns: output path.
        """
        self._ensure_doc()
        base, ext = os.path.splitext(self.pdf_path)
        if not ext:
            ext = ".pdf"
        out_path = base + suffix + ext

        self.doc.set_toc(self.toc)
        self.doc.save(out_path, incremental=False)
        self.modified = False
        return out_path