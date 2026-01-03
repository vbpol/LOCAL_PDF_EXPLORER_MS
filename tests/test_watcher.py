import sys
import os
import time
import pytest
from PyQt6.QtCore import QCoreApplication

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.services.file_watcher import FileWatcherService

@pytest.fixture
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    yield app

def test_file_creation_detection(qapp, tmp_path):
    """
    Test that creating a PDF triggers the signal.
    """
    service = FileWatcherService()
    
    # Track signal emission
    signals_received = []
    def on_created(path):
        signals_received.append(path)
        
    service.handler.file_created.connect(on_created)
    
    # Start watching
    watch_dir = str(tmp_path)
    service.start_watching(watch_dir)
    
    # Create a PDF file
    test_file = os.path.join(watch_dir, "new_doc.pdf")
    with open(test_file, 'w') as f:
        f.write("dummy content")
        
    # Wait for event (watchdog is threaded)
    start_time = time.time()
    while not signals_received and time.time() - start_time < 2:
        qapp.processEvents()
        time.sleep(0.1)
        
    service.stop_watching()
    
    assert len(signals_received) > 0
    assert os.path.normpath(signals_received[0]) == os.path.normpath(test_file)
    print("File Creation Detected Successfully")

def test_ignore_non_pdf(qapp, tmp_path):
    """
    Test that creating a TXT file DOES NOT trigger the signal.
    """
    service = FileWatcherService()
    signals_received = []
    service.handler.file_created.connect(lambda p: signals_received.append(p))
    
    watch_dir = str(tmp_path)
    service.start_watching(watch_dir)
    
    # Create a TXT file
    test_file = os.path.join(watch_dir, "notes.txt")
    with open(test_file, 'w') as f:
        f.write("dummy content")
        
    # Wait briefly
    start_time = time.time()
    while time.time() - start_time < 1:
        qapp.processEvents()
        time.sleep(0.1)
        
    service.stop_watching()
    
    assert len(signals_received) == 0
    print("Non-PDF Ignored Successfully")
