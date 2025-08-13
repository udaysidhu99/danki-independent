#!/usr/bin/env python3
"""
Debug the "Again" button behavior to see why cards are disappearing.
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


def debug_again_card_flow():
    """Debug the complete flow when a card is rated Again."""
    print("🔍 Debugging Again Card Flow")
    print("=" * 40)
    
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck
        deck_id = db.create_deck("Debug Test")
        note_id = db.add_note(deck_id, "Test Word", "Test Answer", {})
        
        # Get initial session
        now = int(time.time())
        session = scheduler.build_session([deck_id], now_ts=now)
        
        print(f"📊 Initial session: {len(session)} cards")
        if session:
            test_card = session[0]
            card_id = test_card['card_id']
            
            print(f"🔍 Test card before review:")
            print(f"   ID: {card_id}")
            print(f"   State: {test_card['state']}")
            print(f"   Due: {test_card['due_ts']}")
            print(f"   Step: {test_card['step_index']}")
            
            # Rate as Again
            print(f"\n🔴 Rating card as AGAIN...")
            scheduler.review(card_id, Rating.AGAIN, 2000, now)
            
            # Check card state immediately after
            updated_card = scheduler._get_card(card_id)
            print(f"\n🔍 Card after AGAIN rating:")
            print(f"   State: {updated_card['state']}")
            print(f"   Due: {updated_card['due_ts']} (now: {now})")
            print(f"   Due in: {(updated_card['due_ts'] - now)} seconds")
            print(f"   Step: {updated_card['step_index']}")
            print(f"   Interval: {updated_card['interval_days']}")
            
            # Check if card appears in immediate session
            session_immediate = scheduler.build_session([deck_id], now_ts=now)
            card_in_immediate = any(c['card_id'] == card_id for c in session_immediate)
            print(f"\n📊 Card in immediate session: {card_in_immediate}")
            print(f"   Session size: {len(session_immediate)}")
            
            # Check if card appears when due
            due_time = updated_card['due_ts'] + 10  # 10 seconds after due
            session_when_due = scheduler.build_session([deck_id], now_ts=due_time)
            card_when_due = any(c['card_id'] == card_id for c in session_when_due)
            print(f"\n📊 Card appears when due: {card_when_due}")
            print(f"   Session size when due: {len(session_when_due)}")
            
            if session_when_due:
                print(f"\n🔍 Cards in session when due:")
                for i, card in enumerate(session_when_due):
                    marker = "🎯" if card['card_id'] == card_id else "📄"
                    print(f"   {i+1}. {marker} {card['state']} - ID: {card['card_id']}")
            
            # Test the dynamic queue rebuild functionality
            print(f"\n🔄 Testing dynamic queue rebuild...")
            
            # Simulate what happens in the UI
            print(f"   1. Card rated → scheduler.review() called ✅")
            print(f"   2. Queue should rebuild → checking...")
            
            # This simulates the rebuild_review_queue() call
            new_session = scheduler.build_session([deck_id], now_ts=due_time)
            learning_cards = [c for c in new_session if c['state'] == 'learning']
            
            print(f"   3. New session has {len(learning_cards)} learning cards")
            
            if learning_cards:
                print(f"   ✅ Learning card found in rebuilt session!")
                learning_card = learning_cards[0]
                print(f"      Position: {new_session.index(learning_card) + 1}")
                print(f"      State: {learning_card['state']}")
                print(f"      Due: {learning_card['due_ts']} vs now: {due_time}")
            else:
                print(f"   ❌ No learning cards in rebuilt session!")
                
                # Check database directly
                all_cards = db.conn.execute(
                    "SELECT * FROM cards WHERE note_id = ?", (note_id,)
                ).fetchall()
                
                print(f"\n🔍 Direct database check:")
                for card in all_cards:
                    print(f"   Card {card['id'][:8]}...")
                    print(f"     State: {card['state']}")
                    print(f"     Due: {card['due_ts']}")
                    print(f"     Step: {card['step_index']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
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
    debug_again_card_flow()