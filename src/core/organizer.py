import shutil
import pandas as pd
from pathlib import Path
from .settings import Settings

class FileOrganizer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.categories = settings.file_categories
        self.default_category = settings.default_category

    def _get_category(self, extension):
        ext = extension.lower()
        for category, extensions in self.categories.items():
            if ext in extensions:
                return category
        return self.default_category

    def scan_directory(self, path, recursive=False):
        """
        Scans directory and returns a Pandas DataFrame of files.
        """
        path_obj = Path(path)
        if not path_obj.exists():
            return pd.DataFrame()

        files_data = []
        
        # Choose iterator based on recursion
        iterator = path_obj.rglob('*') if recursive else path_obj.iterdir()
        
        for item in iterator:
            if item.is_dir():
                continue
            
            # Check ignore list
            if item.name in self.settings.ignore_files:
                continue

            category = self._get_category(item.suffix)
            # For recursive scan, we might want to preserve structure or flatten.
            # Current logic flattens into category folders in the root.
            # This is fine for the "Organizer" logic.
            
            target_dir = path_obj / category
            target_path = target_dir / item.name

            files_data.append({
                'original_path': str(item),
                'filename': item.name,
                'extension': item.suffix,
                'category': category,
                'target_dir': str(target_dir),
                'target_path': str(target_path),
                'status': 'pending',
                'action': 'move'
            })
        
        return pd.DataFrame(files_data)

    def _get_unique_filename(self, target_path):
        """Resolves filename conflicts."""
        path = Path(target_path)
        if not path.exists():
            return path
        
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1
        
        while path.exists():
            path = parent / f"{stem}_{counter}{suffix}"
            counter += 1
        return path

    def organize(self, df, dry_run=False):
        """
        Executes the organization based on the DataFrame.
        Returns the updated DataFrame.
        """
        if df.empty:
            return df

        results = []
        
        for index, row in df.iterrows():
            if row['status'] != 'pending':
                results.append(row)
                continue

            src = Path(row['original_path'])
            target_dir = Path(row['target_dir'])
            initial_target_path = Path(row['target_path'])
            
            # Recalculate unique path just before move to avoid race conditions/conflicts
            final_target_path = self._get_unique_filename(initial_target_path)
            
            # Update row with final path
            row['target_path'] = str(final_target_path)

            try:
                if not dry_run:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(final_target_path))
                    row['status'] = 'success'
                else:
                    row['status'] = 'dry_run_success'
            except Exception as e:
                row['status'] = f'error: {str(e)}'
            
            results.append(row)

        return pd.DataFrame(results)
