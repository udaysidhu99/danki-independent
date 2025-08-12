#!/usr/bin/env python3
"""Test the 'Again' button behavior to ensure cards reappear quickly."""

from danki.engine.db import Database
from danki.engine.scheduler import Scheduler, Rating
import time

def test_again_behavior():
    """Test that Again button makes cards reappear quickly."""
    db = Database("danki_data.sqlite")
    scheduler = Scheduler("danki_data.sqlite")
    
    # Get a deck with cards
    decks = db.list_decks()
    if not decks:
        print("❌ No decks found for testing")
        return
        
    deck_id = decks[0]['id']  # Use first available deck
    print(f"🧪 Testing with deck: {decks[0]['name']}")
    
    # Get due cards
    now_ts = int(time.time())
    cards = scheduler.build_session([deck_id], now_ts)
    
    if not cards:
        print("❌ No cards due for testing")
        return
        
    test_card = cards[0]
    card_id = test_card['card_id']
    
    print(f"\n📋 Testing card: '{test_card['front']}' → '{test_card['back']}'")
    print(f"   Current state: {test_card['state']}")
    print(f"   Current due: {test_card['due_ts']} ({time.ctime(test_card['due_ts'])})")
    
    # Hit "Again" (MISSED rating)
    print(f"\n❌ Rating card as MISSED (Again)...")
    scheduler.review(card_id, Rating.MISSED, 5000)  # 5 second answer time
    
    # Check new due time
    updated_card = scheduler._get_card(card_id)
    new_due_ts = updated_card['due_ts']
    time_diff = new_due_ts - now_ts
    
    print(f"   New state: {updated_card['state']}")
    print(f"   New due: {new_due_ts} ({time.ctime(new_due_ts)})")
    print(f"   Due in: {time_diff} seconds ({time_diff/60:.1f} minutes)")
    
    # Check if it shows up in session soon
    print(f"\n🔄 Checking if card appears in session now...")
    immediate_session = scheduler.build_session([deck_id], now_ts)
    card_in_session = any(c['card_id'] == card_id for c in immediate_session)
    print(f"   In current session: {'✅ YES' if card_in_session else '❌ NO'}")
    
    print(f"\n🔄 Checking if card appears in session after 1 minute...")
    future_session = scheduler.build_session([deck_id], now_ts + 60)  # 1 minute later
    card_in_future_session = any(c['card_id'] == card_id for c in future_session)
    print(f"   In 1-minute session: {'✅ YES' if card_in_future_session else '❌ NO'}")
    
    print(f"\n🎯 Expected behavior:")
    print(f"   - Card should be due in ~1 minute after hitting Again")
    print(f"   - Card should reappear in the same session after 1 minute")
    print(f"   - This allows immediate re-learning like Anki")

if __name__ == "__main__":
    test_again_behavior()