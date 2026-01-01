# Data Flow Engineering Documentation

**System**: Local PDF Explorer / File Organizer
**Scope**: Data Lifecycle & Transformations

---

## 1. Overview
The application handles data flow through a linear pipeline for initialization (Scan -> Enrich -> Display) and a cyclic loop for updates (Edit -> Persist -> Update View). The primary data structure is a **Pandas DataFrame**, chosen for its efficiency in handling tabular data and batch operations.

---

## 2. Data Stages

### 2.1 Stage 1: Ingestion (Scanning)
**Source**: Local File System
**Component**: `FileOrganizer.scan_directory`
**Logic**:
-   Iterates utilizing `pathlib` generators (`rglob`) for memory efficiency.
-   **Transformation**: Converts `Path` objects into a list of dictionaries.
-   **Output**: "Raw" DataFrame.
    ```python
    {
        'original_path': str,   # Primary Identifier
        'filename': str,
        'extension': str,
        'category': str         # Derived from extension rules
    }
    ```

### 2.2 Stage 2: Enrichment (Metadata Join)
**Source**: SQLite Database (`pdf_metadata` table)
**Component**: `CoreApp.scan` (post-processing)
**Logic**:
-   Iterates the Raw DataFrame.
-   Performs a **Lookup** for each `original_path` in the database.
-   **Transformation**: Appends `tags` and `notes` columns. Default is empty string `""` if no DB record found.
-   **Output**: "Master" DataFrame. This is the **Single Point of Truth (SPOT)** for the active session.

### 2.3 Stage 3: Presentation (UI Binding)
**Source**: Master DataFrame
**Component**: `PDFTableModel`
**Logic**:
-   Wraps the Master DataFrame.
-   Does **not** copy data; holds a reference.
-   **Transformation**: Formats specific columns for display (e.g., stripping extensions from filenames).
-   **Filtering**: `PDFSortFilterProxyModel` applies Regex logic dynamically on top of this model without mutating the underlying data.

---

## 3. Data Mutation (Updates)

### 3.1 Metadata Editing
When a user modifies tags/notes:
1.  **View Layer**: Collects new strings.
2.  **Controller**: Calls `CoreApp.update_file_metadata(path, tags, notes)`.
3.  **Persistence**: `PDFManager` executes `INSERT OR REPLACE` into `pdf_metadata`.
    *   *Guarantee*: SQLite Ensure consistency via ACID transaction.
4.  **InMemory Sync**: `DataProcessor.update_metadata` locates the row in Master DataFrame (`df.loc[mask]`) and updates it in-place.
    *   *Rationale*: Avoids a costly re-scan of the file system just to update strings.

### 3.2 File Operations (Rename/Move)
When a user renames a file:
1.  **Execution**: `os.rename(old, new)`.
2.  **Consistency Check**: If OS operation fails, flow aborts with error message.
3.  **InMemory Sync**:
    *   Update `original_path`, `filename`, `filename_no_ext` in Master DataFrame.
    *   Update `relative_path` (re-calculated).
4.  **Persistence Update**: (Future Implementation)
    *   *Gap*: Currently, the DB is indexed by path. Renaming breaks the link to old metadata if not explicitly handled (i.e., we must also update the primary key in SQLite or lose tags). associated with that file.

---

## 4. Concurrency & Integrity

| Hazard | Handling | Risk Level |
| :--- | :--- | :--- |
| **Race Condition** | File moved by external app during scan. | **Medium**. Application will show "missing" file until re-scan. |
| **Data Loss** | Application crash during metadata save. | **Low**. SQLite transactions minimize corruption risk. |
| **Stale Data** | User renames file externally. | **High**. Metadata linked to old path becomes orphaned. |

### Recommendation
Implement a **File System Watcher** (`QFileSystemWatcher` or `watchdog`) to detect external changes and trigger auto-resync or prompt the user.
