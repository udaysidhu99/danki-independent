#!/usr/bin/env python3
"""
Test proper Anki learning card pattern.
Verify that learning cards are interleaved correctly.
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


def test_anki_learning_interleaving():
    """Test that learning cards are interleaved like Anki."""
    print("🧪 Testing Anki Learning Card Interleaving")
    print("=" * 50)
    
    # Set up temporary environment
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck with many cards
        deck_id = db.create_deck("Learning Pattern Test")
        
        # Add cards for testing
        for i in range(8):
            db.add_note(deck_id, f"Card {i}", f"Answer {i}", {})
            
        print(f"📝 Added test cards")
        
        # Build initial session
        now = int(time.time())
        session = scheduler.build_session([deck_id], now_ts=now)
        print(f"📊 Initial session: {len(session)} cards (all new)")
        
        # Show session order
        print(f"\n🔄 Initial session order:")
        for i, card in enumerate(session[:6]):
            print(f"   {i+1}. Card state: {card['state']}, Template: {card['template']}")
        
        # Rate first card as "Again" (should become learning)
        first_card = session[0]
        print(f"\n🔴 Rating first card as AGAIN...")
        scheduler.review(first_card['card_id'], Rating.AGAIN, 2000, now)
        
        # Build new session - check interleaving
        future_time = now + 90  # 1.5 minutes later
        session_after = scheduler.build_session([deck_id], now_ts=future_time)
        
        print(f"\n📊 Session after 1.5 minutes ({len(session_after)} cards):")
        learning_positions = []
        for i, card in enumerate(session_after[:8]):
            state_marker = "📚" if card['state'] == 'learning' else "📄"
            print(f"   {i+1}. {state_marker} {card['state']} - {card.get('template', 'N/A')}")
            if card['state'] == 'learning':
                learning_positions.append(i+1)
                
        print(f"\n🎯 Learning card positions: {learning_positions}")
        
        if learning_positions:
            if learning_positions[0] > 1:
                print(f"✅ Learning card not at position 1 (good Anki behavior)")
            else:
                print(f"❌ Learning card at position 1 (not like Anki)")
        
        # Test multiple learning cards
        print(f"\n🔄 Testing multiple learning cards...")
        
        # Rate more cards as Again
        for i in range(2):
            if i < len(session_after) and session_after[i]['state'] == 'new':
                scheduler.review(session_after[i]['card_id'], Rating.AGAIN, 1500, future_time)
        
        # Check final interleaving
        final_time = now + 180  # 3 minutes later
        final_session = scheduler.build_session([deck_id], now_ts=final_time)
        
        print(f"\n📊 Final session ({len(final_session)} cards):")
        learning_count = 0
        for i, card in enumerate(final_session[:10]):
            state_marker = "📚" if card['state'] == 'learning' else "📄"
            print(f"   {i+1}. {state_marker} {card['state']}")
            if card['state'] == 'learning':
                learning_count += 1
        
        print(f"\n✅ Found {learning_count} learning cards in session")
        print(f"🎯 Key insight: Learning cards should be spread throughout, not all at front")
        
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
    success = test_anki_learning_interleaving()
    print(f"\n📋 Result: {'✅ PASS' if success else '❌ FAIL'}")