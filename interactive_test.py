#!/usr/bin/env python3
"""
Interactive testing tool for SM-2 scheduler.
Allows manual verification of scheduler behavior.
"""

import sys
import time
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from danki.engine.scheduler import Scheduler, Rating
from danki.engine.db import Database


class InteractiveSchedulerTester:
    """Interactive tool for testing scheduler behavior manually."""
    
    def __init__(self):
        self.scheduler = None
        self.db = None
        self.deck_id = None
        self.current_time_offset = 0  # Offset from real time for simulation
        self.setup_temp_environment()
        
    def setup_temp_environment(self):
        """Set up temporary database and scheduler."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()
        self.temp_db_path = temp_db.name
        
        self.scheduler = Scheduler(self.temp_db_path)
        self.db = Database(self.temp_db_path)
        
        # Create test deck
        self.deck_id = self.db.create_deck("Interactive Test Deck")
        
        print(f"✅ Created temporary database: {self.temp_db_path}")
        print(f"✅ Created test deck: {self.deck_id}")
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.scheduler:
            self.scheduler.db.close()
        if self.db:
            self.db.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
            print(f"🗑️  Cleaned up: {self.temp_db_path}")
    
    def get_current_time(self):
        """Get current simulated time."""
        return int(time.time()) + self.current_time_offset
    
    def format_time(self, timestamp):
        """Format timestamp for display."""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    
    def format_duration(self, seconds):
        """Format duration in seconds to human readable."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds//60}m {seconds%60}s"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
    
    def print_separator(self):
        print("-" * 60)
    
    def create_card(self):
        """Create a new test card."""
        print("\n📝 Creating New Card")
        self.print_separator()
        
        front = input("Enter front text (or press Enter for 'Test'): ").strip()
        if not front:
            front = "Test"
            
        back = input("Enter back text (or press Enter for 'Test'): ").strip()
        if not back:
            back = "Test"
        
        note_id = self.db.add_note(self.deck_id, front, back)
        
        # Get the card ID
        card = self.db.conn.execute(
            "SELECT id FROM cards WHERE note_id = ?", (note_id,)
        ).fetchone()
        
        card_id = card['id']
        print(f"✅ Created card: {front} → {back} (ID: {card_id})")
        
        return card_id
    
    def show_card_details(self, card_id):
        """Show detailed information about a card."""
        card = self.db.conn.execute("""
            SELECT c.*, n.front, n.back, n.meta
            FROM cards c
            JOIN notes n ON c.note_id = n.id
            WHERE c.id = ?
        """, (card_id,)).fetchone()
        
        if not card:
            print(f"❌ Card not found: {card_id}")
            return
        
        now = self.get_current_time()
        due_in = card['due_ts'] - now
        
        print(f"\n📋 Card Details: {card['front']} → {card['back']}")
        print(f"   State: {card['state']}")
        print(f"   Due: {self.format_time(card['due_ts'])} ({self.format_duration(abs(due_in))} {'ago' if due_in < 0 else 'from now'})")
        print(f"   Interval: {card['interval_days']} days")
        print(f"   Ease: {card['ease']}")
        print(f"   Lapses: {card['lapses']}")
        print(f"   Step Index: {card['step_index']}")
        
        return dict(card)
    
    def show_all_cards(self):
        """Show all cards in the deck."""
        cards = self.db.conn.execute("""
            SELECT c.*, n.front, n.back
            FROM cards c
            JOIN notes n ON c.note_id = n.id
            WHERE n.deck_id = ?
            ORDER BY c.due_ts
        """, (self.deck_id,)).fetchall()
        
        print(f"\n📚 All Cards in Deck ({len(cards)} total)")
        self.print_separator()
        
        now = self.get_current_time()
        for i, card in enumerate(cards, 1):
            due_in = card['due_ts'] - now
            status = "DUE" if due_in <= 0 else "FUTURE"
            
            print(f"{i}. {card['front']} → {card['back']}")
            print(f"   State: {card['state']}, Due: {self.format_duration(abs(due_in))} {'ago' if due_in < 0 else 'from now'} [{status}]")
        
        return [dict(card) for card in cards]
    
    def show_due_cards(self):
        """Show cards due for review."""
        session = self.scheduler.build_session([self.deck_id], self.get_current_time())
        
        print(f"\n⏰ Cards Due for Review ({len(session)} total)")
        self.print_separator()
        
        if not session:
            print("No cards due for review.")
            return []
        
        for i, card in enumerate(session, 1):
            print(f"{i}. {card['front']} → {card['back']} ({card['state']})")
        
        return session
    
    def review_card(self, card_id=None):
        """Review a specific card or select one."""
        if not card_id:
            due_cards = self.show_due_cards()
            if not due_cards:
                return
            
            try:
                choice = input("\nEnter card number to review (or Enter to skip): ").strip()
                if not choice:
                    return
                
                card_idx = int(choice) - 1
                if 0 <= card_idx < len(due_cards):
                    card = due_cards[card_idx]
                    card_id = card['card_id']
                else:
                    print("Invalid choice.")
                    return
            except ValueError:
                print("Invalid input.")
                return
        
        # Show card details before review
        card = self.show_card_details(card_id)
        if not card:
            return
        
        print(f"\n🎯 Reviewing: {card['front']} → {card['back']}")
        print("Ratings: 0=Missed, 1=Almost, 2=Got It")
        
        try:
            rating_input = input("Rate this card (0-2): ").strip()
            if not rating_input:
                print("Skipped review.")
                return
            
            rating = int(rating_input)
            if rating not in [0, 1, 2]:
                print("Invalid rating. Use 0, 1, or 2.")
                return
            
            # Record the review
            answer_ms = 5000  # Simulate 5 second answer time
            self.scheduler.review(card_id, Rating(rating), answer_ms, self.get_current_time())
            
            # Show updated card state
            print(f"\n✅ Rated as {rating} ({'Missed' if rating == 0 else 'Almost' if rating == 1 else 'Got It'})")
            self.show_card_details(card_id)
            
        except ValueError:
            print("Invalid input. Please enter 0, 1, or 2.")
    
    def advance_time(self):
        """Advance simulated time."""
        print("\n⏰ Time Travel")
        self.print_separator()
        print("Current time:", self.format_time(self.get_current_time()))
        
        print("Options:")
        print("1. Minutes")
        print("2. Hours") 
        print("3. Days")
        
        try:
            unit_choice = input("Choose unit (1-3): ").strip()
            if not unit_choice:
                return
            
            amount = int(input("Enter amount: ").strip())
            
            if unit_choice == "1":
                self.current_time_offset += amount * 60
            elif unit_choice == "2":
                self.current_time_offset += amount * 3600
            elif unit_choice == "3":
                self.current_time_offset += amount * 86400
            else:
                print("Invalid choice.")
                return
            
            print(f"✅ Advanced time. New time: {self.format_time(self.get_current_time())}")
            
        except ValueError:
            print("Invalid input.")
    
    def show_stats(self):
        """Show deck statistics."""
        stats = self.db.get_stats_today([self.deck_id], self.get_current_time())
        
        print(f"\n📊 Deck Statistics")
        self.print_separator()
        print(f"New: {stats['new']}")
        print(f"Learning: {stats['learning']}")
        print(f"Review: {stats['review']}")
        print(f"Total due: {stats['total']}")
    
    def show_menu(self):
        """Show main menu."""
        print(f"\n🧪 Interactive Scheduler Tester")
        self.print_separator()
        print("1. Create card")
        print("2. Show all cards")
        print("3. Show due cards")
        print("4. Review card")
        print("5. Advance time")
        print("6. Show statistics")
        print("7. Card details")
        print("8. Quit")
        print(f"\nCurrent time: {self.format_time(self.get_current_time())}")
    
    def run(self):
        """Run the interactive tester."""
        print("🚀 Starting Interactive Scheduler Tester")
        print("This tool allows you to manually test the SM-2 scheduler behavior.")
        print("You can create cards, review them, and advance time to see scheduling in action.")
        
        try:
            while True:
                self.show_menu()
                choice = input("\nEnter your choice (1-8): ").strip()
                
                if choice == "1":
                    self.create_card()
                elif choice == "2":
                    self.show_all_cards()
                elif choice == "3":
                    self.show_due_cards()
                elif choice == "4":
                    self.review_card()
                elif choice == "5":
                    self.advance_time()
                elif choice == "6":
                    self.show_stats()
                elif choice == "7":
                    cards = self.show_all_cards()
                    if cards:
                        try:
                            idx = int(input("Enter card number for details: ")) - 1
                            if 0 <= idx < len(cards):
                                self.show_card_details(cards[idx]['id'])
                        except ValueError:
                            print("Invalid input.")
                elif choice == "8":
                    break
                else:
                    print("Invalid choice. Please enter 1-8.")
                
                input("\nPress Enter to continue...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user.")
        
        finally:
            self.cleanup()


def main():
    """Run the interactive tester."""
    tester = InteractiveSchedulerTester()
    tester.run()


if __name__ == "__main__":
    main()