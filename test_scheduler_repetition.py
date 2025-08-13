#!/usr/bin/env python3
"""
Test the scheduler behavior for immediate repetition without UI components.
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


def test_scheduler_repetition_behavior():
    """Test that scheduler properly handles card transitions."""
    print("🔍 Testing Scheduler Repetition Behavior")
    print("=" * 45)
    
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck with multiple cards
        deck_id = db.create_deck("Scheduler Test Deck")
        note_ids = []
        for i in range(5):
            note_id = db.add_note(deck_id, f"German {i}", f"English {i}", {})
            note_ids.append(note_id)
        
        print(f"📚 Created deck with {len(note_ids)} notes")
        
        # Build initial session
        now = int(time.time())
        session = scheduler.build_session([deck_id], now_ts=now)
        
        print(f"📊 Initial session: {len(session)} cards")
        print(f"   States: {[c['state'] for c in session]}")
        
        if len(session) >= 3:
            # Track first card
            first_card = session[0]
            card_id = first_card['card_id']
            
            print(f"\n🔍 Testing card: {card_id[:8]}... (state: {first_card['state']})")
            
            # Rate first card as "Again"
            print(f"🔴 Rating as AGAIN...")
            scheduler.review(card_id, Rating.AGAIN, 2000, now)
            
            # Check card state after rating
            updated_card = db.conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
            if updated_card:
                print(f"   New state: {updated_card['state']}")
                print(f"   Due in: {(updated_card['due_ts'] - now)/60:.1f} minutes")
            
            # Build new session immediately (simulates dynamic rebuild)
            new_session = scheduler.build_session([deck_id], now_ts=now)
            
            print(f"\n📊 Session after rating: {len(new_session)} cards")
            print(f"   States: {[c['state'] for c in new_session]}")
            
            # Check if the same card appears in new session
            card_positions = []
            for i, card in enumerate(new_session):
                if card['card_id'] == card_id:
                    card_positions.append(i)
            
            if card_positions:
                print(f"   🔍 Rated card appears at positions: {[p+1 for p in card_positions]}")
                
                # This is expected - learning cards due soon should appear
                # The issue is in UI filtering, not scheduler logic
                if card_positions[0] == 0:
                    print(f"   ⚠️  Card appears IMMEDIATELY (position 1) - this causes UI issue")
                else:
                    print(f"   ✅ Card appears later in session (position {card_positions[0]+1})")
            else:
                print(f"   ❌ Card doesn't appear at all - this would be a bug too")
            
            # Test with more time passed
            print(f"\n🕐 Testing after 2 minutes...")
            future_session = scheduler.build_session([deck_id], now_ts=now + 120)
            future_card_positions = [i for i, card in enumerate(future_session) if card['card_id'] == card_id]
            
            if future_card_positions:
                print(f"   📊 Card appears at positions: {[p+1 for p in future_card_positions]}")
            else:
                print(f"   📊 Card doesn't appear yet")
                
            return len(new_session) > 0  # Success if session has cards
        
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
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
    success = test_scheduler_repetition_behavior()
    print(f"\n📋 Result: {'✅ PASS' if success else '❌ FAIL'}")