#!/usr/bin/env python3
"""Reset existing cards and test bidirectional card creation."""

from danki.engine.db import Database
import time

def reset_and_test():
    """Delete existing cards and test bidirectional functionality."""
    db = Database("danki_data.sqlite")
    
    print("🗑️  Deleting all existing cards and notes...")
    
    # Delete all cards and notes (CASCADE will handle related data)
    db.conn.execute("DELETE FROM cards")
    db.conn.execute("DELETE FROM notes")
    db.conn.execute("DELETE FROM daily_stats")
    db.conn.commit()
    
    print("✅ All existing data cleared!")
    
    # Create a test deck with bidirectional cards enabled
    deck_id = db.create_deck('Bidirectional Test', False, {
        "new_per_day": 10,
        "rev_per_day": 20,
        "steps_min": [10, 1440],
        "bidirectional_cards": True
    })
    
    print(f"📚 Created test deck: Bidirectional Test")
    
    # Add a test card
    print("\n➕ Adding test card: 'der Hund' ↔ 'the dog'")
    
    note_id = db.add_note(
        deck_id=deck_id,
        front="der Hund",
        back="the dog",
        meta={
            "artikel_d": "der",
            "plural_d": "die Hunde", 
            "word_type": "noun",
            "s1": "Der Hund bellt laut.",
            "s1e": "The dog barks loudly."
        }
    )
    
    # Check how many cards were created
    cards = db.conn.execute("SELECT * FROM cards WHERE note_id = ?", (note_id,)).fetchall()
    
    print(f"\n🔍 Cards created for note {note_id}:")
    for card in cards:
        template = card['template']
        state = card['state']
        print(f"  - Card ID: {card['id']}")
        print(f"    Template: {template}")
        print(f"    State: {state}")
        
        if template == 'front->back':
            print(f"    Direction: 'der Hund' → 'the dog' (German to English)")
        else:
            print(f"    Direction: 'the dog' → 'der Hund' (English to German)")
    
    print(f"\n✅ Successfully created {len(cards)} cards from 1 note!")
    
    # Check deck stats
    now_ts = int(time.time())
    stats = db.get_stats_today([deck_id], now_ts)
    print(f"\n📊 Deck stats: {stats}")
    
    print(f"\n🎯 Ready to test! Run 'python main.py' and review the cards.")
    print(f"   You should see both directions:")
    print(f"   1. German → English: 'der Hund' → 'the dog'") 
    print(f"   2. English → German: 'the dog' → 'der Hund'")

if __name__ == "__main__":
    reset_and_test()