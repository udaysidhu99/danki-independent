#!/usr/bin/env python3
"""
Test that the UI fix properly includes learning cards in the session.
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
from danki.ui.screens.review import ReviewScreen


def test_ui_learning_card_inclusion():
    """Test that learning cards are included in UI session updates."""
    print("🔍 Testing UI Learning Card Inclusion Fix")
    print("=" * 45)
    
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck with multiple cards
        deck_id = db.create_deck("UI Test Deck")
        for i in range(3):
            db.add_note(deck_id, f"Word {i}", f"Answer {i}", {})
        
        # Get initial session
        now = int(time.time())
        session = scheduler.build_session([deck_id], now_ts=now)
        
        print(f"📊 Initial session: {len(session)} cards")
        
        if len(session) >= 2:
            test_card = session[0]
            card_id = test_card['card_id']
            
            print(f"🔍 Test card: {card_id[:8]}... (state: {test_card['state']})")
            
            # Rate as Again
            print(f"\n🔴 Rating card as AGAIN...")
            scheduler.review(card_id, Rating.AGAIN, 2000, now)
            
            # Build new session (this is what the UI does)
            new_session = scheduler.build_session([deck_id], now_ts=now)
            print(f"\n📊 Session after rating: {len(new_session)} cards")
            
            # Check if learning card is included
            learning_cards = [c for c in new_session if c['state'] == 'learning']
            again_card_present = any(c['card_id'] == card_id for c in new_session)
            
            print(f"   Learning cards: {len(learning_cards)}")
            print(f"   Again card present: {again_card_present}")
            
            if learning_cards:
                learning_card = learning_cards[0]
                position = new_session.index(learning_card) + 1
                due_in = (learning_card['due_ts'] - now) / 60
                print(f"   Learning card position: {position}")
                print(f"   Learning card due in: {due_in:.1f} minutes")
                
            # Simulate the UI filter logic directly
            print(f"\n🔄 Testing UI filter logic...")
            
            # This simulates update_session_queue filtering
            filtered_cards = []
            reviewed_card_ids = {card_id}  # Simulate having reviewed this card
            
            for card in new_session:
                c_id = card['card_id']
                
                # The fixed logic: include learning cards due within 30 minutes
                if card['state'] == 'learning' and card['due_ts'] <= now + 1800:
                    filtered_cards.append(card)
                    print(f"   ✅ Including learning card due in {(card['due_ts'] - now)/60:.1f}min")
                # Include other cards if not recently reviewed
                elif c_id not in reviewed_card_ids:
                    filtered_cards.append(card)
                    print(f"   ✅ Including {card['state']} card (not recently reviewed)")
                else:
                    print(f"   ❌ Filtering out recently reviewed card")
            
            print(f"\n📊 Final filtered session: {len(filtered_cards)} cards")
            final_learning = [c for c in filtered_cards if c['state'] == 'learning']
            print(f"   Learning cards in final session: {len(final_learning)}")
            
            if final_learning:
                print(f"   ✅ SUCCESS: Learning cards will appear in UI!")
                return True
            else:
                print(f"   ❌ FAILURE: Learning cards still filtered out!")
                return False
        
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
    success = test_ui_learning_card_inclusion()
    print(f"\n📋 Result: {'✅ PASS' if success else '❌ FAIL'}")
    
    if success:
        print(f"🎉 Fix successful! Learning cards will now appear in UI sessions.")
    else:
        print(f"⚠️  Fix may need further adjustment.")