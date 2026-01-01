import argparse
import sys
from ...core.app import CoreApp

def run():
    parser = argparse.ArgumentParser(description="CoreApp File Organizer")
    parser.add_argument("path", nargs="?", default=".", help="Directory to organize")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without moving files")
    parser.add_argument("--export", help="Export scan results to JSON file")
    
    args = parser.parse_args()
    
    # 1. Initialize App
    try:
        app = CoreApp()
    except Exception as e:
        print(f"Initialization Error: {e}")
        sys.exit(1)

    print(f"Scanning directory: {args.path}")

    # 2. Scan
    df = app.scan(args.path)
    
    if df.empty:
        print("No files found to organize.")
        return

    print(f"\nFound {len(df)} files.")
    
    # Preview
    if 'filename' in df.columns:
        print("\n--- Preview ---")
        print(df[['filename', 'category', 'target_path']].to_string(index=False))
        print("---------------\n")

    # 3. Export if requested
    if args.export:
        app.export_plan(args.export)
        print(f"Exported plan to {args.export}")

    # 4. Execute
    if args.dry_run:
        print("DRY RUN: No files will be moved.")
        result_df = app.execute_plan(dry_run=True)
    else:
        print("Starting organization...")
        result_df = app.execute_plan(dry_run=False)
        print("Organization complete.")

    # 5. Summary
    if not result_df.empty:
        success_count = len(result_df[result_df['status'].str.contains('success')])
        error_count = len(result_df[result_df['status'].str.contains('error')])
        print(f"\nSummary: {success_count} moved, {error_count} errors.")

if __name__ == "__main__":
    run()
