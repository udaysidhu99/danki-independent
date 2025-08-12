# engine/scheduler.py

import time
import math
from enum import IntEnum
from typing import Optional
from .db import Database

class Rating(IntEnum):
    MISSED = 0
    ALMOST = 1
    GOT_IT = 2

class Scheduler:
    """SM-2 based spaced repetition scheduler."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = Database(db_path)

    def add_note(self, deck_id: str, front: str, back: str, meta: Optional[dict] = None) -> str:
        """Add a note to a deck. Returns the new note ID."""
        return self.db.add_note(deck_id, front, back, meta)

    def build_session(self, deck_ids: list[str], now_ts: Optional[int] = None,
                      max_new: Optional[int] = None, max_rev: Optional[int] = None) -> list[dict]:
        """Return a list of cards for today's session."""
        if now_ts is None:
            now_ts = int(time.time())
            
        if not deck_ids:
            return []
            
        # Get all due cards
        cards = self.db.get_cards_for_review(deck_ids, now_ts)
        
        # Separate by state
        new_cards = [c for c in cards if c['state'] == 'new']
        learning_cards = [c for c in cards if c['state'] == 'learning']
        review_cards = [c for c in cards if c['state'] == 'review']
        
        # Apply limits
        if max_new is not None:
            new_cards = new_cards[:max_new]
        if max_rev is not None:
            review_cards = review_cards[:max_rev]
            
        # Order: learning first (most urgent), then new, then review
        session = learning_cards + new_cards + review_cards
        
        return session

    def review(self, card_id: str, rating: Rating, answer_ms: int,
               now_ts: Optional[int] = None) -> None:
        """Record a review result and update card scheduling."""
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
        
        # Learning steps in minutes: [10, 1440] (10 min, 1 day)
        LEARNING_STEPS = [10, 1440]
        
        if current_state == 'new':
            # New card transitions
            if rating == Rating.MISSED:
                # Stay in learning, reset to first step
                new_state = 'learning'
                new_step_index = 0
                new_due_ts = now_ts + (LEARNING_STEPS[0] * 60)  # 10 minutes
                new_interval = 0
                new_ease = current_ease
                new_lapses = current_lapses
            else:
                # Move to learning
                new_state = 'learning'
                new_step_index = 0 if rating == Rating.ALMOST else 1
                step_minutes = LEARNING_STEPS[new_step_index]
                new_due_ts = now_ts + (step_minutes * 60)
                new_interval = 0
                new_ease = current_ease
                new_lapses = current_lapses
                
        elif current_state == 'learning':
            if rating == Rating.MISSED:
                # Reset to first learning step
                new_state = 'learning'
                new_step_index = 0
                new_due_ts = now_ts + (LEARNING_STEPS[0] * 60)
                new_interval = 0
                new_ease = current_ease
                new_lapses = current_lapses + 1
            elif rating == Rating.ALMOST:
                # Stay at current step
                new_state = 'learning'
                new_step_index = current_step
                step_minutes = LEARNING_STEPS[min(current_step, len(LEARNING_STEPS) - 1)]
                new_due_ts = now_ts + (step_minutes * 60)
                new_interval = 0
                new_ease = current_ease
                new_lapses = current_lapses
            else:  # GOT_IT
                if current_step >= len(LEARNING_STEPS) - 1:
                    # Graduate to review
                    new_state = 'review'
                    new_step_index = 0
                    new_interval = 1.0  # Start with 1 day
                    new_due_ts = now_ts + int(new_interval * 24 * 3600)
                    new_ease = current_ease
                    new_lapses = current_lapses
                else:
                    # Advance to next learning step
                    new_state = 'learning'
                    new_step_index = current_step + 1
                    step_minutes = LEARNING_STEPS[new_step_index]
                    new_due_ts = now_ts + (step_minutes * 60)
                    new_interval = 0
                    new_ease = current_ease
                    new_lapses = current_lapses
                    
        elif current_state == 'review':
            if rating == Rating.MISSED:
                # Lapse: back to learning
                new_state = 'learning'
                new_step_index = 0
                new_due_ts = now_ts + (LEARNING_STEPS[0] * 60)
                new_interval = 0
                new_ease = max(1.3, current_ease - 0.8)  # Reduce ease, floor at 1.3
                new_lapses = current_lapses + 1
            else:
                # Stay in review, update interval and ease
                new_state = 'review'
                new_step_index = 0
                new_lapses = current_lapses
                
                if rating == Rating.ALMOST:
                    # Hard: reduce ease, multiply interval by 1.2
                    new_ease = max(1.3, current_ease - 0.15)
                    new_interval = max(1.0, current_interval * 1.2)
                else:  # GOT_IT
                    # Good: keep ease, multiply by ease factor
                    new_ease = current_ease
                    new_interval = current_interval * new_ease
                    
                new_due_ts = now_ts + int(new_interval * 24 * 3600)
        else:
            # Suspended or unknown state - no changes
            return (current_state, card['due_ts'], current_interval, 
                   current_ease, current_lapses, current_step)
        
        return (new_state, new_due_ts, new_interval, new_ease, new_lapses, new_step_index)

    def suspend(self, card_id: str) -> None:
        """Suspend a card from appearing in reviews."""
        self.db.suspend_card(card_id)

    def get_stats_today(self, deck_ids: list[str], now_ts: Optional[int] = None) -> dict:
        """Get today's review statistics."""
        if now_ts is None:
            now_ts = int(time.time())
        return self.db.get_stats_today(deck_ids, now_ts)

