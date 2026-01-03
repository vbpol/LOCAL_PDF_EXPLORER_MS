# Phase 2: Advanced Features - Spec & Plan (Revised)

## 1. Change Specification

### 1.1 Integrated PDF Reader (Pro Version)
*   **Goal**: A complete "Power User" environment.
*   **Layout**: 3-Pane Design.
    *   **Left (Navigation)**: ToC Tree with "Chapter Notes" editor at the bottom.
    *   **Center (View)**: PDF Page View (Image).
    *   **Right (Metadata)**: File Details, Tags, General Notes (CRUD).
*   **Features**:
    *   **ToC extraction**: Auto-loaded.
    *   **Chapter Notes**: Select node -> Edit text -> Auto-save to ToC JSON.
    *   **File Metadata**: Edit Tags/Notes -> Save Button -> Updates DB.

### 1.2 Main Grid Enhancements
*   **Actions Column**: Add a generic "Action Delegate" allowing multiple buttons.
    *   **Existing**: Open Folder (Yellow Folder icon).
    *   **New**: "ToC Status" Button (Book icon).
        *   **Red**: No ToC in DB. Click -> Generates ToC (background).
        *   **Green**: ToC exists. Click -> Opens Reader directly.

## 2. Detailed Implementation Plan

### 2.1 Core Services
1.  **Dependency**: `pymupdf` (Done).
2.  **Service**: `PDFRenderer` (Done).
3.  **Storage**: Ensure `update_metadata` can handle the `bookmarks` JSON blob.

### 2.2 UI Components
1.  **Refactor `ReaderWindow`**:
    *   Add **Right Dock/Panel** for File Metadata (`MetadataView` logic reused or simplified).
    *   Implement "Save Chapter Note" logic.
2.  **Refactor `ActionDelegate`** (Main Table):
    *   Support multiple buttons in one cell.
    *   Add Logic: `if bookmarks: paint_green else: paint_red`.

### 2.3 Controller Logic
1.  **MainController**:
    *   Handle "Action Click" -> If ToC missing, call `PDFRenderer.get_toc` -> Save to DB -> Refresh View.
2.  **ReaderController** (New? Or keep in Window):
    *   Handle "Save File Metadata".
    *   Handle "Save Chapter Note" -> Update local ToC tree -> Save full JSON to DB.

## 3. Validation
*   **Grid**: Verify buttons change color after generation.
*   **Reader**: Verify Notes added to Chapter 1 persist after closing/reopening.
