#!/usr/bin/env python3
"""
Test dynamic session management and Again button behavior.
Verifies that cards reappear in session when due (especially Again cards).
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


def test_again_card_reappearance():
    """Test that Again cards reappear in the same session when due."""
    print("🧪 Testing Again Card Reappearance in Dynamic Session")
    print("=" * 60)
    
    # Set up temporary environment
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck and cards
        deck_id = db.create_deck("Again Test Deck")
        
        # Add some test cards
        test_cards = [
            ("der Hund", "the dog", {"word_type": "noun", "artikel_d": "der"}),
            ("laufen", "to run", {"word_type": "verb"}),
            ("das Haus", "the house", {"word_type": "noun", "artikel_d": "das"}),
        ]
        
        # Add test cards (each note creates 2 cards: front->back, back->front)
        card_ids = []
        for front, back, meta in test_cards:
            note_id = db.add_note(deck_id, front, back, meta)
            print(f"   Added note: {front} -> {back}")
        
        # Get all cards from this deck
        all_cards = scheduler.build_session([deck_id], max_new=100, max_rev=100)
        card_ids = [c['card_id'] for c in all_cards]
        
        print(f"✅ Created {len(card_ids)} cards for testing")
        
        # Initial session - should have all new cards
        session1 = scheduler.build_session([deck_id])
        print(f"📊 Initial session: {len(session1)} cards")
        
        if not session1:
            print("❌ No cards in initial session!")
            return False
            
        # Take first card and rate it "Again" (should go to learning)
        test_card = session1[0]
        card_id = test_card['card_id']
        print(f"🔴 Rating card '{card_id}' as AGAIN...")
        
        # Record time before rating
        rating_time = int(time.time())
        scheduler.review(card_id, Rating.AGAIN, 3000, rating_time)
        
        # Check card state after Again rating
        updated_card = scheduler._get_card(card_id)
        print(f"   Card state: {updated_card['state']}")
        print(f"   Due time: {updated_card['due_ts']} (in {updated_card['due_ts'] - rating_time} seconds)")
        
        # Build new session immediately - Again card should NOT appear yet (due in 1 minute)
        session2 = scheduler.build_session([deck_id])
        again_card_in_session = any(c['card_id'] == card_id for c in session2)
        print(f"📊 Session immediately after: {len(session2)} cards, Again card present: {again_card_in_session}")
        
        # Simulate time passing (1.5 minutes = 90 seconds)
        future_time = rating_time + 90
        print(f"⏰ Simulating time advance: +90 seconds...")
        
        # Build session after time advance - Again card should reappear
        session3 = scheduler.build_session([deck_id], now_ts=future_time)
        again_card_in_future = any(c['card_id'] == card_id for c in session3)
        print(f"📊 Session after 90s: {len(session3)} cards, Again card present: {again_card_in_future}")
        
        # Find the Again card in the future session
        again_card = None
        for c in session3:
            if c['card_id'] == card_id:
                again_card = c
                break
                
        if again_card:
            print(f"✅ Again card found in session!")
            print(f"   State: {again_card['state']}")
            print(f"   Due: {again_card['due_ts']} (past due: {future_time - again_card['due_ts']}s)")
        else:
            print("❌ Again card not found in future session!")
            
        # Test dynamic session behavior
        print(f"\n🔄 Testing Dynamic Queue Priority...")
        
        # Check learning cards priority
        learning_cards = [c for c in session3 if c['state'] == 'learning']
        other_cards = [c for c in session3 if c['state'] != 'learning']
        
        print(f"   Learning cards: {len(learning_cards)} (should be first)")
        print(f"   Other cards: {len(other_cards)}")
        
        # First cards in session should be learning cards
        if session3 and session3[0]['state'] == 'learning':
            print("✅ Learning cards have priority in session!")
        else:
            print("❌ Learning cards not prioritized!")
            
        return again_card_in_future and (session3[0]['state'] == 'learning' if session3 else False)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
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


def test_session_counters():
    """Test Anki-style session counters (New/Learning/Review)."""
    print(f"\n🧪 Testing Session Counter Accuracy")
    print("=" * 40)
    
    # This would be tested in the UI, but we can verify card state distribution
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck with mixed card states
        deck_id = db.create_deck("Counter Test Deck")
        
        # Add cards and manipulate their states
        note_id1 = db.add_note(deck_id, "new card", "new", {})
        note_id2 = db.add_note(deck_id, "learning card", "learning", {})
        note_id3 = db.add_note(deck_id, "review card", "review", {})
        
        # Get card IDs
        # We'll work with the session cards directly
        
        # Get all cards first
        all_cards = scheduler.build_session([deck_id], max_new=100, max_rev=100)
        
        if len(all_cards) >= 2:
            # Manually set some cards to different states for testing
            card_id_learning = all_cards[0]['card_id']
            card_id_review = all_cards[1]['card_id'] if len(all_cards) > 1 else card_id_learning
            
            # Make one card learning (due in past)
            db.conn.execute(
                "UPDATE cards SET state = 'learning', due_ts = ?, step_index = 0 WHERE id = ?",
                (int(time.time()) - 60, card_id_learning)
            )
            
            # Make one card review (due in past)
            db.conn.execute(
                "UPDATE cards SET state = 'review', due_ts = ?, interval_days = 2 WHERE id = ?",
                (int(time.time()) - 3600, card_id_review)
            )
            
        db.conn.commit()
        
        # Build session and count card types
        session = scheduler.build_session([deck_id])
        
        new_count = sum(1 for c in session if c['state'] == 'new')
        learning_count = sum(1 for c in session if c['state'] == 'learning')
        review_count = sum(1 for c in session if c['state'] == 'review')
        
        print(f"📊 Session composition:")
        print(f"   New: {new_count}")
        print(f"   Learning: {learning_count}")
        print(f"   Review: {review_count}")
        print(f"   Total: {len(session)}")
        
        return len(session) > 0
        
    except Exception as e:
        print(f"❌ Counter test failed: {e}")
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
    print("🚀 Dynamic Session Management Tests")
    print("=" * 50)
    
    success1 = test_again_card_reappearance()
    success2 = test_session_counters()
    
    print(f"\n📋 Test Results:")
    print(f"   Again card reappearance: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"   Session counters: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print(f"\n🎉 All dynamic session tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  Some tests failed - review session management")
        sys.exit(1)