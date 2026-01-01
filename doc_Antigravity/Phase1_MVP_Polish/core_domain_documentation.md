# Core Domain Engineering Documentation

**System**: Local PDF Explorer / File Organizer
**Module**: `src.core`
**Version**: 1.0.0

---

## 1. Module Overview
The `src.core` module acts as the **Data & Business Logic Layer** of the application. It is designed to be:
-   **UI Agnostic**: Can be run from a CLI or a GUI.
-   **Stateful**: Maintains the current "Plan" (files found) and application configuration.
-   **Data-Driven**: Heavily relies on `pandas.DataFrame` for batch processing of file data.

---

## 2. Core Components Specification

### 2.1 `CoreApp` (Facade)
The entry point for all high-level operations.
-   **State Management**: Holds `self.current_plan` (DataFrame). This acts as the session state.
-   **Dependency Injection**: Initializes `Storage`, `Settings`, and `FileOrganizer` upon instantiation, wiring them together.
-   **Observer Pattern**: Implements `add_observer(callback)` to allow external listeners (like UI Progress Bars) to hook into long-running operations (scans/moves).

### 2.2 `FileOrganizer` (The Engine)
Responsible for analyzing the file system and proposing changes.

#### Algorithm: `scan_directory`
1.  **Input**: Root directory path, Recursive flag.
2.  **Traversal**:
    *   If `Recursive=True`: Uses `pathlib.Path.rglob('*')`.
    *   If `Recursive=False`: Uses `pathlib.Path.iterdir()`.
3.  **Filtering**: Skips directories and files listed in `Settings.ignore_files`.
4.  **Categorization**:
    *   Checks file extension against `Settings.file_categories` map.
    *   Returns specific category (e.g., "Documents") or `Settings.default_category` ("Others").
5.  **Output**: Returns a 'Raw' DataFrame with columns: `original_path`, `filename`, `extension`, `category`, `target_dir`, `status` ('pending').

#### Algorithm: `organize` (Execution)
1.  **Input**: DataFrame (Plan).
2.  **Conflict Resolution strategy**: `_get_unique_filename`.
    *   Checks if `target_path` exists.
    *   If exists, appends `_N` (e.g., `file_1.pdf`) incrementing N until unique.
    *   *Critical*: This check happens *just before* the move operation to minimize race conditions.
3.  **Atomicity**: File moves are performed using `shutil.move`. Failures (PermissionError) are caught and logged to the `status` column without halting the entire batch.

### 2.3 `DataProcessor` (Transformation)
A pure functional service class for DataFrame manipulations.
-   **`process_scan_results`**: Enriches raw scan data.
    -   Adds `relative_path` for clean UI display.
    -   Derives `file_type` for sorting.
    -   Filters dataset (currently enforces `.pdf` extension filter if required by business logic).

### 2.4 `Storage` (Persistence)
Manages the SQLite database `history.db`.

#### Database Design Decisions
-   **Raw SQL**: Used over ORM (SQLAlchemy) for:
    -   **Performance**: Bulk inserts/updates are faster.
    -   **Simplicity**: No need for object mapping overhead for simple schema.
    -   **Dependency Weight**: Keeps `requirements.txt` light.
-   **Upsert Logic**: Metadata updates use `INSERT OR REPLACE` or `ON CONFLICT DO UPDATE` patterns to ensure idempotency.

---

## 3. Data Flow & Structures

### 3.1 The "Plan" DataFrame
The central data structure passed between Core and UI.

| Column | Data Type | Source | Purpose |
| :--- | :--- | :--- | :--- |
| `original_path` | `str` | `FileOrganizer` | Source of truth for file location. |
| `filename` | `str` | `FileOrganizer` | Display name. |
| `category` | `str` | `FileOrganizer` | Grouping key. |
| `tags` | `str` | `CoreApp` (via `PDFManager`) | Searchable metadata. |
| `notes` | `str` | `CoreApp` (via `PDFManager`) | User annotations. |
| `status` | `str` | `FileOrganizer` | Execution state (pending/success/error). |

---

## 4. Configuration (`config/settings.json`)
The behavior of the Core Domain is driven by an external JSON configuration.

```json
{
    "db_path": "data/history.db",
    "default_category": "Others",
    "ignore_files": [".DS_Store", "Thumbs.db"],
    "file_categories": {
        "Images": [".jpg", ".png"],
        "Documents": [".pdf", ".docx"]
    }
}
```

---

## 5. Error Handling Strategy

1.  **Scanning**:
    *   `PermissionError` on directory access: Currently skipped/suppressed by iteration or might raise depending on OS. *Recommendation: Add explicit try-catch inside the iterator loop.*
2.  **File Operations**:
    *   `organize()` wraps individual file moves in `try-except Exception`.
    *   Errors are written to the `status` column of the DataFrame.
    *   The function returns the modified DataFrame so the UI can highlight failed rows.

---

## 6. Performance Characteristics

-   **Scanning**: Linear O(N) relative to file count. Synchronous execution is a bottleneck for N > 10,000 files.
-   **Metadata Enrichment**: Executed row-by-row on the DataFrame after scan.
    *   *Optimization*: Uses SQLite index on `file_path` for O(1) lookups per file.
    *   *Total Complexity*: O(N) DB queries. *Potential Optimization: Batch SELECT WHERE IN (...).*
