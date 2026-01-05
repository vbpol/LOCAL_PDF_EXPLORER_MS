You’re seeing three separate issues:

1. Footer text like **“Page 8 of 16”, “Page 11 of 16”** is wrongly treated as headings.
2. A two‑line heading **“Integration with Other AVEVA Cloud Services and On‑Premises Products”** becomes two bookmarks instead of one.
3. On the “Document Purpose and Audience / About …” page, you want a hierarchy:

```text
AVEVA Unified Engineering on CONNECT with WorkSpaces
    Document Purpose and Audience
    About AVEVA Unified Engineering on CONNECT with WorkSpaces
```

Below is a revised `PDFBookmarkModel.auto_generate_toc()` that addresses all three, while keeping the same public API.

### What this version does

- **Ignores headers/footers**  
  Lines whose vertical center is in the top or bottom ~6% of the page are not considered for headings or fallbacks.  
  In addition, any line matching `^Page \d+ of \d+` is explicitly ignored.  
  This removes “Page 8 of 16”, “Page 11 of 16”, etc.

- **Merges headings across blocks**  
  `current_title` / `current_level` are maintained across the whole page, not per block.  
  That means if the heading is split into multiple layout blocks (like your “Integration with … Products”), all consecutive heading lines of the same level are concatenated into **one** bookmark.

- **Uses font size + color for headings**  
  Same as the previous enhancement: body font size & color are estimated; color‑highlighted headings like “Third‑party Software Licenses” and “AVEVA Cloud Solutions Security” are detected even if their size is similar to body text.

- **Per‑page demotion to get a parent + children on the first content page**  
  After building raw heading entries we do a small post‑processing step:

  For each page, we:
  - sort headings by vertical position (top→down),
  - treat the **first heading** as the “anchor”,
  - **demote later headings that have the same level as the anchor** by one level (if possible).

  So if “AVEVA Unified Engineering on CONNECT with WorkSpaces” and
  “Document Purpose and Audience” share the same style, the first stays level 1 and the others become level 2 → you get the hierarchy you expect.

---

### Drop‑in replacement for `PDFBookmarkModel`

Replace your existing `PDFBookmarkModel` class with this one (only this class; the rest of your script can stay as is):

