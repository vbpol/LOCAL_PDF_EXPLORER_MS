# Core Domain Diagram

This diagram details the internal structure and relationships of the `src.core` package, which encapsulates the application's business logic.

```mermaid
classDiagram
    namespace Core {
        class CoreApp {
            -Settings settings
            -FileOrganizer organizer
            -Storage storage
            -PDFManager pdf_manager
            -DataFrame current_plan
            -list _observers
            +__init__(config_path)
            +scan(directory_path, recursive) : DataFrame
            +execute_plan(dry_run) : DataFrame
            +export_plan(output_path) : bool
            +add_observer(callback)
            -_notify(current, total, message)
        }

        class FileOrganizer {
            -Settings settings
            -dict categories
            -str default_category
            +__init__(settings)
            +scan_directory(path, recursive) : DataFrame
            +organize(df, dry_run) : DataFrame
            -_get_category(extension) : str
            -_get_unique_filename(target_path) : Path
        }

        class DataProcessor {
            <<Service>>
            +process_scan_results(df, root_path) : DataFrame
            +update_metadata(df, file_path, tags, notes) : DataFrame
        }

        class PDFManager {
            -Storage storage
            +__init__(storage)
            +get_metadata(file_path) : dict
            +update_metadata(file_path, tags, notes, bookmarks)
        }

        class Storage {
            -Path db_path
            +__init__(db_path)
            -_init_db()
            +save_root_history(path)
            +get_root_history() : list
            +get_pdf_metadata(file_path) : dict
            +update_pdf_metadata(file_path, tags, notes, ...)
            +save_history(df)
            +get_history() : DataFrame
        }

        class Settings {
            -dict config
            +db_path : str
            +file_categories : dict
            +default_category : str
            +ignore_files : list
            +__init__(config_path)
            +load_config(path)
            +save_config(new_config)
        }
    }

    CoreApp *-- Settings : Composes
    CoreApp *-- FileOrganizer : Composes
    CoreApp *-- Storage : Composes
    CoreApp *-- PDFManager : Composes
    FileOrganizer --> Settings : Uses Config
    PDFManager --> Storage : Persists Data
    CoreApp ..> DataProcessor : Uses (Implicit via Controller or Internal)
```

## Interaction Flow (Scan & Organize)

```mermaid
sequenceDiagram
    participant Ctrl as Controller
    participant Core as CoreApp
    participant Org as FileOrganizer
    participant Proc as DataProcessor
    participant PDF as PDFManager

    Ctrl->>Core: scan(path)
    Core->>Org: scan_directory(path)
    loop Every File
        Org->>Org: _get_category()
        Org->>Org: Build Record
    end
    Org-->>Core: Raw DataFrame
    
    Core->>Core: Apply PDF Metadata Enrichment
    loop Every Row
        Core->>PDF: get_metadata(original_path)
        PDF-->>Core: {tags, notes}
    end
    
    Core->>Proc: process_scan_results(df)
    Proc-->>Core: Processed DataFrame
    Core-->>Ctrl: Final DataFrame
```
