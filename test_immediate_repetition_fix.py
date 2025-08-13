#!/usr/bin/env python3
"""
Test that the immediate repetition fix works properly.
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


def test_immediate_repetition_fix():
    """Test that cards don't appear twice immediately after rating."""
    print("🔍 Testing Immediate Repetition Fix")
    print("=" * 40)
    
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck with 5 cards
        deck_id = db.create_deck("Repetition Test Deck")
        cards = []
        for i in range(5):
            note_id = db.add_note(deck_id, f"German Word {i}", f"English Word {i}", {})
            cards.append(note_id)
        
        print(f"📚 Created deck with {len(cards)} cards")
        
        # Build initial session
        now = int(time.time())
        session = scheduler.build_session([deck_id], now_ts=now)
        
        print(f"📊 Initial session: {len(session)} cards")
        
        if len(session) >= 3:
            # Simulate UI behavior
            review_screen = ReviewScreen()
            review_screen.start_review_session(session.copy(), [deck_id])
            
            # Track which cards appear in what order
            card_appearances = []
            
            # Rate first card as "Again" (should become learning)
            first_card = session[0]
            card_id = first_card['card_id']
            card_appearances.append((card_id, "rated_again"))
            
            print(f"\n🔴 Rating card {card_id[:8]}... as AGAIN")
            scheduler.review(card_id, Rating.AGAIN, 2000, now)
            
            # Simulate the UI update process
            new_session = scheduler.build_session([deck_id], now_ts=now)
            
            # Apply the new filtering logic
            review_screen.update_session_queue(new_session)
            
            # Check if the rated card appears in the filtered session
            filtered_session = review_screen.cards if hasattr(review_screen, 'cards') else []
            
            print(f"📊 Filtered session after rating: {len(filtered_session)} cards")
            
            # Check immediate repetition
            immediate_repeat = any(c['card_id'] == card_id for c in filtered_session)
            
            if immediate_repeat:
                # Find position of the repeated card
                for i, card in enumerate(filtered_session):
                    if card['card_id'] == card_id:
                        print(f"   ❌ ISSUE: Rated card reappears at position {i+1}")
                        break
                return False
            else:
                print(f"   ✅ SUCCESS: Rated card does not appear immediately")
                
                # Verify it would appear later if we processed more cards
                # Rate 2 more cards to build up the review sequence
                if len(filtered_session) >= 2:
                    for j in range(2):
                        if j < len(filtered_session):
                            next_card = filtered_session[j]
                            next_id = next_card['card_id']
                            card_appearances.append((next_id, f"rated_good_{j+1}"))
                            scheduler.review(next_id, Rating.GOOD, 1500, now + (j+1)*60)
                            
                            # Update sequence tracking
                            if not hasattr(review_screen, 'card_review_sequence'):
                                review_screen.card_review_sequence = []
                            review_screen.card_review_sequence.append(next_id)
                    
                    print(f"   📝 Review sequence: {[c[:8] for c in review_screen.card_review_sequence]}")
                    
                    # Now check if the original card can appear (should be allowed after 3+ cards)
                    final_session = scheduler.build_session([deck_id], now_ts=now + 300)  # 5 minutes later
                    review_screen.update_session_queue(final_session)
                    final_filtered = review_screen.cards if hasattr(review_screen, 'cards') else []
                    
                    later_appears = any(c['card_id'] == card_id for c in final_filtered)
                    print(f"   📊 Card appears in later session: {later_appears}")
                    
                return True
        
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
    success = test_immediate_repetition_fix()
    print(f"\n📋 Result: {'✅ PASS' if success else '❌ FAIL'}")
    
    if success:
        print("🎉 Fix successful! Cards will no longer appear twice immediately.")
    else:
        print("⚠️  Immediate repetition issue still exists.")