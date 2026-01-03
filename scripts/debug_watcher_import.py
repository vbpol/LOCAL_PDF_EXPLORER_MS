import sys
import os

# Add project root
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root)

print(f"Root: {root}")

try:
    from src.core.services.file_watcher import FileWatcherService
    print(" Import Success")
except Exception as e:
    print(f" Import Failed: {e}")
    import traceback
    traceback.print_exc()

import fitz
print("Fitz (PyMuPDF) imported")
from watchdog.observers import Observer
print("Watchdog imported")
