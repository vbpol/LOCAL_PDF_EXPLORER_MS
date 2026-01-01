
import unittest
import os
import shutil
import pandas as pd
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core.storage import Storage
from src.core.app import CoreApp

class TestHistory(unittest.TestCase):
    def setUp(self):
        # Setup temporary test environment
        self.test_dir = Path("test_history_env")
        self.test_dir.mkdir(exist_ok=True)
        self.db_path = self.test_dir / "history.db"
        self.storage = Storage(str(self.db_path))
        
        # Create some fake folders
        (self.test_dir / "folder_a").mkdir(exist_ok=True)
        (self.test_dir / "folder_b").mkdir(exist_ok=True)

    def tearDown(self):
        # Cleanup
        if self.test_dir.exists():
            try:
                shutil.rmtree(self.test_dir)
            except PermissionError:
                pass # Sometimes windows holds lock

    def test_save_and_get_history(self):
        path_a = str((self.test_dir / "folder_a").resolve())
        path_b = str((self.test_dir / "folder_b").resolve())
        
        self.storage.save_root_history(path_a)
        time.sleep(1.1) # Wait to ensure timestamp difference
        self.storage.save_root_history(path_b)
        
        # Check order (most recent first)
        history = self.storage.get_root_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], path_b)
        self.assertEqual(history[1], path_a)
        
        # Update path_a access time
        time.sleep(1.1)
        self.storage.save_root_history(path_a)
        history = self.storage.get_root_history()
        self.assertEqual(history[0], path_a)

    def test_relative_path_logic(self):
        # Simulate DataFrame logic from Controller
        root = self.test_dir / "folder_a"
        sub = root / "sub"
        sub.mkdir()
        file = sub / "test.pdf"
        file.touch()
        
        df = pd.DataFrame([{
            'original_path': str(file.resolve()),
            'filename': 'test.pdf'
        }])
        
        root_path = str(root.resolve())
        df['relative_path'] = df['original_path'].apply(lambda x: os.path.relpath(x, start=root_path))
        
        expected_rel = os.path.join("sub", "test.pdf")
        self.assertEqual(df.iloc[0]['relative_path'], expected_rel)

if __name__ == '__main__':
    unittest.main()
