"""Preferences dialog for Danki application."""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QLineEdit, QComboBox, QFrame, QMessageBox,
                              QGroupBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...utils.config import config


class PreferencesDialog(QDialog):
    """Dialog for managing application preferences."""
    
    # Signal emitted when preferences are saved
    preferences_saved = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.resize(500, 300)
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        """Set up the preferences dialog UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Preferences")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # AI Settings Group
        ai_group = QGroupBox("AI Card Generation")
        ai_layout = QVBoxLayout(ai_group)
        
        # API Key
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("Gemini API Key:"))
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your Gemini API key...")
        self.api_key_input.setMinimumWidth(300)
        api_layout.addWidget(self.api_key_input)
        
        ai_layout.addLayout(api_layout)
        
        # Translation Language
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Translation Language:"))
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Spanish", "Hindi", "French"])
        self.language_combo.setMinimumWidth(150)
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        
        ai_layout.addLayout(lang_layout)
        
        # API Key help
        help_label = QLabel("Get your free API key from: https://ai.google.dev/")
        help_label.setStyleSheet("color: #666; font-size: 11px;")
        ai_layout.addWidget(help_label)
        
        layout.addWidget(ai_group)
        
        # Future settings groups can go here
        # e.g., Review Settings, Audio Settings, etc.
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_preferences)
        self.save_btn.setStyleSheet("QPushButton { background-color: #0078d7; color: white; padding: 8px 16px; }")
        self.save_btn.setDefault(True)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_current_settings(self):
        """Load current settings from config."""
        # Load API key
        saved_api_key = config.get_api_key()
        if saved_api_key:
            self.api_key_input.setText(saved_api_key)
        
        # Load translation language
        saved_language = config.get_translation_language()
        self.language_combo.setCurrentText(saved_language)
    
    def save_preferences(self):
        """Save preferences to config."""
        # Save API key
        api_key = self.api_key_input.text().strip()
        if api_key:
            config.set_api_key(api_key)
        
        # Save translation language
        language = self.language_combo.currentText()
        config.set_translation_language(language)
        
        # Emit signal and close
        self.preferences_saved.emit()
        QMessageBox.information(self, "Preferences Saved", 
                              "Your preferences have been saved successfully!")
        self.accept()