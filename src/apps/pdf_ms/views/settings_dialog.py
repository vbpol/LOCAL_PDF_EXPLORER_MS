from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                             QDialogButtonBox, QCheckBox, QLabel, QWidget)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    """
    Dialog to manage application settings.
    """
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 300)
        self.current_settings = current_settings
        self.new_settings = {}
        
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Default Category
        self.edit_default_category = QLineEdit()
        form_layout.addRow("Default Category:", self.edit_default_category)
        
        # DB Path (Read-only for now or editable if restart required)
        self.edit_db_path = QLineEdit()
        self.edit_db_path.setReadOnly(True) # Changing DB path requires complex logic
        self.edit_db_path.setToolTip("Path to the SQLite database.")
        form_layout.addRow("Database Path:", self.edit_db_path)
        
        # Backup Enabled
        self.chk_backup = QCheckBox("Enable Backups")
        form_layout.addRow("", self.chk_backup)
        
        # Log Format
        self.edit_log_format = QLineEdit()
        form_layout.addRow("Log Format:", self.edit_log_format)

        # Separator
        separator = QLabel("--- App Info ---")
        separator.setStyleSheet("font-weight: bold; margin-top: 10px;")
        form_layout.addRow(separator)

        # Local DEV Version
        self.edit_local_version = QLineEdit()
        form_layout.addRow("Local DEV Version:", self.edit_local_version)

        # Local DEV Date
        self.edit_local_date = QLineEdit()
        form_layout.addRow("Local DEV Date:", self.edit_local_date)

        # Last Version on Github
        self.edit_last_version = QLineEdit()
        form_layout.addRow("Last Version on GitHub:", self.edit_last_version)

        # Date of Publication
        self.edit_publication_date = QLineEdit()
        form_layout.addRow("Date of Publication:", self.edit_publication_date)

        # GitHub Repository URL
        self.edit_github_url = QLineEdit()
        form_layout.addRow("GitHub Repository URL:", self.edit_github_url)

        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_settings(self):
        self.edit_default_category.setText(self.current_settings.get("default_category", "Others"))
        self.edit_db_path.setText(self.current_settings.get("db_path", "data/history.db"))
        self.chk_backup.setChecked(self.current_settings.get("backup_enabled", False))
        self.edit_log_format.setText(self.current_settings.get("log_format", "json"))
        
        self.edit_local_version.setText(self.current_settings.get("local_dev_version", "0.1.0"))
        self.edit_local_date.setText(self.current_settings.get("local_dev_date", ""))
        self.edit_last_version.setText(self.current_settings.get("last_version_github", ""))
        self.edit_publication_date.setText(self.current_settings.get("date_of_publication", ""))
        self.edit_github_url.setText(self.current_settings.get("github_repository_url", ""))

    def get_settings(self):
        """
        Return the updated settings dictionary.
        """
        return {
            "default_category": self.edit_default_category.text(),
            # "db_path": self.edit_db_path.text(), # Ignored for now
            "backup_enabled": self.chk_backup.isChecked(),
            "log_format": self.edit_log_format.text(),
            "local_dev_version": self.edit_local_version.text(),
            "local_dev_date": self.edit_local_date.text(),
            "last_version_github": self.edit_last_version.text(),
            "date_of_publication": self.edit_publication_date.text(),
            "github_repository_url": self.edit_github_url.text()
        }
