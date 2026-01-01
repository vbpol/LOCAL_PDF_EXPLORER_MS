# Use Case Engineering Documentation

**System**: Local PDF Explorer / File Organizer
**Scope**: Functional Requirements & Industrial Analysis

---

## 1. Current System Use Cases

### UC-01: Connect & Scan Workspace
*   **Actor**: User
*   **Goal**: Load a project folder into the application.
*   **Main Flow**:
    1.  User clicks "Open Folder".
    2.  System prompts for directory selection (OS dialog).
    3.  System scans recursively for all files (default: all types, highlighted regular categories).
    4.  System matches files against local SQLite DB to retrieve previously saved tags.
    5.  System displays table with filename, tags, and category.
*   **Alternative Flow**:
    *   *History Select*: User selects a previously opened path from the Toolbar Dropdown. System loads instantly.

### UC-02: Rapid Metadata Tagging
*   **Actor**: User
*   **Goal**: Classify a document for future retrieval.
*   **Main Flow**:
    1.  User selects a row (e.g., "invoice_001.pdf").
    2.  System highlights row and populates "Metadata Panel".
    3.  User inputs "Finance, 2025, Paid" into Tags field.
    4.  User inputs "Payment confirmation for Q1" into Notes field.
    5.  User clicks "Save" (or Ctrl+S).
    6.  System commits to SQLite and updates the Grid View.

### UC-03: Contextual Search
*   **Actor**: User
*   **Goal**: Find a specific document among thousands.
*   **Main Flow**:
    1.  User types "invoice|contract" into Search Bar.
    2.  System applies Regex filter to Filename and Tags columns in real-time.
    3.  View updates to show only matching rows.

---

## 2. Potential "Pro Industrial" Use Cases

To elevate this application to an **Enterprise/Industrial Grade** solution, the following advanced use cases would provide significant value in sectors like Legal, Engineering, Finance, and Healthcare.

### UC-PRO-01: Automated Document Intelligence (OCR & Extraction)
*   **Target Sector**: Finance (Invoices), Legal (Contracts).
*   **Description**: Instead of manual tagging, the system automatically parses the PDF content.
*   **Workflow**:
    1.  User drops a scanned PDF into the "Input" folder.
    2.  **Background Service** runs OCR (Tesseract/AWS Textract).
    3.  System extracts key-value pairs via Regex/LLM: `Invoice Date`, `Total Amount`, `Vendor Name`.
    4.  **Auto-Tagging**: System automatically applies tags: `Vendor: Acme Corp`, `Amount: >$10k`.
*   **Value**: Reduces manual data entry by 90%.

### UC-PRO-02: Engineering Blueprint Version Control
*   **Target Sector**: Construction, Manufacturing, Architecture.
*   **Description**: Handling large-format PDF drawings with strict revision control.
*   **Workflow**:
    1.  Engineer saves `Schematic_v1.pdf`.
    2.  System detects file; hashes content.
    3.  Engineer saves `Schematic_v2.pdf`.
    4.  System links v2 to v1 as a **Revision Chain**.
    5.  **Audit Log**: System records "User X updated Schematic to v2 on [Date]".
*   **Value**: Prevents using outdated drawings on the production floor (a major liability issue).

### UC-PRO-03: Regulatory Compliance Archiving (WORM)
*   **Target Sector**: Healthcare (HIPAA), Finance (SEC/SOX).
*   **Description**: Ensuring files are immutable once finalized.
*   **Workflow**:
    1.  User marks dossier as "Finalized".
    2.  System calculates **SHA-256 Checksum** and stores it in a tamper-proof ledger (or Blockchain).
    3.  System sets file attribute to **Read-Only** on the file server.
    4.  Any attempt to modify the file triggers a "Compliance Violation" alert.
*   **Value**: Critical ensures audit readiness and legal defense.

### UC-PRO-04: Team Collaboration & Conflict Resolution
*   **Target Sector**: Any mid-to-large Enterprise.
*   **Description**: Multiple users organizing the same repository.
*   **Workflow**:
    1.  User A opens file `Project_Spec.pdf` to add notes.
    2.  System acquires a **File Lock** (soft lock in DB).
    3.  User B tries to edit `Project_Spec.pdf`.
    4.  System displays: *"Locked by User A. Read-Only Mode."*
    5.  **Real-Time Sync**: When User A saves, User B's view auto-refreshes via WebSocket/Polling.
*   **Value**: Prevents data overwrite and loss in shared drive environments.

### UC-PRO-05: Workflow Approval Chains
*   **Target Sector**: HR, Procurement.
*   **Description**: Moving documents through a status lifecycle.
*   **Workflow**:
    1.  User uploads "Purchase_Req.pdf". Status: `Pending`.
    2.  System notifies Manager via Email/Slack webhook.
    3.  Manager opens App, reviews, changes Status to `Approved`.
    4.  System moves file to `/Approved` folder automatically.
*   **Value**: Automates business process logic (BPA).
