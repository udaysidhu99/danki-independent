#!/usr/bin/env python3
"""
Comprehensive unit tests for SM-2 scheduler implementation.
Tests core logic without database dependencies.
"""

import sys
import time
import tempfile
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from danki.engine.scheduler import Scheduler, Rating


class MockCard:
    """Mock card for testing scheduler logic without database."""
    
    def __init__(self, state='new', ease=2.5, interval_days=0, lapses=0, step_index=0):
        self.data = {
            'state': state,
            'ease': ease,
            'interval_days': interval_days,
            'lapses': lapses,
            'step_index': step_index,
            'due_ts': int(time.time())  # Default to now
        }
    
    def __getitem__(self, key):
        return self.data[key]
    
    def update(self, **kwargs):
        self.data.update(kwargs)


class SchedulerTester:
    """Test harness for SM-2 scheduler logic."""
    
    def __init__(self):
        self.scheduler = None
        self.test_results = []
        self.setup_temp_scheduler()
    
    def setup_temp_scheduler(self):
        """Create temporary scheduler for testing."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()
        self.temp_db_path = temp_db.name
        self.scheduler = Scheduler(self.temp_db_path)
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.scheduler:
            self.scheduler.db.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
    
    def run_test(self, name, test_func):
        """Run a single test and record results."""
        try:
            test_func()
            result = f"✅ PASS: {name}"
            self.test_results.append(('PASS', name, None))
        except Exception as e:
            result = f"❌ FAIL: {name} - {str(e)}"
            self.test_results.append(('FAIL', name, str(e)))
        
        print(result)
        return result
    
    def assert_card_state(self, result, expected_state, expected_due_offset=None, expected_interval=None):
        """Helper to validate card state transitions."""
        state, due_ts, interval, ease, lapses, step_index = result
        
        if state != expected_state:
            raise AssertionError(f"Expected state '{expected_state}', got '{state}'")
        
        if expected_due_offset is not None:
            now = int(time.time())
            expected_due = now + expected_due_offset
            if abs(due_ts - expected_due) > 60:  # Allow 1 minute tolerance
                raise AssertionError(f"Expected due_ts ~{expected_due}, got {due_ts}")
        
        if expected_interval is not None:
            if abs(interval - expected_interval) > 0.1:
                raise AssertionError(f"Expected interval {expected_interval}, got {interval}")
    
    # NEW CARD TESTS
    def test_new_card_missed(self):
        """New card rated MISSED should go to learning step 0 (10 min)."""
        card = MockCard(state='new')
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.AGAIN, now)
        
        self.assert_card_state(result, 'learning', 1 * 60, 0)  # 1 minute
    
    def test_new_card_almost(self):
        """New card rated ALMOST should go to learning step 0 (10 min)."""
        card = MockCard(state='new')
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.HARD, now)
        
        self.assert_card_state(result, 'learning', 1 * 60, 0)  # 1 minute
    
    def test_new_card_got_it(self):
        """New card rated GOOD should start learning at step 0 (1 minute)."""
        card = MockCard(state='new')
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.GOOD, now)
        
        self.assert_card_state(result, 'learning', 1 * 60, 0)  # 1 minute
    
    # LEARNING CARD TESTS
    def test_learning_step_0_missed(self):
        """Learning step 0 rated AGAIN should reset to step 0 (1 min)."""
        card = MockCard(state='learning', step_index=0)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.AGAIN, now)
        
        self.assert_card_state(result, 'learning', 1 * 60, 0)
    
    def test_learning_step_0_almost(self):
        """Learning step 0 rated HARD should stay at step 0 (10 min minimum)."""
        card = MockCard(state='learning', step_index=0)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.HARD, now)
        
        self.assert_card_state(result, 'learning', 10 * 60, 0)
    
    def test_learning_step_0_got_it(self):
        """Learning step 0 rated GOT_IT should advance to step 1 (1 day)."""
        card = MockCard(state='learning', step_index=0)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.GOOD, now)
        
        self.assert_card_state(result, 'learning', 10 * 60, 0)
    
    def test_learning_step_1_missed(self):
        """Learning step 1 rated AGAIN should reset to step 0 (1 min)."""
        card = MockCard(state='learning', step_index=1)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.AGAIN, now)
        
        self.assert_card_state(result, 'learning', 1 * 60, 0)
    
    def test_learning_step_1_almost(self):
        """Learning step 1 rated ALMOST should stay at step 1 (1 day)."""
        card = MockCard(state='learning', step_index=1)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.HARD, now)
        
        self.assert_card_state(result, 'learning', 10 * 60, 0)
    
    def test_learning_graduation(self):
        """Learning step 1 rated GOT_IT should graduate to review (1 day)."""
        card = MockCard(state='learning', step_index=1)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.GOOD, now)
        
        # With fuzzing, graduation interval ~1 day (±5%)
        state, due_ts, interval, ease, lapses, step_index = result
        now = int(time.time())
        expected_due = now + (24 * 3600)  # 1 day
        
        assert state == 'review', f"Expected 'review', got '{state}'"
        assert 0.95 <= interval <= 1.05, f"Expected interval ~1.0 (±5%), got {interval}"
        assert abs(due_ts - expected_due) <= (0.05 * 24 * 3600), f"Due time within fuzzing range"
    
    # REVIEW CARD TESTS
    def test_review_missed_lapse(self):
        """Review card rated MISSED should lapse back to learning."""
        card = MockCard(state='review', ease=2.5, interval_days=5.0)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.AGAIN, now)
        
        state, due_ts, interval, ease, lapses, step_index = result
        
        assert state == 'learning', f"Expected 'learning', got '{state}'"
        assert step_index == 0, f"Expected step_index=0, got {step_index}"
        assert ease < 2.5, f"Expected ease < 2.5, got {ease}"  # Should be reduced
        assert ease >= 1.3, f"Expected ease >= 1.3, got {ease}"  # Floor at 1.3
    
    def test_review_almost_hard(self):
        """Review card rated ALMOST should reduce ease and increase interval by 1.2x."""
        card = MockCard(state='review', ease=2.5, interval_days=5.0)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.HARD, now)
        
        state, due_ts, interval, ease, lapses, step_index = result
        
        assert state == 'review', f"Expected 'review', got '{state}'"
        assert ease == 2.35, f"Expected ease=2.35, got {ease}"  # 2.5 - 0.15
        # Allow for fuzzing (±5%)
        expected = 6.0  # 5.0 * 1.2
        assert 5.7 <= interval <= 6.3, f"Expected interval ~6.0 (±5%), got {interval}"
    
    def test_review_got_it_good(self):
        """Review card rated GOT_IT should maintain ease and multiply by ease factor."""
        card = MockCard(state='review', ease=2.5, interval_days=5.0)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.GOOD, now)
        
        state, due_ts, interval, ease, lapses, step_index = result
        
        assert state == 'review', f"Expected 'review', got '{state}'"
        assert ease == 2.5, f"Expected ease=2.5, got {ease}"  # Unchanged
        # Allow for fuzzing (±5%)
        expected = 12.5  # 5.0 * 2.5
        assert 11.9 <= interval <= 13.1, f"Expected interval ~12.5 (±5%), got {interval}"
    
    def test_ease_floor_enforcement(self):
        """Ease should never go below 1.3."""
        card = MockCard(state='review', ease=1.35, interval_days=2.0)  # Close to floor
        now = int(time.time())
        
        # Multiple missed reviews should not push ease below 1.3
        result = self.scheduler._calculate_next_state(card.data, Rating.AGAIN, now)
        state, due_ts, interval, ease, lapses, step_index = result
        
        assert ease >= 1.3, f"Expected ease >= 1.3, got {ease}"
    
    def test_interval_minimum(self):
        """Intervals should have reasonable minimums."""
        card = MockCard(state='review', ease=1.3, interval_days=0.5)
        now = int(time.time())
        
        result = self.scheduler._calculate_next_state(card.data, Rating.HARD, now)
        state, due_ts, interval, ease, lapses, step_index = result
        
        assert interval >= 1.0, f"Expected interval >= 1.0, got {interval}"
    
    def run_all_tests(self):
        """Run all unit tests and return summary."""
        print("🧪 Running SM-2 Scheduler Unit Tests")
        print("=" * 50)
        
        # New card tests
        self.run_test("New card MISSED → learning", self.test_new_card_missed)
        self.run_test("New card ALMOST → learning", self.test_new_card_almost)
        self.run_test("New card GOT_IT → learning step 1", self.test_new_card_got_it)
        
        # Learning tests
        self.run_test("Learning step 0 MISSED → reset", self.test_learning_step_0_missed)
        self.run_test("Learning step 0 ALMOST → stay", self.test_learning_step_0_almost)
        self.run_test("Learning step 0 GOT_IT → advance", self.test_learning_step_0_got_it)
        self.run_test("Learning step 1 MISSED → reset", self.test_learning_step_1_missed)
        self.run_test("Learning step 1 ALMOST → stay", self.test_learning_step_1_almost)
        self.run_test("Learning graduation", self.test_learning_graduation)
        
        # Review tests
        self.run_test("Review MISSED → lapse", self.test_review_missed_lapse)
        self.run_test("Review ALMOST → hard", self.test_review_almost_hard)
        self.run_test("Review GOT_IT → good", self.test_review_got_it_good)
        
        # Edge case tests
        self.run_test("Ease floor enforcement", self.test_ease_floor_enforcement)
        self.run_test("Interval minimum", self.test_interval_minimum)
        
        print("\n" + "=" * 50)
        
        # Summary
        passed = sum(1 for result in self.test_results if result[0] == 'PASS')
        failed = sum(1 for result in self.test_results if result[0] == 'FAIL')
        
        print(f"📊 Test Summary: {passed} passed, {failed} failed")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for status, name, error in self.test_results:
                if status == 'FAIL':
                    print(f"  - {name}: {error}")
        
        return passed, failed, self.test_results


def main():
    """Run the test suite."""
    tester = SchedulerTester()
    
    try:
        passed, failed, results = tester.run_all_tests()
        return failed == 0  # Return True if all tests passed
    finally:
        tester.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)