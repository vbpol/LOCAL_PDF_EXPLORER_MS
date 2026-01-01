# Phase 1: MVP Core Polish - Spec & Plan

## 1. Change Specification
The goal of Phase 1 is to stabilize the Core MVP features and prepare the ground for Advanced features.
*   **Headless Capability**: Demonstrate `CoreApp` can run without UI.
*   **Documentation Refinement**: Consolidate current specs.

## 2. Detailed Implementation Plan
1.  **Script**: Create `src/run_phase1.py`.
    *   Initialize `CoreApp`.
    *   Load Config/DB.
    *   Perform a dry-run scan of a target folder.
    *   Output results to Console/JSON.
2.  **Validation**: Verify script runs clean without `ImportError` or PyQt dependency issues at runtime (though PyQt is installed, the logic shouldn't need a `QApplication`).

## 3. Validation Tests & Checklist
- [x] Script `src/run_phase1.py` exists.
- [x] Running script prints JSON output of file list.
- [x] No GUI window appears (Headless).
- [x] Database connection is successful.

## 4. Implementation Report
(See `implementation_report.md`)
