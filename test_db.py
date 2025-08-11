#!/usr/bin/env python3
"""Test script for database functionality."""

from danki.engine.db import Database
import os

def main():
    # Test database creation and operations
    db_path = "test_danki.sqlite"
    
    # Clean up any existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    print("Testing Danki database...")
    
    # Initialize database
    db = Database(db_path)
    print("✓ Database created with schema")
    
    # Create a test deck
    deck_id = db.create_deck("Test German A1", is_builtin=False)
    print(f"✓ Created deck: {deck_id}")
    
    # Add some notes
    note1 = db.add_note(deck_id, "der Hund", "the dog", {"article": "der", "tags": ["A1"]})
    note2 = db.add_note(deck_id, "die Katze", "the cat", {"article": "die", "tags": ["A1"]})
    print(f"✓ Added notes: {note1}, {note2}")
    
    # List decks
    decks = db.list_decks()
    print(f"✓ Found {len(decks)} decks:")
    for deck in decks:
        print(f"  - {deck['name']} (builtin: {deck['is_builtin']})")
    
    # Get cards for review
    import time
    now = int(time.time())
    cards = db.get_cards_for_review([deck_id], now)
    print(f"✓ Found {len(cards)} cards for review:")
    for card in cards:
        print(f"  - {card['front']} -> {card['back']} (state: {card['state']})")
    
    # Get stats
    stats = db.get_stats_today([deck_id], now)
    print(f"✓ Today's stats: {stats}")
    
    # Load from JSONL
    cards_from_jsonl = db.load_deck_from_jsonl("danki/data/decks/a1.sample.jsonl")
    print(f"✓ Loaded {len(cards_from_jsonl)} cards from JSONL")
    
    db.close()
    print("✓ Database closed")
    
    # Clean up
    os.remove(db_path)
    print("✓ Test database removed")
    
    print("\nAll database tests passed! 🎉")

if __name__ == "__main__":
    main()