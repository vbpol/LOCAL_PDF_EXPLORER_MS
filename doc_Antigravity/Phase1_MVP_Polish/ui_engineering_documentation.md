# UI Engineering Documentation

**System**: Local PDF Explorer / File Organizer
**Module**: `src.apps.pdf_ms`
**Technology**: PyQt6

---

## 1. UI Layer Overview
The UI layer implements the **View** and **Controller** portions of the MVC architecture. It is designed to be:
-   **Responsive**: Uses Signal/Slot mechanism for asynchronous event handling.
-   **Decoupled**: Views like `MetadataView` do not know about the `MainController` or the `CoreApp`. They strictly emit signals.
-   **Data-Bound**: The `PDFTableView` is driven entirely by the `PDFTableModel` (read-only) and `QSortFilterProxyModel` (sorting/filtering).

---

## 2. Component Specifications

### 2.1 `MainController`
The central orchestrator.
-   **Lifecycle**: Instantiated by `Launcher`. Creates `MainWindow` and `CoreApp`.
-   **Responsibilities**:
    1.  **Bridge**: Connects View signals to Core methods.
    2.  **State Logic**: Maintains the application state (e.g., currently selected file path) implicitly via the selection model.
    3.  **Window Management**: Handles `show()`, `close()`, and `SettingsDialog` execution.

### 2.2 `MainWindow`
The structural container.
-   **Layout**: `QSplitter` (Horizontal).
    -   **Left**: `PDFTableView` (File List).
    -   **Right**: `MetadataView` (Context Panel) inside a wrapper widget for toggling visibility.
-   **Toolbar**: Contains standard actions (Open, Settings) and the Search Bar.

### 2.3 `PDFTableView`
A highly customized `QTableView`.
-   **Features**:
    -   **Context Menu**: Custom menu for "Rename", "Open Folder", "Edit Metadata".
    -   **Columns**: hardcoded configuration in `configure_columns()` (Filename, Type, Tags, Category, Path, Actions).
    -   **Delegates**: Uses `ActionDelegate` for the "Actions" column (buttons inside cells).
-   **Signals**:
    -   `file_rename_requested(index, new_name)`: Emitted when user commits a rename in the dialog.
    -   `file_open_requested(index)`: Emitted on double-click or context menu action.

### 2.4 `MetadataView`
A "Passive View" form.
-   **Inputs**: `QLineEdit` (Tags), `QTextEdit` (Notes).
-   **Operation**:
    -   `set_data(path, tags, notes)`: Populates the form.
    -   `on_save()`: Emits `save_requested` with current field values. It performs no validation or I/O itself.

---

## 3. Signal & Slot Architecture

This table defines the key event flows in the system.

| Trigger (View) | Signal | Slot (Controller) | Action |
| :--- | :--- | :--- | :--- |
| **Open Folder** | `act_open_folder.triggered` | `open_folder` | Opens directory picker, calls `CoreApp.scan`, updates Model. |
| **Search Input** | `search_input.textChanged` | `on_search` | Updates `proxy_model.setFilterRegularExpression`. |
| **Select Row** | `selectionModel.selectionChanged` | `on_selection_changed` | Fetches metadata for selected file, calls `metadata_view.set_data`. |
| **Save Metadata** | `save_requested` | `save_metadata` | Calls `CoreApp.update_metadata`, refreshes Model. |
| **Rename File** | `file_rename_requested` | `rename_file` | Calls `os.rename`, updates DataFrame, refreshes Model, restores selection. |

---

## 4. Model-View Implementation Details

### 4.1 Data Binding
The `PDFTableModel` wraps the pandas DataFrame.
-   **`rowCount()`**: Directly returns `len(df)`.
-   **`data()`**: Uses `df.iloc[row]` to fetch data.
-   **Performance**: Since data is in-memory (Pandas), lookups are O(1). Sort/Filter is handled by the Proxy Model, which maps indices.

### 4.2 Proxy Filtering
`PDFSortFilterProxyModel` extends `QSortFilterProxyModel`.
-   **Filtering Logic**: `filterAcceptsRow`.
-   **Current Limitation**: Only filters based on visible columns (Filename, Tags). Hidden data (Notes) is currently not searchable via the standard proxy implementation unless exposed in the Model.

---

## 5. Styling
The application uses **QStyleSheet** (CSS-like) for theming.
-   Located in `MainWindow` or individual widgets.
-   **Standardization**: To improve consistent look & feel, style sheets should be moved to a central `.qss` file or a static string constant in `src/resources`.
