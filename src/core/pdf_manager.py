from .storage import Storage
import json

class PDFManager:
    def __init__(self, storage: Storage):
        self.storage = storage

    def get_metadata(self, file_path: str):
        """Get metadata for a file, parsing JSON fields if necessary."""
        data = self.storage.get_pdf_metadata(file_path)
        # Ensure tags are a list if stored as JSON/CSV, or keep as string depending on design
        # For this MVC, let's keep it simple: Tags are comma-separated strings in UI, stored as string
        return data

    def update_metadata(self, file_path: str, tags: str, notes: str, bookmarks: str = ""):
        """Update metadata in storage."""
        # Check if bookmarks is empty, maybe we should preserve existing?
        # Current usage suggests this method is for overwriting provided fields.
        # But if we want partial updates, we should use update_custom.
        self.storage.update_pdf_metadata(file_path, tags, notes, bookmarks)

    def update_custom(self, file_path: str, **kwargs):
        """
        Perform a partial update.
        Reads existing metadata, updates only provided keys, and saves back.
        Supported keys: 'tags', 'notes', 'bookmarks'.
        """
        current = self.get_metadata(file_path)
        
        tags = kwargs.get('tags', current['tags'])
        notes = kwargs.get('notes', current['notes'])
        bookmarks = kwargs.get('bookmarks', current['bookmarks'])
        
        self.storage.update_pdf_metadata(file_path, tags, notes, bookmarks)
