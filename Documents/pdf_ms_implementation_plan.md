# PDF-MS Implementation Plan

## Phase 1: Core Extension (Data & Logic)
- [ ] **Dependency Update**: Add `PyQt6` to `requirements.txt`.
- [ ] **Database Schema Update**: Modify `src/core/storage.py` to include `pdf_metadata` table creation.
- [ ] **PDF Manager Module**: Create `src/core/pdf_manager.py`.
    - Methods: `update_metadata(path, tags, notes)`, `get_metadata(path)`, `search_metadata(query)`.
- [ ] **CoreApp Update**: Expose `PDFManager` in `src/core/app.py`.

## Phase 2: GUI Architecture Skeleton
- [ ] **Structure Setup**: Create `src/interfaces/gui/` structure.
    - `src/interfaces/gui/main_window.py`
    - `src/interfaces/gui/widgets/`
    - `src/interfaces/gui/utils/`
- [ ] **Entry Point**: Create `run_gui.py` in root.

## Phase 3: GUI Components Implementation
- [ ] **Main Window**: Setup QMainWindow with layout (Splitter: FileView | MetadataPanel).
- [ ] **File View Widget**:
    - Implement `QTableView` or `QTreeView`.
    - Connect to `CoreApp.scan()` to populate data.
    - Custom model `PDFTableModel` (inheriting `QAbstractTableModel`) to display Pandas DataFrame.
- [ ] **Metadata Panel**:
    - `QTextEdit` for Notes.
    - `QLineEdit` (or custom TagWidget) for Tags.
    - Save Button (or auto-save on focus lost).
- [ ] **Controller Integration**:
    - Connect selection change in File View to load data in Metadata Panel.
    - Connect Save action to `CoreApp.pdf_manager.update_metadata`.

## Phase 4: Refinement & Validation
- [ ] **Search Feature**: Implement filter logic in `PDFTableModel` or via `CoreApp` query.
- [ ] **Open File**: Implement `os.startfile` (Windows) on double-click.
- [ ] **Testing**:
    - Verify data persistence after restart.
    - specific test script `tests/test_pdf_core.py`.

## Validation Checklist
- [ ] App launches without errors.
- [ ] Scans directory and lists PDF files.
- [ ] Can add a tag "Test" to a file.
- [ ] Can add a note "Hello World" to a file.
- [ ] Restart app -> "Test" and "Hello World" persist.
- [ ] Double click opens the PDF.
