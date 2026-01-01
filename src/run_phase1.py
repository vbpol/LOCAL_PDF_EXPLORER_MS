import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.app import CoreApp

def main():
    print("Initializing CoreApp (Headless Mode)...")
    app = CoreApp()
    
    # Define a test path (ensure this exists or use current dir)
    target_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Scanning directory: {target_dir}")
    # Run scan
    df = app.scan(target_dir)
    
    print(f"Scan Complete. Found {len(df)} files.")
    
    # Convert a subset to JSON for demonstration
    if not df.empty:
        result = df[['filename', 'category', 'status']].head(5).to_dict(orient='records')
        print(json.dumps(result, indent=2))
    else:
        print("No files found.")

if __name__ == "__main__":
    main()
