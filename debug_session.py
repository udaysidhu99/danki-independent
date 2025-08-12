#!/usr/bin/env python3
"""Debug the session building to see what card data is passed to review screen."""

from danki.engine.db import Database
from danki.engine.scheduler import Scheduler
import time

def debug_session():
    """Debug what the scheduler returns for review session."""
    db = Database("danki_data.sqlite")
    scheduler = Scheduler("danki_data.sqlite")
    
    # Get all deck IDs
    decks = db.list_decks()
    deck_ids = [deck['id'] for deck in decks]
    
    print(f"🔍 Building session for {len(deck_ids)} decks...")
    
    # Build session like the main app does
    cards = scheduler.build_session(deck_ids, max_new=10, max_rev=50)
    
    print(f"\n📋 Session contains {len(cards)} cards:")
    print("=" * 80)
    
    for i, card in enumerate(cards, 1):
        print(f"\n📇 Card {i} (passed to review screen):")
        
        # Show all available keys in the card dict
        print(f"  Keys: {list(card.keys())}")
        
        # Show key fields
        card_id = card.get('id') or card.get('card_id', 'MISSING')
        template = card.get('template', 'MISSING')
        front = card.get('front', 'MISSING')
        back = card.get('back', 'MISSING')
        state = card.get('state', 'MISSING')
        
        print(f"  Card ID: {card_id}")
        print(f"  Template: '{template}'")
        print(f"  Front: '{front}'")
        print(f"  Back: '{back}'")
        print(f"  State: {state}")
        
        # Test the review logic manually
        if template == 'back->front':
            question = back    # English
            answer = front     # German
            direction = "English → German"
        else:
            question = front   # German
            answer = back      # English  
            direction = "German → English"
            
        print(f"  Should Display: '{question}' → '{answer}' ({direction})")

if __name__ == "__main__":
    debug_session()