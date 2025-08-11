"""Review screen for Danki application."""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QFrame, QProgressBar)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut
import time


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
        front_font.setPointSize(18)
        self.front_label.setFont(front_font)
        self.front_label.setWordWrap(True)
        card_layout.addWidget(self.front_label)
        
        # Back text (hidden initially)
        self.back_label = QLabel()
        self.back_label.setAlignment(Qt.AlignCenter)
        back_font = QFont()
        back_font.setPointSize(16)
        self.back_label.setFont(back_font)
        self.back_label.setWordWrap(True)
        self.back_label.hide()
        card_layout.addWidget(self.back_label)
        
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
        
        # Show front
        self.front_label.setText(card['front'])
        
        # Hide back and rating buttons
        self.back_label.hide()
        self.missed_button.hide()
        self.almost_button.hide()
        self.got_it_button.hide()
        
        # Show the show answer button
        self.show_answer_button.show()
        
    def show_answer(self):
        """Show the answer and rating buttons."""
        if not self.current_card:
            return
            
        self.is_answer_shown = True
        
        # Show back text
        self.back_label.setText(self.current_card['back'])
        self.back_label.show()
        
        # Hide show answer button, show rating buttons
        self.show_answer_button.hide()
        self.missed_button.show()
        self.almost_button.show()
        self.got_it_button.show()
        
        # TODO: Play TTS
        
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
        self.front_label.setText("🎉 Review Complete!")
        self.back_label.hide()
        self.missed_button.hide()
        self.almost_button.hide()
        self.got_it_button.hide()
        self.show_answer_button.hide()