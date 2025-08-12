"""Main UI application for Danki flashcard app."""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtCore import Qt

from .screens.home import HomeScreen
from .screens.review import ReviewScreen
from .screens.add_cards import AddCardsScreen
from ..engine.db import Database
from ..engine.scheduler import Scheduler, Rating


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Danki Independent")
        self.resize(700, 500)
        
        # Initialize database and scheduler
        self.database = Database("danki_data.sqlite")
        self.scheduler = Scheduler("danki_data.sqlite")
        
        # Create tab widget for main navigation
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Create screens
        self.home_screen = HomeScreen(self.database)
        self.add_cards_screen = AddCardsScreen(self.database)
        self.review_screen = ReviewScreen()
        
        # Add screens as tabs
        self.tab_widget.addTab(self.home_screen, "🏠 Home")
        self.tab_widget.addTab(self.add_cards_screen, "➕ Add Cards")
        self.tab_widget.addTab(self.review_screen, "📚 Review")
        
        # Connect signals
        self.home_screen.start_review_requested.connect(self.start_review)
        self.home_screen.deck_created.connect(self.on_deck_created)
        self.add_cards_screen.cards_added.connect(self.on_cards_added)
        self.review_screen.back_to_home.connect(self.show_home)
        self.review_screen.review_finished.connect(self.review_complete)
        self.review_screen.card_rated.connect(self.on_card_rated)
        
        # Start on home tab
        self.tab_widget.setCurrentIndex(0)
        
    def show_home(self):
        """Show the home tab."""
        self.tab_widget.setCurrentIndex(0)
        self.home_screen.refresh_deck_list()
        # TODO: Update stats
        
    def start_review(self):
        """Start a review session."""
        self.tab_widget.setCurrentIndex(2)  # Switch to Review tab
        
        # Get all deck IDs
        decks = self.database.list_decks()
        if not decks:
            self.review_screen.start_review_session([])
            return
            
        deck_ids = [deck['id'] for deck in decks]
        
        # Build review session with scheduler
        try:
            cards = self.scheduler.build_session(deck_ids, max_new=10, max_rev=50)
            self.review_screen.start_review_session(cards)
        except Exception as e:
            print(f"Error building review session: {e}")
            self.review_screen.start_review_session([])
        
    def review_complete(self):
        """Handle review session completion."""
        self.review_screen.show_completion()
        # TODO: Update stats
        
    def on_cards_added(self, count):
        """Handle cards being added."""
        print(f"Added {count} cards!")
        # Refresh home screen deck list and add cards screen deck list
        self.home_screen.refresh_deck_list()
        self.add_cards_screen.refresh_decks()
        # TODO: Show success notification
        
    def on_deck_created(self, deck_name):
        """Handle deck creation from home screen."""
        print(f"Created deck: {deck_name}")
        # Refresh add cards screen deck list
        self.add_cards_screen.refresh_decks()
        
    def on_card_rated(self, card_id, rating, answer_ms):
        """Handle card rating during review."""
        try:
            # Convert rating to scheduler Rating enum
            scheduler_rating = Rating(rating)
            self.scheduler.review(card_id, scheduler_rating, answer_ms)
            print(f"Card {card_id} rated {rating} in {answer_ms}ms")
        except Exception as e:
            print(f"Error processing card rating: {e}")
        

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Danki Independent")
    app.setOrganizationName("Danki")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
