# UI Subsystems Diagram

This diagram details the `src.apps.pdf_ms` package, focusing on the View-Controller interactions and the signal/slot architecture.

## Class Hierarchy (View Layer)

```mermaid
classDiagram
    namespace Views {
        class MainWindow {
            -QToolBar toolbar
            -QSplitter splitter
            +PDFTableView table_view
            +MetadataView metadata_view
            +add_metadata_view(widget)
            +toggle_info_panel(checked)
        }

        class PDFTableView {
            -ActionDelegate action_delegate
            +file_open_requested(index)
            +file_rename_requested(index, name)
            +metadata_edit_requested(index)
            +configure_columns()
            +show_context_menu(pos)
        }

        class MetadataView {
            -QLabel lbl_file
            -QLineEdit txt_tags
            -QTextEdit txt_notes
            +save_requested(path, tags, notes)
            +set_data(path, tags, notes)
        }

        class SettingsDialog {
            -QLineEdit edit_default_category
            -QCheckBox chk_backup
            +get_settings() : dict
        }
    }

    namespace Controllers {
        class MainController {
            -CoreApp app_core
            -MainWindow main_window
            -PDFTableModel table_model
            -PDFSortFilterProxyModel proxy_model
            +show()
            +open_folder()
            +on_selection_changed(...)
            +save_metadata(...)
        }
    }
    
    namespace Models {
        class PDFTableModel {
             +set_data(df)
             +get_file_path_at(row)
        }
        class PDFSortFilterProxyModel {
             +filterAcceptsRow(...)
        }
    }

    MainController o-- MainWindow : Owns
    MainController o-- PDFTableModel : Owns
    MainWindow *-- PDFTableView : Contains
    MainWindow *-- MetadataView : Contains
    MainWindow ..> SettingsDialog : Creates
    PDFTableView --|> QTableView : Inherits
    PDFTableView ..> ActionDelegate : Uses
```

## Signal Flow (User Interaction)

```mermaid
sequenceDiagram
    participant User
    participant View as PDFTableView
    participant Win as MainWindow
    participant Ctrl as MainController
    participant Model as PDFTableModel
    participant Core as CoreApp

    rect rgb(240, 240, 255)
    note right of User: Scenario: User Double Clicks File
    User->>View: Double Click (Index)
    View->>Win: Emit doubleClicked(Index)
    Win->>Ctrl: Slot on_double_click(Index)
    Ctrl->>Model: get_file_path_at(Row)
    Model-->>Ctrl: "C:/Docs/file.pdf"
    Ctrl->>Core: (System Call) os.startfile()
    end

    rect rgb(255, 240, 240)
    note right of User: Scenario: User Saves Metadata
    User->>Win: Click "Save" in MetadataView
    Win->>Ctrl: Emit save_requested(path, tags, notes)
    Ctrl->>Core: update_file_metadata(...)
    Ctrl->>Model: set_data(df)
    Model->>View: dataChanged() (Repaint)
    end
```
