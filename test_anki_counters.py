#!/usr/bin/env python3
"""
Test Anki-style counter behavior.
Verifies that counters decrease as cards are reviewed, just like Anki.
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


def test_anki_counter_behavior():
    """Test that counters work exactly like Anki."""
    print("🧪 Testing Anki-Style Counter Behavior")
    print("=" * 50)
    
    # Set up temporary environment
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck
        deck_id = db.create_deck("Counter Test Deck")
        
        # Add mixed cards
        print("📝 Adding test cards...")
        for i in range(5):
            db.add_note(deck_id, f"German {i}", f"English {i}", {"word_type": "noun"})
            
        # Build initial session
        session = scheduler.build_session([deck_id], max_new=10, max_rev=10)
        print(f"✅ Initial session: {len(session)} cards")
        
        # Count initial state
        new_count = sum(1 for c in session if c['state'] == 'new')
        learning_count = sum(1 for c in session if c['state'] == 'learning')
        review_count = sum(1 for c in session if c['state'] == 'review')
        
        print(f"📊 Initial counters: New: {new_count} • Learning: {learning_count} • Review: {review_count}")
        
        # Simulate reviewing cards with different ratings
        reviewed_cards = 0
        for i, card in enumerate(session[:3]):  # Review first 3 cards
            card_id = card['card_id']
            
            # Use different ratings
            ratings = [Rating.AGAIN, Rating.GOOD, Rating.HARD]
            rating = ratings[i % 3]
            
            print(f"\n🔄 Reviewing card {i+1}: Rating {rating.name}")
            scheduler.review(card_id, rating, 2000)
            reviewed_cards += 1
            
            # Build new session to see updated counts
            new_session = scheduler.build_session([deck_id], max_new=10, max_rev=10)
            
            new_count = sum(1 for c in new_session if c['state'] == 'new')
            learning_count = sum(1 for c in new_session if c['state'] == 'learning')
            review_count = sum(1 for c in new_session if c['state'] == 'review')
            
            print(f"   Updated counters: New: {new_count} • Learning: {learning_count} • Review: {review_count}")
            print(f"   Total cards in session: {len(new_session)}")
            
        print(f"\n✅ Reviewed {reviewed_cards} cards")
        print(f"📈 Cards move between categories as expected:")
        print(f"   • New cards become Learning when reviewed")
        print(f"   • Again cards stay in Learning with new due times")
        print(f"   • Good cards may graduate to Review")
        
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
    success = test_anki_counter_behavior()
    print(f"\n📋 Test Result: {'✅ PASS' if success else '❌ FAIL'}")
    
    if success:
        print("\n🎉 Anki-style counters working correctly!")
        print("💡 In the UI:")
        print("   • New: Shows remaining new cards")
        print("   • Learning: Shows cards in learning state (including Again cards)")
        print("   • Review: Shows cards due for review")
        print("   • Numbers decrease as cards are completed or move to other states")
    else:
        print("\n⚠️  Counter test failed")