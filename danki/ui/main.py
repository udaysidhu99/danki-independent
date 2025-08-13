"""Main UI application for Danki flashcard app."""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QMessageBox
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
        self.review_screen = ReviewScreen()  # Keep for review sessions, but not as tab
        
        # Add screens as tabs (no Review tab)
        self.tab_widget.addTab(self.home_screen, "🏠 Home")
        self.tab_widget.addTab(self.add_cards_screen, "➕ Add Cards")
        
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
        """Show the home tab and restore main navigation."""
        try:
            # Restore the tab widget as central widget if it's not already
            if self.centralWidget() != self.tab_widget:
                self.setCentralWidget(self.tab_widget)
            
            # Switch to home tab and refresh
            self.tab_widget.setCurrentIndex(0)
            self.home_screen.refresh_deck_list()
        except RuntimeError:
            # Widgets were deleted, recreate everything
            self.recreate_ui()
            
    def recreate_ui(self):
        """Recreate the main UI if widgets were deleted."""
        try:
            # Recreate all components
            from .screens.home import HomeScreen
            from .screens.add_cards import AddCardsScreen
            
            # Create new screens
            self.home_screen = HomeScreen(self.database)
            self.add_cards_screen = AddCardsScreen(self.database)
            
            # Create new tab widget
            self.tab_widget = QTabWidget()
            self.setCentralWidget(self.tab_widget)
            
            # Add tabs
            self.tab_widget.addTab(self.home_screen, "🏠 Home")
            self.tab_widget.addTab(self.add_cards_screen, "➕ Add Cards")
            
            # Reconnect signals
            self.home_screen.start_review_requested.connect(self.start_review)
            self.home_screen.deck_created.connect(self.on_deck_created)
            self.add_cards_screen.cards_added.connect(self.on_cards_added)
            
            # Set to home tab and refresh
            self.tab_widget.setCurrentIndex(0)
            self.home_screen.refresh_deck_list()
        except Exception as e:
            print(f"Error recreating UI: {e}")
            # Force close if we can't recover
            self.close()
        
    def start_review(self, deck_id):
        """Start a review session for a specific deck."""
        if not deck_id:
            QMessageBox.warning(self, "No Deck Selected", "Please select a deck to review.")
            return
            
        # Use only the selected deck
        deck_ids = [deck_id]
        
        # Build review session with scheduler
        try:
            cards = self.scheduler.build_session(deck_ids, max_new=10, max_rev=50)
            if not cards:
                # Get deck name for better error message
                deck_name = "Selected deck"
                try:
                    deck_info = self.database.get_deck(deck_id)
                    if deck_info:
                        deck_name = deck_info['name']
                except:
                    pass
                    
                QMessageBox.information(self, "No Cards Due", f"No cards are due for review in '{deck_name}' right now!")
                return
                
            # Ensure review screen exists and is connected
            self.ensure_review_screen()
                
            # Replace main content with review screen
            self.setCentralWidget(self.review_screen)
            self.review_screen.start_review_session(cards, deck_ids)
            
        except Exception as e:
            print(f"Error building review session: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start review session: {str(e)}")
            
    def ensure_review_screen(self):
        """Ensure review screen exists and is properly connected."""
        try:
            # Test if review screen is still valid by accessing a property
            _ = self.review_screen.isVisible()
        except (RuntimeError, AttributeError):
            # Review screen was deleted, recreate it
            from .screens.review import ReviewScreen
            self.review_screen = ReviewScreen()
            self.review_screen.back_to_home.connect(self.show_home)
            self.review_screen.review_finished.connect(self.review_complete)
            self.review_screen.card_rated.connect(self.on_card_rated)
        
    def review_complete(self):
        """Handle review session completion."""
        try:
            self.review_screen.show_completion()
        except (RuntimeError, AttributeError):
            # Review screen was deleted, just return to home
            self.show_home()
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
        """Handle card rating during review with dynamic queue rebuilding."""
        try:
            # Convert rating to scheduler Rating enum
            scheduler_rating = Rating(rating)
            self.scheduler.review(card_id, scheduler_rating, answer_ms)
            print(f"Card {card_id} rated {rating} in {answer_ms}ms")
            
            # CRITICAL: Rebuild session queue dynamically (Anki behavior)
            self.rebuild_review_queue()
            
        except Exception as e:
            print(f"Error processing card rating: {e}")
    
    def rebuild_review_queue(self):
        """Rebuild the review queue after each card to include newly due learning cards."""
        try:
            if not hasattr(self.review_screen, 'current_deck_ids'):
                return
                
            # Get the deck being reviewed
            deck_ids = getattr(self.review_screen, 'current_deck_ids', [])
            if not deck_ids:
                return
            
            # Build new session with current limits
            new_cards = self.scheduler.build_session(deck_ids, max_new=10, max_rev=50)
            
            if new_cards:
                # Update the review screen with refreshed queue
                self.review_screen.update_session_queue(new_cards)
            else:
                # No more cards - end session
                self.review_screen.end_session_early()
                
        except Exception as e:
            print(f"Error rebuilding review queue: {e}")
        

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
