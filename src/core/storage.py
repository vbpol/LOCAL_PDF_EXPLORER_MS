import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

class Storage:
    def __init__(self, db_path="data/history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with history table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                original_path TEXT,
                filename TEXT,
                category TEXT,
                target_path TEXT,
                status TEXT,
                action TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pdf_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                tags TEXT,
                notes TEXT,
                bookmarks TEXT,
                is_bookmarked INTEGER DEFAULT 0,
                last_modified TEXT
            )
        ''')
        
        # Migration: Add is_bookmarked column if it doesn't exist
        try:
            cursor.execute("SELECT is_bookmarked FROM pdf_metadata LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE pdf_metadata ADD COLUMN is_bookmarked INTEGER DEFAULT 0")
            conn.commit()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS root_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                last_accessed TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def save_root_history(self, path):
        """Save a root folder path to history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        accessed = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Upsert: if path exists, update timestamp
        cursor.execute('''
            INSERT INTO root_history (path, last_accessed)
            VALUES (?, ?)
            ON CONFLICT(path) DO UPDATE SET
                last_accessed=excluded.last_accessed
        ''', (str(path), accessed))
        conn.commit()
        conn.close()

    def get_root_history(self):
        """Retrieve root folder history ordered by most recent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM root_history ORDER BY last_accessed DESC")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_pdf_metadata(self, file_path):
        """Retrieve metadata for a specific PDF file."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT tags, notes, bookmarks, is_bookmarked FROM pdf_metadata WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "tags": row[0], 
                "notes": row[1], 
                "bookmarks": row[2],
                "is_bookmarked": bool(row[3])
            }
        return {"tags": "", "notes": "", "bookmarks": "", "is_bookmarked": False}

    def update_bookmark_status(self, file_path, is_bookmarked):
        """Update only the bookmark status (favorite/starred)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        modified = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Upsert logic is tricky for partial update if row doesn't exist.
        # Check if exists first.
        cursor.execute("SELECT 1 FROM pdf_metadata WHERE file_path = ?", (file_path,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute('''
                UPDATE pdf_metadata 
                SET is_bookmarked = ?, last_modified = ?
                WHERE file_path = ?
            ''', (1 if is_bookmarked else 0, modified, file_path))
        else:
            # Insert new row with default empty values for others
            cursor.execute('''
                INSERT INTO pdf_metadata (file_path, tags, notes, bookmarks, is_bookmarked, last_modified)
                VALUES (?, '', '', '', ?, ?)
            ''', (file_path, 1 if is_bookmarked else 0, modified))
            
        conn.commit()
        conn.close()

    def update_pdf_metadata(self, file_path, tags, notes, bookmarks):
        """Update or insert metadata for a PDF file."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        modified = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO pdf_metadata (file_path, tags, notes, bookmarks, last_modified)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                tags=excluded.tags,
                notes=excluded.notes,
                bookmarks=excluded.bookmarks,
                last_modified=excluded.last_modified
        ''', (file_path, tags, notes, bookmarks, modified))
        conn.commit()
        conn.close()

    def save_history(self, df):
        """Save operations history to SQLite."""
        if df.empty:
            return

        # Ensure timestamp is string for SQLite
        df['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Filter columns to match table schema
        cols = ['timestamp', 'original_path', 'filename', 'category', 'target_path', 'status', 'action']
        
        # If df doesn't have some columns, add them
        for col in cols:
            if col not in df.columns:
                df[col] = None

        save_df = df[cols].copy()
        
        conn = sqlite3.connect(self.db_path)
        save_df.to_sql('history', conn, if_exists='append', index=False)
        conn.close()

    def get_history(self):
        """Retrieve history as DataFrame."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM history", conn)
        conn.close()
        return df

    def export_json(self, df, path):
        """Export current operations to JSON."""
        df.to_json(path, orient='records', indent=4)
