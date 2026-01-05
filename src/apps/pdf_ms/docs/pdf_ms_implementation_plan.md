# PDF-MS Implementation Plan

## Phase 1: Core Extension (Data & Logic)
- [x] **Dependency Update**: Add `PyQt6` to `requirements.txt`.
- [x] **Database Schema Update**: Modify `src/core/storage.py` to include `pdf_metadata` table creation.
- [x] **PDF Manager Module**: Create `src/core/pdf_manager.py`.
    - Methods: `update_metadata(path, tags, notes)`, `get_metadata(path)`, `search_metadata(query)`.
- [x] **CoreApp Update**: Expose `PDFManager` in `src/core/app.py`.

## Phase 2: GUI Architecture Skeleton
- [x] **Structure Setup**: Create `src/apps/pdf_ms/` structure (moved from `src/interfaces/gui`).
    - `src/apps/pdf_ms/controllers/`
    - `src/apps/pdf_ms/views/`
    - `src/apps/pdf_ms/models/`
- [x] **Entry Point**: Create `run_pdf_ms.py` in root.

## Phase 3: GUI Components Implementation
- [x] **Main Window**: Setup QMainWindow with layout (Splitter: FileView | MetadataPanel).
- [x] **File View Widget**:
    - Implement `QTableView`.
    - Connect to `CoreApp.scan()` to populate data.
    - Custom model `PDFTableModel` (inheriting `QAbstractTableModel`) to display Pandas DataFrame.
- [x] **Metadata Panel**:
    - `QTextEdit` for Notes.
    - `QLineEdit` for Tags.
    - Save Button.
- [x] **Controller Integration**:
    - Connect selection change in File View to load data in Metadata Panel.
    - Connect Save action to `CoreApp.update_file_metadata`.

## Phase 4: Refinement & Validation
- [x] **Search Feature**: Implement filter logic in `PDFTableModel` or via `CoreApp` query (Implemented in Controller).
- [x] **Filter PDF**: Ensure only PDF files are listed in the app.
- [x] **Open File**: Implement `os.startfile` (Windows) on double-click.
- [x] **Testing**:
    - Logic verified via `tests/test_pdf_app_logic.py`.
    - Verify data persistence (via Controller logic and CoreApp integration).

## Phase 5: Advanced Features (Current)
- [x] **PDF Reader Integration**:
    - `ReaderWindow` with PyMuPDF rendering.
    - Navigation controls (Next/Prev, Go to Page).
- [x] **Table of Contents (ToC)**:
    - Extract ToC from PDF.
    - Store ToC in `bookmarks` column in DB.
    - Display ToC in Reader side panel.
- [x] **User Bookmarks (Favorites)**:
    - Add `is_bookmarked` column to `pdf_metadata` table.
    - Create `BookmarkService` for toggling favorites.
    - Add "Fav" (★) column to Grid View.
    - Allow toggling via click on grid cell.
    - **Batch Action**: Add context menu option to toggle bookmarks for multiple selected files.
- [x] **Settings & Versioning**:
    - Settings Dialog with persistent storage.
    - Dynamic App Title with Version/Date/AI-IDE info.
    - `Version_History.md` tracking.

## Phase 6: ToC Engine & Optimization
- [x] **PDF Engine Service**:
    - Create `src/core/services/pdf_engine.py`.
    - Implement `has_toc(file_path) -> bool` using `pymupdf`.
    - Implement `extract_toc(file_path) -> list` (refactored from `PDFRenderer`).
    - Ensure scalability for large file lists.
- [x] **Integration**:
    - Update `CoreApp.scan()` to verify ToC status using `PDFEngine`.
    - Update `PDFTableModel` "ToC" column to reflect actual status (✓/✗).
    - Update `MainController` to use `PDFEngine.extract_toc` for extraction.
- [x] **Testing**:
    - Create unit tests for `PDFEngine` (`tests/test_app_scan_toc.py`).
    - Verified on real files in `E:\AVEVA-TM docs\1D ENGINEERING`.

## Phase 7: Modular Reader Refactor (Reader V2)
- [x] **Architecture Refactor**:
    - Split `ReaderWindow` into self-contained components:
        - `src/apps/pdf_ms/views/reader/reader_window.py` (Main Container)
        - `src/apps/pdf_ms/views/reader/components/pdf_viewer_view.py` (Middle Panel)
        - `src/apps/pdf_ms/views/reader/components/pdf_toolbar.py` (Toolbar)
        - `src/apps/pdf_ms/views/reader/components/toc_panel.py` (Left Panel)
        - `src/apps/pdf_ms/views/reader/components/metadata_panel.py` (Right Panel Wrapper)
- [x] **PDF Viewer Enhancements**:
    - **Zoom/Scroll**: Implement Ctrl+Scroll for Zoom.
    - **View Modes**:
        - Fit to Page (Aspect Ratio preserved, fully visible).
        - Fit Width (Scroll vertically).
        - Fit Height.
        - Full Mode (Fullscreen).
- [x] **Toolbar Extension**:
    - Add buttons for new view modes.
    - Zoom In/Out controls.
- [x] **Validation**:
    - Verify all panels work independently and communicate correctly.
    - Verify Zoom/Fit logic.
    - Verify Full Screen mode works (Toggle + ESC key).
    - Verify Docking features (Movable panels).

## Validation Checklist
- [x] App launches without errors.
- [x] Scans directory and lists PDF files.
- [x] Can add a tag "Test" to a file.
- [x] Can add a note "Hello World" to a file.
- [x] Restart app -> "Test" and "Hello World" persist (verified via CoreApp logic).
- [x] Double click opens the PDF.
- [x] ToC extraction works and persists.
- [x] User Favorites (Star) persist across sessions.
- [x] Reader opens with new modular layout (Dockable Panels).
- [x] ToC navigation works.
- [x] Zoom In/Out works (Mouse Wheel & Buttons).
- [x] Fit Width/Page works.
- [x] Full Screen mode works (including ESC to exit).
- [x] Chapter Notes saving works.
- [x] Metadata saving from Reader works.
