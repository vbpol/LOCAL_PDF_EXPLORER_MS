# Project Workflow & Release Process

## 1. Phase Completion Workflow
When a development phase (e.g., Phase 1 MVP Polish) is completed:

1.  **Validate Core**: Run the corresponding phase script (e.g., `scripts/run_phase1.bat`) to ensure CoreApp stability in headless mode.
2.  **Validate UI (Automated)**: Run `pytest tests/test_ui_smoke.py` to ensure the application initializes without crashing.
3.  **Validate UI (Manual)**: Run `run.bat` to verify the window opens and renders correctly.
4.  **Bump Version**:
    *   Open `src/__init__.py`.
    *   Increment `__version__` (Semantic Versioning: Major.Minor.Patch).
    *   *Example*: `0.1.0` -> `0.1.1`.
3.  **Documentation**:
    *   Ensure `doc_Antigravity/PhaseX/implementation_report.md` is filled and signed off.
4.  **Git Commit & Tag**:
    ```bash
    git add .
    git commit -m "feat: complete Phase 1, bump version to 0.1.1"
    git tag -a v0.1.1 -m "Release Phase 1"
    git push origin main --tags
    ```

## 2. GitHub Project Integration
(Recommended Usage)

*   **Issues**: Create an Issue for each Phase spec item.
*   **Projects**: Use a Kanban board ("Todo", "In Progress", "Done").
*   **Milestones**: Assign Issues to "Phase 1", "Phase 2" milestones.

## 3. Automation (Future)
*   A GitHub Action can be added to auto-run `run_phase1.py` on Pull Request.
