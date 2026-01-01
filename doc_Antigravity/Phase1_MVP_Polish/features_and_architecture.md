# Features and Architecture Mapping

This document outlines the key features of the local PDF Explorer / File Organizer application and maps them to the underlying architecture components.

## Architecture Overview

The application follows a **Model-View-Controller (MVC)** design pattern, implemented using **PyQt6** for the UI and **Pandas/SQLite** for data management.

-   **Model Layer**: Handles business logic and data persistence.
    -   `CoreApp`: The main entry point for business logic.
    -   `PDFManager`: Manages specific metadata logic.
    -   `FileOrganizer`: Handles file system scanning and categorization rules.
    -   `Storage`: Interfaces with the SQLite database.
    -   `PDFTableModel` & `PDFSortFilterProxyModel`: PyQt adapters for displaying data.
-   **View Layer**: Displays data and captures user input.
    -   `MainWindow`: The primary container.
    -   `MetadataView`: Form for editing file details.
    -   `PDFTableView`: Displays the list of files.
-   **Controller Layer**: Coordinates interaction.
    -   `MainController`: Binds Views to Models, handles user actions (clicks, saves), and orchestrates application flow.

## Feature Mapping

| Feature | Description | Architecture Component / Implementation |
| :--- | :--- | :--- |
| **Recursive File Scanning** | Scans a selected directory and subdirectories for files, primarily PDFs. | **Model**: `CoreApp` calls `FileOrganizer.scan_directory`.<br>**Implementation**: Uses `pathlib.rglob`, returns a Pandas DataFrame. |
| **PDF Metadata Management** | View and edit "Tags", "Notes", and "Bookmarks" for individual PDF files. | **View**: `MetadataView` displays fields.<br>**Controller**: `MainController` captures "Save" signal.<br>**Model**: `PDFManager` reads/writes to `Storage` (SQLite); `DataProcessor` updates the in-memory DataFrame. |
| **Categorization** | Automatically validates file types and assigns categories (e.g., "PDF File") based on extensions. | **Model**: `FileOrganizer` applies rules defined in `Settings`.<br>**Model**: `DataProcessor` enriches the raw scan data. |
| **Data Persistence** | Saves scan history, file metadata, and application usage (recently opened folders). | **Model**: `Storage` class encapsulates all SQLite `INSERT`/`SELECT` operations.<br>**Database**: `data/history.db`. |
| **Search & Filtering** | Real-time filtering of the file list by filename, tags, or path. | **Model**: `PDFSortFilterProxyModel` extends `QSortFilterProxyModel`.<br>**Logic**: RegExp matching against specific columns in the `PDFTableModel`. |
| **File Operations** | Open file in default viewer, open containing folder, rename file. | **Controller**: `MainController` contains the logic.<br>**Implementation**: Uses `os.startfile`, `os.rename`. **Note**: Renaming logic interacts with the Model to update the display after the file system change. |
| **Application History** | Dropdown list of previously accessed root directories for quick access. | **Model**: `Storage` maintains `root_history` table.<br>**Controller**: `MainController` loads this on startup and updates `MainWindow`'s combo box. |

## Data Flow Example: Editing Metadata

1.  **User Action**: User selects a file in `PDFTableView`.
2.  **Controller**: `MainController.on_selection_changed` is triggered.
3.  **Model Query**: Controller calls `app_core.pdf_manager.get_metadata(path)`.
4.  **View Update**: Controller passes data to `metadata_view.set_data(...)`.
5.  **User Edit**: User changes tags and clicks "Save".
6.  **Controller**: `MainController` receives `save_requested` signal.
7.  **Model Update**: Controller calls `app_core.update_file_metadata(...)` to save to DB and `DataProcessor` to update the in-memory DataFrame.
8.  **View Refresh**: Controller touches the `PDFTableModel` to reflect changes in the list.
