# Use Case Diagram

This diagram captures the functional requirements of the system from the perspective of the User.

```mermaid
usecaseDiagram
    actor "User (Knowledge Worker)" as User
    
    package "PDF Organizer App" {
        usecase "Scan Directory" as UC1
        usecase "View File List" as UC2
        usecase "Filter/Search Files" as UC3
        usecase "Open File" as UC4
        usecase "Edit Metadata\n(Tags/Notes)" as UC5
        usecase "Rename File" as UC6
        usecase "Organize/Categorize" as UC7
        usecase "View History" as UC8
    }

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    User --> UC6
    User --> UC8

    %% Relationships
    UC1 ..> UC7 : <<include>> (Auto-Categorization)
    UC3 ..> UC2 : <<extends>>
    UC5 ..> UC2 : <<extends>>
```

## Actor Definitions

*   **User (Knowledge Worker)**: A professional managing a local library of documents (PDFs, research papers, invoices).

## Functional Use Cases

| ID | Name | Description | Pre-condition |
| :--- | :--- | :--- | :--- |
| **UC1** | **Scan Directory** | Recursively index a folder to build the workspace. | Folder exists on disk. |
| **UC3** | **Search/Filter** | Filter the visible list by regex query on filename or tags. | Directory scanned. |
| **UC5** | **Edit Metadata** | Add free-text tags and notes to a specific file. | File selected in list. |
| **UC6** | **Rename File** | Change physical filename on disk; System updates DB link. | File is not open in another app. |
