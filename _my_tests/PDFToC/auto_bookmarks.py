#!/usr/bin/env python3
"""
Automatically add bookmarks to a PDF based on large text (e.g., headings).

Heuristic:
- Any text with font size >= FONT_THRESHOLD is treated as a heading.
- Each such heading becomes a top-level bookmark in the outline.

Usage:
    pip install pymupdf
    python auto_bookmarks.py input.pdf output.pdf
"""

import sys
import fitz  # PyMuPDF

FONT_THRESHOLD = 16  # adjust depending on your document


def build_toc(doc):
    """
    Build a simple TOC: each large-text span (>= FONT_THRESHOLD) becomes
    a level-1 bookmark pointing to its page.
    """
    toc = []  # list of [level, title, page_number]

    for page_index, page in enumerate(doc):
        page_num = page_index + 1  # 1-based
        text_dict = page.get_text("dict")  # text + layout + font info

        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size", 0)
                    text = span.get("text", "").strip()

                    if not text:
                        continue

                    if size >= FONT_THRESHOLD:
                        # Create a level-1 bookmark for this heading
                        toc.append([1, text, page_num])
                        # If you only want the first heading per page, uncomment:
                        # break
                # if you used 'break' above, remember to break higher levels too if desired

    return toc


def main(input_pdf, output_pdf):
    doc = fitz.open(input_pdf)

    toc = build_toc(doc)

    if not toc:
        print("No headings detected with the current heuristic; no bookmarks created.")
    else:
        print(f"Creating {len(toc)} bookmarks in the outline…")

    # Replace existing TOC with our generated one
    doc.set_toc(toc)
    doc.save(output_pdf)
    doc.close()
    print(f"Saved: {output_pdf}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python auto_bookmarks.py input.pdf output.pdf")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])