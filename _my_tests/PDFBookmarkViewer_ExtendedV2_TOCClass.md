Below is an **enhanced `PDFBookmarkModel`** that:

- Groups multi‑line headings into a single bookmark.
- Automatically infers **hierarchical levels** (1, 2, 3, …) from font sizes, so you get a nested structure closer to what you showed (Preface → section → subsection).
- Still exposes the same public endpoints as before, so it’s drop‑in compatible with the `PDFBookmarkViewerMain` script I gave you:
  - `has_bookmarks()`
  - `get_toc()`
  - `auto_generate_toc()`
  - `save_inplace()`
  - `save_copy()`

You only need to **replace your existing `PDFBookmarkModel` class** with the version below.  
No other changes are strictly required, because `PDFBookmarkDock._generate_bookmarks()` already calls `auto_generate_toc(font_threshold=16.0)` which this class still supports.

---

### Enhanced `PDFBookmarkModel`

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
                        max_levels: int = 3) -> int
         -> generates a hierarchical TOC based on font size patterns.

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
    # Enhanced automatic TOC generation
    # ------------------------------------------------------------------

    def auto_generate_toc(self,
                          font_threshold: float = 14.0,
                          max_levels: int = 3) -> int:
        """
        Generate a hierarchical TOC from text based on font sizes.

        Heuristics:
        -----------
        - Scan the whole document and collect all text spans (with letters).
        - Compute median font size = "body" size.
        - Heading sizes are rounded (0.5pt) sizes > max(body_size, font_threshold).
        - The largest N heading sizes (up to max_levels) become levels 1..N.
        - For each page/block:
            * Combine consecutive heading lines with the same level into
              one bookmark title (fixes multi-line headings).
        - Produce TOC entries of the form [level, title, page_number].

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

        rounded_sizes = [round05(s) for s in all_sizes]
        unique_sizes = sorted(set(rounded_sizes))

        # Heading candidates are sizes above both body_size and font_threshold
        threshold = max(body_size, font_threshold)
        heading_sizes = [s for s in unique_sizes if s > threshold]
        if not heading_sizes:
            # fallback: take largest few sizes
            heading_sizes = unique_sizes[-max_levels:]

        # Use at most max_levels distinct heading sizes for levels 1..N
        heading_sizes = sorted(heading_sizes, reverse=True)[:max_levels]

        # For convenience, map rounded size -> level
        # Larger font -> smaller level number (1 is top)
        size_to_level: dict[float, int] = {}
        for idx, s in enumerate(heading_sizes):
            size_to_level[s] = idx + 1  # 1..max_levels

        # ---------------- Pass 2: detect headings & build TOC --------
        toc: list[list] = []
        seen = set()  # (page_num, level, title)

        for page_index, page in enumerate(self.doc):
            page_num = page_index + 1
            try:
                text_dict = page.get_text("dict")
            except Exception:
                continue

            for block in text_dict.get("blocks", []):
                current_title: Optional[str] = None
                current_level: Optional[int] = None

                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue

                    # Combine all span texts for this line
                    line_text_parts = []
                    sizes_this_line = []

                    for span in spans:
                        txt = span.get("text", "")
                        if not txt:
                            continue
                        line_text_parts.append(txt)
                        sizes_this_line.append(float(span.get("size", 0.0)))

                    line_text = " ".join(line_text_parts).strip()
                    if not line_text or not any(c.isalpha() for c in line_text):
                        # flush any pending heading if we hit a blank / non-text
                        if current_title and current_level is not None:
                            key = (page_num, current_level, current_title)
                            if key not in seen:
                                toc.append([current_level, current_title, page_num])
                                seen.add(key)
                            current_title = None
                            current_level = None
                        continue

                    max_size = max(sizes_this_line) if sizes_this_line else 0.0
                    s_rounded = round05(max_size)

                    # Determine if this line is a heading line
                    # Find the largest heading size <= s_rounded
                    heading_level = None
                    for hs in heading_sizes:
                        if s_rounded >= hs:
                            heading_level = size_to_level[hs]
                            break

                    if heading_level is None:
                        # not a heading line -> flush any pending heading
                        if current_title and current_level is not None:
                            key = (page_num, current_level, current_title)
                            if key not in seen:
                                toc.append([current_level, current_title, page_num])
                                seen.add(key)
                            current_title = None
                            current_level = None
                        continue

                    # It's a heading line. If same level as current, append text;
                    # otherwise flush the previous heading and start a new one.
                    if current_title and current_level == heading_level:
                        current_title += " " + line_text
                    else:
                        if current_title and current_level is not None:
                            key = (page_num, current_level, current_title)
                            if key not in seen:
                                toc.append([current_level, current_title, page_num])
                                seen.add(key)
                        current_title = line_text
                        current_level = heading_level

                # End of block: flush pending heading
                if current_title and current_level is not None:
                    key = (page_num, current_level, current_title)
                    if key not in seen:
                        toc.append([current_level, current_title, page_num])
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
```

---

### How this improves the structure

Compared to the previous simple version:

1. **Hierarchical levels**  
   - It analyzes all text sizes in the document.
   - Estimates a **body font size** (median).
   - All rounded sizes above `max(body_size, font_threshold)` are treated as headings.
   - The **largest** heading size → level 1 (chapter),  
     next size → level 2 (section), etc., up to `max_levels`.

2. **Multi‑line headings**  
   - Consecutive heading lines of the **same level** in a block are concatenated into a single bookmark title.  
   - So a big heading wrapped onto two lines becomes one bookmark, not two.

3. **Less noise**  
   - Non‑heading lines (body text, tables, lists) are filtered out by:
     - font size threshold, and
     - requiring at least one alphabetic character in the line.

---

### Integration with your existing script

In your `PDFBookmarkViewer_Extended.py` (or equivalent):

1. **Find and remove the old `PDFBookmarkModel` class**.
2. Paste the class above in its place.
3. Do not change `PDFBookmarkDock` — it will still call:

   ```python
   count = self.model.auto_generate_toc(font_threshold=16.0)
   ```

   which now uses the improved logic.

You can tweak behavior by adjusting:

- `font_threshold` passed from `PDFBookmarkDock` (e.g. 14, 15, 16).
- `max_levels` default in `auto_generate_toc` (e.g. 3 or 4).

If you have a particular PDF whose structure still looks off (e.g., certain levels collapsed or too flat), send a description of its header fonts (or a few screenshots of different headings) and I can tune the heuristics further (e.g., also considering left‑indent / bold flags).