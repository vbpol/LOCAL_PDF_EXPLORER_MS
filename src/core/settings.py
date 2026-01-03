import json
from pathlib import Path

class Settings:
    def __init__(self, config_path="config/settings.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            # Return default config if file missing
            return {
                "file_categories": {},
                "default_category": "Others",
                "ignore_files": [],
                "ignore_folders": [],
                "backup_enabled": False,
                "db_path": "data/history.db",
                "log_format": "json",
                "last_version_github": "",
            "date_of_publication": "",
            "github_repository_url": "",
            "local_dev_version": "0.1.0",
            "local_dev_date": ""
        }
        
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def save_config(self, new_config):
        """
        Update and save configuration to JSON file.
        """
        self.config.update(new_config)
        
        # Ensure directory exists
        if not self.config_path.parent.exists():
            self.config_path.parent.mkdir(parents=True)
            
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    @property
    def file_categories(self):
        return self.config.get("file_categories", {})

    @property
    def default_category(self):
        return self.config.get("default_category", "Others")
    
    @property
    def ignore_files(self):
        return self.config.get("ignore_files", [])

    @property
    def ignore_folders(self):
        return self.config.get("ignore_folders", [])

    @property
    def db_path(self):
        return self.config.get("db_path", "data/history.db")
