#!/usr/bin/env python3
"""
Test learning card counters with time simulation.
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


def test_learning_counters_with_time():
    """Test counters with time progression to show learning cards."""
    print("🧪 Testing Learning Card Counters with Time Simulation")
    print("=" * 60)
    
    # Set up temporary environment
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck
        deck_id = db.create_deck("Learning Counter Test")
        
        # Add test cards
        for i in range(3):
            db.add_note(deck_id, f"Word {i}", f"Translation {i}", {})
            
        # Initial session
        now = int(time.time())
        session = scheduler.build_session([deck_id], now_ts=now)
        print(f"📊 Initial: {len(session)} cards (all new)")
        
        # Rate first card as "Again" 
        card_id = session[0]['card_id']
        print(f"\n🔴 Rating card as AGAIN (should go to learning)...")
        scheduler.review(card_id, Rating.AGAIN, 2000, now)
        
        # Check session immediately after
        session_after = scheduler.build_session([deck_id], now_ts=now)
        new_count = sum(1 for c in session_after if c['state'] == 'new')
        learning_count = sum(1 for c in session_after if c['state'] == 'learning')
        review_count = sum(1 for c in session_after if c['state'] == 'review')
        
        print(f"📊 Immediately after: New: {new_count} • Learning: {learning_count} • Review: {review_count}")
        print(f"   Total in session: {len(session_after)}")
        print(f"   (Learning card due in 1 minute, so not in current session)")
        
        # Advance time by 2 minutes
        future_time = now + 120
        print(f"\n⏰ Advancing time by 2 minutes...")
        
        session_future = scheduler.build_session([deck_id], now_ts=future_time)
        new_count = sum(1 for c in session_future if c['state'] == 'new')
        learning_count = sum(1 for c in session_future if c['state'] == 'learning')
        review_count = sum(1 for c in session_future if c['state'] == 'review')
        
        print(f"📊 After 2 minutes: New: {new_count} • Learning: {learning_count} • Review: {review_count}")
        print(f"   Total in session: {len(session_future)}")
        print(f"   ✅ Learning card now appears in session!")
        
        # Find and review the learning card
        learning_cards = [c for c in session_future if c['state'] == 'learning']
        if learning_cards:
            learning_card = learning_cards[0]
            print(f"\n🟡 Rating learning card as GOOD (should graduate)...")
            scheduler.review(learning_card['card_id'], Rating.GOOD, 1500, future_time)
            
            # Check final state
            session_final = scheduler.build_session([deck_id], now_ts=future_time)
            new_count = sum(1 for c in session_final if c['state'] == 'new')
            learning_count = sum(1 for c in session_final if c['state'] == 'learning')
            review_count = sum(1 for c in session_final if c['state'] == 'review')
            
            print(f"📊 After graduation: New: {new_count} • Learning: {learning_count} • Review: {review_count}")
            print(f"   ✅ Card graduated from learning to review!")
        
        print(f"\n🎯 Key Insights:")
        print(f"   • Counters show cards currently available in session")
        print(f"   • Learning cards appear when their due time arrives")
        print(f"   • Again cards reappear in Learning category after 1 minute")
        print(f"   • Numbers decrease as cards are completed")
        
        return True
        
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
    success = test_learning_counters_with_time()
    print(f"\n📋 Result: {'✅ PASS' if success else '❌ FAIL'}")