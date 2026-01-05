from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QTextEdit, QLineEdit, QPushButton)
from PyQt6.QtCore import pyqtSignal

class MetadataView(QWidget):
    """
    MVC View: The form for editing metadata.
    Single Responsibility: Display current metadata and capture user edits.
    Passive View: Doesn't save data itself, emits signals.
    """
    
    save_requested = pyqtSignal(str, str, str) # file_path, tags, notes

    def __init__(self):
        super().__init__()
        self.current_file_path = None
        self.setMinimumWidth(200) # Ensure it doesn't get crushed too small
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Header
        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setStyleSheet("font-weight: bold;")
        self.lbl_file.setWordWrap(True)  # Allow wrapping for long paths
        layout.addWidget(self.lbl_file)

        # Tags
        layout.addWidget(QLabel("Tags (comma separated):"))
        self.txt_tags = QLineEdit()
        self.txt_tags.setToolTip("Enter tags separated by commas")
        layout.addWidget(self.txt_tags)

        # Notes
        layout.addWidget(QLabel("Notes:"))
        self.txt_notes = QTextEdit()
        self.txt_notes.setToolTip("Enter general notes for this file")
        layout.addWidget(self.txt_notes)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Metadata")
        self.btn_save.setToolTip("Save tags and notes to database")
        self.btn_save.clicked.connect(self.on_save)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        self.setLayout(layout)

    def set_data(self, file_path, tags, notes):
        self.current_file_path = file_path
        self.lbl_file.setText(f"File: {file_path}")
        self.txt_tags.setText(tags)
        self.txt_notes.setText(notes)

    def on_save(self):
        if self.current_file_path:
            self.save_requested.emit(
                self.current_file_path, 
                self.txt_tags.text(), 
                self.txt_notes.toPlainText()
            )
