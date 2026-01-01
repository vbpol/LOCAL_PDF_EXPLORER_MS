# Optimization & Industrial MVP Roadmap

**Date:** 2026-01-01
**Context:** Transforming the Local PDF Explorer into a robust, industrial-grade solution.

---

## 1. Optimization Recommendations

Current limitation: The application runs synchronously on the main UI thread, leading to potential "Application Not Responding" (ANR) states during heavy file operations.

### 1.1 Concurrency & threading
*   **Problem**: `CoreApp.scan()` and `FileOrganizer.organize()` are blocking.
*   **Solution**: Implement **Worker Thread Pattern** using `QThread` or `QRunnable` + `QThreadPool`.
    *   Create a `ScanWorker` signal that emits partial results or progress.
    *   Keep the UI responsive (allow "Cancel" button during scan).
*   **Impact**: Essential for UX when handling >1,000 files.

### 1.2 Database Tuning
*   **Problem**: Metadata enrichment performs a SELECT for every file row (N+1 Select Problem).
*   **Solution**:
    *   **Batch Loading**: Fetch all relevant tags for the scanned directory in one query: `SELECT * FROM pdf_metadata WHERE file_path IN (...)`.
    *   **Indexing**: Ensure `file_path` column in SQLite is strictly indexed (already done via UNIQUE constraint, but confirm execution plan).
    *   **WAL Mode**: Enable Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) for better concurrency if multiple threads access the DB.

### 1.3 UI Virtalization
*   **Problem**: Loading thousands of rows into `QTableView` can consume memory.
*   **Solution**:
    *   Ensure `PDFTableModel` only holds references to the DataFrame.
    *   Use `fetchMore` pattern (Pagination) if the dataset grows into the millions.

---

## 2. Industrial MVP Extensions

To make this application "Industrial Grade" (deployable to a team or enterprise environment), the following features are required.

### 2.1 Packaging & Distribution
*   **PyInstaller/Nuitka**: Create a standalone `.exe` or `.app` to remove dependency on Python installation.
*   **Signed Installer**: Sign the executable with a trusted Code Signing Certificate to avoid Windows Defender warnings.
*   **Auto-Updater**: Integrate **PyUpdater** or **Omaha** to push patches to users automatically.

### 2.2 Shared Team Collaboration (Remote Sync)
*   **Current**: Local SQLite DB (`history.db`).
*   **Extension**:
    *   **Centralized Database**: Allow switching to PostgreSQL/MySQL for a shared team metadata repository.
    *   **File Locking**: If mostly local shared drives (NAS), implement file locking (`.lock` files) to prevent two users from organizing the same folder simultaneously.

### 2.3 Robust Logging & Telemetry
*   **Structured Logging**: Replace `print()` with Python `logging` module (JSON format).
*   **Sentry Integration**: capture unhandled exceptions and crashes in production.
*   **Audit Trail**: Record *who* changed a file's name or metadata and *when*, stored in a tamper-evident log.

### 2.4 CI/CD Pipeline
*   **Linting**: Enforce `flake8` or `ruff` in GitHub Actions.
*   **Testing**: Require 80%+ code coverage (pytest) before merge.
*   **Automated Builds**: GitHub Action to build the `.exe` artifact on every Tag push.

---

## 3. Architecture Evolution (Micro-Services?)
If the scope expands beyond a desktop tool:
*   **Headless Core**: Separate `src.core` into a standalone FastAPI microservice.
*   **Web Frontend**: Replace PyQt with React/Next.js for a web-based document management system (DMS).
*   **Search Engine**: Integrate **ElasticSearch** or **MeiliSearch** for full-text search content within PDFs (using `pypdf` or `tesseract` for OCR).
