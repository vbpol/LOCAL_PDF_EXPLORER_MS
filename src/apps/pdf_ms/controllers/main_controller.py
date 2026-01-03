from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication
from PyQt6.QtCore import QModelIndex, Qt
import os
import sys
import subprocess

from src.core.app import CoreApp
from src.core.data_processor import DataProcessor
from src.core.settings import Settings
from src.apps.pdf_ms.models.pdf_table_model import PDFTableModel
from src.apps.pdf_ms.models.pdf_proxy_model import PDFSortFilterProxyModel
from src.apps.pdf_ms.views.main_window import MainWindow
from src.apps.pdf_ms.views.metadata_view import MetadataView
from src.apps.pdf_ms.views.settings_dialog import SettingsDialog
from src.apps.pdf_ms.views.reader_window import ReaderWindow

class MainController:
    """
    MVC Controller: The Glue.
    Responsibilities:
    1. Handle user actions from Views (Open Folder, Select File, Save).
    2. Call Model (CoreApp) to fetch/update data.
    3. Update Views with new data.
    """
    def __init__(self):
        self.app_core = CoreApp()
        self.data_processor = DataProcessor()
        self.full_df = None # Store complete scanned data
        
        # Initialize Views
        self.main_window = MainWindow()
        self.metadata_view = MetadataView()
        self.main_window.add_metadata_view(self.metadata_view)
        
        # Initialize Model Wrapper
        self.table_model = PDFTableModel()
        
        # Proxy Model for Sorting/Filtering
        self.proxy_model = PDFSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        
        self.main_window.table_view.setModel(self.proxy_model)

        # Connect Signals
        self.main_window.act_open_folder.triggered.connect(self.open_folder)
        self.main_window.act_restart.triggered.connect(self.restart_app)
        self.main_window.act_settings.triggered.connect(self.open_settings)
        self.main_window.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.main_window.table_view.doubleClicked.connect(self.on_double_click)
        self.main_window.search_input.textChanged.connect(self.on_search)
        self.metadata_view.save_requested.connect(self.save_metadata)
        self.main_window.combo_history.activated.connect(self.on_history_selected)
        
        # Connect Table Signals
        self.main_window.table_view.file_open_requested.connect(self.on_double_click)
        self.main_window.table_view.folder_open_requested.connect(self.open_containing_folder)
        self.main_window.table_view.metadata_edit_requested.connect(self.on_edit_metadata) # Optional explicit edit
        self.main_window.table_view.file_rename_requested.connect(self.rename_file)
        self.main_window.table_view.toc_action_requested.connect(self.on_toc_action)
        self.main_window.table_view.batch_toc_requested.connect(self.on_batch_toc_generation)
        
        # Connect Metadata View Signals (if any generic ones, currently handled via Reader or dedicated view)
        pass

        self.reader_windows = [] # Keep references to prevent GC

        # Initialize File Watcher BEFORE loading history
        from src.core.services.file_watcher import FileWatcherService
        self.file_watcher = FileWatcherService()
        self.file_watcher.handler.file_created.connect(self.on_file_changed)
        self.file_watcher.handler.file_deleted.connect(self.on_file_changed)
        self.file_watcher.handler.file_moved.connect(self.on_file_changed)

        # Load History and Startup (may trigger _load_folder_data which needs file_watcher)
        self.load_history_and_startup()

    def on_file_changed(self, path):
        """
        Refresh view when file system changes.
        Optimisation: Could update model directly, but simple reload is safer for MVP.
        """
        # Checks if the change is relevant to the current directory
        current_root = self.main_window.combo_history.currentText()
        if current_root:
            normalized_root = os.path.abspath(current_root)
            normalized_path = os.path.abspath(path)
            
            # Simple check if changed file is within current root
            if normalized_path.startswith(normalized_root):
                 print(f"File changed: {path}. Reloading...")
                 self._load_folder_data(current_root)

    def show(self):
        self.main_window.show()

    def on_toc_action(self, index):
        """
        Handle click on ToC Status button.
        """
        row = index.row()
        file_path = self.table_model.get_file_path_at(row)
        if not file_path or not os.path.exists(file_path):
            return

        has_toc = self.app_core.refresh_toc_status(file_path)
        
        if has_toc:
            # Open Reader
            reader = ReaderWindow(file_path, self.app_core, self.main_window)
            reader.show()
            self.reader_windows.append(reader)
        else:
            # Generate ToC
            try:
                # Show loading cursor
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                
                from src.core.services.pdf_renderer import PDFRenderer
                import json
                
                toc = PDFRenderer.get_toc(file_path)
                toc_json = json.dumps(toc)
                self.app_core.update_file_custom(file_path, bookmarks=toc_json)
                
                # Refresh UI (Reload folder to update 'has_toc' column)
                # We could just update the model data if we knew where to poke, but reloading is safer for MVP
                current_root = self.main_window.combo_history.currentText()
                if current_root:
                    self._load_folder_data(current_root)
                    
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", f"ToC Generation Failed: {str(e)}")
            finally:
                QApplication.restoreOverrideCursor()

    def on_edit_metadata(self, index):
        """
        Explicit action to edit metadata.
        Opens Reader Window focused on metadata (Right Panel).
        """
        self.on_double_click(index)

    def on_batch_toc_generation(self, indexes):
        """
        Generate ToC for multiple selected PDFs.
        """
        if not indexes:
            return
            
        # Show progress / confirmation
        reply = QMessageBox.question(
            self.main_window,
            "Batch ToC Generation",
            f"Generate Table of Contents for {len(indexes)} selected PDFs?\n\n"
            "This may take a few moments for large files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            from src.core.services.pdf_renderer import PDFRenderer
            import json
            
            success_count = 0
            error_files = []
            
            for index in indexes:
                try:
                    source_index = self.proxy_model.mapToSource(index)
                    row = source_index.row()
                    file_path = self.table_model.get_file_path_at(row)
                    
                    if not file_path or not os.path.exists(file_path):
                        error_files.append(os.path.basename(file_path) if file_path else "Unknown")
                        continue
                    
                    # Extract ToC
                    toc = PDFRenderer.get_toc(file_path)
                    toc_json = json.dumps(toc)
                    
                    # Save to DB
                    self.app_core.update_file_custom(file_path, bookmarks=toc_json)
                    success_count += 1
                    
                except Exception as e:
                    error_files.append(f"{os.path.basename(file_path)}: {str(e)}")
            
            # Refresh UI
            current_root = self.main_window.combo_history.currentText()
            if current_root:
                self._load_folder_data(current_root)
            
            # Show summary
            msg = f"Successfully generated ToC for {success_count}/{len(indexes)} files."
            if error_files:
                msg += f"\n\n Errors:\n" + "\n".join(error_files[:5])  # Show first 5 errors
                if len(error_files) > 5:
                    msg += f"\n... and {len(error_files) - 5} more."
            
            QMessageBox.information(self.main_window, "Batch ToC Complete", msg)
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Batch generation failed: {str(e)}")
        finally:
            QApplication.restoreOverrideCursor()

    def load_history_and_startup(self):
        history = self.app_core.get_root_history()
        self.main_window.combo_history.clear()
        if history:
            self.main_window.combo_history.addItems(history)
            # Auto-load the most recent one
            first_root = history[0]
            if os.path.exists(first_root):
                 self._load_folder_data(first_root)

    def on_history_selected(self, index):
        folder_path = self.main_window.combo_history.itemText(index)
        if folder_path:
             self._load_folder_data(folder_path)

    def update_history_combo(self, current_path):
        # Block signals to prevent triggering on_history_selected loop
        self.main_window.combo_history.blockSignals(True)
        
        # Refresh list from DB to get correct order (most recent first)
        history = self.app_core.get_root_history()
        self.main_window.combo_history.clear()
        self.main_window.combo_history.addItems(history)
        
        # Select the current one
        index = self.main_window.combo_history.findText(current_path)
        if index >= 0:
             self.main_window.combo_history.setCurrentIndex(index)
             
        self.main_window.combo_history.blockSignals(False)

    def restart_app(self):
        """
        Restarts the application by launching the run_pdf_ms.bat file.
        """
        # Close the current window
        self.main_window.close()
        
        # Determine the path to the batch file
        # Assuming the batch file is in the project root
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        bat_path = os.path.join(root_dir, "run_pdf_ms.bat")
        
        if os.path.exists(bat_path):
             subprocess.Popen([bat_path], shell=True, cwd=root_dir)
        else:
             # Fallback to python restart if bat not found
             python = sys.executable
             os.execl(python, python, *sys.argv)
             
        QApplication.quit()

    def open_containing_folder(self, index: QModelIndex):
        """
        Open the folder containing the selected file in Windows Explorer.
        """
        if not index.isValid():
            return
            
        # Map proxy index to source index if needed (though on_double_click logic handles it via helper)
        # But here we just need the file path.
        
        # We can reuse logic from on_double_click to get path, then open dirname
        source_index = self.proxy_model.mapToSource(index)
        row = source_index.row()
        file_path = self.table_model.get_file_path_at(row)
        
        if file_path and os.path.exists(file_path):
            folder_path = os.path.dirname(file_path)
            try:
                os.startfile(folder_path)
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", f"Failed to open folder: {str(e)}")
        else:
            QMessageBox.warning(self.main_window, "Warning", "File path not found or invalid.")

    def rename_file(self, index: QModelIndex, new_name: str):
        """
        Rename file logic.
        """
        # Map proxy index to source index
        source_index = self.proxy_model.mapToSource(index)
        row = source_index.row()
        
        # Get current file path
        current_path = self.table_model.get_file_path_at(row)
        
        if not current_path or not os.path.exists(current_path):
             QMessageBox.warning(self.main_window, "Error", "File not found!")
             return
             
        # Construct new path
        directory = os.path.dirname(current_path)
        old_name = os.path.basename(current_path)
        ext = os.path.splitext(old_name)[1]
        
        # Ensure new name has extension or append original
        if not new_name.lower().endswith(ext.lower()):
            new_name += ext
            
        new_path = os.path.join(directory, new_name)
        
        if os.path.exists(new_path):
             QMessageBox.warning(self.main_window, "Error", "A file with that name already exists!")
             return
             
        try:
            # Rename file on disk
            os.rename(current_path, new_path)
            
            # Update Database/Core (if it tracks paths by ID, update path; if path is key, delete/insert)
            # The current CoreApp uses path as key. So we might need to handle this.
            # But CoreApp mainly scans. Metadata is tied to path.
            # We should update metadata to new path if possible.
            
            # Let's see if we can update metadata
            # self.app_core.pdf_manager.rename_file(current_path, new_path) # Not implemented yet
            
            # For now, simplest approach:
            # 1. Update DF
            # 2. Update Model
            
            # Update DataFrame
            # We need to update 'original_path', 'filename', 'filename_no_ext', 'relative_path'
            mask = self.full_df['original_path'] == current_path
            
            self.full_df.loc[mask, 'filename'] = new_name
            self.full_df.loc[mask, 'filename_no_ext'] = os.path.splitext(new_name)[0]
            self.full_df.loc[mask, 'original_path'] = new_path
            
            if 'relative_path' in self.full_df.columns:
                 # Re-calculate relative path if we have root
                 # We don't store root explicitly in controller except implicitly via context
                 # But we can approximate or just leave it if it's in same folder
                 # If new_name is just name change, directory is same.
                 # So relative path just changes filename.
                 old_rel = self.full_df.loc[mask, 'relative_path'].values[0]
                 new_rel = os.path.join(os.path.dirname(old_rel), new_name)
                 self.full_df.loc[mask, 'relative_path'] = new_rel

            # Refresh Model
            self.table_model.set_data(self.full_df)
            
            QMessageBox.information(self.main_window, "Success", f"Renamed to {new_name}")

            # Restore Selection
            # Find the row with the new path in the full_df (which is mapped to model rows 1:1)
            # But model might be sorted/filtered via proxy.
            
            # 1. Find the new row index in source model
            # We can search in self.full_df again, but we just updated it.
            # We can iterate or use loc. index is preserved in pandas usually?
            # self.full_df index is usually 0..N.
            
            # Let's find the index of the row where original_path == new_path
            new_row_indices = self.full_df.index[self.full_df['original_path'] == new_path].tolist()
            
            if new_row_indices:
                source_row = new_row_indices[0]
                source_idx = self.table_model.index(source_row, 0)
                
                # Map to proxy
                proxy_idx = self.proxy_model.mapFromSource(source_idx)
                
                if proxy_idx.isValid():
                    self.main_window.table_view.selectRow(proxy_idx.row())
                    self.main_window.table_view.scrollTo(proxy_idx)
            
        except Exception as e:
             QMessageBox.critical(self.main_window, "Error", f"Failed to rename: {str(e)}")

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self.main_window, "Select Folder")
        if folder:
            self._load_folder_data(folder)

    def _load_folder_data(self, folder_path):
        if not os.path.exists(folder_path):
             QMessageBox.warning(self.main_window, "Error", f"Path does not exist: {folder_path}")
             return

        # Scan
        raw_df = self.app_core.scan(folder_path, recursive=True)
        
        # Process Data via DataProcessor
        df = self.data_processor.process_scan_results(raw_df, root_path=folder_path)
        
        self.full_df = df
        
        # Update View Model
        self.table_model.set_data(self.full_df)
        
        # Reset Metadata View
        self.metadata_view.set_data("", "", "")

        # Save History & Update UI
        self.app_core.save_root_history(folder_path)
        self.update_history_combo(folder_path)
        
        # Update Title
        self.main_window.setWindowTitle(f"PDF Management System - {folder_path}")
        
        # Start Watcher
        self.file_watcher.start_watching(folder_path)

    def on_search(self, text):
        # Use Proxy Model Filtering
        from PyQt6.QtCore import QRegularExpression
        
        # Escape special characters for regex if needed, or use Wildcard pattern
        # Here we use case-insensitive fixed string match via regex escaping or just simple contains
        # But QRegularExpression is powerful.
        
        if not text:
            self.proxy_model.setFilterRegularExpression("")
        else:
            # Create a regex that matches any part of the string
            # QRegularExpression.escape(text) is safer for literal search
            pattern = QRegularExpression.escape(text)
            regex = QRegularExpression(pattern)
            regex.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.proxy_model.setFilterRegularExpression(regex)

    def open_settings(self):
        settings = Settings()
        dialog = SettingsDialog(settings.config, self.main_window)
        if dialog.exec():
            new_config = dialog.get_settings()
            settings.save_config(new_config)
            QMessageBox.information(self.main_window, "Success", "Settings saved successfully!")

    def on_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            # Get the first selected row (Proxy Index)
            proxy_index = indexes[0]
            
            # Map to Source Index
            source_index = self.proxy_model.mapToSource(proxy_index)
            row = source_index.row()
            
            # Get data from Model
            file_path = self.table_model.get_file_path_at(row)
            
            # Fetch fresh metadata from Core (SSOT)
            meta = self.app_core.pdf_manager.get_metadata(file_path)
            self.metadata_view.set_data(file_path, meta['tags'], meta['notes'])
        else:
            # Clear metadata view if no selection
            self.metadata_view.set_data("", "", "")

    def save_metadata(self, file_path, tags, notes):
        try:
            # Update Core (SSOT)
            self.app_core.update_file_metadata(file_path, tags, notes)
            
            # Update In-Memory DF via DataProcessor
            self.full_df = self.data_processor.update_metadata(self.full_df, file_path, tags, notes)
                
            # Force view update?
            # The model references the same DF, but we might need to notify change
            # However, if we modified self.full_df in place (which Pandas often does for assignment if no copy), it might be fine.
            # But update_metadata returns the DF, so let's set it back.
            
            # Better: Notify model specific row changed
            # Finding the row is expensive if we don't have the index. 
            # For now, simplest is to reset model or emit dataChanged if we had index.
            # But the table model holds a reference to self.full_df (or a copy of it).
            # If set_data stored the reference, modifying self.full_df in place updates the model's data.
            # If update_metadata returns a new object, we need to call set_data again.
            
            self.table_model.set_data(self.full_df)
            
            # Re-apply scroll/selection if needed (not implemented yet)
            
            QMessageBox.information(self.main_window, "Success", "Metadata saved successfully!")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", str(e))

    def on_double_click(self, index: QModelIndex):
        # Index is from Proxy Model
        source_index = self.proxy_model.mapToSource(index)
        row = source_index.row()
        
        file_path = self.table_model.get_file_path_at(row)
        if file_path and os.path.exists(file_path):
            # NEW: Open Reader Window instead of system viewer
            reader = ReaderWindow(file_path, self.app_core, self.main_window)
            reader.show()
            self.reader_windows.append(reader) # Prevent GC
            
            # Clean up closed windows
            reader.destroyed.connect(lambda: self.reader_windows.remove(reader) if reader in self.reader_windows else None)
        else:
            QMessageBox.warning(self.main_window, "Error", "File does not exist.")
