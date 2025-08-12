#!/usr/bin/env python3
"""Debug how cards are converted to dictionaries."""

from danki.engine.db import Database
import time

def debug_card_conversion():
    """Debug the card conversion process."""
    db = Database("danki_data.sqlite")
    
    # Get cards directly from database
    now_ts = int(time.time())
    decks = db.list_decks()
    deck_ids = [deck['id'] for deck in decks]
    
    print("🔍 Raw database query result:")
    raw_cards = db.get_cards_for_review(deck_ids, now_ts)
    
    for i, card in enumerate(raw_cards):
        print(f"\nCard {i+1}:")
        print(f"  Type: {type(card)}")
        print(f"  Keys: {list(card.keys()) if hasattr(card, 'keys') else 'No keys method'}")
        
        if hasattr(card, 'keys'):
            for key in card.keys():
                print(f"    {key}: {card[key]}")
        else:
            # If it's a SQLite Row, try to access fields directly
            try:
                print(f"    id: {card['id']}")
                print(f"    template: {card['template']}")
                print(f"    front: {card['front']}")
                print(f"    back: {card['back']}")
            except Exception as e:
                print(f"    Error accessing fields: {e}")

if __name__ == "__main__":
    debug_card_conversion()