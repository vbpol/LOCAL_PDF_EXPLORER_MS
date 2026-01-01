
PyQt6 MVP Architect

Industrial-grade PDF & video organizer • grid exploration • tags • bookmarks • notes • configurable metadata
Jump to implementation plan

Contents

    1. Product overview
    2. Functional requirements
    3. High-level architecture
    4. Data model
    5. UI & UX layout
    6. PyQt6 class design
    7. Core interaction flows
    8. Step-by-step implementation plan
    9. Next steps & extensions

1. Product overview

Goal: design a PyQt6-based desktop MVP for industrial use to organize, explore, review, and manage PDFs and videos within a selected root folder (including subfolders). The app focuses on:

    Grid-based visual exploration of PDFs & videos (with thumbnails).
    File-focused side panel for bookmarks, tags, notes/comments.
    Configurable metadata display (settings-driven columns & fields).
    Non-destructive organization: metadata in an internal DB; file paths on disk remain intact.

This page gives you an implementation-ready architecture and PyQt6 class skeletons you can copy into your project.
2. Functional requirements
Core

    Select a root folder; recursively index PDFs and video files.
    Support subfolder structures for classification and categorization (preserve folder hierarchy).
    Grid view (thumbnails + key metadata) for all files inside the selected root (with filters).
    Detail panel for the selected file:
        Basic metadata (name, relative path, size, type, modified date).
        User-managed tags.
        Per-file notes/comments.
        Bookmarks (page number for PDFs, timestamp for videos).
    Open file in an internal viewer (PDF viewer or video player) for quick review.
    Settings dialog to control metadata display: which columns, sorting, thumbnail size, etc.

Non-functional

    Responsive for folders with a few thousand files (MVP; not petabyte-scale).
    Safe: metadata in SQLite; original files untouched.
    Extensible: clear separation between UI, domain logic, and persistence.

3. High-level architecture
Layers

    Presentation (PyQt6)
        Main window & dockable panels (folder tree, grid, details).
        PDF viewer & video player widgets.
        Settings dialog and filtering controls.
    Domain / Application services
        File indexing & re-indexing service (root folder aware).
        Tagging, bookmarking, notes management.
        Search & filtering over DB.
    Persistence & infrastructure
        SQLite DB for metadata, tags, notes, bookmarks, settings.
        File system scanning (os / pathlib / watchdog).
        Metadata extraction (PyPDF2 / fitz for PDFs, ffprobe for video).

