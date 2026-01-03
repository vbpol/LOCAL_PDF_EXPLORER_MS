from src.core.storage import Storage

class BookmarkService:
    """
    Service to handle user bookmarks (favorites/starred files).
    Scalable design to allow future extensions (e.g., bookmark categories, tags).
    """
    def __init__(self, storage: Storage):
        self.storage = storage

    def toggle_bookmark(self, file_path: str) -> bool:
        """
        Toggles the bookmark status for the given file.
        Returns the new status (True/False).
        """
        meta = self.storage.get_pdf_metadata(file_path)
        new_status = not meta.get('is_bookmarked', False)
        self.storage.update_bookmark_status(file_path, new_status)
        return new_status

    def is_bookmarked(self, file_path: str) -> bool:
        """Check if a file is bookmarked."""
        meta = self.storage.get_pdf_metadata(file_path)
        return meta.get('is_bookmarked', False)

    def get_all_bookmarks(self):
        """
        Retrieve all bookmarked files.
        (Future implementation for a 'Bookmarks' view)
        """
        # TODO: Add query method in Storage if needed
        pass
