#!/usr/bin/env python3
"""Debug script to check what data is actually in the cards."""

from danki.engine.db import Database
import time

def debug_cards():
    """Debug the card data to see what's actually stored."""
    db = Database("danki_data.sqlite")
    
    # Get all cards
    cards = db.conn.execute("""
        SELECT c.*, n.front, n.back, n.meta, d.name as deck_name
        FROM cards c
        JOIN notes n ON c.note_id = n.id  
        JOIN decks d ON n.deck_id = d.id
        ORDER BY c.due_ts
    """).fetchall()
    
    print(f"🔍 Found {len(cards)} cards in database:")
    print("=" * 80)
    
    for i, card in enumerate(cards, 1):
        print(f"\n📇 Card {i}:")
        print(f"  ID: {card['id']}")
        print(f"  Template: {card['template']}")
        print(f"  Note Front: '{card['front']}'")
        print(f"  Note Back: '{card['back']}'")
        print(f"  State: {card['state']}")
        
        # Simulate what the review screen should show
        template = card['template']
        if template == 'back->front':
            question = card['back']  # English
            answer = card['front']   # German
            direction = "English → German"
        else:
            question = card['front'] # German  
            answer = card['back']    # English
            direction = "German → English"
            
        print(f"  Should Show: '{question}' → '{answer}' ({direction})")
    
    print("\n" + "=" * 80)
    print("🎯 Expected behavior:")
    print("  Card 1: 'der Hund' → 'the dog' (German → English)")
    print("  Card 2: 'the dog' → 'der Hund' (English → German)")

if __name__ == "__main__":
    debug_cards()