Recommended stack

    Python 3.10+
    PyQt6
        QtWidgets: QMainWindow, QDockWidget, QListView/QTableView, QTreeView, QDialog.
        QtGui: QStandardItemModel or QAbstractTableModel, QIcon, QPixmap, QPainter.
        QtCore: QThreadPool, QRunnable, QObject, pyqtSignal, QSettings.
        QtMultimedia: QMediaPlayer, QAudioOutput.
        QtMultimediaWidgets: QVideoWidget (or equivalent for your Qt version).
        QtPdf: QPdfDocument, QPdfView (or a 3rd-party viewer if QtPdf isn't available).
    Libraries
        SQLite via sqlite3 or SQLAlchemy (lightweight ORM optional).
        watchdog for real-time file system change tracking (optional for MVP; can start with manual refresh).
        PyPDF2 or pymupdf for PDF metadata & thumbnails.
        ffmpeg/ffprobe called via subprocess for video metadata & thumbnails (or opencv).

4. Data model (SQLite)

Keep all user data in a local SQLite database. Files remain on disk.
Core tables

    files
        id (PK)
        root_id (FK to roots)
        relative_path (path from root)
        name, extension, mime_type
        size_bytes, modified_ts
        file_type (enum: pdf, video, other)
        page_count (PDF) / duration_seconds (video)
        hash (optional, for change detection)
    roots
        id, absolute_path, label, last_indexed_ts
    tags
        id, name (unique), color, description
    file_tags (many-to-many)
        file_id, tag_id
    notes
        id, file_id, body, created_ts, updated_ts
    bookmarks
        id, file_id
        page_number (PDF) or timestamp_seconds (video)
        label, created_ts

Settings & configuration

    settings (key/value)
        id, section, key, value, type
        Examples:
            (ui, grid.thumbnail_size, 160)
            (ui, grid.columns, ["name","file_type","size_bytes","tags"])
            (ui, theme, "dark")
            (indexing, auto_rescan, true)
    Alternatively, use QSettings for some per-user UI configs and DB for domain settings.

5. UI & UX layout (PyQt6)
Main window regions

Use QMainWindow with dock widgets:

    Top toolbar (main window toolbar)
        Root folder selector (button + label).
        Search bar (filter by name, tag, note text).
        Filter controls (file type, tag filter, date range).
        Settings button (opens settings dialog).
        Refresh/re-index button.
    Left dock: Folder tree
        QTreeView + custom QAbstractItemModel or QFileSystemModel limited to root.
        Clicking a folder filters the grid to that directory subtree.
    Center: File grid view
        QListView in IconMode or QTableView with a custom delegate.
        Each cell shows thumbnail, file name, tags icons, key metadata.
        Supports multi-select, sorting, and context menu.
    Right dock: Details panel for selected file
        Tabs: Details, Tags, Notes, Bookmarks.
        Preview thumbnail; button to open full viewer.
    Bottom dock (optional): Recent files or global bookmarks.

Grid view design

    Use QListView with a custom QStyledItemDelegate for a Pinterest-like grid.
    Model: FileItemModel (subclass of QAbstractTableModel or QAbstractListModel).
    Role-based data: standard roles (Qt.DisplayRole, Qt.DecorationRole) + custom roles for metadata, tags, etc.
    Thumbnail generation in background threads with caching (e.g., on disk in a .thumbnails folder under root).
    Settings-driven: thumbnail size, visible overlays (tags, duration, page count).

Settings dialog

Use QDialog with tabs:

    Grid
        Thumbnail size slider.
        Toggle visibility of metadata badges: file type, size, modification date, tags count.
        Column configuration if you provide a table view.
    Indexing
        Include/exclude patterns (e.g. *.tmp, backup folders).
        Automatic rescan interval or manual-only.
    Viewer
        Default zoom mode for PDF.
        Video playback defaults (volume, loop, playback speed).

6. PyQt6 class design (skeletons)

Below are skeletons you can adapt. They are structured for maintainability: UI, services, and persistence are clearly separated.

"""app.py - Application entry point"""

from PyQt6.QtWidgets import QApplication
from core.database import AppDatabase
from core.file_indexer import FileIndexer
from ui.main_window import MainWindow


def main():
    import sys

    app = QApplication(sys.argv)

    db = AppDatabase("app_data.db")
    indexer = FileIndexer(db)

    window = MainWindow(db=db, indexer=indexer)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

Keep the entry point thin; most logic lives in dedicated modules.

"""app.py - Application entry point"""

from PyQt6.QtWidgets import QApplication
from core.database import AppDatabase
from core.file_indexer import FileIndexer
from ui.main_window import MainWindow


def main():
    import sys

    app = QApplication(sys.argv)

    db = AppDatabase("app_data.db")
    indexer = FileIndexer(db)

    window = MainWindow(db=db, indexer=indexer)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

Keep the entry point thin; most logic lives in dedicated modules.

7. Core interaction flows
7.1. Root selection & indexing

    User clicks Select root... in the toolbar.
    QFileDialog returns path; FileIndexer.index_root_async is called.
    Worker thread scans recursively; for each PDF/video:
        Insert or update files row.
        Extract & update technical metadata.
    Progress signals update status bar or a small progress bar.
    On finished, MainWindow queries DB for root_id, constructs FileItemModel, and assigns it to grid view.

7.2. Exploration & selection

    User navigates folders via left tree.
    Tree selection change triggers model reload with folder_filter on relative_path.
    Grid view shows thumbnails; double-click opens viewer for PDF or video.
    Selecting a file row emits selectionChanged, used to:
        Update detail labels (name, path, size, etc.).
        Load tags, latest note, bookmarks from DB.
        Adjust actions (bookmark button enabled only for viewable types).

7.3. Tags & notes

    User types comma-separated tags in the Tags tab and clicks Save tags.
    Application splits, normalizes (trim, lowercase), creates missing tags in tags table.
    Updates file_tags mappings for selected file.
    Grid view reflects tags via small badges (if enabled in settings).
    Notes tab allows writing free-form text; saving inserts/updates row in notes.

7.4. Bookmarks

    When viewing a PDF, user jumps to a page and clicks Add bookmark.
    Viewer reports current page or playback time back to main app (signal).
    App inserts a row in bookmarks with page_number or timestamp_seconds.
    Bookmarks tab shows list; double-clicking opens the viewer at that exact position.

8. Step-by-step implementation plan

    Bootstrap project structure

    project_root/
    ├─ app.py
    ├─ core/
    │  ├─ __init__.py
    │  ├─ database.py
    │  ├─ file_indexer.py
    │  └─ settings_service.py (optional)
    └─ ui/
       ├─ __init__.py
       ├─ main_window.py
       ├─ models.py
       ├─ settings_dialog.py
       └─ viewers/
          ├─ pdf_viewer.py
          └─ video_viewer.py

    Implement AppDatabase and schema
        Finalize columns as per your needs; run some simple unit tests for CRUD.
        Add helper methods for common queries: get files by root, tags, etc.
    Implement FileIndexer
        Start without thumbnails and extended metadata.
        Later, add PDF page count & video duration extraction.
        Finally, implement thumbnail generation and cache.
    Build MainWindow layout
        Create toolbar, folder tree dock, grid view, and detail tabs.
        Wire Select root → indexer → reload model → view.
    Implement FileItemModel & basic selection logic
        On selection change, look up file in DB and populate detail fields.
        Hook tags/notes/bookmarks loading.
    Add tagging, notes, and bookmarks persistence
        Create utility methods in dedicated services (e.g., TagService, NotesService).
        Call them from MainWindow/Detail panel when user interacts.
    Implement settings dialog
        Store settings in DB, and/or use QSettings for pure UI preferences.
        On accept, update grid view configuration (thumbnail size, visible metadata).
    Add viewers
        PDF: Use QtPdf if available or an embedded browser widget / PyMuPDF-based viewer.
        Video: QMediaPlayer + QVideoWidget with basic transport controls.
        Expose the current page/time via signals for bookmark creation.
    Polish and harden
        Error handling for missing files (deleted on disk after indexing).
        Optional: background watcher (watchdog) to auto-refresh on file changes.
        Export/import of metadata (e.g., JSON) for backup.

9. Next steps & extensions

    Advanced search: full-text search on notes & file names; maybe integrate SQLite FTS5 for performance.
    Workspaces: save sets of filters/tags as named workspaces for recurring reviews.
    Batch operations: apply tags to multiple files, move/copy tagged sets to export locations.
    Collaboration: share metadata DB on network drive (careful with concurrent write access).
    Analytics: heatmap of most-accessed files, aging reports (e.g., which PDFs not opened for 1 year).

