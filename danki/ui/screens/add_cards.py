"""Add Cards screen for Danki application with Gemini AI integration."""

import re
import json
import requests
from typing import List, Dict, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QTextEdit, QComboBox, QProgressBar,
                              QCheckBox, QLineEdit, QMessageBox, QFrame)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

from ...utils.config import config


class GeminiWorker(QThread):
    """Worker thread for Gemini API calls to avoid blocking UI."""
    
    # Signals
    progress_updated = Signal(int)  # Progress value
    word_processed = Signal(str, dict, bool)  # word, result, success
    finished = Signal(int, int)  # success_count, total_count
    
    def __init__(self, words: List[str], api_key: str, translation_language: str = "English"):
        super().__init__()
        self.words = words
        self.api_key = api_key
        self.translation_language = translation_language
        self.should_stop = False
        
    def stop(self):
        """Request to stop processing."""
        self.should_stop = True
        
    def run(self):
        """Process words with Gemini API."""
        success_count = 0
        
        for i, word in enumerate(self.words):
            if self.should_stop:
                break
                
            # Validate word format
            if not re.match(r"^[a-zA-ZäöüÄÖÜß\s\-]+$", word):
                self.word_processed.emit(word, {"error": "Invalid characters"}, False)
                self.progress_updated.emit(i + 1)
                continue
                
            # Call Gemini API (placeholder for now)
            result = self.query_gemini_api(word)
            
            if "error" not in result:
                success_count += 1
                self.word_processed.emit(word, result, True)
            else:
                self.word_processed.emit(word, result, False)
                
            self.progress_updated.emit(i + 1)
            
        self.finished.emit(success_count, len(self.words))
        
    def query_gemini_api(self, word: str) -> Dict:
        """Query Gemini API for comprehensive German word information."""
        GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        
        prompt = (
            f"You are a helpful German language assistant. For the word: **{word}**, provide the following structured information.\n"
            f"Translate ONLY into {self.translation_language}. Do NOT include English translations unless {self.translation_language} is English.\n"
            f"Your task is to return translations and example sentences ONLY in {self.translation_language}.\n"
            "Use consistent fields: base_e, s1e, s2e, s3e.\n"
            "If the word is not a valid German word, return this JSON exactly:\n"
            '{"error": "Not a valid German word"}\n\n'
            "1. **base_d**: The original German word\n"
            f"2. **base_e**: The {self.translation_language} translation(s)\n"
            "3. **artikel_d**: The definite article if the word is a noun (e.g., \"der\", \"die\", \"das\"). Leave empty if not a noun.\n"
            "4. **plural_d**: The plural form (for nouns). Leave empty if not a noun.\n"
            "5. **word_type**: The word type: \"noun\", \"verb\", \"adjective\", etc.\n"
            "6. **conjugation**: For verbs only, provide present tense conjugation as object: {\"ich\": \"form\", \"du\": \"form\", \"er_sie_es\": \"form\", \"wir\": \"form\", \"ihr\": \"form\", \"sie_Sie\": \"form\"}\n"
            "7. **praesens**: Present tense (3rd person singular), e.g., \"läuft\"\n"
            "8. **praeteritum**: Simple past tense (3rd person singular), e.g., \"lief\"\n"
            "9. **perfekt**: Present perfect form, e.g., \"ist gelaufen\"\n"
            "10. **full_d**: A combined string of the above three conjugation forms, e.g., \"läuft, lief, ist gelaufen\"\n"
            "11. **s1**: A natural German sentence using the word\n"
            "12. **s1e**: Translation of s1 sentence\n"
            "13. **s2** (optional): A second German sentence if the word has different context\n"
            "14. **s2e** (optional): Translation of s2 sentence\n"
            "15. **s3** (optional): A third German sentence for nuance\n"
            "16. **s3e** (optional): Translation of s3 sentence\n\n"
            "Example for verb:\n"
            "```json\n"
            "{\n"
            '  "base_d": "laufen",\n'
            f'  "base_e": "to run",\n'
            '  "artikel_d": "",\n'
            '  "plural_d": "",\n'
            '  "word_type": "verb",\n'
            '  "conjugation": {"ich": "laufe", "du": "läufst", "er_sie_es": "läuft", "wir": "laufen", "ihr": "lauft", "sie_Sie": "laufen"},\n'
            '  "praesens": "läuft",\n'
            '  "praeteritum": "lief",\n'
            '  "perfekt": "ist gelaufen",\n'
            '  "full_d": "läuft, lief, ist gelaufen",\n'
            '  "s1": "Ich laufe jeden Morgen im Park.",\n'
            '  "s1e": "I run every morning in the park.",\n'
            '  "s2": "Er läuft zur Arbeit.",\n'
            '  "s2e": "He runs to work."\n'
            "}\n"
            "```\n\n"
            "Example for noun:\n"
            "```json\n"
            "{\n"
            '  "base_d": "der Hund",\n'
            f'  "base_e": "the dog",\n'
            '  "artikel_d": "der",\n'
            '  "plural_d": "die Hunde",\n'
            '  "word_type": "noun",\n'
            '  "conjugation": {},\n'
            '  "praesens": "",\n'
            '  "praeteritum": "",\n'
            '  "perfekt": "",\n'
            '  "full_d": "der Hund",\n'
            '  "s1": "Der Hund läuft im Garten.",\n'
            '  "s1e": "The dog runs in the garden."\n'
            "}\n"
            "```"
        )

        headers = {'Content-Type': 'application/json'}
        body = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        try:
            response = requests.post(GEMINI_ENDPOINT, headers=headers, json=body, timeout=30)
            result = response.json()
            
            if "candidates" not in result:
                return {"error": f"Gemini error: {result.get('error', 'No candidates returned')}"}
                
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Extract JSON from response
            match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
            if not match:
                return {"error": "JSON block not found in Gemini response"}
                
            try:
                parsed = json.loads(match.group(1))
            except json.JSONDecodeError as e:
                return {"error": f"JSON parsing failed: {str(e)}"}
            
            # Ensure we have required fields
            if "error" in parsed:
                return parsed
                
            # Set defaults for missing fields
            parsed.setdefault("base_d", word)
            parsed.setdefault("base_e", "[translation missing]")
            parsed.setdefault("artikel_d", "")
            parsed.setdefault("plural_d", "")
            parsed.setdefault("word_type", "unknown")
            parsed.setdefault("conjugation", {})
            parsed.setdefault("s1", "")
            parsed.setdefault("s1e", "")
            parsed.setdefault("s2", "")
            parsed.setdefault("s2e", "")
            parsed.setdefault("s3", "")
            parsed.setdefault("s3e", "")
            
            # Ensure full_d has a sensible value
            if not parsed.get("full_d"):
                if parsed["word_type"] == "verb" and parsed.get("praesens"):
                    forms = [parsed.get("praesens", ""), parsed.get("praeteritum", ""), parsed.get("perfekt", "")]
                    parsed["full_d"] = ", ".join(filter(None, forms))
                elif parsed["word_type"] == "noun" and parsed.get("artikel_d"):
                    parsed["full_d"] = f"{parsed['artikel_d']} {parsed['base_d']}"
                else:
                    parsed["full_d"] = parsed["base_d"]
            
            return parsed

        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


