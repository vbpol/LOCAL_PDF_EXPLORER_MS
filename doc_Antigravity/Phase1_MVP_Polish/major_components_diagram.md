# Major Components Diagram

This diagram represents the high-level software components and their dependencies, following a structure similar to a C4 Component diagram.

```mermaid
componentDiagram
    component "Main Application (Launcher)" as Launcher
    
    package "Presentation Layer (UI)" {
        component "Main Window" as View
        component "Main Controller" as Controller
        component "Data Models" as UIModels
    }

    package "Domain Layer (Core)" {
        component "Core Facade" as Core
        component "File Organizer" as Organizer
        component "PDF Manager" as Manager
        component "Data Processor" as Processor
    }

    package "Infrastructure Layer" {
        component "Storage (SQLite)" as DB
        component "Settings (JSON)" as Config
        component "File System" as FS
    }

    Launcher --> Controller : Initializes
    Controller --> View : Manages
    Controller --> Core : Delegates Business Logic
    Controller ..> UIModels : Updates
    
    View --> Controller : Sends User Events
    UIModels --> View : Binding (Data)
    
    Core --> Organizer : Uses
    Core --> Manager : Uses
    Core --> Processor : Uses
    Core --> Config : Reads Config
    
    Organizer --> FS : R/W Operations
    Manager --> DB : CRUD Operations
    DB --> FS : Persists to
    Core --> DB : Log History
```

## Data Flow Description

1.  **Initialization**: The `Launcher` starts the `Controller`, which spins up the `Core` services and the `View`.
2.  **User Interaction**: Events from the `View` (like "Open Folder") are handled by the `Controller`.
3.  **Processing**: The `Controller` calls the `Core` facade. The `Core` orchestrates the `Organizer` (for files) and `Manager` (for metadata).
4.  **Persistence**: `Manager` interacts with `Storage` to save data to the SQLite `DB`.
5.  **Feedback**: Core returns data (DataFrames) which the `Controller` transforms into `UIModels` for the `View` to render.
