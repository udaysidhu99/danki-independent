"""Home screen for Danki application."""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QLineEdit, QComboBox, QFrame, QListWidget,
                              QListWidgetItem, QInputDialog, QMessageBox, QMenu)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class HomeScreen(QWidget):
    """Main home screen with add cards and start review functionality."""
    
    # Signals
    start_review_requested = Signal(str)  # deck_id - now passes selected deck ID
    show_stats_requested = Signal()
    deck_created = Signal(str)  # deck_name
    
    def __init__(self, database=None):
        super().__init__()
        self.database = database
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the home screen UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Danki Independent")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # Deck list section
        deck_list_frame = QFrame()
        deck_list_frame.setFrameStyle(QFrame.StyledPanel)
        deck_list_layout = QVBoxLayout(deck_list_frame)
        
        # Header with title and new deck button
        deck_header_layout = QHBoxLayout()
        deck_list_title = QLabel("My Decks")
        deck_list_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        deck_header_layout.addWidget(deck_list_title)
        
        deck_header_layout.addStretch()
        
        self.new_deck_btn = QPushButton("+ New Deck")
        self.new_deck_btn.clicked.connect(self.create_new_deck)
        self.new_deck_btn.setStyleSheet("QPushButton { background-color: #0078d7; color: white; padding: 4px 8px; }")
        deck_header_layout.addWidget(self.new_deck_btn)
        
        deck_list_layout.addLayout(deck_header_layout)
        
        # Deck list widget
        self.deck_list = QListWidget()
        self.deck_list.setMinimumHeight(150)
        self.deck_list.itemDoubleClicked.connect(self.on_deck_selected)
        self.deck_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.deck_list.customContextMenuRequested.connect(self.show_deck_context_menu)
        deck_list_layout.addWidget(self.deck_list)
        
        # No decks message (hidden when decks exist)
        self.no_decks_label = QLabel("No decks yet. Click 'New Deck' or use the 'Add Cards' tab!")
        self.no_decks_label.setAlignment(Qt.AlignCenter)
        self.no_decks_label.setStyleSheet("color: grey; padding: 20px; font-style: italic;")
        deck_list_layout.addWidget(self.no_decks_label)
        
        layout.addWidget(deck_list_frame)
        
        layout.addSpacing(20)
        
        # Today's goal section
        goal_frame = QFrame()
        goal_frame.setFrameStyle(QFrame.StyledPanel)
        goal_layout = QVBoxLayout(goal_frame)
        
        goal_title = QLabel("Today's Goal")
        goal_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        goal_layout.addWidget(goal_title)
        
        self.stats_label = QLabel("New: 0 | Learning: 0 | Review: 0")
        goal_layout.addWidget(self.stats_label)
        
        # Start review button
        self.review_button = QPushButton("Start Review")
        self.review_button.clicked.connect(self.start_review_requested.emit)
        self.review_button.setMinimumHeight(40)
        goal_layout.addWidget(self.review_button)
        
        layout.addWidget(goal_frame)
        
        layout.addStretch()
        
        # Stats info button
        info_layout = QHBoxLayout()
        info_layout.addStretch()
        self.stats_button = QPushButton("ⓘ Stats")
        self.stats_button.clicked.connect(self.show_stats_requested.emit)
        info_layout.addWidget(self.stats_button)
        layout.addLayout(info_layout)
        
        self.setLayout(layout)
        
        # Initialize deck list
        self.refresh_deck_list()
        
    def create_new_deck(self):
        """Create a new deck."""
        deck_name, ok = QInputDialog.getText(self, "New Deck", "Enter deck name:")
        
        if not ok or not deck_name.strip():
            return
            
        deck_name = deck_name.strip()
        
        if not self.database:
            QMessageBox.warning(self, "Error", "No database connection.")
            return
            
        try:
            # Check if deck already exists
            existing_decks = self.database.list_decks()
            for deck in existing_decks:
                if deck['name'].lower() == deck_name.lower():
                    QMessageBox.warning(self, "Deck Exists", f"A deck named '{deck_name}' already exists.")
                    return
            
            # Create new deck
            deck_id = self.database.create_deck(deck_name)
            QMessageBox.information(self, "Success", f"Created deck '{deck_name}'!")
            
            # Refresh the list
            self.refresh_deck_list()
            
            # Emit signal
            self.deck_created.emit(deck_name)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create deck: {str(e)}")
    
    def refresh_deck_list(self):
        """Refresh the deck list display."""
        self.deck_list.clear()
        
        if not self.database:
            self.no_decks_label.setVisible(True)
            self.deck_list.setVisible(False)
            return
            
        try:
            decks = self.database.list_decks()
            
            if not decks:
                self.no_decks_label.setVisible(True)
                self.deck_list.setVisible(False)
            else:
                self.no_decks_label.setVisible(False)
                self.deck_list.setVisible(True)
                
                # Add decks to list and calculate overall stats
                import time
                now_ts = int(time.time())
                
                # Calculate overall stats for all decks
                total_stats = {"new": 0, "learning": 0, "review": 0}
                
                from ...utils.study_time import study_time
                study_date = study_time.get_study_date(now_ts)
                
                for deck in decks:
                    deck_id = deck['id']
                    
                    # Get deck preferences and daily stats
                    prefs = self.database.get_deck_preferences(deck_id)
                    daily_stats = self.database.get_daily_stats(deck_id, study_date)
                    
                    # Get available cards (due now)
                    stats = self.database.get_stats_today([deck_id], now_ts)
                    
                    # Calculate remaining daily allowance
                    new_per_day = prefs.get('new_per_day', 10)
                    rev_per_day = prefs.get('rev_per_day', 100)
                    
                    new_studied = daily_stats['new_studied']
                    rev_studied = daily_stats['rev_studied']
                    
                    new_remaining = max(0, new_per_day - new_studied)
                    rev_remaining = max(0, rev_per_day - rev_studied)
                    
                    # Limit available cards by daily remaining
                    available_new = min(stats.get('new', 0), new_remaining)
                    available_rev = min(stats.get('review', 0), rev_remaining)
                    available_learning = stats.get('learning', 0)  # Learning cards always available
                    
                    total_available = available_new + available_learning + available_rev
                    
                    # Add to total stats
                    total_stats["new"] += available_new
                    total_stats["learning"] += available_learning
                    total_stats["review"] += available_rev
                    
                    # Create list item with daily progress
                    item_text = f"📚 {deck['name']}"
                    
                    if total_available > 0:
                        # Show available cards
                        parts = []
                        if available_new > 0:
                            parts.append(f"{available_new} new")
                        if available_learning > 0:
                            parts.append(f"{available_learning} learning")
                        if available_rev > 0:
                            parts.append(f"{available_rev} review")
                        item_text += f" ({', '.join(parts)})"
                    elif new_studied > 0 or rev_studied > 0:
                        # Show finished for today
                        item_text += f" ✅ Done today ({new_studied}/{new_per_day} new, {rev_studied}/{rev_per_day} review)"
                    else:
                        # No cards available and none studied
                        item_text += " (no cards due)"
                    
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, deck_id)  # Store deck ID
                    
                    # Disable if finished for the day
                    if total_available == 0 and (new_studied > 0 or rev_studied > 0):
                        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                    
                    self.deck_list.addItem(item)
                
                # Update the overall stats display
                self.update_stats(total_stats)
                    
        except Exception as e:
            print(f"Error refreshing deck list: {e}")
            self.no_decks_label.setText(f"Error loading decks: {str(e)}")
            self.no_decks_label.setVisible(True)
            self.deck_list.setVisible(False)
            
    def on_deck_selected(self, item):
        """Handle deck selection (double-click)."""
        deck_id = item.data(Qt.UserRole)
        
        # Check if deck is available for review (not disabled)
        if not (item.flags() & Qt.ItemIsEnabled):
            return  # Don't start review for finished decks
            
        # Extract deck name for logging
        full_text = item.text()
        if '📚 ' in full_text:
            deck_name = full_text.split('📚 ')[1].split(' (')[0]
        else:
            deck_name = full_text.split(' (')[0]
        
        print(f"Starting review for deck: {deck_name} (ID: {deck_id})")
        self.start_review_requested.emit(deck_id)  # Pass deck_id to signal
        
    def show_deck_context_menu(self, position):
        """Show context menu for deck list."""
        item = self.deck_list.itemAt(position)
        if not item:
            return
            
        deck_id = item.data(Qt.UserRole)
        # Extract deck name more safely
        full_text = item.text()
        if '📚 ' in full_text:
            deck_name = full_text.split('📚 ')[1].split(' (')[0]
        else:
            deck_name = full_text.split(' (')[0]
        
        menu = QMenu(self)
        
        # Add actions
        review_action = menu.addAction("📚 Start Review")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Delete Deck")
        
        # Style the menu (not individual actions in PySide6)
        menu.setStyleSheet("""
            QMenu::item:selected {
                background-color: #e3f2fd;
            }
            QMenu::item[text*="Delete"] {
                color: red;
            }
        """)
        
        # Show menu
        action = menu.exec_(self.deck_list.mapToGlobal(position))
        
        if action == review_action:
            self.on_deck_selected(item)
        elif action == delete_action:
            self.delete_deck(deck_id, deck_name)
            
    def delete_deck(self, deck_id: str, deck_name: str):
        """Delete a deck after confirmation."""
        if not self.database:
            return
            
        # Get deck stats for confirmation
        import time
        now_ts = int(time.time())
        stats = self.database.get_stats_today([deck_id], now_ts)
        
        # Confirmation dialog
        msg = f"Are you sure you want to delete the deck '{deck_name}'?"
        if stats['total'] > 0:
            msg += f"\\n\\nThis will permanently delete {stats['total']} cards."
            
        reply = QMessageBox.question(
            self, 
            "Delete Deck", 
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            # Delete deck (CASCADE will delete cards automatically)
            cursor = self.database.conn.cursor()
            cursor.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
            self.database.conn.commit()
            
            QMessageBox.information(self, "Deleted", f"Deck '{deck_name}' has been deleted.")
            
            # Refresh both screens
            self.refresh_deck_list()
            # Signal to refresh other screens
            self.deck_created.emit("")  # Empty string signals refresh
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete deck: {str(e)}")
    
    def set_database(self, database):
        """Set the database connection."""
        self.database = database
        self.refresh_deck_list()
        
    def update_stats(self, stats_dict):
        """Update the stats display."""
        new = stats_dict.get('new', 0)
        learning = stats_dict.get('learning', 0) 
        review = stats_dict.get('review', 0)
        self.stats_label.setText(f"New: {new} | Learning: {learning} | Review: {review}")
        
    def update_decks(self, deck_list):
        """Update the deck selection combo box."""
        self.deck_combo.clear()
        for deck in deck_list:
            self.deck_combo.addItem(deck['name'], deck['id'])