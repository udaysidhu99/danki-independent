# engine/scheduler.py

import time
import math
import random
from enum import IntEnum
from typing import Optional
from .db import Database

class Rating(IntEnum):
    """Anki-compatible 4-button rating system."""
    AGAIN = 1   # Complete failure - reset/lapse
    HARD = 2    # Difficult recall - reduced interval
    GOOD = 3    # Successful recall - standard interval
    EASY = 4    # Effortless recall - bonus interval

    # Legacy compatibility
    MISSED = AGAIN
    ALMOST = HARD
    GOT_IT = GOOD

class Scheduler:
    """Enhanced SM-2+ scheduler matching Anki behavior.
    
    Implements Anki's proven enhancements:
    - 4-button rating system (Again/Hard/Good/Easy)
    - Interval fuzzing (±5% randomization)
    - Enhanced graduating intervals
    - Late review handling with partial credit
    - Proper lapse multiplier (0.5)
    - Easy bonus multiplier (1.3)
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = Database(db_path)

    def add_note(self, deck_id: str, front: str, back: str, meta: Optional[dict] = None) -> str:
        """Add a note to a deck. Returns the new note ID."""
        return self.db.add_note(deck_id, front, back, meta)

    def build_session(self, deck_ids: list[str], now_ts: Optional[int] = None,
                      max_new: Optional[int] = None, max_rev: Optional[int] = None) -> list[dict]:
        """Return a list of cards for today's session with daily limits."""
        if now_ts is None:
            now_ts = int(time.time())
            
        if not deck_ids:
            return []
            
        from ..utils.study_time import study_time
        study_date = study_time.get_study_date(now_ts)
        
        # Get all due cards
        cards = self.db.get_cards_for_review(deck_ids, now_ts)
        
        # Separate by state
        new_cards = [c for c in cards if c['state'] == 'new']
        learning_cards = [c for c in cards if c['state'] == 'learning']
        review_cards = [c for c in cards if c['state'] == 'review']
        
        # Apply daily limits per deck
        filtered_new_cards = []
        filtered_review_cards = []
        
        # Group cards by deck
        cards_by_deck = {}
        for card in new_cards + review_cards:
            deck_id = card.get('deck_id')
            if not deck_id:
                # Get deck_id from note if not directly available
                note_row = self.db.conn.execute("SELECT deck_id FROM notes WHERE id = ?", (card['note_id'],)).fetchone()
                deck_id = note_row['deck_id'] if note_row else None
                
            if deck_id:
                if deck_id not in cards_by_deck:
                    cards_by_deck[deck_id] = {'new': [], 'review': []}
                
                if card in new_cards:
                    cards_by_deck[deck_id]['new'].append(card)
                else:
                    cards_by_deck[deck_id]['review'].append(card)
        
        # Apply daily limits for each deck
        for deck_id, deck_cards in cards_by_deck.items():
            # Get deck preferences and daily stats
            prefs = self.db.get_deck_preferences(deck_id)
            daily_stats = self.db.get_daily_stats(deck_id, study_date)
            
            # Calculate remaining daily allowance
            new_per_day = prefs.get('new_per_day', 10)
            rev_per_day = prefs.get('rev_per_day', 100)
            
            new_remaining = max(0, new_per_day - daily_stats['new_studied'])
            rev_remaining = max(0, rev_per_day - daily_stats['rev_studied'])
            
            # Apply global max limits if provided
            if max_new is not None:
                new_remaining = min(new_remaining, max_new - len(filtered_new_cards))
            if max_rev is not None:
                rev_remaining = min(rev_remaining, max_rev - len(filtered_review_cards))
            
            # Add cards up to daily limits
            filtered_new_cards.extend(deck_cards['new'][:new_remaining])
            filtered_review_cards.extend(deck_cards['review'][:rev_remaining])
        
        # ANKI-STYLE LEARNING CARD MANAGEMENT
        # Include learning cards that will be due during the session (not just right now)
        # This ensures "Again" cards appear in the session even if due in 1 minute
        session_duration = 1800  # 30 minutes - typical session length
        due_learning = [c for c in learning_cards if c['due_ts'] <= now_ts + session_duration]
        future_learning = [c for c in learning_cards if c['due_ts'] > now_ts + session_duration]
        
        # Build session with proper Anki interleaving:
        # Learning cards are mixed in, not all at front
        session = self._build_anki_session(
            due_learning, filtered_new_cards, filtered_review_cards, future_learning
        )
        
        return session
    
    def _build_anki_session(self, learning_cards, new_cards, review_cards, future_learning):
        """Build session with proper Anki-style card interleaving.
        
        Anki's algorithm:
        - Learning cards appear every ~3-4 cards
        - New cards are limited and spread throughout
        - Review cards fill the gaps
        - Future learning cards added at end
        """
        session = []
        
        # Create pools
        learning_pool = learning_cards.copy()
        new_pool = new_cards.copy()
        review_pool = review_cards.copy()
        
        # Anki interleaving pattern:
        # Show 1-2 learning cards, then 2-3 other cards, repeat
        cards_since_learning = 0
        learning_interval = 3  # Show learning card every ~3 cards
        
        while learning_pool or new_pool or review_pool:
            # Add learning card if due and interval reached
            if learning_pool and cards_since_learning >= learning_interval:
                session.append(learning_pool.pop(0))
                cards_since_learning = 0
            
            # Add new card (limited distribution)
            elif new_pool and len(session) % 4 == 1:  # Every 4th position
                session.append(new_pool.pop(0))
                cards_since_learning += 1
                
            # Add review card (fills most slots)
            elif review_pool:
                session.append(review_pool.pop(0))
                cards_since_learning += 1
                
            # Fallback: add any remaining card
            elif new_pool:
                session.append(new_pool.pop(0))
                cards_since_learning += 1
            elif learning_pool:
                session.append(learning_pool.pop(0))
                cards_since_learning = 0
            else:
                break
        
        # Add future learning cards at end
        session.extend(future_learning)
        
        return session

    def review(self, card_id: str, rating: Rating, answer_ms: int,
               now_ts: Optional[int] = None) -> None:
        """Record a review result and update card scheduling.
        
        Args:
            card_id: Card being reviewed
            rating: Rating.AGAIN/HARD/GOOD/EASY (Anki 4-button system)
            answer_ms: Time taken to answer in milliseconds
            now_ts: Timestamp of review (defaults to now)
        """
        if now_ts is None:
            now_ts = int(time.time())
            
        # Get current card state
        card = self._get_card(card_id)
        if not card:
            return
            
        prev_state = card['state']
        prev_interval = card['interval_days']
        
        # Calculate new card state based on SM-2
        new_state, new_due_ts, new_interval, new_ease, new_lapses, new_step_index = \
            self._calculate_next_state(card, rating, now_ts)
        
        # Update card in database
        self.db.update_card_after_review(
            card_id, new_state, new_due_ts, new_interval, 
            new_ease, new_lapses, new_step_index
        )
        
        # Log the review
        self.db.log_review(
            card_id, rating, answer_ms, prev_state, prev_interval, new_interval
        )
        
        # Update daily stats for the deck
        from ..utils.study_time import study_time
        study_date = study_time.get_study_date(now_ts)
        
        # Get deck_id for this card
        note_row = self.db.conn.execute("SELECT deck_id FROM notes WHERE id = ?", (card['note_id'],)).fetchone()
        if note_row:
            deck_id = note_row['deck_id']
            
            # Determine if this counts as a new card or review for daily stats
            new_count = 0
            rev_count = 0
            
            if prev_state == 'new':
                # This was a new card being studied for first time
                new_count = 1
            elif prev_state in ['learning', 'review']:
                # This was a review/re-review
                rev_count = 1
                
            # Increment daily stats
            if new_count > 0 or rev_count > 0:
                self.db.increment_daily_stats(deck_id, study_date, new_count, rev_count)

    def _get_card(self, card_id: str) -> Optional[dict]:
        """Get card by ID."""
        cards = self.db.conn.execute(
            "SELECT * FROM cards WHERE id = ?", (card_id,)
        ).fetchone()
        
        if cards:
            return dict(cards)
        return None

    def _calculate_next_state(self, card: dict, rating: Rating, now_ts: int) -> tuple:
        """Calculate next card state using SM-2 algorithm."""
        current_state = card['state']
        current_ease = card['ease']
        current_interval = card['interval_days']
        current_lapses = card['lapses']
        current_step = card['step_index']
        
        # SM-2+ Configuration (Anki defaults)
        LEARNING_STEPS = [1, 10]         # Learning steps in minutes
        GRADUATING_INTERVAL_GOOD = 1      # Days when graduating with Good
        GRADUATING_INTERVAL_EASY = 4      # Days when graduating with Easy
        STARTING_EASE = 2.5               # Starting ease factor (250%)
        MINIMUM_EASE = 1.3               # Minimum ease factor (130%)
        HARD_MULTIPLIER = 1.2            # Hard answer multiplier
        EASY_MULTIPLIER = 1.3            # Easy answer multiplier
        LAPSE_MULTIPLIER = 0.5           # Interval reduction on lapse
        
        if current_state == 'new':
            # New card → Learning state transition
            new_state = 'learning'
            new_lapses = current_lapses
            new_ease = STARTING_EASE if current_ease == 0 else current_ease
            new_interval = 0
            
            if rating == Rating.AGAIN:
                # Reset to first step
                new_step_index = 0
                new_due_ts = now_ts + (LEARNING_STEPS[0] * 60)
            elif rating == Rating.HARD:
                # Start at first step
                new_step_index = 0
                new_due_ts = now_ts + (LEARNING_STEPS[0] * 60)
            elif rating == Rating.GOOD:
                # Start at first step (normal progression)
                new_step_index = 0
                new_due_ts = now_ts + (LEARNING_STEPS[0] * 60)
            else:  # EASY
                # Graduate immediately with easy interval
                new_state = 'review'
                new_step_index = 0
                new_interval = self._apply_fuzz(GRADUATING_INTERVAL_EASY)
                new_due_ts = now_ts + int(new_interval * 24 * 3600)
                
        elif current_state == 'learning':
            new_ease = current_ease
            new_interval = 0
            
            if rating == Rating.AGAIN:
                # Reset to first learning step
                new_state = 'learning'
                new_step_index = 0
                new_due_ts = now_ts + (LEARNING_STEPS[0] * 60)
                new_lapses = current_lapses + 1
            elif rating == Rating.HARD:
                # Repeat current step (minimum 10 minutes)
                new_state = 'learning'
                new_step_index = current_step
                step_minutes = max(10, LEARNING_STEPS[min(current_step, len(LEARNING_STEPS) - 1)])
                new_due_ts = now_ts + (step_minutes * 60)
                new_lapses = current_lapses
            elif rating == Rating.GOOD:
                if current_step >= len(LEARNING_STEPS) - 1:
                    # Graduate to review with standard interval
                    new_state = 'review'
                    new_step_index = 0
                    new_interval = self._apply_fuzz(GRADUATING_INTERVAL_GOOD)
                    new_due_ts = now_ts + int(new_interval * 24 * 3600)
                    new_lapses = current_lapses
                else:
                    # Advance to next learning step
                    new_state = 'learning'
                    new_step_index = current_step + 1
                    step_minutes = LEARNING_STEPS[new_step_index]
                    new_due_ts = now_ts + (step_minutes * 60)
                    new_lapses = current_lapses
            else:  # EASY
                # Graduate to review with bonus interval
                new_state = 'review'
                new_step_index = 0
                new_interval = self._apply_fuzz(GRADUATING_INTERVAL_EASY)
                new_due_ts = now_ts + int(new_interval * 24 * 3600)
                new_lapses = current_lapses
                    
        elif current_state == 'review':
            new_state = 'review'
            new_step_index = 0
            
            # Calculate days late for partial credit
            days_late = max(0, (now_ts - card['due_ts']) / (24 * 3600))
            
            if rating == Rating.AGAIN:
                # Lapse: transition to relearning
                new_state = 'learning'  # Relearning uses learning steps
                new_step_index = 0
                new_due_ts = now_ts + (LEARNING_STEPS[0] * 60)
                new_interval = max(1, current_interval * LAPSE_MULTIPLIER)  # Reduce interval
                new_ease = max(MINIMUM_EASE, current_ease - 0.2)  # Anki lapse penalty
                new_lapses = current_lapses + 1
            else:
                # Stay in review state
                new_lapses = current_lapses
                
                if rating == Rating.HARD:
                    # Hard: reduce ease and apply hard multiplier
                    new_ease = max(MINIMUM_EASE, current_ease - 0.15)
                    new_interval = max(1.0, current_interval * HARD_MULTIPLIER)
                elif rating == Rating.GOOD:
                    # Good: standard SM-2 with late review credit
                    new_ease = current_ease  # No ease change
                    new_interval = (current_interval + days_late/2) * new_ease
                else:  # EASY
                    # Easy: bonus ease and multiplier with late credit
                    new_ease = current_ease + 0.15
                    new_interval = (current_interval + days_late) * new_ease * EASY_MULTIPLIER
                
                # Apply fuzzing and set due date
                new_interval = self._apply_fuzz(new_interval)
                new_due_ts = now_ts + int(new_interval * 24 * 3600)
        else:
            # Suspended or unknown state - no changes
            return (current_state, card['due_ts'], current_interval, 
                   current_ease, current_lapses, current_step)
        
        return (new_state, new_due_ts, new_interval, new_ease, new_lapses, new_step_index)
    
    def _apply_fuzz(self, interval: float) -> float:
        """Apply Anki's interval fuzzing (±5% randomization).
        
        Prevents cards from clustering on the same review day.
        """
        if interval < 1:
            return interval
        
        # Apply ±5% fuzzing
        fuzz_factor = 0.95 + (random.random() * 0.1)  # 0.95 to 1.05
        return max(1.0, interval * fuzz_factor)

    def suspend(self, card_id: str) -> None:
        """Suspend a card from appearing in reviews."""
        self.db.suspend_card(card_id)

    def get_stats_today(self, deck_ids: list[str], now_ts: Optional[int] = None) -> dict:
        """Get today's review statistics."""
        if now_ts is None:
            now_ts = int(time.time())
        return self.db.get_stats_today(deck_ids, now_ts)

