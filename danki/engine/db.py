"""Database layer for Danki flashcard application."""

import sqlite3
import json
import time
import uuid
from typing import Optional, Any, Dict, List
from pathlib import Path


class Database:
    """SQLite database manager for Danki."""

    def __init__(self, path: str):
        """Initialize database connection.
        
        Args:
            path: Path to SQLite database file
        """
        self.path = path
        self._ensure_path_exists()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._setup_database()

    def _ensure_path_exists(self) -> None:
        """Ensure the database directory exists."""
        db_path = Path(self.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    def _setup_database(self) -> None:
        """Set up database with WAL mode and create tables."""
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.create_tables()

    def create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS decks (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            is_builtin INTEGER NOT NULL DEFAULT 0,
            prefs JSON NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            deck_id TEXT NOT NULL,
            front TEXT NOT NULL,
            back TEXT NOT NULL,
            meta JSON,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            note_id TEXT NOT NULL,
            template TEXT NOT NULL,
            state TEXT NOT NULL,
            due_ts INTEGER NOT NULL,
            interval_days REAL NOT NULL DEFAULT 0,
            ease REAL NOT NULL DEFAULT 2.5,
            lapses INTEGER NOT NULL DEFAULT 0,
            step_index INTEGER NOT NULL DEFAULT 0,
            last_review_ts INTEGER,
            UNIQUE(note_id, template),
            FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS review_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT NOT NULL,
            ts INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            answer_ms INTEGER NOT NULL,
            prev_state TEXT,
            prev_interval REAL,
            next_interval REAL,
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id TEXT NOT NULL,
            study_date TEXT NOT NULL,  -- YYYY-MM-DD format
            new_studied INTEGER NOT NULL DEFAULT 0,
            rev_studied INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            UNIQUE(deck_id, study_date),
            FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_cards_due ON cards(state, due_ts);
        CREATE INDEX IF NOT EXISTS idx_daily_stats ON daily_stats(deck_id, study_date);
        """
        
        self.conn.executescript(schema)
        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def create_deck(self, name: str, is_builtin: bool = False, 
                   prefs: Optional[Dict] = None) -> str:
        """Create a new deck.
        
        Args:
            name: Deck name (must be unique)
            is_builtin: Whether this is a built-in deck
            prefs: Deck preferences (defaults to standard settings)
            
        Returns:
            Deck ID
        """
        if prefs is None:
            prefs = {
                "new_per_day": 10,
                "rev_per_day": 100,
                "steps_min": [1, 10],  # 1 min, 10 min - Anki default for immediate re-learning
                "bidirectional_cards": True  # Enable bidirectional cards by default
            }
        
        deck_id = str(uuid.uuid4())
        
        self.conn.execute(
            "INSERT INTO decks (id, name, is_builtin, prefs) VALUES (?, ?, ?, ?)",
            (deck_id, name, int(is_builtin), json.dumps(prefs))
        )
        self.conn.commit()
        return deck_id

    def get_deck(self, deck_id: str) -> Optional[Dict]:
        """Get deck by ID."""
        row = self.conn.execute(
            "SELECT * FROM decks WHERE id = ?", (deck_id,)
        ).fetchone()
        
        if row:
            return {
                "id": row["id"],
                "name": row["name"],
                "is_builtin": bool(row["is_builtin"]),
                "prefs": json.loads(row["prefs"])
            }
        return None

    def list_decks(self) -> List[Dict]:
        """List all decks."""
        rows = self.conn.execute(
            "SELECT * FROM decks ORDER BY is_builtin DESC, name"
        ).fetchall()
        
        return [{
            "id": row["id"],
            "name": row["name"], 
            "is_builtin": bool(row["is_builtin"]),
            "prefs": json.loads(row["prefs"])
        } for row in rows]

    def add_note(self, deck_id: str, front: str, back: str, 
                meta: Optional[Dict] = None) -> str:
        """Add a note and create associated card.
        
        Args:
            deck_id: Target deck ID
            front: Front text
            back: Back text
            meta: Optional metadata
            
        Returns:
            Note ID
        """
        note_id = str(uuid.uuid4())
        now_ts = int(time.time())
        
        # Insert note
        self.conn.execute(
            "INSERT INTO notes (id, deck_id, front, back, meta, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (note_id, deck_id, front, back, json.dumps(meta) if meta else None, now_ts)
        )
        
        # Get deck preferences to check if bidirectional cards are enabled
        prefs = self.get_deck_preferences(deck_id)
        bidirectional = prefs.get('bidirectional_cards', True)  # Default to True
        
        # Create card(s) for the note
        # Always create front->back card
        card_id_1 = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO cards (id, note_id, template, state, due_ts) VALUES (?, ?, ?, ?, ?)",
            (card_id_1, note_id, "front->back", "new", now_ts)
        )
        
        # Create back->front card if bidirectional is enabled
        if bidirectional:
            card_id_2 = str(uuid.uuid4())
            self.conn.execute(
                "INSERT INTO cards (id, note_id, template, state, due_ts) VALUES (?, ?, ?, ?, ?)",
                (card_id_2, note_id, "back->front", "new", now_ts)
            )
        
        self.conn.commit()
        return note_id

    def get_learning_cards(self, deck_ids: List[str], now_ts: int) -> List[Dict]:
        """Get learning cards due now or within session timeframe (Anki Phase 1)."""
        if not deck_ids:
            return []
            
        deck_placeholders = ",".join("?" for _ in deck_ids)
        session_duration = 1800  # 30 minutes - include cards due during session
        
        query = f"""
        SELECT c.*, n.front, n.back, n.meta, d.name as deck_name
        FROM cards c
        JOIN notes n ON c.note_id = n.id  
        JOIN decks d ON n.deck_id = d.id
        WHERE n.deck_id IN ({deck_placeholders})
        AND c.state = 'learning'
        AND c.due_ts <= ? + {session_duration}
        ORDER BY c.due_ts
        """
        
        rows = self.conn.execute(query, deck_ids + [now_ts]).fetchall()
        return self._rows_to_card_dicts(rows)
    
    def get_review_cards(self, deck_ids: List[str], now_ts: int, limit: Optional[int] = None) -> List[Dict]:
        """Get review cards due today (Anki Phase 2)."""
        if not deck_ids:
            return []
            
        deck_placeholders = ",".join("?" for _ in deck_ids)
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
        SELECT c.*, n.front, n.back, n.meta, d.name as deck_name
        FROM cards c
        JOIN notes n ON c.note_id = n.id  
        JOIN decks d ON n.deck_id = d.id
        WHERE n.deck_id IN ({deck_placeholders})
        AND c.state = 'review'
        AND c.due_ts <= ?
        ORDER BY c.due_ts
        {limit_clause}
        """
        
        rows = self.conn.execute(query, deck_ids + [now_ts]).fetchall()
        return self._rows_to_card_dicts(rows)
    
    def get_new_cards(self, deck_ids: List[str], limit: Optional[int] = None) -> List[Dict]:
        """Get new cards up to daily limit (Anki Phase 3)."""
        if not deck_ids:
            return []
            
        deck_placeholders = ",".join("?" for _ in deck_ids)
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
        SELECT c.*, n.front, n.back, n.meta, d.name as deck_name
        FROM cards c
        JOIN notes n ON c.note_id = n.id  
        JOIN decks d ON n.deck_id = d.id
        WHERE n.deck_id IN ({deck_placeholders})
        AND c.state = 'new'
        ORDER BY c.id  -- Order added for consistent selection
        {limit_clause}
        """
        
        rows = self.conn.execute(query, deck_ids).fetchall()
        return self._rows_to_card_dicts(rows)
    
    def _rows_to_card_dicts(self, rows) -> List[Dict]:
        """Convert database rows to card dictionaries."""
        return [{
            "card_id": row["id"],
            "note_id": row["note_id"],
            "template": row["template"],
            "front": row["front"],
            "back": row["back"],
            "meta": json.loads(row["meta"]) if row["meta"] else None,
            "state": row["state"],
            "due_ts": row["due_ts"],
            "interval_days": row["interval_days"],
            "ease": row["ease"],
            "lapses": row["lapses"],
            "step_index": row["step_index"],
            "deck_name": row["deck_name"]
        } for row in rows]

    def get_cards_for_review(self, deck_ids: List[str], now_ts: int,
                           max_new: Optional[int] = None, 
                           max_rev: Optional[int] = None) -> List[Dict]:
        """Return cards due for review."""
        if not deck_ids:
            return []
            
        deck_placeholders = ",".join("?" for _ in deck_ids)
        
        # Include cards that are due now OR learning cards due within session timeframe
        session_duration = 1800  # 30 minutes
        query = f"""
        SELECT c.*, n.front, n.back, n.meta, d.name as deck_name
        FROM cards c
        JOIN notes n ON c.note_id = n.id  
        JOIN decks d ON n.deck_id = d.id
        WHERE n.deck_id IN ({deck_placeholders})
        AND (
            c.due_ts <= ? OR 
            (c.state = 'learning' AND c.due_ts <= ? + {session_duration})
        )
        AND c.state != 'suspended'
        ORDER BY c.due_ts
        """
        
        rows = self.conn.execute(query, deck_ids + [now_ts, now_ts]).fetchall()
        
        return [{
            "card_id": row["id"],
            "note_id": row["note_id"],
            "template": row["template"],  # Add missing template field!
            "front": row["front"],
            "back": row["back"],
            "meta": json.loads(row["meta"]) if row["meta"] else None,
            "state": row["state"],
            "due_ts": row["due_ts"],
            "interval_days": row["interval_days"],
            "ease": row["ease"],
            "lapses": row["lapses"],
            "step_index": row["step_index"],
            "deck_name": row["deck_name"]
        } for row in rows]

    def update_card_after_review(self, card_id: str, new_state: str, 
                               new_due_ts: int, new_interval: float,
                               new_ease: float, new_lapses: int,
                               new_step_index: int) -> None:
        """Update card state after review."""
        now_ts = int(time.time())
        
        self.conn.execute("""
            UPDATE cards 
            SET state = ?, due_ts = ?, interval_days = ?, ease = ?, 
                lapses = ?, step_index = ?, last_review_ts = ?
            WHERE id = ?
        """, (new_state, new_due_ts, new_interval, new_ease, 
              new_lapses, new_step_index, now_ts, card_id))
        
        self.conn.commit()

    def log_review(self, card_id: str, rating: int, answer_ms: int,
                  prev_state: str, prev_interval: float, 
                  next_interval: float) -> None:
        """Log a review in the review log."""
        now_ts = int(time.time())
        
        self.conn.execute("""
            INSERT INTO review_log 
            (card_id, ts, rating, answer_ms, prev_state, prev_interval, next_interval)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (card_id, now_ts, rating, answer_ms, prev_state, prev_interval, next_interval))
        
        self.conn.commit()

    def suspend_card(self, card_id: str) -> None:
        """Mark a card as suspended."""
        self.conn.execute(
            "UPDATE cards SET state = 'suspended' WHERE id = ?",
            (card_id,)
        )
        self.conn.commit()

    def get_stats_today(self, deck_ids: List[str], now_ts: int) -> Dict:
        """Get today's review statistics."""
        if not deck_ids:
            return {"new": 0, "learning": 0, "review": 0, "total": 0}
            
        deck_placeholders = ",".join("?" for _ in deck_ids)
        
        # Count cards due today by state
        query = f"""
        SELECT c.state, COUNT(*) as count
        FROM cards c
        JOIN notes n ON c.note_id = n.id
        WHERE n.deck_id IN ({deck_placeholders})
        AND c.due_ts <= ?
        AND c.state != 'suspended'
        GROUP BY c.state
        """
        
        rows = self.conn.execute(query, deck_ids + [now_ts]).fetchall()
        
        stats = {"new": 0, "learning": 0, "review": 0}
        for row in rows:
            stats[row["state"]] = row["count"]
            
        stats["total"] = sum(stats.values())
        return stats

    def load_deck_from_jsonl(self, deck_path: str) -> list[dict]:
        """
        Load a deck from a JSONL file and return a list of card dicts.

        Each line should be a JSON object with at least 'front' and 'back'.
        Lines that fail to parse are skipped with a console message.
        """
        from pathlib import Path
        import json

        p = Path(deck_path)
        if not p.exists():
            raise FileNotFoundError(f"Deck file not found: {deck_path}")

        cards: list[dict] = []
        with p.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                    if isinstance(obj, dict) and "front" in obj and "back" in obj:
                        cards.append(obj)
                except json.JSONDecodeError as e:
                    print(f"[deck] skipping invalid JSON line: {e}: {raw[:80]}")
        return cards

    def get_daily_stats(self, deck_id: str, study_date: str) -> Dict:
        """Get daily stats for a deck on a specific study date."""
        row = self.conn.execute(
            "SELECT new_studied, rev_studied FROM daily_stats WHERE deck_id = ? AND study_date = ?",
            (deck_id, study_date)
        ).fetchone()
        
        if row:
            return {"new_studied": row["new_studied"], "rev_studied": row["rev_studied"]}
        else:
            return {"new_studied": 0, "rev_studied": 0}

    def increment_daily_stats(self, deck_id: str, study_date: str, new_count: int = 0, rev_count: int = 0) -> None:
        """Increment daily stats for a deck. Creates entry if it doesn't exist."""
        self.conn.execute(
            """INSERT OR REPLACE INTO daily_stats (deck_id, study_date, new_studied, rev_studied, created_at)
               VALUES (?, ?, 
                       COALESCE((SELECT new_studied FROM daily_stats WHERE deck_id = ? AND study_date = ?), 0) + ?,
                       COALESCE((SELECT rev_studied FROM daily_stats WHERE deck_id = ? AND study_date = ?), 0) + ?,
                       ?)""",
            (deck_id, study_date, deck_id, study_date, new_count, deck_id, study_date, rev_count, int(time.time()))
        )
        self.conn.commit()

    def get_deck_preferences(self, deck_id: str) -> Dict:
        """Get deck preferences."""
        row = self.conn.execute("SELECT prefs FROM decks WHERE id = ?", (deck_id,)).fetchone()
        if row:
            return json.loads(row["prefs"])
        else:
            # Return default preferences
            return {
                "new_per_day": 20,  # Anki default
                "rev_per_day": 200,  # Anki default (10x new cards)
                "steps_min": [1, 10],
                "bidirectional_cards": True
            }

    def update_deck_preferences(self, deck_id: str, preferences: Dict) -> None:
        """Update deck preferences."""
        # Get current preferences and merge with updates
        current_prefs = self.get_deck_preferences(deck_id)
        current_prefs.update(preferences)
        
        # Auto-calculate review limit based on new cards (Anki behavior)
        if "new_per_day" in preferences:
            current_prefs["rev_per_day"] = current_prefs["new_per_day"] * 10
        
        # Update database
        self.conn.execute(
            "UPDATE decks SET prefs = ? WHERE id = ?", 
            (json.dumps(current_prefs), deck_id)
        )
        self.conn.commit()
