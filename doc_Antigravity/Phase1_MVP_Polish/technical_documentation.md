# Engineering Documentation: Local PDF Organizer

**Version:** 1.0.0
**Date:** 2026-01-01
**Author:** Antigravity AI

---

## 1. System Overview

The **Local PDF Organizer** is a desktop application designed to manage, categorize, and annotate PDF files on a local Windows file system. It leverages the **MVC (Model-View-Controller)** pattern to separate concerns between the UI (PyQt6) and business logic (Python/Pandas).

### 1.1 Technical Stack
-   **Language**: Python 3.10+
-   **GUI Framework**: PyQt6
-   **Data Processing**: Pandas
-   **Persistence**: SQLite3
-   **Build System**: setuptools / batch scripts

---

## 2. Component Architecture

### 2.1 Core Application (`src.core`)
The core module encapsulates all business logic, independent of the UI.

*   **`CoreApp`**: Facade for the core subsystem. Initializes `FileOrganizer`, `PDFManager`, and `Storage`.
*   **`FileOrganizer`**: Handles filesystem operations.
    *   **Algorithm**: Recursive descent using `pathlib.Path.rglob`.
    *   **Conflict Resolution**: Appends `_{counter}` to filenames if a target exists during organization.
*   **`PDFManager`**: Domain service for handling PDF-specific data.
    *   **Responsibility**: CRUD operations for metadata (tags, notes).
*   **`Storage`**: Data Access Layer (DAL).
    *   **Implementation**: Raw SQL queries via `sqlite3` for minimal overhead.

### 2.2 Data Model (`src.apps.pdf_ms.models`)
The application uses a hybrid data model:
1.  **Transient State**: `pandas.DataFrame` is used as the primary in-memory data structure for the current file list. This allows for fast sorting, filtering, and batch updates.
2.  **Persistent State**: SQLite tables store long-term data.

#### In-Memory DataFrame Schema
| Column | Type | Description |
| :--- | :--- | :--- |
| `original_path` | `str` | Absolute path to the file. **(Primary Key equivalent)** |
| `filename` | `str` | Name of the file with extension. |
| `tags` | `str` | Comma-separated tags (enriched from DB). |
| `notes` | `str` | User notes (enriched from DB). |
| `relative_path` | `str` | Path relative to the scan root. |

### 2.3 User Interface (`src.apps.pdf_ms.views`)
*   **`MainWindow`**: Main application container.
*   **`PDFTableView`**: Custom `QTableView` with optimizations for large datasets.
*   **`MetadataView`**: QWidget form for property editing.

---

## 3. Database Schema

The application uses a local SQLite database located at `data/history.db`.

### 3.1 Table: `pdf_metadata`
Stores user-generated annotations for files.
```sql
CREATE TABLE pdf_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE,  -- Absolute path (Windows format)
    tags TEXT,
    notes TEXT,
    bookmarks TEXT,
    last_modified TEXT
);
```

### 3.2 Table: `root_history`
Tracks recently opened folders for the "History" dropdown.
```sql
CREATE TABLE root_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE,
    last_accessed TEXT
);
```

---

## 4. Key Workflows

### 4.1 File Scanning & Loading
1.  **Initiation**: `MainController.open_folder()` -> `CoreApp.scan(path)`.
2.  **Execution**: `FileOrganizer.scan_directory()` iterates filesystem and builds a DataFrame.
3.  **Enrichment**: `CoreApp` iterates the DataFrame and performs a lookup in `pdf_metadata` for each file to populate `tags` and `notes`.
4.  **Display**: The enriched DataFrame is passed to `PDFTableModel.set_data()`.

### 4.2 Metadata Update
1.  **User Input**: User edits fields in `MetadataView` and clicks "Save".
2.  **Handling**: `MainController` calls `CoreApp.update_file_metadata()`.
3.  **Persistence**: `PDFManager` -> `Storage` executes an `INSERT OR REPLACE` (Upsert) on `pdf_metadata`.
4.  **State Sync**: `MainController` updates the specific row in the in-memory master DataFrame to reflect changes immediately without re-scanning.

---

## 5. API Reference (Core)

#### `CoreApp.scan(directory_path, recursive=False) -> pd.DataFrame`
Scans the directory and returns a DataFrame containing file info and metadata.

#### `PDFManager.get_metadata(file_path) -> dict`
Returns a dictionary `{'tags': str, 'notes': str, 'bookmarks': str}`. Returns empty strings if no record exists.

#### `Storage.save_history(df: pd.DataFrame)`
Logs operations to the history table.

---

## 6. Deployment & Configuration

*   **Config File**: `config/settings.json` loads default behaviors (e.g., recursive scan default, ignore patterns).
*   **Entry Point**: `run.bat` activates the environment and calls `src/main.py` (implied).

---

## 7. Future Considerations
*   **Concurrency**: Moving `scan_directory` to a `QThread` to prevent UI blocking on >10k file directories.
*   **Search**: Extending `PDFSortFilterProxyModel` to support "Notes" filtering by implementing a custom `filterAcceptsRow` using the source DataFrame.
