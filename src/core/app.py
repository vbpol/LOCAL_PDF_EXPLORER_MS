import pandas as pd
from .settings import Settings
from .organizer import FileOrganizer
from .storage import Storage
from .pdf_manager import PDFManager
from .services.bookmark_service import BookmarkService
from .services.pdf_engine import PDFEngine
from pathlib import Path

class CoreApp:
    def __init__(self, config_path="config/settings.json"):
        self.settings = Settings(config_path)
        self.organizer = FileOrganizer(self.settings)
        self.storage = Storage(self.settings.db_path)
        self.pdf_manager = PDFManager(self.storage)
        self.bookmark_service = BookmarkService(self.storage)
        self.current_plan = None
        self._observers = []

    def add_observer(self, observer_callback):
        """
        Add a callback function to receive progress updates.
        Callback signature: callback(current, total, message)
        """
        self._observers.append(observer_callback)

    def _notify(self, current, total, message):
        for callback in self._observers:
            callback(current, total, message)

    def scan(self, directory_path: str, recursive=False):
        path = Path(directory_path).resolve()
        self.current_plan = self.organizer.scan_directory(path, recursive=recursive)
        
        # Enrich with PDF metadata if available
        if self.current_plan is not None and not self.current_plan.empty:
            def get_meta(row):
                # Assuming 'target_path' or 'original_path' is the key. 
                # If we are just scanning, it's 'original_path'.
                # However, organizer returns 'original_path' column.
                fpath = str(row['original_path'])
                meta = self.pdf_manager.get_metadata(fpath)
                
                # Check DB for extracted ToC
                has_toc = bool(meta.get('bookmarks'))
                
                # If not in DB, check file physically (Real-time verification)
                if not has_toc:
                     has_toc = PDFEngine.has_toc(fpath)

                is_bookmarked = meta.get('is_bookmarked', False)
                return pd.Series([meta['tags'], meta['notes'], has_toc, is_bookmarked])

            self.current_plan[['tags', 'notes', 'has_toc', 'is_bookmarked']] = self.current_plan.apply(get_meta, axis=1)

        return self.current_plan

    def execute_plan(self, dry_run=False):
        if self.current_plan is None or self.current_plan.empty:
            return self.current_plan
        
        result_df = self.organizer.organize(self.current_plan, dry_run=dry_run)
        
        if not dry_run:
            self.storage.save_history(result_df)
            
        self.current_plan = result_df
        return result_df

    def export_plan(self, output_path: str):
        if self.current_plan is not None:
            self.current_plan.to_json(output_path, orient='records', indent=4)
            return True
        return False

    def get_history(self):
        return self.storage.get_history()

    def save_root_history(self, path):
        self.storage.save_root_history(path)

    def get_root_history(self):
        return self.storage.get_root_history()

    def update_file_metadata(self, file_path, tags, notes):
        # We preserve existing bookmarks if possible.
        # Calling update_custom is safer if we don't want to wipe bookmarks.
        self.pdf_manager.update_custom(file_path, tags=tags, notes=notes)

    def update_file_custom(self, file_path, **kwargs):
        self.pdf_manager.update_custom(file_path, **kwargs)

    def refresh_toc_status(self, file_path):
        """Returns True if file has bookmarks in DB, else False."""
        meta = self.pdf_manager.get_metadata(file_path)
        return bool(meta.get('bookmarks'))

    def toggle_bookmark(self, file_path):
        """Toggle user bookmark (favorite) status."""
        return self.bookmark_service.toggle_bookmark(file_path)
