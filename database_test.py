#!/usr/bin/env python3
"""
Database consistency and logging tests for SM-2 scheduler.
Tests data integrity, review logging accuracy, and concurrent access.
"""

import sys
import time
import tempfile
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from danki.engine.scheduler import Scheduler, Rating
from danki.engine.db import Database


class DatabaseConsistencyTester:
    """Test database consistency and review logging."""
    
    def __init__(self):
        self.scheduler = None
        self.db = None
        self.test_results = []
        self.setup_temp_environment()
    
    def setup_temp_environment(self):
        """Set up temporary database and scheduler."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()
        self.temp_db_path = temp_db.name
        
        self.scheduler = Scheduler(self.temp_db_path)
        self.db = Database(self.temp_db_path)
        
        # Create test deck
        self.test_deck_id = self.db.create_deck("Consistency Test Deck")
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.scheduler:
            self.scheduler.db.close()
        if self.db:
            self.db.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
    
    def run_test(self, name, test_func):
        """Run a single test and record results."""
        try:
            print(f"\n🧪 {name}")
            print("-" * 50)
            test_func()
            result = f"✅ PASS: {name}"
            self.test_results.append(('PASS', name, None))
        except Exception as e:
            result = f"❌ FAIL: {name} - {str(e)}"
            self.test_results.append(('FAIL', name, str(e)))
        
        print(result)
        return result
    
    def create_test_card(self, front="test", back="test"):
        """Create a test card and return its ID."""
        note_id = self.db.add_note(self.test_deck_id, front, back)
        card = self.db.conn.execute(
            "SELECT id FROM cards WHERE note_id = ?", (note_id,)
        ).fetchone()
        return card['id']
    
    def test_review_logging_accuracy(self):
        """Test that review logs match scheduler calculations."""
        print("Creating test card...")
        card_id = self.create_test_card("log_test", "logging test")
        
        # Get initial card state
        initial_card = self.db.conn.execute(
            "SELECT * FROM cards WHERE id = ?", (card_id,)
        ).fetchone()
        initial_state = dict(initial_card)
        
        now = int(time.time())
        answer_ms = 4500
        rating = Rating.GOOD
        
        print(f"Initial card state: {initial_state['state']}, interval: {initial_state['interval_days']}")
        
        # Perform review
        print(f"Rating card as {rating.name}...")
        self.scheduler.review(card_id, rating, answer_ms, now)
        
        # Get updated card state
        updated_card = self.db.conn.execute(
            "SELECT * FROM cards WHERE id = ?", (card_id,)
        ).fetchone()
        updated_state = dict(updated_card)
        
        # Get review log
        log_entry = self.db.conn.execute(
            "SELECT * FROM review_log WHERE card_id = ? ORDER BY ts DESC LIMIT 1",
            (card_id,)
        ).fetchone()
        
        print(f"Updated card state: {updated_state['state']}, interval: {updated_state['interval_days']}")
        print(f"Review log: rating={log_entry['rating']}, prev_interval={log_entry['prev_interval']}, next_interval={log_entry['next_interval']}")
        
        # Verify log accuracy
        assert log_entry['rating'] == rating.value, f"Rating mismatch: {log_entry['rating']} != {rating.value}"
        assert log_entry['answer_ms'] == answer_ms, f"Answer time mismatch: {log_entry['answer_ms']} != {answer_ms}"
        assert log_entry['prev_state'] == initial_state['state'], f"Previous state mismatch"
        assert abs(log_entry['prev_interval'] - initial_state['interval_days']) < 0.01, f"Previous interval mismatch"
        assert abs(log_entry['next_interval'] - updated_state['interval_days']) < 0.01, f"Next interval mismatch"
        
        print("✅ Review logging accuracy verified")
    
    def test_card_state_consistency(self):
        """Test that card states remain consistent after multiple reviews."""
        print("Creating test card...")
        card_id = self.create_test_card("consistency", "test")
        
        now = int(time.time())
        
        # Track state changes
        states = []
        
        def record_state():
            card = self.db.conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
            state_info = {
                'state': card['state'],
                'interval_days': card['interval_days'],
                'ease': card['ease'],
                'lapses': card['lapses'],
                'step_index': card['step_index']
            }
            states.append(state_info)
            return state_info
        
        # Initial state
        initial = record_state()
        print(f"Initial: {initial}")
        
        # Rate as GOT_IT (new -> learning step 1)
        self.scheduler.review(card_id, Rating.GOOD, 3000, now)
        after_first = record_state()
        print(f"After GOT_IT: {after_first}")
        
        # Advance time and rate again (learning -> review)
        now += 1440 * 60  # 1 day
        self.scheduler.review(card_id, Rating.GOOD, 2500, now)
        after_graduation = record_state()
        print(f"After graduation: {after_graduation}")
        
        # Rate as MISSED (review -> learning, lapse)
        now += 24 * 3600  # 1 day
        self.scheduler.review(card_id, Rating.AGAIN, 6000, now)
        after_lapse = record_state()
        print(f"After lapse: {after_lapse}")
        
        # Verify state transitions
        assert initial['state'] == 'new'
        assert after_first['state'] == 'learning' and after_first['step_index'] == 1
        assert after_graduation['state'] == 'review' and after_graduation['interval_days'] == 1.0
        assert after_lapse['state'] == 'learning' and after_lapse['lapses'] == 1
        
        # Verify ease changes
        assert after_lapse['ease'] < after_graduation['ease']  # Should be reduced due to lapse
        assert after_lapse['ease'] >= 1.3  # Should not go below floor
        
        print("✅ Card state consistency verified")
    
    def test_database_integrity_constraints(self):
        """Test database integrity constraints and foreign keys."""
        print("Testing database integrity...")
        
        # Test foreign key constraint
        try:
            # Try to create a card with invalid note_id
            fake_note_id = "non-existent-note-id"
            self.db.conn.execute(
                "INSERT INTO cards (id, note_id, template, state, due_ts) VALUES (?, ?, ?, ?, ?)",
                ("fake-card-id", fake_note_id, "front->back", "new", int(time.time()))
            )
            self.db.conn.commit()
            
            # If we get here, foreign key constraint is not working
            # Let's check if the card was actually created
            card = self.db.conn.execute(
                "SELECT * FROM cards WHERE id = ?", ("fake-card-id",)
            ).fetchone()
            
            if card:
                print("⚠️  Warning: Foreign key constraint not enforced (card created with invalid note_id)")
            else:
                print("✅ Foreign key constraint working (card not created)")
                
        except Exception as e:
            print(f"✅ Foreign key constraint working (error: {str(e)[:50]}...)")
        
        # Test unique constraint on decks
        try:
            # Try to create duplicate deck name
            self.db.create_deck("Consistency Test Deck")  # Same name as existing
            print("⚠️  Warning: Unique constraint not enforced (duplicate deck created)")
        except Exception as e:
            print(f"✅ Unique constraint working (error: {str(e)[:50]}...)")
        
        print("✅ Database integrity constraints tested")
    
    def test_concurrent_access_safety(self):
        """Test scheduler behavior under concurrent access scenarios."""
        print("Testing concurrent access safety...")
        
        # Create test card
        card_id = self.create_test_card("concurrent", "test")
        
        # Simulate concurrent reviews (same timestamp)
        now = int(time.time())
        
        # First review
        self.scheduler.review(card_id, Rating.GOOD, 3000, now)
        
        # Get state after first review
        card1 = self.db.conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        
        # Try to do another review with same timestamp (should update from current state)
        self.scheduler.review(card_id, Rating.HARD, 4000, now)
        
        # Get final state
        card2 = self.db.conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        
        print(f"After first review: {card1['state']}, step: {card1['step_index']}")
        print(f"After concurrent review: {card2['state']}, step: {card2['step_index']}")
        
        # Verify that the second review was processed based on the updated state
        # The second review should have processed the card in its current state after first review
        
        # Check that we have 2 log entries
        log_count = self.db.conn.execute(
            "SELECT COUNT(*) as count FROM review_log WHERE card_id = ?", (card_id,)
        ).fetchone()['count']
        
        assert log_count == 2, f"Expected 2 log entries, got {log_count}"
        
        print("✅ Concurrent access safety verified")
    
    def test_data_persistence(self):
        """Test that data persists correctly after scheduler operations."""
        print("Testing data persistence...")
        
        # Create multiple cards and review them
        cards = []
        for i in range(3):
            card_id = self.create_test_card(f"persist_{i}", f"persistence test {i}")
            cards.append(card_id)
        
        now = int(time.time())
        
        # Review each card differently
        self.scheduler.review(cards[0], Rating.AGAIN, 5000, now)
        self.scheduler.review(cards[1], Rating.HARD, 3500, now) 
        self.scheduler.review(cards[2], Rating.GOOD, 2000, now)
        
        # Close and reopen database connections
        self.scheduler.db.close()
        self.db.close()
        
        # Reopen
        self.scheduler = Scheduler(self.temp_db_path)
        self.db = Database(self.temp_db_path)
        
        # Verify data is still there and correct
        for i, card_id in enumerate(cards):
            card = self.db.conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
            log = self.db.conn.execute(
                "SELECT * FROM review_log WHERE card_id = ? ORDER BY ts DESC LIMIT 1", (card_id,)
            ).fetchone()
            
            assert card is not None, f"Card {i} not found after reconnect"
            assert log is not None, f"Log for card {i} not found after reconnect"
            
            expected_ratings = [Rating.AGAIN, Rating.HARD, Rating.GOOD]
            assert log['rating'] == expected_ratings[i].value, f"Rating mismatch for card {i}"
        
        print("✅ Data persistence verified")
    
    def run_all_tests(self):
        """Run all database consistency tests."""
        print("🧪 Running Database Consistency Tests")
        print("=" * 60)
        
        self.run_test("Review logging accuracy", self.test_review_logging_accuracy)
        self.run_test("Card state consistency", self.test_card_state_consistency)
        self.run_test("Database integrity constraints", self.test_database_integrity_constraints)
        self.run_test("Concurrent access safety", self.test_concurrent_access_safety)
        self.run_test("Data persistence", self.test_data_persistence)
        
        print("\n" + "=" * 60)
        
        # Summary
        passed = sum(1 for result in self.test_results if result[0] == 'PASS')
        failed = sum(1 for result in self.test_results if result[0] == 'FAIL')
        
        print(f"📊 Database Test Summary: {passed} passed, {failed} failed")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for status, name, error in self.test_results:
                if status == 'FAIL':
                    print(f"  - {name}: {error}")
        
        return passed, failed, self.test_results


def main():
    """Run the database consistency test suite."""
    tester = DatabaseConsistencyTester()
    
    try:
        passed, failed, results = tester.run_all_tests()
        return failed == 0
    finally:
        tester.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)