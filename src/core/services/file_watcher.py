import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt6.QtCore import QObject, pyqtSignal

class FileMetadataHandler(QObject, FileSystemEventHandler):
    """
    Handles file system events and emits Qt signals.
    """
    # Signals to update UI
    file_created = pyqtSignal(str)
    file_deleted = pyqtSignal(str)
    file_moved = pyqtSignal(str, str) # src, dest
    
    def __init__(self):
        QObject.__init__(self) # Init Qt Object

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            self.file_created.emit(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            self.file_deleted.emit(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            self.file_moved.emit(event.src_path, event.dest_path)

class FileWatcherService(QObject):
    """
    Service to watch a directory for PDF changes.
    """
    def __init__(self):
        super().__init__()
        self.observer = Observer()
        self.handler = FileMetadataHandler()
        self.watch = None
        
    def start_watching(self, path):
        if self.watch:
             self.observer.unschedule(self.watch)
             
        self.watch = self.observer.schedule(self.handler, path, recursive=True)
        if not self.observer.is_alive():
            self.observer.start()
            
    def stop_watching(self):
        self.observer.stop()
        self.observer.join()
