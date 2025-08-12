"""Review screen for Danki application."""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QFrame, QProgressBar)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut
import time

# Import TTS
from ...utils.tts import german_tts


class ReviewScreen(QWidget):
    """Review screen with card display and rating buttons."""
    
    # Signals
    card_rated = Signal(str, int, int)  # card_id, rating, answer_ms
    review_finished = Signal()
    back_to_home = Signal()
    
    def __init__(self):
        super().__init__()
        self.current_card = None
        self.card_shown_at = None
        self.is_answer_shown = False
        self.setup_ui()
        self.setup_shortcuts()
        
    def setup_ui(self):
        """Set up the review screen UI."""
        layout = QVBoxLayout()
        
        # Header with progress
        header_layout = QHBoxLayout()
        
        self.back_button = QPushButton("← Back")
        self.back_button.clicked.connect(self.back_to_home.emit)
        header_layout.addWidget(self.back_button)
        
        header_layout.addStretch()
        
        # Audio toggle button
        self.audio_toggle_btn = QPushButton("🔊")  # Speaker icon
        self.audio_toggle_btn.clicked.connect(self.toggle_audio)
        self.audio_toggle_btn.setFixedSize(40, 30)
        self.audio_toggle_btn.setToolTip("Toggle audio on/off")
        header_layout.addWidget(self.audio_toggle_btn)
        
        header_layout.addSpacing(10)
        
        self.progress_label = QLabel("Card 1 of 10")
        header_layout.addWidget(self.progress_label)
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        layout.addSpacing(20)
        
        # Card display
        self.card_frame = QFrame()
        self.card_frame.setFrameStyle(QFrame.StyledPanel)
        self.card_frame.setMinimumHeight(200)
        card_layout = QVBoxLayout(self.card_frame)
        
        # Front text
        self.front_label = QLabel("Click 'Show Answer' to begin")
        self.front_label.setAlignment(Qt.AlignCenter)
        front_font = QFont()
        front_font.setPointSize(24)
        front_font.setBold(True)
        self.front_label.setFont(front_font)
        self.front_label.setWordWrap(True)
        self.front_label.setStyleSheet("QLabel { color: #1a252f; padding: 20px; }")
        card_layout.addWidget(self.front_label)
        
        # Back content (hidden initially) - will contain translation and metadata
        self.back_widget = QWidget()
        back_layout = QVBoxLayout(self.back_widget)
        back_layout.setSpacing(15)
        
        # Translation
        self.translation_label = QLabel()
        self.translation_label.setAlignment(Qt.AlignCenter)
        translation_font = QFont()
        translation_font.setPointSize(18)
        self.translation_label.setFont(translation_font)
        self.translation_label.setWordWrap(True)
        self.translation_label.setStyleSheet("QLabel { color: #27ae60; font-weight: bold; }")
        back_layout.addWidget(self.translation_label)
        
        # Metadata display (article, conjugations, examples)
        self.metadata_label = QLabel()
        self.metadata_label.setAlignment(Qt.AlignCenter)
        metadata_font = QFont()
        metadata_font.setPointSize(12)
        self.metadata_label.setFont(metadata_font)
        self.metadata_label.setWordWrap(True)
        self.metadata_label.setStyleSheet("QLabel { color: #7f8c8d; }")
        back_layout.addWidget(self.metadata_label)
        
        self.back_widget.hide()
        card_layout.addWidget(self.back_widget)
        
        layout.addWidget(self.card_frame)
        
        layout.addSpacing(20)
        
        # Show answer / Rating buttons
        self.button_frame = QFrame()
        button_layout = QVBoxLayout(self.button_frame)
        
        # Show answer button
        self.show_answer_button = QPushButton("Show Answer (Space)")
        self.show_answer_button.clicked.connect(self.show_answer)
        self.show_answer_button.setMinimumHeight(40)
        button_layout.addWidget(self.show_answer_button)
        
        # Rating buttons (hidden initially)
        rating_layout = QHBoxLayout()
        
        self.missed_button = QPushButton("Missed (1)")
        self.missed_button.clicked.connect(lambda: self.rate_card(0))
        self.missed_button.setStyleSheet("QPushButton { background-color: #ff6b6b; }")
        self.missed_button.hide()
        rating_layout.addWidget(self.missed_button)
        
        self.almost_button = QPushButton("Almost (2)")
        self.almost_button.clicked.connect(lambda: self.rate_card(1))
        self.almost_button.setStyleSheet("QPushButton { background-color: #feca57; }")
        self.almost_button.hide()
        rating_layout.addWidget(self.almost_button)
        
        self.got_it_button = QPushButton("Got It (3)")
        self.got_it_button.clicked.connect(lambda: self.rate_card(2))
        self.got_it_button.setStyleSheet("QPushButton { background-color: #48dbfb; }")
        self.got_it_button.hide()
        rating_layout.addWidget(self.got_it_button)
        
        button_layout.addLayout(rating_layout)
        layout.addWidget(self.button_frame)
        
        layout.addStretch()
        
        self.setLayout(layout)
        
    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        # Space to show answer
        space_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        space_shortcut.activated.connect(self.handle_space_key)
        
        # Number keys for rating
        one_shortcut = QShortcut(QKeySequence(Qt.Key_1), self)
        one_shortcut.activated.connect(lambda: self.rate_card(0))
        
        two_shortcut = QShortcut(QKeySequence(Qt.Key_2), self)
        two_shortcut.activated.connect(lambda: self.rate_card(1))
        
        three_shortcut = QShortcut(QKeySequence(Qt.Key_3), self)
        three_shortcut.activated.connect(lambda: self.rate_card(2))
        
    def handle_space_key(self):
        """Handle space key press - show answer or do nothing if answer already shown."""
        if not self.is_answer_shown:
            self.show_answer()
            
    def start_review_session(self, cards):
        """Start a review session with the given cards."""
        self.cards = cards
        self.current_card_index = 0
        if cards:
            self.show_card(cards[0])
            self.update_progress()
        else:
            self.front_label.setText("No cards to review!")
            self.show_answer_button.hide()
            
    def show_card(self, card):
        """Display a card for review."""
        self.current_card = card
        self.card_shown_at = time.time()
        self.is_answer_shown = False
        
        # Format front text for German cards
        front_text = self._format_front_text(card)
        self.front_label.setText(front_text)
        
        # Hide back and rating buttons
        self.back_widget.hide()
        self.missed_button.hide()
        self.almost_button.hide()
        self.got_it_button.hide()
        
        # Show the show answer button
        self.show_answer_button.show()
        
        # Auto-play German audio when German is shown
        self._play_german_audio_if_needed(card, front_text)

    def _format_front_text(self, card):
        """Format the front text based on card template direction."""
        template = card.get('template', 'front->back')
        meta = card.get('meta', {})
        
        # Determine what to show based on template
        if template == 'back->front':
            # Show English -> German direction
            display_text = card['back']  # Show English (back) as question
        else:
            # Show German -> English direction (default)
            display_text = card['front']  # Show German (front) as question
            
            # For German front, add article if it's a noun and not already present
            if meta and meta.get('word_type') == 'noun':
                article = meta.get('artikel_d', '')
                if article and template == 'front->back':
                    # Check if article is already present to avoid duplication
                    if not display_text.startswith(f"{article} "):
                        return f"{article} {display_text}"
        
        return display_text
        
    def show_answer(self):
        """Show the answer and rating buttons."""
        if not self.current_card:
            return
            
        self.is_answer_shown = True
        
        # Format and show back content
        self._show_back_content(self.current_card)
        
        # Hide show answer button, show rating buttons
        self.show_answer_button.hide()
        self.missed_button.show()
        self.almost_button.show()
        self.got_it_button.show()

    def _show_back_content(self, card):
        """Display formatted back content based on card template direction."""
        template = card.get('template', 'front->back')
        meta = card.get('meta', {})
        
        # Determine what to show as answer based on template
        if template == 'back->front':
            # English -> German: Show German (front) as answer
            answer_text = card['front']
            
            # Add article for German nouns when showing as answer (avoid duplication)
            if meta and meta.get('word_type') == 'noun':
                article = meta.get('artikel_d', '')
                if article and not answer_text.startswith(f"{article} "):
                    answer_text = f"{article} {answer_text}"
        else:
            # German -> English: Show English (back) as answer  
            answer_text = card['back']
        
        self.translation_label.setText(answer_text)
        
        # Format metadata (same regardless of direction)
        metadata_text = self._format_metadata(card)
        self.metadata_label.setText(metadata_text)
        
        # Show the back widget
        self.back_widget.show()
        
        # Auto-play German audio when German answer is revealed (back->front cards)
        if template == 'back->front':
            self._play_german_audio_if_needed(card, answer_text)

    def _format_metadata(self, card):
        """Format metadata for German language cards."""
        meta = card.get('meta', {})
        if not meta:
            return ""
        
        lines = []
        word_type = meta.get('word_type', '')
        
        if word_type == 'noun':
            # Show article and plural
            artikel = meta.get('artikel_d', '')
            plural = meta.get('plural_d', '')
            if artikel or plural:
                info = []
                if artikel:
                    # Color-code articles
                    color = {"der": "#3498db", "die": "#e74c3c", "das": "#f39c12"}.get(artikel, "#7f8c8d")
                    info.append(f'<span style="color: {color}; font-weight: bold;">{artikel}</span>')
                if plural:
                    info.append(f"plural: {plural}")
                lines.append(" • ".join(info))
                
        elif word_type == 'verb':
            # Show conjugations
            conjugation = meta.get('conjugation', {})
            if conjugation:
                lines.append("<b>Conjugation:</b>")
                conj_parts = []
                for person, form in conjugation.items():
                    if form:
                        conj_parts.append(f"{person}: {form}")
                if conj_parts:
                    lines.append(" • ".join(conj_parts[:3]))  # Show first 3
                    if len(conj_parts) > 3:
                        lines.append(" • ".join(conj_parts[3:]))  # Show rest
            
            # Show key tenses
            praeteritum = meta.get('praeteritum', '')
            perfekt = meta.get('perfekt', '')
            if praeteritum or perfekt:
                tenses = []
                if praeteritum:
                    tenses.append(f"Past: {praeteritum}")
                if perfekt:
                    tenses.append(f"Perfect: {perfekt}")
                lines.append(" • ".join(tenses))
        
        # Show example sentences
        examples = []
        for i in range(1, 4):  # s1, s2, s3
            example = meta.get(f's{i}', '')
            example_en = meta.get(f's{i}e', '')
            if example:
                if example_en:
                    examples.append(f"<i>{example}</i><br>&nbsp;&nbsp;→ {example_en}")
                else:
                    examples.append(f"<i>{example}</i>")
        
        if examples:
            lines.append("")  # Add spacing
            lines.append("<b>Examples:</b>")
            lines.extend(examples[:2])  # Show max 2 examples
        
        return "<br>".join(lines)
        
    def rate_card(self, rating):
        """Rate the current card and move to next."""
        if not self.current_card or not self.is_answer_shown:
            return
            
        # Calculate answer time
        answer_ms = int((time.time() - self.card_shown_at) * 1000)
        
        # Emit signal
        self.card_rated.emit(self.current_card['card_id'], rating, answer_ms)
        
        # Move to next card
        self.current_card_index += 1
        if self.current_card_index < len(self.cards):
            self.show_card(self.cards[self.current_card_index])
            self.update_progress()
        else:
            # Review session complete
            self.review_finished.emit()
            
    def update_progress(self):
        """Update progress display."""
        if hasattr(self, 'cards') and self.cards:
            current = self.current_card_index + 1
            total = len(self.cards)
            self.progress_label.setText(f"Card {current} of {total}")
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        else:
            self.progress_label.setText("No cards")
            self.progress_bar.setValue(0)
            
    def show_completion(self):
        """Show review completion screen."""
        # Hide all review elements
        self.back_widget.hide()
        self.missed_button.hide()
        self.almost_button.hide() 
        self.got_it_button.hide()
        self.show_answer_button.hide()
        
        # Show completion message
        self.front_label.setText("🎉 All Reviews Complete!\n\nGreat job! Come back tomorrow for more cards.")
        self.front_label.setStyleSheet("QLabel { color: #27ae60; padding: 40px; text-align: center; }")
        
        # Update progress to show completion
        if hasattr(self, 'cards') and self.cards:
            total = len(self.cards)
            self.progress_label.setText(f"Completed {total} cards")
            self.progress_bar.setValue(total)
        else:
            self.progress_label.setText("Session complete")
            
        # User can manually click back button to return home
    
    def toggle_audio(self):
        """Toggle TTS audio on/off and update button appearance."""
        new_state = german_tts.toggle_enabled()
        
        # Update button icon based on state
        if new_state:
            self.audio_toggle_btn.setText("🔊")  # Speaker on
            self.audio_toggle_btn.setToolTip("Audio on - Click to turn off")
        else:
            self.audio_toggle_btn.setText("🔇")  # Speaker off
            self.audio_toggle_btn.setToolTip("Audio off - Click to turn on")
    
    def _play_german_audio_if_needed(self, card, text):
        """Play German TTS audio if conditions are met."""
        if not german_tts.is_enabled():
            return
            
        template = card.get('template', 'front->back')
        meta = card.get('meta', {})
        
        # Determine if we should play German audio
        should_play_german = False
        german_text = ""
        
        if template == 'front->back':
            # German -> English direction: always play German (front text)
            should_play_german = True
            german_text = card['front']
            
            # Add article for nouns (avoid duplication)
            if meta and meta.get('word_type') == 'noun':
                article = meta.get('artikel_d', '')
                if article and not german_text.startswith(f"{article} "):
                    german_text = f"{article} {german_text}"
                    
        elif template == 'back->front':
            # English -> German direction: only play when showing German answer
            if text == card['front'] or (meta and meta.get('word_type') == 'noun' and 
                                        meta.get('artikel_d') and 
                                        text.startswith(meta.get('artikel_d', ''))):
                should_play_german = True
                german_text = card['front']
                
                # Add article for nouns if not already included
                if meta and meta.get('word_type') == 'noun':
                    article = meta.get('artikel_d', '')
                    if article and not german_text.startswith(article):
                        german_text = f"{article} {german_text}"
        
        # Play German audio if conditions are met
        if should_play_german and german_text:
            german_tts.speak(german_text)