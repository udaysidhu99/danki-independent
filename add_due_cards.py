#!/usr/bin/env python3
"""Add new cards that are immediately due for testing bidirectional display."""

from danki.engine.db import Database
import time

def add_due_cards():
    """Add new cards that are due right now."""
    db = Database("danki_data.sqlite")
    
    # Get the bidirectional test deck
    decks = db.list_decks()
    test_deck = None
    for deck in decks:
        if deck['name'] == 'Bidirectional Test':
            test_deck = deck
            break
    
    if not test_deck:
        print("❌ Could not find 'Bidirectional Test' deck")
        return
        
    deck_id = test_deck['id']
    
    print(f"➕ Adding new test cards to '{test_deck['name']}'...")
    
    # Add a simple test word
    note_id = db.add_note(
        deck_id=deck_id,
        front="das Buch",
        back="the book",
        meta={
            "artikel_d": "das",
            "plural_d": "die Bücher",
            "word_type": "noun",
            "s1": "Das Buch ist interessant.",
            "s1e": "The book is interesting."
        }
    )
    
    print(f"✅ Added note: 'das Buch' ↔ 'the book'")
    
    # Check how many cards were created
    cards = db.conn.execute("SELECT * FROM cards WHERE note_id = ?", (note_id,)).fetchall()
    
    print(f"\n🔍 Cards created:")
    for card in cards:
        print(f"  - Template: {card['template']}, State: {card['state']}, Due: {card['due_ts']}")
        
    # Verify they are due now
    now_ts = int(time.time())
    due_cards = db.get_cards_for_review([deck_id], now_ts)
    
    print(f"\n📋 Due cards: {len(due_cards)} total")
    for i, card in enumerate(due_cards, 1):
        print(f"  Card {i}: Template '{card['template']}' - '{card['front']}' / '{card['back']}'")

if __name__ == "__main__":
    add_due_cards()