class AddCardsScreen(QWidget):
    """Add Cards screen with bulk word processing and Gemini integration."""
    
    # Signals
    cards_added = Signal(int)  # Number of cards added
    deck_created = Signal(str)  # Deck name
    
    def __init__(self, database=None):
        super().__init__()
        self.database = database
        self.gemini_worker = None
        self.setup_ui()
        self.load_saved_settings()
        
    def setup_ui(self):
        """Set up the Add Cards screen UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Add Cards with AI")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # API Key section
        api_section = QFrame()
        api_section.setFrameStyle(QFrame.StyledPanel)
        api_layout = QVBoxLayout(api_section)
        
        api_label = QLabel("Gemini API Configuration")
        api_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        api_layout.addWidget(api_label)
        
        api_input_layout = QHBoxLayout()
        api_input_layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your Gemini API key...")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_input_layout.addWidget(self.api_key_input)
        
        self.save_api_btn = QPushButton("Save")
        self.save_api_btn.clicked.connect(self.save_api_key)
        api_input_layout.addWidget(self.save_api_btn)
        api_layout.addLayout(api_input_layout)
        
        # Translation language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Translation Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Spanish", "Hindi", "French"])
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        api_layout.addLayout(lang_layout)
        
        layout.addWidget(api_section)
        layout.addSpacing(20)
        
        # Deck selection section
        deck_section = QFrame()
        deck_section.setFrameStyle(QFrame.StyledPanel)
        deck_layout = QVBoxLayout(deck_section)
        
        deck_title = QLabel("Select or Create Deck")
        deck_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        deck_layout.addWidget(deck_title)
        
        deck_selection_layout = QHBoxLayout()
        deck_selection_layout.addWidget(QLabel("Deck:"))
        self.deck_combo = QComboBox()
        self.deck_combo.setEditable(True)  # Allow typing new deck names
        self.deck_combo.setPlaceholderText("Select existing or type new deck name...")
        deck_selection_layout.addWidget(self.deck_combo)
        
        self.refresh_decks_btn = QPushButton("Refresh")
        self.refresh_decks_btn.clicked.connect(self.refresh_decks)
        deck_selection_layout.addWidget(self.refresh_decks_btn)
        deck_layout.addLayout(deck_selection_layout)
        
        layout.addWidget(deck_section)
        layout.addSpacing(20)
        
        # Word input section
        input_section = QFrame()
        input_section.setFrameStyle(QFrame.StyledPanel)
        input_layout = QVBoxLayout(input_section)
        
        input_title = QLabel("Add German Words")
        input_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        input_layout.addWidget(input_title)
        
        input_label = QLabel("Enter German words (comma or line separated):")
        input_layout.addWidget(input_label)
        
        disclaimer = QLabel("Gemini AI will generate translations, conjugations, and example sentences.")
        disclaimer.setStyleSheet("color: grey; font-size: 10px; font-style: italic;")
        input_layout.addWidget(disclaimer)
        
        self.words_input = QTextEdit()
        self.words_input.setPlaceholderText("laufen, der Hund, sprechen\\nessen\\nschlafen")
        self.words_input.setFixedHeight(100)
        input_layout.addWidget(self.words_input)
        
        # Options
        options_layout = QHBoxLayout()
        self.allow_duplicates_cb = QCheckBox("Allow duplicate words")
        self.allow_duplicates_cb.setChecked(True)
        options_layout.addWidget(self.allow_duplicates_cb)
        options_layout.addStretch()
        input_layout.addLayout(options_layout)
        
        layout.addWidget(input_section)
        
        layout.addSpacing(20)
        
        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Output log
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setFixedHeight(80)
        self.output_log.setLineWrapMode(QTextEdit.WidgetWidth)
        self.output_log.setVisible(False)
        layout.addWidget(self.output_log)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_inputs)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        
        self.process_btn = QPushButton("Process Words with AI")
        self.process_btn.clicked.connect(self.process_words)
        self.process_btn.setMinimumHeight(40)
        self.process_btn.setStyleSheet("QPushButton { background-color: #0078d7; color: white; font-weight: bold; }")
        button_layout.addWidget(self.process_btn)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Initialize
        self.refresh_decks()
        self.update_ui_state()
        
        # Connect signals
        self.words_input.textChanged.connect(self.update_ui_state)
        self.api_key_input.textChanged.connect(self.update_ui_state)
        
    def load_saved_settings(self):
        """Load saved settings from config."""
        # Load API key
        saved_api_key = config.get_api_key()
        if saved_api_key:
            self.api_key_input.setText("••••••••")  # Show that key is saved
            self.api_key_input.setPlaceholderText("API key saved (click to change)")
            
        # Load translation language
        saved_language = config.get_translation_language()
        self.language_combo.setCurrentText(saved_language)
        
        self.update_ui_state()
    
    def save_api_key(self):
        """Save the API key persistently."""
        key = self.api_key_input.text().strip()
        
        # If showing masked key, don't overwrite
        if key == "••••••••":
            QMessageBox.information(self, "API Key", "API key is already saved!")
            return
            
        if not key:
            QMessageBox.warning(self, "Invalid API Key", "Please enter a valid Gemini API key.")
            return
            
        # Save to persistent config
        config.set_api_key(key)
        
        # Update UI to show key is saved
        self.api_key_input.setText("••••••••")
        self.api_key_input.setPlaceholderText("API key saved (click to change)")
        
        QMessageBox.information(self, "API Key Saved", "Gemini API key saved successfully!")
        self.update_ui_state()
        
    def refresh_decks(self):
        """Refresh the deck list from database."""
        if not self.database:
            return
            
        self.deck_combo.clear()
        
        try:
            decks = self.database.list_decks()
            for deck in decks:
                self.deck_combo.addItem(deck['name'], deck['id'])
                
            # Add option to create new deck
            self.deck_combo.addItem("[Create New Deck]", None)
            
        except Exception as e:
            QMessageBox.warning(self, "Database Error", f"Failed to load decks: {str(e)}")
            
    def clear_inputs(self):
        """Clear all input fields."""
        self.words_input.clear()
        self.output_log.clear()
        self.progress_bar.setValue(0)
        
    def update_ui_state(self):
        """Update UI element states based on input."""
        has_words = bool(self.words_input.toPlainText().strip())
        # Check if we have a saved API key or current input
        has_api_key = bool(config.get_api_key() or 
                          (self.api_key_input.text().strip() and 
                           self.api_key_input.text().strip() != "••••••••"))
        has_deck = self.deck_combo.currentText() != ""
        
        self.process_btn.setEnabled(has_words and has_api_key and has_deck)
        self.clear_btn.setEnabled(has_words or bool(self.output_log.toPlainText()))
        
    def process_words(self):
        """Process words using Gemini API."""
        if self.gemini_worker and self.gemini_worker.isRunning():
            self.gemini_worker.stop()
            self.gemini_worker.wait()
            self.process_btn.setText("Process Words with AI")
            return
            
        # Get inputs
        words_text = self.words_input.toPlainText().strip()
        if not words_text:
            return
            
        # Parse words (comma or newline separated)
        words = re.split(r'[,\n]', words_text)
        words = [w.strip() for w in words if w.strip()]
        
        if not words:
            QMessageBox.warning(self, "No Words", "Please enter some German words to process.")
            return
            
        # Get or create deck
        deck_name = self.deck_combo.currentText()
        if not deck_name or deck_name == "[Create New Deck]":
            deck_name = self.deck_combo.currentText() if self.deck_combo.isEditable() else "My German Deck"
            
        # Ensure deck exists
        try:
            deck_id = self.ensure_deck_exists(deck_name)
            self.current_deck_id = deck_id  # Store for use in worker
        except Exception as e:
            QMessageBox.critical(self, "Deck Error", f"Failed to create/access deck: {str(e)}")
            return
            
        # Set up UI for processing
        self.output_log.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(words))
        self.progress_bar.setValue(0)
        self.output_log.clear()
        self.output_log.append(f"Processing {len(words)} words...")
        
        # Start processing
        api_key = config.get_api_key() or self.api_key_input.text().strip()
        translation_lang = self.language_combo.currentText()
        
        # Save translation language preference
        config.set_translation_language(translation_lang)
        
        self.gemini_worker = GeminiWorker(words, api_key, translation_lang)
        self.gemini_worker.progress_updated.connect(self.progress_bar.setValue)
        self.gemini_worker.word_processed.connect(self.on_word_processed)
        self.gemini_worker.finished.connect(self.on_processing_finished)
        
        self.process_btn.setText("Stop Processing")
        self.gemini_worker.start()
        
    def ensure_deck_exists(self, deck_name: str) -> str:
        """Ensure deck exists, create if necessary."""
        if not self.database:
            raise Exception("No database connection")
            
        # Check if deck exists
        decks = self.database.list_decks()
        for deck in decks:
            if deck['name'] == deck_name:
                return deck['id']
                
        # Create new deck
        deck_id = self.database.create_deck(deck_name)
        self.refresh_decks()
        return deck_id
        
    def on_word_processed(self, word: str, result: Dict, success: bool):
        """Handle word processing result."""
        if success:
            try:
                # Use the stored deck_id
                deck_id = getattr(self, 'current_deck_id', None)
                if not deck_id:
                    raise Exception("No deck selected")
                
                # Add note to database
                note_id = self.database.add_note(
                    deck_id=deck_id,
                    front=result.get('base_d', word),
                    back=result.get('base_e', '[translation]'),
                    meta=result
                )
                
                meaning = result.get('base_e', '[translation]')
                self.output_log.append(f"✓ Added: {word} → {meaning}")
                
            except Exception as e:
                self.output_log.append(f"✗ Failed to save {word}: {str(e)}")
        else:
            error = result.get('error', 'Unknown error')
            self.output_log.append(f"✗ Failed: {word} - {error}")
            
    def on_processing_finished(self, success_count: int, total_count: int):
        """Handle processing completion."""
        self.output_log.append(f"\\nDone! Successfully processed {success_count}/{total_count} words.")
        self.process_btn.setText("Process Words with AI")
        
        if success_count > 0:
            self.cards_added.emit(success_count)
            
        # Clean up
        self.gemini_worker = None
        
    def set_database(self, database):
        """Set the database connection."""
        self.database = database
        self.refresh_decks()