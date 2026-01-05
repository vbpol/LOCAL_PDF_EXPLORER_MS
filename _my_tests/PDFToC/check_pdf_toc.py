#!/usr/bin/env python3
"""
Check if a PDF has a navigable Table of Contents (ToC):

- Document outline / bookmarks.
- Internal page links (GoTo / Dest), typically used by clickable ToCs.

Usage:
    python check_pdf_toc.py your_file.pdf
"""

import argparse
import sys

# Try pypdf first, then PyPDF2 as fallback
try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader  # type: ignore
    except ImportError:
        print("Error: Install 'pypdf' (recommended) or 'PyPDF2':\n"
              "    pip install pypdf\n"
              "or:\n"
              "    pip install PyPDF2",
              file=sys.stderr)
        sys.exit(1)


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
            # Outline item or destination
            count += 1

    _walk(outline_obj)
    return count


def get_outline(reader) -> int:
    """Return total count of outline entries (bookmarks)."""
    outline = None

    # Different versions of pypdf / PyPDF2 expose outline differently
    for attr_name in ("outline", "outlines"):
        if hasattr(reader, attr_name):
            try:
                outline = getattr(reader, attr_name)
                break
            except Exception:
                pass

    if outline is None:
        # Older PyPDF2 API
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
        links: list of (page_index, link_type) where link_type is "Dest" or "GoTo".
    """
    links = []

    for page_index, page in enumerate(reader.pages):
        annots = page.get("/Annots", [])
        if not annots:
            continue

        for annot in annots:
            try:
                obj = annot.get_object()
            except Exception:
                continue

            if obj.get("/Subtype") != "/Link":
                continue

            dest = obj.get("/Dest")
            action = obj.get("/A")

            if dest is not None:
                links.append((page_index, "Dest"))
            elif action is not None and action.get("/S") == "/GoTo":
                links.append((page_index, "GoTo"))

    return links


def main():
    parser = argparse.ArgumentParser(
        description="Check if a PDF has a navigable Table of Contents (bookmarks / internal links)."
    )
    parser.add_argument("pdf", help="Path to the PDF file")
    args = parser.parse_args()

    # Load PDF
    try:
        reader = PdfReader(args.pdf)
    except Exception as e:
        print(f"Error opening PDF: {e}", file=sys.stderr)
        sys.exit(1)

    # Try to decrypt if encrypted (no password)
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")  # try blank password
        except Exception:
            print("The PDF is encrypted and could not be decrypted without a password.",
                  file=sys.stderr)
            sys.exit(1)

    # Check outline (bookmarks)
    outline_count = 0
    try:
        outline_count = get_outline(reader)
    except Exception:
        outline_count = 0

    # Check internal links
    links = []
    try:
        links = find_internal_links(reader)
    except Exception:
        links = []

    # Aggregate link counts per page
    links_per_page = {}
    for page_idx, link_type in links:
        links_per_page.setdefault(page_idx + 1, 0)  # 1-based page numbers
        links_per_page[page_idx + 1] += 1

    # Output results
    print(f"PDF: {args.pdf}")
    print("-" * 60)
    print(f"Outline / bookmarks entries: {outline_count}")
    if outline_count > 0:
        print("  -> This PDF has a document outline (sidebar ToC).")
    else:
        print("  -> No document outline/bookmarks found.")

    total_links = len(links)
    print(f"Internal navigation links (GoTo/Dest): {total_links}")
    if total_links > 0:
        print("  -> Internal clickable links found on these pages:")
        for page_num in sorted(links_per_page):
            print(f"     - Page {page_num}: {links_per_page[page_num]} link(s)")
    else:
        print("  -> No internal navigation links found.")

    print("-" * 60)
    if outline_count > 0 or total_links > 0:
        print("Conclusion: This PDF has some form of navigable structure "
              "(bookmarks and/or internal links).")
    else:
        print("Conclusion: No navigable ToC/bookmarks or internal navigation links detected.")


if __name__ == "__main__":
    main()