# Phase 2: Advanced Features - Walkthrough

## 1. Overview
Phase 2 transformed the application from a simple organizer into a **Power User Review Station**. We replaced the external PDF viewer with a fully integrated, "headless-first" Reader, added automated database persistence for study notes, and implemented real-time file watching.

## 2. New Features

### 2.1 Integrated "Pro" Reader
*   **Split-Pane View**: ToC Tree (Left), PDF Page (Center), Metadata Editor (Right).
*   **Deep Navigation**: Click any ToC item to jump to the page.
*   **Study Notes**: Add notes **specific to a chapter/section**. These are saved to the database.
*   **Metadata Editing**: Edit file tags and global notes directly while reading.

![Reader Screenshot](img/reader_mvp_screenshot.png)

### 2.2 Table Action Column
*   **ToC Status Button**:
    *   🔴 **Red**: No ToC. Click to auto-generate from PDF structure.
    *   🟢 **Green**: ToC Ready. Click to open the Pro Reader.
*   **Context Aware**: Tooltips guide the user on what the button does.

### 2.3 User Guidance (Tooltips)
*   Added comprehensive tooltips to all buttons, inputs, and search fields.

### 2.4 File Watcher Service
*   **Auto-Update**: Dropping a PDF into the folder immediately refreshes the UI.
*   **Tech**: Powered by `watchdog` library.

## 3. Technical Implementation
*   **Core**: `PDFRenderer` (using `pymupdf`) handles headless extraction and rendering.
*   **Persistence**: Bookmarks and Notes are stored as JSON in the `pdf_metadata` table.
*   **Architecture**: `ReaderWindow` injects `CoreApp` dependency for direct DB access (CRUD).

## 4. Verification Results
*   **Core**: `src/run_phase2.py` validated extraction/rendering (Headless).
*   **UI**: `tests/test_phase2_ui.py` passed (Reader Launch).
*   **Services**: `tests/test_watcher.py` passed (File Events).

## 5. Next Steps (Phase 3)
*   **AI Integration**: Auto-tagging based on content.
*   **Search**: Semantic search within PDF content.
