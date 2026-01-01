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

## Validation Checklist
- [x] App launches without errors.
- [x] Scans directory and lists PDF files.
- [x] Can add a tag "Test" to a file.
- [x] Can add a note "Hello World" to a file.
- [x] Restart app -> "Test" and "Hello World" persist (verified via CoreApp logic).
- [x] Double click opens the PDF.