```python
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
        3) Estimate dominant body text color (most common color near body size).
        4) For each page:
           - Track current_title/current_level across ALL blocks
             (so wrapped headings like "Integration with ... Products"
              become a single bookmark).
           - A line is considered a heading if:
             * Its font size maps to a heading size, OR
             * Its color differs from the dominant body text color AND
               its font size is close to or above body size.
           - Lines in the top/bottom ~6% of the page or matching
             "Page N of M" are ignored (header/footer).
           - Consecutive heading lines with the same level are concatenated.
        5) If a page had no headings at all and force_page_heading is True,
           the largest text line on that page (excluding header/footer) is
           used as a fallback heading.
        6) Per-page structural tweak: for each page, if multiple headings
           share the same level, we treat the first as the anchor and
           demote subsequent headings of the same level by one level
           (child of the first). This gives structures like:

               AVEVA Unified Engineering on CONNECT with WorkSpaces
                   Document Purpose and Audience
                   About AVEVA Unified Engineering on CONNECT with WorkSpaces

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

        import re

        # Regex to detect page footers like "Page 8 of 16"
        re_page_footer = re.compile(r"^Page\s+\d+\s+of\s+\d+\b", re.I)

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

        # ---------------- Pass 2: detect headings & build raw entries --
        # We'll store entries as dicts with page, level, title, y_mid
        entries: list[dict] = []

        for page_index, page in enumerate(self.doc):
            page_num = page_index + 1
            try:
                text_dict = page.get_text("dict")
            except Exception:
                continue

            page_height = float(page.rect.height or 1.0)
            header_margin = page_height * 0.06
            footer_margin = page_height * 0.06

            # Per-page fallback candidate
            page_best_size = 0.0
            page_best_text: Optional[str] = None
            page_best_color: Optional[str] = None
            page_best_y_mid: float = 0.0

            page_had_heading = False

            current_title: Optional[str] = None
            current_level: Optional[int] = None
            current_y_mid: Optional[float] = None

            def flush_current():
                nonlocal current_title, current_level, current_y_mid
                if current_title and current_level is not None:
                    entries.append(
                        {
                            "page": page_num,
                            "level": current_level,
                            "title": current_title,
                            "y": current_y_mid if current_y_mid is not None else 0.0,
                        }
                    )
                current_title = None
                current_level = None
                current_y_mid = None

            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue

                    bbox = line.get("bbox", None)
                    if bbox and len(bbox) == 4:
                        x0, y0, x1, y1 = bbox
                        line_y_mid = (y0 + y1) / 2.0
                    else:
                        line_y_mid = 0.0

                    # Ignore header/footer zones completely for heading logic
                    if (
                        line_y_mid < header_margin
                        or line_y_mid > page_height - footer_margin
                    ):
                        # Could still be body text; don't use for headings or fallback
                        continue

                    # Combine span texts and gather size/color
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
                        flush_current()
                        continue

                    # Skip explicit "Page N of M" footer text
                    if re_page_footer.match(line_text):
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

                    # Track best line on this page for fallback (still ignoring
                    # header/footer because we already filtered by y_mid)
                    if max_size > page_best_size:
                        page_best_size = max_size
                        page_best_text = line_text
                        page_best_color = line_color_key
                        page_best_y_mid = line_y_mid

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
                    # even across blocks (current_* spans the entire page).
                    if current_title and current_level == heading_level:
                        current_title += " " + line_text
                        # y_mid of heading stays the first line's y
                    else:
                        flush_current()
                        current_title = line_text
                        current_level = heading_level
                        current_y_mid = line_y_mid

            # End of page: flush any current heading
            flush_current()

            # Fallback per-page heading if none found
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

                entries.append(
                    {
                        "page": page_num,
                        "level": heading_level,
                        "title": page_best_text,
                        "y": page_best_y_mid,
                    }
                )

        # ---------------- Pass 3: per-page structural tweak ---------

        # Sort entries by page, then by vertical position (top->down)
        entries.sort(key=lambda e: (e["page"], e["y"]))

        # For each page, demote headings of the same level as the first
        # heading on that page, so you get:
        #   TopHeading (level L)
        #       Other headings with same size/level become level L+1
        from collections import defaultdict

        by_page: dict[int, list[int]] = defaultdict(list)
        for idx, e in enumerate(entries):
            by_page[e["page"]].append(idx)

        max_defined_level = max(size_to_level.values(), default=1)

        for page_num, idx_list in by_page.items():
            if len(idx_list) <= 1:
                continue
            # First heading on the page is the anchor
            anchor_idx = idx_list[0]
            anchor_level = entries[anchor_idx]["level"]

            for j in idx_list[1:]:
                if entries[j]["level"] == anchor_level:
                    entries[j]["level"] = min(anchor_level + 1, max_defined_level)

        # ---------------- Build final TOC (removing duplicates) -----

        toc: list[list] = []
        seen_final = set()

        for e in entries:
            key = (e["page"], e["level"], e["title"])
            if key in seen_final:
                continue
            seen_final.add(key)
            toc.append([e["level"], e["title"], e["page"]])

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
```

---

### What you should see after this change

- **“Page 8 of 16”, “Page 11 of 16”**: gone from bookmarks.
- **“Integration with Other AVEVA Cloud Services and On‑Premises Products”**: a single bookmark, not wrapped into two separate entries.
- On the “Document Purpose and Audience” page:

  ```text
  AVEVA Unified Engineering on CONNECT with WorkSpaces
      Document Purpose and Audience
      About AVEVA Unified Engineering on CONNECT with WorkSpaces
  ```

  (assuming the second/third headings share the same style as the first; if their font sizes are already mapped to a lower level, they will stay lower.)

If you still see a specific line mis‑classified after this, tell me:

- the exact text of the line,
- roughly where it is on the page (top/middle/bottom),

and I can refine the pattern (for example, adding another regex filter or adjusting the header/footer margin percentage).