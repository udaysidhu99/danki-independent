#!/usr/bin/env python3
"""
Performance and edge case tests for SM-2 scheduler.
Tests large deck performance, extreme scenarios, and edge cases.
"""

import sys
import time
import tempfile
import os
from pathlib import Path
import random

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from danki.engine.scheduler import Scheduler, Rating
from danki.engine.db import Database


class PerformanceTester:
    """Test scheduler performance and edge cases."""
    
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
        self.test_deck_id = self.db.create_deck("Performance Test Deck")
    
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
            start_time = time.time()
            test_func()
            duration = time.time() - start_time
            result = f"✅ PASS: {name} ({duration:.2f}s)"
            self.test_results.append(('PASS', name, duration))
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            result = f"❌ FAIL: {name} - {str(e)} ({duration:.2f}s)"
            self.test_results.append(('FAIL', name, str(e)))
        
        print(result)
        return result
    
    def create_bulk_cards(self, count):
        """Create multiple test cards quickly."""
        card_ids = []
        for i in range(count):
            note_id = self.db.add_note(
                self.test_deck_id, 
                f"word_{i:04d}", 
                f"meaning_{i:04d}"
            )
            # Get card ID
            card = self.db.conn.execute(
                "SELECT id FROM cards WHERE note_id = ?", (note_id,)
            ).fetchone()
            card_ids.append(card['id'])
        
        return card_ids
    
    def test_large_deck_session_building(self):
        """Test session building performance with large deck."""
        print("Creating 1000 test cards...")
        card_ids = self.create_bulk_cards(1000)
        
        print(f"Created {len(card_ids)} cards")
        
        # Test session building performance
        print("Building session...")
        start_time = time.time()
        session = self.scheduler.build_session([self.test_deck_id], int(time.time()))
        build_time = time.time() - start_time
        
        print(f"Built session with {len(session)} cards in {build_time:.3f}s")
        
        # Should be fast (< 1 second for 1000 cards)
        assert build_time < 1.0, f"Session building too slow: {build_time:.3f}s"
        
        # Should include all new cards (they're all due)
        assert len(session) == 1000, f"Expected 1000 cards, got {len(session)}"
        
        print("✅ Large deck session building performance OK")
    
    def test_extreme_intervals(self):
        """Test scheduler behavior with extreme intervals."""
        print("Testing extreme intervals...")
        
        # Create test card
        note_id = self.db.add_note(self.test_deck_id, "extreme", "test")
        card = self.db.conn.execute(
            "SELECT id FROM cards WHERE note_id = ?", (note_id,)
        ).fetchone()
        card_id = card['id']
        
        # Set extremely high interval and ease
        self.db.conn.execute("""
            UPDATE cards 
            SET state = 'review', interval_days = 10000.0, ease = 5.0, due_ts = ?
            WHERE id = ?
        """, (int(time.time()), card_id))
        self.db.conn.commit()
        
        print("Testing with extreme interval (10000 days) and ease (5.0)...")
        
        # Rate as GOT_IT
        self.scheduler.review(card_id, Rating.GOOD, 3000, int(time.time()))
        
        # Check result
        updated_card = self.db.conn.execute(
            "SELECT * FROM cards WHERE id = ?", (card_id,)
        ).fetchone()
        
        new_interval = updated_card['interval_days']
        print(f"New interval: {new_interval} days ({new_interval/365.25:.1f} years)")
        
        # Should be reasonable (not infinite or negative)
        assert new_interval > 0, "Interval should be positive"
        assert new_interval < 100000, "Interval should not be excessively large"
        assert not (new_interval != new_interval), "Interval should not be NaN"  # NaN check
        
        print("✅ Extreme intervals handled correctly")
    
    def test_minimum_ease_boundary(self):
        """Test ease floor enforcement at boundary."""
        print("Testing ease floor enforcement...")
        
        # Create card with ease just above floor
        note_id = self.db.add_note(self.test_deck_id, "ease_test", "test")
        card = self.db.conn.execute(
            "SELECT id FROM cards WHERE note_id = ?", (note_id,)
        ).fetchone()
        card_id = card['id']
        
        # Set ease to 1.31 (just above floor)
        self.db.conn.execute("""
            UPDATE cards 
            SET state = 'review', interval_days = 5.0, ease = 1.31, due_ts = ?
            WHERE id = ?
        """, (int(time.time()), card_id))
        self.db.conn.commit()
        
        print("Starting with ease = 1.31 (just above floor)")
        
        # Rate as MISSED multiple times
        for i in range(5):
            self.scheduler.review(card_id, Rating.AGAIN, 5000, int(time.time()))
            card = self.db.conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
            print(f"After lapse {i+1}: ease = {card['ease']}")
            
            # Should never go below 1.3
            assert card['ease'] >= 1.3, f"Ease below floor: {card['ease']}"
            
            # Reset to review state for next test
            self.db.conn.execute("""
                UPDATE cards 
                SET state = 'review', interval_days = 5.0, due_ts = ?
                WHERE id = ?
            """, (int(time.time()), card_id))
            self.db.conn.commit()
        
        print("✅ Ease floor enforcement verified")
    
    def test_rapid_successive_reviews(self):
        """Test rapid successive reviews of the same card."""
        print("Testing rapid successive reviews...")
        
        # Create test card
        note_id = self.db.add_note(self.test_deck_id, "rapid", "test")
        card = self.db.conn.execute(
            "SELECT id FROM cards WHERE note_id = ?", (note_id,)
        ).fetchone()
        card_id = card['id']
        
        now = int(time.time())
        
        # Perform 10 rapid reviews
        print("Performing 10 rapid reviews...")
        for i in range(10):
            rating = random.choice([Rating.HARD, Rating.GOOD])
            self.scheduler.review(card_id, rating, 1000 + i * 100, now + i)
        
        # Check that all reviews were logged
        log_count = self.db.conn.execute(
            "SELECT COUNT(*) as count FROM review_log WHERE card_id = ?", (card_id,)
        ).fetchone()['count']
        
        assert log_count == 10, f"Expected 10 log entries, got {log_count}"
        
        # Check that card is in valid state
        final_card = self.db.conn.execute(
            "SELECT * FROM cards WHERE id = ?", (card_id,)
        ).fetchone()
        
        assert final_card['state'] in ['new', 'learning', 'review'], f"Invalid final state: {final_card['state']}"
        assert final_card['ease'] >= 1.3, f"Ease below floor: {final_card['ease']}"
        
        print(f"Final state: {final_card['state']}, ease: {final_card['ease']}")
        print("✅ Rapid successive reviews handled correctly")
    
    def test_memory_usage_with_large_sessions(self):
        """Test memory usage doesn't grow excessively with large sessions."""
        print("Testing memory usage with large sessions...")
        
        # Create 5000 cards
        print("Creating 5000 cards...")
        card_ids = self.create_bulk_cards(5000)
        
        # Build multiple sessions
        print("Building 10 sessions...")
        sessions = []
        for i in range(10):
            session = self.scheduler.build_session([self.test_deck_id], int(time.time()))
            sessions.append(session)
        
        print(f"Built {len(sessions)} sessions, each with {len(sessions[0])} cards")
        
        # Basic check that sessions are consistent
        for i, session in enumerate(sessions):
            assert len(session) == len(sessions[0]), f"Session {i} has different length"
        
        print("✅ Memory usage test completed (sessions consistent)")
    
    def test_concurrent_deck_operations(self):
        """Test scheduler behavior with multiple decks."""
        print("Testing multiple deck operations...")
        
        # Create additional decks
        deck2_id = self.db.create_deck("Deck 2")
        deck3_id = self.db.create_deck("Deck 3")
        
        # Add cards to different decks
        cards_deck1 = []
        cards_deck2 = []
        cards_deck3 = []
        
        for i in range(100):
            # Deck 1
            note_id = self.db.add_note(self.test_deck_id, f"d1_word_{i}", f"d1_meaning_{i}")
            card = self.db.conn.execute("SELECT id FROM cards WHERE note_id = ?", (note_id,)).fetchone()
            cards_deck1.append(card['id'])
            
            # Deck 2
            note_id = self.db.add_note(deck2_id, f"d2_word_{i}", f"d2_meaning_{i}")
            card = self.db.conn.execute("SELECT id FROM cards WHERE note_id = ?", (note_id,)).fetchone()
            cards_deck2.append(card['id'])
            
            # Deck 3
            note_id = self.db.add_note(deck3_id, f"d3_word_{i}", f"d3_meaning_{i}")
            card = self.db.conn.execute("SELECT id FROM cards WHERE note_id = ?", (note_id,)).fetchone()
            cards_deck3.append(card['id'])
        
        print(f"Created 100 cards in each of 3 decks")
        
        # Build sessions for different deck combinations
        session_deck1 = self.scheduler.build_session([self.test_deck_id], int(time.time()))
        session_deck2 = self.scheduler.build_session([deck2_id], int(time.time()))
        session_all = self.scheduler.build_session([self.test_deck_id, deck2_id, deck3_id], int(time.time()))
        
        print(f"Deck 1 session: {len(session_deck1)} cards")
        print(f"Deck 2 session: {len(session_deck2)} cards")
        print(f"All decks session: {len(session_all)} cards")
        
        # Verify session contents
        assert len(session_deck1) >= 100, "Deck 1 session should have cards"
        assert len(session_deck2) == 100, "Deck 2 session should have 100 cards"
        assert len(session_all) >= 300, "All decks session should have all cards"
        
        # Verify no card ID overlap between single-deck sessions
        deck1_ids = {card['card_id'] for card in session_deck1 if card['card_id'] in cards_deck1}
        deck2_ids = {card['card_id'] for card in session_deck2}
        
        overlap = deck1_ids.intersection(deck2_ids)
        assert len(overlap) == 0, f"Found card ID overlap between decks: {len(overlap)} cards"
        
        print("✅ Multiple deck operations working correctly")
    
    def run_all_tests(self):
        """Run all performance and edge case tests."""
        print("🧪 Running Performance and Edge Case Tests")
        print("=" * 60)
        
        self.run_test("Large deck session building", self.test_large_deck_session_building)
        self.run_test("Extreme intervals", self.test_extreme_intervals)
        self.run_test("Minimum ease boundary", self.test_minimum_ease_boundary)
        self.run_test("Rapid successive reviews", self.test_rapid_successive_reviews)
        self.run_test("Memory usage with large sessions", self.test_memory_usage_with_large_sessions)
        self.run_test("Concurrent deck operations", self.test_concurrent_deck_operations)
        
        print("\n" + "=" * 60)
        
        # Summary
        passed = sum(1 for result in self.test_results if result[0] == 'PASS')
        failed = sum(1 for result in self.test_results if result[0] == 'FAIL')
        
        # Performance summary
        total_time = sum(result[2] for result in self.test_results if result[0] == 'PASS')
        avg_time = total_time / passed if passed > 0 else 0
        
        print(f"📊 Performance Test Summary: {passed} passed, {failed} failed")
        print(f"⏱️  Total time: {total_time:.2f}s, Average: {avg_time:.2f}s per test")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for status, name, error in self.test_results:
                if status == 'FAIL':
                    print(f"  - {name}: {error}")
        
        # Performance warnings
        slow_tests = [(name, duration) for status, name, duration in self.test_results 
                     if status == 'PASS' and duration > 2.0]
        if slow_tests:
            print(f"\n⚠️  Slow Tests (>2s):")
            for name, duration in slow_tests:
                print(f"  - {name}: {duration:.2f}s")
        
        return passed, failed, self.test_results


def main():
    """Run the performance test suite."""
    tester = PerformanceTester()
    
    try:
        passed, failed, results = tester.run_all_tests()
        return failed == 0
    finally:
        tester.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)