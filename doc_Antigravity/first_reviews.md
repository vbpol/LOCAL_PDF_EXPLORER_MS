# Codebase Review Report

## 1. Project Overview
The project is a **PDF Management System** built with **Python**, **PyQt6**, and **Pandas**. It follows a **Model-View-Controller (MVC)** architecture.
- **Core Logic**: Handles file scanning, organization, and metadata management (`src/core`).
- **Data Persistence**: Uses **SQLite** (`src/core/storage.py`) for maintaining history and metadata.
- **UI**: Built with PyQt6, featuring a table view with sorting/filtering capabilities (`src/apps/pdf_ms`).

## 2. Architecture & Design
### Strengths
- **MVC Pattern**: The separation between `MainController`, `MainWindow`, and `PDFTableModel` is clear and well-maintained. This makes the code modular and easier to test.
- **Data Handling**: Using `pandas` for handling file lists and `sqlite3` for persistence is a solid choice for a local desktop application, offering good performance and flexibility.
- **Dependency Injection**: The `CoreApp` and `PDFManager` use dependency injection (passing `Storage` and `Settings`), which facilitates testing and decoupling.

### Weaknesses / Areas for Improvement
- **Search Logic Limitation**: Separation of concerns usually requires the ProxyModel to filter based on data it can see. Currently, the `PDFSortFilterProxyModel` attempts to filter by "Notes", but "Notes" are not exposed in the `data()` method of `PDFTableModel` (only Filename, Tags, etc. are). This means searching for notes will likely fail or require a hack.
- **State Management**: `MainController` holds `self.full_df` (the master DataFrame). Any change to metadata requires updating specific rows in this DataFrame and then refreshing the model. As the app grows, this might become error-prone.
- **Blocking Operations**: `scan_directory` in `FileOrganizer` is likely synchronous. For large directories (thousands of files), this will freeze the UI.

## 3. Code Quality & Formatting
- **Readability**: Variable names are descriptive (`file_path`, `folder_path`, `df`).
- **Type Hinting**: Used in some places (`pdf_manager.py`, `data_processor.py`), but could be more consistent across the codebase, especially in `MainController`.
- **Hardcoding**:
    - `CoreApp` defaults to `config/settings.json`.
    - `MainWindow` has fixed sizes (`resize(1000, 600)`) and column headers.
- **Error Handling**: `try-except` blocks are used in key areas (e.g., renaming files), showing good defensive programming practices.

## 4. Specific Recommendations

### A. Fix Search Functionality
**Issue**: The search bar promises to search "filenames, tags, notes...", but `PDFSortFilterProxyModel.filterAcceptsRow` cannot access "notes" efficiently because they aren't in the column model.
**Recommendation**:
1.  Modify `PDFTableModel.data()` to return the entire row object (or just the notes) for a custom `UserRole`.
2.  Update `PDFSortFilterProxyModel` to query this `UserRole` when filtering.

### B. Improve Performance (Async Scanning)
**Issue**: `_load_folder_data` calls `app_core.scan()`, which is synchronous.
**Recommendation**: Move the scanning logic to a structured thread (using `QThread` or `QRunnable`) to keep the UI responsive during large scans.

### C. Refactor `MainController`
**Issue**: `MainController` is becoming a "God Class". It handles UI events, business logic calls, renaming logic, and window management.
**Recommendation**:
-   Move "File Rename" logic wholly into `PDFManager` or `FileOrganizer`. The controller should just call `app_core.rename_file(...)`.
-   Delegate detailed specific view logic (like `open_containing_folder`) to a helper or the view itself if appropriate (though Controller handling it is okay for MVC).

### D. Testing
**Observation**: Existing tests (`test_history.py`, `test_startup.py`) cover persistence and startup.
**Recommendation**: Add unit tests for `FileOrganizer.scan_directory` (mocking filesystem) and `DataProcessor`.

## 5. Conclusion
The codebase is in good shape. It works as intended for a personal file management tool. The architecture is sound, but attention should be paid to the "Search" implementation and potential UI freezing on large datasets.
