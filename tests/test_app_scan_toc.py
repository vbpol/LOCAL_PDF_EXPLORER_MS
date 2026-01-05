import sys
import os
import pandas as pd
import pytest

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..')
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

from src.core.app import CoreApp

def test_scan_toc_population():
    # Setup
    app = CoreApp(config_path="config/settings.json")
    
    # Use the test_files directory
    test_files_dir = os.path.join(current_dir, '..', 'test_files')
    test_files_dir = os.path.abspath(test_files_dir)
    
    print(f"Scanning directory: {test_files_dir}")
    
    # Scan
    df = app.scan(test_files_dir)
    
    # Verify DataFrame columns
    assert 'has_toc' in df.columns
    assert 'filename' in df.columns
    
    print("\nScan Results:")
    print(df[['filename', 'has_toc']])
    
    # Verify specific files
    # We know 'dummy_with_toc.pdf' has ToC, 'dummy_no_toc.pdf' does not.
    
    row_with_toc = df[df['filename'] == 'dummy_with_toc.pdf']
    if not row_with_toc.empty:
        assert row_with_toc.iloc[0]['has_toc'] == True, "dummy_with_toc.pdf should have has_toc=True"
        print("✓ dummy_with_toc.pdf verification passed")
        
    row_no_toc = df[df['filename'] == 'dummy_no_toc.pdf']
    if not row_no_toc.empty:
        assert row_no_toc.iloc[0]['has_toc'] == False, "dummy_no_toc.pdf should have has_toc=False"
        print("✓ dummy_no_toc.pdf verification passed")

if __name__ == "__main__":
    try:
        test_scan_toc_population()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTest Failed: {e}")
        import traceback
        traceback.print_exc()
