# Strategic Roadmap & Engineering Recommendations

**Date:** 2026-01-01
**Status:** DRAFT
**Scope:** Architecture Evolution from MVP to Industrial Grade

---

## 1. Documentation Review Summary

The `doc_Antigravity` folder now contains a comprehensive suite of technical documents covering:
*   **Architecture**: High-level C4-style diagrams and MVC breakdown.
*   **Core Domain**: Deep dive into `FileOrganizer`, `PDFManager`, and Data Flow.
*   **UI**: Signal/Slot architecture and View hierarchy.
*   **Use Cases**: Functional requirements analysis.

**Assessment**: The current architecture is **solid**. The separation of `CoreApp` (Logic) from `MainWindow` (UI) via `MainController` allows for safe expansion. The file-based SQLite approach is appropriate for the current scale but has a clear upgrade path.

---

## 2. Evolution Roadmap

This roadmap proposes a staged evolution. Each stage builds upon the previous one without refactoring the core foundation, adhering to the **Open/Closed Principle**.

### Phase 1: Core MVP Polish (The "Stability" Update)
*Goal: Perfect the current feature set and fix technical debt.*

*   **1. Async Scanning (Critical Optimization)**
    *   **Logic**: Move `scan_directory` to a `QThread`.
    *   **Architecture**: No change to Core. Controller handles the thread management.
    *   **Benefit**: Prevents UI freeze on folders with >100 files.
*   **2. Full Search Capability**
    *   **Logic**: Extend `PDFSortFilterProxyModel` to filter by "Notes" (currently missing).
    *   **Architecture**: Minor update to `PDfTableModel.data()` to expose `UserRole` data.
*   **3. Robust Renaming**
    *   **Logic**: Ensure renaming a file updates the database Primary Key (path) or use a UUID-based schema.
    *   **Architecture**: Update `Storage.update_pdf_metadata` to handle key changes.

### Phase 2: Advanced Features (The "Power User" Update)
*Goal: Enhance productivity for single users.*

*   **1. File System Watcher**
    *   **Feature**: Auto-detect external file moves/deletes.
    *   **Implementation**: Integrate `watchdog` library.
    *   **Connection**: New Service `FileWatcherService` injected into `CoreApp`.
*   **2. Batch Metadata Editing**
    *   **Feature**: Select 50 files -> Apply tag "Invoice" to all.
    *   **Implementation**: Update `MainController` to handle list selection; Loop updates in `CoreApp`.
*   **3. Advanced Filtering**
    *   **Feature**: Filter by Date Range, File Size, or "Missing Tags".
    *   **Implementation**: Add specific filter widgets to UI; Update Proxy Model logic.
*   **4. PDF Content Navigation (ToC)**
    *   **Feature**: Extract and display PDF Table of Contents (Bookmarks) in the Metadata Panel.
    *   **Logic**: Use `pypdf` or `PyMuPDF` to traverse the outline tree.
    *   **Architecture**: New method `PDFManager.extract_toc(path)`. Display in a `QTreeWidget` in `MetadataView`.
    *   **Value**: Allows users to understand document structure without opening it.

### Phase 3: Pro Level (The "Automation" & "AI" Update)
*Goal: Automated intelligence and specific vertical workflows.*

*   **1. Plugin System / Event Bus**
    *   **Concept**: Allow "Processors" to subscribe to `FileFound` events.
    *   **Feature**: **OCR Processor** (extract text from images), **Invoice Processor** (regex extract total).
    *   **Architecture**: Add `PluginManager` to `CoreApp`.
*   **2. AI-Powered Content Review (GenAI)**
    *   **Feature**: "Summarize this PDF", "Explain Chapter 3", "Generate Tutorial".
    *   **Logic**: Unified `AIService` Interface with switchable backends.
    *   **Implementation Tiers**:
        *   **Local (Privacy-First)**: **Ollama** running Llama 3 / Mistral. No data leaves the machine.
        *   **Cloud (Free Tier)**: **Google Gemini API** (high limits), **Groq** (fast inference), or **Hugging Face** Inference API.
        *   **Enterprise (Scalable)**: **Azure OpenAI Service** (via Startup Subscription). Use for heavy workloads or when specific compliance/SLA is needed.
    *   **Architecture**:
        *   **Service**: `AIService` (interface) injected into Core.
        *   **UI**: New `AIAssistantView` (Chat interface) docked in MainWindow.
*   **3. Version Control (Light)**
    *   **Feature**: "Save as Revision".
    *   **Architecture**: New DB table `file_revisions`. Physical storage logic in `FileOrganizer` to handle `_v2`, `_v3`.
*   **3. Custom Views/Dashboards**
    *   **Feature**: Pie chart of "Files by Category".
    *   **Architecture**: New View Component `AnalyticsView` querying existing `Storage`.

### Phase 4: Industrial Grade (The "Enterprise" Update)
*Goal: Team collaboration, security, and scale.*

*   **1. Database Abstraction (DAL)**
    *   **Change**: Decouple `Storage` from SQLite.
    *   **Goal**: Support **PostgreSQL** or **SQL Server**.
    *   **Architecture**: Introduce `StorageInterface`. `SQLiteStorage` and `PostgresStorage` implement it.
*   **2. Headless Server Mode**
    *   **Change**: Run `CoreApp` as a FastAPI/Flask service.
    *   **Goal**: Centralized server indexing a NAS; Desktop App becomes a thin client.
*   **3. Audit & Security**
    *   **Feature**: "Who changed this tag?".
    *   **Architecture**: Add `UserContext` to `CoreApp` methods. Log all `manage.py` actions to secure audit log.

---

## 3. Architectural Impact Analysis

How to implement these extensions **without harming** the current structure:

| Extension | Architecture Strategy | Risk |
| :--- | :--- | :--- |
| **Async Scan** | Wrap existing synchronous `scan()` in a Worker. **Do not** make `scan()` itself async/await unless rewriting Core. | Low |
| **OCR / Plugins** | Use **Decorator Pattern** or **Observer Pattern** on `FileOrganizer`. When file is found, pass through chain of processors. | Low |
| **Remote DB** | The `Storage` class is already injected into `CoreApp`. Create a new class `RemoteStorage` matching the API. Switch via `config.json`. | Medium (Latency) |
| **Web UI** | `CoreApp` and `FileOrganizer` are UI-agnostic. They can be imported by a Flask route handler directly. | Low |

## 4. Immediate Recommended Next Steps

1.  **Refactor Rename Logic**: Move renaming logic out of `MainController` into `CoreApp`/`PDFManager` to centralize the "Rename + DB Update" atomic operation.
2.  **Fix Search**: The current search experience is incomplete. This provides high user value for low effort.
3.  **Unit Tests**: Add tests for `FileOrganizer` filtering logic before adding more features (`watchdog`, plugins) to ensure no regressions.
