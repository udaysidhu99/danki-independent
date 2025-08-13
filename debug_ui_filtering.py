#!/usr/bin/env python3
"""
Debug the UI filtering logic to understand immediate repetition.
"""

import sys
import time
import tempfile
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from danki.engine.scheduler import Scheduler, Rating
from danki.engine.db import Database


def simulate_ui_filtering(new_cards, reviewed_card_ids=None, card_review_sequence=None):
    """Simulate the UI filtering logic from update_session_queue."""
    if reviewed_card_ids is None:
        reviewed_card_ids = set()
    if card_review_sequence is None:
        card_review_sequence = []
    
    filtered_cards = []
    now = int(time.time())
    
    print(f"🔍 Filtering {len(new_cards)} cards...")
    print(f"   Reviewed card IDs: {[c_id[:8] + '...' for c_id in reviewed_card_ids]}")
    print(f"   Review sequence: {[c_id[:8] + '...' for c_id in card_review_sequence]}")
    
    for i, card in enumerate(new_cards):
        card_id = card['card_id']
        state = card['state']
        due_ts = card['due_ts']
        
        print(f"\n   Card {i+1}: {card_id[:8]}... (state: {state})")
        print(f"           Due in: {(due_ts - now)/60:.1f} minutes")
        
        # For learning cards, ensure proper interleaving (not immediate repetition)
        if state == 'learning':
            # Check if this card was one of the last 3 reviewed cards
            recent_reviews = card_review_sequence[-3:] if len(card_review_sequence) >= 3 else card_review_sequence
            
            in_recent = card_id in recent_reviews
            due_now = due_ts <= now
            no_other_cards = len([c for c in new_cards if c['state'] != 'learning' and c['card_id'] not in reviewed_card_ids]) == 0
            
            print(f"           In recent 3: {in_recent}")
            print(f"           Due now: {due_now}")
            print(f"           No other cards: {no_other_cards}")
            
            # Include learning cards if:
            # 1. They haven't been reviewed recently (not in last 3), OR
            # 2. They're actually due now (not just due within 30 minutes), OR
            # 3. There are no other cards to show
            if (not in_recent or due_now or no_other_cards):
                filtered_cards.append(card)
                print(f"           ✅ INCLUDED")
            else:
                print(f"           ❌ FILTERED OUT")
        else:
            # Include other cards if not recently reviewed  
            if card_id not in reviewed_card_ids:
                filtered_cards.append(card)
                print(f"           ✅ INCLUDED (new/review card)")
            else:
                print(f"           ❌ FILTERED OUT (recently reviewed)")
    
    return filtered_cards


def test_ui_filtering_logic():
    """Test the UI filtering logic step by step."""
    print("🔍 Testing UI Filtering Logic")
    print("=" * 35)
    
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck
        deck_id = db.create_deck("UI Filter Test Deck")
        for i in range(4):
            db.add_note(deck_id, f"Word {i}", f"Translation {i}", {})
        
        # Build initial session
        now = int(time.time())
        session = scheduler.build_session([deck_id], now_ts=now)
        
        print(f"📊 Initial session: {len(session)} cards")
        
        # Simulate rating first card as "Again"
        first_card = session[0]
        card_id = first_card['card_id']
        
        print(f"\n🔴 Rating card {card_id[:8]}... as AGAIN")
        scheduler.review(card_id, Rating.AGAIN, 2000, now)
        
        # Build new session (what scheduler provides)
        new_session = scheduler.build_session([deck_id], now_ts=now)
        print(f"\n📊 New session from scheduler: {len(new_session)} cards")
        
        # Simulate UI state
        reviewed_card_ids = {card_id}
        card_review_sequence = [card_id]
        
        # Apply UI filtering
        filtered_cards = simulate_ui_filtering(new_session, reviewed_card_ids, card_review_sequence)
        
        print(f"\n📊 Final filtered session: {len(filtered_cards)} cards")
        
        # Check if the rated card appears in filtered results
        appears_immediately = len(filtered_cards) > 0 and filtered_cards[0]['card_id'] == card_id
        
        if appears_immediately:
            print(f"❌ ISSUE: Rated card appears immediately in filtered session")
            return False
        else:
            print(f"✅ SUCCESS: Rated card properly filtered from immediate appearance")
            return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        try:
            if 'scheduler' in locals():
                scheduler.db.close()
            if 'db' in locals():
                db.close()
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
        except:
            pass


if __name__ == "__main__":
    success = test_ui_filtering_logic()
    print(f"\n📋 Result: {'✅ PASS' if success else '❌ FAIL'}")