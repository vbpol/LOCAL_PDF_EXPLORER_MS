import pandas as pd
import os

class DataProcessor:
    """
    Core component for Pandas DataFrame manipulations.
    Handles data processing, filtering, and transformation.
    """

    def __init__(self):
        pass

    def process_scan_results(self, df: pd.DataFrame, root_path: str = None) -> pd.DataFrame:
        """
        Process the raw scan results:
        1. Filter for PDFs
        2. Calculate relative paths
        3. Extract File Type and Filename without extension
        4. Add 'Actions' placeholder column
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 1. Filter for PDFs (case insensitive)
        if 'extension' in df.columns:
            df = df[df['extension'].str.lower() == '.pdf'].copy()
        
        if df.empty:
            return df

        # 2. Calculate Relative Paths
        if root_path and 'original_path' in df.columns:
             df['relative_path'] = df['original_path'].apply(
                 lambda x: os.path.relpath(x, start=root_path) if os.path.exists(root_path) else x
             )

        # 3. Extract File Type and Filename without extension
        if 'filename' in df.columns:
            df['filename_no_ext'] = df['filename'].apply(os.path.splitext).str[0]
        
        if 'extension' in df.columns:
            df['file_type'] = df['extension'].str.replace('.', '', regex=False).str.upper() + " File"

        # 4. Add Placeholder for Actions (can be used by View delegates)
        # We don't necessarily need data here, but it ensures the column exists if we want to bind it
        df['actions'] = '' 

        return df

    def update_metadata(self, df: pd.DataFrame, file_path: str, tags: str, notes: str) -> pd.DataFrame:
        """
        Update metadata in the dataframe.
        """
        if df is not None:
            mask = df['original_path'] == file_path
            df.loc[mask, 'tags'] = tags
            df.loc[mask, 'notes'] = notes
        return df
