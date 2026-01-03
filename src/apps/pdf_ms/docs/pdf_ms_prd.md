# Product Requirements Document: PDF Management System (PDF-MS)

## 1. Introduction
**PDF-MS** is a local Windows desktop application designed to help users organize, explore, and annotate their PDF document collections. Built upon the robust `CoreApp` architecture, it leverages PyQt6 for a responsive GUI and SQLite for persistent local storage of metadata.

## 2. Goals & Objectives
- **Organization**: efficient browsing of PDF files in managed directories.
- **Annotation**: Allow users to add context to files via Tags, Notes, and Bookmarks without modifying the original PDF files.
- **Persistence**: Save all user-generated metadata in a local SQLite database.
- **Privacy**: Fully local execution; no data leaves the machine.
- **Usability**: Intuitive "Explorer-like" interface with a dedicated metadata panel.

## 3. Target Audience
- Single user on Windows OS.
- Users with large collections of PDF documents (e.g., technical docs, research papers, invoices) who need better organization than standard File Explorer.

## 4. Key Features

### 4.1 File Explorer & Organization
- **Directory Scanning**: Select and scan folders for PDF files.
- **Grid/List View**: Display files with metadata columns (Filename, Tags, Date, Path).
- **Filtering**: Filter files by Tags or Search terms (filename/notes).

### 4.2 Metadata Management
- **Tags**: Add, remove, and manage custom tags (e.g., "Invoice", "Urgent", "Personal").
- **Notes**: Rich text or plain text notes associated with a specific file.
- **Table of Contents (Structure)**: View and navigate PDF internal structure (ToC). Store extraction status.
- **User Bookmarks (Favorites)**: "Star" or favorite files for quick access/visibility in the grid. Support for single click toggle and batch selection toggle.

### 4.3 Persistence
- **SQLite Database**: Stores mappings between File Paths (or Hashes) and Metadata.
- **Data Integrity**: Handles file moves/renames (re-association logic to be defined).

### 4.4 Viewer Integration
- **Open**: Double-click to open in system default PDF viewer.
- **Preview (Optional)**: Simple first-page preview in the UI if feasible.

## 5. Non-Functional Requirements
- **Performance**: Instant loading of metadata for thousands of files.
- **Compatibility**: Windows 10/11.
- **Tech Stack**: Python 3.x, PyQt6, SQLite, Pandas.

## 6. User Flows
1.  **Launch**: User opens app.
2.  **Select Folder**: User chooses a root folder to manage.
3.  **Scan**: App scans folder, matches existing metadata from DB.
4.  **Browse**: User sees list of PDFs.
5.  **Annotate**: User selects a file -> Details Panel opens -> User types notes/adds tags -> Auto-save.
6.  **Bookmark**: User clicks "Star" icon on a row -> File is marked as favorite.
7.  **Search**: User types "Invoice" -> List filters to show only matching files.

## 7. Data Model (SQLite)

### `pdf_metadata` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER PK | Unique ID |
| `file_path` | TEXT | Absolute path (primary key logical) |
| `file_hash` | TEXT | MD5/SHA256 for tracking renames (optional phase 2) |
| `tags` | TEXT | JSON string or comma-separated tags |
| `notes` | TEXT | User notes |
| `bookmarks` | TEXT | JSON string: ToC Data `[{"page": 1, "label": "Intro"}]` |
| `is_bookmarked` | INTEGER | 0 or 1. User Favorite status. |
| `last_modified` | TEXT | Timestamp of last metadata edit |

## 8. Interface Mockup Concept
```
+---------------------------------------------------------------+
|  [Select Folder] [Refresh] |  Search: [_____________]         |
+-------------------+-------------------------------------------+
|  Folders Tree     |  File Grid (Name, Tags, Path)             |
|  > Docs           |  [PDF] Report.pdf   [Work, Urgent]        |
|  > Invoices       |  [PDF] Manual.pdf   [Ref]                 |
|                   |                                           |
|                   |                                           |
+-------------------+-------------------------------------------+
|  Status Bar       |  Metadata Panel (Bottom or Right)         |
|                   |  File: Report.pdf                         |
|                   |  Tags: [x] Work  [x] Urgent  (+) Add      |
|                   |  Notes: __________________________________|
|                   |         | Must review by Monday.         ||
|                   |         |________________________________||
+-------------------+-------------------------------------------+
```
