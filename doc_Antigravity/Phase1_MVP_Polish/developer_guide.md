# Developer Guide (Phase 1: MVP Polish)

**Version:** 0.1.1

## 1. Environment Setup

### 1.1 Prerequisites
*   Python 3.10+
*   Windows OS (for `run.bat` compatibility)

### 1.2 Installation
1.  Clone the repository.
2.  Run `run.bat` once. It will automatically:
    *   Create a `.env` virtual environment.
    *   Install dependencies from `requirements.txt`.

## 2. Architecture Overview
The application follows a **Model-View-Controller (MVC)** pattern.

*   **Core (`src/core`)**: Business logic. Independent of UI.
    *   `CoreApp`: Facade for entry.
    *   `FileOrganizer`: Scans directories.
    *   `Storage`: SQLite interaction.
*   **App (`src/apps/pdf_ms`)**: PyQt6 Implementation.
    *   `MainController`: Glues Core and Views.
    *   `MainWindow`: The UI container.

## 3. Running & Testing

### 3.1 Manual Run
*   **GUI**: Run `run.bat` or `python src/main.py`.
*   **Headless**: Run `scripts/run_phase1.bat`.

### 3.2 Automated Tests
Run the test suite using `pytest`:
```bash
python -m pytest tests
```
*   `test_ui_smoke.py`: Checks if the GUI starts up.
*   `test_startup.py`: Checks controller initialization.

## 4. Release Workflow
1.  **Validate**: Run `pytest` and `scripts/run_phase1.bat`.
2.  **Bump Version**: Update `__version__` in `src/__init__.py`.
3.  **Tag**: `git tag -a vX.Y.Z -m "Release X"`.
