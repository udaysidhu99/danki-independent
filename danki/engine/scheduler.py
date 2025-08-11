# engine/scheduler.py

from enum import IntEnum
from typing import Optional

class Rating(IntEnum):
    MISSED = 0
    ALMOST = 1
    GOT_IT = 2

class Scheduler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # TODO: init DB connection

    def add_note(self, deck_id: str, front: str, back: str, meta: Optional[dict] = None) -> str:
        """Add a note to a deck. Returns the new note ID."""
        # TODO: implement
        return "note-id-placeholder"

    def build_session(self, deck_ids: list[str], now_ts: Optional[int] = None,
                      max_new: Optional[int] = None, max_rev: Optional[int] = None) -> list[dict]:
        """Return a list of cards for today’s session."""
        # TODO: implement
        return []

    def review(self, card_id: str, rating: Rating, answer_ms: int,
               now_ts: Optional[int] = None) -> None:
        """Record a review result."""
        # TODO: implement
        pass

    def suspend(self, card_id: str) -> None:
        """Suspend a card from appearing in reviews."""
        # TODO: implement
        pass

