# engine/db.py

from typing import Optional, Any

class Database:
    def __init__(self, path: str):
        self.path = path
        # TODO: connect to SQLite (or other)
        pass

    def create_tables(self) -> None:
        """Create necessary tables if they don’t exist."""
        # TODO: implement
        pass

    def add_card(self, deck_id: str, front: str, back: str, meta: Optional[dict] = None) -> str:
        """Insert a card and return its ID."""
        # TODO: implement
        return "card-id-placeholder"

    def get_cards_for_review(self, deck_ids: list[str], now_ts: int,
                             max_new: Optional[int], max_rev: Optional[int]) -> list[dict]:
        """Return cards due for review."""
        # TODO: implement
        return []

    def update_card_review(self, card_id: str, rating: Any, answer_ms: int, now_ts: int) -> None:
        """Update review stats for a card."""
        # TODO: implement
        pass

    def suspend_card(self, card_id: str) -> None:
        """Mark a card as suspended."""
        # TODO: implement
        pass
